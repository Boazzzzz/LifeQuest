import calendar
import sqlite3
from datetime import date, datetime, timedelta, timezone

from app.core.exceptions import ConflictError, NotFoundError
from app.models.activity import ActivityEvent, ActivityEventType
from app.models.subscription import (
    SubscriptionAttentionItem,
    Subscription,
    SubscriptionCreate,
    SubscriptionLifecycleStatus,
    SubscriptionMonthlyOverview,
    SubscriptionUpcomingCharge,
    SubscriptionScheduleStatus,
    SubscriptionUpdate,
    SubscriptionRecurrenceKind,
    generate_subscription_key,
)
from app.repositories.activity import ActivityRepository
from app.repositories.subscription import SubscriptionRepository


class SubscriptionNotFoundError(NotFoundError):
    pass


class SubscriptionConflictError(ConflictError):
    pass


class SubscriptionService:
    def __init__(
        self,
        repository: SubscriptionRepository | None = None,
        activity_repository: ActivityRepository | None = None,
    ) -> None:
        self.repository = repository or SubscriptionRepository()
        self.activity_repository = activity_repository or ActivityRepository()

    def create_subscription(self, payload: SubscriptionCreate) -> Subscription:
        now = datetime.now(timezone.utc)
        lifecycle_status = self._resolve_lifecycle_status(payload.status, payload.active)
        subscription = Subscription(
            key=payload.key or generate_subscription_key(payload.name),
            name=payload.name,
            amount=payload.amount,
            currency=payload.currency,
            recurrence_kind=payload.recurrence_kind,
            billing_day=payload.billing_day,
            anchor_charge_date=payload.anchor_charge_date,
            interval_days=payload.interval_days,
            category=payload.category,
            status=lifecycle_status,
            active=self._status_is_active(lifecycle_status),
            notes=payload.notes,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
        )

        try:
            created = self.repository.create_subscription(subscription)
        except sqlite3.IntegrityError as error:
            raise SubscriptionConflictError(self._build_conflict_message(subscription)) from error
        self.activity_repository.create_event(
            ActivityEvent(
                event_type=ActivityEventType.subscription_created,
                source="subscription",
                payload={
                    "subscription_id": created.id,
                    "key": created.key,
                    "name": created.name,
                    "amount": created.amount,
                    "currency": created.currency,
                },
            )
        )
        return self._attach_next_charge_date(created)

    def list_subscriptions(self, active_only: bool = False, reference_date: date | None = None) -> list[Subscription]:
        subscriptions = self.repository.list_subscriptions(active_only=active_only)
        hydrated = [self._attach_next_charge_date(subscription, reference_date) for subscription in subscriptions]
        return sorted(
            hydrated,
            key=lambda item: (
                self._subscription_sort_rank(item),
                item.next_charge_date or date.max,
                item.name.lower(),
            ),
        )

    def get_subscription(self, key_or_id: str, reference_date: date | None = None) -> Subscription:
        subscription = self.repository.get_subscription_by_key_or_id(key_or_id)
        if subscription is None:
            raise SubscriptionNotFoundError(f"Subscription not found: {key_or_id}")
        return self._attach_next_charge_date(subscription, reference_date)

    def update_subscription(self, key_or_id: str, payload: SubscriptionUpdate) -> Subscription:
        current = self.get_subscription(key_or_id)
        previous_status = current.status
        updates = payload.model_dump(exclude_unset=True)

        for field_name, value in updates.items():
            setattr(current, field_name, value)
        current.status = self._resolve_updated_lifecycle_status(
            requested_status=updates.get("status"),
            requested_active=updates.get("active"),
            current_status=previous_status,
        )
        current.active = self._status_is_active(current.status)
        current = Subscription.model_validate(current.model_dump())
        current.updated_at = datetime.now(timezone.utc)

        try:
            updated = self.repository.update_subscription(current)
        except sqlite3.IntegrityError as error:
            raise SubscriptionConflictError(self._build_conflict_message(current)) from error
        self.activity_repository.create_event(
            ActivityEvent(
                event_type=ActivityEventType.subscription_updated,
                source="subscription",
                payload={
                    "subscription_id": updated.id,
                    "key": updated.key,
                    "name": updated.name,
                    "amount": updated.amount,
                    "currency": updated.currency,
                    "status": updated.status.value,
                },
            )
        )
        return self._attach_next_charge_date(updated)

    def build_monthly_overview(
        self,
        target_date: date | None = None,
        days_ahead: int = 30,
    ) -> SubscriptionMonthlyOverview:
        reference_date = target_date or datetime.now(timezone.utc).date()
        window_end = reference_date + timedelta(days=max(1, days_ahead))
        subscriptions = self.list_subscriptions(active_only=False, reference_date=reference_date)
        active_subscriptions = [
            subscription for subscription in subscriptions if subscription.status == SubscriptionLifecycleStatus.active
        ]

        totals_by_currency: dict[str, float] = {}
        totals_by_category: dict[str, dict[str, float]] = {}
        upcoming_charges: list[SubscriptionUpcomingCharge] = []
        missing_schedule_subscriptions: list[SubscriptionAttentionItem] = []
        for subscription in active_subscriptions:
            totals_by_currency[subscription.currency] = round(
                totals_by_currency.get(subscription.currency, 0.0) + subscription.amount,
                2,
            )
            category_bucket = totals_by_category.setdefault(subscription.category.value, {})
            category_bucket[subscription.currency] = round(
                category_bucket.get(subscription.currency, 0.0) + subscription.amount,
                2,
            )
            if subscription.schedule_status == SubscriptionScheduleStatus.needs_review:
                missing_schedule_subscriptions.append(
                    SubscriptionAttentionItem(
                        id=subscription.id,
                        key=subscription.key,
                        name=subscription.name,
                        amount=subscription.amount,
                        currency=subscription.currency,
                        category=subscription.category,
                        recurrence_kind=subscription.recurrence_kind,
                        reason="missing_schedule",
                        schedule_summary=subscription.schedule_summary or "Billing schedule not recorded yet.",
                    )
                )
            if subscription.next_charge_date is None or subscription.next_charge_date > window_end:
                continue
            upcoming_charges.append(
                SubscriptionUpcomingCharge(
                    id=subscription.id,
                    key=subscription.key,
                    name=subscription.name,
                    amount=subscription.amount,
                    currency=subscription.currency,
                    recurrence_kind=subscription.recurrence_kind,
                    billing_day=subscription.billing_day,
                    anchor_charge_date=subscription.anchor_charge_date,
                    interval_days=subscription.interval_days,
                    category=subscription.category,
                    next_charge_date=subscription.next_charge_date,
                    days_until_charge=subscription.days_until_charge or 0,
                    schedule_summary=subscription.schedule_summary or "Scheduled charge",
                )
            )

        upcoming_charges.sort(key=lambda item: (item.next_charge_date, item.name.lower()))
        return SubscriptionMonthlyOverview(
            target_date=reference_date,
            window_end=window_end,
            active_subscription_count=len(active_subscriptions),
            paused_subscription_count=sum(
                1 for subscription in subscriptions if subscription.status == SubscriptionLifecycleStatus.paused
            ),
            cancelled_subscription_count=sum(
                1 for subscription in subscriptions if subscription.status == SubscriptionLifecycleStatus.cancelled
            ),
            scheduled_subscription_count=sum(
                1
                for subscription in active_subscriptions
                if subscription.schedule_status == SubscriptionScheduleStatus.scheduled
            ),
            missing_schedule_count=len(missing_schedule_subscriptions),
            totals_by_currency=totals_by_currency,
            totals_by_category=totals_by_category,
            upcoming_charges=upcoming_charges,
            missing_schedule_subscriptions=missing_schedule_subscriptions,
        )

    def _attach_next_charge_date(
        self,
        subscription: Subscription,
        reference_date: date | None = None,
    ) -> Subscription:
        if subscription.status != SubscriptionLifecycleStatus.active:
            subscription.next_charge_date = None
            subscription.days_until_charge = None
            subscription.schedule_status = SubscriptionScheduleStatus.inactive
            subscription.active = False
            if subscription.status == SubscriptionLifecycleStatus.paused:
                subscription.schedule_summary = "Paused subscription"
            else:
                subscription.schedule_summary = "Cancelled subscription"
            return subscription

        subscription.active = True
        effective_reference_date = reference_date or datetime.now(timezone.utc).date()
        if subscription.recurrence_kind == SubscriptionRecurrenceKind.monthly and subscription.billing_day is not None:
            subscription.next_charge_date = self._next_monthly_charge_date(
                billing_day=subscription.billing_day,
                reference_date=effective_reference_date,
            )
            subscription.days_until_charge = (subscription.next_charge_date - effective_reference_date).days
            subscription.schedule_status = SubscriptionScheduleStatus.scheduled
            subscription.schedule_summary = f"Monthly on day {subscription.billing_day}"
            return subscription

        if (
            subscription.recurrence_kind == SubscriptionRecurrenceKind.fixed_days
            and subscription.anchor_charge_date is not None
            and subscription.interval_days is not None
        ):
            subscription.next_charge_date = self._next_fixed_days_charge_date(
                anchor_charge_date=subscription.anchor_charge_date,
                interval_days=subscription.interval_days,
                reference_date=effective_reference_date,
            )
            subscription.days_until_charge = (subscription.next_charge_date - effective_reference_date).days
            subscription.schedule_status = SubscriptionScheduleStatus.scheduled
            subscription.schedule_summary = (
                f"Every {subscription.interval_days} days from {subscription.anchor_charge_date.isoformat()}"
            )
            return subscription

        subscription.next_charge_date = None
        subscription.days_until_charge = None
        subscription.schedule_status = SubscriptionScheduleStatus.needs_review
        if subscription.recurrence_kind == SubscriptionRecurrenceKind.unknown:
            subscription.schedule_summary = "Billing date not recorded yet"
        else:
            subscription.schedule_summary = "Schedule configuration is incomplete"
        return subscription

    def _next_monthly_charge_date(self, billing_day: int, reference_date: date) -> date:
        current_month_charge = date(
            reference_date.year,
            reference_date.month,
            min(billing_day, calendar.monthrange(reference_date.year, reference_date.month)[1]),
        )
        if current_month_charge >= reference_date:
            return current_month_charge

        next_year, next_month = self._shift_month(reference_date.year, reference_date.month)
        next_month_last_day = calendar.monthrange(next_year, next_month)[1]
        return date(next_year, next_month, min(billing_day, next_month_last_day))

    def _next_fixed_days_charge_date(
        self,
        anchor_charge_date: date,
        interval_days: int,
        reference_date: date,
    ) -> date:
        if anchor_charge_date >= reference_date:
            return anchor_charge_date

        days_since_anchor = (reference_date - anchor_charge_date).days
        cycles_since_anchor = (days_since_anchor + interval_days - 1) // interval_days
        return anchor_charge_date + timedelta(days=cycles_since_anchor * interval_days)

    def _shift_month(self, year: int, month: int) -> tuple[int, int]:
        if month == 12:
            return year + 1, 1
        return year, month + 1

    def _build_conflict_message(self, subscription: Subscription) -> str:
        if self.repository.get_subscription_by_key(subscription.key) is not None:
            return f"Subscription key already exists: {subscription.key}"
        return f"Subscription name already exists: {subscription.name}"

    def _subscription_sort_rank(self, subscription: Subscription) -> int:
        if subscription.status == SubscriptionLifecycleStatus.active and subscription.schedule_status == SubscriptionScheduleStatus.scheduled:
            return 0
        if subscription.status == SubscriptionLifecycleStatus.active and subscription.schedule_status == SubscriptionScheduleStatus.needs_review:
            return 1
        if subscription.status == SubscriptionLifecycleStatus.paused:
            return 2
        if subscription.status == SubscriptionLifecycleStatus.cancelled:
            return 3
        return 4

    def _resolve_lifecycle_status(
        self,
        status: SubscriptionLifecycleStatus | str | None,
        active: bool | None,
    ) -> SubscriptionLifecycleStatus:
        if status is not None:
            return SubscriptionLifecycleStatus(status)
        if active is False:
            return SubscriptionLifecycleStatus.paused
        return SubscriptionLifecycleStatus.active

    def _status_is_active(self, status: SubscriptionLifecycleStatus) -> bool:
        return status == SubscriptionLifecycleStatus.active

    def _resolve_updated_lifecycle_status(
        self,
        requested_status: SubscriptionLifecycleStatus | str | None,
        requested_active: bool | None,
        current_status: SubscriptionLifecycleStatus | str,
    ) -> SubscriptionLifecycleStatus:
        if requested_status is not None:
            return SubscriptionLifecycleStatus(requested_status)
        if requested_active is False:
            return SubscriptionLifecycleStatus.paused
        if requested_active is True:
            return SubscriptionLifecycleStatus.active
        return SubscriptionLifecycleStatus(current_status)
