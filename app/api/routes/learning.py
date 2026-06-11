from datetime import date

from fastapi import APIRouter, Query

from app.integrations.anki import AnkiDailyStats
from app.integrations.github import GitHubDailyPythonActivity
from app.models.anki import (
    AnkiDifficultCardTrend,
    AnkiHistoryOverview,
    AnkiReviewedTodayOverview,
    AnkiTodayOverview,
)
from app.models.japanese import JapaneseDashboardOverview
from app.models.learning import (
    LearningCheckinDraft,
    LearningCheckinDraftRequest,
    LearningPulse,
    LearningSession,
    LearningSessionCreate,
    LearningSubject,
)
from app.services.learning import LearningService
from app.services.notion_sync import NotionSyncService

router = APIRouter(prefix="/learning", tags=["learning"])


@router.post("/sessions", response_model=LearningSession)
def create_learning_session(payload: LearningSessionCreate) -> LearningSession:
    return LearningService().create_session(payload)


@router.get("/sessions", response_model=list[LearningSession])
def list_learning_sessions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    target_date: date | None = Query(default=None, alias="date"),
    subject: LearningSubject | None = Query(default=None),
) -> list[LearningSession]:
    return LearningService().list_sessions(
        limit=limit,
        offset=offset,
        target_date=target_date,
        subject=subject,
    )


@router.post("/checkin/draft", response_model=LearningCheckinDraft)
def draft_learning_checkin(payload: LearningCheckinDraftRequest) -> LearningCheckinDraft:
    return LearningService().draft_checkin(payload.text)


@router.get("/pulse/today", response_model=LearningPulse)
async def get_today_learning_pulse() -> LearningPulse:
    return await LearningService().build_today_pulse()


@router.get("/anki/today", response_model=AnkiTodayOverview)
async def get_today_anki_overview() -> AnkiTodayOverview:
    return await LearningService().get_anki_today_overview()


@router.get("/anki/reviewed-today", response_model=AnkiReviewedTodayOverview)
async def get_anki_reviewed_today(target_date: date | None = Query(default=None, alias="date")) -> AnkiReviewedTodayOverview:
    return await LearningService().get_anki_reviewed_today_overview(target_date=target_date)


@router.get("/anki/history", response_model=AnkiHistoryOverview)
def get_anki_history(days: int = Query(default=7, ge=1, le=90)) -> AnkiHistoryOverview:
    return LearningService().get_anki_history(days=days)


@router.get("/anki/difficult-history", response_model=list[AnkiDifficultCardTrend])
def get_anki_difficult_history(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[AnkiDifficultCardTrend]:
    return LearningService().get_anki_difficult_card_history(days=days, limit=limit)


@router.get("/japanese/dashboard", response_model=JapaneseDashboardOverview)
async def get_japanese_dashboard(
    target_date: date | None = Query(default=None, alias="date"),
    history_days: int = Query(default=7, ge=1, le=30),
    difficult_days: int = Query(default=14, ge=1, le=60),
    difficult_limit: int = Query(default=10, ge=1, le=30),
) -> JapaneseDashboardOverview:
    return await LearningService().get_japanese_dashboard(
        target_date=target_date,
        history_days=history_days,
        difficult_days=difficult_days,
        difficult_limit=difficult_limit,
    )


@router.post("/import/anki/today", response_model=AnkiDailyStats)
async def import_today_anki_reviews() -> AnkiDailyStats:
    return await LearningService().import_anki_today()


@router.post("/import/github/today", response_model=GitHubDailyPythonActivity)
async def import_today_github_activity() -> GitHubDailyPythonActivity:
    return await LearningService().import_github_today()


@router.post("/pulse/today/sync-notion")
async def sync_today_learning_pulse_to_notion() -> dict[str, str]:
    pulse = await LearningService().build_today_pulse()
    return await NotionSyncService().sync_learning_pulse(pulse)
