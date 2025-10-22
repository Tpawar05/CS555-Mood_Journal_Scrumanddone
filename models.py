from extensions import db
from datetime import datetime

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    rating = db.Column(db.Integer, nullable=False)
    mood = db.Column(db.String(50))
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
