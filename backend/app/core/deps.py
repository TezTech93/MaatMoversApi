"""Shared FastAPI dependencies."""
import json

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.managers import user_manager
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Authorization header."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_access_token(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = user_manager.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_client(user: User = Depends(get_current_user)) -> User:
    if user.client is None:
        raise HTTPException(status_code=403, detail="Client profile required")
    return user


def require_mover(user: User = Depends(get_current_user)) -> User:
    if user.mover is None:
        raise HTTPException(status_code=403, detail="Mover profile required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Supreme admin only. Managers are rejected here."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def _granted_permissions(user: User) -> set:
    if not user.permissions:
        return set()
    try:
        data = json.loads(user.permissions)
        return set(data) if isinstance(data, list) else set()
    except (ValueError, TypeError):
        return set()


def require_permission(*keys: str):
    """Supreme admins bypass. Managers must hold at least one of `keys`.

    Also accepts the special token 'manager' meaning "any manager,
    regardless of permissions" — used for endpoints managers should
    always reach (e.g. raising an escalation).
    """
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role == "admin":
            return user
        if user.role != "manager":
            raise HTTPException(
                status_code=403, detail="Admin or manager required"
            )
        granted = _granted_permissions(user)
        if "manager" in keys:
            return user
        if not granted.intersection(keys):
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: {' or '.join(keys)}",
            )
        return user
    return checker