"""All DB logic for users. Routers must go through here, never query directly."""
import json

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


# ── Auth lookups ─────────────────────────────────────────

def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def get_by_username(db: Session, username: str) -> User | None:
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
    user = get_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ── Managers ─────────────────────────────────────────────

def list_managers(db: Session, *, include_inactive: bool = False):
    q = db.query(User).filter(User.role == "manager")
    if not include_inactive:
        q = q.filter(User.is_active.is_(True))
    return q.order_by(User.created_at.desc()).all()


def create_manager(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    phone: str | None,
    permissions: list[str],
) -> User:
    manager = User(
        email=email.lower(),
        username=username,
        password_hash=hash_password(password),
        role="manager",
        phone=phone,
        permissions=json.dumps(sorted(set(permissions))),
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


def update_manager(
    db: Session,
    manager: User,
    *,
    username: str | None = None,
    phone: str | None = None,
    permissions: list[str] | None = None,
) -> User:
    if username is not None and username != manager.username:
        manager.username = username
    if phone is not None:
        manager.phone = phone
    if permissions is not None:
        manager.permissions = json.dumps(sorted(set(permissions)))
    db.commit()
    db.refresh(manager)
    return manager


def delete_manager(db: Session, manager: User) -> None:
    """Hard delete a manager. Managers have no client/mover/booking/payment
    records, so this is safe. Escalations authored by them null out via
    ON DELETE SET NULL."""
    db.delete(manager)
    db.commit()