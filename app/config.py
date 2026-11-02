from functools import lru_cache
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: SecretStr
    device_api_key: SecretStr
    dashboard_api_key: SecretStr
    device_id: str = Field(default="esp32-01", pattern=r"^[a-zA-Z0-9_-]{1,48}$")
    stale_after_seconds: int = Field(default=30, ge=10, le=3600)
    ingest_per_minute: int = Field(default=120, ge=30, le=3600)
    retention_days: int = Field(default=30, ge=1, le=3650)

    @field_validator("device_api_key", "dashboard_api_key")
    @classmethod
    def strong_key(cls, value):
        raw = value.get_secret_value()
        if len(raw) < 32 or raw.lower().startswith(("change", "replace", "example")):
            raise ValueError("Use a randomly generated key of at least 32 characters")
        return value

    @model_validator(mode="after")
    def separate_keys(self):
        if self.device_api_key == self.dashboard_api_key:
            raise ValueError("Device and dashboard keys must differ")
        if not self.database_url.get_secret_value().startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            raise ValueError("PostgreSQL is required")
        return self

    @property
    def sqlalchemy_url(self):
        url = self.database_url.get_secret_value()
        return url.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)

@lru_cache
def get_settings():
    return Settings()
