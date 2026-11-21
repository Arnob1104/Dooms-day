from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Supabase gives you a standard Postgres connection string
    # (Project Settings -> Database -> Connection string). Paste it here.
    # Falls back to a local SQLite file so the app also runs with zero setup.
    database_url: str = "sqlite:///./doomsday.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    seed_sample_data: bool = False

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
