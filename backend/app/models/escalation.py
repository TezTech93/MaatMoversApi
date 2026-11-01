"""Escalations raised by managers for supreme admins to resolve."""
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.mixins import utcnow


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True)
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    related_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    related_booking_id = Column(
        Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(String(16), nullable=False, default="open")
    resolved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "status in ('open','in_progress','resolved')",
            name="ck_escalations_status",
        ),
    )