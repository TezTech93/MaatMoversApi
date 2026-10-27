"""Stripe client + high-level helpers. All Stripe calls go through here."""
from typing import Optional

import stripe

from app.core.config import settings


def _ensure_configured() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY


# ── Checkout ─────────────────────────────────────────────

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


# ── Refunds ──────────────────────────────────────────────

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


# ── Connect ──────────────────────────────────────────────

def create_express_account(*, email: str, country: Optional[str] = None) -> dict:
    """Create a Stripe Connect Express account for a mover.

    Only the `transfers` capability is requested because MaatMovers charges
    on the platform account. Express onboarding collects KYC/bank details.
    """
    _ensure_configured()
    account = stripe.Account.create(
        type="express",
        country=country or settings.CONNECT_COUNTRY,
        email=email,
        capabilities={"transfers": {"requested": True}},
        business_type="individual",
        metadata={"platform": "maatmovers"},
    )
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
    """Create a single-use Stripe-hosted onboarding link for an Express account."""
    _ensure_configured()
    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url or settings.CONNECT_REFRESH_URL,
        return_url=return_url or settings.CONNECT_RETURN_URL,
        type="account_onboarding",
    )
    return {"url": link["url"], "expires_at": link.get("expires_at")}


def retrieve_account(account_id: str) -> dict:
    _ensure_configured()
    account = stripe.Account.retrieve(account_id)
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

def construct_webhook_event(payload: bytes, signature: str) -> dict:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    return stripe.Webhook.construct_event(
        payload, signature, settings.STRIPE_WEBHOOK_SECRET
    )