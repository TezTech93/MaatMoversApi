"""Payment routes.

Phase 5.1: deposit checkout + webhook.
Phase 5.2: final payment checkout + webhook branching.
Phase 5.3: refunds (auto-on-cancel + admin manual) + charge.refunded webhook.
Phase 5.4: Connect onboarding.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin, require_client
from app.core.serializers import serialize_booking
from app.managers import (
    booking_manager,
    mover_manager,
    notification_manager,
    payment_manager,
)
from app.models.user import User
from app.services import stripe_service


router = APIRouter(prefix="/payments", tags=["payments"])


# ═══════════════════════════════════════════════════════════
# Internal helpers shared by routes and the cancel flow
# ═══════════════════════════════════════════════════════════

def _create_deposit_checkout(*, booking, current_user: User, db: Session) -> dict:
    """Shared by /bookings/{id}/confirm and /payments/deposit/{id}."""
    if current_user.is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    if booking.status != "draft":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start checkout for booking in status '{booking.status}'",
        )
    if booking.client_id != current_user.client.id:
        raise HTTPException(status_code=403, detail="Not your booking")

    existing = payment_manager.latest_pending_deposit(db, booking.id)
    if existing and existing.stripe_checkout_session_id:
        try:
            session = stripe_service.retrieve_checkout_session(
                existing.stripe_checkout_session_id
            )
            if session.get("status") == "open" and session.get("url"):
                return {
                    "booking": booking_manager.get_by_id(db, booking.id),
                    "checkout_url": session["url"],
                    "reused": True,
                }
        except Exception as e:
            print(f"[payments] could not reuse deposit session: {e}")

    try:
        session = stripe_service.create_deposit_checkout_session(
            booking_id=booking.id,
            amount_cents=booking.deposit_cents,
            product_name=f"Deposit — {booking.service.name} booking #{booking.id}",
            customer_email=current_user.email,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"[payments] stripe session create failed: {e}")
        raise HTTPException(status_code=502, detail="Could not create checkout session")

    payment_manager.create_pending_deposit(
        db,
        booking_id=booking.id,
        amount_cents=booking.deposit_cents,
        session_id=session["id"],
    )
    return {
        "booking": booking_manager.get_by_id(db, booking.id),
        "checkout_url": session["url"],
        "reused": False,
    }


def refund_deposit_for_booking(
    db: Session, booking, initiated_by: str = "auto"
) -> dict:
    """Issue a Stripe refund for the deposit. Idempotent.

    Returns:
        {
            'refunded': bool,
            'reason': str (only when refunded=False),
            'refund_id': str | None,
            'amount_cents': int | None,
            'initiated_by': str,
        }
    """
    if payment_manager.has_succeeded_refund(db, booking.id):
        return {"refunded": False, "reason": "already_refunded", "initiated_by": initiated_by}

    existing_pending = payment_manager.latest_pending_refund(db, booking.id)
    if existing_pending is not None:
        return {"refunded": False, "reason": "pending_refund_exists", "initiated_by": initiated_by}

    deposit = payment_manager.deposit_succeeded_for_booking(db, booking.id)
    if deposit is None or not deposit.stripe_payment_intent_id:
        return {"refunded": False, "reason": "no_paid_deposit", "initiated_by": initiated_by}

    # Create the pending row first so the webhook always has somewhere to land.
    tx = payment_manager.create_pending_refund(
        db,
        booking_id=booking.id,
        amount_cents=deposit.amount_cents,
        payment_intent_id=deposit.stripe_payment_intent_id,
    )

    try:
        refund = stripe_service.refund_payment_intent(
            deposit.stripe_payment_intent_id,
            amount_cents=deposit.amount_cents,
            reason="requested_by_customer",
        )
    except Exception as e:
        print(f"[refund] stripe error for booking {booking.id}: {e}")
        payment_manager.mark_refund_failed(db, tx.id)
        return {
            "refunded": False,
            "reason": "stripe_error",
            "error": str(e),
            "initiated_by": initiated_by,
        }

    print(
        f"[refund] issued re={refund['id']} booking={booking.id} "
        f"pi={deposit.stripe_payment_intent_id} amount={deposit.amount_cents}"
    )
    return {
        "refunded": True,
        "refund_id": refund["id"],
        "amount_cents": deposit.amount_cents,
        "initiated_by": initiated_by,
    }


# ═══════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════

@router.post("/deposit/{booking_id}")
def deposit(
    booking_id: int,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> dict:
    """Create (or reuse) a Stripe Checkout Session for the refundable deposit."""
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _create_deposit_checkout(booking=booking, current_user=current_user, db=db)


@router.post("/final/{booking_id}")
def final(
    booking_id: int,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db),
) -> dict:
    """Create (or reuse) a Stripe Checkout Session for the remaining balance."""
    if current_user.is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None or booking.client_id != current_user.client.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Final payment can only be made on completed bookings (current: {booking.status})",
        )
    if payment_manager.deposit_succeeded_for_booking(db, booking.id) is None:
        raise HTTPException(status_code=409, detail="Deposit has not been paid")
    if payment_manager.final_succeeded_for_booking(db, booking.id) is not None:
        raise HTTPException(status_code=409, detail="Final payment already made")

    remaining = booking.total_cents - booking.deposit_cents
    if remaining <= 0:
        raise HTTPException(status_code=409, detail="Nothing left to pay")

    existing = payment_manager.latest_pending_final(db, booking.id)
    if existing and existing.stripe_checkout_session_id:
        try:
            session = stripe_service.retrieve_checkout_session(
                existing.stripe_checkout_session_id
            )
            if session.get("status") == "open" and session.get("url"):
                return {
                    "booking": booking_manager.get_by_id(db, booking.id),
                    "checkout_url": session["url"],
                    "remaining_cents": remaining,
                    "reused": True,
                }
        except Exception as e:
            print(f"[payments] could not reuse final session: {e}")

    try:
        session = stripe_service.create_final_checkout_session(
            booking_id=booking.id,
            amount_cents=remaining,
            product_name=f"Balance — {booking.service.name} booking #{booking.id}",
            customer_email=current_user.email,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"[payments] stripe final session create failed: {e}")
        raise HTTPException(status_code=502, detail="Could not create checkout session")

    payment_manager.create_pending_final(
        db, booking_id=booking.id, amount_cents=remaining, session_id=session["id"]
    )
    return {
        "booking": booking_manager.get_by_id(db, booking.id),
        "checkout_url": session["url"],
        "remaining_cents": remaining,
        "reused": False,
    }


@router.post("/refund/{booking_id}")
def refund(
    booking_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Admin: refund the deposit for a booking. Idempotent.

    Use cases: disputes, goodwill, correcting a bad auto-refund decision.
    """
    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if payment_manager.has_succeeded_refund(db, booking.id):
        raise HTTPException(status_code=409, detail="Deposit already refunded")
    if payment_manager.latest_pending_refund(db, booking.id) is not None:
        raise HTTPException(status_code=409, detail="A refund is already in progress")
    if payment_manager.deposit_succeeded_for_booking(db, booking.id) is None:
        raise HTTPException(status_code=409, detail="No succeeded deposit to refund")

    result = refund_deposit_for_booking(db, booking, initiated_by="admin")
    if not result.get("refunded"):
        if result.get("reason") == "stripe_error":
            raise HTTPException(
                status_code=502,
                detail=f"Refund failed: {result.get('error', 'unknown')}",
            )
        raise HTTPException(
            status_code=409, detail=result.get("reason", "Refund not issued")
        )

    return {
        "booking": serialize_booking(booking_manager.get_by_id(db, booking.id)),
        "refund": result,
    }


