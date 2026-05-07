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

