import argparse
import asyncio
from datetime import datetime, timezone
from typing import Sequence

from app.core.database import initialize_database
from app.core.logging import configure_logging
from app.models.learning import LearningSessionCreate, LearningSubject
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

    return parser


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


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
