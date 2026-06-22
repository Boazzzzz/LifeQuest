import asyncio
from datetime import date

from fastapi.testclient import TestClient

from app.core.database import initialize_database
from app.main import app
from app.models.learning import LearningPulse
from app.services.game import GameQuestActionError, GameService


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    initialize_database()


class FakeLearningService:
    def __init__(
        self,
        *,
        python_minutes: int = 0,
        japanese_minutes: int = 0,
        anki_reviews: int = 0,
    ) -> None:
        self.python_minutes = python_minutes
        self.japanese_minutes = japanese_minutes
        self.anki_reviews = anki_reviews

    async def build_pulse(self, target_date: date) -> LearningPulse:
        return LearningPulse(
            date=target_date,
            python_minutes=self.python_minutes,
            japanese_minutes=self.japanese_minutes,
            total_minutes=self.python_minutes + self.japanese_minutes,
            session_count=0,
            anki_reviews=self.anki_reviews,
            focus_score=0,
            summary="fake pulse",
            tomorrow_priority="keep going",
        )


def quest_by_key(board, key: str):
    return next(quest for quest in board.quests if quest.key == key)


def test_daily_board_starts_with_gentle_pending_quests(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = GameService(learning_service=FakeLearningService())

    board = asyncio.run(service.build_daily_board(date.fromisoformat("2026-05-21")))

    assert board.completed_count == 0
    assert board.skipped_count == 0
    assert board.earned_xp == 0
    assert board.available_xp == 100
    assert quest_by_key(board, "python-focus").status == "pending"
    assert quest_by_key(board, "japanese-review").status == "pending"
    assert "不扣分" in board.gentle_message


def test_daily_board_completes_python_from_learning_pulse(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = GameService(learning_service=FakeLearningService(python_minutes=25))

    board = asyncio.run(service.build_daily_board(date.fromisoformat("2026-05-21")))

    quest = quest_by_key(board, "python-focus")
    assert quest.status == "completed"
    assert quest.completion_source == "learning_signal"
    assert board.earned_xp == 30


def test_daily_board_completes_japanese_from_anki_reviews(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = GameService(learning_service=FakeLearningService(anki_reviews=1))

    board = asyncio.run(service.build_daily_board(date.fromisoformat("2026-05-21")))

    quest = quest_by_key(board, "japanese-review")
    assert quest.status == "completed"
    assert quest.progress_label == "日文 0/15 分鐘，Anki 1 張"
    assert board.earned_xp == 25


def test_manual_complete_and_skip_are_recorded_for_the_day(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = GameService(learning_service=FakeLearningService())
    target_date = date.fromisoformat("2026-05-21")

    board = asyncio.run(service.complete_quest("life-admin-check", target_date))
    board = asyncio.run(service.skip_quest("daily-brief", target_date))

    assert quest_by_key(board, "life-admin-check").status == "completed"
    assert quest_by_key(board, "daily-brief").status == "skipped"
    assert board.completed_count == 1
    assert board.skipped_count == 1
    assert board.earned_xp == 10


def test_skip_does_not_override_completed_learning_signal(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = GameService(learning_service=FakeLearningService(python_minutes=30))
    target_date = date.fromisoformat("2026-05-21")

    board = asyncio.run(service.skip_quest("python-focus", target_date))

    quest = quest_by_key(board, "python-focus")
    assert quest.status == "completed"
    assert quest.completion_source == "learning_signal"
    assert board.earned_xp == 30


def test_learning_signal_quest_cannot_be_manually_completed(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = GameService(learning_service=FakeLearningService())

    try:
        asyncio.run(service.complete_quest("python-focus", date.fromisoformat("2026-05-21")))
    except GameQuestActionError as error:
        assert "automatically" in str(error)
    else:
        raise AssertionError("Expected auto quest manual completion to be rejected")


def test_game_api_daily_board_complete_skip_and_unknown_quest(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    with TestClient(app) as client:
        board_response = client.get("/game/daily-board", params={"target_date": "2026-05-21"})
        complete_response = client.post(
            "/game/daily-board/life-admin-check/complete",
            params={"target_date": "2026-05-21"},
        )
        skip_response = client.post(
            "/game/daily-board/daily-brief/skip",
            params={"target_date": "2026-05-21"},
        )
        unknown_response = client.post(
            "/game/daily-board/not-real/skip",
            params={"target_date": "2026-05-21"},
        )

    assert board_response.status_code == 200
    assert complete_response.status_code == 200
    assert skip_response.status_code == 200
    assert unknown_response.status_code == 404
    assert complete_response.json()["earned_xp"] == 10
    assert skip_response.json()["skipped_count"] == 1
