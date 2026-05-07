from datetime import date

from fastapi.testclient import TestClient

from app.core.database import initialize_database
from app.integrations.anki import AnkiDailyStats
from app.main import app
from app.models.learning import LearningSessionCreate, LearningSubject
from app.services.learning import LearningService


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


def test_anki_status_endpoint_reports_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    with TestClient(app) as client:
        response = client.get("/integrations/anki/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["connected"] is False
