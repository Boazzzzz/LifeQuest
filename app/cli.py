import argparse
import asyncio
import sys
from datetime import date, datetime, timezone
from typing import Sequence

from app.integrations.anki import AnkiAdapter
from app.core.database import initialize_database
from app.core.logging import configure_logging
from app.core.migrations import list_migration_statuses, run_migrations
from app.models.automation import (
    AutomationCategory,
    AutomationDefinitionCreate,
    AutomationRunCreate,
    AutomationRunStatus,
    AutomationTriggerSource,
)
from app.models.anki import AnkiHistoryOverview, AnkiReviewedTodayOverview, AnkiTodayOverview
from app.models.learning import LearningSessionCreate, LearningSubject
from app.models.subscription import (
    SubscriptionCategory,
    SubscriptionCreate,
    SubscriptionLifecycleStatus,
    SubscriptionRecurrenceKind,
    SubscriptionUpdate,
)
from app.models.work_knowledge import (
    WorkKnowledgeCategory,
    WorkKnowledgeNoteCreate,
    WorkKnowledgeSensitivity,
    WorkKnowledgeSource,
)
from app.services.automation import AutomationConflictError, AutomationNotFoundError, AutomationService
from app.services.learning import LearningService
from app.services.notion_schema import NotionSchemaService
from app.services.notion_sync import NotionSyncService
from app.services.scheduled_automation import ScheduledAutomationNotFoundError, ScheduledAutomationService
from app.services.subscription import SubscriptionConflictError, SubscriptionNotFoundError, SubscriptionService
from app.services.work_knowledge import WorkKnowledgeNotFoundError, WorkKnowledgeService


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    _configure_console_output()
    configure_logging()

    if args.command == "db":
        return _db_command(args)

    initialize_database()

    if args.command == "log":
        return _log_learning_session(args)
    if args.command == "pulse":
        return asyncio.run(_print_today_pulse())
    if args.command == "daily":
        return asyncio.run(_run_daily())
    if args.command == "anki-status":
        return asyncio.run(_print_anki_status())
    if args.command == "anki-today":
        return asyncio.run(_print_anki_today())
    if args.command == "anki-reviewed-today":
        return asyncio.run(_print_anki_reviewed_today(args))
    if args.command == "anki-history":
        return _print_anki_history(args)
    if args.command == "anki-difficult-history":
        return _print_anki_difficult_history(args)
    if args.command == "import-anki":
        return asyncio.run(_import_anki_today())
    if args.command == "import-github":
        return asyncio.run(_import_github_today())
    if args.command == "sync-notion":
        return asyncio.run(_sync_notion_today())
    if args.command == "automation":
        return _automation_command(args)
    if args.command == "subscription":
        return _subscription_command(args)
    if args.command == "work":
        return _work_command(args)
    if args.command == "notion":
        return _notion_command(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lifequest", description="LifeQuest command line tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    log_parser = subparsers.add_parser("log", help="Record a learning session.")
    log_parser.add_argument("subject", choices=[subject.value for subject in LearningSubject])
    log_parser.add_argument("minutes", type=int)
    log_parser.add_argument("summary", nargs="+")
    log_parser.add_argument("--difficulty", type=int, choices=range(1, 6))
    log_parser.add_argument("--energy-level", type=int, choices=range(1, 6))
    log_parser.add_argument("--tag", action="append", default=[])
    log_parser.add_argument("--started-at", type=parse_datetime)
    log_parser.add_argument("--ended-at", type=parse_datetime)

    subparsers.add_parser("pulse", help="Print today's learning pulse.")
    subparsers.add_parser("daily", help="Run the daily local learning check workflow.")
    subparsers.add_parser("anki-status", help="Check AnkiConnect status and configured decks.")
    subparsers.add_parser("anki-today", help="Show today's Anki stats from snapshot or live data.")
    reviewed_today_parser = subparsers.add_parser(
        "anki-reviewed-today",
        help="Show all unique cards reviewed today across new learning and reviews.",
    )
    reviewed_today_parser.add_argument("--date", type=parse_date, default=None)
    history_parser = subparsers.add_parser("anki-history", help="Show recent Anki snapshot history.")
    history_parser.add_argument("--days", type=int, default=7)
    difficult_history_parser = subparsers.add_parser(
        "anki-difficult-history",
        help="Show difficult cards that repeated in recent snapshots.",
    )
    difficult_history_parser.add_argument("--days", type=int, default=7)
    difficult_history_parser.add_argument("--limit", type=int, default=10)
    subparsers.add_parser("import-anki", help="Import today's Anki review stats.")
    subparsers.add_parser("import-github", help="Import today's GitHub Python activity.")
    subparsers.add_parser("sync-notion", help="Sync today's learning pulse to Notion.")
    add_db_parser(subparsers)
    add_automation_parser(subparsers)
    add_subscription_parser(subparsers)
    add_work_parser(subparsers)
    add_notion_parser(subparsers)

    return parser


def add_automation_parser(subparsers: argparse._SubParsersAction) -> None:
    automation_parser = subparsers.add_parser("automation", help="Manage automation registry and run ledger.")
    automation_subparsers = automation_parser.add_subparsers(dest="automation_command", required=True)

    automation_subparsers.add_parser("list", help="List registered automations.")

    register_parser = automation_subparsers.add_parser("register", help="Register an existing automation project.")
    register_parser.add_argument("key")
    register_parser.add_argument("name", nargs="+")
    register_parser.add_argument("--category", choices=[category.value for category in AutomationCategory], default="other")
    register_parser.add_argument("--project-path")
    register_parser.add_argument("--command-hint")
    register_parser.add_argument("--schedule-hint")
    register_parser.add_argument("--log-path")
    register_parser.add_argument("--owner")
    register_parser.add_argument("--notes")
    register_parser.add_argument("--tag", action="append", default=[])
    register_parser.add_argument("--disabled", action="store_true")

    runs_parser = automation_subparsers.add_parser("runs", help="List runs for one automation.")
    runs_parser.add_argument("automation_ref")
    runs_parser.add_argument("--limit", type=int, default=20)

    recent_parser = automation_subparsers.add_parser("recent", help="List recent automation runs.")
    recent_parser.add_argument("--limit", type=int, default=20)

    automation_subparsers.add_parser("scheduled-tasks", help="List built-in scheduled automation tasks.")
    run_scheduled_parser = automation_subparsers.add_parser(
        "run-scheduled",
        help="Run one built-in scheduled automation task and record the result.",
    )
    run_scheduled_parser.add_argument("task_key")

    automation_subparsers.add_parser("sync-notion", help="Sync automation registry to Notion.")

    log_run_parser = automation_subparsers.add_parser("log-run", help="Record one automation run.")
    log_run_parser.add_argument("automation_ref")
    log_run_parser.add_argument("--status", choices=[status.value for status in AutomationRunStatus], required=True)
    log_run_parser.add_argument(
        "--trigger-source",
        choices=[source.value for source in AutomationTriggerSource],
        default=AutomationTriggerSource.cli.value,
    )
    log_run_parser.add_argument("--items-processed", type=int, default=0)
    log_run_parser.add_argument("--summary", nargs="+")
    log_run_parser.add_argument("--error-message")
    log_run_parser.add_argument("--external-run-id")
    log_run_parser.add_argument("--log-excerpt")
    log_run_parser.add_argument("--started-at", type=parse_datetime)
    log_run_parser.add_argument("--finished-at", type=parse_datetime)


def add_db_parser(subparsers: argparse._SubParsersAction) -> None:
    db_parser = subparsers.add_parser("db", help="Inspect or apply database migrations.")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)
    db_subparsers.add_parser("upgrade", help="Apply all pending database migrations.")
    db_subparsers.add_parser("status", help="Show the current migration status.")


