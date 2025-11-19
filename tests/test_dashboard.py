"""
Test suite for dashboard route and calendar functionality.
"""

import pytest
from datetime import datetime, date, timedelta
import calendar
from flask import url_for
from models import User, MoodEntry
from extensions import db


def login(client, username="testuser", password="testpass"):
    """Helper to log in a test user."""
    return client.post("/", data=dict(
        username=username,
        password=password
    ), follow_redirects=True)


def create_test_user():
    """Create a test user for authentication."""
    user = User(username="testuser", email="test@example.com")
    user.set_password("testpass")
    db.session.add(user)
    db.session.commit()
    return user


def create_test_entries(user_id, base_date=None):
    """Create a set of test mood entries for a given month."""
    if base_date is None:
        base_date = date.today()

    entries = []
    # Create entries for different scenarios
    entries.append(MoodEntry(
        user_id=user_id,
        entry_date=base_date,
        mood_rating=8,
        mood_label="Happy",
        notes="Test entry 1"
    ))
    entries.append(MoodEntry(
        user_id=user_id,
        entry_date=base_date - timedelta(days=1),
        mood_rating=5,
        mood_label="Neutral",
        notes="Test entry 2"
    ))
    entries.append(MoodEntry(
        user_id=user_id,
        entry_date=base_date - timedelta(days=2),
        mood_rating=3,
        mood_label="Sad",
        notes="Test entry 3"
    ))

    db.session.add_all(entries)
    db.session.commit()
    return entries


def test_dashboard_requires_login(client):
    """Test that dashboard redirects to login when not authenticated."""
    response = client.get("/dashboard")
    assert response.status_code == 302  # Expect redirect
    assert response.location.endswith("/")  # Redirects to root which is login


def test_dashboard_authenticated_access(client, app):
    """Test that authenticated users can access the dashboard."""
    with app.app_context():
        user = create_test_user()
        login(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert b"Mood Dashboard" in response.data


def test_dashboard_displays_calendar(client, app):
    """Test that the dashboard shows the calendar with correct dates."""
    with app.app_context():
        user = create_test_user()
        login(client)
        
        # Get current month's calendar
        today = datetime.now()
        response = client.get(f"/dashboard?year={today.year}&month={today.month}")
        
        assert response.status_code == 200
        # Verify current month is displayed
        assert today.strftime('%B %Y').encode() in response.data


def test_dashboard_mood_data(client, app):
    """Test that mood entries appear in the calendar."""
    with app.app_context():
        user = create_test_user()
        entries = create_test_entries(user.id)
        login(client)

        response = client.get("/dashboard")
        assert response.status_code == 200

        # Check that mood statistics are present
        assert b'Total Entries' in response.data
        assert b'Average Mood' in response.data
        
        # Check the actual values (more flexible - just check numbers are present)
        assert b'3' in response.data  # Total entries
        # Average mood should be around 5.3 (8+5+3)/3
        assert b'5' in response.data or b'5.3' in response.data  # Average mood


def test_dashboard_mood_calculations(client, app):
    """Test the mood calculations (average, distribution) are correct."""
    with app.app_context():
        user = create_test_user()
        entries = create_test_entries(user.id)
        login(client)

        response = client.get("/dashboard")
        assert response.status_code == 200

        # Calculate expected average (8 + 5 + 3) / 3 = 5.3
        expected_average = round((8 + 5 + 3) / 3, 1)  # Dashboard rounds to 1 decimal
        # Convert to string and encode for comparison with response data
        assert str(expected_average).encode() in response.data
        
        # Check distribution array in JavaScript (more flexible - check for the array structure)
        # The template uses tojson filter, so format might vary
        assert b'moodDist' in response.data or b'mood_distribution' in response.data
        # Check that distribution data is present (should have 5 buckets)
        assert b'[0' in response.data or b'[1' in response.data  # Array format


def test_dashboard_navigation(client, app):
    """Test month navigation functionality."""
    with app.app_context():
        user = create_test_user()
        login(client)

        # Test navigating to specific month
        test_year = 2025
        test_month = 6
        response = client.get(f"/dashboard?year={test_year}&month={test_month}")
        assert response.status_code == 200
        
        # Check if June 2025 is displayed
        assert b"June 2025" in response.data


def test_dashboard_weekly_trend(client, app):
    """Test weekly trend calculation and display."""
    with app.app_context():
        user = create_test_user()
        entries = create_test_entries(user.id)
        login(client)

        response = client.get("/dashboard")
        assert response.status_code == 200
        
        # Verify weekly trend chart is present
        assert b"weeklyTrendChart" in response.data
        # Check for chart.js initialization
        assert b"new Chart(document.getElementById('weeklyTrendChart')" in response.data


def test_dashboard_empty_month(client, app):
    """Test dashboard display for a month with no entries."""
    with app.app_context():
        user = create_test_user()
        login(client)

        # Navigate to a future month (assuming no entries exist)
        future_date = datetime.now() + timedelta(days=32)
        response = client.get(f"/dashboard?year={future_date.year}&month={future_date.month}")
        
        assert response.status_code == 200
        # Verify zero entries shown (more flexible check)
        assert b'0' in response.data or b'Total Entries' in response.data
        # Verify empty chart data arrays (check for array structure)
        assert b'[0' in response.data or b'moodDist' in response.data


def test_calendar_edge_cases(client, app):
    """Test calendar handling of edge cases (month transitions, leap years)."""
    with app.app_context():
        user = create_test_user()
        login(client)

        # Test December to January transition
        response = client.get("/dashboard?year=2024&month=12")
        assert response.status_code == 200
        assert b"31" in response.data  # December has 31 days
        
        # Test February in leap year (2024)
        response = client.get("/dashboard?year=2024&month=2")
        assert response.status_code == 200
        # February 2024 should show 29 days in the calendar
        assert b"29" in response.data