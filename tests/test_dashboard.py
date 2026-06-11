from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.database import initialize_database
from app.main import app
from app.models.automation import (
    AutomationCategory,
    AutomationDefinitionCreate,
    AutomationRunCreate,
    AutomationRunStatus,
    AutomationTriggerSource,
)
from app.models.learning import LearningSessionCreate, LearningSubject
from app.models.subscription import SubscriptionCategory, SubscriptionCreate, SubscriptionRecurrenceKind
from app.models.work_knowledge import WorkKnowledgeCategory, WorkKnowledgeNoteCreate
from app.services.automation import AutomationService
from app.services.dashboard import DashboardService
from app.services.learning import LearningService
from app.services.subscription import SubscriptionService
from app.services.work_knowledge import WorkKnowledgeService


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)
    initialize_database()


def test_dashboard_service_builds_live_overview(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    target_date = date.fromisoformat("2026-05-09")
    started_at = datetime(2026, 5, 9, 1, 0, tzinfo=timezone.utc)

    LearningService().create_session(
        LearningSessionCreate(
            subject=LearningSubject.python,
            duration_minutes=45,
            summary="Implemented dashboard overview API.",
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=45),
        )
    )
    SubscriptionService().create_subscription(
        SubscriptionCreate(
            name="Spotify Premium",
            amount=149.0,
            billing_day=15,
            category=SubscriptionCategory.entertainment,
        )
    )
    SubscriptionService().create_subscription(
        SubscriptionCreate(
            name="ChatGPT Plus",
            amount=20.0,
            currency="USD",
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            category=SubscriptionCategory.ai,
        )
    )

    automation = AutomationService().create_definition(
        AutomationDefinitionCreate(
            key="raindrop-classifier",
            name="Raindrop Classifier",
            category=AutomationCategory.knowledge,
            schedule_hint="daily",
        )
    )
    AutomationService().create_run(
        automation.key,
        AutomationRunCreate(
            status=AutomationRunStatus.failed,
            trigger_source=AutomationTriggerSource.manual,
            items_processed=2,
            summary="Classifier run needs investigation.",
        ),
    )

    WorkKnowledgeService().create_note(
        WorkKnowledgeNoteCreate(
            title="Nginx upstream check",
            category=WorkKnowledgeCategory.nginx,
            sanitized_summary="Check the upstream service before changing proxy config.",
            follow_up="Document the healthy restart order.",
            tags=["ops"],
        )
    )

    overview = __import__("asyncio").run(DashboardService().build_overview(target_date=target_date))

    assert overview.hero.status == "live"
    assert overview.learning.pulse.total_minutes == 45
    assert overview.learning.recent_sessions[0].summary == "Implemented dashboard overview API."
    assert overview.subscriptions.overview.active_subscription_count == 2
    assert overview.subscriptions.overview.missing_schedule_count == 1
    assert overview.automations.needs_attention_count == 1
    assert overview.knowledge.follow_up_count == 1
    assert overview.launchpad[0].key == "learning"
    assert overview.recent_activity
    assert any(item.title == "Added subscription" for item in overview.recent_activity)
    assert any(item.title == "有訂閱仍缺少扣款排程" for item in overview.attention_items)
    assert any(item.title == "有自動化最近執行不穩" for item in overview.attention_items)


def test_dashboard_api_returns_overview_payload(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    started_at = datetime(2026, 5, 9, 8, 30, tzinfo=timezone.utc)

    LearningService().create_session(
        LearningSessionCreate(
            subject=LearningSubject.japanese,
            duration_minutes=30,
            summary="Reviewed N3 cards.",
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=30),
        )
    )
    WorkKnowledgeService().create_note(
        WorkKnowledgeNoteCreate(
            title="Systemd service status",
            category=WorkKnowledgeCategory.linux,
            sanitized_summary="Use systemctl status and journalctl together.",
            tags=["work"],
        )
    )

    with TestClient(app) as client:
        overview_response = client.get("/dashboard/overview", params={"target_date": "2026-05-09"})
        page_response = client.get("/dashboard")

    assert overview_response.status_code == 200
    assert page_response.status_code == 200
    payload = overview_response.json()
    assert payload["target_date"] == "2026-05-09"
    assert payload["hero"]["status"] == "live"
    assert payload["learning"]["pulse"]["japanese_minutes"] == 30
    assert payload["knowledge"]["note_count"] == 1
    assert payload["attention_items"]
    assert payload["recent_activity"]
    assert "LifeQuest" in page_response.text
