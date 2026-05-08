import json
from datetime import datetime

from app.core.database import connect
from app.models.work_knowledge import WorkKnowledgeNote


class WorkKnowledgeRepository:
    def create_note(self, note: WorkKnowledgeNote) -> WorkKnowledgeNote:
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO work_knowledge_notes (
                    id, title, category, sanitized_summary, commands, concepts,
                    source, sensitivity, systems, follow_up, tags, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._note_values(note),
            )
        return note

    def list_notes(self, limit: int = 100) -> list[WorkKnowledgeNote]:
        with connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM work_knowledge_notes
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_note(row) for row in rows]

    def get_note(self, note_id: str) -> WorkKnowledgeNote | None:
        with connect() as connection:
            row = connection.execute(
                "SELECT * FROM work_knowledge_notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        return self._row_to_note(row) if row else None

    def _note_values(self, note: WorkKnowledgeNote) -> tuple:
        return (
            note.id,
            note.title,
            note.category.value,
            note.sanitized_summary,
            json.dumps(note.commands, ensure_ascii=False),
            json.dumps(note.concepts, ensure_ascii=False),
            note.source.value,
            note.sensitivity.value,
            json.dumps(note.systems, ensure_ascii=False),
            note.follow_up,
            json.dumps(note.tags, ensure_ascii=False),
            note.created_at.isoformat(),
            note.updated_at.isoformat(),
        )

    def _row_to_note(self, row) -> WorkKnowledgeNote:
        return WorkKnowledgeNote(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            sanitized_summary=row["sanitized_summary"],
            commands=json.loads(row["commands"]),
            concepts=json.loads(row["concepts"]),
            source=row["source"],
            sensitivity=row["sensitivity"],
            systems=json.loads(row["systems"]),
            follow_up=row["follow_up"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
