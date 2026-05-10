from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LifeQuest"
    environment: str = "development"
    database_backend: Literal["sqlite", "mssql"] = "sqlite"
    database_path: Path = Path("data/lifequest.db")
    mssql_connection_string: str | None = None
    log_level: str = "INFO"

    anki_enabled: bool = False
    anki_connect_url: str = "http://127.0.0.1:8765"
    anki_api_version: int = 6
    anki_timeout_seconds: float = 5.0
    anki_decks: str = ""
    anki_desktop_path: Path | None = None

    github_enabled: bool = False
    github_token: str | None = None
    github_username: str | None = None
    github_api_version: str = "2022-11-28"
    github_timeout_seconds: float = 10.0

    notion_enabled: bool = False
    notion_token: str | None = None
    notion_parent_page_id: str | None = Field(default=None)
    notion_learning_pulse_data_source_id: str | None = Field(default=None)
    notion_learning_pulse_database_id: str | None = Field(default=None)
    notion_automations_data_source_id: str | None = Field(default=None)
    notion_automations_database_id: str | None = Field(default=None)
    notion_work_knowledge_data_source_id: str | None = Field(default=None)
    notion_work_knowledge_database_id: str | None = Field(default=None)
    notion_japanese_verb_forms_data_source_id: str | None = Field(default=None)
    notion_japanese_verb_forms_database_id: str | None = Field(default=None)
    notion_inbox_data_source_id: str | None = Field(default=None)
    notion_inbox_database_id: str | None = Field(default=None)
    notion_api_version: str | None = None
    notion_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
