from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LifeQuest"
    environment: str = "development"
    database_path: Path = Path("data/lifequest.db")
    log_level: str = "INFO"

    anki_enabled: bool = False
    anki_connect_url: str = "http://127.0.0.1:8765"
    anki_api_version: int = 6
    anki_timeout_seconds: float = 5.0
    anki_decks: str = ""

    github_enabled: bool = False
    github_token: str | None = None
    github_username: str | None = None

    notion_enabled: bool = False
    notion_token: str | None = None
    notion_learning_pulse_database_id: str | None = Field(default=None)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
