import pytest
from app import app

@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client

def create_user(app):
    from models import User
    from extensions import db
    with app.app_context():
        # Prevent duplicates if a test runs twice
        existing = User.query.filter_by(username="username").first()
        if existing:
            return

        user = User(username="username", email="test@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

def login(client):
    client.post("/", data={
        "username": "username",
        "password": "password"
    }, follow_redirects=True)
