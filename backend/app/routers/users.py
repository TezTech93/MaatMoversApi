"""User self-service routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.core.serializers import serialize_user
from app.managers import user_manager
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UpdateUserRequest


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
    """Soft-delete the current user (is_active = False)."""
    current_user.is_active = False
    db.commit()