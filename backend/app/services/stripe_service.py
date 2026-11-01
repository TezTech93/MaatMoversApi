"""Stripe client + high-level helpers. All Stripe calls go through here."""
import json
from typing import Optional

import requests
import stripe

from app.core.config import settings


STRIPE_API_BASE = "https://api.stripe.com"
STRIPE_API_VERSION = "2026-10-28.endive"


def _ensure_configured() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY


# ── Checkout (v1) ────────────────────────────────────────

def _create_checkout_session(
    *,
    booking_id: int,
    amount_cents: int,
    product_name: str,
    customer_email: Optional[str],
    kind: str,
) -> dict:
    """Internal — shared by deposit and final session creation."""
    _ensure_configured()
    pi_metadata = {"booking_id": str(booking_id), "kind": kind}
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": product_name},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        success_url=(
            f"{settings.CHECKOUT_SUCCESS_URL}&booking_id={booking_id}&kind={kind}"
        ),
        cancel_url=(
            f"{settings.CHECKOUT_CANCEL_URL}&booking_id={booking_id}&kind={kind}"
        ),
        client_reference_id=str(booking_id),
        metadata={"booking_id": str(booking_id), "kind": kind},
        payment_intent_data={"metadata": pi_metadata},
        customer_email=customer_email or None,
    )
    return {
        "id": session["id"],
        "url": session["url"],
        "payment_intent": session.get("payment_intent"),
        "status": session.get("status"),
    }


def create_deposit_checkout_session(
    *,
    booking_id: int,
    amount_cents: int,
    product_name: str,
    customer_email: Optional[str],
) -> dict:
    """Checkout Session for the refundable deposit.

    Do NOT pass payment_method_types — removed from the Checkout Sessions
    API in the 2026-09-30 release.
    """
    return _create_checkout_session(
        booking_id=booking_id,
        amount_cents=amount_cents,
        product_name=product_name,
        customer_email=customer_email,
        kind="deposit",
    )


def create_final_checkout_session(
    *,
    booking_id: int,
    amount_cents: int,
    product_name: str,
    customer_email: Optional[str],
) -> dict:
    """Checkout Session for the remaining balance after completion."""
    return _create_checkout_session(
        booking_id=booking_id,
        amount_cents=amount_cents,
        product_name=product_name,
        customer_email=customer_email,
        kind="final",
    )


def retrieve_checkout_session(session_id: str) -> dict:
    _ensure_configured()
    session = stripe.checkout.Session.retrieve(session_id)
    return {
        "id": session["id"],
        "url": session["url"],
        "status": session.get("status"),
        "payment_intent": session.get("payment_intent"),
    }


# ── Refunds (v1) ─────────────────────────────────────────

def refund_payment_intent(
    payment_intent_id: str,
    amount_cents: Optional[int] = None,
    reason: Optional[str] = None,
) -> dict:
    """Refund a PaymentIntent. Full refund when amount_cents is None."""
    _ensure_configured()
    params: dict = {"payment_intent": payment_intent_id}
    if amount_cents is not None:
        params["amount"] = amount_cents
    if reason in ("duplicate", "fraudulent", "requested_by_customer"):
        params["reason"] = reason
    refund = stripe.Refund.create(**params)
    return {
        "id": refund["id"],
        "amount": refund["amount"],
        "status": refund.get("status"),
        "payment_intent": refund.get("payment_intent"),
    }


# ── Connect (v2) ─────────────────────────────────────────

def _v2_headers() -> dict:
    _ensure_configured()
    return {
        "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
        "Stripe-Version": STRIPE_API_VERSION,
        "Content-Type": "application/json",
    }


