"""Public app metadata."""
from fastapi import APIRouter


router = APIRouter(prefix="/about", tags=["about"])


@router.get("")
def about() -> dict:
    """Public app metadata for the client to display."""
    return {
        "name": "MaatMovers",
        "version": "0.2.0",
        "description": "Two-sided moving-services marketplace",
        "support_email": "support@maatmovers.example",
    }