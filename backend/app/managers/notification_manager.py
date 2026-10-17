"""DB logic for notifications and push tokens."""
import json

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.push_token import PushToken


def create(db: Session, *, user_id: int, kind: str, title: str, body: str, data=None) -> Notification:
    n = Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        data_json=json.dumps(data) if data is not None else None,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def list_for_user(db: Session, user_id: int):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_by_id(db: Session, notification_id: int) -> Notification | None:
    return db.query(Notification).filter(Notification.id == notification_id).first()


def mark_read(db: Session, notification: Notification) -> Notification:
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def upsert_push_token(db: Session, *, user_id: int, token: str, platform: str | None) -> PushToken:
    existing = db.query(PushToken).filter(PushToken.token == token).first()
    if existing:
        existing.user_id = user_id
        existing.platform = platform
        db.commit()
        db.refresh(existing)
        return existing
    t = PushToken(user_id=user_id, token=token, platform=platform)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t