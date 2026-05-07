from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.learning import LearningSubject


class ActivityEventType(StrEnum):
    learning_session_created = "learning_session_created"
    anki_reviews_imported = "anki_reviews_imported"
    github_commits_imported = "github_commits_imported"
    notion_sync_completed = "notion_sync_completed"
    notion_sync_failed = "notion_sync_failed"


class ActivityEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: ActivityEventType
    subject: LearningSubject | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

