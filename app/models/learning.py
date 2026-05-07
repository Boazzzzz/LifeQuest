from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class LearningSubject(StrEnum):
    python = "python"
    japanese = "japanese"


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
            return value.replace(tzinfo=timezone.utc)
        return value


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


class LearningPulse(BaseModel):
    date: date
    python_minutes: int = 0
    japanese_minutes: int = 0
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
