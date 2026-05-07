from fastapi import APIRouter, Query

from app.models.learning import LearningPulse, LearningSession, LearningSessionCreate
from app.services.learning import LearningService
from app.services.notion_sync import NotionSyncService

router = APIRouter(prefix="/learning", tags=["learning"])


@router.post("/sessions", response_model=LearningSession)
def create_learning_session(payload: LearningSessionCreate) -> LearningSession:
    return LearningService().create_session(payload)


@router.get("/sessions", response_model=list[LearningSession])
def list_learning_sessions(limit: int = Query(default=100, ge=1, le=500)) -> list[LearningSession]:
    return LearningService().list_sessions(limit=limit)


@router.get("/pulse/today", response_model=LearningPulse)
async def get_today_learning_pulse() -> LearningPulse:
    return await LearningService().build_today_pulse()


@router.post("/pulse/today/sync-notion")
async def sync_today_learning_pulse_to_notion() -> dict[str, str]:
    pulse = await LearningService().build_today_pulse()
    return await NotionSyncService().sync_learning_pulse(pulse)

