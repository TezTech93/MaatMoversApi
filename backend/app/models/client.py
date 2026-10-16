"""Client profile."""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import utcnow


class Client(Base):
    """A user acting as a client. One-to-one with User."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    default_address = Column(String(500), nullable=True)
    default_lat = Column(Float, nullable=True)
    default_lng = Column(Float, nullable=True)
    stripe_customer_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="client")