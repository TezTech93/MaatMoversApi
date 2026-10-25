"""Stripe webhook event dedup table."""
from sqlalchemy import Column, DateTime, String

from app.core.database import Base
from app.models.mixins import utcnow


class ProcessedEvent(Base):
    """One row per Stripe event.id that has been processed (or is being processed)."""

    __tablename__ = "processed_events"

    event_id = Column(String(128), primary_key=True)
    event_type = Column(String(64), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)