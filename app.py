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

@app.route('/mood-journal', methods=['GET', 'POST'])
def mood_journal():
    if request.method == 'POST':
        mood = request.form.get('mood', '').strip()
        notes = request.form.get('notes', '').strip()

        if mood:
            entry = MoodEntry(mood=mood, notes=notes or None)
            db.session.add(entry)
            db.session.commit()

        return redirect(url_for('mood_journal'))


    entries = MoodEntry.query.order_by(MoodEntry.created_at.desc()).all()
    return render_template('apps/mood_journal/index.html', page_id='mood-journal', entries=entries)

@app.route('/logs', methods=['GET'])
def logs():
    entries = MoodEntry.query.order_by(MoodEntry.created_at.desc()).all()
    return render_template('apps/mood_journal/logs.html', page_id='mood-journal', entries=entries)

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('app.db'):
        init_db()
    app.run(debug=True)
