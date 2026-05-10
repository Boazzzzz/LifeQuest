from datetime import date, datetime, timedelta, timezone

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
from app.models.learning import LearningSessionCreate, LearningSubject
from app.models.subscription import SubscriptionCategory, SubscriptionCreate, SubscriptionRecurrenceKind, SubscriptionUpdate
from app.models.work_knowledge import WorkKnowledgeCategory, WorkKnowledgeNoteCreate
from app.services.activity import ActivityService
from app.services.automation import AutomationService
from app.services.review import ReviewService
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


def test_activity_timeline_collects_multiple_modules(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    started_at = datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)

    LearningService().create_session(
        LearningSessionCreate(
            subject=LearningSubject.python,
            duration_minutes=40,
            summary="Built weekly review shape.",
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=40),
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
    WorkKnowledgeService().create_note(
        WorkKnowledgeNoteCreate(
            title="Nginx upstream check",
            category=WorkKnowledgeCategory.nginx,
            sanitized_summary="Check upstream health before changing proxy config.",
        )
    )
    automation = AutomationService().create_definition(
        AutomationDefinitionCreate(
            key="raindrop-classifier",
            name="Raindrop Classifier",
            category=AutomationCategory.knowledge,
        )
    )
    AutomationService().create_run(
        automation.key,
        AutomationRunCreate(
            status=AutomationRunStatus.partial,
            trigger_source=AutomationTriggerSource.manual,
            summary="Classifier needs more rules.",
        ),
    )

    timeline = ActivityService().get_recent_timeline(limit=10)

    assert len(timeline.items) >= 4
    assert any(item.title == "Added subscription" for item in timeline.items)
    assert any(item.title == "Captured knowledge note" for item in timeline.items)
    assert any(item.title.startswith("Automation run:") for item in timeline.items)


def test_weekly_review_builds_cross_module_summary(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    target_date = date.today()
    started_at = datetime.combine(target_date - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    LearningService().create_session(
        LearningSessionCreate(
            subject=LearningSubject.japanese,
            duration_minutes=35,
            summary="Reviewed N3 cards.",
            started_at=started_at,
            ended_at=started_at + timedelta(minutes=35),
        )
    )
    subscription_service = SubscriptionService()
    created = subscription_service.create_subscription(
        SubscriptionCreate(
            name="ChatGPT Plus",
            amount=20.0,
            currency="USD",
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            category=SubscriptionCategory.ai,
        )
    )
    subscription_service.update_subscription(created.key, SubscriptionUpdate(notes="Primary AI tool"))
    WorkKnowledgeService().create_note(
        WorkKnowledgeNoteCreate(
            title="Systemd service status",
            category=WorkKnowledgeCategory.linux,
            sanitized_summary="Use systemctl status and journalctl together.",
            follow_up="Turn this into a checklist.",
        )
    )

    automation = AutomationService().create_definition(
        AutomationDefinitionCreate(
            key="open-anki",
            name="Open Anki",
            category=AutomationCategory.learning,
        )
    )
    AutomationService().create_run(
        automation.key,
        AutomationRunCreate(
            status=AutomationRunStatus.success,
            trigger_source=AutomationTriggerSource.cli,
            items_processed=1,
            summary="Launched desktop Anki.",
        ),
    )

    review = ReviewService().build_weekly_review(target_date=target_date)

    assert review.target_date == target_date
    assert review.learning.total_minutes == 35
    assert review.subscriptions.missing_schedule_count == 1
    assert review.automations.success_count == 1
    assert review.knowledge.follow_up_count == 1
    assert review.timeline
    assert review.keep_doing
    assert review.needs_attention
    assert review.next_week_focus


def test_activity_and_weekly_review_routes_and_page(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    with TestClient(app) as client:
        timeline_response = client.get("/activity/timeline")
        review_response = client.get("/reviews/weekly", params={"target_date": "2026-05-09"})
        page_response = client.get("/review/weekly")

    assert timeline_response.status_code == 200
    assert review_response.status_code == 200
    assert page_response.status_code == 200
    assert "LifeQuest Weekly Review" in page_response.text
