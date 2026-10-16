"""User model — the single source of identity for both sides of the marketplace."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String

from app.core.database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now, used as a column default."""
    return datetime.now(timezone.utc)


class User(Base):
    """An authenticated account. Role is the signup role; profiles are separate tables."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(30), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False)  # client | mover | admin
    phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    strikes = Column(Integer, nullable=False, default=0)
    is_blocked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    __table_args__ = (
        CheckConstraint("role in ('client','mover','admin')", name="ck_users_role"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email} role={self.role}>"