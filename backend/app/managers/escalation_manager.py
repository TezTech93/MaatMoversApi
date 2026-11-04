"""Escalation queue: managers raise, supreme admins resolve."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.escalation import Escalation


def create(
    db: Session,
    *,
    created_by_id: int,
    subject: str,
    body: str,
    related_user_id: int | None = None,
    related_booking_id: int | None = None,
) -> Escalation:
    e = Escalation(
        created_by_id=created_by_id,
        subject=subject,
        body=body,
        related_user_id=related_user_id,
        related_booking_id=related_booking_id,
        status="open",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def get_by_id(db: Session, escalation_id: int) -> Escalation | None:
    return db.query(Escalation).filter(Escalation.id == escalation_id).first()


def list_all(db: Session, *, status: str | None = None):
    q = db.query(Escalation)
    if status:
        q = q.filter(Escalation.status == status)
    return q.order_by(Escalation.created_at.desc()).all()


def resolve(db: Session, escalation: Escalation, resolver_id: int, status: str) -> Escalation:
    escalation.status = status
    if status == "resolved":
        escalation.resolved_by_id = resolver_id
        escalation.resolved_at = datetime.now(timezone.utc)
    else:
        escalation.resolved_by_id = None
        escalation.resolved_at = None
    db.commit()
    db.refresh(escalation)
    return escalation