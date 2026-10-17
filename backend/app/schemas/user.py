"""Request bodies for /users."""
from pydantic import BaseModel, Field


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)