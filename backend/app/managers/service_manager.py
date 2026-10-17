"""DB logic for services."""
from sqlalchemy.orm import Session

from app.models.service import Service


def list_active(db: Session):
    return db.query(Service).filter(Service.is_active.is_(True)).order_by(Service.id).all()


def list_all(db: Session):
    return db.query(Service).order_by(Service.id).all()


def get_by_id(db: Session, service_id: int) -> Service | None:
    return db.query(Service).filter(Service.id == service_id).first()


def create(db: Session, **fields) -> Service:
    s = Service(**fields)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def update(db: Session, service: Service, **fields) -> Service:
    for k, v in fields.items():
        setattr(service, k, v)
    db.commit()
    db.refresh(service)
    return service


def delete(db: Session, service: Service) -> None:
    service.is_active = False
    db.commit()