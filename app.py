from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import os
import csv
import io
from extensions import db
from datetime import datetime, date, timedelta
import calendar
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True)

# Configure upload settings
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models import MoodEntry, User


def _to_date(val):
    """Normalize an entry_date-like value to a datetime.date or return None.

    Handles: date, datetime, ISO date/time strings, YYYYMMDD ints/strings, and unix timestamps.
    """
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        s = val.strip()
        # Try ISO date first
        try:
            return date.fromisoformat(s)
        except Exception:
            pass
        # Try ISO datetime
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            pass
        # Try YYYYMMDD
        if s.isdigit():
            if len(s) == 8:
                try:
                    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
                except Exception:
                    pass
            # Try unix timestamp
            try:
                return datetime.fromtimestamp(int(s)).date()
            except Exception:
                pass
        return None
    if isinstance(val, int):
        s = str(val)
        if len(s) == 8:
            try:
                return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except Exception:
                pass
        try:
            return datetime.fromtimestamp(val).date()
        except Exception:
            return None
    return None


def _normalize_entries(entries):
    """Mutate a list of MoodEntry objects so their `entry_date` attributes are date objects when possible."""
    if not entries:
        return
    for e in entries:
        ed = _to_date(e.entry_date)
        if ed is not None:
            # assign back for template rendering (no commit)
            e.entry_date = ed


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('home'))

        elif user and str(user.pin) == password:
            session['logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            # Match test expectations: show a generic invalid credential message
            flash("Invalid username or password", 'error')
            return redirect(url_for('login'))

    return render_template('home/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        pin = request.form.get('PIN')

        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))

        # Create new user (preserve PIN functionality)
        new_user = User(username=username, email=email, pin=pin)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('home/register.html')

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    today = datetime.utcnow().date()

    # check if user has logged today
    has_logged_today = MoodEntry.query.filter_by(
        user_id=user_id,
        entry_date=today
    ).first() is not None

    reminder_banner_home = None
    if not has_logged_today:
        reminder_banner_home = "Don’t forget to log your mood today"

    return render_template(
        'home/index.html',
        page_id='home',
        reminder_banner_home=reminder_banner_home
    )



@app.route('/profile')
def profile():
    """Display user's personal information"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your profile', 'error')
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)

    total_entries = MoodEntry.query.filter_by(user_id=user_id).count()
    recent_entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.timestamp.desc()).limit(5).all()
    # Normalize recent entry dates for template rendering
    _normalize_entries(recent_entries)
    return render_template('home/profile.html', user=user, total_entries=total_entries, recent_entries=recent_entries)


@app.route('/logs')
def logs():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if user_id:
        entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.timestamp.desc()).all()
        _normalize_entries(entries)
    else:
        entries = []

    return render_template('mood_journal/logs.html', entries=entries, page_id='home')


@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    entry = MoodEntry.query.get_or_404(entry_id)

    if entry.user_id != user_id:
        flash('You can only delete your own entries', 'error')
        return redirect(url_for('logs'))

    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted successfully!')
    return redirect(url_for('logs'))


@app.route('/delete-all-entries', methods=['POST'])
def delete_all_entries():
    """Delete all entries for the currently logged-in user."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to perform this action', 'error')
        return redirect(url_for('login'))

    # Remove all mood entries for this user
    try:
        MoodEntry.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        db.session.commit()
        flash('All entries deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Failed to delete all entries')
        flash('Failed to delete all entries', 'error')

    return redirect(url_for('logs'))


@app.route('/toggle-privacy/<int:entry_id>', methods=['POST'])
def toggle_privacy(entry_id):
    # Support both normal form posts and AJAX requests
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('Accept', '').find('application/json') != -1

    if not session.get('logged_in'):
        if is_ajax:
            return jsonify({'error': 'login_required'}), 401
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    entry = MoodEntry.query.get_or_404(entry_id)
    if entry.user_id != user_id:
        if is_ajax:
            return jsonify({'error': 'not_owner'}), 403
        flash('You can only modify your own entries', 'error')
        return redirect(url_for('logs'))

    # Use getattr for safe attribute access with fallback
    entry.is_private = not getattr(entry, 'is_private', False)
    db.session.commit()
    status = 'locked (private)' if entry.is_private else 'unlocked (public)'
    if is_ajax:
        return jsonify({'is_private': entry.is_private, 'status': status}), 200

    flash(f'Entry {status}!', 'success')
    return redirect(url_for('logs'))


