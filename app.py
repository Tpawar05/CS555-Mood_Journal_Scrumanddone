from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import os
import csv
import io
from extensions import db
from datetime import datetime, date, timedelta
import calendar




app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models import MoodEntry, User  


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if user exists in database
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) :
            session['logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('home'))

        elif user and str(user.pin) == password:
            session['logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash("Password/PIN does not match", 'error')
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

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))

        # Create new user
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
    return render_template('home/index.html', page_id='home')


@app.route('/profile')
def profile():
    """Display user's personal information"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Get the current user from the database
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your profile', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    # Get user statistics
    total_entries = MoodEntry.query.filter_by(user_id=user_id).count()
    recent_entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.timestamp.desc()).limit(5).all()
    
    return render_template('home/profile.html', user=user, total_entries=total_entries, recent_entries=recent_entries)


@app.route('/logs')
def logs():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Only show entries for the logged-in user
    user_id = session.get('user_id')
    if user_id:
        entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.timestamp.desc()).all()
    else:
        entries = []
    
    return render_template('mood_journal/logs.html', entries=entries, page_id='home')


# DELETE ENTRY ROUTE
@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    entry = MoodEntry.query.get_or_404(entry_id)
    
    # Ensure user can only delete their own entries
    if entry.user_id != user_id:
        flash('You can only delete your own entries', 'error')
        return redirect(url_for('logs'))
    
    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted successfully!')
    return redirect(url_for('logs'))


# EDIT ENTRY ROUTE
@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    entry = MoodEntry.query.get_or_404(entry_id)
    
    # Ensure user can only edit their own entries
    if entry.user_id != user_id:
        flash('You can only edit your own entries', 'error')
        return redirect(url_for('logs'))

    if request.method == 'POST':
        from datetime import datetime

        # Update editable fields
        entry.mood_label = request.form.get('mood_label')
        
        date_str = request.form.get('entry_date')
        if date_str:
            entry.entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        entry.mood_rating = int(request.form.get('mood_rating', 5))
        entry.notes = request.form.get('notes')

        db.session.commit()
        flash('Entry updated successfully!')
        return redirect(url_for('logs'))

    return render_template('mood_journal/edit.html', entry=entry)

# Exporting single entry to CSV

@app.route('/export/<int:entry_id>')
def export_single_entry(entry_id):
    entry = MoodEntry.query.get_or_404(entry_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Entry ID", "Date", "Mood Label", "Rating", 
        "Notes", "Time Spent (sec)", "Created At"
    ])

    # Single row
    writer.writerow([
        entry.id,
        entry.entry_date.strftime("%Y-%m-%d"),
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

# Exporting all entries to CSV
@app.route('/export-all')
def export_all_entries():
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
            entry.entry_date.strftime("%Y-%m-%d"),
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



#Export entries given a date range
@app.route('/export-range')
def export_range():
    start = request.args.get('start_date')
    end = request.args.get('end_date')

    # Validate: must have both dates
    if not start or not end:
        flash("Please choose both start and end dates.", "error")
        return redirect(url_for('logs'))

    #Convert date strings
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for('logs'))

    # Query entries in range
    entries = MoodEntry.query.filter(
        MoodEntry.entry_date >= start_date,
        MoodEntry.entry_date <= end_date
    ).order_by(MoodEntry.entry_date.asc()).all()

    # Prepare CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Entry ID", "Date", "Mood Label", "Rating",
        "Notes", "Time Spent (sec)", "Created At"
    ])

    for entry in entries:
        writer.writerow([
            entry.id,
            entry.entry_date.strftime("%Y-%m-%d"),
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

    # allow optional month/year via query params
    today = datetime.now()
    try:
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))
    except (TypeError, ValueError):
        year = today.year
        month = today.month

    # calendar matrix for the requested month
    cal = calendar.monthcalendar(year, month)
    calendar_dates = []

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.entry_date >= start_date,
        MoodEntry.entry_date < end_date
    ).order_by(MoodEntry.entry_date).all()

    mood_lookup = {entry.entry_date: entry.mood_rating for entry in entries}

    for week in cal:
        row = []
        for d in week:
            if d == 0:
                row.append((None, None))
            else:
                cell_date = date(year, month, d)
                row.append((cell_date, mood_lookup.get(cell_date)))
        calendar_dates.append(row)

    total_entries = len(entries)
    average_mood = sum(e.mood_rating for e in entries) / total_entries if total_entries > 0 else 0

    # bucket function: map raw rating (1-10) to 1-5
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

    mood_distribution = [0] * 5
    for e in entries:
        mood_distribution[bucket(e.mood_rating) - 1] += 1

    # weekly trend for current week (Mon..Sun)
    week_start = (today - timedelta(days=today.weekday())).date()
    week_entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.entry_date >= week_start,
        MoodEntry.entry_date < week_start + timedelta(days=7)
    ).all()
    week_sums = [0] * 7
    week_counts = [0] * 7
    for e in week_entries:
        idx = e.entry_date.weekday()
        week_sums[idx] += e.mood_rating
        week_counts[idx] += 1
    weekly_trend = [round(week_sums[i] / week_counts[i], 1) if week_counts[i] else None for i in range(7)]

    # last 7 days trend
    last7 = []
    for delta in range(6, -1, -1):
        d = (today - timedelta(days=delta)).date()
        day_vals = [e.mood_rating for e in entries if e.entry_date == d]
        last7.append(round(sum(day_vals) / len(day_vals), 1) if day_vals else None)

    return render_template('mood_journal/dashboard.html',
                           calendar_dates=calendar_dates,
                           current_month=date(year, month, 1).strftime('%B %Y'),
                           average_mood=average_mood,
                           total_entries=total_entries,
                           mood_distribution=mood_distribution,
                           weekly_trend=weekly_trend,
                           last7_trend=last7)


@app.route('/account', methods=['GET', 'POST'])
def account():
    # Account settings: change password, delete account
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.get(session.get('user_id'))
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')

        # Change password
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

        # Delete account
        if action == 'delete_account':
            # Remove user entries first to satisfy FK constraints
            MoodEntry.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            session.clear()
            flash('Account deleted successfully', 'success')
            return redirect(url_for('login'))

    return render_template('mood_journal/account.html', user=user)


@app.route('/check-password', methods=['POST'])
def check_password():
    """Endpoint to validate current password in real-time"""
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

    # Compute weekly aggregates for the logged-in user
    user_id = session.get('user_id')
    from collections import defaultdict

    # Get all entries for the user ordered by date
    entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.entry_date).all()

    # Group entries by week start (Monday)
    weeks = defaultdict(list)
    for e in entries:
        d = e.entry_date
        # ensure d is a date object
        if not isinstance(d, (date,)):
            d = d.date()
        week_start = d - timedelta(days=d.weekday())
        weeks[week_start].append(e)

    # Build summary list sorted by descending week_start (most recent first)
    summaries = []
    for week_start in sorted(weeks.keys(), reverse=True):
        week_entries = weeks[week_start]
        total = len(week_entries)
        avg = round(sum(e.mood_rating for e in week_entries) / total, 1) if total else None

        # find highest and lowest mood entries (sample notable entries)
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

    # If no entries, still show empty list
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
        # Calculate time spent
        start_time = session.get('entry_start_time')
        time_spent = 0
        if start_time:
            time_spent = int((datetime.utcnow() - datetime.fromisoformat(start_time)).total_seconds())
            session.pop('entry_start_time', None)  # Clear the start time

        # Grab form data
        title = request.form.get("title")  # from the HTML form
        date_str = request.form.get("date")
        rating = int(request.form.get("mood_rating", 5))
        notes = request.form.get("notes")

        # Convert date string to Python date
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()

        # If title provided, use it as label; else derive label from rating
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

        # Create and save new entry
        new_entry = MoodEntry(
            user_id=user_id,
            entry_date=entry_date,
            mood_rating=rating,
            mood_label=mood,
            notes=notes,
            time_spent_seconds=time_spent
        )

        db.session.add(new_entry)
        db.session.commit()
        return redirect("/mood-journal")

    # Set start time when loading the page
    session['entry_start_time'] = datetime.utcnow().isoformat()
    
    # Display entries for the logged-in user only
    entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.timestamp.desc()).all()
    return render_template("mood_journal/index.html", entries=entries)

def seed_test_entries():
    """
    Seed the database with sample mood entries for testing.
    Automatically skipped if entries already exist.
    """

    from datetime import datetime, timedelta
    from models import MoodEntry

    if MoodEntry.query.count() == 0:
        print(" Implementing test mood entries...")

        today = datetime.utcnow().date()

        sample_entries = [
            MoodEntry(user_id=1, entry_date=today, mood_rating=8, mood_label="Happy", notes="Had a great day with friends!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=1), mood_rating=4, mood_label="Tired", notes="Stayed up late finishing hw"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=2), mood_rating=6, mood_label="Chill", notes="Walked and coffee shop visit"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=3), mood_rating=2, mood_label="Overwhelmed", notes="Too many assignments this week"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=5), mood_rating=9, mood_label="Excited", notes="Day was great today!!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=7), mood_rating=3, mood_label="Unmotivated", notes="Felt sluggish all day"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=10), mood_rating=7, mood_label="Productive", notes="Finally cleaned the apartment"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=12), mood_rating=5, mood_label="Neutral", notes="Average day, just went with the flow"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=14), mood_rating=10, mood_label="Euphoric", notes="Got good news!"),
            MoodEntry(user_id=1, entry_date=today - timedelta(days=20), mood_rating=1, mood_label="Exhausted", notes="Midterm season😵‍💫"),
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
        seed_test_entries() #creates entries if none exist 
    app.run(debug=True)