def add_work_parser(subparsers: argparse._SubParsersAction) -> None:
    work_parser = subparsers.add_parser("work", help="Capture sanitized work knowledge.")
    work_subparsers = work_parser.add_subparsers(dest="work_command", required=True)

    capture_parser = work_subparsers.add_parser("capture", help="Capture one sanitized work knowledge note.")
    capture_parser.add_argument("title", nargs="+")
    capture_parser.add_argument("--category", choices=[category.value for category in WorkKnowledgeCategory], default="other")
    capture_parser.add_argument("--summary", required=True)
    capture_parser.add_argument("--command", dest="commands", action="append", default=[])
    capture_parser.add_argument("--concept", action="append", default=[])
    capture_parser.add_argument("--source", choices=[source.value for source in WorkKnowledgeSource], default="manual")
    capture_parser.add_argument(
        "--sensitivity",
        choices=[sensitivity.value for sensitivity in WorkKnowledgeSensitivity],
        default="personal",
    )
    capture_parser.add_argument("--system", action="append", default=[])
    capture_parser.add_argument("--follow-up")
    capture_parser.add_argument("--tag", action="append", default=[])

    list_parser = work_subparsers.add_parser("list", help="List recent work knowledge notes.")
    list_parser.add_argument("--limit", type=int, default=20)

    work_subparsers.add_parser("sync-notion", help="Sync work knowledge notes to Notion.")


