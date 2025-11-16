import csv
from io import StringIO
from app import app, db
from models import MoodEntry
from datetime import date

def seed_entries():
    """Ensures entries exist inside the same app context used by routes."""
    MoodEntry.query.delete()
    e1 = MoodEntry(
        user_id=1,
        entry_date=date(2025, 1, 1),
        mood_rating=7,
        mood_label="Good",
        notes="Test note 1",
        time_spent_seconds=45
    )
    e2 = MoodEntry(
        user_id=1,
        entry_date=date(2025, 1, 3),
        mood_rating=4,
        mood_label="Tired",
        notes="Test note 2",
        time_spent_seconds=120
    )
    db.session.add_all([e1, e2])
    db.session.commit()


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_entries()


def test_export_single_entry():
    tester = app.test_client()

    with app.app_context():
        seed_entries()   # ensure entries exist for this request

    response = tester.get('/export/1')
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv"

    reader = list(csv.reader(StringIO(response.data.decode())))
    assert reader[1][2] == "Good"


def test_export_all_entries():
    tester = app.test_client()

    with app.app_context():
        seed_entries()

    response = tester.get("/export-all")
    assert response.status_code == 200

    reader = list(csv.reader(StringIO(response.data.decode())))
    assert len(reader) >= 3   # header + 2 rows


def test_export_range():
    tester = app.test_client()

    with app.app_context():
        seed_entries()

    response = tester.get("/export-range?start_date=2025-01-01&end_date=2025-01-02")
    assert response.status_code == 200

    reader = list(csv.reader(StringIO(response.data.decode())))
    assert len(reader) == 2   # header + 1 row
    assert reader[1][2] == "Good"