@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    entry = MoodEntry.query.get_or_404(entry_id)

    if entry.user_id != user_id:
        flash('You can only edit your own entries', 'error')
        return redirect(url_for('logs'))

    if request.method == 'POST':
        entry.mood_label = request.form.get('mood_label')

        date_str = request.form.get('entry_date')
        if date_str:
            entry.entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        entry.mood_rating = int(request.form.get('mood_rating', 5))
        entry.notes = request.form.get('notes')

        # Handle image removal
        if request.form.get('remove_image') == '1' and entry.image_path:
            # Delete the old image file
            old_image_path = os.path.join(basedir, 'static', entry.image_path)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
            entry.image_path = None

        # Handle new image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Delete old image if exists
                if entry.image_path:
                    old_image_path = os.path.join(basedir, 'static', entry.image_path)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                entry.image_path = os.path.join('uploads', unique_filename)
            elif file and file.filename != '':
                flash('Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, or WEBP).', 'error')

        db.session.commit()
        flash('Entry updated successfully!')
        return redirect(url_for('logs'))

    return render_template('mood_journal/edit.html', entry=entry)


@app.route('/export/<int:entry_id>')
def export_single_entry(entry_id):
    entry = MoodEntry.query.get_or_404(entry_id)
    
    # Check if entry is private; if so, deny access
    if getattr(entry, 'is_private', False):
        flash('Cannot export private entries.', 'error')
        return redirect(url_for('logs'))

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Entry ID", "Date", "Mood Label", "Rating",
        "Notes", "Time Spent (sec)", "Created At"
    ])

    # Single row
    ed = _to_date(entry.entry_date) or entry.entry_date
    ed_str = ed.strftime("%Y-%m-%d") if hasattr(ed, 'strftime') else str(ed)
    writer.writerow([
        entry.id,
        ed_str,
        entry.mood_label,
        entry.mood_rating,
        entry.notes or "",
        entry.time_spent_seconds or 0,
        entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=entry_{entry.id}.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route('/export-all')
def export_all_entries():
    # Only export non-private entries (check if column exists for backward compatibility)
    try:
        entries = MoodEntry.query.filter_by(is_private=False).order_by(MoodEntry.entry_date.desc()).all()
    except Exception:
        # Fallback if is_private column doesn't exist
        entries = MoodEntry.query.order_by(MoodEntry.entry_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Entry ID", "Date", "Mood Label", "Rating",
        "Notes", "Time Spent (sec)", "Created At"
    ])

    for entry in entries:
        writer.writerow([
            entry.id,
            (_to_date(entry.entry_date) or entry.entry_date).strftime("%Y-%m-%d") if (_to_date(entry.entry_date) or entry.entry_date) else "",
            entry.mood_label,
            entry.mood_rating,
            entry.notes or "",
            entry.time_spent_seconds or 0,
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=all_entries.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route('/export-range')
def export_range():
    start = request.args.get('start_date')
    end = request.args.get('end_date')

    if not start or not end:
        flash("Please choose both start and end dates.", "error")
        return redirect(url_for('logs'))

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for('logs'))

    # Only export non-private entries
    try:
        entries = MoodEntry.query.filter(
            MoodEntry.entry_date >= start_date,
            MoodEntry.entry_date <= end_date,
            MoodEntry.is_private == False
        ).order_by(MoodEntry.entry_date.asc()).all()
    except Exception:
        # Fallback if is_private column doesn't exist
        entries = MoodEntry.query.filter(
            MoodEntry.entry_date >= start_date,
            MoodEntry.entry_date <= end_date
        ).order_by(MoodEntry.entry_date.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Entry ID", "Date", "Mood Label", "Rating",
        "Notes", "Time Spent (sec)", "Created At"
    ])

    for entry in entries:
        ed = _to_date(entry.entry_date) or entry.entry_date
        ed_str = ed.strftime("%Y-%m-%d") if hasattr(ed, 'strftime') else str(ed)
        writer.writerow([
            entry.id,
            ed_str,
            entry.mood_label,
            entry.mood_rating,
            entry.notes or "",
            entry.time_spent_seconds or 0,
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=entries_{start}_to_{end}.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view dashboard', 'error')
        return redirect(url_for('login'))

    today = datetime.now()
    try:
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))
    except (TypeError, ValueError):
        year = today.year
        month = today.month

    # Normalize month/year so month wraps across years (e.g., month=13 -> month=1, year+1)
    # Convert to a zero-based month index and recompute year/month
    total_months = year * 12 + (month - 1)
    norm_year = total_months // 12
    norm_month = (total_months % 12) + 1
    year = norm_year
    month = norm_month

    calendar.setfirstweekday(calendar.SUNDAY)

    cal = calendar.monthcalendar(year, month)

    # start is first day of the normalized month; end is first day of next month
    start_date = date(year, month, 1)
    # compute next month/year using the same normalization logic
    next_total = year * 12 + (month - 1) + 1
    next_year = next_total // 12
    next_month = (next_total % 12) + 1
    end_date = date(next_year, next_month, 1)

    entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.entry_date >= start_date,
        MoodEntry.entry_date < end_date
    ).order_by(MoodEntry.entry_date).all()

    mood_lookup = {}
    for entry in entries:
        ed = _to_date(entry.entry_date)
        if ed is not None:
            mood_lookup[ed] = entry.mood_rating

    # Original numeric bucket function (used for charts)
    def bucket(r):
        if r <= 2:
            return 1
        if r <= 4:
            return 2
        if r <= 6:
            return 3
        if r <= 8:
            return 4
        return 5

    selected_filter = request.args.get("filter") or None

    # Named bucket for calendar/filter
    def get_bucket(r):
        if r is None:
            return None
        if r <= 2:
            return "terrible"
        if r <= 4:
            return "bad"
        if r <= 6:
            return "neutral"
        if r <= 8:
            return "good"
        return "excellent"

    # Build full calendar data
    calendar_dates = []
    for week in cal:
        row = []
        for d in week:
            if d == 0:
                row.append((None, None, None))
            else:
                cell_date = date(year, month, d)
                mood = mood_lookup.get(cell_date)
                bucket_name = get_bucket(mood) if mood else None
                row.append((cell_date, mood, bucket_name))
        calendar_dates.append(row)

    # Count bucket totals
    bucket_counts = {
        "terrible": 0,
        "bad": 0,
        "neutral": 0,
        "good": 0,
        "excellent": 0,
    }

    for week in calendar_dates:
        for day, mood, bucket_name in week:
            if bucket_name:
                bucket_counts[bucket_name] += 1

    # If no moods at all, default summary to neutral/0
    if any(bucket_counts.values()):
        summary_bucket_name = selected_filter if selected_filter else max(
            bucket_counts, key=lambda b: bucket_counts[b]
        )
    else:
        summary_bucket_name = selected_filter or "neutral"

    bucket_label_map = {
        "terrible": "Terrible (1–2)",
        "bad": "Bad (3–4)",
        "neutral": "Neutral (5–6)",
        "good": "Good (7–8)",
        "excellent": "Excellent (9–10)",
    }

    bucket_msg_map = {
        "terrible": "Rough days, please be kind to yourself.",
        "bad": "Tougher days, take note of what drains you.",
        "neutral": "Pretty steady, a neutral baseline.",
        "good": "Plenty of good days!",
        "excellent": "Lots of amazing days, celebrate what’s working.",
    }

    summary_days = bucket_counts.get(summary_bucket_name, 0)
    summary_label = bucket_label_map[summary_bucket_name]
    summary_message = bucket_msg_map[summary_bucket_name]
    summary_day_word = "day" if summary_days == 1 else "days"

    total_entries = len(entries)
    average_mood = (
        sum(e.mood_rating for e in entries) / total_entries
        if total_entries > 0 else 0
    )

    mood_distribution = [0] * 5
    for e in entries:
        mood_distribution[bucket(e.mood_rating) - 1] += 1

    week_start = (today - timedelta(days=today.weekday())).date()
    week_entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.entry_date >= week_start,
        MoodEntry.entry_date < week_start + timedelta(days=7)
    ).all()
    week_sums = [0] * 7
    week_counts = [0] * 7
    for e in week_entries:
        ed = _to_date(e.entry_date)
        if ed is None:
            continue
        idx = ed.weekday()
        week_sums[idx] += e.mood_rating
        week_counts[idx] += 1

    weekly_trend = [
        round(week_sums[i] / week_counts[i], 1) if week_counts[i] else None
        for i in range(7)
    ]

    last7 = []
    for delta in range(6, -1, -1):
        d = (today - timedelta(days=delta)).date()
        day_vals = [e.mood_rating for e in entries if _to_date(e.entry_date) == d]
        last7.append(round(sum(day_vals) / len(day_vals), 1) if day_vals else None)

    #  STREAK CALCULATION (FIXED)
    # -------------------------------------
    all_entries = MoodEntry.query.filter_by(user_id=user_id).all()

    # Normalize and group by date (ignore duplicates)
    cleaned_dates = { _to_date(e.entry_date) for e in all_entries if _to_date(e.entry_date) }

    # Remove None and sort
    entry_dates = sorted(d for d in cleaned_dates if d is not None)

    current_streak = 0
    longest_streak = 0

    if entry_dates:
        # Longest streak
        streak = 1
        for i in range(1, len(entry_dates)):
            if entry_dates[i] == entry_dates[i-1] + timedelta(days=1):
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

        # Current streak
        today_date = datetime.utcnow().date()  # <<< IMPORTANT FIX
        if entry_dates[-1] == today_date:
            current_streak = 1
            i = len(entry_dates) - 1
            while i > 0 and entry_dates[i] == entry_dates[i-1] + timedelta(days=1):
                current_streak += 1
                i -= 1
        elif entry_dates[-1] == today_date - timedelta(days=1):
            current_streak = 1
            i = len(entry_dates) - 1
            while i > 0 and entry_dates[i] == entry_dates[i-1] + timedelta(days=1):
                current_streak += 1
                i -= 1
        else:
            current_streak = 0

    #  BADGE LOGIC

    badges = []

    # Streak badges
    streak_milestones = [1, 3, 7, 14, 30]
    for m in streak_milestones:
        if current_streak >= m:
            if m == 1:
                badges.append("🥇 1-Day Streak")
            elif m == 3:
                badges.append("🥈 3-Day Streak")
            elif m == 7:
                badges.append("🔥 7-Day Streak")
            elif m == 14:
                badges.append("✨ 14-Day Streak")
            elif m == 30:
                badges.append("🌟 30-Day Streak")

    # Total entry count badges
    entry_milestones = [10, 25, 50, 100]
    for m in entry_milestones:
        if total_entries >= m:
            badges.append(f"📘 {m} Entries")

    # Sort badges
    badges.sort()


    # --- AUTO DAILY REMINDER FOR DASHBOARD ---
    today_date = datetime.utcnow().date()
    has_logged_today = any(_to_date(e.entry_date) == today_date for e in all_entries)




    reminder_banner = None
    if not has_logged_today:
        reminder_banner = "You haven't logged your mood today"

    return render_template(
        'mood_journal/dashboard.html',
        calendar_dates=calendar_dates,
        current_month=date(year, month, 1).strftime('%B %Y'),
        average_mood=average_mood,
        total_entries=total_entries,
        mood_distribution=mood_distribution,
        weekly_trend=weekly_trend,
        last7_trend=last7,
        month=month,
        year=year,
        summary_days=summary_days,
        summary_day_word=summary_day_word,
        summary_label=summary_label,
        summary_message=summary_message,
        current_streak=current_streak,
        longest_streak=longest_streak,
        badges=badges,
        reminder_banner=reminder_banner
    )



