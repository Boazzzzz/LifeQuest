from datetime import date

from app.core.database import initialize_database
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

