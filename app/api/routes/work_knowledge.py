from fastapi import APIRouter, HTTPException, Query, status

from app.models.work_knowledge import WorkKnowledgeNote, WorkKnowledgeNoteCreate
from app.services.notion_sync import NotionSyncService
from app.services.work_knowledge import WorkKnowledgeNotFoundError, WorkKnowledgeService

router = APIRouter(prefix="/work-knowledge", tags=["work-knowledge"])


@router.post("", response_model=WorkKnowledgeNote, status_code=status.HTTP_201_CREATED)
def create_work_knowledge_note(payload: WorkKnowledgeNoteCreate) -> WorkKnowledgeNote:
    return WorkKnowledgeService().create_note(payload)


@router.get("", response_model=list[WorkKnowledgeNote])
def list_work_knowledge_notes(limit: int = Query(default=100, ge=1, le=500)) -> list[WorkKnowledgeNote]:
    return WorkKnowledgeService().list_notes(limit=limit)


@router.post("/sync-notion")
async def sync_work_knowledge_to_notion() -> dict:
    notes = WorkKnowledgeService().list_notes(limit=500)
    return await NotionSyncService().sync_work_knowledge(notes)


@router.get("/{note_id}", response_model=WorkKnowledgeNote)
def get_work_knowledge_note(note_id: str) -> WorkKnowledgeNote:
    try:
        return WorkKnowledgeService().get_note(note_id)
    except WorkKnowledgeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
