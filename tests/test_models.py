from datetime import date
from models import MoodEntry
from extensions import db


def test_mood_entry_model_creation(app):
    """Test that a MoodEntry object can be created and stored."""
    with app.app_context():
        db.session.query(MoodEntry).delete()  # clear old data

        entry = MoodEntry(
            user_id=1,
            entry_date=date(2025, 10, 23),
            mood_rating=9,
            mood_label="Happy",
            notes="Everything went well today!"
        )
        db.session.add(entry)
        db.session.commit()

        saved = MoodEntry.query.first()
        assert saved is not None
        assert saved.mood_label == "Happy"
        assert saved.mood_rating == 9
        assert saved.notes == "Everything went well today!"


def test_mood_entry_no_duplicates(app):
    """Ensure multiple MoodEntry instances can coexist independently."""
    with app.app_context():
        db.session.query(MoodEntry).delete()

        e1 = MoodEntry(
            user_id=1,
            entry_date=date(2025, 10, 22),
            mood_rating=5,
            mood_label="Neutral",
            notes="Calm day."
        )
        e2 = MoodEntry(
            user_id=2,
            entry_date=date(2025, 10, 23),
            mood_rating=7,
            mood_label="Good",
            notes="Productive day."
        )
        db.session.add_all([e1, e2])
        db.session.commit()

        all_entries = MoodEntry.query.all()
        assert len(all_entries) == 2
        assert all_entries[0].mood_label in ["Neutral", "Good"]
        assert all_entries[1].mood_label in ["Neutral", "Good"]
