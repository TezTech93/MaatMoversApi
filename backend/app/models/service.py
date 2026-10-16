"""Service catalog."""
from sqlalchemy import Boolean, Column, Integer, String, Text

from app.core.database import Base


class Service(Base):
    """A bookable service (Local Move, Long Distance, etc.)."""

    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    base_price_cents = Column(Integer, nullable=False)
    per_mile_cents = Column(Integer, nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)