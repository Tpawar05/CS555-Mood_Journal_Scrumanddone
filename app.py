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

from models import MoodEntry, User  

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if user exists in database
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))  # 👈 redirect back to '/' route

    return render_template('home/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

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
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('home/register.html')


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
    if not os.path.exists('app.db'):
        init_db()
    app.run(debug=True)