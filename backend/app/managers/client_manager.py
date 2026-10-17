"""DB logic for clients."""
from sqlalchemy.orm import Session

from app.models.client import Client


def get_for_user(db: Session, user_id: int) -> Client | None:
    return db.query(Client).filter(Client.user_id == user_id).first()


def create_for_user(db: Session, user_id: int) -> Client:
    c = Client(user_id=user_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_default_address(db: Session, client: Client, *, address, lat, lng) -> Client:
    client.default_address = address
    client.default_lat = lat
    client.default_lng = lng
    db.commit()
    db.refresh(client)
    return client