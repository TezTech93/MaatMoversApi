"""Application settings loaded from environment variables / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values come from env or backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "MaatMovers"
    APP_ENV: str = "development"

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    CORS_ORIGINS: str = "http://localhost:8081,http://localhost:19006"

    # Email
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    CHECKOUT_SUCCESS_URL: str = "http://localhost:8081/?checkout=success"
    CHECKOUT_CANCEL_URL: str = "http://localhost:8081/?checkout=cancel"


settings = Settings()