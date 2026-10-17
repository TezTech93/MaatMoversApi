"""Request bodies for /notifications."""
from pydantic import BaseModel


class RegisterTokenRequest(BaseModel):
    token: str
    platform: str | None = None