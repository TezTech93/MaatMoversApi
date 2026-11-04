"""Admin routes.

Phase 6.1: manager CRUD.
Phase 6.2: movers, clients, strikes, escalations.
Phase 6.3: services, bookings, transactions.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_permission
from app.core.serializers import (
    serialize_booking,
    serialize_client,
    serialize_escalation,
    serialize_manager,
    serialize_mover,
    serialize_strike,
    serialize_user,
)
from app.managers import (
    booking_manager,
    client_manager,
    escalation_manager,
    mover_manager,
    notification_manager,
    strike_manager,
    user_manager,
)
from app.models.booking import Booking
from app.models.user import User
from app.schemas.admin import (
    AdminBlockUserRequest,
    AdminUpdateClientRequest,
    AdminUpdateMoverRequest,
    AdminVerifyMoverRequest,
    CreateEscalationRequest,
    CreateManagerRequest,
    CreateStrikeRequest,
    ResolveEscalationRequest,
    UpdateManagerRequest,
)


router = APIRouter(prefix="/admin", tags=["admin"])


# ═══════════════════════════════════════════════════════════
# Managers (supreme admin only)
# ═══════════════════════════════════════════════════════════

@router.get("/managers")
def list_managers(
    include_inactive: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Supreme admin: list managers."""
    rows = user_manager.list_managers(db, include_inactive=include_inactive)
    return {"managers": [serialize_manager(u) for u in rows]}


@router.post("/managers", status_code=201)
def create_manager(
    payload: CreateManagerRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Supreme admin: create a new manager with explicit permissions."""
    if user_manager.get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if user_manager.get_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    manager = user_manager.create_manager(
        db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        phone=payload.phone,
        permissions=payload.permissions,
    )
    print(f"[admin] created manager id={manager.id} email={manager.email}")
    return {"manager": serialize_manager(manager)}


@router.get("/managers/{manager_id}")
def get_manager(
    manager_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    manager = user_manager.get_by_id(db, manager_id)
    if manager is None or manager.role != "manager":
        raise HTTPException(status_code=404, detail="Manager not found")
    return {"manager": serialize_manager(manager)}


@router.put("/managers/{manager_id}")
def update_manager(
    manager_id: int,
    payload: UpdateManagerRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    manager = user_manager.get_by_id(db, manager_id)
    if manager is None or manager.role != "manager":
        raise HTTPException(status_code=404, detail="Manager not found")
    if payload.username is not None and payload.username != manager.username:
        existing = user_manager.get_by_username(db, payload.username)
        if existing and existing.id != manager.id:
            raise HTTPException(status_code=409, detail="Username already taken")
    manager = user_manager.update_manager(
        db,
        manager,
        username=payload.username,
        phone=payload.phone,
        permissions=payload.permissions,
    )
    return {"manager": serialize_manager(manager)}


@router.delete("/managers/{manager_id}", status_code=204)
def delete_manager(
    manager_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    manager = user_manager.get_by_id(db, manager_id)
    if manager is None or manager.role != "manager":
        raise HTTPException(status_code=404, detail="Manager not found")
    user_manager.delete_manager(db, manager)


# ═══════════════════════════════════════════════════════════
# Shared user actions (block / soft-delete)
# ═══════════════════════════════════════════════════════════

def _target_role_permission(user: User, action: str) -> str:
    """Return 'movers.{action}' or 'clients.{action}' based on target user role."""
    if user.mover is not None:
        return f"movers.{action}"
    if user.client is not None:
        return f"clients.{action}"
    raise HTTPException(status_code=400, detail="Target is not a mover or client")


@router.post("/users/{user_id}/block")
def block_user(
    user_id: int,
    payload: AdminBlockUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Block or unblock a user. Requires movers.block or clients.block."""
    target = user_manager.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    perm_key = _target_role_permission(target, "block")
    # Manually enforce (require_permission is fixed at route definition time)
    if current_user.role != "admin":
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Admin or manager required")
        granted = set(json.loads(current_user.permissions or "[]"))
        if perm_key not in granted:
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm_key}")

    target.is_blocked = payload.blocked
    db.commit()
    db.refresh(target)
    print(f"[admin] user {target.id} blocked={payload.blocked} by {current_user.id}")
    return {"user": serialize_user(target)}