def add_subscription_parser(subparsers: argparse._SubParsersAction) -> None:
    subscription_parser = subparsers.add_parser("subscription", help="Track recurring monthly subscriptions.")
    subscription_subparsers = subscription_parser.add_subparsers(dest="subscription_command", required=True)

    add_parser = subscription_subparsers.add_parser("add", help="Add one subscription.")
    add_parser.add_argument("name", nargs="+")
    add_parser.add_argument("--key")
    add_parser.add_argument("--amount", type=float, required=True)
    add_parser.add_argument("--currency", default="TWD")
    add_parser.add_argument(
        "--recurrence",
        choices=[kind.value for kind in SubscriptionRecurrenceKind],
        default=SubscriptionRecurrenceKind.monthly.value,
    )
    add_parser.add_argument("--billing-day", type=int)
    add_parser.add_argument("--anchor-charge-date", type=parse_date)
    add_parser.add_argument("--interval-days", type=int)
    add_parser.add_argument(
        "--category",
        choices=[category.value for category in SubscriptionCategory],
        default="other",
    )
    add_parser.add_argument(
        "--status",
        choices=[status.value for status in SubscriptionLifecycleStatus],
        default=SubscriptionLifecycleStatus.active.value,
    )
    add_parser.add_argument("--notes")
    add_parser.add_argument("--tag", action="append", default=[])
    add_parser.add_argument("--inactive", action="store_true")

    list_parser = subscription_subparsers.add_parser("list", help="List subscriptions.")
    list_parser.add_argument("--all", action="store_true")
    list_parser.add_argument(
        "--status",
        choices=[status.value for status in SubscriptionLifecycleStatus],
    )

    overview_parser = subscription_subparsers.add_parser("overview", help="Show monthly subscription overview.")
    overview_parser.add_argument("--date", type=parse_date, default=None)
    overview_parser.add_argument("--days-ahead", type=int, default=30)

    update_parser = subscription_subparsers.add_parser("update", help="Update one subscription.")
    update_parser.add_argument("subscription_ref")
    update_parser.add_argument("--name", nargs="+")
    update_parser.add_argument("--amount", type=float)
    update_parser.add_argument("--currency")
    update_parser.add_argument(
        "--recurrence",
        choices=[kind.value for kind in SubscriptionRecurrenceKind],
    )
    update_parser.add_argument("--billing-day", type=int)
    update_parser.add_argument("--anchor-charge-date", type=parse_date)
    update_parser.add_argument("--interval-days", type=int)
    update_parser.add_argument(
        "--category",
        choices=[category.value for category in SubscriptionCategory],
    )
    update_parser.add_argument(
        "--status",
        choices=[status.value for status in SubscriptionLifecycleStatus],
    )
    update_parser.add_argument("--notes")
    update_parser.add_argument("--tag", action="append", default=None)
    state_group = update_parser.add_mutually_exclusive_group()
    state_group.add_argument("--active", dest="active", action="store_true")
    state_group.add_argument("--inactive", dest="active", action="store_false")
    update_parser.set_defaults(active=None)


def add_notion_parser(subparsers: argparse._SubParsersAction) -> None:
    notion_parser = subparsers.add_parser("notion", help="Check and bootstrap Notion schemas.")
    notion_subparsers = notion_parser.add_subparsers(dest="notion_command", required=True)

    notion_subparsers.add_parser("schemas", help="List supported Notion schemas.")

    check_parser = notion_subparsers.add_parser("check", help="Check Notion database/data source schema.")
    check_parser.add_argument("schema", nargs="?", default="all")

    bootstrap_parser = notion_subparsers.add_parser("bootstrap", help="Create or repair Notion schema.")
    bootstrap_parser.add_argument("schema", nargs="?", default="all")


def _log_learning_session(args: argparse.Namespace) -> int:
    service = LearningService()
    session = service.create_session(
        LearningSessionCreate(
            subject=args.subject,
            duration_minutes=args.minutes,
            summary=" ".join(args.summary),
            difficulty=args.difficulty,
            energy_level=args.energy_level,
            tags=args.tag,
            started_at=args.started_at,
            ended_at=args.ended_at,
        )
    )
    print(f"Logged {session.subject.value} for {session.duration_minutes} min: {session.summary}")
    return 0


async def _print_today_pulse() -> int:
    pulse = await LearningService().build_today_pulse()
    _print_pulse(pulse)
    return 0


