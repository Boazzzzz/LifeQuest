from datetime import date

from fastapi import APIRouter, Query

from app.models.dashboard import DashboardOverview
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    target_date: date | None = Query(default=None),
) -> DashboardOverview:
    return await DashboardService().build_overview(target_date=target_date)
