# init_db.py
from app import app
from extensions import db
from models import *

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database initialized — all tables are ready!")
