"""Strike records."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from app.core.database import Base
from app.models.mixins import utcnow


class Strike(Base):
    """A strike issued against a user. Three strikes → blocked.

    `booking_id` is null for manual admin strikes without a specific booking.
    `created_by_id` is null for system-issued strikes (cancellation policy);
    non-null when an admin issued it manually.
    """

    __tablename__ = "strikes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True, index=True)
    reason = Column(Text, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)