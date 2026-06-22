from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["ui"])

_STATIC_ROOT = Path(__file__).resolve().parents[2] / "static"
_HOME_INDEX = _STATIC_ROOT / "dashboard" / "index.html"
_JAPANESE_INDEX = _STATIC_ROOT / "japanese" / "index.html"
_NIGHTLY_INDEX = _STATIC_ROOT / "nightly" / "index.html"
_WEEKLY_REVIEW_INDEX = _STATIC_ROOT / "weekly-review" / "index.html"
_SUBSCRIPTIONS_INDEX = _STATIC_ROOT / "subscriptions" / "index.html"
_MONEY_INDEX = _STATIC_ROOT / "money" / "index.html"


@router.get("/", include_in_schema=False)
def lifequest_home_page() -> FileResponse:
    return FileResponse(_HOME_INDEX)


@router.get("/dashboard", include_in_schema=False)
def lifequest_dashboard_page() -> FileResponse:
    return FileResponse(_HOME_INDEX)


@router.get("/life-admin/subscriptions", include_in_schema=False)
def lifequest_subscriptions_page() -> FileResponse:
    return FileResponse(_SUBSCRIPTIONS_INDEX)


@router.get("/life-admin/money", include_in_schema=False)
def lifequest_money_page() -> FileResponse:
    return FileResponse(_MONEY_INDEX)


@router.get("/japanese", include_in_schema=False)
def japanese_dashboard_page() -> FileResponse:
    return FileResponse(_JAPANESE_INDEX)


@router.get("/nightly", include_in_schema=False)
def nightly_checkin_page() -> FileResponse:
    return FileResponse(_NIGHTLY_INDEX)


@router.get("/checkin", include_in_schema=False)
def checkin_alias_page() -> FileResponse:
    return FileResponse(_NIGHTLY_INDEX)


@router.get("/review/weekly", include_in_schema=False)
def weekly_review_page() -> FileResponse:
    return FileResponse(_WEEKLY_REVIEW_INDEX)
