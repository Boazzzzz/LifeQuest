from datetime import date
from pydantic import BaseModel

from app.core.config import settings


class AnkiDailyStats(BaseModel):
    reviews: int = 0
    accuracy: float | None = None
    difficult_cards: list[str] = []


class AnkiAdapter:
    async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
        if not settings.anki_enabled:
            return AnkiDailyStats()

        # First real implementation should call AnkiConnect's getNumCardsReviewedToday
        # and card review endpoints. Kept inert until the local Anki workflow is confirmed.
        return AnkiDailyStats()

