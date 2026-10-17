"""Request bodies for /clients."""
from pydantic import BaseModel


class UpdateClientRequest(BaseModel):
    default_address: str | None = None
    default_lat: float | None = None
    default_lng: float | None = None