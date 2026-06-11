from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.cli import main as cli_main
from app.core.database import connect
from app.core.database import initialize_database
from app.integrations.anki import AnkiAdapter
from app.integrations.anki import AnkiDailyStats
from app.integrations.github import GitHubDailyPythonActivity
from app.integrations.openai_checkin import OpenAICheckinDraftAdapter, OpenAICheckinDraftError
from app.main import app
from app.models.anki import AnkiDailySnapshot, AnkiReviewedTodayOverview
from app.models.learning import LearningCheckinDraft, LearningSessionCreate, LearningSubject
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


def test_learning_pulse_counts_sre_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)
    initialize_database()

    service = LearningService()
    service.create_session(
        LearningSessionCreate(
            subject=LearningSubject.sre,
            duration_minutes=30,
            summary="Practiced Linux incident triage.",
            started_at=datetime(2026, 5, 20, 17, 0, tzinfo=timezone.utc),
        )
    )

    pulse = __import__("asyncio").run(service.build_pulse(date(2026, 5, 21)))

    assert pulse.sre_minutes == 30
    assert pulse.total_minutes == 30
    assert "SRE 30 min" in pulse.summary


def test_learning_pulse_uses_local_learning_day_boundaries(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.config.settings.anki_enabled", False)
    monkeypatch.setattr("app.core.config.settings.github_enabled", False)
    initialize_database()

    service = LearningService()
    service.create_session(
        LearningSessionCreate(
            subject=LearningSubject.japanese,
            duration_minutes=25,
            summary="Late night local review.",
            started_at=datetime(2026, 5, 10, 16, 30, tzinfo=timezone.utc),
        )
    )

    previous_day = __import__("asyncio").run(service.build_pulse(date(2026, 5, 10)))
    local_day = __import__("asyncio").run(service.build_pulse(date(2026, 5, 11)))

    assert previous_day.total_minutes == 0
    assert local_day.japanese_minutes == 25
    assert local_day.total_minutes == 25


def test_learning_session_create_validates_time_window_and_normalizes_tags():
    payload = LearningSessionCreate(
        subject=LearningSubject.python,
        duration_minutes=30,
        summary="Practice.",
        started_at=datetime(2026, 5, 11, 9, 0),
        ended_at=datetime(2026, 5, 11, 9, 30),
        tags=[" fastapi ", "FastAPI", "", "routing"],
    )

    assert payload.started_at == datetime(2026, 5, 11, 1, 0, tzinfo=timezone.utc)
    assert payload.ended_at == datetime(2026, 5, 11, 1, 30, tzinfo=timezone.utc)
    assert payload.tags == ["fastapi", "routing"]

    with pytest.raises(ValidationError, match="ended_at must be later"):
        LearningSessionCreate(
            subject=LearningSubject.python,
            duration_minutes=30,
            summary="Broken.",
            started_at=datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 5, 11, 9, 30, tzinfo=timezone.utc),
        )

    with pytest.raises(ValidationError, match="duration_minutes must match"):
        LearningSessionCreate(
            subject=LearningSubject.python,
            duration_minutes=30,
            summary="Mismatch.",
            started_at=datetime(2026, 5, 11, 9, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 5, 11, 10, 0, tzinfo=timezone.utc),
        )


def test_learning_service_drafts_checkin_from_free_text():
    class DisabledOpenAIAdapter:
        enabled = False

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            raise AssertionError("disabled adapter should not be called")

    draft = LearningService(openai_checkin_adapter=DisabledOpenAIAdapter()).draft_checkin(
        "今天 Anki 複習 18 分鐘，另外看了 N3 文法。ている 還有點卡。"
    )

    assert draft.subject == LearningSubject.japanese
    assert draft.duration_minutes == 18
    assert draft.draft_source == "local"
    assert draft.warnings == ["AI 未設定，先用本地整理。"]
    assert "Anki" in draft.summary
    assert "複習，另外" in draft.summary
    assert "nightly-checkin" in draft.tags
    assert "japanese" in draft.tags
    assert "anki" in draft.tags
    assert "grammar" in draft.tags
    assert "18 分鐘" in draft.assistant_note


