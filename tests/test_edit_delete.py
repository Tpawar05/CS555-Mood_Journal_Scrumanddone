# tests/test_edit_delete.py
import pytest
from app import app, db
from models import MoodEntry
from datetime import datetime

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Seed a single test entry
            entry = MoodEntry(
                user_id=1,
                entry_date=datetime.utcnow().date(),
                mood_rating=5,
                mood_label="Neutral",
                notes="Test entry"
            )
            db.session.add(entry)
            db.session.commit()
        yield client


def test_edit_entry(client):
    """Test editing an existing entry"""
    with app.app_context():
        entry = MoodEntry.query.first()
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


def test_delete_entry(client):
    """Test deleting an entry"""
    with app.app_context():
        entry = MoodEntry.query.first()
        assert entry is not None

    response = client.post(f'/delete/{entry.id}', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        deleted = MoodEntry.query.get(entry.id)
        assert deleted is None
