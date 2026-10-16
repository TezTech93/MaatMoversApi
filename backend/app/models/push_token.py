"""Expo push tokens. Extension to the original schema — required by /notifications/register-token."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import utcnow


class PushToken(Base):
    """A device push token for a user."""

    __tablename__ = "push_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    platform = Column(String(16), nullable=True)  # ios | android | web
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)