import argparse
import asyncio
from datetime import datetime, timezone
from typing import Sequence

from app.core.database import initialize_database
from app.core.logging import configure_logging
from app.models.automation import (
    AutomationCategory,
    AutomationDefinitionCreate,
    AutomationRunCreate,
    AutomationRunStatus,
    AutomationTriggerSource,
)
from app.models.learning import LearningSessionCreate, LearningSubject
from app.services.automation import AutomationConflictError, AutomationNotFoundError, AutomationService
from app.services.learning import LearningService
from app.services.notion_sync import NotionSyncService


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging()
    initialize_database()

    if args.command == "log":
        return _log_learning_session(args)
    if args.command == "pulse":
        return asyncio.run(_print_today_pulse())
    if args.command == "import-anki":
        return asyncio.run(_import_anki_today())
    if args.command == "import-github":
        return asyncio.run(_import_github_today())
    if args.command == "sync-notion":
        return asyncio.run(_sync_notion_today())
    if args.command == "automation":
        return _automation_command(args)

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
    subparsers.add_parser("import-anki", help="Import today's Anki review stats.")
    subparsers.add_parser("import-github", help="Import today's GitHub Python activity.")
    subparsers.add_parser("sync-notion", help="Sync today's learning pulse to Notion.")
    add_automation_parser(subparsers)

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
    print(f"Date: {pulse.date.isoformat()}")
    print(f"Python: {pulse.python_minutes} min")
    print(f"Japanese: {pulse.japanese_minutes} min")
    print(f"Anki: {pulse.anki_reviews} reviews")
    print(f"GitHub Python commits: {pulse.github_python_commits}")
    print(f"Focus score: {pulse.focus_score}")
    print(f"Tomorrow: {pulse.tomorrow_priority}")
    if pulse.integration_warnings:
        print("Warnings: " + " | ".join(pulse.integration_warnings))
    return 0


async def _import_anki_today() -> int:
    stats = await LearningService().import_anki_today()
    if stats.error:
        print(f"Anki import warning: {stats.error}")
        return 1
    print(f"Anki reviews: {stats.reviews}, accuracy: {stats.accuracy}")
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
        if args.automation_command == "sync-notion":
            return asyncio.run(_automation_sync_notion(service))
        if args.automation_command == "log-run":
            return _automation_log_run(service, args)
    except (AutomationConflictError, AutomationNotFoundError) as error:
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


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
