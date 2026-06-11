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
from app.services.scheduled_automation import ScheduledAutomationService


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
            key="weekly-review",
            name="Weekly Review",
            category=AutomationCategory.workflow,
            schedule_hint="daily",
            tags=["review"],
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
    assert definitions[0].key == "weekly-review"
    assert definitions[0].last_run_status == AutomationRunStatus.success
    assert definitions[0].last_run_summary == "Tagged unsorted bookmarks."
    assert runs[0].items_processed == 42


def test_automation_service_rejects_duplicate_keys(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = AutomationService()
    payload = AutomationDefinitionCreate(key="weekly-review", name="Weekly Review")

    service.create_definition(payload)

    with pytest.raises(AutomationConflictError):
        service.create_definition(payload)


def test_automation_api_registers_and_lists_runs(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    with TestClient(app) as client:
        create_response = client.post(
            "/automations",
            json={
                "key": "anki-daily",
                "name": "Anki Daily Import",
                "category": "learning",
            },
        )
        run_response = client.post(
            "/automations/anki-daily/runs",
            json={
                "status": "partial",
                "trigger_source": "api",
                "items_processed": 3,
                "summary": "Synced available queue items.",
            },
        )
        list_response = client.get("/automations/anki-daily/runs")

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
            "weekly-review",
            "Weekly",
            "Review",
            "--category",
            "workflow",
            "--tag",
            "daily",
        ]
    )
    log_code = cli_main(
        [
            "automation",
            "log-run",
            "weekly-review",
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
    assert "Registered automation weekly-review" in captured.out
    assert "weekly-review [workflow] Weekly Review" in captured.out
    assert "last: success" in captured.out


def test_scheduled_automation_service_runs_anki_daily_and_records_run(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    class FakeLearningService:
        async def import_anki_today(self):
            class Stats:
                enabled = True
                error = None
                reviews = 46
                decks = ["N3"]

            return Stats()

    service = ScheduledAutomationService(learning_service=FakeLearningService())
    run = service.run("anki-daily")
    definitions = AutomationService().list_definitions()

    assert run.status == AutomationRunStatus.success
    assert run.items_processed == 46
    assert "Imported 46 Anki reviews" in (run.summary or "")
    assert definitions[0].key == "anki-daily"
    assert definitions[0].last_run_status == AutomationRunStatus.success


def test_scheduled_automation_service_runs_open_anki_and_records_run(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    desktop_path = tmp_path / "anki.exe"
    desktop_path.write_text("", encoding="utf-8")
    launches = []

    def fake_popen(args, **kwargs):
        launches.append((args, kwargs))
        return object()

    monkeypatch.setattr("app.core.config.settings.anki_desktop_path", str(desktop_path))
    monkeypatch.setattr("app.services.scheduled_automation.subprocess.Popen", fake_popen)

    service = ScheduledAutomationService()
    run = service.run("open-anki")
    definitions = AutomationService().list_definitions()

    assert launches[0][0] == [str(desktop_path)]
    assert run.status == AutomationRunStatus.success
    assert run.items_processed == 1
    assert definitions[0].key == "open-anki"
    assert definitions[0].last_run_status == AutomationRunStatus.success


def test_scheduled_automation_cli_lists_and_runs_anki_daily(tmp_path, monkeypatch, capsys):
    use_temp_database(tmp_path, monkeypatch)
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    list_code = cli_main(["automation", "scheduled-tasks"])
    run_code = cli_main(["automation", "run-scheduled", "anki-daily"])
    captured = capsys.readouterr()

    assert list_code == 0
    assert run_code == 0
    assert "anki-daily [learning] Anki Daily Import" in captured.out
    assert "skipped" in captured.out.lower()


def test_scheduled_automation_cli_runs_open_anki(tmp_path, monkeypatch, capsys):
    use_temp_database(tmp_path, monkeypatch)
    desktop_path = tmp_path / "anki.exe"
    desktop_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.core.config.settings.anki_desktop_path", str(desktop_path))
    monkeypatch.setattr("app.services.scheduled_automation.subprocess.Popen", lambda *args, **kwargs: object())

    run_code = cli_main(["automation", "run-scheduled", "open-anki"])
    captured = capsys.readouterr()

    assert run_code == 0
    assert "Launched desktop Anki" in captured.out
