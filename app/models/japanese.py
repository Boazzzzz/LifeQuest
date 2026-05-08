from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class JapaneseVerbGroup(StrEnum):
    ichidan = "ichidan"
    godan = "godan"
    suru = "suru"
    kuru = "kuru"
    irregular = "irregular"


class JLPTLevel(StrEnum):
    n5 = "N5"
    n4 = "N4"
    n3 = "N3"
    n2 = "N2"
    n1 = "N1"
    unknown = "unknown"


class JapaneseVerbFormCreate(BaseModel):
    dictionary_form: str = Field(min_length=1, max_length=120)
    reading: str | None = Field(default=None, max_length=120)
    meaning: str | None = Field(default=None, max_length=500)
    verb_group: JapaneseVerbGroup
    jlpt_level: JLPTLevel = JLPTLevel.unknown
    confidence: int | None = Field(default=None, ge=1, le=5)
    plain_nonpast: str | None = Field(default=None, max_length=120)
    polite_nonpast: str | None = Field(default=None, max_length=120)
    plain_past: str | None = Field(default=None, max_length=120)
    polite_past: str | None = Field(default=None, max_length=120)
    plain_negative: str | None = Field(default=None, max_length=120)
    polite_negative: str | None = Field(default=None, max_length=120)
    plain_negative_past: str | None = Field(default=None, max_length=120)
    polite_negative_past: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list)

    @field_validator("dictionary_form", "reading", "meaning", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()]


class JapaneseVerbForm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    dictionary_form: str
    reading: str | None = None
    meaning: str | None = None
    verb_group: JapaneseVerbGroup
    jlpt_level: JLPTLevel = JLPTLevel.unknown
    confidence: int | None = None
    plain_nonpast: str
    polite_nonpast: str
    plain_past: str
    polite_past: str
    plain_negative: str
    polite_negative: str
    plain_negative_past: str
    polite_negative_past: str
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

