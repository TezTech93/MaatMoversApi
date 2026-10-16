"""Transaction ledger."""
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import utcnow


class Transaction(Base):
    """A money movement tied to a booking. Populated by Stripe webhooks in Phase 5."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    stripe_payment_intent_id = Column(String(128), nullable=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="usd")
    kind = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("kind in ('deposit','final','refund','payout')", name="ck_tx_kind"),
        CheckConstraint("status in ('pending','succeeded','failed','refunded')", name="ck_tx_status"),
    )