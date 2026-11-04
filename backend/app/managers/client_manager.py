"""DB logic for clients."""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.client import Client


def get_for_user(db: Session, user_id: int) -> Client | None:
    return db.query(Client).filter(Client.user_id == user_id).first()


def get_by_id(db: Session, client_id: int) -> Client | None:
    return db.query(Client).filter(Client.id == client_id).first()


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


def update_profile(
    db: Session,
    client: Client,
    *,
    default_address=None,
    default_lat=None,
    default_lng=None,
) -> Client:
    if default_address is not None:
        client.default_address = default_address
    if default_lat is not None:
        client.default_lat = default_lat
    if default_lng is not None:
        client.default_lng = default_lng
    db.commit()
    db.refresh(client)
    return client


def list_admin(
    db: Session,
    *,
    q: str | None = None,
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 25,
):
    """Admin list with search and pagination. Returns (rows, total)."""
    from app.models.user import User

    base = db.query(Client).join(User, User.id == Client.user_id)
    if not include_inactive:
        base = base.filter(User.is_active.is_(True))
    if q:
        pattern = f"%{q.lower()}%"
        base = base.filter(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    total = base.count()
    offset = (page - 1) * page_size
    rows = base.order_by(Client.created_at.desc()).offset(offset).limit(page_size).all()
    return rows, total