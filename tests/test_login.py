
import pytest
from app import app

@pytest.fixture
def client():
    """Set up a Flask test client for the app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_login_invalid_credentials(client):
    """Invalid login should fail"""
    response = client.post("/login", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 200  # stays on login page
    assert b"Invalid username or password" in response.data


def test_login_valid_credentials(client):
    """Valid login should redirect to /home/index.html"""
    response = client.post("/login", data={"username": "username", "password": "password"})
    assert response.status_code == 302  # Redirect
    assert "/home/index.html" in response.location


def test_home_requires_login(client):
    """Accessing /home/index.html without logging in redirects to /"""
    response = client.get("/home/index.html", follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")  # redirected to login page


def test_login_and_access_home(client):
    """After successful login, user can access home page"""
    client.post("/login", data={"username": "username", "password": "password"})
    response = client.get("/home/index.html")
    assert response.status_code == 200
    assert b"Mood Journal" in response.data


def test_logout_clears_session(client):
    """Logging out should redirect to login and restrict future access"""
    # Login first
    client.post("/login", data={"username": "username", "password": "password"})
    # Logout
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Log in" in response.data  # back on login page

    # Try accessing home again after logout
    response = client.get("/home/index.html", follow_redirects=False)
    assert response.status_code == 302  # should be redirected again