async def _run_daily() -> int:
    service = LearningService()
    print("Daily check")
    print("===========")

    anki_stats = await service.import_anki_today()
    if not anki_stats.enabled:
        print("Anki: disabled")
    elif anki_stats.error:
        print(f"Anki: import warning ({anki_stats.error})")
    else:
        snapshot = service.get_anki_snapshot(datetime.now().date())
        print("Anki: snapshot updated")
        _print_anki_overview(
            service.build_anki_overview(
                stats=anki_stats,
                source="snapshot",
                imported_at=snapshot.imported_at if snapshot is not None else None,
            )
        )

    print("")
    print("Learning pulse")
    print("--------------")
    _print_pulse(await service.build_today_pulse())
    return 0


async def _print_anki_status() -> int:
    status = await AnkiAdapter().check_status()
    if not status.enabled:
        print("Anki status: disabled (set ANKI_ENABLED=true to enable)")
        return 0

    if not status.connected:
        print(f"Anki status: not connected ({status.error or 'unknown error'})")
        print(f"URL: {status.url}")
        return 1

    print("Anki status: connected")
    print(f"URL: {status.url}")
    print(f"API version: {status.api_version}")
    print(f"Scope: {status.scope}")
    print(f"Decks in use: {', '.join(status.decks) if status.decks else '(none)'}")
    if status.configured_decks:
        print(f"Configured decks: {', '.join(status.configured_decks)}")
    if status.missing_decks:
        print(f"Missing configured decks: {', '.join(status.missing_decks)}")
    return 0


async def _print_anki_today() -> int:
    overview = await LearningService().get_anki_today_overview()
    if not overview.enabled:
        print("Anki today: disabled (set ANKI_ENABLED=true to enable)")
        return 0

    if overview.error:
        print(f"Anki today: unavailable ({overview.error})")
        return 1

    _print_anki_overview(overview)
    return 0


async def _print_anki_reviewed_today(args: argparse.Namespace) -> int:
    overview = await LearningService().get_anki_reviewed_today_overview(target_date=args.date)
    if not overview.enabled:
        print("Anki reviewed today: disabled (set ANKI_ENABLED=true to enable)")
        return 0

    if overview.error:
        print(f"Anki reviewed today: unavailable ({overview.error})")
        return 1

    _print_reviewed_today_overview(overview)
    return 0


def _print_anki_history(args: argparse.Namespace) -> int:
    history = LearningService().get_anki_history(days=max(1, args.days))
    _print_anki_history_overview(history)
    return 0


def _print_anki_difficult_history(args: argparse.Namespace) -> int:
    trends = LearningService().get_anki_difficult_card_history(
        days=max(1, args.days),
        limit=max(1, args.limit),
    )
    print(f"Difficult cards history ({max(1, args.days)} days)")
    print("===================================")
    if not trends:
        print("No difficult cards recorded in recent snapshots.")
        return 0

    for trend in trends:
        print(f"{trend.hit_count}x | {trend.last_seen_on.isoformat()} | {trend.label}")
    return 0


async def _import_anki_today() -> int:
    service = LearningService()
    stats = await service.import_anki_today()
    if not stats.enabled:
        print("Anki import skipped: ANKI_ENABLED=false")
        return 0
    if stats.error:
        print(f"Anki import warning: {stats.error}")
        return 1
    print("Anki import: snapshot updated")
    snapshot = service.get_anki_snapshot(datetime.now().date())
    _print_anki_overview(
        service.build_anki_overview(
            stats=stats,
            source="snapshot",
            imported_at=snapshot.imported_at if snapshot is not None else None,
        )
    )
    return 0


async def _import_github_today() -> int:
    activity = await LearningService().import_github_today()
    if activity.error:
        print(f"GitHub import warning: {activity.error}")
        return 1
    print(
        f"GitHub commits: {activity.commits}, "
        f"Python commits: {activity.python_commits}, "
        f"repos: {', '.join(activity.repositories)}"
    )
    return 0


async def _sync_notion_today() -> int:
    pulse = await LearningService().build_today_pulse()
    result = await NotionSyncService().sync_learning_pulse(pulse)
    print(f"Notion sync: {result}")
    return 0 if result.get("status") in {"created", "updated", "skipped"} else 1


def _db_command(args: argparse.Namespace) -> int:
    if args.db_command == "upgrade":
        run_migrations()
        print("Database migrations applied.")
        return _db_status()
    if args.db_command == "status":
        return _db_status()
    return 1


