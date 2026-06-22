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


def _apply_sqlite_money_schema_migration(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS money_goals (
            id TEXT PRIMARY KEY,
            goal_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'TWD',
            monthly_contribution_target REAL NOT NULL DEFAULT 0,
            target_date TEXT,
            protected INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_money_goals_key
        ON money_goals(goal_key);

        CREATE INDEX IF NOT EXISTS idx_money_goals_category_status
        ON money_goals(category, status);

        CREATE TABLE IF NOT EXISTS money_goal_contributions (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            occurred_on TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'TWD',
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (goal_id) REFERENCES money_goals(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_money_goal_contributions_goal_date
        ON money_goal_contributions(goal_id, occurred_on DESC);

        CREATE TABLE IF NOT EXISTS money_weekly_checkins (
            id TEXT PRIMARY KEY,
            week_start_date TEXT NOT NULL UNIQUE,
            monthly_income REAL NOT NULL DEFAULT 0,
            necessary_expenses REAL NOT NULL DEFAULT 0,
            flexible_expenses REAL NOT NULL DEFAULT 0,
            planned_savings REAL NOT NULL DEFAULT 0,
            actual_savings REAL NOT NULL DEFAULT 0,
            investment_contribution REAL NOT NULL DEFAULT 0,
            debt_payment REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'TWD',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_money_weekly_checkins_week
        ON money_weekly_checkins(week_start_date DESC);

        CREATE TABLE IF NOT EXISTS money_loan_scenarios (
            id TEXT PRIMARY KEY,
            loan_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            principal REAL NOT NULL,
            annual_interest_rate REAL NOT NULL,
            term_months INTEGER NOT NULL,
            monthly_payment REAL NOT NULL,
            start_date TEXT,
            purpose TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_money_loan_scenarios_key
        ON money_loan_scenarios(loan_key);

        CREATE TABLE IF NOT EXISTS money_leverage_strategy_plans (
            id TEXT PRIMARY KEY,
            plan_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            market TEXT NOT NULL DEFAULT 'tw',
            base_asset_label TEXT NOT NULL,
            leveraged_asset_label TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'TWD',
            target_total_equity_exposure_pct REAL NOT NULL DEFAULT 100,
            leveraged_position_pct REAL NOT NULL DEFAULT 50,
            cash_reserve_pct REAL NOT NULL DEFAULT 50,
            rebalance_frequency TEXT NOT NULL DEFAULT 'quarterly',
            emergency_fund_months_required REAL NOT NULL DEFAULT 6,
            max_debt_service_ratio REAL NOT NULL DEFAULT 0.2,
            minimum_cash_reserve_pct REAL NOT NULL DEFAULT 30,
            max_strategy_drawdown_pct REAL NOT NULL DEFAULT 35,
            protected_goal_keys TEXT NOT NULL DEFAULT '[]',
            loan_scenario_id TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (loan_scenario_id) REFERENCES money_loan_scenarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_money_leverage_strategy_plans_key
        ON money_leverage_strategy_plans(plan_key);

        CREATE INDEX IF NOT EXISTS idx_money_leverage_strategy_plans_status
        ON money_leverage_strategy_plans(status);

        CREATE TABLE IF NOT EXISTS money_strategy_decision_logs (
            id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            decision_date TEXT NOT NULL,
            decision TEXT NOT NULL,
            rationale TEXT NOT NULL,
            emotion TEXT,
            source_links TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES money_leverage_strategy_plans(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_money_strategy_decision_logs_plan_date
        ON money_strategy_decision_logs(plan_id, decision_date DESC);
        """
    )


def _apply_mssql_money_schema_migration(connection: Connection) -> None:
    cursor = connection.cursor()
    statements = [
        """
        IF OBJECT_ID(N'money_goals', N'U') IS NULL
        BEGIN
            CREATE TABLE money_goals (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                goal_key NVARCHAR(120) NOT NULL UNIQUE,
                name NVARCHAR(200) NOT NULL,
                category NVARCHAR(50) NOT NULL,
                target_amount FLOAT NOT NULL,
                current_amount FLOAT NOT NULL CONSTRAINT df_money_goals_current_amount DEFAULT 0,
                currency NVARCHAR(8) NOT NULL CONSTRAINT df_money_goals_currency DEFAULT N'TWD',
                monthly_contribution_target FLOAT NOT NULL CONSTRAINT df_money_goals_monthly_target DEFAULT 0,
                target_date NVARCHAR(32) NULL,
                protected BIT NOT NULL CONSTRAINT df_money_goals_protected DEFAULT 1,
                status NVARCHAR(20) NOT NULL CONSTRAINT df_money_goals_status DEFAULT N'active',
                notes NVARCHAR(MAX) NULL,
                created_at NVARCHAR(64) NOT NULL,
                updated_at NVARCHAR(64) NOT NULL
            )
        END
        """,
        """
        IF OBJECT_ID(N'money_goal_contributions', N'U') IS NULL
        BEGIN
            CREATE TABLE money_goal_contributions (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                goal_id NVARCHAR(64) NOT NULL,
                occurred_on NVARCHAR(32) NOT NULL,
                amount FLOAT NOT NULL,
                currency NVARCHAR(8) NOT NULL CONSTRAINT df_money_goal_contributions_currency DEFAULT N'TWD',
                note NVARCHAR(MAX) NULL,
                created_at NVARCHAR(64) NOT NULL,
                CONSTRAINT fk_money_goal_contributions_goal
                    FOREIGN KEY (goal_id) REFERENCES money_goals(id) ON DELETE CASCADE
            )
        END
        """,
        """
        IF OBJECT_ID(N'money_weekly_checkins', N'U') IS NULL
        BEGIN
            CREATE TABLE money_weekly_checkins (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                week_start_date NVARCHAR(32) NOT NULL UNIQUE,
                monthly_income FLOAT NOT NULL CONSTRAINT df_money_weekly_income DEFAULT 0,
                necessary_expenses FLOAT NOT NULL CONSTRAINT df_money_weekly_necessary DEFAULT 0,
                flexible_expenses FLOAT NOT NULL CONSTRAINT df_money_weekly_flexible DEFAULT 0,
                planned_savings FLOAT NOT NULL CONSTRAINT df_money_weekly_planned DEFAULT 0,
                actual_savings FLOAT NOT NULL CONSTRAINT df_money_weekly_actual DEFAULT 0,
                investment_contribution FLOAT NOT NULL CONSTRAINT df_money_weekly_investment DEFAULT 0,
                debt_payment FLOAT NOT NULL CONSTRAINT df_money_weekly_debt DEFAULT 0,
                currency NVARCHAR(8) NOT NULL CONSTRAINT df_money_weekly_currency DEFAULT N'TWD',
                notes NVARCHAR(MAX) NULL,
                created_at NVARCHAR(64) NOT NULL,
                updated_at NVARCHAR(64) NOT NULL
            )
        END
        """,
        """
        IF OBJECT_ID(N'money_loan_scenarios', N'U') IS NULL
        BEGIN
            CREATE TABLE money_loan_scenarios (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                loan_key NVARCHAR(120) NOT NULL UNIQUE,
                name NVARCHAR(200) NOT NULL,
                principal FLOAT NOT NULL,
                annual_interest_rate FLOAT NOT NULL,
                term_months INT NOT NULL,
                monthly_payment FLOAT NOT NULL,
                start_date NVARCHAR(32) NULL,
                purpose NVARCHAR(MAX) NULL,
                notes NVARCHAR(MAX) NULL,
                created_at NVARCHAR(64) NOT NULL,
                updated_at NVARCHAR(64) NOT NULL
            )
        END
        """,
        """
        IF OBJECT_ID(N'money_leverage_strategy_plans', N'U') IS NULL
        BEGIN
            CREATE TABLE money_leverage_strategy_plans (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                plan_key NVARCHAR(120) NOT NULL UNIQUE,
                name NVARCHAR(200) NOT NULL,
                market NVARCHAR(20) NOT NULL CONSTRAINT df_money_leverage_market DEFAULT N'tw',
                base_asset_label NVARCHAR(200) NOT NULL,
                leveraged_asset_label NVARCHAR(200) NOT NULL,
                currency NVARCHAR(8) NOT NULL CONSTRAINT df_money_leverage_currency DEFAULT N'TWD',
                target_total_equity_exposure_pct FLOAT NOT NULL CONSTRAINT df_money_leverage_target_exposure DEFAULT 100,
                leveraged_position_pct FLOAT NOT NULL CONSTRAINT df_money_leverage_position DEFAULT 50,
                cash_reserve_pct FLOAT NOT NULL CONSTRAINT df_money_leverage_cash DEFAULT 50,
                rebalance_frequency NVARCHAR(20) NOT NULL CONSTRAINT df_money_leverage_rebalance DEFAULT N'quarterly',
                emergency_fund_months_required FLOAT NOT NULL CONSTRAINT df_money_leverage_emergency DEFAULT 6,
                max_debt_service_ratio FLOAT NOT NULL CONSTRAINT df_money_leverage_debt_ratio DEFAULT 0.2,
                minimum_cash_reserve_pct FLOAT NOT NULL CONSTRAINT df_money_leverage_min_cash DEFAULT 30,
                max_strategy_drawdown_pct FLOAT NOT NULL CONSTRAINT df_money_leverage_max_drawdown DEFAULT 35,
                protected_goal_keys NVARCHAR(MAX) NOT NULL CONSTRAINT df_money_leverage_goal_keys DEFAULT N'[]',
                loan_scenario_id NVARCHAR(64) NULL,
                status NVARCHAR(20) NOT NULL CONSTRAINT df_money_leverage_status DEFAULT N'draft',
                notes NVARCHAR(MAX) NULL,
                created_at NVARCHAR(64) NOT NULL,
                updated_at NVARCHAR(64) NOT NULL,
                CONSTRAINT fk_money_leverage_loan
                    FOREIGN KEY (loan_scenario_id) REFERENCES money_loan_scenarios(id)
            )
        END
        """,
        """
        IF OBJECT_ID(N'money_strategy_decision_logs', N'U') IS NULL
        BEGIN
            CREATE TABLE money_strategy_decision_logs (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                plan_id NVARCHAR(64) NOT NULL,
                decision_date NVARCHAR(32) NOT NULL,
                decision NVARCHAR(200) NOT NULL,
                rationale NVARCHAR(MAX) NOT NULL,
                emotion NVARCHAR(200) NULL,
                source_links NVARCHAR(MAX) NOT NULL CONSTRAINT df_money_decision_links DEFAULT N'[]',
                created_at NVARCHAR(64) NOT NULL,
                CONSTRAINT fk_money_strategy_decision_logs_plan
                    FOREIGN KEY (plan_id) REFERENCES money_leverage_strategy_plans(id) ON DELETE CASCADE
            )
        END
        """,
    ]
    for statement in statements:
        cursor.execute(statement)


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
    MigrationRevision(
        revision="0004_money_schema",
        description="Create Money Quest goals, cashflow, loan, and leverage guardrail tables.",
        apply_sqlite=_apply_sqlite_money_schema_migration,
        apply_mssql=_apply_mssql_money_schema_migration,
    ),
)
