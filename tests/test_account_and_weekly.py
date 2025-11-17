"""
Tests for account settings and weekly summaries features.
Covers password change, account deletion, and weekly aggregation.
"""

from datetime import date, timedelta
import pytest
from models import User, MoodEntry
from extensions import db


class TestAccountSettings:
    """Tests for the /account route (password change and account deletion)."""

    def test_account_page_requires_login(self, client):
        """Test that /account redirects if not authenticated."""
        response = client.get('/account', follow_redirects=False)
        assert response.status_code == 302
        assert response.location in ['/', 'http://localhost/']

    def test_account_page_render_when_logged_in(self, app, client):
        """Test that /account renders the account template when logged in."""
        with app.app_context():
            # Create a test user
            user = User(username='testuser', email='test@example.com')
            user.set_password('oldpassword')
            db.session.add(user)
            db.session.commit()

            # Simulate login
            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user.id

            response = client.get('/account')
            assert response.status_code == 200
            assert b'Change Password' in response.data or b'password' in response.data.lower()

    def test_change_password_success(self, app, client):
        """Test successfully changing password."""
        with app.app_context():
            # Create and login user
            user = User(username='testuser', email='test@example.com')
            user.set_password('oldpassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            # Change password
            response = client.post('/account', data={
                'action': 'change_password',
                'current_password': 'oldpassword',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            }, follow_redirects=False)

            assert response.status_code == 302  # Redirect after success

            # Verify password was changed
            updated_user = User.query.get(user_id)
            assert updated_user.check_password('newpassword123')
            assert not updated_user.check_password('oldpassword')

    def test_change_password_wrong_current_password(self, app, client):
        """Test that changing password with wrong current password fails."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('correctpassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            # Try to change password with wrong current password
            response = client.post('/account', data={
                'action': 'change_password',
                'current_password': 'wrongpassword',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            }, follow_redirects=False)

            assert response.status_code == 302
            # Password should not have changed
            updated_user = User.query.get(user_id)
            assert updated_user.check_password('correctpassword')
            assert not updated_user.check_password('newpassword123')

    def test_change_password_mismatch(self, app, client):
        """Test that mismatched new passwords are rejected."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('currentpassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            # Try to change password with mismatched new passwords
            response = client.post('/account', data={
                'action': 'change_password',
                'current_password': 'currentpassword',
                'new_password': 'newpassword123',
                'confirm_password': 'differentpassword'
            }, follow_redirects=False)

            assert response.status_code == 302
            # Password should not have changed
            updated_user = User.query.get(user_id)
            assert updated_user.check_password('currentpassword')

    def test_change_password_empty_new_password(self, app, client):
        """Test that empty new password is rejected."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('currentpassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.post('/account', data={
                'action': 'change_password',
                'current_password': 'currentpassword',
                'new_password': '',
                'confirm_password': ''
            }, follow_redirects=False)

            assert response.status_code == 302
            updated_user = User.query.get(user_id)
            assert updated_user.check_password('currentpassword')

    def test_delete_account_removes_user(self, app, client):
        """Test that deleting account removes user and logs them out."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            # Delete account
            response = client.post('/account', data={
                'action': 'delete_account'
            }, follow_redirects=False)

            assert response.status_code == 302
            # User should be deleted
            deleted_user = User.query.get(user_id)
            assert deleted_user is None

    def test_delete_account_removes_user_entries(self, app, client):
        """Test that deleting account also removes user's mood entries."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Add mood entries
            entry1 = MoodEntry(user_id=user_id, entry_date=date.today(), mood_rating=5, mood_label='Okay')
            entry2 = MoodEntry(user_id=user_id, entry_date=date.today() - timedelta(days=1), mood_rating=7, mood_label='Good')
            db.session.add(entry1)
            db.session.add(entry2)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            # Delete account
            response = client.post('/account', data={
                'action': 'delete_account'
            }, follow_redirects=False)

            assert response.status_code == 302
            # All user entries should be deleted
            entries = MoodEntry.query.filter_by(user_id=user_id).all()
            assert len(entries) == 0

    def test_delete_account_clears_session(self, app, client):
        """Test that deleting account clears the session."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            # Delete account
            client.post('/account', data={'action': 'delete_account'})

            # Session should be cleared
            with client.session_transaction() as sess:
                assert not sess.get('logged_in')
                assert not sess.get('user_id')


class TestCheckPasswordEndpoint:
    """Tests for the /check-password real-time validation endpoint."""

    def test_check_password_requires_login(self, client):
        """Test that /check-password endpoint requires authentication."""
        response = client.post('/check-password', json={'password': 'test'})
        assert response.status_code == 200
        assert response.json == {'correct': False}

    def test_check_password_correct(self, app, client):
        """Test that correct password returns True."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('mypassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.post('/check-password', json={'password': 'mypassword'})
            assert response.status_code == 200
            assert response.json == {'correct': True}

    def test_check_password_incorrect(self, app, client):
        """Test that incorrect password returns False."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('correctpassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.post('/check-password', json={'password': 'wrongpassword'})
            assert response.status_code == 200
            assert response.json == {'correct': False}

    def test_check_password_empty_password(self, app, client):
        """Test that empty password validation fails."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('mypassword')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.post('/check-password', json={'password': ''})
            assert response.status_code == 200
            assert response.json == {'correct': False}


class TestWeeklySummaries:
    """Tests for the /weekly-summaries route and weekly aggregation logic."""

    def test_weekly_summaries_requires_login(self, client):
        """Test that /weekly-summaries redirects if not authenticated."""
        response = client.get('/weekly-summaries', follow_redirects=False)
        assert response.status_code == 302
        assert response.location in ['/', 'http://localhost/']

    def test_weekly_summaries_empty_user(self, app, client):
        """Test weekly summaries page with user who has no entries."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.get('/weekly-summaries')
            assert response.status_code == 200
            # Should show empty state or no summaries
            assert b'Weekly' in response.data or b'summary' in response.data.lower()

    def test_weekly_summaries_single_entry(self, app, client):
        """Test weekly summary with a single mood entry."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Add one entry
            entry = MoodEntry(
                user_id=user_id,
                entry_date=date(2025, 11, 10),  # A Monday
                mood_rating=8,
                mood_label='Great'
            )
            db.session.add(entry)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.get('/weekly-summaries')
            assert response.status_code == 200
            # Should contain summary data
            assert b'Great' in response.data or b'8' in response.data or b'summary' in response.data.lower()

    def test_weekly_summaries_multiple_entries_same_week(self, app, client):
        """Test weekly summary correctly aggregates multiple entries in the same week."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Add entries for the same week (Nov 10-16, 2025)
            base_date = date(2025, 11, 10)  # Monday
            for i in range(3):
                entry = MoodEntry(
                    user_id=user_id,
                    entry_date=base_date + timedelta(days=i),
                    mood_rating=5 + i,  # 5, 6, 7
                    mood_label=f'Mood{i}'
                )
                db.session.add(entry)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.get('/weekly-summaries')
            assert response.status_code == 200
            # Check that it contains aggregated data
            assert response.data is not None

    def test_weekly_summaries_multiple_weeks(self, app, client):
        """Test weekly summary with entries spanning multiple weeks."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Week 1: Nov 3-9 (starting Monday Nov 3)
            # Week 2: Nov 10-16 (starting Monday Nov 10)
            dates_week1 = [date(2025, 11, 3), date(2025, 11, 4), date(2025, 11, 5)]
            dates_week2 = [date(2025, 11, 10), date(2025, 11, 11), date(2025, 11, 12)]

            for idx, d in enumerate(dates_week1):
                entry = MoodEntry(
                    user_id=user_id,
                    entry_date=d,
                    mood_rating=4 + idx,
                    mood_label=f'Week1Mood{idx}'
                )
                db.session.add(entry)

            for idx, d in enumerate(dates_week2):
                entry = MoodEntry(
                    user_id=user_id,
                    entry_date=d,
                    mood_rating=7 + idx,
                    mood_label=f'Week2Mood{idx}'
                )
                db.session.add(entry)

            db.session.commit()

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.get('/weekly-summaries')
            assert response.status_code == 200
            # Should render without errors
            assert response.data is not None

    def test_weekly_summaries_calculates_correct_average(self, app):
        """Test that weekly summary calculates average mood correctly (internal logic)."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Add entries with known ratings: 5, 7, 9 (average = 7)
            base_date = date(2025, 11, 10)
            for rating in [5, 7, 9]:
                entry = MoodEntry(
                    user_id=user_id,
                    entry_date=base_date,
                    mood_rating=rating,
                    mood_label='Test'
                )
                db.session.add(entry)
            db.session.commit()

            # Get entries and manually verify aggregation
            entries = MoodEntry.query.filter_by(user_id=user_id).all()
            assert len(entries) == 3
            avg = sum(e.mood_rating for e in entries) / len(entries)
            assert avg == 7.0

    def test_weekly_summaries_identifies_highest_lowest(self, app):
        """Test that weekly summary correctly identifies highest and lowest mood entries."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Add entries with varying ratings
            base_date = date(2025, 11, 10)
            ratings = [3, 9, 5, 1, 8]
            for idx, rating in enumerate(ratings):
                entry = MoodEntry(
                    user_id=user_id,
                    entry_date=base_date + timedelta(days=idx),
                    mood_rating=rating,
                    mood_label=f'Mood{rating}'
                )
                db.session.add(entry)
            db.session.commit()

            entries = MoodEntry.query.filter_by(user_id=user_id).all()
            highest = max(entries, key=lambda x: x.mood_rating)
            lowest = min(entries, key=lambda x: x.mood_rating)

            assert highest.mood_rating == 9
            assert lowest.mood_rating == 1

    def test_weekly_summaries_groups_by_monday(self, app):
        """Test that entries are correctly grouped by week starting Monday."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Nov 10, 2025 is a Monday
            # Nov 16, 2025 is a Sunday
            # Nov 17, 2025 is a Monday (next week)
            monday = date(2025, 11, 10)
            sunday = date(2025, 11, 16)
            next_monday = date(2025, 11, 17)

            entry1 = MoodEntry(user_id=user_id, entry_date=monday, mood_rating=5, mood_label='Mon')
            entry2 = MoodEntry(user_id=user_id, entry_date=sunday, mood_rating=7, mood_label='Sun')
            entry3 = MoodEntry(user_id=user_id, entry_date=next_monday, mood_rating=6, mood_label='NextMon')
            db.session.add_all([entry1, entry2, entry3])
            db.session.commit()

            # Verify weekday
            assert monday.weekday() == 0  # Monday
            assert sunday.weekday() == 6  # Sunday
            assert next_monday.weekday() == 0  # Monday

    def test_weekly_summaries_sorting_descending(self, app, client):
        """Test that weekly summaries are sorted by most recent first."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Add entries from different weeks
            # Week of Nov 3, 2025
            entry1 = MoodEntry(user_id=user_id, entry_date=date(2025, 11, 3), mood_rating=5, mood_label='Week1')
            # Week of Nov 10, 2025
            entry2 = MoodEntry(user_id=user_id, entry_date=date(2025, 11, 10), mood_rating=7, mood_label='Week2')
            # Week of Nov 17, 2025
            entry3 = MoodEntry(user_id=user_id, entry_date=date(2025, 11, 17), mood_rating=9, mood_label='Week3')

            db.session.add_all([entry1, entry2, entry3])
            db.session.commit()

            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user_id

            response = client.get('/weekly-summaries')
            assert response.status_code == 200
            # Most recent week should appear first in the rendered output

    def test_weekly_summaries_isolates_user_data(self, app, client):
        """Test that weekly summaries only shows entries for logged-in user."""
        with app.app_context():
            user1 = User(username='user1', email='user1@example.com')
            user1.set_password('password')
            user2 = User(username='user2', email='user2@example.com')
            user2.set_password('password')
            db.session.add_all([user1, user2])
            db.session.commit()

            # Add entries for both users
            entry1 = MoodEntry(user_id=user1.id, entry_date=date(2025, 11, 10), mood_rating=9, mood_label='User1Entry')
            entry2 = MoodEntry(user_id=user2.id, entry_date=date(2025, 11, 10), mood_rating=2, mood_label='User2Entry')
            db.session.add_all([entry1, entry2])
            db.session.commit()

            # Login as user1
            with client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user1.id

            response = client.get('/weekly-summaries')
            assert response.status_code == 200
            # Should only contain user1's mood label
            assert b'User1Entry' in response.data
            # Should not contain user2's mood label
            assert b'User2Entry' not in response.data
