"""Request bodies for /bookings."""
from datetime import datetime

from pydantic import BaseModel, Field


class CreateBookingRequest(BaseModel):
    service_id: int
    pickup_address: str = Field(min_length=1, max_length=500)
    pickup_lat: float
    pickup_lng: float
    dropoff_address: str = Field(min_length=1, max_length=500)
    dropoff_lat: float
    dropoff_lng: float
    scheduled_at: datetime


class CancelBookingRequest(BaseModel):
    reason: str | None = None