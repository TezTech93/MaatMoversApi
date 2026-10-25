"""Stripe client + high-level helpers. All Stripe calls go through here."""
from typing import Optional

import stripe

from app.core.config import settings


def _ensure_configured() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY


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
        success_url=f"{settings.CHECKOUT_SUCCESS_URL}&booking_id={booking_id}&kind={kind}",
        cancel_url=f"{settings.CHECKOUT_CANCEL_URL}&booking_id={booking_id}&kind={kind}",
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

    NOTE: do NOT pass payment_method_types — removed from the Checkout
    Sessions API in the 2026-09-30 release.
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


def refund_payment_intent(
    payment_intent_id: str,
    amount_cents: Optional[int] = None,
    reason: Optional[str] = None,
) -> dict:
    """Refund a PaymentIntent. Full refund when amount_cents is None.

    `reason` must be one of: duplicate | fraudulent | requested_by_customer
    """
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


def construct_webhook_event(payload: bytes, signature: str) -> dict:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    return stripe.Webhook.construct_event(
        payload, signature, settings.STRIPE_WEBHOOK_SECRET
    )