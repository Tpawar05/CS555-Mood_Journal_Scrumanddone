from flask import Flask, render_template, request, redirect, url_for
import os

from extensions import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models import MoodEntry  # noqa: E402

@app.route('/')
def login():
    return render_template('home/index.html', page_id='home')

@app.route('/home')
def home():
    return render_template('home/index.html', page_id='home')


@app.route('/logs')
def logs():
    return render_template('mood_journal/logs.html', page_id='home')

@app.route("/mood-journal", methods=["GET", "POST"])
def mood_journal():
    from datetime import datetime

    if request.method == "POST":
        title = request.form.get("title")
        date_str = request.form.get("date")
        rating = int(request.form.get("rating", 5))
        notes = request.form.get("notes")

        # Convert date string to Python date
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()

        # Convert numeric rating to mood label
        if rating <= 2:
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
            title=title,
            date=entry_date,
            rating=rating,
            mood=mood,
            notes=notes
        )
        db.session.add(new_entry)
        db.session.commit()
        return redirect("/mood-journal")

    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    return render_template("mood_journal/index.html", entries=entries)

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('app.db'):
        init_db()
    app.run(debug=True)
