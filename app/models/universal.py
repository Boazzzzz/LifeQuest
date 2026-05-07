from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class NodeSource(StrEnum):
    manual = "manual"
    notion = "notion"
    raindrop = "raindrop"
    anki = "anki"
    github = "github"
    filesystem = "filesystem"
    telegram = "telegram"
    stash = "stash"


class UniversalNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    tags: list[str] = Field(default_factory=list)
    source: NodeSource
    source_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

