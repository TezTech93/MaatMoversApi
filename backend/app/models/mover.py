"""Mover profile."""
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer,
    String, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import utcnow


class Mover(Base):
    """A user acting as a mover. One-to-one with User."""

    __tablename__ = "movers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    service_radius_miles = Column(Integer, nullable=False)
    home_address = Column(String(500), nullable=False)
    home_lat = Column(Float, nullable=False)
    home_lng = Column(Float, nullable=False)
    bio = Column(Text, nullable=True)
    verification_status = Column(String(16), nullable=False, default="pending")

    # Stripe Connect Express
    stripe_connect_id = Column(String(64), nullable=True, unique=True, index=True)
    stripe_connect_charges_enabled = Column(Boolean, nullable=False, default=False)
    stripe_connect_payouts_enabled = Column(Boolean, nullable=False, default=False)
    stripe_connect_details_submitted = Column(Boolean, nullable=False, default=False)
    stripe_connect_onboarded_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="mover")

    __table_args__ = (
        CheckConstraint(
            "service_radius_miles >= 1 AND service_radius_miles <= 25",
            name="ck_movers_radius",
        ),
        CheckConstraint(
            "verification_status in ('pending','approved','rejected')",
            name="ck_movers_verification",
        ),
    )