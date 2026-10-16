"""User model — the single source of identity for both sides of the marketplace."""
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import utcnow


class User(Base):
    """An authenticated account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(30), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False)
    phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    strikes = Column(Integer, nullable=False, default=0)
    is_blocked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    mover = relationship("Mover", back_populates="user", uselist=False)
    client = relationship("Client", back_populates="user", uselist=False)

    __table_args__ = (
        CheckConstraint("role in ('client','mover','admin')", name="ck_users_role"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email} role={self.role}>"