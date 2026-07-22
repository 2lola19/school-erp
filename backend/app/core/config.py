from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "School ERP API"
    VERSION: str = "1.2.0"
    API_V1_STR: str = "/api/v1"
    SQLALCHEMY_DATABASE_URI: str = (
        "postgresql+asyncpg://school:school@localhost:5432/school_erp"
    )
    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    SECURE_COOKIES: bool = False
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"
    PAYSTACK_SECRET_KEY: str | None = None
    FLUTTERWAVE_SECRET_HASH: str | None = None
    BILLING_WEBHOOK_MAX_ATTEMPTS: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