def test_learning_service_drafts_python_and_sre_checkins():
    class DisabledOpenAIAdapter:
        enabled = False

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            raise AssertionError("disabled adapter should not be called")

    service = LearningService(openai_checkin_adapter=DisabledOpenAIAdapter())
    python_draft = service.draft_checkin("Python FastAPI route 測了 1.5 hours，順便補 pytest。")
    sre_draft = service.draft_checkin("Kubernetes nginx ingress 排障 45 min")

    assert python_draft.subject == LearningSubject.python
    assert python_draft.duration_minutes == 90
    assert python_draft.tags == ["nightly-checkin", "python", "fastapi", "pytest"]

    assert sre_draft.subject == LearningSubject.sre
    assert sre_draft.duration_minutes == 45
    assert "kubernetes" in sre_draft.tags
    assert "nginx" in sre_draft.tags


def test_openai_checkin_adapter_requests_structured_output_schema():
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output_text": (
                    '{"subject":"japanese","duration_minutes":18,"summary":"Anki 複習和 N3 文法",'
                    '"difficulty":null,"energy_level":null,'
                    '"tags":["nightly-checkin","japanese","anki","grammar"],'
                    '"assistant_note":"我已整理成日文 18 分鐘。"}'
                )
            }

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    adapter = OpenAICheckinDraftAdapter(
        api_key="test-key",
        model="gpt-5.4-mini",
        timeout_seconds=3,
        client_factory=FakeClient,
    )
    draft = adapter.draft_checkin("今天 Anki 複習 18 分鐘，另外看了 N3 文法。")

    assert draft.draft_source == "ai"
    assert draft.subject == LearningSubject.japanese
    assert draft.duration_minutes == 18
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "gpt-5.4-mini"
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True
    assert captured["json"]["text"]["format"]["schema"]["properties"]["subject"]["enum"] == [
        "python",
        "japanese",
        "sre",
    ]


def test_openai_checkin_adapter_rejects_invalid_response_schema():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": '{"subject":"music","duration_minutes":18}'}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def post(self, url, headers, json):
            return FakeResponse()

    adapter = OpenAICheckinDraftAdapter(api_key="test-key", client_factory=FakeClient)

    with pytest.raises(OpenAICheckinDraftError):
        adapter.draft_checkin("整理這段")


def test_learning_service_uses_ai_draft_when_available():
    class FakeOpenAIAdapter:
        enabled = True

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            return LearningCheckinDraft(
                subject=LearningSubject.python,
                duration_minutes=35,
                summary="FastAPI route 測試",
                difficulty=None,
                energy_level=None,
                tags=["nightly-checkin", "python", "fastapi"],
                original_text=text,
                assistant_note="AI 已整理成 Python 35 分鐘。",
                draft_source="ai",
            )

    draft = LearningService(openai_checkin_adapter=FakeOpenAIAdapter()).draft_checkin("Python FastAPI route 測了 35 分鐘")

    assert draft.draft_source == "ai"
    assert draft.subject == LearningSubject.python
    assert draft.warnings == []


def test_learning_service_falls_back_when_ai_draft_fails():
    class FailingOpenAIAdapter:
        enabled = True

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            raise OpenAICheckinDraftError("boom")

    draft = LearningService(openai_checkin_adapter=FailingOpenAIAdapter()).draft_checkin("Kubernetes nginx ingress 排障 45 min")

    assert draft.draft_source == "local"
    assert draft.subject == LearningSubject.sre
    assert draft.duration_minutes == 45
    assert draft.warnings == ["AI 暫時不可用，先用本地整理。"]


def test_learning_service_skips_ai_when_api_key_is_missing():
    class DisabledOpenAIAdapter:
        enabled = False

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            raise AssertionError("disabled adapter should not be called")

    draft = LearningService(openai_checkin_adapter=DisabledOpenAIAdapter()).draft_checkin("Python pytest 20 min")

    assert draft.draft_source == "local"
    assert draft.subject == LearningSubject.python
    assert draft.warnings == ["AI 未設定，先用本地整理。"]


