import pytest
from models import MoodEntry
from datetime import date, timedelta
from extensions import db


def test_add_entry_persists_no_duplicates(client):
    """Confirm that entries are stored correctly and not duplicated"""


    # Add one entry
    entry1 = MoodEntry(
        user_id=1,
        mood_label="calm",
        mood_rating=8,
        notes="Yoga classes",
        entry_date=date.today()
    )
    db.session.add(entry1)
    db.session.commit()

    # Add a second entry
    entry2 = MoodEntry(
        user_id=2,
        mood_label="Ecstatic",
        mood_rating=10,
        notes="Hang out with friends",
        entry_date=date.today()- timedelta(days=1)
    )
    db.session.add(entry2)
    db.session.commit()

    #add a third entry
    entry3 = MoodEntry(
        user_id=3,
        mood_label="sad",
        mood_rating=9,
        notes="Sunny day",
        entry_date=date.today()+ timedelta(days=1)
    )
    db.session.add(entry3)
    db.session.commit()
    entries = MoodEntry.query.all()

    # verify entries persist with no missing data
    assert len(entries) == 3
    assert all(e.mood_label and e.entry_date for e in entries)


def test_entry_fields_integrity(client):
    """Check that all required fields are saved properly"""

    entry = MoodEntry(
        user_id=4,
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
