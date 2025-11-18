from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
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


@app.route('/logs')
def logs():
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    return render_template('mood_journal/logs.html', entries=entries, page_id='home')


# DELETE ENTRY ROUTE
@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    entry = MoodEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted successfully!')
    return redirect(url_for('logs'))


# EDIT ENTRY ROUTE
@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    entry = MoodEntry.query.get_or_404(entry_id)

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



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
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


@app.route("/mood-journal", methods=["GET", "POST"])
def mood_journal():
    from datetime import datetime

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
            user_id=1,  # placeholder until auth is connected
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
    
    # Display entries
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
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
