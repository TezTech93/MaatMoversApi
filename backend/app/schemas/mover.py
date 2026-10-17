"""Request bodies for /movers."""
from pydantic import BaseModel, Field


class BecomeMoverRequest(BaseModel):
    service_radius_miles: int = Field(ge=1, le=25)
    home_address: str = Field(min_length=1, max_length=500)
    home_lat: float
    home_lng: float
    bio: str | None = None


class UpdateMoverRequest(BaseModel):
    service_radius_miles: int | None = Field(default=None, ge=1, le=25)
    bio: str | None = None
    home_address: str | None = None
    home_lat: float | None = None
    home_lng: float | None = None


class DeclineRequest(BaseModel):
    reason: str | None = None