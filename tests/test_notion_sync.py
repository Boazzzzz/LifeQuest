from datetime import date

from app.models.learning import LearningPulse
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
