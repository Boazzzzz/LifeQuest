from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator


LEARNING_TIMEZONE = ZoneInfo("Asia/Taipei")


class LearningSubject(StrEnum):
    python = "python"
    japanese = "japanese"
    sre = "sre"


class LearningSource(StrEnum):
    manual = "manual"
    anki = "anki"
    github = "github"
    notion = "notion"
    timer = "timer"
    import_job = "import_job"


class LearningSessionCreate(BaseModel):
    subject: LearningSubject
    duration_minutes: int = Field(gt=0, le=1440)
    summary: str = Field(min_length=1, max_length=2000)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    source: LearningSource = LearningSource.manual
    difficulty: int | None = Field(default=None, ge=1, le=5)
    energy_level: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)

    @field_validator("started_at", "ended_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=LEARNING_TIMEZONE)
        return value.astimezone(timezone.utc)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        tags = []
        seen = set()
        for tag in value:
            normalized = tag.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            tags.append(normalized)
            seen.add(key)
        return tags

    @model_validator(mode="after")
    def validate_time_window(self) -> "LearningSessionCreate":
        if self.started_at is None or self.ended_at is None:
            return self

        duration_seconds = (self.ended_at - self.started_at).total_seconds()
        if duration_seconds <= 0:
            raise ValueError("ended_at must be later than started_at")

        expected_seconds = self.duration_minutes * 60
        if abs(duration_seconds - expected_seconds) > 60:
            raise ValueError("duration_minutes must match the started_at and ended_at window")
        return self


class LearningSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    subject: LearningSubject
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int
    source: LearningSource
    summary: str
    difficulty: int | None = None
    energy_level: int | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LearningCheckinDraftRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class LearningCheckinDraft(BaseModel):
    subject: LearningSubject
    duration_minutes: int = Field(gt=0, le=1440)
    summary: str = Field(min_length=1, max_length=2000)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    energy_level: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    original_text: str
    assistant_note: str
    draft_source: Literal["ai", "local"] = "local"
    warnings: list[str] = Field(default_factory=list)


class LearningPulse(BaseModel):
    date: date
    python_minutes: int = 0
    japanese_minutes: int = 0
    sre_minutes: int = 0
    total_minutes: int = 0
    session_count: int = 0
    anki_reviews: int = 0
    anki_accuracy: float | None = None
    anki_difficult_cards: list[str] = Field(default_factory=list)
    github_commits: int = 0
    github_python_commits: int = 0
    github_repositories: list[str] = Field(default_factory=list)
    github_python_files: list[str] = Field(default_factory=list)
    focus_score: int = Field(default=0, ge=0, le=100)
    summary: str
    tomorrow_priority: str
    integration_warnings: list[str] = Field(default_factory=list)
