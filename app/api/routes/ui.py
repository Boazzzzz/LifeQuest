from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["ui"])

_STATIC_ROOT = Path(__file__).resolve().parents[2] / "static"
_HOME_INDEX = _STATIC_ROOT / "dashboard" / "index.html"
_JAPANESE_INDEX = _STATIC_ROOT / "japanese" / "index.html"
_SUBSCRIPTIONS_INDEX = _STATIC_ROOT / "subscriptions" / "index.html"


@router.get("/", include_in_schema=False)
def lifequest_home_page() -> FileResponse:
    return FileResponse(_HOME_INDEX)


@router.get("/dashboard", include_in_schema=False)
def lifequest_dashboard_page() -> FileResponse:
    return FileResponse(_HOME_INDEX)


@router.get("/life-admin/subscriptions", include_in_schema=False)
def lifequest_subscriptions_page() -> FileResponse:
    return FileResponse(_SUBSCRIPTIONS_INDEX)


@router.get("/japanese", include_in_schema=False)
def japanese_dashboard_page() -> FileResponse:
    return FileResponse(_JAPANESE_INDEX)
