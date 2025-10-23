"""
Pytest configuration and fixtures for testing.
This version ensures CI runs all tests in-memory and isolated.
"""

import pytest
from app import app as flask_app
from extensions import db


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask app with an in-memory SQLite database.
    This avoids file I/O and works on GitHub CI.
    """
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"check_same_thread": False}},
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Provides a Flask test client for HTTP requests."""
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_db(app):
    """Clear all data between tests to ensure isolation."""
    yield
    with app.app_context():
        # Import here to avoid early database access
        from models import MoodEntry
        # Clean up all tables after each test
        db.session.query(MoodEntry).delete()
        db.session.commit()