@router.delete("/users/{user_id}", status_code=204)
def soft_delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete a user (is_active=false). Requires movers.delete or clients.delete."""
    target = user_manager.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete a supreme admin")

    perm_key = _target_role_permission(target, "delete")
    if current_user.role != "admin":
        if current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Admin or manager required")
        granted = set(json.loads(current_user.permissions or "[]"))
        if perm_key not in granted:
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm_key}")

    target.is_active = False
    db.commit()
    print(f"[admin] soft-deleted user {target.id} by {current_user.id}")


# ═══════════════════════════════════════════════════════════
# Movers
# ═══════════════════════════════════════════════════════════

@router.get("/movers")
def list_movers(
    q: str | None = None,
    verification_status: str | None = None,
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("movers.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Admin: paginated mover list with search and status filter."""
    rows, total = mover_manager.list_admin(
        db,
        q=q,
        verification_status=verification_status,
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
    )
    pages = (total + page_size - 1) // page_size
    return {
        "movers": [
            {
                **serialize_mover(m),
                "user": serialize_user(m.user) if m.user else None,
            }
            for m in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/movers/{mover_id}")
def get_mover(
    mover_id: int,
    current_user: User = Depends(require_permission("movers.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Admin: mover detail with recent bookings and strikes."""
    mover = mover_manager.get_by_id(db, mover_id)
    if mover is None:
        raise HTTPException(status_code=404, detail="Mover not found")

    recent = (
        db.query(Booking)
        .filter(Booking.mover_id == mover.id)
        .order_by(Booking.created_at.desc())
        .limit(10)
        .all()
    )
    strike_rows = strike_manager.list_for_user(db, mover.user_id)

    return {
        "mover": serialize_mover(mover),
        "user": serialize_user(mover.user),
        "recent_bookings": [serialize_booking(b) for b in recent],
        "strikes": [serialize_strike(s, u) for s, u in strike_rows],
    }


@router.put("/movers/{mover_id}")
def update_mover(
    mover_id: int,
    payload: AdminUpdateMoverRequest,
    current_user: User = Depends(require_permission("movers.edit")),
    db: Session = Depends(get_db),
) -> dict:
    """Admin: edit mover profile fields. Email is not editable here."""
    mover = mover_manager.get_by_id(db, mover_id)
    if mover is None:
        raise HTTPException(status_code=404, detail="Mover not found")

    if payload.username is not None and payload.username != mover.user.username:
        existing = user_manager.get_by_username(db, payload.username)
        if existing and existing.id != mover.user_id:
            raise HTTPException(status_code=409, detail="Username already taken")
        mover.user.username = payload.username
    if payload.phone is not None:
        mover.user.phone = payload.phone

    mover = mover_manager.update_profile(
        db,
        mover,
        service_radius_miles=payload.service_radius_miles,
        home_address=payload.home_address,
        home_lat=payload.home_lat,
        home_lng=payload.home_lng,
        bio=payload.bio,
    )
    db.refresh(mover.user)
    print(f"[admin] updated mover {mover.id} by {current_user.id}")
    return {"mover": serialize_mover(mover), "user": serialize_user(mover.user)}


@router.post("/movers/{mover_id}/verify")
def verify_mover(
    mover_id: int,
    payload: AdminVerifyMoverRequest,
    current_user: User = Depends(require_permission("movers.edit")),
    db: Session = Depends(get_db),
) -> dict:
    """Admin: approve, reject, or reset a mover's verification status."""
    mover = mover_manager.get_by_id(db, mover_id)
    if mover is None:
        raise HTTPException(status_code=404, detail="Mover not found")

    old = mover.verification_status
    mover = mover_manager.set_verification(db, mover, payload.status)
    print(f"[admin] mover {mover.id} verification {old} → {payload.status} by {current_user.id}")

    # Notify the mover on any status change
    if payload.status != old:
        label = {
            "approved": "Approved",
            "rejected": "Rejected",
            "pending": "Set back to pending",
        }.get(payload.status, payload.status.title())
        try:
            notification_manager.create(
                db,
                user_id=mover.user_id,
                kind="verification_update",
                title=f"Mover verification: {label}",
                body=f"Your mover profile has been {payload.status}.",
                data={"mover_id": mover.id},
            )
        except Exception as e:
            print(f"[admin] verification notification failed: {e}")

    return {"mover": serialize_mover(mover)}


# ═══════════════════════════════════════════════════════════
# Clients
# ═══════════════════════════════════════════════════════════

@router.get("/clients")
def list_clients(
    q: str | None = None,
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = client_manager.list_admin(
        db,
        q=q,
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
    )
    pages = (total + page_size - 1) // page_size
    return {
        "clients": [
            {
                **serialize_client(c),
                "user": serialize_user(c.user) if c.user else None,
            }
            for c in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/clients/{client_id}")
def get_client(
    client_id: int,
    current_user: User = Depends(require_permission("clients.view")),
    db: Session = Depends(get_db),
) -> dict:
    client = client_manager.get_by_id(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    recent = (
        db.query(Booking)
        .filter(Booking.client_id == client.id)
        .order_by(Booking.created_at.desc())
        .limit(10)
        .all()
    )
    strike_rows = strike_manager.list_for_user(db, client.user_id)

    return {
        "client": serialize_client(client),
        "user": serialize_user(client.user),
        "recent_bookings": [serialize_booking(b) for b in recent],
        "strikes": [serialize_strike(s, u) for s, u in strike_rows],
    }


@router.put("/clients/{client_id}")
def update_client(
    client_id: int,
    payload: AdminUpdateClientRequest,
    current_user: User = Depends(require_permission("clients.edit")),
    db: Session = Depends(get_db),
) -> dict:
    client = client_manager.get_by_id(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    if payload.username is not None and payload.username != client.user.username:
        existing = user_manager.get_by_username(db, payload.username)
        if existing and existing.id != client.user_id:
            raise HTTPException(status_code=409, detail="Username already taken")
        client.user.username = payload.username
    if payload.phone is not None:
        client.user.phone = payload.phone

    client = client_manager.update_profile(
        db,
        client,
        default_address=payload.default_address,
        default_lat=payload.default_lat,
        default_lng=payload.default_lng,
    )
    db.refresh(client.user)
    return {"client": serialize_client(client), "user": serialize_user(client.user)}


# ═══════════════════════════════════════════════════════════
# Strikes
# ═══════════════════════════════════════════════════════════

@router.get("/users/{user_id}/strikes")
def list_user_strikes(
    user_id: int,
    current_user: User = Depends(require_permission("strikes.view")),
    db: Session = Depends(get_db),
) -> dict:
    target = user_manager.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = strike_manager.list_for_user(db, user_id)
    return {
        "strikes": [serialize_strike(s, u) for s, u in rows],
        "current_strikes": target.strikes,
        "is_blocked": target.is_blocked,
    }


@router.post("/users/{user_id}/strikes", status_code=201)
def create_strike(
    user_id: int,
    payload: CreateStrikeRequest,
    current_user: User = Depends(require_permission("strikes.create")),
    db: Session = Depends(get_db),
) -> dict:
    target = user_manager.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.booking_id is not None:
        booking = booking_manager.get_by_id(db, payload.booking_id)
        if booking is None:
            raise HTTPException(status_code=400, detail="Booking not found")

    strike, blocked_now = strike_manager.create_manual(
        db,
        target=target,
        reason=payload.reason,
        created_by_id=current_user.id,
        booking_id=payload.booking_id,
    )
    print(f"[admin] manual strike user={target.id} strike={strike.id} by {current_user.id}")

    try:
        notification_manager.create(
            db,
            user_id=target.id,
            kind="strike_issued",
            title="A strike was added to your account",
            body=f"Reason: {payload.reason}. You now have {target.strikes} strike(s).",
            data={"strike_id": strike.id},
        )
    except Exception as e:
        print(f"[admin] strike notification failed: {e}")

    return {
        "strike": serialize_strike(strike, current_user.username),
        "current_strikes": target.strikes,
        "blocked_now": blocked_now,
    }


@router.delete("/strikes/{strike_id}", status_code=204)
def delete_strike(
    strike_id: int,
    current_user: User = Depends(require_permission("strikes.delete")),
    db: Session = Depends(get_db),
) -> None:
    strike = strike_manager.get_by_id(db, strike_id)
    if strike is None:
        raise HTTPException(status_code=404, detail="Strike not found")
    target = strike_manager.delete_strike(db, strike)
    print(f"[admin] deleted strike {strike_id} by {current_user.id}")
    if target is not None:
        try:
            notification_manager.create(
                db,
                user_id=target.id,
                kind="strike_removed",
                title="A strike was removed",
                body=f"You now have {target.strikes} strike(s).",
                data={},
            )
        except Exception as e:
            print(f"[admin] strike removal notification failed: {e}")


@router.post("/users/{user_id}/clear-strikes")
def clear_strikes(
    user_id: int,
    current_user: User = Depends(require_permission("strikes.clear")),
    db: Session = Depends(get_db),
) -> dict:
    target = user_manager.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    count = strike_manager.clear_for_user(db, target)
    print(f"[admin] cleared {count} strikes for user={user_id} by {current_user.id}")

    try:
        notification_manager.create(
            db,
            user_id=target.id,
            kind="strikes_cleared",
            title="Your strikes were cleared",
            body="A MaatMovers admin cleared your strikes and unblocked your account.",
            data={},
        )
    except Exception as e:
        print(f"[admin] clear-strikes notification failed: {e}")

    return {"cleared": count, "user": serialize_user(target)}


# ═══════════════════════════════════════════════════════════
# Escalations
# ═══════════════════════════════════════════════════════════

@router.get("/escalations")
def list_escalations(
    status: str | None = None,
    current_user: User = Depends(require_permission("escalations.view")),
    db: Session = Depends(get_db),
) -> dict:
    rows = escalation_manager.list_all(db, status=status)
    return {"escalations": [serialize_escalation(e) for e in rows]}


@router.post("/escalations", status_code=201)
def create_escalation(
    payload: CreateEscalationRequest,
    current_user: User = Depends(require_permission("escalations.create")),
    db: Session = Depends(get_db),
) -> dict:
    e = escalation_manager.create(
        db,
        created_by_id=current_user.id,
        subject=payload.subject,
        body=payload.body,
        related_user_id=payload.related_user_id,
        related_booking_id=payload.related_booking_id,
    )
    print(f"[admin] escalation {e.id} created by {current_user.id}")
    return {"escalation": serialize_escalation(e)}


@router.get("/escalations/{escalation_id}")
def get_escalation(
    escalation_id: int,
    current_user: User = Depends(require_permission("escalations.view")),
    db: Session = Depends(get_db),
) -> dict:
    e = escalation_manager.get_by_id(db, escalation_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return {"escalation": serialize_escalation(e)}


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(
    escalation_id: int,
    payload: ResolveEscalationRequest,
    current_user: User = Depends(require_permission("escalations.resolve")),
    db: Session = Depends(get_db),
) -> dict:
    e = escalation_manager.get_by_id(db, escalation_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    e = escalation_manager.resolve(db, e, current_user.id, payload.status)
    print(f"[admin] escalation {e.id} → {payload.status} by {current_user.id}")
    return {"escalation": serialize_escalation(e)}