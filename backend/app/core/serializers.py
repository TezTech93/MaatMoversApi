"""Response serializers. Routers return plain dicts; these functions produce them."""
import json

from app.models.booking import Booking
from app.models.client import Client
from app.models.mover import Mover
from app.models.notification import Notification
from app.models.service import Service
from app.models.user import User


def _iso(dt):
    return dt.isoformat() if dt else None


def serialize_user(user: User) -> dict:
    """Public shape of a user, matching the Phase 1 contract."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "phone": user.phone,
        "is_active": user.is_active,
        "strikes": user.strikes,
        "is_blocked": user.is_blocked,
        "created_at": _iso(user.created_at),
        "updated_at": _iso(user.updated_at),
        "mover_profile": serialize_mover(user.mover) if user.mover else None,
        "client_profile": serialize_client(user.client) if user.client else None,
    }


def serialize_mover(m: Mover) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "service_radius_miles": m.service_radius_miles,
        "home_address": m.home_address,
        "home_lat": m.home_lat,
        "home_lng": m.home_lng,
        "bio": m.bio,
        "verification_status": m.verification_status,
        "stripe_connect_id": m.stripe_connect_id,
        "stripe_connect_charges_enabled": m.stripe_connect_charges_enabled,
        "stripe_connect_payouts_enabled": m.stripe_connect_payouts_enabled,
        "stripe_connect_details_submitted": m.stripe_connect_details_submitted,
        "stripe_connect_onboarded_at": _iso(m.stripe_connect_onboarded_at),
        "created_at": _iso(m.created_at),
    }


def serialize_client(c: Client) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "default_address": c.default_address,
        "default_lat": c.default_lat,
        "default_lng": c.default_lng,
        "stripe_customer_id": c.stripe_customer_id,
        "created_at": _iso(c.created_at),
    }


def serialize_service(s: Service) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "base_price_cents": s.base_price_cents,
        "per_mile_cents": s.per_mile_cents,
        "estimated_duration_minutes": s.estimated_duration_minutes,
        "is_active": s.is_active,
    }


def serialize_booking(b: Booking) -> dict:
    return {
        "id": b.id,
        "client_id": b.client_id,
        "mover_id": b.mover_id,
        "service_id": b.service_id,
        "status": b.status,
        "pickup_address": b.pickup_address,
        "pickup_lat": b.pickup_lat,
        "pickup_lng": b.pickup_lng,
        "dropoff_address": b.dropoff_address,
        "dropoff_lat": b.dropoff_lat,
        "dropoff_lng": b.dropoff_lng,
        "scheduled_at": _iso(b.scheduled_at),
        "distance_miles": b.distance_miles,
        "total_cents": b.total_cents,
        "deposit_cents": b.deposit_cents,
        "cancelled_at": _iso(b.cancelled_at),
        "cancellation_reason": b.cancellation_reason,
        "created_at": _iso(b.created_at),
        "updated_at": _iso(b.updated_at),
        "service": serialize_service(b.service) if b.service else None,
    }


def serialize_notification(n: Notification) -> dict:
    data = None
    if n.data_json:
        try:
            data = json.loads(n.data_json)
        except (ValueError, TypeError):
            data = None
    return {
        "id": n.id,
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "data": data,
        "read": n.is_read,
        "created_at": _iso(n.created_at),
    }