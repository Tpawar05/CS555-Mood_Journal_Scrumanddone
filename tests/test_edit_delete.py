# tests/test_edit_delete.py
import pytest
from app import app, db
from models import MoodEntry, User
from datetime import datetime

@pytest.fixture
def client(app):
    """Create test client with app context"""
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create a test user
            user = User(username="testuser", email="test@example.com")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()
            
            # Seed a single test entry for the user
            entry = MoodEntry(
                user_id=user.id,
                entry_date=datetime.utcnow().date(),
                mood_rating=5,
                mood_label="Neutral",
                notes="Test entry"
            )
            db.session.add(entry)
            db.session.commit()
        yield client


def test_edit_entry(client, app):
    """Test editing an existing entry"""
    # Log in first
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        client.post("/", data={"username": "testuser", "password": "testpass"})
        entry = MoodEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None

    response = client.post(f'/edit/{entry.id}', data={
        'mood_label': 'Updated Mood',
        'entry_date': datetime.utcnow().date().isoformat(),
        'mood_rating': 8,
        'notes': 'Updated test notes'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        updated = MoodEntry.query.get(entry.id)
        assert updated.mood_label == 'Updated Mood'
        assert updated.mood_rating == 8


def test_delete_entry(client, app):
    """Test deleting an entry"""
    # Log in first
    with app.app_context():
        user = User.query.filter_by(username="testuser").first()
        client.post("/", data={"username": "testuser", "password": "testpass"})
        entry = MoodEntry.query.filter_by(user_id=user.id).first()
        assert entry is not None
        entry_id = entry.id

    response = client.post(f'/delete/{entry_id}', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        deleted = MoodEntry.query.get(entry_id)
        assert deleted is None
