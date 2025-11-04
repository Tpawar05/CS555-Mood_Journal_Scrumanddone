from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from extensions import db

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
            return redirect(url_for('login'))  # redirect back to '/' route

    return render_template('home/login.html')


@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # ensure redirects to '/'
    return render_template('home/index.html', page_id='home')

@app.route('/logs')
def logs():
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    return render_template('mood_journal/logs.html', entries=entries, page_id='home')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/mood-journal", methods=["GET", "POST"])
def mood_journal():
    from datetime import datetime

    if request.method == "POST":
        #  Updated field names to match your HTML
        label = request.form.get("mood_label")  
        date_str = request.form.get("entry_date")  
        rating = int(request.form.get("mood_rating", 5))
        notes = request.form.get("notes")
        timer = request.form.get("timer")

        # Properly convert date from picker
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()

        # Use label if present, else derive from rating
        if label and label.strip():
            mood = label.strip()
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
            timer=timer
        )

        db.session.add(new_entry)
        db.session.commit()
        return redirect("/mood-journal")

    # Display entries
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    from datetime import datetime as _dt
    return render_template("mood_journal/index.html", entries=entries, current_date=_dt.utcnow().date().isoformat())


def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('app.db'):
        init_db()
    app.run(debug=True)
