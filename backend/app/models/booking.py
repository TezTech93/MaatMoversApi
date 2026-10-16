"""Booking model."""
from sqlalchemy import (
    CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import utcnow


class Booking(Base):
    """A move requested by a client and (eventually) accepted by a mover."""

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    mover_id = Column(Integer, ForeignKey("movers.id"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)

    status = Column(String(16), nullable=False, default="draft")
    pickup_address = Column(String(500), nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    dropoff_address = Column(String(500), nullable=False)
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)

    distance_miles = Column(Float, nullable=False)
    total_cents = Column(Integer, nullable=False)
    deposit_cents = Column(Integer, nullable=False, default=1000)

    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    service = relationship("Service")

    __table_args__ = (
        CheckConstraint(
            "status in ('draft','pending','accepted','in_progress','completed','cancelled','refunded')",
            name="ck_bookings_status",
        ),
    )