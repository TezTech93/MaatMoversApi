"""Service catalog routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.serializers import serialize_service
from app.managers import service_manager
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceUpdate


router = APIRouter(prefix="/services", tags=["services"])


@router.get("")
def list_services(db: Session = Depends(get_db)) -> dict:
    """Public list of active services."""
    services = service_manager.list_active(db)
    return {"services": [serialize_service(s) for s in services]}


@router.get("/{service_id}")
def get_service(service_id: int, db: Session = Depends(get_db)) -> dict:
    """Fetch a single service by id."""
    service = service_manager.get_by_id(db, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"service": serialize_service(service)}


@router.post("", status_code=201)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """Admin-only: create a new service."""
    service = service_manager.create(db, **payload.model_dump())
    return {"service": serialize_service(service)}


@router.put("/{service_id}")
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """Admin-only: update a service."""
    service = service_manager.get_by_id(db, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    service = service_manager.update(db, service, **updates)
    return {"service": serialize_service(service)}


@router.delete("/{service_id}", status_code=204)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Admin-only: soft-deactivate a service."""
    service = service_manager.get_by_id(db, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    service_manager.delete(db, service)