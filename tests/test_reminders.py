from datetime import datetime, timedelta
from app import app, db
from models import User, MoodEntry

def setup_user(client):
    """Create and login a test user."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com", pin="1234")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
        return user.id

def login(client):
    return client.post("/", data={"username": "testuser", "password": "testpass"}, follow_redirects=True)

def test_reminder_shows_when_no_entry_today(client):
    user_id = setup_user(client)
    login(client)

    # ensure no entries today
    with app.app_context():
        MoodEntry.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    resp = client.get("/dashboard")
    assert b"You haven't logged your mood today" in resp.data

def test_no_reminder_when_entry_exists_today(client):
    user_id = setup_user(client)
    login(client)

    today = datetime.utcnow().date()

    # add today's entry
    with app.app_context():
        entry = MoodEntry(
            user_id=user_id,
            entry_date=today,
            mood_rating=5,
            mood_label="Neutral"
        )
        db.session.add(entry)
        db.session.commit()

    resp = client.get("/dashboard")
    assert b"You haven't logged your mood today" not in resp.data


def test_homepage_reminder_logic(client):
    user_id = setup_user(client)
    login(client)

    # no entry today → reminder should appear
    with app.app_context():
        MoodEntry.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    resp = client.get("/home")
    assert b"Don\xe2\x80\x99t forget to log your mood today" in resp.data
