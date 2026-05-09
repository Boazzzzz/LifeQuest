from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.core.database import connect
from app.core.database import initialize_database
from app.integrations.anki import AnkiAdapter
from app.integrations.anki import AnkiDailyStats
from app.integrations.github import GitHubDailyPythonActivity
from app.main import app
from app.models.anki import AnkiDailySnapshot
from app.models.learning import LearningSessionCreate, LearningSubject
from app.repositories.anki import AnkiSnapshotRepository
from app.services.learning import LearningService
from app.services.notion_sync import NotionSyncService


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


def test_learning_pulse_includes_github_python_activity(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)
    initialize_database()

    class FakeGitHubAdapter:
        async def get_daily_python_activity(self, target_date: date) -> GitHubDailyPythonActivity:
            return GitHubDailyPythonActivity(
                enabled=True,
                connected=True,
                commits=3,
                python_commits=2,
                repositories=["david/lifequest"],
                python_files=["app/main.py", "app/services/learning.py"],
                commit_messages=["Practice FastAPI", "Refine learning service"],
            )

    service = LearningService(github_adapter=FakeGitHubAdapter())
    pulse = __import__("asyncio").run(service.build_pulse(date.today()))

    assert pulse.github_commits == 3
    assert pulse.github_python_commits == 2
    assert pulse.github_repositories == ["david/lifequest"]
    assert pulse.github_python_files == ["app/main.py", "app/services/learning.py"]
    assert pulse.focus_score == 8


def test_import_anki_persists_daily_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeAnkiAdapter:
        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                reviews=55,
                accuracy=91.2,
                difficult_cards=["N3: grammar"],
                decks=["N3", "Core"],
            )

    service = LearningService(anki_adapter=FakeAnkiAdapter())
    stats = __import__("asyncio").run(service.import_anki_today())
    snapshot = service.get_anki_snapshot(date.today())
    overview = __import__("asyncio").run(service.get_anki_today_overview())

    assert stats.reviews == 55
    assert snapshot is not None
    assert snapshot.scope == "all_decks"
    assert snapshot.reviews == 55
    assert snapshot.again_count == 0
    assert snapshot.decks == ["N3", "Core"]
    assert overview.source == "snapshot"
    assert overview.reviews == 55


def test_learning_pulse_prefers_imported_anki_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class ImportingAnkiAdapter:
        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                reviews=30,
                accuracy=88.0,
                difficult_cards=["N3: vocab"],
                decks=["N3"],
            )

    class FailingAnkiAdapter:
        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            return AnkiDailyStats(
                enabled=True,
                connected=False,
                error="live adapter should not be needed after import",
            )

    importer = LearningService(anki_adapter=ImportingAnkiAdapter())
    __import__("asyncio").run(importer.import_anki_today())

    reader = LearningService(anki_adapter=FailingAnkiAdapter())
    pulse = __import__("asyncio").run(reader.build_pulse(date.today()))

    assert pulse.anki_reviews == 30
    assert pulse.anki_accuracy == 88.0
    assert pulse.integration_warnings == []


def test_anki_adapter_filters_to_configured_decks():
    class FakeAnkiAdapter(AnkiAdapter):
        def __init__(self) -> None:
            super().__init__(enabled=True, decks=["N3", "Missing Deck"])

        async def _invoke(self, action: str, params=None):
            if action == "deckNames":
                return ["N3", "N3::High Frequency", "N3::Low Frequency", "Core"]
            if action == "cardReviews":
                if params and params.get("deck") == "N3::High Frequency":
                    return [
                        [1, 101, 0, 1],
                        [2, 102, 0, 3],
                    ]
                if params and params.get("deck") == "N3::Low Frequency":
                    return [
                        [3, 103, 0, 3],
                    ]
                return []
            if action == "findCards":
                query = params.get("query") if params else ""
                if query == 'deck:"N3"':
                    return [101]
                if query == 'deck:"N3::High Frequency"':
                    return [101, 102]
                if query == 'deck:"N3::Low Frequency"':
                    return [103]
                return []
            if action == "areDue":
                cards = params.get("cards") if params else []
                return [card in {101, 103} for card in cards]
            if action == "cardsInfo":
                cards = set(params.get("cards", []) if params else [])
                all_cards = [
                    {
                        "deckName": "N3::High Frequency",
                        "fields": {"Front": {"value": "grammar point"}},
                        "cardId": 101,
                        "queue": 1,
                        "type": 1,
                    },
                    {
                        "deckName": "N3::High Frequency",
                        "fields": {"Front": {"value": "reading point"}},
                        "cardId": 102,
                        "queue": 2,
                        "type": 2,
                    },
                    {
                        "deckName": "N3::Low Frequency",
                        "fields": {"Front": {"value": "vocab point"}},
                        "cardId": 103,
                        "queue": 2,
                        "type": 2,
                    },
                ]
                return [card for card in all_cards if card["cardId"] in cards]
            raise AssertionError(f"unexpected action: {action}")

        def _date_range_ms(self, target_date: date) -> tuple[int, int]:
            return 0, 10

    stats = __import__("asyncio").run(FakeAnkiAdapter().get_daily_stats(date.today()))

    assert stats.scope == "configured_decks"
    assert stats.reviews == 3
    assert stats.again_count == 1
    assert stats.hard_count == 0
    assert stats.good_count == 2
    assert stats.easy_count == 0
    assert stats.non_again_rate == 66.7
    assert stats.due_count == 2
    assert stats.new_due_count == 0
    assert stats.learn_due_count == 1
    assert stats.review_due_count == 1
    assert stats.decks == ["N3", "N3::High Frequency", "N3::Low Frequency"]
    assert stats.configured_decks == ["N3", "Missing Deck"]
    assert stats.missing_decks == ["Missing Deck"]
    assert stats.difficult_cards == ["N3::High Frequency: grammar point"]


