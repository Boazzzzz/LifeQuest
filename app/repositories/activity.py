import json

from app.core.database import execute
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

