from datetime import date, datetime, timezone
from enum import StrEnum
import re
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class SubscriptionCategory(StrEnum):
    software = "software"
    entertainment = "entertainment"
    education = "education"
    cloud = "cloud"
    ai = "ai"
    productivity = "productivity"
    finance = "finance"
    utilities = "utilities"
    membership = "membership"
    other = "other"


class SubscriptionRecurrenceKind(StrEnum):
    monthly = "monthly"
    fixed_days = "fixed_days"
    unknown = "unknown"


class SubscriptionLifecycleStatus(StrEnum):
    active = "active"
    paused = "paused"
    cancelled = "cancelled"


class SubscriptionScheduleStatus(StrEnum):
    scheduled = "scheduled"
    needs_review = "needs_review"
    inactive = "inactive"


class SubscriptionCreate(BaseModel):
    key: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0, le=1_000_000)
    currency: str = Field(default="TWD", min_length=3, max_length=8)
    recurrence_kind: SubscriptionRecurrenceKind = SubscriptionRecurrenceKind.monthly
    billing_day: int | None = Field(default=None, ge=1, le=31)
    anchor_charge_date: date | None = None
    interval_days: int | None = Field(default=None, ge=1, le=366)
    category: SubscriptionCategory = SubscriptionCategory.other
    status: SubscriptionLifecycleStatus | None = None
    active: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] = Field(default_factory=list)

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()]

    @field_validator("anchor_charge_date", mode="before")
    @classmethod
    def normalize_anchor_charge_date(cls, value: date | str | None) -> date | None:
        if value is None or isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @field_validator("interval_days")
    @classmethod
    def validate_interval_days(cls, value: int | None, info) -> int | None:
        recurrence_kind = info.data.get("recurrence_kind")
        if recurrence_kind == SubscriptionRecurrenceKind.fixed_days and value is None:
            raise ValueError("interval_days is required for fixed_days subscriptions")
        return value

    @field_validator("billing_day")
    @classmethod
    def validate_billing_day(cls, value: int | None, info) -> int | None:
        recurrence_kind = info.data.get("recurrence_kind")
        if recurrence_kind == SubscriptionRecurrenceKind.monthly and value is None:
            raise ValueError("billing_day is required for monthly subscriptions")
        return value

    @field_validator("anchor_charge_date")
    @classmethod
    def validate_anchor_charge_date(cls, value: date | None, info) -> date | None:
        recurrence_kind = info.data.get("recurrence_kind")
        if recurrence_kind == SubscriptionRecurrenceKind.fixed_days and value is None:
            raise ValueError("anchor_charge_date is required for fixed_days subscriptions")
        return value


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: float | None = Field(default=None, gt=0, le=1_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    billing_day: int | None = Field(default=None, ge=1, le=31)
    recurrence_kind: SubscriptionRecurrenceKind | None = None
    anchor_charge_date: date | None = None
    interval_days: int | None = Field(default=None, ge=1, le=366)
    category: SubscriptionCategory | None = None
    status: SubscriptionLifecycleStatus | None = None
    active: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("anchor_charge_date", mode="before")
    @classmethod
    def normalize_anchor_charge_date(cls, value: date | str | None) -> date | None:
        if value is None or isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [tag.strip() for tag in value if tag.strip()]


class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    name: str
    amount: float
    currency: str
    recurrence_kind: SubscriptionRecurrenceKind = SubscriptionRecurrenceKind.monthly
    billing_day: int | None = None
    anchor_charge_date: date | None = None
    interval_days: int | None = None
    category: SubscriptionCategory
    status: SubscriptionLifecycleStatus = SubscriptionLifecycleStatus.active
    active: bool = True
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_charge_date: date | None = None
    days_until_charge: int | None = None
    schedule_status: SubscriptionScheduleStatus = SubscriptionScheduleStatus.needs_review
    schedule_summary: str | None = None


class SubscriptionUpcomingCharge(BaseModel):
    id: str
    key: str
    name: str
    amount: float
    currency: str
    recurrence_kind: SubscriptionRecurrenceKind
    billing_day: int | None = None
    anchor_charge_date: date | None = None
    interval_days: int | None = None
    category: SubscriptionCategory
    next_charge_date: date
    days_until_charge: int
    schedule_summary: str


class SubscriptionAttentionItem(BaseModel):
    id: str
    key: str
    name: str
    amount: float
    currency: str
    category: SubscriptionCategory
    recurrence_kind: SubscriptionRecurrenceKind
    reason: str
    schedule_summary: str


class SubscriptionMonthlyOverview(BaseModel):
    target_date: date
    window_end: date
    active_subscription_count: int
    paused_subscription_count: int
    cancelled_subscription_count: int
    scheduled_subscription_count: int
    missing_schedule_count: int
    totals_by_currency: dict[str, float] = Field(default_factory=dict)
    totals_by_category: dict[str, dict[str, float]] = Field(default_factory=dict)
    upcoming_charges: list[SubscriptionUpcomingCharge] = Field(default_factory=list)
    missing_schedule_subscriptions: list[SubscriptionAttentionItem] = Field(default_factory=list)


def generate_subscription_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if slug:
        return slug
    return f"subscription-{uuid4().hex[:8]}"
