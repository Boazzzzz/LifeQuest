import sqlite3

from app.core.database import initialize_database
from app.core.exceptions import (
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
)
from app.integrations.anki import AnkiConnectError
from app.integrations.github import GitHubIntegrationError
from app.services.automation import AutomationConflictError, AutomationNotFoundError
from app.services.scheduled_automation import ScheduledAutomationNotFoundError
from app.services.subscription import SubscriptionConflictError, SubscriptionNotFoundError
from app.services.work_knowledge import WorkKnowledgeNotFoundError


def test_initialize_database_records_sqlite_migrations(temp_database):
    with sqlite3.connect(temp_database) as connection:
        versions = {
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }

    assert versions == {
        "0001_anki_snapshot_rollup_columns",
        "0002_subscription_recurrence_status",
    }


def test_initialize_database_upgrades_legacy_sqlite_tables(temp_database_path):
    with sqlite3.connect(temp_database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE anki_daily_snapshots (
                id TEXT PRIMARY KEY,
                snapshot_date TEXT NOT NULL UNIQUE,
                reviews INTEGER NOT NULL,
                accuracy REAL,
                difficult_cards TEXT NOT NULL DEFAULT '[]',
                decks TEXT NOT NULL DEFAULT '[]',
                imported_at TEXT NOT NULL
            );

            CREATE TABLE subscriptions (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                billing_day INTEGER NOT NULL,
                category TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            INSERT INTO subscriptions (
                id, key, name, amount, currency, billing_day, category,
                active, notes, tags, created_at, updated_at
            )
            VALUES (
                'sub_1', 'legacy-service', 'Legacy Service', 100, 'TWD', 12,
                'utility', 1, NULL, '[]', '2026-05-01T00:00:00+00:00',
                '2026-05-01T00:00:00+00:00'
            );
            """
        )

    initialize_database()

    with sqlite3.connect(temp_database_path) as connection:
        snapshot_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(anki_daily_snapshots)").fetchall()
        }
        subscription_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(subscriptions)").fetchall()
        }
        subscription = connection.execute(
            """
            SELECT recurrence_kind, billing_day, status, active
            FROM subscriptions
            WHERE key = 'legacy-service'
            """
        ).fetchone()

    assert {"scope", "again_count", "due_count", "review_due_count"}.issubset(snapshot_columns)
    assert "recurrence_kind" in subscription_columns
    assert "anchor_charge_date" in subscription_columns
    assert "interval_days" in subscription_columns
    assert "status" in subscription_columns
    assert subscription_columns["billing_day"][3] == 0
    assert subscription == ("monthly", 12, "active", 1)


def test_domain_exceptions_share_common_base_classes():
    assert issubclass(AutomationNotFoundError, NotFoundError)
    assert issubclass(SubscriptionNotFoundError, NotFoundError)
    assert issubclass(WorkKnowledgeNotFoundError, NotFoundError)
    assert issubclass(ScheduledAutomationNotFoundError, NotFoundError)
    assert issubclass(AutomationConflictError, ConflictError)
    assert issubclass(SubscriptionConflictError, ConflictError)
    assert issubclass(AnkiConnectError, ExternalServiceError)
    assert issubclass(GitHubIntegrationError, ExternalServiceError)
    assert issubclass(ConfigurationError, RuntimeError)
    assert issubclass(ConflictError, ValueError)
    assert issubclass(NotFoundError, ValueError)
