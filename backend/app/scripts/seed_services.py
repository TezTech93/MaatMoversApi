"""Seed the services table with a few defaults.

Usage: python -m app.scripts.seed_services
"""
from app.core.database import SessionLocal
from app.managers import service_manager


DEFAULTS = [
    {
        "name": "Local Move",
        "description": "Short in-town move.",
        "base_price_cents": 8000,
        "per_mile_cents": 200,
        "estimated_duration_minutes": 60,
        "is_active": True,
    },
    {
        "name": "Small Move",
        "description": "Studio or one-bedroom move.",
        "base_price_cents": 12000,
        "per_mile_cents": 300,
        "estimated_duration_minutes": 120,
        "is_active": True,
    },
    {
        "name": "Long Distance",
        "description": "Cross-town or cross-region move.",
        "base_price_cents": 20000,
        "per_mile_cents": 400,
        "estimated_duration_minutes": 240,
        "is_active": True,
    },
]


def main() -> None:
    """Insert default services if the table is empty."""
    db = SessionLocal()
    try:
        existing = service_manager.list_all(db)
        if existing:
            print(f"[seed_services] table already has {len(existing)} services, skipping")
            return
        for row in DEFAULTS:
            s = service_manager.create(db, **row)
            print(f"[seed_services] created service id={s.id} name={s.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()