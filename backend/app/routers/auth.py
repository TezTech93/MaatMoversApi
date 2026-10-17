"""Auth routes: register, login, and current-user lookup."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.core.serializers import serialize_user
from app.managers import user_manager
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    """Register a new client or mover and return a JWT plus the serialized user."""
    if user_manager.get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if user_manager.get_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    user = user_manager.create_user(
        db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        role=payload.role,
        phone=payload.phone,
    )
    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """Authenticate by email + password and return a JWT plus the serialized user."""
    user = user_manager.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(user)}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    """Return the authenticated user's full profile."""
    return {"user": serialize_user(current_user)}