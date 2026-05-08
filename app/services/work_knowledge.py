from datetime import datetime, timezone

from app.models.work_knowledge import WorkKnowledgeNote, WorkKnowledgeNoteCreate
from app.repositories.work_knowledge import WorkKnowledgeRepository


class WorkKnowledgeNotFoundError(ValueError):
    pass


class WorkKnowledgeService:
    def __init__(self, repository: WorkKnowledgeRepository | None = None) -> None:
        self.repository = repository or WorkKnowledgeRepository()

    def create_note(self, payload: WorkKnowledgeNoteCreate) -> WorkKnowledgeNote:
        now = datetime.now(timezone.utc)
        note = WorkKnowledgeNote(
            title=payload.title,
            category=payload.category,
            sanitized_summary=payload.sanitized_summary,
            commands=payload.commands,
            concepts=payload.concepts,
            source=payload.source,
            sensitivity=payload.sensitivity,
            systems=payload.systems,
            follow_up=payload.follow_up,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_note(note)

    def list_notes(self, limit: int = 100) -> list[WorkKnowledgeNote]:
        return self.repository.list_notes(limit=limit)

    def get_note(self, note_id: str) -> WorkKnowledgeNote:
        note = self.repository.get_note(note_id)
        if note is None:
            raise WorkKnowledgeNotFoundError(f"Work knowledge note not found: {note_id}")
        return note
