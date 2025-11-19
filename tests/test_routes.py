import pytest
from models import MoodEntry, User
from extensions import db


@pytest.mark.usefixtures("client")
class TestMoodJournalRoutes:
    def _create_and_login_user(self, client, app):
        """Helper to create a user and log in"""
        with app.app_context():
            user = User(username="testuser", email="test@example.com")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        
        # Log in
        client.post("/", data={"username": "testuser", "password": "testpass"})
        return user_id

    def test_mood_journal_get_returns_ok(self, client, app):
        """GET /mood-journal should return 200 and render page"""
        self._create_and_login_user(client, app)
        response = client.get("/mood-journal")
        assert response.status_code == 200

    def test_mood_journal_post_creates_entry(self, client, app):
        """POST /mood-journal should create new entry"""
        user_id = self._create_and_login_user(client, app)
        entry_data = {
            "title": "Relaxed",
            "date": "2025-10-23",
            "mood_rating": "8",
            "notes": "Had a peaceful day with tea and reading."
        }
        response = client.post("/mood-journal", data=entry_data, follow_redirects=False)
        assert response.status_code == 302  # Redirect after success

        with app.app_context():
            stored = MoodEntry.query.filter_by(mood_label="Relaxed", user_id=user_id).first()
            assert stored is not None
            assert stored.mood_rating == 8
            assert stored.notes == "Had a peaceful day with tea and reading."

    def test_mood_journal_post_defaults_when_missing_title(self, client, app):
        """If no title is given, mood label should derive from rating"""
        user_id = self._create_and_login_user(client, app)
        entry_data = {
            "title": "",
            "date": "2025-10-23",
            "mood_rating": "3",
            "notes": "Felt tired but okay."
        }
        response = client.post("/mood-journal", data=entry_data, follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            stored = MoodEntry.query.filter_by(mood_label="Bad", user_id=user_id).first()
            assert stored is not None
            assert stored.mood_rating == 3
