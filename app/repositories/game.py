from datetime import datetime

from app.core.database import execute, fetch_all, fetch_one
from app.models.game import GameQuestAction, GameQuestEvent


class GameQuestEventRepository:
    def upsert_event(self, event: GameQuestEvent) -> GameQuestEvent:
        existing = self.get_event(event.quest_key, event.event_date)
        if existing is None:
            execute(
                """
                INSERT INTO game_quest_events (
                    id, quest_key, event_date, action, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.quest_key,
                    event.event_date.isoformat(),
                    event.action.value,
                    event.source,
                    event.created_at.isoformat(),
                    event.updated_at.isoformat(),
                ),
            )
            return event

        existing.action = event.action
        existing.source = event.source
        existing.updated_at = event.updated_at
        execute(
            """
            UPDATE game_quest_events
            SET action = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                existing.action.value,
                existing.source,
                existing.updated_at.isoformat(),
                existing.id,
            ),
        )
        return existing

    def get_event(self, quest_key: str, event_date) -> GameQuestEvent | None:
        row = fetch_one(
            """
            SELECT * FROM game_quest_events
            WHERE quest_key = ? AND event_date = ?
            """,
            (quest_key, event_date.isoformat()),
        )
        return self._row_to_event(row) if row else None

    def list_events_for_date(self, event_date) -> dict[str, GameQuestEvent]:
        rows = fetch_all(
            """
            SELECT * FROM game_quest_events
            WHERE event_date = ?
            ORDER BY quest_key ASC
            """,
            (event_date.isoformat(),),
        )
        return {str(row["quest_key"]): self._row_to_event(row) for row in rows}

    def _row_to_event(self, row) -> GameQuestEvent:
        return GameQuestEvent(
            id=row["id"],
            quest_key=row["quest_key"],
            event_date=datetime.fromisoformat(row["event_date"]).date(),
            action=GameQuestAction(row["action"]),
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
