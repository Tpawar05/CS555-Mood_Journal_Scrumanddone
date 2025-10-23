import pytest
from models import MoodEntry


@pytest.mark.usefixtures("client")
class TestMoodJournalRoutes:
    def test_mood_journal_get_returns_ok(self, client):
        """GET /mood-journal should return 200 and render page"""
        response = client.get("/mood-journal")
        assert response.status_code == 200

    def test_mood_journal_post_creates_entry(self, client):
        """POST /mood-journal should create new entry"""
        entry_data = {
            "title": "Relaxed",
            "date": "2025-10-23",
            "mood_rating": "8",
            "notes": "Had a peaceful day with tea and reading."
        }
        response = client.post("/mood-journal", data=entry_data, follow_redirects=False)
        assert response.status_code == 302  # Redirect after success

        stored = MoodEntry.query.filter_by(mood_label="Relaxed").first()
        assert stored is not None
        assert stored.mood_rating == 8
        assert stored.notes == "Had a peaceful day with tea and reading."

    def test_mood_journal_post_defaults_when_missing_title(self, client):
        """If no title is given, mood label should derive from rating"""
        entry_data = {
            "title": "",
            "date": "2025-10-23",
            "mood_rating": "3",
            "notes": "Felt tired but okay."
        }
        response = client.post("/mood-journal", data=entry_data, follow_redirects=False)
        assert response.status_code == 302

        stored = MoodEntry.query.filter_by(mood_label="Bad").first()
        assert stored is not None
        assert stored.mood_rating == 3
