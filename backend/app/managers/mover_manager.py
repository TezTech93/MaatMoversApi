"""DB logic for movers."""
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.models.mover import Mover


def get_for_user(db: Session, user_id: int) -> Mover | None:
    return db.query(Mover).filter(Mover.user_id == user_id).first()


def get_by_id(db: Session, mover_id: int) -> Mover | None:
    return db.query(Mover).filter(Mover.id == mover_id).first()


def get_by_stripe_connect_id(db: Session, account_id: str) -> Mover | None:
    if not account_id:
        return None
    return db.query(Mover).filter(Mover.stripe_connect_id == account_id).first()


def create_for_user(
    db: Session,
    user_id: int,
    *,
    service_radius_miles,
    home_address,
    home_lat,
    home_lng,
    bio,
) -> Mover:
    m = Mover(
        user_id=user_id,
        service_radius_miles=service_radius_miles,
        home_address=home_address,
        home_lat=home_lat,
        home_lng=home_lng,
        bio=bio,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def update_profile(
    db: Session,
    mover: Mover,
    *,
    service_radius_miles=None,
    bio=None,
    home_address=None,
    home_lat=None,
    home_lng=None,
) -> Mover:
    if service_radius_miles is not None:
        mover.service_radius_miles = service_radius_miles
    if bio is not None:
        mover.bio = bio
    if home_address is not None:
        mover.home_address = home_address
    if home_lat is not None:
        mover.home_lat = home_lat
    if home_lng is not None:
        mover.home_lng = home_lng
    db.commit()
    db.refresh(mover)
    return mover


def set_stripe_connect_account(db: Session, mover: Mover, account_id: str) -> Mover:
    mover.stripe_connect_id = account_id
    db.commit()
    db.refresh(mover)
    return mover


def update_connect_status(
    db: Session,
    mover: Mover,
    *,
    charges_enabled: bool,
    payouts_enabled: bool,
    details_submitted: bool,
) -> Mover:
    mover.stripe_connect_charges_enabled = bool(charges_enabled)
    mover.stripe_connect_payouts_enabled = bool(payouts_enabled)
    mover.stripe_connect_details_submitted = bool(details_submitted)
    db.commit()
    db.refresh(mover)
    return mover


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in miles between two coordinates."""
    R = 3958.7613
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    return 2 * R * asin(sqrt(a))


def find_available(db: Session, *, lat: float, lng: float, radius_miles: int):
    """Return (mover, distance_miles) for approved movers covering the point."""
    movers = (
        db.query(Mover)
        .filter(Mover.verification_status == "approved")
        .all()
    )
    out = []
    for m in movers:
        d = haversine_miles(lat, lng, m.home_lat, m.home_lng)
        if d <= m.service_radius_miles and d <= radius_miles:
            out.append((m, d))
    out.sort(key=lambda x: x[1])
    return out