def _db_status() -> int:
    statuses = list_migration_statuses()
    if not statuses:
        print("No migrations registered.")
        return 0

    for status in statuses:
        state = "applied" if status.applied else "pending"
        print(f"{status.revision} [{state}] {status.description}")
    pending = sum(1 for status in statuses if not status.applied)
    print(f"Pending migrations: {pending}")
    return 0


def _automation_command(args: argparse.Namespace) -> int:
    service = AutomationService()
    try:
        if args.automation_command == "list":
            return _automation_list(service)
        if args.automation_command == "register":
            return _automation_register(service, args)
        if args.automation_command == "runs":
            return _automation_runs(service, args.automation_ref, args.limit)
        if args.automation_command == "recent":
            return _automation_recent(service, args.limit)
        if args.automation_command == "scheduled-tasks":
            return _automation_scheduled_tasks()
        if args.automation_command == "run-scheduled":
            return _automation_run_scheduled(args.task_key)
        if args.automation_command == "sync-notion":
            return asyncio.run(_automation_sync_notion(service))
        if args.automation_command == "log-run":
            return _automation_log_run(service, args)
    except (AutomationConflictError, AutomationNotFoundError, ScheduledAutomationNotFoundError) as error:
        print(str(error))
        return 1
    return 1


def _automation_list(service: AutomationService) -> int:
    automations = service.list_definitions()
    if not automations:
        print("No automations registered yet.")
        return 0

    for automation in automations:
        state = "enabled" if automation.enabled else "disabled"
        last = ""
        if automation.last_run_status:
            last = f" | last: {automation.last_run_status.value}"
        print(f"{automation.key} [{automation.category.value}] {automation.name} ({state}){last}")
    return 0


def _automation_register(service: AutomationService, args: argparse.Namespace) -> int:
    automation = service.create_definition(
        AutomationDefinitionCreate(
            key=args.key,
            name=" ".join(args.name),
            category=args.category,
            external_project_path=args.project_path,
            command_hint=args.command_hint,
            schedule_hint=args.schedule_hint,
            log_path=args.log_path,
            owner=args.owner,
            enabled=not args.disabled,
            notes=args.notes,
            tags=args.tag,
        )
    )
    print(f"Registered automation {automation.key}: {automation.name}")
    return 0


def _automation_runs(service: AutomationService, automation_ref: str, limit: int) -> int:
    runs = service.list_runs(automation_ref, limit=limit)
    if not runs:
        print("No runs recorded yet.")
        return 0
    for run in runs:
        print(_format_automation_run(run))
    return 0


def _automation_recent(service: AutomationService, limit: int) -> int:
    runs = service.list_recent_runs(limit=limit)
    if not runs:
        print("No runs recorded yet.")
        return 0
    for run in runs:
        print(_format_automation_run(run))
    return 0


def _automation_scheduled_tasks() -> int:
    tasks = ScheduledAutomationService().list_specs()
    if not tasks:
        print("No built-in scheduled tasks yet.")
        return 0

    for task in tasks:
        print(f"{task.key} [{task.category.value}] {task.name} | schedule: {task.schedule_hint}")
    return 0


def _automation_run_scheduled(task_key: str) -> int:
    run = ScheduledAutomationService().run(task_key)
    print(_format_automation_run(run))
    if run.error_message:
        print(f"error: {run.error_message}")
    return 0 if run.status in {AutomationRunStatus.success, AutomationRunStatus.skipped} else 1


def _automation_log_run(service: AutomationService, args: argparse.Namespace) -> int:
    run = service.create_run(
        args.automation_ref,
        AutomationRunCreate(
            status=args.status,
            started_at=args.started_at,
            finished_at=args.finished_at,
            trigger_source=args.trigger_source,
            items_processed=args.items_processed,
            summary=" ".join(args.summary) if args.summary else None,
            error_message=args.error_message,
            external_run_id=args.external_run_id,
            log_excerpt=args.log_excerpt,
        ),
    )
    print(f"Recorded automation run {run.id}: {run.status.value}")
    return 0


async def _automation_sync_notion(service: AutomationService) -> int:
    result = await NotionSyncService().sync_automations(service.list_definitions())
    print(f"Automation Notion sync: {result}")
    return 0 if result.get("status") in {"synced", "partial", "skipped"} else 1


def _format_automation_run(run) -> str:
    summary = f" | {run.summary}" if run.summary else ""
    return (
        f"{run.started_at.isoformat()} "
        f"{run.status.value} "
        f"items={run.items_processed} "
        f"automation_id={run.automation_id}{summary}"
    )


