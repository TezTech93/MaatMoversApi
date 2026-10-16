"""FastAPI application entrypoint for MaatMovers."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title=settings.APP_NAME)

    # 1. CORS middleware first, per conventions.
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Routers (order will extend in Phase 2+).
    app.include_router(auth.router)

    # 3. Static mount reserved for later phases.

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict:
        """Liveness probe used by Render and by local dev."""
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

    return app


app = create_app()