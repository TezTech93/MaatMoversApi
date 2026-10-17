"""Mover profile and matching routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_mover
from app.core.serializers import serialize_booking, serialize_mover
from app.managers import booking_manager, mover_manager, notification_manager
from app.models.user import User
from app.schemas.mover import BecomeMoverRequest, DeclineRequest, UpdateMoverRequest


router = APIRouter(prefix="/movers", tags=["movers"])


@router.post("/me", status_code=201)
def become_mover(
    payload: BecomeMoverRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a mover profile for the current user. Idempotent on the create; updates fields if exists."""
    existing = mover_manager.get_for_user(db, current_user.id)
    if existing:
        mover = mover_manager.update_profile(
            db, existing,
            service_radius_miles=payload.service_radius_miles,
            home_address=payload.home_address,
            home_lat=payload.home_lat,
            home_lng=payload.home_lng,
            bio=payload.bio,
        )
        return {"mover": serialize_mover(mover)}
    mover = mover_manager.create_for_user(
        db, current_user.id,
        service_radius_miles=payload.service_radius_miles,
        home_address=payload.home_address,
        home_lat=payload.home_lat,
        home_lng=payload.home_lng,
        bio=payload.bio,
    )
    return {"mover": serialize_mover(mover)}


@router.get("/me")
def get_my_mover(
    current_user: User = Depends(require_mover),
    db: Session = Depends(get_db),
) -> dict:
    """Mover profile plus basic stats."""
    mover = current_user.mover
    completed = sum(1 for b in booking_manager.list_for_mover(db, mover.id) if b.status == "completed")
    return {"mover": serialize_mover(mover), "stats": {"completed_bookings": completed}}


@router.put("/me")
def update_my_mover(
    payload: UpdateMoverRequest,
    current_user: User = Depends(require_mover),
    db: Session = Depends(get_db),
) -> dict:
    """Update radius, bio, or home location."""
    mover = mover_manager.update_profile(
        db, current_user.mover,
        service_radius_miles=payload.service_radius_miles,
        bio=payload.bio,
        home_address=payload.home_address,
        home_lat=payload.home_lat,
        home_lng=payload.home_lng,
    )
    return {"mover": serialize_mover(mover)}


@router.get("/available")
def list_available_movers(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_miles: int = Query(25, ge=1, le=25),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """List approved movers within radius_miles of the given point, sorted by distance."""
    results = mover_manager.find_available(db, lat=lat, lng=lng, radius_miles=radius_miles)
    return {
        "movers": [
            {**serialize_mover(m), "distance_miles": round(d, 2)}
            for m, d in results
        ]
    }


@router.get("/me/available-bookings")
def list_available_bookings(
    current_user: User = Depends(require_mover),
    db: Session = Depends(get_db),
) -> dict:
    """Pending bookings whose pickup is within the mover's own service radius."""
    mover = current_user.mover
    results = booking_manager.list_pending_near(
        db, lat=mover.home_lat, lng=mover.home_lng, radius_miles=mover.service_radius_miles
    )
    return {
        "bookings": [
            {**serialize_booking(b), "distance_miles": round(d, 2)}
            for b, d in results
        ]
    }


@router.post("/me/accept/{booking_id}")
def accept_booking(
    booking_id: int,
    current_user: User = Depends(require_mover),
    db: Session = Depends(get_db),
) -> dict:
    """Accept a pending booking. First mover to accept wins (guarded by row lock)."""
    mover = current_user.mover
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "pending" or booking.mover_id is not None:
        raise HTTPException(status_code=409, detail="Booking is no longer available")
    if current_user.is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    booking = booking_manager.assign_mover(db, booking, mover.id)

    # Notify the client
    notification_manager.create(
        db,
        user_id=booking.client.user_id,
        kind="booking_accepted",
        title="Your move has been accepted",
        body=f"A mover has accepted your booking #{booking.id}.",
        data={"booking_id": booking.id},
    )
    return {"booking": serialize_booking(booking)}


@router.post("/me/decline/{booking_id}", status_code=204)
def decline_booking(
    booking_id: int,
    payload: DeclineRequest | None = None,
    current_user: User = Depends(require_mover),
    db: Session = Depends(get_db),
) -> None:
    """Decline a booking. No-op server-side in Phase 2 — decline tracking lands in Phase 4."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return None