def test_learning_service_lists_sessions_with_limit_and_offset(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    service = LearningService()
    for started_at, summary in [
        (datetime(2026, 5, 7, 9, 0, tzinfo=timezone.utc), "Oldest session"),
        (datetime(2026, 5, 8, 9, 0, tzinfo=timezone.utc), "Middle session"),
        (datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc), "Newest session"),
    ]:
        service.create_session(
            LearningSessionCreate(
                subject=LearningSubject.python,
                duration_minutes=30,
                summary=summary,
                started_at=started_at,
            )
        )

    first_page = service.list_sessions(limit=2, offset=0)
    second_page = service.list_sessions(limit=2, offset=2)

    assert [session.summary for session in first_page] == ["Newest session", "Middle session"]
    assert [session.summary for session in second_page] == ["Oldest session"]


def test_learning_service_lists_sessions_with_date_and_subject_filters(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    service = LearningService()
    for subject, started_at, summary in [
        (LearningSubject.python, datetime(2026, 5, 10, 15, 0, tzinfo=timezone.utc), "Previous local day"),
        (LearningSubject.python, datetime(2026, 5, 10, 16, 30, tzinfo=timezone.utc), "Python local day"),
        (LearningSubject.japanese, datetime(2026, 5, 11, 1, 0, tzinfo=timezone.utc), "Japanese local day"),
    ]:
        service.create_session(
            LearningSessionCreate(
                subject=subject,
                duration_minutes=20,
                summary=summary,
                started_at=started_at,
            )
        )

    sessions = service.list_sessions(target_date=date(2026, 5, 11), subject=LearningSubject.python)

    assert [session.summary for session in sessions] == ["Python local day"]


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


def test_anki_adapter_closes_desktop_with_ankiconnect_action():
    actions = []

    class FakeAnkiAdapter(AnkiAdapter):
        def __init__(self) -> None:
            super().__init__(enabled=True)

        async def _invoke(self, action: str, params=None):
            actions.append((action, params))
            return None

    __import__("asyncio").run(FakeAnkiAdapter().close_desktop())

    assert actions == [("guiExitAnki", None)]


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


def test_nightly_checkin_page_serves_html(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")

    with TestClient(app) as client:
        response = client.get("/nightly")
        alias_response = client.get("/checkin")

    assert response.status_code == 200
    assert alias_response.status_code == 200
    assert "LifeQuest Nightly Check-in" in response.text
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


def test_learning_sessions_api_supports_offset_pagination(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    with TestClient(app) as client:
        for started_at, summary in [
            ("2026-05-07T09:00:00Z", "Oldest session"),
            ("2026-05-08T09:00:00Z", "Middle session"),
            ("2026-05-09T09:00:00Z", "Newest session"),
        ]:
            response = client.post(
                "/learning/sessions",
                json={
                    "subject": "python",
                    "duration_minutes": 20,
                    "summary": summary,
                    "started_at": started_at,
                },
            )
            assert response.status_code == 200

        response = client.get("/learning/sessions", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert [session["summary"] for session in response.json()] == ["Middle session"]


def test_learning_sessions_api_supports_date_and_subject_filters(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    with TestClient(app) as client:
        for subject, started_at, summary in [
            ("python", "2026-05-10T15:00:00Z", "Previous local day"),
            ("python", "2026-05-10T16:30:00Z", "Python local day"),
            ("japanese", "2026-05-11T01:00:00Z", "Japanese local day"),
        ]:
            response = client.post(
                "/learning/sessions",
                json={
                    "subject": subject,
                    "duration_minutes": 20,
                    "summary": summary,
                    "started_at": started_at,
                },
            )
            assert response.status_code == 200

        response = client.get(
            "/learning/sessions",
            params={"date": "2026-05-11", "subject": "python"},
        )

    assert response.status_code == 200
    assert [session["summary"] for session in response.json()] == ["Python local day"]


def test_learning_checkin_draft_endpoint_structures_free_text(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class DisabledOpenAIAdapter:
        enabled = False

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            raise AssertionError("disabled adapter should not be called")

    monkeypatch.setattr("app.services.learning.OpenAICheckinDraftAdapter", DisabledOpenAIAdapter)

    with TestClient(app) as client:
        response = client.post(
            "/learning/checkin/draft",
            json={"text": "今天 Linux systemd journal 看了 30 分鐘，整理 nginx 502 排障。"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "sre"
    assert payload["duration_minutes"] == 30
    assert "nightly-checkin" in payload["tags"]
    assert "linux" in payload["tags"]
    assert "nginx" in payload["tags"]


def test_learning_checkin_draft_endpoint_returns_ai_source_when_adapter_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeOpenAIAdapter:
        enabled = True

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            return LearningCheckinDraft(
                subject=LearningSubject.python,
                duration_minutes=40,
                summary="FastAPI 測試",
                tags=["nightly-checkin", "python", "fastapi"],
                original_text=text,
                assistant_note="AI 已整理成 Python 40 分鐘。",
                draft_source="ai",
            )

    monkeypatch.setattr("app.services.learning.OpenAICheckinDraftAdapter", FakeOpenAIAdapter)

    with TestClient(app) as client:
        response = client.post("/learning/checkin/draft", json={"text": "Python FastAPI 測了 40 分鐘"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_source"] == "ai"
    assert payload["subject"] == "python"
    assert payload["warnings"] == []


def test_learning_checkin_draft_endpoint_falls_back_when_adapter_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class FakeOpenAIAdapter:
        enabled = True

        def draft_checkin(self, text: str) -> LearningCheckinDraft:
            raise OpenAICheckinDraftError("boom")

    monkeypatch.setattr("app.services.learning.OpenAICheckinDraftAdapter", FakeOpenAIAdapter)

    with TestClient(app) as client:
        response = client.post("/learning/checkin/draft", json={"text": "Kubernetes nginx ingress 排障 45 min"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_source"] == "local"
    assert payload["subject"] == "sre"
    assert payload["duration_minutes"] == 45
    assert payload["warnings"] == ["AI 暫時不可用，先用本地整理。"]


def test_japanese_dashboard_reuses_anki_and_github_stats_for_pulse(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr("app.core.database.settings.database_path", tmp_path / "lifequest.db")
    initialize_database()

    class CountingAnkiAdapter:
        def __init__(self) -> None:
            self.daily_stats_calls = 0

        async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
            self.daily_stats_calls += 1
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                reviews=12,
                accuracy=90.0,
                decks=["N3"],
            )

        async def get_reviewed_today_overview(self, target_date: date | None = None) -> AnkiReviewedTodayOverview:
            return AnkiReviewedTodayOverview(
                enabled=True,
                connected=True,
                target_date=target_date or date.today(),
                total_reviews=12,
                total_unique_cards=10,
                decks=["N3"],
            )

    class CountingGitHubAdapter:
        def __init__(self) -> None:
            self.daily_activity_calls = 0

        async def get_daily_python_activity(self, target_date: date) -> GitHubDailyPythonActivity:
            self.daily_activity_calls += 1
            return GitHubDailyPythonActivity(
                enabled=True,
                connected=True,
                commits=1,
                python_commits=1,
            )

    anki_adapter = CountingAnkiAdapter()
    github_adapter = CountingGitHubAdapter()
    service = LearningService(anki_adapter=anki_adapter, github_adapter=github_adapter)

    dashboard = __import__("asyncio").run(service.get_japanese_dashboard(target_date=date(2026, 5, 11)))

    assert dashboard.pulse.anki_reviews == 12
    assert dashboard.anki_today.reviews == 12
    assert anki_adapter.daily_stats_calls == 1
    assert github_adapter.daily_activity_calls == 1


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
