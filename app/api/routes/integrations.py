from fastapi import APIRouter

from app.integrations.anki import AnkiAdapter, AnkiStatus
from app.integrations.github import GitHubAdapter, GitHubStatus

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/anki/status", response_model=AnkiStatus)
async def get_anki_status() -> AnkiStatus:
    return await AnkiAdapter().check_status()


@router.get("/github/status", response_model=GitHubStatus)
async def get_github_status() -> GitHubStatus:
    return await GitHubAdapter().check_status()
