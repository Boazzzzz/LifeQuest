from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class GameQuestAction(StrEnum):
    completed = "completed"
    skipped = "skipped"


class GameQuestStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    skipped = "skipped"


class GameQuestCompletionType(StrEnum):
    learning_signal = "learning_signal"
    manual = "manual"


class GameQuestEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    quest_key: str
    event_date: date
    action: GameQuestAction
    source: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameQuest(BaseModel):
    key: str
    title: str
    description: str
    xp: int = Field(ge=0)
    category: str
    completion_type: GameQuestCompletionType
    status: GameQuestStatus
    progress_label: str
    action_label: str | None = None
    completion_source: str | None = None


class GameDailyBoard(BaseModel):
    target_date: date
    quests: list[GameQuest]
    completed_count: int
    skipped_count: int
    total_count: int
    earned_xp: int
    available_xp: int
    gentle_message: str
