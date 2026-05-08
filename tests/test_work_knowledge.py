from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.core.database import initialize_database
from app.main import app
from app.models.work_knowledge import WorkKnowledgeCategory, WorkKnowledgeNoteCreate
from app.services.work_knowledge import WorkKnowledgeService


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    initialize_database()


def test_work_knowledge_service_creates_note(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = WorkKnowledgeService()

    note = service.create_note(
        WorkKnowledgeNoteCreate(
            title="Nginx 502 troubleshooting pattern",
            category=WorkKnowledgeCategory.nginx,
            sanitized_summary="A 502 often means the proxy cannot reach upstream.",
            commands=["systemctl status", "journalctl -u service"],
            concepts=["reverse proxy", "upstream health"],
            systems=["linux"],
            tags=["troubleshooting"],
        )
    )

    notes = service.list_notes()

    assert notes[0].id == note.id
    assert notes[0].commands == ["systemctl status", "journalctl -u service"]
    assert notes[0].concepts == ["reverse proxy", "upstream health"]


def test_work_knowledge_api_create_and_sync_skip(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    monkeypatch.setattr("app.core.config.settings.notion_enabled", False)

    with TestClient(app) as client:
        create_response = client.post(
            "/work-knowledge",
            json={
                "title": "Disk usage check",
                "category": "linux",
                "sanitized_summary": "Use df and du to identify disk pressure.",
                "commands": ["df -h", "du -sh *"],
                "concepts": ["disk usage"],
                "systems": ["linux"],
            },
        )
        list_response = client.get("/work-knowledge")
        sync_response = client.post("/work-knowledge/sync-notion")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "Disk usage check"
    assert sync_response.json() == {"status": "skipped", "reason": "notion_disabled"}


def test_work_knowledge_cli_capture(tmp_path, monkeypatch, capsys):
    use_temp_database(tmp_path, monkeypatch)

    exit_code = cli_main(
        [
            "work",
            "capture",
            "Systemd",
            "service",
            "status",
            "--category",
            "linux",
            "--summary",
            "Use systemctl status and journalctl to inspect service failures.",
            "--command",
            "systemctl status <service>",
            "--concept",
            "systemd",
            "--system",
            "linux",
            "--tag",
            "work",
        ]
    )
    list_code = cli_main(["work", "list"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert list_code == 0
    assert "Captured work knowledge" in captured.out
    assert "Systemd service status" in captured.out
