"""All DB logic for users. Routers must go through here, never query directly."""
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by primary key."""
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> User | None:
    """Fetch a user by email (case-insensitive)."""
    return db.query(User).filter(User.email == email.lower()).first()


def get_by_username(db: Session, username: str) -> User | None:
    """Fetch a user by exact username."""
    return db.query(User).filter(User.username == username).first()


def create_user(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    role: str,
    phone: str | None = None,
) -> User:
    """Insert a new user with a hashed password. Caller checks uniqueness first."""
    user = User(
        email=email.lower(),
        username=username,
        password_hash=hash_password(password),
        role=role,
        phone=phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid and the account is active, else None."""
    user = get_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user