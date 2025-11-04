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

from models import MoodEntry  

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple static credentials for testing
        if username == 'username' and password == 'password':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))  # 👈 redirect back to '/' route

    return render_template('home/login.html')


@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # 👈 ensure redirects to '/'
    return render_template('home/index.html', page_id='home')

@app.route('/logs')
def logs():
    entries =MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    return render_template('mood_journal/logs.html', entries=entries, page_id='home')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Get current month and year
    today = datetime.now()
    year = today.year
    month = today.month
    
    # Calculate calendar dates
    cal = calendar.monthcalendar(year, month)
    calendar_dates = []
    
    # Get all mood entries for the current month (use date objects to match model column type)
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        # first day of next month
        end_date = date(year, month + 1, 1)

    entries = MoodEntry.query.filter(
        MoodEntry.entry_date >= start_date,
        MoodEntry.entry_date < end_date
    ).all()

    # Create mood entry lookup (models.MoodEntry.entry_date is a Date)
    mood_lookup = {entry.entry_date: entry.mood_rating for entry in entries}
    
    # Format calendar data
    for week in cal:
        calendar_week = []
        for day in week:
            if day == 0:
                calendar_week.append((None, None))
            else:
                # avoid shadowing the imported `date` class by using `cell_date`
                cell_date = date(year, month, day)
                mood = mood_lookup.get(cell_date)
                calendar_week.append((cell_date, mood))
        calendar_dates.append(calendar_week)
    
    # Calculate statistics
    total_entries = len(entries)
    average_mood = sum(entry.mood_rating for entry in entries) / total_entries if total_entries > 0 else 0
    
    return render_template('mood_journal/dashboard.html',
                         calendar_dates=calendar_dates,
                         current_month=today.strftime('%B %Y'),
                         average_mood=average_mood,
                         total_entries=total_entries)


@app.route("/mood-journal", methods=["GET", "POST"])
def mood_journal():
    from datetime import datetime

    if request.method == "POST":
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
            notes=notes
        )

        db.session.add(new_entry)
        db.session.commit()
        return redirect("/mood-journal")

    # Display entries
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    return render_template("mood_journal/index.html", entries=entries)


def init_db():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    # ensure instance folder exists and DB initialized at instance/app.db
    db_path = os.path.join(instance_path, 'app.db')
    if not os.path.exists(db_path):
        init_db()
    app.run(debug=True)