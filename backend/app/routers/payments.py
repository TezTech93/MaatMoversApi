"""Payment routes. Phase 5 fills in the real implementations."""
from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/deposit/{booking_id}")
def deposit(booking_id: int):
    """Stripe Checkout for the refundable deposit. Implemented in Phase 5."""
    raise HTTPException(status_code=501, detail="Not implemented until Phase 5")


@router.post("/final/{booking_id}")
def final(booking_id: int):
    """Stripe PaymentIntent for the remaining balance. Implemented in Phase 5."""
    raise HTTPException(status_code=501, detail="Not implemented until Phase 5")


@router.post("/refund/{booking_id}")
def refund(booking_id: int):
    """Issue a refund. Implemented in Phase 5."""
    raise HTTPException(status_code=501, detail="Not implemented until Phase 5")


@router.post("/webhook")
def webhook():
    """Stripe webhook receiver. Implemented in Phase 5."""
    raise HTTPException(status_code=501, detail="Not implemented until Phase 5")


@router.post("/connect/onboard")
def connect_onboard():
    """Stripe Connect Express onboarding. Implemented in Phase 5."""
    raise HTTPException(status_code=501, detail="Not implemented until Phase 5")