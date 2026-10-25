"""User self-service routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.core.serializers import serialize_user
from app.managers import booking_manager, user_manager
from app.models.push_token import PushToken
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UpdateUserRequest
from app.services import email_service


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    """Full profile including nested role-specific data."""
    return {"user": serialize_user(current_user)}


@router.put("/me")
def update_me(
    payload: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update username and/or phone."""
    if payload.username and payload.username != current_user.username:
        existing = user_manager.get_by_username(db, payload.username)
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=409, detail="Username already taken")
        current_user.username = payload.username
    if payload.phone is not None:
        current_user.phone = payload.phone
    db.commit()
    db.refresh(current_user)
    return {"user": serialize_user(current_user)}


@router.put("/me/password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Change the current user's password after verifying the old one."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}


@router.delete("/me", status_code=204)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete the current user.

    - Rejects if any active bookings exist (pending / accepted / in_progress).
      The user must finish or cancel those first.
    - Auto-cancels draft bookings (no money involved).
    - Deletes push tokens (device PII).
    - Sets is_active = False (login blocked, existing JWTs expire naturally).
    - Sends a confirmation email.
    - Keeps audit trail (bookings, transactions, strikes) for marketplace integrity.
    """
    active_statuses = ("pending", "accepted", "in_progress")
    active = []
    if current_user.client:
        active += [
            b for b in booking_manager.list_for_client(db, current_user.client.id)
            if b.status in active_statuses
        ]
    if current_user.mover:
        active += [
            b for b in booking_manager.list_for_mover(db, current_user.mover.id)
            if b.status in active_statuses
        ]

    if active:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You have {len(active)} active booking(s). Finish or cancel "
                "them before deleting your account."
            ),
        )

    # Cancel drafts silently (no money, no strikes per policy)
    if current_user.client:
        for b in booking_manager.list_for_client(db, current_user.client.id):
            if b.status == "draft":
                booking_manager.cancel(db, b, "Account deleted")
    if current_user.mover:
        for b in booking_manager.list_for_mover(db, current_user.mover.id):
            if b.status == "draft":
                booking_manager.cancel(db, b, "Account deleted")

    # Drop push tokens (device-level PII)
    db.query(PushToken).filter(PushToken.user_id == current_user.id).delete()

    # Soft delete
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Confirmation email (best-effort)
    try:
        email_service.send_email(
            to_email=current_user.email,
            subject="Your MaatMovers account has been deactivated",
            body_text=(
                "Your MaatMovers account has been deactivated. You can no longer "
                "sign in with this email.\n\n"
                "If this was a mistake, contact support."
            ),
        )
    except Exception as e:
        print(f"[delete] confirmation email failed: {e}")