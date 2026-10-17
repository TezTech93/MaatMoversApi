"""FastAPI application entrypoint for MaatMovers."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    about, auth, bookings, clients, movers, notifications,
    payments, services, users,
)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title=settings.APP_NAME)

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(clients.router)
    app.include_router(movers.router)
    app.include_router(services.router)
    app.include_router(bookings.router)
    app.include_router(payments.router)
    app.include_router(notifications.router)
    app.include_router(about.router)

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict:
        """Liveness probe."""
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

    return app


app = create_app()