import pytest
from app import app
from extensions import db
from models import User


@pytest.fixture
def client(app):
    """Set up a Flask test client for the app"""
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_user(app):
    """Create a test user in the database"""
    with app.app_context():
        user = User(username="username", email="test@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


def test_login_invalid_credentials(client):
    """Invalid login should fail"""
    response = client.post("/", data={"username": "wrong", "password": "wrong"}, follow_redirects=True)
    assert response.status_code == 200  
    assert b"Invalid username or password" in response.data


def test_login_valid_credentials(client, test_user):
    """Valid login should redirect to /home"""
    response = client.post("/", data={"username": "username", "password": "password"})
    assert response.status_code == 302  # redirect
    assert response.location.endswith("/home")


def test_home_requires_login(client):
    """Accessing /home without logging in redirects to /"""
    response = client.get("/home", follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")  # redirected to login page


def test_login_and_access_home(client, test_user):
    """After successful login, user can access home page"""
    client.post("/", data={"username": "username", "password": "password"})
    response = client.get("/home")
    assert response.status_code == 200
    assert b"Mood Journal" in response.data


def test_logout_clears_session(client, test_user):
    """Logging out should redirect to login and restrict future access"""
    # Login first
    client.post("/", data={"username": "username", "password": "password"})
    # Logout
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data or b"Log in" in response.data  # back on login page

    # Try accessing home again after logout
    response = client.get("/home", follow_redirects=False)
    assert response.status_code == 302  # redirected again
    assert response.location.endswith("/")

