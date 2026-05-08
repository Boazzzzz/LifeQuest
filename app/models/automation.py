from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class AutomationCategory(StrEnum):
    knowledge = "knowledge"
    media = "media"
    game = "game"
    learning = "learning"
    system = "system"
    workflow = "workflow"
    other = "other"


class AutomationRunStatus(StrEnum):
    running = "running"
    success = "success"
    failed = "failed"
    partial = "partial"
    skipped = "skipped"


class AutomationTriggerSource(StrEnum):
    manual = "manual"
    scheduled = "scheduled"
    external = "external"
    api = "api"
    cli = "cli"
    unknown = "unknown"


class AutomationDefinitionCreate(BaseModel):
    key: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str = Field(min_length=1, max_length=200)
    category: AutomationCategory = AutomationCategory.other
    external_project_path: str | None = Field(default=None, max_length=1000)
    command_hint: str | None = Field(default=None, max_length=1000)
    schedule_hint: str | None = Field(default=None, max_length=500)
    log_path: str | None = Field(default=None, max_length=1000)
    owner: str | None = Field(default=None, max_length=200)
    enabled: bool = True
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list)

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()]


class AutomationDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: AutomationCategory | None = None
    external_project_path: str | None = Field(default=None, max_length=1000)
    command_hint: str | None = Field(default=None, max_length=1000)
    schedule_hint: str | None = Field(default=None, max_length=500)
    log_path: str | None = Field(default=None, max_length=1000)
    owner: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [tag.strip() for tag in value if tag.strip()]


class AutomationDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    name: str
    category: AutomationCategory
    external_project_path: str | None = None
    command_hint: str | None = None
    schedule_hint: str | None = None
    log_path: str | None = None
    owner: str | None = None
    enabled: bool = True
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_run_at: datetime | None = None
    last_run_status: AutomationRunStatus | None = None
    last_run_summary: str | None = None


class AutomationRunCreate(BaseModel):
    status: AutomationRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trigger_source: AutomationTriggerSource = AutomationTriggerSource.manual
    items_processed: int = Field(default=0, ge=0)
    summary: str | None = Field(default=None, max_length=4000)
    error_message: str | None = Field(default=None, max_length=4000)
    external_run_id: str | None = Field(default=None, max_length=500)
    log_excerpt: str | None = Field(default=None, max_length=8000)

    @field_validator("started_at", "finished_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class AutomationRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    automation_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: AutomationRunStatus
    trigger_source: AutomationTriggerSource
    items_processed: int = 0
    summary: str | None = None
    error_message: str | None = None
    external_run_id: str | None = None
    log_excerpt: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

