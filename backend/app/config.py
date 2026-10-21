from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://hrms:hrms@localhost:5432/hrms"
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION_USE_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = Field(
        default=30,
        validation_alias=AliasChoices("JWT_ACCESS_EXPIRE_MINUTES", "JWT_EXPIRE_MINUTES"),
    )
    jwt_refresh_expire_days: int = Field(default=14, validation_alias="JWT_REFRESH_EXPIRE_DAYS")
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    login_rate_per_minute: int = Field(
        default=10,
        validation_alias=AliasChoices("LOGIN_RATE_PER_MINUTE", "RATE_LIMIT_LOGIN_PER_MIN"),
    )
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", validation_alias="SMTP_FROM")
    slack_webhook_url: str = Field(default="", validation_alias="SLACK_WEBHOOK_URL")
    upload_dir: str = Field(default="./uploads", validation_alias="UPLOAD_DIR")
    max_upload_bytes: int = Field(default=5_000_000, validation_alias="MAX_UPLOAD_BYTES")
    public_ui_base_url: str = Field(default="", validation_alias="PUBLIC_UI_BASE_URL")
    password_reset_expire_hours: int = Field(default=24, validation_alias="PASSWORD_RESET_EXPIRE_HOURS")
    password_min_length: int = Field(default=8, validation_alias="PASSWORD_MIN_LENGTH")
    document_retention_years: int = Field(default=7, validation_alias="DOCUMENT_RETENTION_YEARS")


def cors_origin_list(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


def public_ui_origin(settings: Settings) -> str:
    """Base URL for links in outbound email (no trailing slash)."""
    raw = (settings.public_ui_base_url or "").strip().rstrip("/")
    if raw:
        return raw
    origins = cors_origin_list(settings.cors_origins)
    if origins:
        return origins[0].rstrip("/")
    return "http://127.0.0.1:8787"


settings = Settings()
