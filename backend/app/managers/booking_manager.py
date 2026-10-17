"""DB logic for bookings."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking


def get_by_id(db: Session, booking_id: int) -> Booking | None:
    return (
        db.query(Booking)
        .options(joinedload(Booking.service))
        .filter(Booking.id == booking_id)
        .first()
    )


def list_for_client(db: Session, client_id: int):
    return (
        db.query(Booking)
        .options(joinedload(Booking.service))
        .filter(Booking.client_id == client_id)
        .order_by(Booking.created_at.desc())
        .all()
    )


def list_for_mover(db: Session, mover_id: int):
    return (
        db.query(Booking)
        .options(joinedload(Booking.service))
        .filter(Booking.mover_id == mover_id)
        .order_by(Booking.created_at.desc())
        .all()
    )


def list_pending_near(db: Session, *, lat: float, lng: float, radius_miles: int):
    """Pending bookings whose pickup is within `radius_miles` of the given point."""
    from app.managers.mover_manager import haversine_miles
    candidates = (
        db.query(Booking)
        .options(joinedload(Booking.service))
        .filter(Booking.status == "pending", Booking.mover_id.is_(None))
        .all()
    )
    out = []
    for b in candidates:
        d = haversine_miles(lat, lng, b.pickup_lat, b.pickup_lng)
        if d <= radius_miles:
            out.append((b, d))
    out.sort(key=lambda x: x[1])
    return out


def create(db: Session, **fields) -> Booking:
    b = Booking(**fields)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def set_status(db: Session, booking: Booking, status: str) -> Booking:
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking


def assign_mover(db: Session, booking: Booking, mover_id: int) -> Booking:
    booking.mover_id = mover_id
    booking.status = "accepted"
    db.commit()
    db.refresh(booking)
    return booking


def cancel(db: Session, booking: Booking, reason: str) -> Booking:
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancellation_reason = reason
    db.commit()
    db.refresh(booking)
    return booking