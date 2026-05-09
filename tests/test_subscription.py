from datetime import date

from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.core.database import initialize_database
from app.main import app
from app.models.subscription import (
    SubscriptionCategory,
    SubscriptionCreate,
    SubscriptionLifecycleStatus,
    SubscriptionRecurrenceKind,
)
from app.services.subscription import SubscriptionConflictError, SubscriptionService


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    initialize_database()


def test_subscription_service_creates_overview_and_upcoming_charge(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = SubscriptionService()

    subscription = service.create_subscription(
        SubscriptionCreate(
            name="Spotify Premium",
            amount=149.0,
            billing_day=15,
            category=SubscriptionCategory.entertainment,
            tags=["music"],
        )
    )

    subscriptions = service.list_subscriptions(reference_date=subscription.created_at.date())
    overview = service.build_monthly_overview(target_date=subscription.created_at.date(), days_ahead=30)

    assert subscriptions[0].key == "spotify-premium"
    assert subscriptions[0].next_charge_date is not None
    assert overview.active_subscription_count == 1
    assert overview.paused_subscription_count == 0
    assert overview.cancelled_subscription_count == 0
    assert overview.scheduled_subscription_count == 1
    assert overview.missing_schedule_count == 0
    assert overview.totals_by_currency == {"TWD": 149.0}
    assert overview.totals_by_category == {"entertainment": {"TWD": 149.0}}
    assert overview.upcoming_charges[0].name == "Spotify Premium"
    assert overview.upcoming_charges[0].days_until_charge is not None


def test_subscription_service_rejects_duplicate_key_or_name(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = SubscriptionService()
    payload = SubscriptionCreate(name="Notion AI", amount=300.0, billing_day=10)

    service.create_subscription(payload)

    try:
        service.create_subscription(payload)
    except SubscriptionConflictError as error:
        assert "already exists" in str(error)
    else:
        raise AssertionError("Expected duplicate subscription conflict")


def test_subscription_api_create_list_update_and_overview(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    with TestClient(app) as client:
        create_response = client.post(
            "/subscriptions",
            json={
                "name": "ChatGPT Plus",
                "amount": 20,
                "currency": "USD",
                "billing_day": 9,
                "category": "ai",
            },
        )
        list_response = client.get("/subscriptions", params={"active_only": True})
        update_response = client.patch(
            "/subscriptions/chatgpt-plus",
            json={
                "notes": "Primary AI tool",
                "tags": ["ai", "writing"],
            },
        )
        overview_response = client.get(
            "/subscriptions/overview/monthly",
            params={"target_date": "2026-05-08", "days_ahead": 10},
        )

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert update_response.status_code == 200
    assert overview_response.status_code == 200
    assert list_response.json()[0]["key"] == "chatgpt-plus"
    assert list_response.json()[0]["status"] == "active"
    assert list_response.json()[0]["schedule_status"] == "scheduled"
    assert update_response.json()["notes"] == "Primary AI tool"
    assert overview_response.json()["totals_by_currency"] == {"USD": 20.0}
    assert overview_response.json()["upcoming_charges"][0]["next_charge_date"] == "2026-05-09"
    assert overview_response.json()["paused_subscription_count"] == 0
    assert overview_response.json()["cancelled_subscription_count"] == 0
    assert overview_response.json()["scheduled_subscription_count"] == 1
    assert overview_response.json()["missing_schedule_count"] == 0


def test_subscription_service_supports_fixed_day_cycle(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = SubscriptionService()

    subscription = service.create_subscription(
        SubscriptionCreate(
            name="Vtuber Member",
            amount=75.0,
            currency="TWD",
            recurrence_kind=SubscriptionRecurrenceKind.fixed_days,
            anchor_charge_date="2026-05-28",
            interval_days=30,
            category=SubscriptionCategory.membership,
            notes="YT membership",
        )
    )

    item = service.get_subscription(subscription.key, reference_date=subscription.created_at.date())
    future_item = service.get_subscription(subscription.key, reference_date=date.fromisoformat("2026-06-29"))

    assert item.next_charge_date == date.fromisoformat("2026-05-28")
    assert item.status == "active"
    assert item.schedule_status == "scheduled"
    assert future_item.next_charge_date == date.fromisoformat("2026-07-27")


def test_subscription_cli_add_list_and_overview(tmp_path, monkeypatch, capsys):
    use_temp_database(tmp_path, monkeypatch)

    add_code = cli_main(
        [
            "subscription",
            "add",
            "YouTube",
            "Premium",
            "--amount",
            "199",
            "--billing-day",
            "28",
            "--category",
            "entertainment",
            "--tag",
            "video",
        ]
    )
    list_code = cli_main(["subscription", "list"])
    overview_code = cli_main(["subscription", "overview", "--date", "2026-05-08", "--days-ahead", "30"])
    captured = capsys.readouterr()

    assert add_code == 0
    assert list_code == 0
    assert overview_code == 0
    assert "Added subscription youtube-premium" in captured.out
    assert "YouTube Premium" in captured.out
    assert "Subscription overview (2026-05-08 to 2026-06-07)" in captured.out
    assert "Paused subscriptions:" in captured.out


def test_subscription_service_marks_unknown_schedule_for_review(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = SubscriptionService()

    service.create_subscription(
        SubscriptionCreate(
            name="ChatGPT Plus",
            amount=20.0,
            currency="USD",
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            category=SubscriptionCategory.ai,
        )
    )

    subscription = service.get_subscription("chatgpt-plus", reference_date=date.fromisoformat("2026-05-09"))
    overview = service.build_monthly_overview(target_date=date.fromisoformat("2026-05-09"), days_ahead=30)

    assert subscription.schedule_status == "needs_review"
    assert subscription.next_charge_date is None
    assert overview.scheduled_subscription_count == 0
    assert overview.missing_schedule_count == 1
    assert overview.missing_schedule_subscriptions[0].key == "chatgpt-plus"


def test_subscription_service_supports_paused_and_cancelled_status(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = SubscriptionService()

    service.create_subscription(
        SubscriptionCreate(
            name="Bahamut Anime",
            amount=390.0,
            currency="JPY",
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            category=SubscriptionCategory.entertainment,
            status=SubscriptionLifecycleStatus.paused,
        )
    )
    service.create_subscription(
        SubscriptionCreate(
            name="Old Membership",
            amount=9.99,
            currency="USD",
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            category=SubscriptionCategory.membership,
            status=SubscriptionLifecycleStatus.cancelled,
        )
    )
    service.create_subscription(
        SubscriptionCreate(
            name="Rika Membership",
            amount=5.7,
            currency="USDT",
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            category=SubscriptionCategory.membership,
            status=SubscriptionLifecycleStatus.paused,
        )
    )

    paused = service.get_subscription("bahamut-anime", reference_date=date.fromisoformat("2026-05-09"))
    cancelled = service.get_subscription("old-membership", reference_date=date.fromisoformat("2026-05-09"))
    crypto_paused = service.get_subscription("rika-membership", reference_date=date.fromisoformat("2026-05-09"))
    overview = service.build_monthly_overview(target_date=date.fromisoformat("2026-05-09"), days_ahead=30)

    assert paused.status == "paused"
    assert paused.active is False
    assert paused.schedule_status == "inactive"
    assert cancelled.status == "cancelled"
    assert cancelled.active is False
    assert crypto_paused.currency == "USDT"
    assert overview.active_subscription_count == 0
    assert overview.paused_subscription_count == 2
    assert overview.cancelled_subscription_count == 1


def test_subscription_service_maps_legacy_inactive_payload_to_paused(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = SubscriptionService()

    subscription = service.create_subscription(
        SubscriptionCreate(
            name="Legacy Inactive Plan",
            amount=12.0,
            recurrence_kind=SubscriptionRecurrenceKind.unknown,
            active=False,
        )
    )

    assert subscription.status == "paused"
    assert subscription.active is False
    assert subscription.schedule_status == "inactive"