@router.post("/connect/onboard")
def connect_onboard():
    """Stripe Connect Express onboarding. Implemented in Phase 5.4."""
    raise HTTPException(status_code=501, detail="Not implemented until Phase 5.4")


# ═══════════════════════════════════════════════════════════
# Webhook
# ═══════════════════════════════════════════════════════════

@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Stripe webhook receiver. Single source of truth for payment state."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = stripe_service.construct_webhook_event(payload, sig_header)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"[stripe-webhook] signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event["id"]
    event_type = event["type"]

    if not payment_manager.try_claim_event(db, event_id, event_type):
        print(f"[stripe-webhook] duplicate event {event_id} ({event_type}) — ack")
        return {"received": True, "duplicate": True}

    try:
        _dispatch_event(db, event_type, event["data"]["object"])
    except Exception as e:
        print(f"[stripe-webhook] handler failed for {event_id}: {e}")
        payment_manager.release_event(db, event_id)
        raise HTTPException(status_code=500, detail="Webhook handler failed")

    print(f"[stripe-webhook] processed {event_type} {event_id}")
    return {"received": True}


def _dispatch_event(db: Session, event_type: str, obj: dict) -> None:
    if event_type in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        _handle_checkout_completed(db, obj)
        return
    if event_type == "payment_intent.succeeded":
        _handle_pi_succeeded(db, obj)
        return
    if event_type == "payment_intent.payment_failed":
        _handle_pi_failed(db, obj)
        return
    if event_type == "charge.refunded":
        _handle_charge_refunded(db, obj)
        return
    print(f"[stripe-webhook] unhandled event type {event_type} (ack)")


