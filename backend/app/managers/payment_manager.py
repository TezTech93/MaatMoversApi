"""DB logic for transactions and processed webhook events."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.processed_event import ProcessedEvent
from app.models.transaction import Transaction


# ── Deposits ──────────────────────────────────────────────

def create_pending_deposit(
    db: Session, *, booking_id: int, amount_cents: int, session_id: str
) -> Transaction:
    tx = Transaction(
        booking_id=booking_id,
        amount_cents=amount_cents,
        currency="usd",
        kind="deposit",
        status="pending",
        stripe_checkout_session_id=session_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def latest_pending_deposit(db: Session, booking_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.booking_id == booking_id,
            Transaction.kind == "deposit",
            Transaction.status == "pending",
        )
        .order_by(Transaction.id.desc())
        .first()
    )


def deposit_succeeded_for_booking(db: Session, booking_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.booking_id == booking_id,
            Transaction.kind == "deposit",
            Transaction.status == "succeeded",
        )
        .order_by(Transaction.id.desc())
        .first()
    )


def mark_deposit_succeeded(
    db: Session, booking_id: int, payment_intent_id: str | None
) -> Transaction | None:
    tx = latest_pending_deposit(db, booking_id)
    if tx is None:
        return None
    tx.status = "succeeded"
    if payment_intent_id:
        tx.stripe_payment_intent_id = payment_intent_id
    db.commit()
    db.refresh(tx)
    return tx


def mark_deposit_failed(db: Session, payment_intent_id: str) -> Transaction | None:
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.kind == "deposit",
            Transaction.stripe_payment_intent_id == payment_intent_id,
            Transaction.status == "pending",
        )
        .first()
    )
    if tx is None:
        return None
    tx.status = "failed"
    db.commit()
    db.refresh(tx)
    return tx


# ── Finals ───────────────────────────────────────────────

def create_pending_final(
    db: Session, *, booking_id: int, amount_cents: int, session_id: str
) -> Transaction:
    tx = Transaction(
        booking_id=booking_id,
        amount_cents=amount_cents,
        currency="usd",
        kind="final",
        status="pending",
        stripe_checkout_session_id=session_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def latest_pending_final(db: Session, booking_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.booking_id == booking_id,
            Transaction.kind == "final",
            Transaction.status == "pending",
        )
        .order_by(Transaction.id.desc())
        .first()
    )


def final_succeeded_for_booking(db: Session, booking_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.booking_id == booking_id,
            Transaction.kind == "final",
            Transaction.status == "succeeded",
        )
        .order_by(Transaction.id.desc())
        .first()
    )


def mark_final_succeeded(
    db: Session, booking_id: int, payment_intent_id: str | None
) -> Transaction | None:
    tx = latest_pending_final(db, booking_id)
    if tx is None:
        return None
    tx.status = "succeeded"
    if payment_intent_id:
        tx.stripe_payment_intent_id = payment_intent_id
    db.commit()
    db.refresh(tx)
    return tx


def mark_final_failed(db: Session, payment_intent_id: str) -> Transaction | None:
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.kind == "final",
            Transaction.stripe_payment_intent_id == payment_intent_id,
            Transaction.status == "pending",
        )
        .first()
    )
    if tx is None:
        return None
    tx.status = "failed"
    db.commit()
    db.refresh(tx)
    return tx


# ── Refunds ──────────────────────────────────────────────

def create_pending_refund(
    db: Session, *, booking_id: int, amount_cents: int, payment_intent_id: str
) -> Transaction:
    """Create a pending refund row. Sets stripe_payment_intent_id to the
    deposit's PI so charge.refunded can locate this row."""
    tx = Transaction(
        booking_id=booking_id,
        amount_cents=amount_cents,
        currency="usd",
        kind="refund",
        status="pending",
        stripe_payment_intent_id=payment_intent_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def latest_pending_refund(db: Session, booking_id: int) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.booking_id == booking_id,
            Transaction.kind == "refund",
            Transaction.status == "pending",
        )
        .order_by(Transaction.id.desc())
        .first()
    )


def has_succeeded_refund(db: Session, booking_id: int) -> bool:
    return (
        db.query(Transaction)
        .filter(
            Transaction.booking_id == booking_id,
            Transaction.kind == "refund",
            Transaction.status == "succeeded",
        )
        .first()
        is not None
    )


def find_pending_refund_by_pi(
    db: Session, payment_intent_id: str
) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.kind == "refund",
            Transaction.stripe_payment_intent_id == payment_intent_id,
            Transaction.status == "pending",
        )
        .order_by(Transaction.id.desc())
        .first()
    )


def mark_refund_succeeded(db: Session, tx_id: int) -> Transaction | None:
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if tx is None:
        return None
    tx.status = "succeeded"
    db.commit()
    db.refresh(tx)
    return tx


def mark_refund_failed(db: Session, tx_id: int) -> Transaction | None:
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if tx is None:
        return None
    tx.status = "failed"
    db.commit()
    db.refresh(tx)
    return tx


# ── Webhook event dedup ──────────────────────────────────

def try_claim_event(db: Session, event_id: str, event_type: str) -> bool:
    row = ProcessedEvent(event_id=event_id, event_type=event_type)
    db.add(row)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def release_event(db: Session, event_id: str) -> None:
    row = db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
    if row is not None:
        db.delete(row)
        db.commit()