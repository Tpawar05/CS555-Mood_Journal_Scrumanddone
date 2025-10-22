import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import User, MoodEntry
from sqlalchemy import inspect

def test_database_connection():
    """Check if the database connection and tables are working."""
    with app.app_context():
        try:

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print("✅ Connected to database successfully!")
            print("📋 Tables found:", tables)

            user_count = db.session.query(User).count()
            entry_count = db.session.query(MoodEntry).count()
            print(f"👤 Users in database: {user_count}")
            print(f"📝 Mood entries in database: {entry_count}")

            sample_user = User.query.first()
            if sample_user:
                print(f"✨ Sample user: {sample_user.username} ({sample_user.email})")
            else:
                print("⚠️ No users found in the database.")

            print(f"🗄️  Connected via URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

        except Exception as e:
            print("❌ Database connection test failed:")
            print(e)

if __name__ == "__main__":
    test_database_connection()
