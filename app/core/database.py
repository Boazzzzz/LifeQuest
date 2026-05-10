import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from app.core.config import settings

try:
    import pyodbc
except ImportError:  # pragma: no cover - exercised only when MSSQL support is used.
    pyodbc = None


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_minutes INTEGER NOT NULL,
    source TEXT NOT NULL,
    summary TEXT NOT NULL,
    difficulty INTEGER,
    energy_level INTEGER,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_started_at
ON learning_sessions(started_at);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_subject
ON learning_sessions(subject);

CREATE TABLE IF NOT EXISTS activity_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    subject TEXT,
    occurred_at TEXT NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anki_daily_snapshots (
    id TEXT PRIMARY KEY,
    snapshot_date TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL DEFAULT 'all_decks',
    reviews INTEGER NOT NULL,
    accuracy REAL,
    again_count INTEGER NOT NULL DEFAULT 0,
    hard_count INTEGER NOT NULL DEFAULT 0,
    good_count INTEGER NOT NULL DEFAULT 0,
    easy_count INTEGER NOT NULL DEFAULT 0,
    non_again_rate REAL,
    due_count INTEGER NOT NULL DEFAULT 0,
    new_due_count INTEGER NOT NULL DEFAULT 0,
    learn_due_count INTEGER NOT NULL DEFAULT 0,
    review_due_count INTEGER NOT NULL DEFAULT 0,
    difficult_cards TEXT NOT NULL DEFAULT '[]',
    decks TEXT NOT NULL DEFAULT '[]',
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_anki_daily_snapshots_snapshot_date
ON anki_daily_snapshots(snapshot_date);

CREATE TABLE IF NOT EXISTS automation_definitions (
    id TEXT PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    external_project_path TEXT,
    command_hint TEXT,
    schedule_hint TEXT,
    log_path TEXT,
    owner TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_automation_definitions_key
ON automation_definitions(key);

CREATE INDEX IF NOT EXISTS idx_automation_definitions_category
ON automation_definitions(category);

CREATE INDEX IF NOT EXISTS idx_automation_definitions_enabled
ON automation_definitions(enabled);

CREATE TABLE IF NOT EXISTS automation_runs (
    id TEXT PRIMARY KEY,
    automation_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    trigger_source TEXT NOT NULL,
    items_processed INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    error_message TEXT,
    external_run_id TEXT,
    log_excerpt TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (automation_id) REFERENCES automation_definitions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_automation_runs_automation_started
ON automation_runs(automation_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_status
ON automation_runs(status);

CREATE TABLE IF NOT EXISTS work_knowledge_notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    sanitized_summary TEXT NOT NULL,
    commands TEXT NOT NULL DEFAULT '[]',
    concepts TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    systems TEXT NOT NULL DEFAULT '[]',
    follow_up TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_work_knowledge_notes_category
ON work_knowledge_notes(category);

CREATE INDEX IF NOT EXISTS idx_work_knowledge_notes_source
ON work_knowledge_notes(source);

CREATE INDEX IF NOT EXISTS idx_work_knowledge_notes_created_at
ON work_knowledge_notes(created_at);

CREATE TABLE IF NOT EXISTS subscriptions (
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

CREATE INDEX IF NOT EXISTS idx_subscriptions_key
ON subscriptions(key);

CREATE INDEX IF NOT EXISTS idx_subscriptions_active
ON subscriptions(active);

CREATE INDEX IF NOT EXISTS idx_subscriptions_category
ON subscriptions(category);
"""


MSSQL_SCHEMA_STATEMENTS = [
    """
    IF OBJECT_ID(N'learning_sessions', N'U') IS NULL
    BEGIN
        CREATE TABLE learning_sessions (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            subject NVARCHAR(50) NOT NULL,
            started_at NVARCHAR(64) NOT NULL,
            ended_at NVARCHAR(64) NULL,
            duration_minutes INT NOT NULL,
            source NVARCHAR(50) NOT NULL,
            summary NVARCHAR(2000) NOT NULL,
            difficulty INT NULL,
            energy_level INT NULL,
            tags NVARCHAR(MAX) NOT NULL CONSTRAINT df_learning_sessions_tags DEFAULT N'[]',
            created_at NVARCHAR(64) NOT NULL
        )
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_learning_sessions_started_at'
          AND object_id = OBJECT_ID(N'learning_sessions')
    )
    BEGIN
        CREATE INDEX idx_learning_sessions_started_at ON learning_sessions(started_at)
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_learning_sessions_subject'
          AND object_id = OBJECT_ID(N'learning_sessions')
    )
    BEGIN
        CREATE INDEX idx_learning_sessions_subject ON learning_sessions(subject)
    END
    """,
    """
    IF OBJECT_ID(N'activity_events', N'U') IS NULL
    BEGIN
        CREATE TABLE activity_events (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            event_type NVARCHAR(100) NOT NULL,
            subject NVARCHAR(50) NULL,
            occurred_at NVARCHAR(64) NOT NULL,
            source NVARCHAR(50) NOT NULL,
            payload NVARCHAR(MAX) NOT NULL,
            created_at NVARCHAR(64) NOT NULL
        )
    END
    """,
    """
    IF OBJECT_ID(N'anki_daily_snapshots', N'U') IS NULL
    BEGIN
        CREATE TABLE anki_daily_snapshots (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            snapshot_date NVARCHAR(32) NOT NULL UNIQUE,
            scope NVARCHAR(50) NOT NULL CONSTRAINT df_anki_daily_snapshots_scope DEFAULT N'all_decks',
            reviews INT NOT NULL,
            accuracy FLOAT NULL,
            again_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_again_count DEFAULT 0,
            hard_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_hard_count DEFAULT 0,
            good_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_good_count DEFAULT 0,
            easy_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_easy_count DEFAULT 0,
            non_again_rate FLOAT NULL,
            due_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_due_count DEFAULT 0,
            new_due_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_new_due_count DEFAULT 0,
            learn_due_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_learn_due_count DEFAULT 0,
            review_due_count INT NOT NULL CONSTRAINT df_anki_daily_snapshots_review_due_count DEFAULT 0,
            difficult_cards NVARCHAR(MAX) NOT NULL CONSTRAINT df_anki_daily_snapshots_difficult_cards DEFAULT N'[]',
            decks NVARCHAR(MAX) NOT NULL CONSTRAINT df_anki_daily_snapshots_decks DEFAULT N'[]',
            imported_at NVARCHAR(64) NOT NULL
        )
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_anki_daily_snapshots_snapshot_date'
          AND object_id = OBJECT_ID(N'anki_daily_snapshots')
    )
    BEGIN
        CREATE INDEX idx_anki_daily_snapshots_snapshot_date ON anki_daily_snapshots(snapshot_date)
    END
    """,
    """
    IF OBJECT_ID(N'automation_definitions', N'U') IS NULL
    BEGIN
        CREATE TABLE automation_definitions (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            [key] NVARCHAR(120) NOT NULL UNIQUE,
            name NVARCHAR(200) NOT NULL,
            category NVARCHAR(50) NOT NULL,
            external_project_path NVARCHAR(1000) NULL,
            command_hint NVARCHAR(1000) NULL,
            schedule_hint NVARCHAR(500) NULL,
            log_path NVARCHAR(1000) NULL,
            owner NVARCHAR(200) NULL,
            enabled BIT NOT NULL CONSTRAINT df_automation_definitions_enabled DEFAULT 1,
            notes NVARCHAR(MAX) NULL,
            tags NVARCHAR(MAX) NOT NULL CONSTRAINT df_automation_definitions_tags DEFAULT N'[]',
            created_at NVARCHAR(64) NOT NULL,
            updated_at NVARCHAR(64) NOT NULL
        )
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_automation_definitions_key'
          AND object_id = OBJECT_ID(N'automation_definitions')
    )
    BEGIN
        CREATE INDEX idx_automation_definitions_key ON automation_definitions([key])
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_automation_definitions_category'
          AND object_id = OBJECT_ID(N'automation_definitions')
    )
    BEGIN
        CREATE INDEX idx_automation_definitions_category ON automation_definitions(category)
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_automation_definitions_enabled'
          AND object_id = OBJECT_ID(N'automation_definitions')
    )
    BEGIN
        CREATE INDEX idx_automation_definitions_enabled ON automation_definitions(enabled)
    END
    """,
    """
    IF OBJECT_ID(N'automation_runs', N'U') IS NULL
    BEGIN
        CREATE TABLE automation_runs (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            automation_id NVARCHAR(64) NOT NULL,
            started_at NVARCHAR(64) NOT NULL,
            finished_at NVARCHAR(64) NULL,
            status NVARCHAR(50) NOT NULL,
            trigger_source NVARCHAR(50) NOT NULL,
            items_processed INT NOT NULL CONSTRAINT df_automation_runs_items_processed DEFAULT 0,
            summary NVARCHAR(MAX) NULL,
            error_message NVARCHAR(MAX) NULL,
            external_run_id NVARCHAR(500) NULL,
            log_excerpt NVARCHAR(MAX) NULL,
            created_at NVARCHAR(64) NOT NULL,
            CONSTRAINT fk_automation_runs_automation
                FOREIGN KEY (automation_id) REFERENCES automation_definitions(id) ON DELETE CASCADE
        )
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_automation_runs_automation_started'
          AND object_id = OBJECT_ID(N'automation_runs')
    )
    BEGIN
        CREATE INDEX idx_automation_runs_automation_started
        ON automation_runs(automation_id, started_at DESC)
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_automation_runs_status'
          AND object_id = OBJECT_ID(N'automation_runs')
    )
    BEGIN
        CREATE INDEX idx_automation_runs_status ON automation_runs(status)
    END
    """,
    """
    IF OBJECT_ID(N'work_knowledge_notes', N'U') IS NULL
    BEGIN
        CREATE TABLE work_knowledge_notes (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            title NVARCHAR(200) NOT NULL,
            category NVARCHAR(50) NOT NULL,
            sanitized_summary NVARCHAR(MAX) NOT NULL,
            commands NVARCHAR(MAX) NOT NULL CONSTRAINT df_work_knowledge_notes_commands DEFAULT N'[]',
            concepts NVARCHAR(MAX) NOT NULL CONSTRAINT df_work_knowledge_notes_concepts DEFAULT N'[]',
            source NVARCHAR(50) NOT NULL,
            sensitivity NVARCHAR(50) NOT NULL,
            systems NVARCHAR(MAX) NOT NULL CONSTRAINT df_work_knowledge_notes_systems DEFAULT N'[]',
            follow_up NVARCHAR(MAX) NULL,
            tags NVARCHAR(MAX) NOT NULL CONSTRAINT df_work_knowledge_notes_tags DEFAULT N'[]',
            created_at NVARCHAR(64) NOT NULL,
            updated_at NVARCHAR(64) NOT NULL
        )
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_work_knowledge_notes_category'
          AND object_id = OBJECT_ID(N'work_knowledge_notes')
    )
    BEGIN
        CREATE INDEX idx_work_knowledge_notes_category ON work_knowledge_notes(category)
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_work_knowledge_notes_source'
          AND object_id = OBJECT_ID(N'work_knowledge_notes')
    )
    BEGIN
        CREATE INDEX idx_work_knowledge_notes_source ON work_knowledge_notes(source)
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_work_knowledge_notes_created_at'
          AND object_id = OBJECT_ID(N'work_knowledge_notes')
    )
    BEGIN
        CREATE INDEX idx_work_knowledge_notes_created_at ON work_knowledge_notes(created_at)
    END
    """,
    """
    IF OBJECT_ID(N'subscriptions', N'U') IS NULL
    BEGIN
        CREATE TABLE subscriptions (
            id NVARCHAR(64) NOT NULL PRIMARY KEY,
            [key] NVARCHAR(120) NOT NULL UNIQUE,
            name NVARCHAR(200) NOT NULL UNIQUE,
            amount FLOAT NOT NULL,
            currency NVARCHAR(8) NOT NULL,
            recurrence_kind NVARCHAR(20) NOT NULL CONSTRAINT df_subscriptions_recurrence_kind DEFAULT N'monthly',
            billing_day INT NULL,
            anchor_charge_date NVARCHAR(32) NULL,
            interval_days INT NULL,
            category NVARCHAR(50) NOT NULL,
            status NVARCHAR(20) NOT NULL CONSTRAINT df_subscriptions_status DEFAULT N'active',
            active BIT NOT NULL CONSTRAINT df_subscriptions_active DEFAULT 1,
            notes NVARCHAR(MAX) NULL,
            tags NVARCHAR(MAX) NOT NULL CONSTRAINT df_subscriptions_tags DEFAULT N'[]',
            created_at NVARCHAR(64) NOT NULL,
            updated_at NVARCHAR(64) NOT NULL
        )
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_subscriptions_key'
          AND object_id = OBJECT_ID(N'subscriptions')
    )
    BEGIN
        CREATE INDEX idx_subscriptions_key ON subscriptions([key])
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_subscriptions_active'
          AND object_id = OBJECT_ID(N'subscriptions')
    )
    BEGIN
        CREATE INDEX idx_subscriptions_active ON subscriptions(active)
    END
    """,
    """
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'idx_subscriptions_category'
          AND object_id = OBJECT_ID(N'subscriptions')
    )
    BEGIN
        CREATE INDEX idx_subscriptions_category ON subscriptions(category)
    END
    """,
]


def initialize_database() -> None:
    from app.core.migrations import run_migrations

    run_migrations()


@contextmanager
def connect() -> Iterator[Any]:
    connection = _open_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def execute(statement: str, params: Sequence[Any] = ()) -> None:
    with connect() as connection:
        cursor = connection.cursor()
        cursor.execute(statement, tuple(params))


def fetch_one(statement: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
    with connect() as connection:
        cursor = connection.cursor()
        cursor.execute(statement, tuple(params))
        rows = _rows_from_cursor(cursor)
    if not rows:
        return None
    return rows[0]


def fetch_all(statement: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        cursor = connection.cursor()
        cursor.execute(statement, tuple(params))
        return _rows_from_cursor(cursor)


def is_mssql_backend() -> bool:
    return settings.database_backend == "mssql"


def select_limit_clause(limit: int) -> str:
    if is_mssql_backend():
        return f"TOP {limit} "
    return ""


def _open_connection() -> Any:
    if settings.database_backend == "sqlite":
        connection = sqlite3.connect(settings.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    connection_string = settings.mssql_connection_string
    if not connection_string:
        raise RuntimeError("MSSQL backend requires MSSQL_CONNECTION_STRING")
    if pyodbc is None:
        raise RuntimeError("MSSQL backend requires the optional 'pyodbc' dependency")
    return pyodbc.connect(connection_string)


def _rows_from_cursor(cursor: Any) -> list[dict[str, Any]]:
    if cursor.description is None:
        return []
    columns = [str(column[0]) for column in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row, strict=False)) for row in rows]


def _ensure_sqlite_snapshot_columns(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(anki_daily_snapshots)").fetchall()
    existing_columns = {str(row[1]) for row in rows}
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
        connection.execute(
            "ALTER TABLE anki_daily_snapshots ADD COLUMN non_again_rate REAL"
        )
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


def _ensure_sqlite_subscription_columns(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS subscriptions_new")
    rows = connection.execute("PRAGMA table_info(subscriptions)").fetchall()
    if not rows:
        return

    existing_columns = {str(row[1]): row for row in rows}
    billing_day_is_required = bool(existing_columns.get("billing_day", [None, None, None, 0])[3])
    required_columns = {"recurrence_kind", "anchor_charge_date", "interval_days", "status"}
    if not billing_day_is_required and required_columns.issubset(existing_columns):
        return

    recurrence_kind_select = "recurrence_kind" if "recurrence_kind" in existing_columns else "'monthly'"
    billing_day_select = "billing_day" if "billing_day" in existing_columns else "NULL"
    anchor_charge_date_select = "anchor_charge_date" if "anchor_charge_date" in existing_columns else "NULL"
    interval_days_select = "interval_days" if "interval_days" in existing_columns else "NULL"
    status_select = "status" if "status" in existing_columns else "CASE WHEN active = 1 THEN 'active' ELSE 'paused' END"

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
