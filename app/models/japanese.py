from datetime import date

from pydantic import BaseModel, Field

from app.models.anki import (
    AnkiDifficultCardTrend,
    AnkiHistoryOverview,
    AnkiReviewedTodayOverview,
    AnkiTodayOverview,
)
from app.models.learning import LearningPulse, LearningSession


class JapaneseDashboardOverview(BaseModel):
    target_date: date
    pulse: LearningPulse
    anki_today: AnkiTodayOverview
    reviewed_today: AnkiReviewedTodayOverview
    history: AnkiHistoryOverview
    difficult_cards: list[AnkiDifficultCardTrend] = Field(default_factory=list)
    japanese_sessions: list[LearningSession] = Field(default_factory=list)
    japanese_session_count: int = 0
    japanese_minutes: int = 0
