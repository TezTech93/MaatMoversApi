"""Public app metadata + privacy policy."""
from fastapi import APIRouter


router = APIRouter(prefix="/about", tags=["about"])


@router.get("")
def about() -> dict:
    """Public app metadata for the client to display."""
    return {
        "name": "MaatMovers",
        "version": "0.5.3",
        "description": "Two-sided moving-services marketplace",
        "support_email": "support@maatmovers.example",
        "privacy_url": "/about/privacy",
    }


@router.get("/privacy")
def privacy() -> dict:
    """Public privacy policy. Structured for native rendering + full text for fallback."""
    sections = [
        {
            "heading": "Information we collect",
            "body": (
                "When you create an account we collect your email address, username, "
                "and (optionally) your phone number. Clients provide pickup and dropoff "
                "addresses and coordinates for each move. Movers provide a home address "
                "and coordinates used for matching. Payment card details are collected "
                "and stored by Stripe, Inc. — MaatMovers never sees or stores full card "
                "numbers."
            ),
        },
        {
            "heading": "How we use your information",
            "body": (
                "We use your data to operate the marketplace: authenticate you, match "
                "clients with movers, process payments, and send transactional emails "
                "and push notifications about your bookings. We do not sell your data."
            ),
        },
        {
            "heading": "Third-party services",
            "body": (
                "We rely on Stripe for payments and refunds, SendGrid (or SMTP) for "
                "transactional email, and Expo for push notifications. Each processes "
                "data under its own privacy policy."
            ),
        },
        {
            "heading": "Data retention",
            "body": (
                "Booking, payment, and strike records are retained to maintain "
                "marketplace integrity and comply with financial record-keeping. "
                "If you delete your account, we deactivate it and remove your device "
                "push tokens; booking history is retained under your user id for audit."
            ),
        },
        {
            "heading": "Your rights",
            "body": (
                "You may update your profile at any time from the app. You may delete "
                "your account from the settings screen; if you have active bookings, "
                "finish or cancel them first. For data-access requests, contact support."
            ),
        },
        {
            "heading": "Contact",
            "body": "Questions: support@maatmovers.example",
        },
    ]
    return {
        "version": "1.0",
        "last_updated": "2026-10-25",
        "summary": (
            "MaatMovers collects only what it needs to run a moving-services "
            "marketplace: account details, move coordinates, and payment data "
            "handled by Stripe. We do not sell your data."
        ),
        "sections": sections,
        "contact_email": "support@maatmovers.example",
    }