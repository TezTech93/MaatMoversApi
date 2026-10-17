"""Notification routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.serializers import serialize_notification
from app.managers import notification_manager
from app.models.user import User
from app.schemas.notification import RegisterTokenRequest


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List the current user's notifications, newest first."""
    items = notification_manager.list_for_user(db, current_user.id)
    return {"notifications": [serialize_notification(n) for n in items]}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark a notification read. Only the owner can do this."""
    n = notification_manager.get_by_id(db, notification_id)
    if n is None or n.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    n = notification_manager.mark_read(db, n)
    return {"notification": serialize_notification(n)}


@router.post("/register-token", status_code=201)
def register_token(
    payload: RegisterTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Register an Expo push token for the current user."""
    t = notification_manager.upsert_push_token(
        db, user_id=current_user.id, token=payload.token, platform=payload.platform
    )
    return {"ok": True, "token_id": t.id}