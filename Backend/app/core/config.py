from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Proxy Access Service"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/proxy"

    
    jwt_secret_key: SecretStr = Field(...)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    activation_key_bytes: int = 32

    redis_url: str = "redis://localhost:6379/0"

    rate_limit_enabled: bool = True
    rate_limit_global_per_minute: int = 120

    admin_email: str | None = None
    admin_password: SecretStr | None = None

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=("app/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
