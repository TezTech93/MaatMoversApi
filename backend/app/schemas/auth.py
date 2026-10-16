"""Pydantic request bodies for auth routes. Responses are plain dicts."""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


class RegisterRequest(BaseModel):
    """Request body for POST /auth/register."""

    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=128)
    role: str  # client | mover
    phone: str | None = None

    @field_validator("username")
    @classmethod
    def _username_format(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars: letters, digits, underscore")
        return v

    @field_validator("role")
    @classmethod
    def _role_allowed(cls, v: str) -> str:
        if v not in ("client", "mover"):
            raise ValueError("role must be 'client' or 'mover'")
        return v


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str