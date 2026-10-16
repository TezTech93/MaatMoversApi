"""Strike records."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from app.core.database import Base
from app.models.mixins import utcnow


class Strike(Base):
    """A strike issued against a user. Three strikes → blocked."""

    __tablename__ = "strikes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)