@app.route('/account', methods=['GET', 'POST'])
def account():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.get(session.get('user_id'))
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
            current = request.form.get('current_password')
            new = request.form.get('new_password')
            confirm = request.form.get('confirm_password')

            if not user.check_password(current):
                flash('Current password is incorrect', 'error')
                return redirect(url_for('account'))

            if not new or new != confirm:
                flash('New passwords do not match or are empty', 'error')
                return redirect(url_for('account'))

            user.set_password(new)
            db.session.commit()
            flash('Password updated successfully', 'success')
            return redirect(url_for('account'))

        if action == 'delete_account':
            MoodEntry.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            session.clear()
            flash('Account deleted successfully', 'success')
            return redirect(url_for('login'))

    return render_template('mood_journal/account.html', user=user)


@app.route('/check-password', methods=['POST'])
def check_password():
    if not session.get('logged_in'):
        return {'correct': False}

    user = User.query.get(session.get('user_id'))
    if not user:
        return {'correct': False}

    data = request.get_json()
    password = data.get('password', '')

    correct = user.check_password(password)
    return {'correct': correct}


@app.route('/weekly-summaries')
def weekly_summaries():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    from collections import defaultdict

    user_id = session.get('user_id')

    entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.entry_date).all()

    weeks = defaultdict(list)
    for e in entries:
        d = _to_date(e.entry_date)
        if d is None:
            # skip entries with unparseable dates
            continue
        week_start = d - timedelta(days=d.weekday())
        weeks[week_start].append(e)

    summaries = []
    for week_start in sorted(weeks.keys(), reverse=True):
        week_entries = weeks[week_start]
        # Normalize entry_date on the entries so templates can safely call .strftime
        _normalize_entries(week_entries)
        total = len(week_entries)
        avg = round(sum(e.mood_rating for e in week_entries) / total, 1) if total else None

        highest = max(week_entries, key=lambda x: x.mood_rating) if total else None
        lowest = min(week_entries, key=lambda x: x.mood_rating) if total else None

        summaries.append({
            'week_start': week_start,
            'week_end': week_start + timedelta(days=6),
            'total': total,
            'average': avg,
            'highest': highest,
            'lowest': lowest,
            'entries': week_entries,
        })

    return render_template('mood_journal/weekly_summaries.html', summaries=summaries)