def test_anki_reviewed_today_groups_unique_cards():
    class FakeAnkiAdapter(AnkiAdapter):
        def __init__(self) -> None:
            super().__init__(enabled=True, decks=["N3"])

        async def _invoke(self, action: str, params=None):
            if action == "deckNames":
                return ["N3", "N3::High Frequency"]
            if action == "cardReviews":
                return [
                    [1000, 101, 0, 3],
                    [2000, 101, 0, 1],
                    [3000, 102, 0, 4],
                ]
            if action == "cardsInfo":
                cards = set(params.get("cards", []) if params else [])
                all_cards = [
                    {
                        "deckName": "N3::High Frequency",
                        "fields": {"Front": {"value": "grammar point"}},
                        "cardId": 101,
                    },
                    {
                        "deckName": "N3",
                        "fields": {"Front": {"value": "vocab point"}},
                        "cardId": 102,
                    },
                ]
                return [card for card in all_cards if card["cardId"] in cards]
            raise AssertionError(f"unexpected action: {action}")

        def _date_range_ms(self, target_date: date) -> tuple[int, int]:
            return 0, 5000

    overview = __import__("asyncio").run(FakeAnkiAdapter().get_reviewed_today_overview())

    assert overview.target_date == date.today()
    assert overview.total_reviews == 3
    assert overview.total_unique_cards == 2
    assert overview.cards[0].card_id == 102
    assert overview.cards[0].easy_count == 1
    assert overview.cards[1].card_id == 101
    assert overview.cards[1].review_count == 2
    assert overview.cards[1].again_count == 1
    assert overview.cards[1].good_count == 1


def test_anki_today_overview_includes_insight_fields(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeAnkiAdapter:
        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                scope="configured_decks",
                reviews=95,
                accuracy=72.4,
                again_count=14,
                difficult_cards=["N3: vocab", "N3: grammar"],
                decks=["N3"],
                configured_decks=["N3"],
            )

    overview = __import__("asyncio").run(LearningService(anki_adapter=FakeAnkiAdapter()).get_anki_today_overview())

    assert overview.scope == "configured_decks"
    assert overview.sync_status == "live_not_snapshotted"
    assert overview.due_count == 0
    assert overview.hard_count == 0
    assert overview.good_count == 0
    assert overview.easy_count == 0
    assert overview.review_load == "heavy"
    assert overview.summary == "Challenging Anki day: 95 reviews at 72.4% accuracy."
    assert overview.recommendation == "Slow down on the hardest cards and review leeches before adding new material."
    assert "run import-anki" in overview.sync_hint


def test_snapshot_overview_marks_stale_import(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeAnkiAdapter:
        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                reviews=10,
                accuracy=95.0,
                decks=["N3"],
            )

    service = LearningService(anki_adapter=FakeAnkiAdapter())
    __import__("asyncio").run(service.import_anki_today())
    snapshot = service.get_anki_snapshot(date.today())
    assert snapshot is not None
    snapshot.imported_at = snapshot.imported_at - timedelta(hours=7)

    overview = service.build_anki_overview(
        stats=AnkiDailyStats(
            enabled=True,
            connected=True,
            reviews=snapshot.reviews,
            accuracy=snapshot.accuracy,
            again_count=snapshot.again_count,
            decks=snapshot.decks,
        ),
        source="snapshot",
        imported_at=snapshot.imported_at,
    )

    assert overview.sync_status == "snapshot_may_be_stale"


