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
    subscription_created = "subscription_created"
    subscription_updated = "subscription_updated"
    work_knowledge_note_created = "work_knowledge_note_created"
    automation_run_recorded = "automation_run_recorded"
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


class ActivityTimelineItem(BaseModel):
    id: str
    event_type: ActivityEventType
    occurred_at: datetime
    source: str
    title: str
    detail: str
    href: str | None = None
    tone: str = "neutral"


class ActivityTimelineOverview(BaseModel):
    items: list[ActivityTimelineItem] = Field(default_factory=list)