@app.route("/mood-journal", methods=["GET", "POST"])
def mood_journal():
    from datetime import datetime

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to create mood entries', 'error')
        return redirect(url_for('login'))

    if request.method == "POST":
        start_time = session.get('entry_start_time')
        time_spent = 0
        if start_time:
            time_spent = int((datetime.utcnow() - datetime.fromisoformat(start_time)).total_seconds())
            session.pop('entry_start_time', None)

        title = request.form.get("title")
        date_str = request.form.get("date")
        rating = int(request.form.get("mood_rating", 5))
        notes = request.form.get("notes")

        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Generate unique filename to prevent conflicts
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                # Store relative path for database
                image_path = os.path.join('uploads', unique_filename)
            elif file and file.filename != '':
                flash('Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, or WEBP).', 'error')

        # Convert date string to Python date
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()

        if title:
            mood = title.strip()
        elif rating <= 2:
            mood = "Terrible"
        elif rating <= 4:
            mood = "Bad"
        elif rating == 5:
            mood = "Neutral"
        elif rating <= 7:
            mood = "Good"
        elif rating <= 9:
            mood = "Excellent"
        else:
            mood = "Amazing"

        new_entry = MoodEntry(
            user_id=user_id,
            entry_date=entry_date,
            mood_rating=rating,
            mood_label=mood,
            notes=notes,
            time_spent_seconds=time_spent,
            image_path=image_path
        )

        db.session.add(new_entry)
        db.session.commit()
        return redirect("/mood-journal")

    session['entry_start_time'] = datetime.utcnow().isoformat()

    entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.timestamp.desc()).all()
    _normalize_entries(entries)
    return render_template("mood_journal/index.html", entries=entries)


