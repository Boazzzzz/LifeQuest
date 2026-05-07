from datetime import date

from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.core.database import initialize_database
from app.integrations.anki import AnkiDailyStats
from app.integrations.github import GitHubDailyPythonActivity
from app.main import app
from app.models.learning import LearningSessionCreate, LearningSubject
from app.services.learning import LearningService
from app.services.notion_sync import NotionSyncService


def test_learning_service_creates_session_and_pulse(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    service = LearningService()
    service.create_session(
        LearningSessionCreate(
            subject=LearningSubject.python,
            duration_minutes=45,
            summary="Practiced FastAPI routing.",
            tags=["fastapi"],
        )
    )

    sessions = service.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].duration_minutes == 45


def test_learning_pulse_includes_anki_stats(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeAnkiAdapter:
        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                reviews=40,
                accuracy=82.5,
                difficult_cards=["N3::語彙: 承知"],
                decks=["N3"],
            )

    service = LearningService(anki_adapter=FakeAnkiAdapter())
    pulse = __import__("asyncio").run(service.build_pulse(date.today()))

    assert pulse.anki_reviews == 40
    assert pulse.anki_accuracy == 82.5
    assert pulse.anki_difficult_cards == ["N3::語彙: 承知"]
    assert pulse.focus_score == 8


def test_learning_pulse_includes_github_python_activity(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeGitHubAdapter:
        async def get_daily_python_activity(self, target_date: date) -> GitHubDailyPythonActivity:
            return GitHubDailyPythonActivity(
                enabled=True,
                connected=True,
                commits=3,
                python_commits=2,
                repositories=["david/lifequest"],
                python_files=["app/main.py", "app/services/learning.py"],
                commit_messages=["Practice FastAPI", "Refine learning service"],
            )

    service = LearningService(github_adapter=FakeGitHubAdapter())
    pulse = __import__("asyncio").run(service.build_pulse(date.today()))

    assert pulse.github_commits == 3
    assert pulse.github_python_commits == 2
    assert pulse.github_repositories == ["david/lifequest"]
    assert pulse.github_python_files == ["app/main.py", "app/services/learning.py"]
    assert pulse.focus_score == 8


def test_anki_status_endpoint_reports_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    with TestClient(app) as client:
        response = client.get("/integrations/anki/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["connected"] is False


def test_github_status_endpoint_reports_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)

    with TestClient(app) as client:
        response = client.get("/integrations/github/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["connected"] is False


def test_cli_log_records_learning_session(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")

    exit_code = cli_main(["log", "japanese", "20", "N3", "grammar", "--tag", "n3"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Logged japanese for 20 min" in captured.out

    service = LearningService()
    sessions = service.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].summary == "N3 grammar"
    assert sessions[0].tags == ["n3"]


def test_notion_service_builds_data_source_parent(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.notion_learning_pulse_data_source_id", "source-id")
    monkeypatch.setattr("app.core.config.settings.notion_learning_pulse_database_id", None)
    monkeypatch.setattr("app.core.config.settings.notion_api_version", None)

    service = NotionSyncService()

    assert service._learning_pulse_parent() == {"type": "data_source_id", "data_source_id": "source-id"}
    assert service.api_version == "2025-09-03"
