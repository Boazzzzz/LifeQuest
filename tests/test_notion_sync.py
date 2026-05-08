from datetime import date

from app.models.automation import AutomationCategory, AutomationDefinition, AutomationRunStatus
from app.models.learning import LearningPulse
from app.models.work_knowledge import (
    WorkKnowledgeCategory,
    WorkKnowledgeNote,
    WorkKnowledgeSensitivity,
    WorkKnowledgeSource,
)
from app.services.notion_sync import NotionSyncService


def test_learning_pulse_notion_properties_match_schema():
    pulse = LearningPulse(
        date=date(2026, 5, 8),
        python_minutes=45,
        japanese_minutes=30,
        total_minutes=75,
        session_count=2,
        anki_reviews=80,
        anki_accuracy=82.5,
        anki_difficult_cards=["Japanese::N3: 承知"],
        github_commits=3,
        github_python_commits=2,
        github_repositories=["Boazzzzz/LifeQuest"],
        github_python_files=["app/main.py"],
        focus_score=60,
        summary="Python 45 min, Japanese 30 min",
        tomorrow_priority="Review N3 grammar and practice FastAPI.",
        integration_warnings=[],
    )

    properties = NotionSyncService()._build_learning_pulse_properties(pulse)

    assert set(properties) == {
        "Date",
        "Name",
        "Python Minutes",
        "Japanese Minutes",
        "Total Minutes",
        "Session Count",
        "Anki Reviews",
        "Anki Accuracy",
        "GitHub Commits",
        "GitHub Python Commits",
        "Focus Score",
        "Summary",
        "Tomorrow Priority",
        "Anki Difficult Cards",
        "GitHub Repositories",
        "GitHub Python Files",
        "Integration Warnings",
    }
    assert properties["Date"] == {"date": {"start": "2026-05-08"}}
    assert properties["Python Minutes"] == {"number": 45}
    assert properties["GitHub Python Commits"] == {"number": 2}


def test_automation_notion_properties_match_schema():
    automation = AutomationDefinition(
        key="raindrop-classifier",
        name="Raindrop Unsorted Classifier",
        category=AutomationCategory.knowledge,
        external_project_path="/projects/raindrop",
        command_hint="python classify.py",
        schedule_hint="daily",
        log_path="/logs/raindrop.log",
        owner="David",
        enabled=True,
        notes="Existing external project.",
        tags=["raindrop", "bookmarks"],
        last_run_status=AutomationRunStatus.success,
        last_run_summary="Tagged 42 bookmarks.",
    )

    properties = NotionSyncService()._build_automation_properties(automation)

    assert set(properties) == {
        "Name",
        "Key",
        "Category",
        "Enabled",
        "Tags",
        "External Project Path",
        "Command Hint",
        "Schedule Hint",
        "Log Path",
        "Owner",
        "Notes",
        "Last Run At",
        "Last Run Status",
        "Last Run Summary",
        "Updated At",
    }
    assert properties["Key"] == {"rich_text": [{"text": {"content": "raindrop-classifier"}}]}
    assert properties["Category"] == {"select": {"name": "knowledge"}}
    assert properties["Enabled"] == {"checkbox": True}
    assert properties["Last Run Status"] == {"select": {"name": "success"}}


def test_work_knowledge_notion_properties_match_schema():
    note = WorkKnowledgeNote(
        id="note-1",
        title="Nginx 502 troubleshooting pattern",
        category=WorkKnowledgeCategory.nginx,
        sanitized_summary="A 502 often means the proxy cannot reach upstream.",
        commands=["systemctl status", "journalctl -u service"],
        concepts=["reverse proxy", "upstream health"],
        source=WorkKnowledgeSource.manual,
        sensitivity=WorkKnowledgeSensitivity.personal,
        systems=["linux"],
        follow_up="Review upstream health checks.",
        tags=["troubleshooting"],
    )

    properties = NotionSyncService()._build_work_knowledge_properties(note)

    assert set(properties) == {
        "Name",
        "LifeQuest ID",
        "Category",
        "Sanitized Summary",
        "Commands",
        "Concepts",
        "Source",
        "Sensitivity",
        "Systems",
        "Follow Up",
        "Tags",
        "Created At",
        "Updated At",
    }
    assert properties["LifeQuest ID"] == {"rich_text": [{"text": {"content": "note-1"}}]}
    assert properties["Category"] == {"select": {"name": "nginx"}}
    assert properties["Sensitivity"] == {"select": {"name": "personal"}}

