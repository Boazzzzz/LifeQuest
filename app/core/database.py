import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import settings


SCHEMA = """
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
"""


def initialize_database() -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
