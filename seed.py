# seed.py
from models import User, MoodEntry
from app import app, db
from datetime import datetime, timedelta
import random

# --- Example users ---
users = [
    User(username="Emma", email="emma@example.com", password="emma"),
    User(username="Koen", email="koen@example.com", password="koen"),
    User(username="Rachel", email="rachel@example.com", password="rachel"),
    User(username="Tanmay", email="tanmay@example.com", password="tanmay"),
]

# --- Example moods ---
moods = [
    (1, "Terrible"), (3, "Bad"), (5, "Neutral"),
    (7, "Good"), (9, "Excellent"), (10, "Amazing")
]

# --- Generate dummy mood entries ---
entries = []
for user in users:
    for i in range(7):  # one week of entries per user
        rating, label = random.choice(moods)
        timer_minutes = random.randint(2, 30)  # random reflection time (2–30 min)

        entry = MoodEntry(
            user=user,
            entry_date=datetime.utcnow().date() - timedelta(days=i),
            mood_rating=rating,
            mood_label=label,
            notes=f"Day {i+1}: Feeling {label.lower()} today.",
            timer=timer_minutes, 
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        entries.append(entry)

# --- Seed database ---
with app.app_context():
    db.drop_all()
    db.create_all()
    db.session.add_all(users + entries)
    db.session.commit()
    print("\n\n Dummy data (including timer values) added successfully!")
