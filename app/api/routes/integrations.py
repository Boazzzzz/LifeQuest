from fastapi import APIRouter

from app.integrations.anki import AnkiAdapter, AnkiStatus

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/anki/status", response_model=AnkiStatus)
async def get_anki_status() -> AnkiStatus:
    return await AnkiAdapter().check_status()
