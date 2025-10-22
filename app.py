from flask import Flask, render_template, request, redirect, url_for, session
import os
from extensions import db
from models import MoodEntry  # noqa: E402

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ---------- ROUTES ----------

# Login page (root)
@app.route('/')
def home():
    return render_template('login.html', page_id='home')


# Handle login form submission
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Simple authentication check
    if username == 'username' and password == 'password':
        session['user'] = username  # store session info
        return redirect('/home/index.html')
    else:
        return render_template('login.html', error='Invalid username or password')


# Home page (after login)
@app.route('/home/index.html')
def home_index():
    # Optional: restrict access if not logged in
    if 'user' not in session:
        return redirect('/')
    return render_template('home/index.html')


# Mood Journal Page
@app.route('/mood-journal', methods=['GET', 'POST'])
def mood_journal():
    # Require login
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        mood = request.form.get('mood', '').strip()
        notes = request.form.get('notes', '').strip()

        if mood:
            entry = MoodEntry(mood=mood, notes=notes or None)
            db.session.add(entry)
            db.session.commit()

        return redirect(url_for('mood_journal'))

    entries = MoodEntry.query.order_by(MoodEntry.created_at.desc()).all()
    return render_template(
        'apps/mood_journal/index.html',
        page_id='mood-journal',
        entries=entries
    )


# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# ---------- DATABASE SETUP ----------
def init_db():
    with app.app_context():
        db.create_all()


# ---------- RUN APP ----------
if __name__ == '__main__':
    if not os.path.exists('app.db'):
        init_db()
    app.run(debug=True)

