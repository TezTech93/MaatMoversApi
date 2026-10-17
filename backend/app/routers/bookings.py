"""Booking routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_client, require_mover
from app.core.serializers import serialize_booking
from app.managers import booking_manager, mover_manager, notification_manager, service_manager
from app.models.user import User
from app.schemas.booking import CancelBookingRequest, CreateBookingRequest


router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", status_code=201)
def create_booking(
    payload: CreateBookingRequest,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> dict:
    """Create a draft booking. Price is computed from the service and pickup→dropoff distance."""
    service = service_manager.get_by_id(db, payload.service_id)
    if service is None or not service.is_active:
        raise HTTPException(status_code=404, detail="Service not available")
    distance = mover_manager.haversine_miles(
        payload.pickup_lat, payload.pickup_lng,
        payload.dropoff_lat, payload.dropoff_lng,
    )
    total = service.base_price_cents + int(round(service.per_mile_cents * distance))
    booking = booking_manager.create(
        db,
        client_id=current_user.client.id,
        service_id=service.id,
        status="draft",
        pickup_address=payload.pickup_address,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_address=payload.dropoff_address,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng,
        scheduled_at=payload.scheduled_at,
        distance_miles=round(distance, 2),
        total_cents=total,
        deposit_cents=1000,
    )
    booking = booking_manager.get_by_id(db, booking.id)
    return {"booking": serialize_booking(booking)}


@router.post("/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> dict:
    """Move draft → pending. Stripe Checkout will be created here in Phase 5."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None or booking.client_id != current_user.client.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "draft":
        raise HTTPException(status_code=409, detail=f"Cannot confirm booking in status '{booking.status}'")
    # NOTE Phase 5: create Stripe Checkout Session here and return checkout_url.
    booking = booking_manager.set_status(db, booking, "pending")

    # Notify matching movers (in-app only in Phase 2; email/push in Phase 4)
    matches = mover_manager.find_available(
        db, lat=booking.pickup_lat, lng=booking.pickup_lng, radius_miles=25
    )
    for mover, _ in matches:
        notification_manager.create(
            db,
            user_id=mover.user_id,
            kind="booking_pending",
            title="New move near you",
            body=f"A new move is available near {booking.pickup_address}.",
            data={"booking_id": booking.id},
        )

    return {"booking": serialize_booking(booking), "matching_movers": len(matches)}


@router.get("")
def list_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Role-aware listing: clients see their bookings, movers see theirs, admins see none via this route."""
    if current_user.client is not None:
        return {"bookings": [serialize_booking(b) for b in booking_manager.list_for_client(db, current_user.client.id)]}
    if current_user.mover is not None:
        return {"bookings": [serialize_booking(b) for b in booking_manager.list_for_mover(db, current_user.mover.id)]}
    return {"bookings": []}


@router.get("/{booking_id}")
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch a booking. Only visible to the owning client, assigned mover, or pending movers."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    is_client_owner = current_user.client and booking.client_id == current_user.client.id
    is_assigned_mover = current_user.mover and booking.mover_id == current_user.mover.id
    is_pending = booking.status == "pending" and booking.mover_id is None and current_user.mover
    if not (is_client_owner or is_assigned_mover or is_pending or current_user.role == "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to view this booking")
    return {"booking": serialize_booking(booking)}


@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    payload: CancelBookingRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Cancel a booking. Strike logic is a Phase 4 feature; Phase 2 just transitions state."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    is_client_owner = current_user.client and booking.client_id == current_user.client.id
    is_assigned_mover = current_user.mover and booking.mover_id == current_user.mover.id
    if not (is_client_owner or is_assigned_mover or current_user.role == "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
    if booking.status in ("completed", "cancelled", "refunded"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel booking in status '{booking.status}'")
    reason = payload.reason if payload else None
    booking = booking_manager.cancel(db, booking, reason or "No reason provided")
    return {"booking": serialize_booking(booking)}


@router.post("/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    current_user: User = Depends(require_mover),
    db: Session = Depends(get_db),
) -> dict:
    """Mover marks the booking complete. Phase 5 will trigger final payment/refund via webhook."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None or booking.mover_id != current_user.mover.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in ("accepted", "in_progress"):
        raise HTTPException(status_code=409, detail=f"Cannot complete booking in status '{booking.status}'")
    booking = booking_manager.set_status(db, booking, "completed")
    if booking.client_id:
        notification_manager.create(
            db,
            user_id=booking.client.user_id,
            kind="booking_completed",
            title="Move completed",
            body=f"Your move #{booking.id} is complete.",
            data={"booking_id": booking.id},
        )
    return {"booking": serialize_booking(booking)}


@router.get("/{booking_id}/transactions")
def list_transactions(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the transaction ledger for a booking. Populated by Stripe webhooks in Phase 5."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    is_client_owner = current_user.client and booking.client_id == current_user.client.id
    is_assigned_mover = current_user.mover and booking.mover_id == current_user.mover.id
    if not (is_client_owner or is_assigned_mover or current_user.role == "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    from app.models.transaction import Transaction
    txs = db.query(Transaction).filter(Transaction.booking_id == booking.id).all()
    return {
        "transactions": [
            {
                "id": t.id,
                "booking_id": t.booking_id,
                "amount_cents": t.amount_cents,
                "currency": t.currency,
                "kind": t.kind,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in txs
        ]
    }