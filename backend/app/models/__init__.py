"""Importing every model here ensures Alembic autogenerate sees them all."""
from app.models.user import User  # noqa: F401
from app.models.mover import Mover  # noqa: F401
from app.models.client import Client  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.booking import Booking  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.strike import Strike  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.push_token import PushToken  # noqa: F401
from app.models.processed_event import ProcessedEvent  # noqa: F401