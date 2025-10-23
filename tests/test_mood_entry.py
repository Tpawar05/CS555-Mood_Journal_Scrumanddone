import pytest
from app import app, db
from models import MoodEntry
from datetime import date

@pytest.fixture
def test_client():
    """Create a fresh test client and database for each test"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # clear any lingering data safely
            db.session.query(MoodEntry).delete()
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def test_add_entry_persists_no_duplicates(test_client):
    """Confirm that entries are stored correctly and not duplicated"""
    with app.app_context():
        # Add one entry
        entry1 = MoodEntry(
            user_id=1,
            mood_label="Happy",
            mood_rating=8,
            notes="Sunny day",
            entry_date=date.today()
        )
        db.session.add(entry1)
        db.session.commit()

        # Add a second entry
        entry2 = MoodEntry(
            user_id=1,
            mood_label="Relaxed",
            mood_rating=7,
            notes="Evening walk",
            entry_date=date.today()
        )
        db.session.add(entry2)
        db.session.commit()

        entries = MoodEntry.query.all()

        # verify entries persist with no missing data
        assert len(entries) == 2
        assert all(e.mood_label and e.entry_date for e in entries)

def test_entry_fields_integrity(test_client):
    """Check that all required fields are saved properly"""
    with app.app_context():
        entry = MoodEntry(
            user_id=1,
            mood_label="Calm",
            mood_rating=6,
            notes="Testing fields",
            entry_date=date.today()
        )
        db.session.add(entry)
        db.session.commit()

        saved = MoodEntry.query.first()
        assert saved.mood_label == "Calm"
        assert saved.mood_rating == 6
        assert saved.notes == "Testing fields"
        assert saved.entry_date == date.today()
