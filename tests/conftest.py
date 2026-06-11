from pathlib import Path

import pytest

from app.core.database import initialize_database


@pytest.fixture
def temp_database_path(tmp_path, monkeypatch) -> Path:
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_backend", "sqlite")
    monkeypatch.setattr("app.core.database.settings.database_backend", "sqlite")
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    return database_path


@pytest.fixture
def temp_database(temp_database_path: Path) -> Path:
    initialize_database()
    return temp_database_path
