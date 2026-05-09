import json
from datetime import datetime

from app.core.database import execute, fetch_all, fetch_one, select_limit_clause
from app.models.subscription import Subscription


class SubscriptionRepository:
    def create_subscription(self, subscription: Subscription) -> Subscription:
        execute(
            """
            INSERT INTO subscriptions (
                id, key, name, amount, currency, recurrence_kind, billing_day,
                anchor_charge_date, interval_days, category, status,
                active, notes, tags, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._subscription_values(subscription),
        )
        return subscription

    def update_subscription(self, subscription: Subscription) -> Subscription:
        execute(
            """
            UPDATE subscriptions
            SET key = ?, name = ?, amount = ?, currency = ?, recurrence_kind = ?,
                billing_day = ?, anchor_charge_date = ?, interval_days = ?,
                category = ?, status = ?, active = ?, notes = ?, tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                subscription.key,
                subscription.name,
                subscription.amount,
                subscription.currency,
                subscription.recurrence_kind.value,
                subscription.billing_day,
                subscription.anchor_charge_date.isoformat() if subscription.anchor_charge_date else None,
                subscription.interval_days,
                subscription.category.value,
                subscription.status.value,
                1 if subscription.active else 0,
                subscription.notes,
                json.dumps(subscription.tags, ensure_ascii=False),
                subscription.updated_at.isoformat(),
                subscription.id,
            ),
        )
        return subscription

    def list_subscriptions(self, active_only: bool = False, limit: int = 500) -> list[Subscription]:
        limit_clause = select_limit_clause(limit)
        where_clause = "WHERE active = 1" if active_only else ""
        query = f"""
            SELECT {limit_clause}* FROM subscriptions
            {where_clause}
            ORDER BY active DESC, name ASC
        """
        rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (limit,))
        return [self._row_to_subscription(row) for row in rows]

    def get_subscription(self, subscription_id: str) -> Subscription | None:
        row = fetch_one("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,))
        return self._row_to_subscription(row) if row else None

    def get_subscription_by_key(self, key: str) -> Subscription | None:
        row = fetch_one("SELECT * FROM subscriptions WHERE key = ?", (key,))
        return self._row_to_subscription(row) if row else None

    def get_subscription_by_key_or_id(self, key_or_id: str) -> Subscription | None:
        return self.get_subscription_by_key(key_or_id) or self.get_subscription(key_or_id)

    def _subscription_values(self, subscription: Subscription) -> tuple:
        return (
            subscription.id,
            subscription.key,
            subscription.name,
            subscription.amount,
            subscription.currency,
            subscription.recurrence_kind.value,
            subscription.billing_day,
            subscription.anchor_charge_date.isoformat() if subscription.anchor_charge_date else None,
            subscription.interval_days,
            subscription.category.value,
            subscription.status.value,
            1 if subscription.active else 0,
            subscription.notes,
            json.dumps(subscription.tags, ensure_ascii=False),
            subscription.created_at.isoformat(),
            subscription.updated_at.isoformat(),
        )

    def _row_to_subscription(self, row) -> Subscription:
        return Subscription(
            id=row["id"],
            key=row["key"],
            name=row["name"],
            amount=float(row["amount"]),
            currency=row["currency"],
            recurrence_kind=row["recurrence_kind"],
            billing_day=row["billing_day"],
            anchor_charge_date=datetime.fromisoformat(row["anchor_charge_date"]).date()
            if row["anchor_charge_date"]
            else None,
            interval_days=row["interval_days"],
            category=row["category"],
            status=row["status"] if row.get("status") else ("active" if bool(row["active"]) else "paused"),
            active=bool(row["active"]),
            notes=row["notes"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