def _subscription_command(args: argparse.Namespace) -> int:
    service = SubscriptionService()
    try:
        if args.subscription_command == "add":
            return _subscription_add(service, args)
        if args.subscription_command == "list":
            active_only = (not args.all) and args.status in {None, SubscriptionLifecycleStatus.active.value}
            return _subscription_list(service, active_only=active_only, status=args.status)
        if args.subscription_command == "overview":
            return _subscription_overview(service, args)
        if args.subscription_command == "update":
            return _subscription_update(service, args)
    except (SubscriptionConflictError, SubscriptionNotFoundError) as error:
        print(str(error))
        return 1
    return 1


def _subscription_add(service: SubscriptionService, args: argparse.Namespace) -> int:
    subscription = service.create_subscription(
        SubscriptionCreate(
            key=args.key,
            name=" ".join(args.name),
            amount=args.amount,
            currency=args.currency,
            recurrence_kind=args.recurrence,
            billing_day=args.billing_day,
            anchor_charge_date=args.anchor_charge_date,
            interval_days=args.interval_days,
            category=args.category,
            status=SubscriptionLifecycleStatus.paused.value if args.inactive else args.status,
            active=not args.inactive,
            notes=args.notes,
            tags=args.tag,
        )
    )
    print(f"Added subscription {subscription.key}: {subscription.name}")
    return 0


def _subscription_list(service: SubscriptionService, active_only: bool, status: str | None = None) -> int:
    subscriptions = service.list_subscriptions(active_only=active_only)
    if status is not None:
        subscriptions = [subscription for subscription in subscriptions if subscription.status.value == status]
    if not subscriptions:
        print("No subscriptions recorded yet." if not active_only else "No active subscriptions recorded yet.")
        return 0

    for subscription in subscriptions:
        next_charge = subscription.next_charge_date.isoformat() if subscription.next_charge_date else "n/a"
        print(
            f"{subscription.key} [{subscription.currency} {subscription.amount:.2f}] "
            f"{_format_subscription_schedule(subscription)} next={next_charge} "
            f"schedule={subscription.schedule_status.value} lifecycle={subscription.status.value} {subscription.name}"
        )
    return 0


def _subscription_overview(service: SubscriptionService, args: argparse.Namespace) -> int:
    overview = service.build_monthly_overview(target_date=args.date, days_ahead=max(1, args.days_ahead))
    print(f"Subscription overview ({overview.target_date.isoformat()} to {overview.window_end.isoformat()})")
    print(f"Active subscriptions: {overview.active_subscription_count}")
    print(f"Paused subscriptions: {overview.paused_subscription_count}")
    print(f"Cancelled subscriptions: {overview.cancelled_subscription_count}")
    print(f"Scheduled subscriptions: {overview.scheduled_subscription_count}")
    print(f"Needs schedule review: {overview.missing_schedule_count}")
    if overview.totals_by_currency:
        print("Monthly totals:")
        for currency, total in sorted(overview.totals_by_currency.items()):
            print(f"- {currency} {total:.2f}")
    else:
        print("Monthly totals: none")

    if overview.totals_by_category:
        print("Category totals:")
        for category, currency_totals in sorted(overview.totals_by_category.items()):
            summary = ", ".join(
                f"{currency} {total:.2f}" for currency, total in sorted(currency_totals.items())
            )
            print(f"- {category}: {summary}")

    if not overview.upcoming_charges:
        print("Upcoming charges: none")
    else:
        print("Upcoming charges:")
        for charge in overview.upcoming_charges:
            print(
                f"- {charge.next_charge_date.isoformat()} | {charge.currency} {charge.amount:.2f} | "
                f"{charge.name} | in {charge.days_until_charge} day(s)"
            )

    if overview.missing_schedule_subscriptions:
        print("Needs review:")
        for subscription in overview.missing_schedule_subscriptions:
            print(
                f"- {subscription.key} | {subscription.currency} {subscription.amount:.2f} | "
                f"{subscription.schedule_summary}"
            )
    return 0


def _subscription_update(service: SubscriptionService, args: argparse.Namespace) -> int:
    subscription = service.update_subscription(
        args.subscription_ref,
        SubscriptionUpdate(
            name=" ".join(args.name) if args.name else None,
            amount=args.amount,
            currency=args.currency,
            recurrence_kind=args.recurrence,
            billing_day=args.billing_day,
            anchor_charge_date=args.anchor_charge_date,
            interval_days=args.interval_days,
            category=args.category,
            status=args.status,
            active=args.active,
            notes=args.notes,
            tags=args.tag,
        ),
    )
    print(f"Updated subscription {subscription.key}: {subscription.name}")
    return 0


