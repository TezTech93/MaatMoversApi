"""One-off CLI to seed an admin user.

Usage:
    python -m app.scripts.create_admin <email> <username> <password>
"""
import sys

from app.core.database import SessionLocal
from app.managers import user_manager


def main() -> None:
    """Parse argv, create an admin user, and print the result."""
    if len(sys.argv) != 4:
        print("usage: python -m app.scripts.create_admin <email> <username> <password>")
        raise SystemExit(2)

    email, username, password = sys.argv[1], sys.argv[2], sys.argv[3]
    db = SessionLocal()
    try:
        if user_manager.get_by_email(db, email):
            print(f"[create_admin] user already exists: {email}")
            raise SystemExit(1)
        user = user_manager.create_user(
            db,
            email=email,
            username=username,
            password=password,
            role="admin",
            phone=None,
        )
        print(f"[create_admin] created admin id={user.id} email={user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()