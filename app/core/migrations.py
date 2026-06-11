import sqlite3
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SQLiteMigration:
    version: str
    description: str
    apply: Callable[[sqlite3.Connection], None]


def run_sqlite_migrations(connection: sqlite3.Connection) -> None:
    _ensure_migration_table(connection)
    applied_versions = _applied_versions(connection)
    for migration in SQLITE_MIGRATIONS:
        if migration.version in applied_versions:
            continue
        migration.apply(connection)
        connection.execute(
            """
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES (?, ?, datetime('now'))
            """,
            (migration.version, migration.description),
        )


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _applied_versions(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {str(row[0]) for row in rows}


def _table_columns(connection: sqlite3.Connection, table_name: str) -> dict[str, sqlite3.Row]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]): row for row in rows}


def _add_anki_snapshot_rollup_columns(connection: sqlite3.Connection) -> None:
    existing_columns = _table_columns(connection, "anki_daily_snapshots")
    if "scope" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN scope TEXT NOT NULL DEFAULT 'all_decks'"
        )
    if "again_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN again_count INTEGER NOT NULL DEFAULT 0"
        )
    if "hard_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN hard_count INTEGER NOT NULL DEFAULT 0"
        )
    if "good_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN good_count INTEGER NOT NULL DEFAULT 0"
        )
    if "easy_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN easy_count INTEGER NOT NULL DEFAULT 0"
        )
    if "non_again_rate" not in existing_columns:
        connection.execute("ALTER TABLE anki_daily_snapshots ADD COLUMN non_again_rate REAL")
    if "due_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN due_count INTEGER NOT NULL DEFAULT 0"
        )
    if "new_due_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN new_due_count INTEGER NOT NULL DEFAULT 0"
        )
    if "learn_due_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN learn_due_count INTEGER NOT NULL DEFAULT 0"
        )
    if "review_due_count" not in existing_columns:
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN review_due_count INTEGER NOT NULL DEFAULT 0"
        )


def _rebuild_subscriptions_for_recurrence_status(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS subscriptions_new")
    existing_columns = _table_columns(connection, "subscriptions")
    if not existing_columns:
        return

    billing_day_is_required = bool(existing_columns.get("billing_day", [None, None, None, 0])[3])
    required_columns = {"recurrence_kind", "anchor_charge_date", "interval_days", "status"}
    if not billing_day_is_required and required_columns.issubset(existing_columns):
        return

    recurrence_kind_select = "recurrence_kind" if "recurrence_kind" in existing_columns else "'monthly'"
    billing_day_select = "billing_day" if "billing_day" in existing_columns else "NULL"
    anchor_charge_date_select = "anchor_charge_date" if "anchor_charge_date" in existing_columns else "NULL"
    interval_days_select = "interval_days" if "interval_days" in existing_columns else "NULL"
    status_select = (
        "status"
        if "status" in existing_columns
        else "CASE WHEN active = 1 THEN 'active' ELSE 'paused' END"
    )

    connection.executescript(
        f"""
        CREATE TABLE subscriptions_new (
            id TEXT PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            recurrence_kind TEXT NOT NULL DEFAULT 'monthly',
            billing_day INTEGER,
            anchor_charge_date TEXT,
            interval_days INTEGER,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            active INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        INSERT INTO subscriptions_new (
            id, key, name, amount, currency, recurrence_kind, billing_day,
            anchor_charge_date, interval_days, category, status, active, notes, tags,
            created_at, updated_at
        )
        SELECT
            id,
            key,
            name,
            amount,
            currency,
            COALESCE({recurrence_kind_select}, 'monthly'),
            {billing_day_select},
            {anchor_charge_date_select},
            {interval_days_select},
            category,
            COALESCE({status_select}, CASE WHEN active = 1 THEN 'active' ELSE 'paused' END),
            active,
            notes,
            tags,
            created_at,
            updated_at
        FROM subscriptions;

        DROP TABLE subscriptions;
        ALTER TABLE subscriptions_new RENAME TO subscriptions;

        CREATE INDEX IF NOT EXISTS idx_subscriptions_key ON subscriptions(key);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(active);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_category ON subscriptions(category);
        """
    )


SQLITE_MIGRATIONS = [
    SQLiteMigration(
        version="0001_anki_snapshot_rollup_columns",
        description="Add scoped Anki review breakdown and due-count columns",
        apply=_add_anki_snapshot_rollup_columns,
    ),
    SQLiteMigration(
        version="0002_subscription_recurrence_status",
        description="Rebuild subscriptions for recurrence and lifecycle status columns",
        apply=_rebuild_subscriptions_for_recurrence_status,
    ),
]
