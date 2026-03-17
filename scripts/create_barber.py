"""
Create a barber user in the database.

Usage (run from the project root):
    python scripts/create_barber.py --email barber@example.com --password yourpassword

The script reads DATABASE_URL from the .env file (or environment variables),
so it works with both SQLite (dev) and PostgreSQL (production).
"""

import argparse
import sys
from pathlib import Path

# Allow importing app modules when run from the project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.base import Base
from app.models.user import User


def create_barber(email: str, password: str) -> None:
    # Ensure the users table exists (safe no-op if already created by Alembic).
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        normalized = email.lower().strip()
        if db.query(User).filter(User.email == normalized).first():
            print(f"A user with email '{normalized}' already exists.")
            return

        user = User(
            email=normalized,
            password_hash=hash_password(password),
            role="barber",
        )
        db.add(user)
        db.commit()
        print(f"Barber user created: {normalized}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a barber user")
    parser.add_argument("--email", required=True, help="Barber's email address")
    parser.add_argument("--password", required=True, help="Barber's password")
    args = parser.parse_args()
    create_barber(args.email, args.password)
