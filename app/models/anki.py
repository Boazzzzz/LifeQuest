from datetime import date, datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class AnkiDailySnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    snapshot_date: date
    scope: str = "all_decks"
    reviews: int = 0
    accuracy: float | None = None
    again_count: int = 0
    hard_count: int = 0
    good_count: int = 0
    easy_count: int = 0
    non_again_rate: float | None = None
    due_count: int = 0
    new_due_count: int = 0
    learn_due_count: int = 0
    review_due_count: int = 0
    difficult_cards: list[str] = Field(default_factory=list)
    decks: list[str] = Field(default_factory=list)
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnkiWorkloadOverview(BaseModel):
    due_count: int = 0
    new_due_count: int = 0
    learn_due_count: int = 0
    review_due_count: int = 0


class AnkiHistoryDay(BaseModel):
    snapshot_date: date
    reviews: int = 0
    accuracy: float | None = None
    non_again_rate: float | None = None
    again_count: int = 0
    hard_count: int = 0
    good_count: int = 0
    easy_count: int = 0
    due_count: int = 0
    imported_at: datetime


class AnkiDifficultCardTrend(BaseModel):
    label: str
    hit_count: int = 0
    last_seen_on: date


class AnkiReviewedCard(BaseModel):
    card_id: int
    deck_name: str
    label: str
    review_count: int = 0
    again_count: int = 0
    hard_count: int = 0
    good_count: int = 0
    easy_count: int = 0
    first_reviewed_at: datetime
    last_reviewed_at: datetime


class AnkiReviewedTodayOverview(BaseModel):
    enabled: bool = False
    connected: bool = False
    target_date: date
    scope: str = "all_decks"
    total_reviews: int = 0
    total_unique_cards: int = 0
    decks: list[str] = Field(default_factory=list)
    configured_decks: list[str] = Field(default_factory=list)
    missing_decks: list[str] = Field(default_factory=list)
    cards: list[AnkiReviewedCard] = Field(default_factory=list)
    error: str | None = None


class AnkiHistoryOverview(BaseModel):
    days: list[AnkiHistoryDay] = Field(default_factory=list)
    streak_days: int = 0
    best_review_day: date | None = None
    total_reviews: int = 0
    average_accuracy: float | None = None


class AnkiTodayOverview(BaseModel):
    enabled: bool = False
    connected: bool = False
    source: str
    scope: str = "all_decks"
    sync_status: str = "unknown"
    sync_hint: str = "Sync desktop Anki before importing if you reviewed on mobile."
    imported_at: datetime | None = None
    reviews: int = 0
    accuracy: float | None = None
    non_again_rate: float | None = None
    again_count: int = 0
    hard_count: int = 0
    good_count: int = 0
    easy_count: int = 0
    due_count: int = 0
    new_due_count: int = 0
    learn_due_count: int = 0
    review_due_count: int = 0
    streak_days: int = 0
    difficult_cards: list[str] = Field(default_factory=list)
    decks: list[str] = Field(default_factory=list)
    configured_decks: list[str] = Field(default_factory=list)
    missing_decks: list[str] = Field(default_factory=list)
    review_load: str = "none"
    summary: str = "No Anki activity yet."
    recommendation: str = "Do one short Anki review block."
    error: str | None = None
