"""Strike policy enforcement.

Rules (from the MaatMovers brief):
- Mover cancels their first-ever accepted booking → immediate block.
- Mover cancels an accepted booking < 6 hours before scheduled_at → strike.
- Mover cancels an accepted booking ≥ 6 hours before scheduled_at → no strike.
- Client cancels an accepted/in_progress booking < 6 hours before scheduled_at → strike.
- Client cancels ≥ 6 hours out → no strike.
- Draft or pending cancellations → no strike (no counterparty invested).
- Admin cancellations → no strike.
- 3 strikes → block. Strikes are permanent until an admin resets them.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.strike import Strike
from app.models.user import User


STRIKE_THRESHOLD = 3
CANCEL_WINDOW_HOURS = 6


def _hours_until_scheduled(booking: Booking) -> float:
    if not booking.scheduled_at:
        return float("inf")
    scheduled = booking.scheduled_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    return (scheduled - datetime.now(timezone.utc)).total_seconds() / 3600.0


def _prior_accepts(db: Session, mover_id: int, current_booking_id: int) -> int:
    """Bookings this mover had been assigned to before this one."""
    return (
        db.query(Booking)
        .filter(
            Booking.mover_id == mover_id,
            Booking.id != current_booking_id,
        )
        .count()
    )


def evaluate_cancellation(db: Session, *, booking: Booking, canceller: User) -> dict:
    """Return a preview of what would happen if `canceller` cancels `booking`.

    Pure read. Never mutates state.
    """
    hours = _hours_until_scheduled(booking)
    within_window = hours < CANCEL_WINDOW_HOURS
    base = {
        "strike_eligible": False,
        "would_strike": False,
        "first_accept_block": False,
        "current_strikes": canceller.strikes,
        "would_reach_block": canceller.is_blocked,
        "hours_until_scheduled": round(hours, 2) if hours != float("inf") else None,
    }

    # Draft / pending → no strike. Nothing has happened yet.
    if booking.status in ("draft", "pending"):
        return base

    # Admin → no strike.
    if canceller.role == "admin":
        return base

    # Mover who owns the assignment.
    if canceller.mover is not None and booking.mover_id == canceller.mover.id:
        prior = _prior_accepts(db, canceller.mover.id, booking.id)
        if prior == 0:
            return {
                **base,
                "strike_eligible": True,
                "would_strike": True,
                "first_accept_block": True,
                "would_reach_block": True,
            }
        if within_window:
            new_count = canceller.strikes + 1
            return {
                **base,
                "strike_eligible": True,
                "would_strike": True,
                "would_reach_block": new_count >= STRIKE_THRESHOLD,
            }
        return {**base, "strike_eligible": True}

    # Client who owns the booking.
    if canceller.client is not None and booking.client_id == canceller.client.id:
        if within_window:
            new_count = canceller.strikes + 1
            return {
                **base,
                "strike_eligible": True,
                "would_strike": True,
                "would_reach_block": new_count >= STRIKE_THRESHOLD,
            }
        return {**base, "strike_eligible": True}

    return base


def apply_cancellation_strike(
    db: Session, *, booking: Booking, canceller: User, reason: str
) -> dict:
    """Apply the strike policy. Mutates canceller.strikes / is_blocked and inserts a Strike row.

    Returns: { strike_issued, blocked_now, strike_reason, current_strikes, is_blocked }
    """
    preview = evaluate_cancellation(db, booking=booking, canceller=canceller)
    strike_issued = False
    blocked_now = False
    strike_reason = None

    if preview["first_accept_block"]:
        strike_issued = True
        strike_reason = "Mover cancelled their first accepted assignment"
    elif preview["would_strike"]:
        strike_issued = True
        strike_reason = (
            f"Cancelled within {CANCEL_WINDOW_HOURS}h of scheduled time"
        )

    if strike_issued:
        canceller.strikes = canceller.strikes + 1
        if preview["first_accept_block"] or canceller.strikes >= STRIKE_THRESHOLD:
            canceller.is_blocked = True
            blocked_now = True
        strike = Strike(
            user_id=canceller.id,
            booking_id=booking.id,
            reason=strike_reason or reason or "Cancellation",
        )
        db.add(strike)
        db.flush()

    return {
        "strike_issued": strike_issued,
        "blocked_now": blocked_now,
        "strike_reason": strike_reason,
        "current_strikes": canceller.strikes,
        "is_blocked": canceller.is_blocked,
    }