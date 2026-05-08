from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class WorkKnowledgeCategory(StrEnum):
    linux = "linux"
    networking = "networking"
    docker = "docker"
    nginx = "nginx"
    database = "database"
    security = "security"
    monitoring = "monitoring"
    cloud = "cloud"
    automation = "automation"
    other = "other"


class WorkKnowledgeSource(StrEnum):
    manual = "manual"
    company_copilot = "company_copilot"
    ticket = "ticket"
    incident = "incident"
    reading = "reading"


class WorkKnowledgeSensitivity(StrEnum):
    public = "public"
    personal = "personal"
    company_internal = "company_internal"
    confidential = "confidential"


class WorkKnowledgeNoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: WorkKnowledgeCategory = WorkKnowledgeCategory.other
    sanitized_summary: str = Field(min_length=1, max_length=4000)
    commands: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    source: WorkKnowledgeSource = WorkKnowledgeSource.manual
    sensitivity: WorkKnowledgeSensitivity = WorkKnowledgeSensitivity.personal
    systems: list[str] = Field(default_factory=list)
    follow_up: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list)

    @field_validator("commands", "concepts", "systems", "tags")
    @classmethod
    def normalize_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class WorkKnowledgeNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    category: WorkKnowledgeCategory
    sanitized_summary: str
    commands: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    source: WorkKnowledgeSource
    sensitivity: WorkKnowledgeSensitivity
    systems: list[str] = Field(default_factory=list)
    follow_up: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

