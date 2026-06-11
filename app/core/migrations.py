from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.database import (
    MSSQL_SCHEMA_STATEMENTS,
    SQLITE_SCHEMA,
    connect,
    is_mssql_backend,
    _ensure_sqlite_snapshot_columns,
    _ensure_sqlite_subscription_columns,
)

Connection = Any
MigrationCallback = Callable[[Connection], None]


@dataclass(frozen=True)
class MigrationRevision:
    revision: str
    description: str
    apply_sqlite: MigrationCallback | None = None
    apply_mssql: MigrationCallback | None = None


@dataclass(frozen=True)
class MigrationStatus:
    revision: str
    description: str
    applied: bool


def run_migrations() -> None:
    if not is_mssql_backend():
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    with connect() as connection:
        _ensure_migration_table(connection)
        applied = _fetch_applied_revisions(connection)
        for migration in MIGRATIONS:
            if migration.revision in applied:
                continue
            _apply_migration(connection, migration)
            _record_migration(connection, migration)


def list_migration_statuses() -> list[MigrationStatus]:
    applied = get_applied_migration_revisions()
    return [
        MigrationStatus(
            revision=migration.revision,
            description=migration.description,
            applied=migration.revision in applied,
        )
        for migration in MIGRATIONS
    ]


def get_applied_migration_revisions() -> set[str]:
    if not is_mssql_backend() and not _sqlite_database_exists(settings.database_path):
        return set()

    with connect() as connection:
        if not _migration_table_exists(connection):
            return set()
        return _fetch_applied_revisions(connection)


def _ensure_migration_table(connection: Connection) -> None:
    if is_mssql_backend():
        connection.cursor().execute(
            """
            IF OBJECT_ID(N'schema_migrations', N'U') IS NULL
            BEGIN
                CREATE TABLE schema_migrations (
                    revision NVARCHAR(64) NOT NULL PRIMARY KEY,
                    description NVARCHAR(255) NOT NULL,
                    applied_at NVARCHAR(64) NOT NULL
                )
            END
            """
        )
        return

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            revision TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _migration_table_exists(connection: Connection) -> bool:
    if is_mssql_backend():
        rows = connection.cursor().execute(
            """
            SELECT 1
            FROM sys.tables
            WHERE name = N'schema_migrations'
            """
        ).fetchall()
        return bool(rows)

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_migrations'
        """
    ).fetchall()
    return bool(rows)


def _fetch_applied_revisions(connection: Connection) -> set[str]:
    if is_mssql_backend():
        rows = connection.cursor().execute(
            "SELECT revision FROM schema_migrations ORDER BY revision"
        ).fetchall()
        return {str(row[0]) for row in rows}

    rows = connection.execute("SELECT revision FROM schema_migrations ORDER BY revision").fetchall()
    return {str(row[0]) for row in rows}


def _record_migration(connection: Connection, migration: MigrationRevision) -> None:
    if is_mssql_backend():
        connection.cursor().execute(
            """
            INSERT INTO schema_migrations (revision, description, applied_at)
            VALUES (?, ?, CONVERT(NVARCHAR(64), SYSUTCDATETIME(), 127))
            """,
            (migration.revision, migration.description),
        )
        return

    connection.execute(
        """
        INSERT INTO schema_migrations (revision, description)
        VALUES (?, ?)
        """,
        (migration.revision, migration.description),
    )


def _apply_migration(connection: Connection, migration: MigrationRevision) -> None:
    callback = migration.apply_mssql if is_mssql_backend() else migration.apply_sqlite
    if callback is None:
        return
    callback(connection)


def _sqlite_database_exists(path: Path) -> bool:
    return path.exists()


def _apply_sqlite_initial_schema(connection: Connection) -> None:
    connection.executescript(SQLITE_SCHEMA)


def _apply_mssql_initial_schema(connection: Connection) -> None:
    cursor = connection.cursor()
    for statement in MSSQL_SCHEMA_STATEMENTS:
        cursor.execute(statement)


def _apply_sqlite_snapshot_column_migration(connection: Connection) -> None:
    _ensure_sqlite_snapshot_columns(connection)


def _apply_sqlite_subscription_schema_migration(connection: Connection) -> None:
    _ensure_sqlite_subscription_columns(connection)


MIGRATIONS: tuple[MigrationRevision, ...] = (
    MigrationRevision(
        revision="0001_initial_schema",
        description="Create the baseline LifeQuest schema.",
        apply_sqlite=_apply_sqlite_initial_schema,
        apply_mssql=_apply_mssql_initial_schema,
    ),
    MigrationRevision(
        revision="0002_anki_snapshot_columns",
        description="Backfill expanded Anki snapshot columns for legacy SQLite databases.",
        apply_sqlite=_apply_sqlite_snapshot_column_migration,
    ),
    MigrationRevision(
        revision="0003_subscription_schema",
        description="Normalize subscription recurrence fields for legacy SQLite databases.",
        apply_sqlite=_apply_sqlite_subscription_schema_migration,
    ),
)
