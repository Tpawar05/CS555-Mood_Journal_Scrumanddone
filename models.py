from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# --- USERS TABLE ---
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    pin = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


# Relationships
    mood_entries = db.relationship('MoodEntry', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)


# --- MOOD ENTRIES TABLE ---
class MoodEntry(db.Model):
    __tablename__ = 'mood_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_date = db.Column(db.Integer)
    mood_rating = db.Column(db.Integer, nullable=False)
    mood_label = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    viewed_at = db.Column(db.DateTime)
    tags = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.now())
    time_spent_seconds = db.Column(db.Integer)
