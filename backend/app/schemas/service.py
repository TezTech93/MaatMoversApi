"""Request bodies for /services (admin only)."""
from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    base_price_cents: int = Field(ge=0)
    per_mile_cents: int = Field(ge=0)
    estimated_duration_minutes: int = Field(gt=0)
    is_active: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price_cents: int | None = Field(default=None, ge=0)
    per_mile_cents: int | None = Field(default=None, ge=0)
    estimated_duration_minutes: int | None = Field(default=None, gt=0)
    is_active: bool | None = None