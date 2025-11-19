# seed.py
from models import User, MoodEntry
from app import app, db
from datetime import datetime, timedelta
import random


# Create some example users
users = [
    User(username="Emma", email="emma@example.com"),
    User(username="Koen", email="koen@example.com"),
    User(username="Rachel", email="rachel@example.com"),
    User(username="Tanmay", email="tanmay@example.com"),
]

# Set passwords using the hashing method (REQUIRED for login to work)
users[0].set_password("emma")
users[1].set_password("koen")
users[2].set_password("rachel")
users[3].set_password("tanmay")

# Example moods
moods = [
    (1, "Terrible"), (3, "Bad"), (5, "Neutral"),
    (7, "Good"), (9, "Excellent"), (10, "Amazing")
]

# Seed database
with app.app_context():
    db.drop_all()   
    db.create_all()
    
    # Add users first and commit to get their IDs
    db.session.add_all(users)
    db.session.commit()
    
    # Now generate dummy mood entries with user IDs (users must be committed first)
    entries = []
    for user in users:
        for i in range(7):  
            rating, label = random.choice(moods)
            entry = MoodEntry(
                user_id=user.id,  # Use user_id instead of user=user
                entry_date=datetime.utcnow().date() - timedelta(days=i),
                mood_rating=rating,
                mood_label=label,
                notes=f"Day {i+1}: Feeling {label.lower()} today.",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            entries.append(entry)
    
    # Add entries and commit
    db.session.add_all(entries)
    db.session.commit()
    print("\n\n✅ Dummy data added successfully!")
    print(f"Created {len(users)} users:")
    for user in users:
        print(f"  - Username: {user.username}, Password: (same as username)")
