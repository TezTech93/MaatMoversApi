"""DB logic for notifications and push tokens, plus best-effort delivery dispatch."""
import json

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.push_token import PushToken
from app.models.user import User


def create(
    db: Session,
    *,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    data=None,
) -> Notification:
    """Create a notification and dispatch email + push. Delivery failures are logged only."""
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

    _dispatch_delivery(db, n, data)
    return n


def _dispatch_delivery(db: Session, n: Notification, data) -> None:
    """Send email + push for a freshly-created notification. Never raises."""
    from app.services import email_service, push_service

    user = db.query(User).filter(User.id == n.user_id).first()
    if user is None or not user.is_active:
        print(f"[notifications] skip delivery user={n.user_id} (inactive/missing)")
        return

    try:
        email_service.send_email(to_email=user.email, subject=n.title, body_text=n.body)
    except Exception as e:
        print(f"[notifications] email dispatch failed user={user.id}: {e}")

    try:
        tokens = [
            t.token
            for t in db.query(PushToken).filter(PushToken.user_id == user.id).all()
        ]
        if not tokens:
            print(f"[notifications] no push tokens for user={user.id}")
            return
        push_service.send_push(tokens, title=n.title, body=n.body, data=data)
    except Exception as e:
        print(f"[notifications] push dispatch failed user={user.id}: {e}")


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


def upsert_push_token(
    db: Session, *, user_id: int, token: str, platform: str | None
) -> PushToken:
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