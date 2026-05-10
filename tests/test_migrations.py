from contextlib import contextmanager

import app.core.migrations as migrations_module
from app.core.migrations import MigrationRevision, list_migration_statuses, run_migrations


def test_run_migrations_applies_only_pending_revisions(tmp_path, monkeypatch):
    callbacks: list[str] = []
    recorded: list[str] = []
    dummy_connection = object()

    @contextmanager
    def fake_connect():
        yield dummy_connection

    revisions = (
        MigrationRevision(
            revision="0001_initial",
            description="Initial schema",
            apply_sqlite=lambda connection: callbacks.append(f"apply:{connection is dummy_connection}:0001"),
        ),
        MigrationRevision(
            revision="0002_follow_up",
            description="Follow-up schema change",
            apply_sqlite=lambda connection: callbacks.append(f"apply:{connection is dummy_connection}:0002"),
        ),
    )

    monkeypatch.setattr(migrations_module, "MIGRATIONS", revisions)
    monkeypatch.setattr(migrations_module, "connect", fake_connect)
    monkeypatch.setattr(migrations_module.settings, "database_backend", "sqlite")
    monkeypatch.setattr(migrations_module.settings, "database_path", tmp_path / "lifequest.db")
    monkeypatch.setattr(migrations_module, "_ensure_migration_table", lambda connection: recorded.append("ensure"))
    monkeypatch.setattr(migrations_module, "_fetch_applied_revisions", lambda connection: {"0001_initial"})
    monkeypatch.setattr(
        migrations_module,
        "_record_migration",
        lambda connection, migration: recorded.append(migration.revision),
    )

    run_migrations()

    assert callbacks == ["apply:True:0002"]
    assert recorded == ["ensure", "0002_follow_up"]


def test_list_migration_statuses_marks_applied_revisions(monkeypatch):
    revisions = (
        MigrationRevision(revision="0001_initial", description="Initial schema"),
        MigrationRevision(revision="0002_follow_up", description="Follow-up schema change"),
    )

    monkeypatch.setattr(migrations_module, "MIGRATIONS", revisions)
    monkeypatch.setattr(migrations_module, "get_applied_migration_revisions", lambda: {"0001_initial"})

    statuses = list_migration_statuses()

    assert [(status.revision, status.applied) for status in statuses] == [
        ("0001_initial", True),
        ("0002_follow_up", False),
    ]