def seed_test_entries():
    from datetime import datetime, timedelta
    from models import MoodEntry

    if MoodEntry.query.count() == 0:
        print(" Implementing test mood entries...")

        today = datetime.utcnow().date()

        sample_entries = [

            MoodEntry(user_id=1, entry_date=today - timedelta(days=0), mood_rating=8, mood_label="Happy", notes="Had a great day with friends!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=1), mood_rating=4, mood_label="Tired", notes="Stayed up late finishing hw"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=2), mood_rating=6, mood_label="Chill", notes="Walked and coffee shop visit"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=3), mood_rating=2, mood_label="Overwhelmed", notes="Too many assignments this week"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=4), mood_rating=9, mood_label="Excited", notes="Day was great today!!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=5), mood_rating=3, mood_label="Unmotivated", notes="Felt sluggish all day"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=6), mood_rating=7, mood_label="Productive", notes="Finally cleaned the apartment"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=7), mood_rating=5, mood_label="Neutral", notes="Average day, just went with the flow"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=8), mood_rating=10, mood_label="Euphoric", notes="Got good news!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=9), mood_rating=1, mood_label="Exhausted", notes="Midterm season😵‍💫"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=10), mood_rating=4, mood_label="Stressed", notes="Cramming for the first exam"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=11), mood_rating=7, mood_label="Content", notes="Nice dinner with friends"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=12), mood_rating=8, mood_label="Inspired", notes="Had a really interesting lecture today"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=13), mood_rating=5, mood_label="Bored", notes="Raining all day, stuck inside"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=14), mood_rating=2, mood_label="Sad", notes="Homesick today 😔"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=15), mood_rating=6, mood_label="Steady", notes="Got into a good flow with coding project"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=16), mood_rating=9, mood_label="Accomplished", notes="Finished the group presentation early!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=17), mood_rating=3, mood_label="Groggy", notes="8am classes are a struggle"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=18), mood_rating=5, mood_label="Distracted", notes="Couldn't focus on reading at all"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=19), mood_rating=8, mood_label="Refreshed", notes="Slept for 10 hours straight"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=20), mood_rating=7, mood_label="Hopeful", notes="Applied to a few internships"),

        ]

        db.session.add_all(sample_entries)
        db.session.commit()
        print("Seeded 10 test mood entries for dashboards/calendars/tests.")
    else:
        print("The entries already exist — skipping seed.")


def init_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    with app.app_context():
        init_db()
        seed_test_entries()
    app.run(debug=True)
