from fastapi import APIRouter, HTTPException, Query, status

from app.models.japanese import JapaneseVerbForm, JapaneseVerbFormCreate
from app.services.japanese import JapaneseService, JapaneseVerbConjugationError, JapaneseVerbFormNotFoundError
from app.services.notion_sync import NotionSyncService

router = APIRouter(prefix="/japanese", tags=["japanese"])


@router.post("/verbs", response_model=JapaneseVerbForm, status_code=status.HTTP_201_CREATED)
def create_japanese_verb_form(payload: JapaneseVerbFormCreate) -> JapaneseVerbForm:
    try:
        return JapaneseService().create_verb_form(payload)
    except JapaneseVerbConjugationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get("/verbs", response_model=list[JapaneseVerbForm])
def list_japanese_verb_forms(limit: int = Query(default=100, ge=1, le=500)) -> list[JapaneseVerbForm]:
    return JapaneseService().list_verb_forms(limit=limit)


@router.post("/verbs/seed", response_model=list[JapaneseVerbForm])
def seed_basic_japanese_verb_forms() -> list[JapaneseVerbForm]:
    return JapaneseService().seed_basic_verb_forms()


@router.post("/verbs/sync-notion")
async def sync_japanese_verb_forms_to_notion() -> dict:
    verb_forms = JapaneseService().list_verb_forms(limit=500)
    return await NotionSyncService().sync_japanese_verb_forms(verb_forms)


@router.get("/verbs/{verb_form_id}", response_model=JapaneseVerbForm)
def get_japanese_verb_form(verb_form_id: str) -> JapaneseVerbForm:
    try:
        return JapaneseService().get_verb_form(verb_form_id)
    except JapaneseVerbFormNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
