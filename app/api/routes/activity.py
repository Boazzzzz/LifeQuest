from fastapi import APIRouter, Query

from app.models.activity import ActivityTimelineOverview
from app.services.activity import ActivityService

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/timeline", response_model=ActivityTimelineOverview)
def get_recent_activity_timeline(limit: int = Query(default=20, ge=1, le=100)) -> ActivityTimelineOverview:
    return ActivityService().get_recent_timeline(limit=limit)