def _format_subscription_schedule(subscription) -> str:
    if subscription.recurrence_kind == SubscriptionRecurrenceKind.monthly:
        return f"monthly day={subscription.billing_day if subscription.billing_day is not None else '?'}"
    if subscription.recurrence_kind == SubscriptionRecurrenceKind.fixed_days:
        anchor = subscription.anchor_charge_date.isoformat() if subscription.anchor_charge_date else "?"
        interval = subscription.interval_days if subscription.interval_days is not None else "?"
        return f"every {interval} days from {anchor}"
    return "schedule=unknown"


def _work_command(args: argparse.Namespace) -> int:
    service = WorkKnowledgeService()
    try:
        if args.work_command == "capture":
            return _work_capture(service, args)
        if args.work_command == "list":
            return _work_list(service, args.limit)
        if args.work_command == "sync-notion":
            return asyncio.run(_work_sync_notion(service))
    except WorkKnowledgeNotFoundError as error:
        print(str(error))
        return 1
    return 1


def _work_capture(service: WorkKnowledgeService, args: argparse.Namespace) -> int:
    note = service.create_note(
        WorkKnowledgeNoteCreate(
            title=" ".join(args.title),
            category=args.category,
            sanitized_summary=args.summary,
            commands=args.commands,
            concepts=args.concept,
            source=args.source,
            sensitivity=args.sensitivity,
            systems=args.system,
            follow_up=args.follow_up,
            tags=args.tag,
        )
    )
    print(f"Captured work knowledge {note.id}: {note.title}")
    return 0


def _work_list(service: WorkKnowledgeService, limit: int) -> int:
    notes = service.list_notes(limit=limit)
    if not notes:
        print("No work knowledge notes captured yet.")
        return 0
    for note in notes:
        print(f"{note.created_at.isoformat()} [{note.category.value}] {note.title}")
    return 0


async def _work_sync_notion(service: WorkKnowledgeService) -> int:
    result = await NotionSyncService().sync_work_knowledge(service.list_notes(limit=500))
    print(f"Work knowledge Notion sync: {result}")
    return 0 if result.get("status") in {"synced", "partial", "skipped"} else 1


def _notion_command(args: argparse.Namespace) -> int:
    service = NotionSchemaService()
    try:
        if args.notion_command == "schemas":
            return _notion_schemas(service)
        if args.notion_command == "check":
            return asyncio.run(_notion_check(service, args.schema))
        if args.notion_command == "bootstrap":
            return asyncio.run(_notion_bootstrap(service, args.schema))
    except ValueError as error:
        print(str(error))
        return 1
    return 1


def _notion_schemas(service: NotionSchemaService) -> int:
    for schema in service.list_schemas():
        print(f"{schema['key']}: {schema['title']}")
    return 0


async def _notion_check(service: NotionSchemaService, schema: str) -> int:
    results = await service.check_all() if schema == "all" else [await service.check(schema)]
    for result in results:
        print(
            f"{result.schema_key}: {result.status} "
            f"missing={len(result.missing_properties)} "
            f"mismatch={len(result.type_mismatches)}"
            + (f" reason={result.reason}" if result.reason else "")
        )
        for item in result.missing_properties:
            print(f"  missing {item.name}: expected {item.expected_type}")
        for item in result.type_mismatches:
            print(f"  mismatch {item.name}: expected {item.expected_type}, got {item.actual_type}")
    return 0


async def _notion_bootstrap(service: NotionSchemaService, schema: str) -> int:
    results = await service.bootstrap_all() if schema == "all" else [await service.bootstrap(schema)]
    for result in results:
        print(
            f"{result.schema_key}: {result.status} "
            f"added={len(result.added_properties)}"
            + (f" reason={result.reason}" if result.reason else "")
        )
        for property_name in result.added_properties:
            print(f"  added {property_name}")
        for step in result.next_steps:
            print(f"  next: {step}")
    return 0


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except ValueError:
            continue


