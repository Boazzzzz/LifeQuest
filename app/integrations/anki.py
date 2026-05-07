import logging
import re
from datetime import date, datetime, time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class AnkiConnectError(RuntimeError):
    pass


class AnkiStatus(BaseModel):
    enabled: bool
    connected: bool
    url: str
    api_version: int | None = None
    decks: list[str] = Field(default_factory=list)
    error: str | None = None


class AnkiDailyStats(BaseModel):
    enabled: bool = False
    connected: bool = False
    reviews: int = 0
    accuracy: float | None = None
    difficult_cards: list[str] = Field(default_factory=list)
    decks: list[str] = Field(default_factory=list)
    error: str | None = None


class AnkiAdapter:
    def __init__(
        self,
        enabled: bool | None = None,
        connect_url: str | None = None,
        api_version: int | None = None,
        timeout_seconds: float | None = None,
        decks: list[str] | None = None,
    ) -> None:
        self.enabled = settings.anki_enabled if enabled is None else enabled
        self.connect_url = connect_url or settings.anki_connect_url
        self.api_version = api_version or settings.anki_api_version
        self.timeout_seconds = timeout_seconds or settings.anki_timeout_seconds
        self.decks = decks if decks is not None else self._parse_configured_decks(settings.anki_decks)

    async def check_status(self) -> AnkiStatus:
        if not self.enabled:
            return AnkiStatus(enabled=False, connected=False, url=self.connect_url)

        try:
            api_version = await self._invoke("version")
            decks = await self._get_target_decks()
            return AnkiStatus(
                enabled=True,
                connected=True,
                url=self.connect_url,
                api_version=api_version,
                decks=decks,
            )
        except AnkiConnectError as error:
            logger.warning("AnkiConnect status check failed: %s", error)
            return AnkiStatus(enabled=True, connected=False, url=self.connect_url, error=str(error))

    async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
        if not self.enabled:
            return AnkiDailyStats(enabled=False)

        try:
            decks = await self._get_target_decks()
            reviews = await self._get_review_count(target_date)
            review_rows = await self._get_review_rows_for_date(target_date, decks)
            accuracy = self._calculate_accuracy(review_rows)
            difficult_cards = await self._get_difficult_card_labels(review_rows)

            return AnkiDailyStats(
                enabled=True,
                connected=True,
                reviews=max(reviews, len(review_rows)),
                accuracy=accuracy,
                difficult_cards=difficult_cards,
                decks=decks,
            )
        except AnkiConnectError as error:
            logger.warning("Anki daily stats unavailable: %s", error)
            return AnkiDailyStats(enabled=True, connected=False, error=str(error))

    async def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"action": action, "version": self.api_version}
        if params is not None:
            payload["params"] = params

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.connect_url, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise AnkiConnectError(str(error)) from error

        if not isinstance(data, dict):
            raise AnkiConnectError("Unexpected AnkiConnect response shape")

        if data.get("error"):
            raise AnkiConnectError(str(data["error"]))

        return data.get("result")

    async def _get_target_decks(self) -> list[str]:
        if self.decks:
            return self.decks

        deck_names = await self._invoke("deckNames")
        if not isinstance(deck_names, list):
            return []
        return [str(deck_name) for deck_name in deck_names]

    async def _get_review_count(self, target_date: date) -> int:
        if target_date == date.today():
            result = await self._invoke("getNumCardsReviewedToday")
            return int(result or 0)

        result = await self._invoke("getNumCardsReviewedByDay")
        if not isinstance(result, list):
            return 0

        target = target_date.isoformat()
        for item in result:
            if isinstance(item, list) and len(item) >= 2 and item[0] == target:
                return int(item[1] or 0)
        return 0

    async def _get_review_rows_for_date(self, target_date: date, decks: list[str]) -> list[list[Any]]:
        if not decks:
            return []

        start_ms, end_ms = self._date_range_ms(target_date)
        rows_by_key: dict[tuple[int, int], list[Any]] = {}

        for deck in decks:
            try:
                result = await self._invoke("cardReviews", {"deck": deck, "startID": start_ms - 1})
            except AnkiConnectError as error:
                logger.info("Skipping Anki review rows for deck %s: %s", deck, error)
                continue

            if not isinstance(result, list):
                continue

            for row in result:
                if not isinstance(row, list) or len(row) < 4:
                    continue
                review_time = int(row[0])
                card_id = int(row[1])
                if start_ms <= review_time <= end_ms:
                    rows_by_key[(review_time, card_id)] = row

        return list(rows_by_key.values())

    def _calculate_accuracy(self, review_rows: list[list[Any]]) -> float | None:
        if not review_rows:
            return None

        correct = sum(1 for row in review_rows if int(row[3]) > 1)
        return round((correct / len(review_rows)) * 100, 1)

    async def _get_difficult_card_labels(self, review_rows: list[list[Any]]) -> list[str]:
        card_ids = []
        for row in review_rows:
            if int(row[3]) == 1:
                card_ids.append(int(row[1]))

        unique_card_ids = list(dict.fromkeys(card_ids))[:10]
        if not unique_card_ids:
            return []

        try:
            result = await self._invoke("cardsInfo", {"cards": unique_card_ids})
        except AnkiConnectError:
            return [str(card_id) for card_id in unique_card_ids]

        if not isinstance(result, list):
            return [str(card_id) for card_id in unique_card_ids]

        labels = []
        for card in result:
            if not isinstance(card, dict):
                continue
            deck_name = str(card.get("deckName") or "Anki")
            first_field = self._first_field_value(card.get("fields"))
            labels.append(f"{deck_name}: {first_field}" if first_field else str(card.get("cardId")))
        return labels

    def _first_field_value(self, fields: Any) -> str | None:
        if not isinstance(fields, dict):
            return None

        for value in fields.values():
            if isinstance(value, dict) and value.get("value"):
                return self._strip_html(str(value["value"]))[:120]
        return None

    def _strip_html(self, value: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", value)
        return " ".join(without_tags.split())

    def _date_range_ms(self, target_date: date) -> tuple[int, int]:
        local_timezone = datetime.now().astimezone().tzinfo
        start = datetime.combine(target_date, time.min, tzinfo=local_timezone)
        end = datetime.combine(target_date, time.max, tzinfo=local_timezone)
        return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    def _parse_configured_decks(self, raw_decks: str) -> list[str]:
        return [deck.strip() for deck in raw_decks.split(",") if deck.strip()]