def _handle_pi_succeeded(db: Session, pi: dict) -> None:
    booking_id = _booking_id_from_pi(db, pi["id"])
    if booking_id is None:
        print(f"[stripe-webhook] no tx for pi {pi['id']} — checkout handler will process")
        return
    kind = (pi.get("metadata") or {}).get("kind")
    if kind == "final":
        payment_manager.mark_final_succeeded(
            db, booking_id=booking_id, payment_intent_id=pi["id"]
        )
    else:
        payment_manager.mark_deposit_succeeded(
            db, booking_id=booking_id, payment_intent_id=pi["id"]
        )


def _handle_pi_failed(db: Session, pi: dict) -> None:
    kind = (pi.get("metadata") or {}).get("kind")
    if kind == "final":
        payment_manager.mark_final_failed(db, pi["id"])
    else:
        payment_manager.mark_deposit_failed(db, pi["id"])


def _handle_charge_refunded(db: Session, charge: dict) -> None:
    pi_id = charge.get("payment_intent")
    if not pi_id:
        print("[stripe-webhook] charge.refunded without payment_intent — skip")
        return

    tx = payment_manager.find_pending_refund_by_pi(db, pi_id)
    if tx is None:
        print(
            f"[stripe-webhook] charge.refunded for pi {pi_id}: no pending refund tx — "
            "already processed or manual"
        )
        return

    payment_manager.mark_refund_succeeded(db, tx.id)

    booking = booking_manager.get_by_id(db, tx.booking_id)
    if booking and booking.status == "cancelled":
        booking = booking_manager.set_status(db, booking, "refunded")

    if booking and booking.client:
        notification_manager.create(
            db,
            user_id=booking.client.user_id,
            kind="refund_processed",
            title="Deposit refunded",
            body=(
                f"Your ${(tx.amount_cents / 100):.2f} deposit for booking "
                f"#{booking.id} has been refunded."
            ),
            data={"booking_id": booking.id},
        )

    print(
        f"[stripe-webhook] refund for booking {booking.id if booking else '?'} "
        f"(pi {pi_id}) → succeeded"
    )


def _booking_id_from_pi(db: Session, payment_intent_id: str) -> int | None:
    from app.models.transaction import Transaction

    tx = (
        db.query(Transaction)
        .filter(
            Transaction.stripe_payment_intent_id == payment_intent_id,
            Transaction.kind == "deposit",
        )
        .first()
    )
    return tx.booking_id if tx else None


def _handle_checkout_completed(db: Session, session: dict) -> None:
    metadata = session.get("metadata") or {}
    kind = metadata.get("kind") or "deposit"
    booking_id_raw = metadata.get("booking_id") or session.get("client_reference_id")
    if not booking_id_raw:
        print("[stripe-webhook] checkout session missing booking_id — skip")
        return
    try:
        booking_id = int(booking_id_raw)
    except (TypeError, ValueError):
        print(f"[stripe-webhook] bad booking_id {booking_id_raw!r} — skip")
        return

    if session.get("payment_status") != "paid":
        print(f"[stripe-webhook] checkout {session.get('id')} not paid yet — wait")
        return

    booking = booking_manager.get_by_id(db, booking_id)
    if booking is None:
        print(f"[stripe-webhook] booking {booking_id} not found")
        return

    if kind == "final":
        _handle_final_paid(db, booking, session)
    else:
        _handle_deposit_paid(db, booking, session)


def _handle_deposit_paid(db: Session, booking, session: dict) -> None:
    payment_manager.mark_deposit_succeeded(
        db, booking_id=booking.id, payment_intent_id=session.get("payment_intent")
    )
    if booking.status != "draft":
        print(f"[stripe-webhook] booking {booking.id} already {booking.status} — no-op")
        return
    booking = booking_manager.set_status(db, booking, "pending")

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
    print(
        f"[stripe-webhook] booking {booking.id} → pending; notified {len(matches)} movers"
    )


def _handle_final_paid(db: Session, booking, session: dict) -> None:
    payment_manager.mark_final_succeeded(
        db, booking_id=booking.id, payment_intent_id=session.get("payment_intent")
    )
    if booking.client:
        notification_manager.create(
            db,
            user_id=booking.client.user_id,
            kind="final_payment_received",
            title="Final payment received",
            body=f"Payment for booking #{booking.id} is complete.",
            data={"booking_id": booking.id},
        )
    if booking.mover_id and booking.mover:
        notification_manager.create(
            db,
            user_id=booking.mover.user_id,
            kind="job_paid",
            title="Client paid the balance",
            body=f"Booking #{booking.id} is fully paid.",
            data={"booking_id": booking.id},
        )
    print(f"[stripe-webhook] booking {booking.id} final payment → succeeded")