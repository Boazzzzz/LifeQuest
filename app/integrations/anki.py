import logging
import re
from datetime import date, datetime, time, timezone
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.anki import AnkiReviewedCard, AnkiReviewedTodayOverview

logger = logging.getLogger(__name__)


class AnkiConnectError(RuntimeError):
    pass


class AnkiStatus(BaseModel):
    enabled: bool
    connected: bool
    url: str
    api_version: int | None = None
    scope: str = "all_decks"
    decks: list[str] = Field(default_factory=list)
    configured_decks: list[str] = Field(default_factory=list)
    available_decks: list[str] = Field(default_factory=list)
    missing_decks: list[str] = Field(default_factory=list)
    error: str | None = None


class AnkiDailyStats(BaseModel):
    enabled: bool = False
    connected: bool = False
    scope: str = "all_decks"
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
    difficult_cards: list[str] = Field(default_factory=list)
    decks: list[str] = Field(default_factory=list)
    configured_decks: list[str] = Field(default_factory=list)
    missing_decks: list[str] = Field(default_factory=list)
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
            deck_info = await self._get_target_deck_info()
            return AnkiStatus(
                enabled=True,
                connected=True,
                url=self.connect_url,
                api_version=api_version,
                scope=deck_info["scope"],
                decks=deck_info["target_decks"],
                configured_decks=deck_info["configured_decks"],
                available_decks=deck_info["available_decks"],
                missing_decks=deck_info["missing_decks"],
            )
        except AnkiConnectError as error:
            logger.warning("AnkiConnect status check failed: %s", error)
            return AnkiStatus(enabled=True, connected=False, url=self.connect_url, error=str(error))

    async def get_daily_stats(self, target_date: date) -> AnkiDailyStats:
        if not self.enabled:
            return AnkiDailyStats(enabled=False)

        try:
            deck_info = await self._get_target_deck_info()
            reviews = await self._get_review_count(target_date) if deck_info["scope"] == "all_decks" else None
            review_rows = await self._get_review_rows_for_date(target_date, deck_info["target_decks"])
            workload = await self._get_due_workload(deck_info["target_decks"])
            button_counts = self._button_counts(review_rows)
            accuracy = self._calculate_accuracy(review_rows)
            difficult_cards = await self._get_difficult_card_labels(review_rows)

            return AnkiDailyStats(
                enabled=True,
                connected=True,
                scope=deck_info["scope"],
                reviews=max(reviews or 0, len(review_rows)) if deck_info["scope"] == "all_decks" else len(review_rows),
                accuracy=accuracy,
                non_again_rate=accuracy,
                again_count=button_counts["again_count"],
                hard_count=button_counts["hard_count"],
                good_count=button_counts["good_count"],
                easy_count=button_counts["easy_count"],
                due_count=workload["due_count"],
                new_due_count=workload["new_due_count"],
                learn_due_count=workload["learn_due_count"],
                review_due_count=workload["review_due_count"],
                difficult_cards=difficult_cards,
                decks=deck_info["target_decks"],
                configured_decks=deck_info["configured_decks"],
                missing_decks=deck_info["missing_decks"],
            )
        except AnkiConnectError as error:
            logger.warning("Anki daily stats unavailable: %s", error)
            return AnkiDailyStats(enabled=True, connected=False, error=str(error))

    async def get_reviewed_today_overview(self, target_date: date | None = None) -> AnkiReviewedTodayOverview:
        target_date = target_date or date.today()
        if not self.enabled:
            return AnkiReviewedTodayOverview(enabled=False, target_date=target_date)

        try:
            deck_info = await self._get_target_deck_info()
            review_rows = await self._get_review_rows_for_date(target_date, deck_info["target_decks"])
            cards = await self._reviewed_cards_from_rows(review_rows)
            return AnkiReviewedTodayOverview(
                enabled=True,
                connected=True,
                target_date=target_date,
                scope=deck_info["scope"],
                total_reviews=len(review_rows),
                total_unique_cards=len(cards),
                decks=deck_info["target_decks"],
                configured_decks=deck_info["configured_decks"],
                missing_decks=deck_info["missing_decks"],
                cards=cards,
            )
        except AnkiConnectError as error:
            logger.warning("Anki reviewed-cards overview unavailable: %s", error)
            return AnkiReviewedTodayOverview(
                enabled=True,
                connected=False,
                target_date=target_date,
                error=str(error),
            )

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

    async def _get_target_deck_info(self) -> dict[str, list[str] | str]:
        deck_names = await self._invoke("deckNames")
        if not isinstance(deck_names, list):
            return {
                "scope": "configured_decks" if self.decks else "all_decks",
                "target_decks": list(self.decks),
                "configured_decks": list(self.decks),
                "available_decks": [],
                "missing_decks": list(self.decks),
            }

        available_decks = [str(deck_name) for deck_name in deck_names]
        if not self.decks:
            return {
                "scope": "all_decks",
                "target_decks": available_decks,
                "configured_decks": [],
                "available_decks": available_decks,
                "missing_decks": [],
            }

        configured_lookup = {deck.casefold(): deck for deck in available_decks}
        target_decks = []
        missing_decks = []
        for configured_deck in self.decks:
            matched_deck = configured_lookup.get(configured_deck.casefold())
            if matched_deck is None:
                missing_decks.append(configured_deck)
            else:
                target_decks.extend(self._expand_deck_with_children(matched_deck, available_decks))

        return {
            "scope": "configured_decks",
            "target_decks": list(dict.fromkeys(target_decks)),
            "configured_decks": list(self.decks),
            "available_decks": available_decks,
            "missing_decks": missing_decks,
        }

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

    async def _get_due_workload(self, decks: list[str]) -> dict[str, int]:
        card_ids = await self._get_card_ids_for_decks(decks)
        if not card_ids:
            return {
                "due_count": 0,
                "new_due_count": 0,
                "learn_due_count": 0,
                "review_due_count": 0,
            }

        due_flags = await self._are_due(card_ids)
        cards_info = await self._cards_info(card_ids)
        info_by_card_id = {
            int(card["cardId"]): card for card in cards_info if isinstance(card, dict) and card.get("cardId") is not None
        }

        workload = {
            "due_count": 0,
            "new_due_count": 0,
            "learn_due_count": 0,
            "review_due_count": 0,
        }
        for card_id, is_due in zip(card_ids, due_flags, strict=False):
            if not is_due:
                continue

            workload["due_count"] += 1
            card_info = info_by_card_id.get(card_id, {})
            queue = card_info.get("queue")
            card_type = card_info.get("type")
            queue_value = int(queue) if isinstance(queue, (int, float)) else None
            type_value = int(card_type) if isinstance(card_type, (int, float)) else None

            if queue_value == 0 or type_value == 0:
                workload["new_due_count"] += 1
            elif queue_value in {1, 3} or type_value == 1:
                workload["learn_due_count"] += 1
            else:
                workload["review_due_count"] += 1

        return workload

    async def _get_card_ids_for_decks(self, decks: list[str]) -> list[int]:
        card_ids: list[int] = []
        for deck in decks:
            result = await self._invoke("findCards", {"query": self._deck_query(deck)})
            if not isinstance(result, list):
                continue
            for card_id in result:
                try:
                    card_ids.append(int(card_id))
                except (TypeError, ValueError):
                    continue
        return list(dict.fromkeys(card_ids))

    async def _are_due(self, card_ids: list[int]) -> list[bool]:
        due_flags: list[bool] = []
        for chunk in self._chunked(card_ids, 200):
            result = await self._invoke("areDue", {"cards": chunk})
            if not isinstance(result, list):
                due_flags.extend([False] * len(chunk))
                continue
            due_flags.extend(bool(flag) for flag in result)
        return due_flags

    async def _cards_info(self, card_ids: list[int]) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for chunk in self._chunked(card_ids, 100):
            result = await self._invoke("cardsInfo", {"cards": chunk})
            if isinstance(result, list):
                cards.extend(card for card in result if isinstance(card, dict))
        return cards

    async def _reviewed_cards_from_rows(self, review_rows: list[list[Any]]) -> list[AnkiReviewedCard]:
        if not review_rows:
            return []

        rows_by_card: dict[int, list[list[Any]]] = {}
        for row in review_rows:
            if not isinstance(row, list) or len(row) < 4:
                continue
            card_id = int(row[1])
            rows_by_card.setdefault(card_id, []).append(row)

        cards_info = await self._cards_info(list(rows_by_card))
        info_by_card_id = {
            int(card["cardId"]): card for card in cards_info if isinstance(card, dict) and card.get("cardId") is not None
        }

        reviewed_cards: list[AnkiReviewedCard] = []
        for card_id, rows in rows_by_card.items():
            sorted_rows = sorted(rows, key=lambda row: int(row[0]))
            button_counts = self._button_counts(sorted_rows)
            card_info = info_by_card_id.get(card_id, {})
            deck_name = str(card_info.get("deckName") or "Anki")
            label = self._card_label(card_info) or str(card_id)
            reviewed_cards.append(
                AnkiReviewedCard(
                    card_id=card_id,
                    deck_name=deck_name,
                    label=label,
                    review_count=len(sorted_rows),
                    again_count=button_counts["again_count"],
                    hard_count=button_counts["hard_count"],
                    good_count=button_counts["good_count"],
                    easy_count=button_counts["easy_count"],
                    first_reviewed_at=self._review_time_to_datetime(int(sorted_rows[0][0])),
                    last_reviewed_at=self._review_time_to_datetime(int(sorted_rows[-1][0])),
                )
            )

        return sorted(
            reviewed_cards,
            key=lambda card: (card.last_reviewed_at, card.deck_name.casefold(), card.label.casefold()),
            reverse=True,
        )

    def _calculate_accuracy(self, review_rows: list[list[Any]]) -> float | None:
        if not review_rows:
            return None

        correct = sum(1 for row in review_rows if int(row[3]) > 1)
        return round((correct / len(review_rows)) * 100, 1)

    def _count_again_answers(self, review_rows: list[list[Any]]) -> int:
        return sum(1 for row in review_rows if int(row[3]) == 1)

    def _button_counts(self, review_rows: list[list[Any]]) -> dict[str, int]:
        counts = {
            "again_count": 0,
            "hard_count": 0,
            "good_count": 0,
            "easy_count": 0,
        }
        for row in review_rows:
            button = int(row[3])
            if button == 1:
                counts["again_count"] += 1
            elif button == 2:
                counts["hard_count"] += 1
            elif button == 3:
                counts["good_count"] += 1
            elif button == 4:
                counts["easy_count"] += 1
        return counts

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
            label = self._card_label(card)
            labels.append(f"{deck_name}: {label}" if label else str(card.get("cardId")))
        return labels

    def _card_label(self, card_info: dict[str, Any]) -> str | None:
        fields = card_info.get("fields")
        if not isinstance(fields, dict):
            return None

        primary = self._field_value(
            fields,
            [
                "VocabKanji",
                "Expression",
                "Word",
                "Kanji",
                "Front",
                "Sentence",
                "SentKanji1",
            ],
        )
        secondary = self._field_value(
            fields,
            [
                "VocabDefTC",
                "VocabDefSC",
                "Meaning",
                "Definition",
                "Back",
                "VocabFurigana",
                "Reading",
                "Yomi",
            ],
        )

        if primary and secondary and primary != secondary:
            return f"{primary} | {secondary}"
        if primary:
            return primary
        if secondary:
            return secondary
        return self._first_field_value(fields)

    def _field_value(self, fields: dict[str, Any], field_names: list[str]) -> str | None:
        for field_name in field_names:
            field = fields.get(field_name)
            if not isinstance(field, dict) or not field.get("value"):
                continue
            value = self._strip_html(str(field["value"]))[:120]
            if value and not self._looks_like_identifier(value):
                return value
        return None

    def _first_field_value(self, fields: Any) -> str | None:
        if not isinstance(fields, dict):
            return None

        for value in fields.values():
            if isinstance(value, dict) and value.get("value"):
                cleaned = self._strip_html(str(value["value"]))[:120]
                if cleaned and not self._looks_like_identifier(cleaned):
                    return cleaned
        return None

    def _looks_like_identifier(self, value: str) -> bool:
        normalized = value.strip()
        if not normalized:
            return True
        if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f-]{27}", normalized, flags=re.IGNORECASE):
            return True
        if re.fullmatch(r"\d+", normalized):
            return True
        return False

    def _strip_html(self, value: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", value)
        return " ".join(without_tags.split())

    def _date_range_ms(self, target_date: date) -> tuple[int, int]:
        local_timezone = datetime.now().astimezone().tzinfo
        start = datetime.combine(target_date, time.min, tzinfo=local_timezone)
        end = datetime.combine(target_date, time.max, tzinfo=local_timezone)
        return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    def _review_time_to_datetime(self, review_time_ms: int) -> datetime:
        return datetime.fromtimestamp(review_time_ms / 1000, tz=timezone.utc).astimezone()

    def _deck_query(self, deck_name: str) -> str:
        escaped_deck_name = deck_name.replace('"', '\\"')
        return f'deck:"{escaped_deck_name}"'

    def _chunked(self, values: list[int], size: int) -> list[list[int]]:
        return [values[index : index + size] for index in range(0, len(values), size)]

    def _expand_deck_with_children(self, deck_name: str, available_decks: list[str]) -> list[str]:
        prefix = f"{deck_name}::"
        return [candidate for candidate in available_decks if candidate == deck_name or candidate.startswith(prefix)]

    def _parse_configured_decks(self, raw_decks: str) -> list[str]:
        return [deck.strip() for deck in raw_decks.split(",") if deck.strip()]
