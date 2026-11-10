"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Campaign Data Hub backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Campaign Data Hub"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://cdh:cdh@localhost:5432/campaign_data_hub"
    cors_origins: str = "http://localhost:5173"
    assessment_data_dir: str = "../assessment/data"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
