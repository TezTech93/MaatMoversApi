"""Strike policy enforcement + admin CRUD."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.strike import Strike
from app.models.user import User


STRIKE_THRESHOLD = 3
CANCEL_WINDOW_HOURS = 6


# ═══════════════════════════════════════════════════════════
# Policy (cancellation flow — unchanged)
# ═══════════════════════════════════════════════════════════

def _hours_until_scheduled(booking: Booking) -> float:
    if not booking.scheduled_at:
        return float("inf")
    scheduled = booking.scheduled_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    return (scheduled - datetime.now(timezone.utc)).total_seconds() / 3600.0


def _prior_accepts(db: Session, mover_id: int, current_booking_id: int) -> int:
    return (
        db.query(Booking)
        .filter(
            Booking.mover_id == mover_id,
            Booking.id != current_booking_id,
        )
        .count()
    )


def evaluate_cancellation(db: Session, *, booking: Booking, canceller: User) -> dict:
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

    if booking.status in ("draft", "pending"):
        return base
    if canceller.role == "admin":
        return base

    if canceller.mover is not None and booking.mover_id == canceller.mover.id:
        prior = _prior_accepts(db, canceller.mover.id, booking.id)
        if prior == 0:
            return {**base, "strike_eligible": True, "would_strike": True,
                    "first_accept_block": True, "would_reach_block": True}
        if within_window:
            new_count = canceller.strikes + 1
            return {**base, "strike_eligible": True, "would_strike": True,
                    "would_reach_block": new_count >= STRIKE_THRESHOLD}
        return {**base, "strike_eligible": True}

    if canceller.client is not None and booking.client_id == canceller.client.id:
        if within_window:
            new_count = canceller.strikes + 1
            return {**base, "strike_eligible": True, "would_strike": True,
                    "would_reach_block": new_count >= STRIKE_THRESHOLD}
        return {**base, "strike_eligible": True}

    return base


def apply_cancellation_strike(
    db: Session, *, booking: Booking, canceller: User, reason: str
) -> dict:
    preview = evaluate_cancellation(db, booking=booking, canceller=canceller)
    strike_issued = False
    blocked_now = False
    strike_reason = None

    if preview["first_accept_block"]:
        strike_issued = True
        strike_reason = "Mover cancelled their first accepted assignment"
    elif preview["would_strike"]:
        strike_issued = True
        strike_reason = f"Cancelled within {CANCEL_WINDOW_HOURS}h of scheduled time"

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


# ═══════════════════════════════════════════════════════════
# Admin CRUD
# ═══════════════════════════════════════════════════════════

def list_for_user(db: Session, user_id: int):
    """Return list of (strike, creator_username_or_None) tuples."""
    rows = (
        db.query(Strike, User.username)
        .outerjoin(User, User.id == Strike.created_by_id)
        .filter(Strike.user_id == user_id)
        .order_by(Strike.issued_at.desc())
        .all()
    )
    return rows


def get_by_id(db: Session, strike_id: int) -> Strike | None:
    return db.query(Strike).filter(Strike.id == strike_id).first()


def create_manual(
    db: Session,
    *,
    target: User,
    reason: str,
    created_by_id: int,
    booking_id: int | None = None,
) -> tuple[Strike, bool]:
    """Create a manual strike. Returns (strike, blocked_now)."""
    strike = Strike(
        user_id=target.id,
        booking_id=booking_id,
        reason=reason,
        created_by_id=created_by_id,
    )
    db.add(strike)
    target.strikes = target.strikes + 1
    blocked_now = False
    if target.strikes >= STRIKE_THRESHOLD and not target.is_blocked:
        target.is_blocked = True
        blocked_now = True
    db.commit()
    db.refresh(strike)
    db.refresh(target)
    return strike, blocked_now


def delete_strike(db: Session, strike: Strike) -> User:
    """Delete one strike and decrement the user's counter. Does NOT auto-unblock."""
    target = db.query(User).filter(User.id == strike.user_id).first()
    if target is not None and target.strikes > 0:
        target.strikes = target.strikes - 1
    db.delete(strike)
    db.commit()
    if target is not None:
        db.refresh(target)
    return target


def clear_for_user(db: Session, target: User) -> int:
    """Delete all strikes for a user and reset counter. Also unblocks.

    Returns the number of strike rows deleted.
    """
    count = db.query(Strike).filter(Strike.user_id == target.id).delete()
    target.strikes = 0
    target.is_blocked = False
    db.commit()
    db.refresh(target)
    return count