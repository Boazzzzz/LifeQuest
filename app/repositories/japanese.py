import json
from datetime import datetime

from app.core.database import connect
from app.models.japanese import JapaneseVerbForm


class JapaneseRepository:
    def create_verb_form(self, verb_form: JapaneseVerbForm) -> JapaneseVerbForm:
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO japanese_verb_forms (
                    id, dictionary_form, reading, meaning, verb_group, jlpt_level,
                    confidence, plain_nonpast, polite_nonpast, plain_past, polite_past,
                    plain_negative, polite_negative, plain_negative_past,
                    polite_negative_past, notes, tags, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._verb_form_values(verb_form),
            )
        return verb_form

    def list_verb_forms(self, limit: int = 100) -> list[JapaneseVerbForm]:
        with connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM japanese_verb_forms
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_verb_form(row) for row in rows]

    def get_verb_form(self, verb_form_id: str) -> JapaneseVerbForm | None:
        with connect() as connection:
            row = connection.execute(
                "SELECT * FROM japanese_verb_forms WHERE id = ?",
                (verb_form_id,),
            ).fetchone()
        return self._row_to_verb_form(row) if row else None

    def _verb_form_values(self, verb_form: JapaneseVerbForm) -> tuple:
        return (
            verb_form.id,
            verb_form.dictionary_form,
            verb_form.reading,
            verb_form.meaning,
            verb_form.verb_group.value,
            verb_form.jlpt_level.value,
            verb_form.confidence,
            verb_form.plain_nonpast,
            verb_form.polite_nonpast,
            verb_form.plain_past,
            verb_form.polite_past,
            verb_form.plain_negative,
            verb_form.polite_negative,
            verb_form.plain_negative_past,
            verb_form.polite_negative_past,
            verb_form.notes,
            json.dumps(verb_form.tags, ensure_ascii=False),
            verb_form.created_at.isoformat(),
            verb_form.updated_at.isoformat(),
        )

    def _row_to_verb_form(self, row) -> JapaneseVerbForm:
        return JapaneseVerbForm(
            id=row["id"],
            dictionary_form=row["dictionary_form"],
            reading=row["reading"],
            meaning=row["meaning"],
            verb_group=row["verb_group"],
            jlpt_level=row["jlpt_level"],
            confidence=row["confidence"],
            plain_nonpast=row["plain_nonpast"],
            polite_nonpast=row["polite_nonpast"],
            plain_past=row["plain_past"],
            polite_past=row["polite_past"],
            plain_negative=row["plain_negative"],
            polite_negative=row["polite_negative"],
            plain_negative_past=row["plain_negative_past"],
            polite_negative_past=row["polite_negative_past"],
            notes=row["notes"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
