import json
from datetime import date, datetime, time, timezone

from app.core.database import execute, fetch_all, is_mssql_backend
from app.models.learning import LearningSession


class LearningRepository:
    def create_session(self, session: LearningSession) -> LearningSession:
        execute(
            """
            INSERT INTO learning_sessions (
                id, subject, started_at, ended_at, duration_minutes, source,
                summary, difficulty, energy_level, tags, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.subject.value,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
                session.duration_minutes,
                session.source.value,
                session.summary,
                session.difficulty,
                session.energy_level,
                json.dumps(session.tags, ensure_ascii=False),
                session.created_at.isoformat(),
            ),
        )
        return session

    def list_sessions(self, limit: int = 100, offset: int = 0) -> list[LearningSession]:
        if is_mssql_backend():
            rows = fetch_all(
                """
                SELECT * FROM learning_sessions
                ORDER BY started_at DESC, id DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                (offset, limit),
            )
        else:
            rows = fetch_all(
                """
                SELECT * FROM learning_sessions
                ORDER BY started_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        return [self._row_to_session(row) for row in rows]

    def list_sessions_for_date(self, target_date: date) -> list[LearningSession]:
        start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
        rows = fetch_all(
            """
            SELECT * FROM learning_sessions
            WHERE started_at >= ? AND started_at <= ?
            ORDER BY started_at ASC
            """,
            (start.isoformat(), end.isoformat()),
        )
        return [self._row_to_session(row) for row in rows]

    def _row_to_session(self, row) -> LearningSession:
        return LearningSession(
            id=row["id"],
            subject=row["subject"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            duration_minutes=row["duration_minutes"],
            source=row["source"],
            summary=row["summary"],
            difficulty=row["difficulty"],
            energy_level=row["energy_level"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