def test_anki_history_and_difficult_card_trends(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    repository = AnkiSnapshotRepository()
    repository.upsert_daily_snapshot(
        AnkiDailySnapshot(
            snapshot_date=date(2026, 5, 7),
            reviews=46,
            accuracy=100.0,
            non_again_rate=100.0,
            again_count=0,
            hard_count=4,
            good_count=38,
            easy_count=4,
            due_count=12,
            difficult_cards=[],
            imported_at=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.upsert_daily_snapshot(
        AnkiDailySnapshot(
            snapshot_date=date(2026, 5, 6),
            reviews=30,
            accuracy=80.0,
            non_again_rate=80.0,
            again_count=3,
            hard_count=5,
            good_count=20,
            easy_count=2,
            due_count=18,
            difficult_cards=["Card A", "Card B"],
            imported_at=datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.upsert_daily_snapshot(
        AnkiDailySnapshot(
            snapshot_date=date(2026, 5, 5),
            reviews=20,
            accuracy=70.0,
            non_again_rate=70.0,
            again_count=5,
            hard_count=4,
            good_count=10,
            easy_count=1,
            due_count=22,
            difficult_cards=["Card A"],
            imported_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        )
    )

    service = LearningService(anki_snapshot_repository=repository)
    history = service.get_anki_history(days=7)
    trends = service.get_anki_difficult_card_history(days=7)

    assert history.streak_days == 3
    assert history.total_reviews == 96
    assert history.average_accuracy == 83.3
    assert history.best_review_day == date(2026, 5, 7)
    assert [day.snapshot_date for day in history.days] == [date(2026, 5, 5), date(2026, 5, 6), date(2026, 5, 7)]
    assert history.days[-1].good_count == 38
    assert history.days[-1].easy_count == 4
    assert trends[0].label == "Card A"
    assert trends[0].hit_count == 2


def test_anki_status_endpoint_reports_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    with TestClient(app) as client:
        response = client.get("/integrations/anki/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["connected"] is False


def test_github_status_endpoint_reports_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)

    with TestClient(app) as client:
        response = client.get("/integrations/github/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["connected"] is False


def test_anki_today_endpoint_reports_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    with TestClient(app) as client:
        response = client.get("/learning/anki/today")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["source"] == "live"


def test_japanese_dashboard_endpoint_reports_disabled_anki(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)

    with TestClient(app) as client:
        response = client.get("/learning/japanese/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["anki_today"]["enabled"] is False
    assert payload["reviewed_today"]["enabled"] is False
    assert payload["japanese_minutes"] == 0
    assert payload["history"]["days"] == []


def test_japanese_dashboard_page_serves_html(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")

    with TestClient(app) as client:
        response = client.get("/japanese")

    assert response.status_code == 200
    assert "LifeQuest 日文學習儀表板" in response.text
    assert 'id="root"' in response.text


def test_cli_log_records_learning_session(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")

    exit_code = cli_main(["log", "japanese", "20", "N3", "grammar", "--tag", "n3"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Logged japanese for 20 min" in captured.out

    service = LearningService()
    sessions = service.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].summary == "N3 grammar"
    assert sessions[0].tags == ["n3"]


def test_cli_anki_status_reports_disabled(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    exit_code = cli_main(["anki-status"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Anki status: disabled" in captured.out


def test_cli_import_anki_reports_disabled(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    exit_code = cli_main(["import-anki"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Anki import skipped: ANKI_ENABLED=false" in captured.out


def test_cli_anki_today_reports_disabled(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    exit_code = cli_main(["anki-today"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Anki today: disabled" in captured.out


def test_cli_anki_reviewed_today_reports_disabled(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)

    exit_code = cli_main(["anki-reviewed-today"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Anki reviewed today: disabled" in captured.out


def test_cli_daily_reports_disabled_anki_and_pulse(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)

    exit_code = cli_main(["daily"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Daily check" in captured.out
    assert "Anki: disabled" in captured.out
    assert "Learning pulse" in captured.out


def test_notion_service_builds_data_source_parent(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.notion_learning_pulse_data_source_id", "source-id")
    monkeypatch.setattr("app.core.config.settings.notion_learning_pulse_database_id", None)
    monkeypatch.setattr("app.core.config.settings.notion_api_version", None)

    service = NotionSyncService()

    assert service._learning_pulse_parent() == {"type": "data_source_id", "data_source_id": "source-id"}
    assert service.api_version == "2025-09-03"


def test_mssql_backend_requires_connection_string(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_backend", "mssql")
    monkeypatch.setattr("app.core.database.settings.database_backend", "mssql")
    monkeypatch.setattr("app.core.config.settings.mssql_connection_string", None)
    monkeypatch.setattr("app.core.database.settings.mssql_connection_string", None)

    with pytest.raises(RuntimeError, match="MSSQL_CONNECTION_STRING"):
        with connect():
            pass
