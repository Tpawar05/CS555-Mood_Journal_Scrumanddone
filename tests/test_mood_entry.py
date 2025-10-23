import pytest
from models import MoodEntry
from datetime import date
from extensions import db


def test_add_entry_persists_no_duplicates(client):
    """Confirm that entries are stored correctly and not duplicated"""
    # client fixture already has app context from conftest.py
    
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


def test_entry_fields_integrity(client):
    """Check that all required fields are saved properly"""
    
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