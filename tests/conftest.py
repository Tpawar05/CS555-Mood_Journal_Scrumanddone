"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures used across all test files:
- app: Flask application instance with test configuration
- client: Flask test client for making HTTP requests
"""

import pytest
from app import app as flask_app
from extensions import db


@pytest.fixture
def app():
    """
    Create and configure a Flask application instance for testing.
    Uses an in-memory SQLite database for CI compatibility.
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


@pytest.fixture
def client(app):
    """Create a Flask test client for making HTTP requests."""
    return app.test_client()
