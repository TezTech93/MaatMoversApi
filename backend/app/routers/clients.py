"""Client profile routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.serializers import serialize_client
from app.managers import client_manager
from app.models.user import User
from app.schemas.client import UpdateClientRequest


router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/me", status_code=201)
def become_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a client profile for the current user. Idempotent."""
    existing = client_manager.get_for_user(db, current_user.id)
    if existing:
        return {"client": serialize_client(existing)}
    client = client_manager.create_for_user(db, current_user.id)
    return {"client": serialize_client(client)}


@router.get("/me")
def get_my_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the current user's client profile."""
    client = client_manager.get_for_user(db, current_user.id)
    if client is None:
        return {"client": None}
    return {"client": serialize_client(client)}


@router.put("/me")
def update_my_client(
    payload: UpdateClientRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update the client's default address."""
    client = client_manager.get_for_user(db, current_user.id)
    if client is None:
        return {"client": None}
    client = client_manager.update_default_address(
        db, client,
        address=payload.default_address,
        lat=payload.default_lat,
        lng=payload.default_lng,
    )
    return {"client": serialize_client(client)}