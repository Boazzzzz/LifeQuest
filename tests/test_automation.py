import pytest
from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.core.database import initialize_database
from app.main import app
from app.models.automation import (
    AutomationCategory,
    AutomationDefinitionCreate,
    AutomationRunCreate,
    AutomationRunStatus,
    AutomationTriggerSource,
)
from app.services.automation import AutomationConflictError, AutomationService


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    initialize_database()


def test_automation_service_registers_definition_and_run(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = AutomationService()

    definition = service.create_definition(
        AutomationDefinitionCreate(
            key="raindrop-classifier",
            name="Raindrop Unsorted Classifier",
            category=AutomationCategory.knowledge,
            schedule_hint="daily",
            tags=["raindrop"],
        )
    )
    run = service.create_run(
        definition.key,
        AutomationRunCreate(
            status=AutomationRunStatus.success,
            trigger_source=AutomationTriggerSource.manual,
            items_processed=42,
            summary="Tagged unsorted bookmarks.",
        ),
    )

    definitions = service.list_definitions()
    runs = service.list_runs(definition.key)

    assert run.finished_at is not None
    assert definitions[0].key == "raindrop-classifier"
    assert definitions[0].last_run_status == AutomationRunStatus.success
    assert definitions[0].last_run_summary == "Tagged unsorted bookmarks."
    assert runs[0].items_processed == 42


def test_automation_service_rejects_duplicate_keys(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = AutomationService()
    payload = AutomationDefinitionCreate(key="telegram-queue", name="Telegram Queue")

    service.create_definition(payload)

    with pytest.raises(AutomationConflictError):
        service.create_definition(payload)


def test_automation_api_registers_and_lists_runs(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    with TestClient(app) as client:
        create_response = client.post(
            "/automations",
            json={
                "key": "stash-sync",
                "name": "Stash Sync",
                "category": "media",
                "external_project_path": "/tmp/stash-sync",
            },
        )
        run_response = client.post(
            "/automations/stash-sync/runs",
            json={
                "status": "partial",
                "trigger_source": "api",
                "items_processed": 3,
                "summary": "Synced available queue items.",
            },
        )
        list_response = client.get("/automations/stash-sync/runs")

    assert create_response.status_code == 201
    assert run_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "partial"
    assert list_response.json()[0]["items_processed"] == 3


def test_automation_api_sync_notion_skips_when_disabled(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    monkeypatch.setattr("app.core.config.settings.notion_enabled", False)

    with TestClient(app) as client:
        response = client.post("/automations/sync-notion")

    assert response.status_code == 200
    assert response.json() == {"status": "skipped", "reason": "notion_disabled"}


def test_automation_cli_registers_and_logs_run(tmp_path, monkeypatch, capsys):
    use_temp_database(tmp_path, monkeypatch)

    register_code = cli_main(
        [
            "automation",
            "register",
            "mobile-game-scripts",
            "Mobile",
            "Game",
            "Scripts",
            "--category",
            "game",
            "--tag",
            "daily",
        ]
    )
    log_code = cli_main(
        [
            "automation",
            "log-run",
            "mobile-game-scripts",
            "--status",
            "success",
            "--items-processed",
            "5",
            "--summary",
            "Completed",
            "daily",
            "script",
            "checks",
        ]
    )
    list_code = cli_main(["automation", "list"])
    captured = capsys.readouterr()

    assert register_code == 0
    assert log_code == 0
    assert list_code == 0
    assert "Registered automation mobile-game-scripts" in captured.out
    assert "mobile-game-scripts [game] Mobile Game Scripts" in captured.out
    assert "last: success" in captured.out
