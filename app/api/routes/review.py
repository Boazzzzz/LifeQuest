from datetime import date

from fastapi import APIRouter, Query

from app.models.review import WeeklyReviewOverview
from app.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/weekly", response_model=WeeklyReviewOverview)
def get_weekly_review(target_date: date | None = Query(default=None)) -> WeeklyReviewOverview:
    return ReviewService().build_weekly_review(target_date=target_date)
