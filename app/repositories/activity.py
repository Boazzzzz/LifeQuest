import json

from datetime import datetime

from app.core.database import execute, fetch_all, select_limit_clause
from app.models.activity import ActivityEvent


class ActivityRepository:
    def create_event(self, event: ActivityEvent) -> ActivityEvent:
        execute(
            """
            INSERT INTO activity_events (
                id, event_type, subject, occurred_at, source, payload, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.event_type.value,
                event.subject.value if event.subject else None,
                event.occurred_at.isoformat(),
                event.source,
                json.dumps(event.payload, ensure_ascii=False),
                event.created_at.isoformat(),
            ),
        )
        return event

    def list_recent_events(self, limit: int = 50) -> list[ActivityEvent]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM activity_events
            ORDER BY occurred_at DESC
        """
        rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (limit,))
        return [self._row_to_event(row) for row in rows]

    def list_events_between(self, start_at: datetime, end_at: datetime, limit: int = 500) -> list[ActivityEvent]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM activity_events
            WHERE occurred_at >= ? AND occurred_at <= ?
            ORDER BY occurred_at DESC
        """
        params = (start_at.isoformat(), end_at.isoformat())
        rows = fetch_all(query, params) if limit_clause else fetch_all(f"{query}\nLIMIT ?", params + (limit,))
        return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row) -> ActivityEvent:
        return ActivityEvent(
            id=row["id"],
            event_type=row["event_type"],
            subject=row["subject"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            source=row["source"],
            payload=json.loads(row["payload"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

