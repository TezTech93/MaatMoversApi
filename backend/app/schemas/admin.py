"""Request bodies for /admin/* routes."""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

VALID_PERMISSIONS = {
    # movers
    "movers.view", "movers.edit", "movers.block", "movers.delete",
    # clients
    "clients.view", "clients.edit", "clients.block", "clients.delete",
    # services
    "services.view", "services.create", "services.edit", "services.delete",
    # bookings
    "bookings.view", "bookings.edit", "bookings.cancel",
    # transactions
    "transactions.view", "transactions.refund", "transactions.payout",
    # strikes
    "strikes.view", "strikes.create", "strikes.delete", "strikes.clear",
    # escalations
    "escalations.create", "escalations.view", "escalations.resolve",
}


class CreateManagerRequest(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    permissions: list[str] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def _username_format(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars: letters, digits, underscore")
        return v

    @field_validator("permissions")
    @classmethod
    def _perms_valid(cls, v: list[str]) -> list[str]:
        unknown = set(v) - VALID_PERMISSIONS
        if unknown:
            raise ValueError(f"Unknown permissions: {sorted(unknown)}")
        return sorted(set(v))


class UpdateManagerRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    phone: str | None = None
    permissions: list[str] | None = None

    @field_validator("username")
    @classmethod
    def _username_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars: letters, digits, underscore")
        return v

    @field_validator("permissions")
    @classmethod
    def _perms_valid(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        unknown = set(v) - VALID_PERMISSIONS
        if unknown:
            raise ValueError(f"Unknown permissions: {sorted(unknown)}")
        return sorted(set(v))

# ── Movers / clients ────────────────────────────────────────

class AdminUpdateMoverRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    phone: str | None = None
    service_radius_miles: int | None = Field(default=None, ge=1, le=25)
    home_address: str | None = Field(default=None, max_length=500)
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lng: float | None = Field(default=None, ge=-180, le=180)
    bio: str | None = None

    @field_validator("username")
    @classmethod
    def _username_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars: letters, digits, underscore")
        return v


class AdminVerifyMoverRequest(BaseModel):
    status: str  # 'approved' | 'rejected' | 'pending'

    @field_validator("status")
    @classmethod
    def _status_valid(cls, v: str) -> str:
        if v not in ("approved", "rejected", "pending"):
            raise ValueError("status must be approved, rejected, or pending")
        return v


class AdminUpdateClientRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    phone: str | None = None
    default_address: str | None = Field(default=None, max_length=500)
    default_lat: float | None = Field(default=None, ge=-90, le=90)
    default_lng: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("username")
    @classmethod
    def _username_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars: letters, digits, underscore")
        return v


class AdminBlockUserRequest(BaseModel):
    blocked: bool


# ── Strikes ─────────────────────────────────────────────────

class CreateStrikeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    booking_id: int | None = None


# ── Escalations ─────────────────────────────────────────────

class CreateEscalationRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=5000)
    related_user_id: int | None = None
    related_booking_id: int | None = None


class ResolveEscalationRequest(BaseModel):
    status: str = "resolved"  # 'in_progress' | 'resolved' | 'open'

    @field_validator("status")
    @classmethod
    def _status_valid(cls, v: str) -> str:
        if v not in ("open", "in_progress", "resolved"):
            raise ValueError("status must be open, in_progress, or resolved")
        return v