def create_express_account(*, email: str, country: Optional[str] = None) -> dict:
    """Create a Stripe Connect account via the Accounts v2 API.

    Self-serve fallback: full dashboard + Stripe-collected fees and losses.
    Express + application/application is preferred but requires
    platform-managed-risk approval; see the Stripe Dashboard Connect settings.
    """
    body = {
        "contact_email": email,
        "identity": {"country": country or settings.CONNECT_COUNTRY},
        "dashboard": "full",
        "defaults": {
            "responsibilities": {
                "fees_collector": "stripe",
                "losses_collector": "stripe",
            }
        },
        "configuration": {
            "merchant": {
                "capabilities": {
                    "card_payments": {"requested": True}
                }
            },
            "recipient": {
                "capabilities": {
                    "stripe_balance": {
                        "stripe_transfers": {"requested": True}
                    }
                }
            },
        },
        "metadata": {"platform": "maatmovers"},
    }
    resp = requests.post(
        f"{STRIPE_API_BASE}/v2/core/accounts",
        headers=_v2_headers(),
        data=json.dumps(body),
        timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Stripe v2 account create failed ({resp.status_code}): {resp.text}"
        )
    account = resp.json()
    return {
        "id": account["id"],
        "charges_enabled": bool(account.get("charges_enabled")),
        "payouts_enabled": bool(account.get("payouts_enabled")),
        "details_submitted": bool(account.get("details_submitted")),
    }
    """Create a Stripe Connect Express account via the Accounts v2 API."""
    body = {
        "contact_email": email,
        "identity": {"country": country or settings.CONNECT_COUNTRY},
        "dashboard": "express",
        "defaults": {
            "responsibilities": {
                "fees_collector": "application",
                "losses_collector": "stripe",   # ← changed from "application"
            }
        },
        "configuration": {
            "recipient": {
                "capabilities": {
                    "stripe_balance": {
                        "stripe_transfers": {"requested": True}
                    }
                }
            }
        },
        "metadata": {"platform": "maatmovers"},
    }
    resp = requests.post(
        f"{STRIPE_API_BASE}/v2/core/accounts",
        headers=_v2_headers(),
        data=json.dumps(body),
        timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Stripe v2 account create failed ({resp.status_code}): {resp.text}"
        )
    account = resp.json()
    return {
        "id": account["id"],
        "charges_enabled": bool(account.get("charges_enabled")),
        "payouts_enabled": bool(account.get("payouts_enabled")),
        "details_submitted": bool(account.get("details_submitted")),
    }
    """Create a Stripe Connect Express account via the Accounts v2 API."""
    body = {
        "contact_email": email,
        "identity": {"country": country or settings.CONNECT_COUNTRY},
        "dashboard": "express",
        "defaults": {
            "responsibilities": {
                "fees_collector": "application",
                "losses_collector": "application",
            }
        },
        "configuration": {
            "recipient": {
                "capabilities": {
                    "stripe_balance": {
                        "stripe_transfers": {"requested": True}
                    }
                }
            }
        },
        "metadata": {"platform": "maatmovers"},
    }
    resp = requests.post(
        f"{STRIPE_API_BASE}/v2/core/accounts",
        headers=_v2_headers(),
        data=json.dumps(body),
        timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Stripe v2 account create failed ({resp.status_code}): {resp.text}"
        )
    account = resp.json()
    return {
        "id": account["id"],
        "charges_enabled": bool(account.get("charges_enabled")),
        "payouts_enabled": bool(account.get("payouts_enabled")),
        "details_submitted": bool(account.get("details_submitted")),
    }


def create_account_onboarding_link(
    *,
    account_id: str,
    refresh_url: Optional[str] = None,
    return_url: Optional[str] = None,
) -> dict:
    """Create a single-use Stripe-hosted onboarding link via Accounts v2.

    NOTE: do NOT pass "configurations" — removed from the v2 Account Links
    API in the 2026-09-30 version. Stripe determines required
    configurations automatically from the Account's own config.
    """
    body = {
        "account": account_id,
        "use_case": {
            "type": "account_onboarding",
            "account_onboarding": {
                "refresh_url": refresh_url or settings.CONNECT_REFRESH_URL,
                "return_url": return_url or settings.CONNECT_RETURN_URL,
            },
        },
    }
    resp = requests.post(
        f"{STRIPE_API_BASE}/v2/core/account_links",
        headers=_v2_headers(),
        data=json.dumps(body),
        timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Stripe v2 account link failed ({resp.status_code}): {resp.text}"
        )
    link = resp.json()
    return {"url": link["url"], "expires_at": link.get("expires_at")}
    """Create a single-use Stripe-hosted onboarding link via Accounts v2."""
    body = {
        "account": account_id,
        "use_case": {
            "type": "account_onboarding",
            "account_onboarding": {
                "configurations": ["recipient"],
                "refresh_url": refresh_url or settings.CONNECT_REFRESH_URL,
                "return_url": return_url or settings.CONNECT_RETURN_URL,
            },
        },
    }
    resp = requests.post(
        f"{STRIPE_API_BASE}/v2/core/account_links",
        headers=_v2_headers(),
        data=json.dumps(body),
        timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Stripe v2 account link failed ({resp.status_code}): {resp.text}"
        )
    link = resp.json()
    return {"url": link["url"], "expires_at": link.get("expires_at")}


def retrieve_account(account_id: str) -> dict:
    """Retrieve a v2 account's current status."""
    resp = requests.get(
        f"{STRIPE_API_BASE}/v2/core/accounts/{account_id}",
        headers=_v2_headers(),
        timeout=10,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Stripe v2 account retrieve failed ({resp.status_code}): {resp.text}"
        )
    account = resp.json()
    return {
        "id": account["id"],
        "charges_enabled": bool(account.get("charges_enabled")),
        "payouts_enabled": bool(account.get("payouts_enabled")),
        "details_submitted": bool(account.get("details_submitted")),
    }


def create_transfer(
    *,
    account_id: str,
    amount_cents: int,
    currency: str = "usd",
    metadata: Optional[dict] = None,
) -> dict:
    """Move funds from the platform balance to a connected Express account."""
    _ensure_configured()
    transfer = stripe.Transfer.create(
        destination=account_id,
        amount=amount_cents,
        currency=currency,
        metadata=metadata or {},
    )
    return {
        "id": transfer["id"],
        "amount": transfer["amount"],
        "destination": transfer.get("destination"),
    }


# ── Webhook ─────────────────────────────────────────────

def construct_webhook_event(payload: bytes, signature: str, secret: str) -> dict:
    """Verify signature with the given secret and return the parsed event.

    Works for both v1 snapshot and v2 thin events — the HMAC signing is
    identical; only the payload shape differs.
    """
    if not secret:
        raise RuntimeError("Webhook secret is not configured")
    return stripe.Webhook.construct_event(payload, signature, secret)