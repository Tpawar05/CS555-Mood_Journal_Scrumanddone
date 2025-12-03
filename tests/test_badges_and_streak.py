import pytest
from datetime import date, timedelta
from models import MoodEntry, User
from extensions import db

def login(client, username="testuser", password="testpass"):
    return client.post("/", data=dict(
        username=username,
        password=password
    ), follow_redirects=True)


def create_user():
    user = User(username="testuser", email="t@example.com")
    user.set_password("testpass")
    db.session.add(user)
    db.session.commit()
    return user


def add_entries(user_id, dates):
    """Helper to insert MoodEntry rows with a fixed rating."""
    for d in dates:
        entry = MoodEntry(
            user_id=user_id,
            entry_date=d,
            mood_rating=7,         # good mood so bucket doesn't matter
            mood_label="Good"
        )
        db.session.add(entry)
    db.session.commit()


def test_streak_0_when_gap(client, app):
    """If the most recent entry is NOT today or yesterday → streak = 0."""
    with app.app_context():
        user = create_user()
        login(client)

        # No entry today or yesterday
        dates = [date.today() - timedelta(days=5)]
        add_entries(user.id, dates)

        res = client.get("/dashboard")
        assert b"Your Streak" in res.data
        assert b"0 days" in res.data


def test_streak_3_days_and_badges(client, app):
    """Three consecutive days → streak = 3 and 1-day + 3-day badges appear."""
    with app.app_context():
        user = create_user()
        login(client)

        # Create a 3-day streak ending yesterday
        today = date.today()
        dates = [today - timedelta(days=1),
                 today - timedelta(days=2),
                 today - timedelta(days=3)]
        add_entries(user.id, dates)

        res = client.get("/dashboard")
        
        # Streak value
        assert b"3 days" in res.data

        # Check streak badges rendered
        assert b"1-Day Streak" in res.data
        assert b"3-Day Streak" in res.data


def test_streak_7_day_badge(client, app):
    """Seven-day streak gives the 7-day badge."""
    with app.app_context():
        user = create_user()
        login(client)

        today = date.today()
        dates = [(today - timedelta(days=i)) for i in range(1, 8)]  # 7 days
        add_entries(user.id, dates)

        res = client.get("/dashboard")

        # Streak computed correctly
        assert b"7 days" in res.data

        # Has the 7-day badge
        assert b"7-Day Streak" in res.data


def test_entry_count_badges(client, app):
    """10+ entries gives the '10 Entries' badge."""
    with app.app_context():
        user = create_user()
        login(client)

        today = date.today()
        dates = [(today + timedelta(days=i)) for i in range(12)]  # 12 entries
        add_entries(user.id, dates)

        res = client.get("/dashboard")

        # Badge should appear
        assert b"10 Entries" in res.data
