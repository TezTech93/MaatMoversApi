# MaatMovers

Two-sided moving-services marketplace. See `backend/` (FastAPI + Postgres) and
`frontend/` (Expo React Native, Phase 3).

## Backend quickstart

    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env        # then edit DATABASE_URL + JWT_SECRET_KEY
    createdb maatmovers
    alembic upgrade head
    uvicorn app.main:app --reload

Health check: `GET http://localhost:8000/healthz`