def _print_anki_overview(overview: AnkiTodayOverview) -> None:
    print(f"Anki today source: {overview.source}")
    print(f"Scope: {overview.scope}")
    print(f"Sync status: {overview.sync_status}")
    if overview.imported_at is not None:
        print(f"Snapshot imported at: {overview.imported_at.isoformat()}")
    print(f"Reviews: {overview.reviews}")
    print(f"Again answers: {overview.again_count}")
    print(
        "Buttons: "
        f"Again {overview.again_count}, "
        f"Hard {overview.hard_count}, "
        f"Good {overview.good_count}, "
        f"Easy {overview.easy_count}"
    )
    print(f"Non-Again rate: {overview.non_again_rate if overview.non_again_rate is not None else 'n/a'}")
    print(f"Legacy accuracy: {overview.accuracy if overview.accuracy is not None else 'n/a'}")
    print(f"Current streak: {overview.streak_days} day(s)")
    print(
        "Due workload: "
        f"{overview.due_count} total "
        f"(new {overview.new_due_count}, learn {overview.learn_due_count}, review {overview.review_due_count})"
    )
    print(f"Review load: {overview.review_load}")
    print(f"Summary: {overview.summary}")
    print(f"Recommendation: {overview.recommendation}")
    print(f"Sync hint: {overview.sync_hint}")
    print(f"Decks in use: {', '.join(overview.decks) if overview.decks else '(none)'}")
    if overview.configured_decks:
        print(f"Configured decks: {', '.join(overview.configured_decks)}")
    if overview.missing_decks:
        print(f"Missing configured decks: {', '.join(overview.missing_decks)}")
    if overview.difficult_cards:
        print("Difficult cards:")
        for card in overview.difficult_cards:
            print(f"- {card}")


def _print_anki_history_overview(history: AnkiHistoryOverview) -> None:
    print("Anki history")
    print("============")
    print(f"Current streak: {history.streak_days} day(s)")
    print(f"Total reviews: {history.total_reviews}")
    print(f"Average non-Again rate: {history.average_accuracy if history.average_accuracy is not None else 'n/a'}")
    print(f"Best review day: {history.best_review_day.isoformat() if history.best_review_day is not None else 'n/a'}")
    if not history.days:
        print("No snapshot history yet. Run import-anki after syncing desktop Anki.")
        return

    print("")
    print("Date        Reviews  Non-Again  Again  Hard  Good  Easy  Due")
    for day in history.days:
        non_again_text = f"{day.non_again_rate:.1f}%" if day.non_again_rate is not None else "n/a"
        print(
            f"{day.snapshot_date.isoformat()}  "
            f"{str(day.reviews).rjust(7)}  "
            f"{non_again_text.rjust(9)}  "
            f"{str(day.again_count).rjust(5)}  "
            f"{str(day.hard_count).rjust(4)}  "
            f"{str(day.good_count).rjust(4)}  "
            f"{str(day.easy_count).rjust(4)}  "
            f"{str(day.due_count).rjust(3)}"
        )


def _print_reviewed_today_overview(overview: AnkiReviewedTodayOverview) -> None:
    print("Anki reviewed today")
    print("===================")
    print(f"Date: {overview.target_date.isoformat()}")
    print(f"Scope: {overview.scope}")
    print(f"Total reviews: {overview.total_reviews}")
    print(f"Unique cards: {overview.total_unique_cards}")
    print(f"Decks in use: {', '.join(overview.decks) if overview.decks else '(none)'}")
    if overview.configured_decks:
        print(f"Configured decks: {', '.join(overview.configured_decks)}")
    if overview.missing_decks:
        print(f"Missing configured decks: {', '.join(overview.missing_decks)}")
    if not overview.cards:
        print("No reviewed cards found for today.")
        return

    print("")
    print("Time      Reviews  Buttons              Deck / Card")
    for card in overview.cards:
        buttons = f"A{card.again_count} H{card.hard_count} G{card.good_count} E{card.easy_count}"
        print(
            f"{card.last_reviewed_at.strftime('%H:%M:%S')}  "
            f"{str(card.review_count).rjust(7)}  "
            f"{buttons.ljust(18)}  "
            f"{card.deck_name}: {card.label}"
        )


def _print_pulse(pulse) -> None:
    print(f"Date: {pulse.date.isoformat()}")
    print(f"Python: {pulse.python_minutes} min")
    print(f"Japanese: {pulse.japanese_minutes} min")
    print(f"SRE: {pulse.sre_minutes} min")
    print(f"Anki: {pulse.anki_reviews} reviews")
    print(f"GitHub Python commits: {pulse.github_python_commits}")
    print(f"Focus score: {pulse.focus_score}")
    print(f"Tomorrow: {pulse.tomorrow_priority}")
    if pulse.integration_warnings:
        print("Warnings: " + " | ".join(pulse.integration_warnings))


if __name__ == "__main__":
    raise SystemExit(main())
