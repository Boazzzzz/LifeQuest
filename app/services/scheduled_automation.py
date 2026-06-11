import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.models.automation import (
    AutomationCategory,
    AutomationDefinition,
    AutomationDefinitionCreate,
    AutomationRun,
    AutomationRunCreate,
    AutomationRunStatus,
    AutomationTriggerSource,
)
from app.core.config import settings
from app.services.automation import AutomationNotFoundError, AutomationService
from app.services.learning import LearningService


class ScheduledAutomationNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class ScheduledAutomationSpec:
    key: str
    name: str
    category: AutomationCategory
    command_hint: str
    schedule_hint: str
    notes: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ScheduledAutomationOutcome:
    status: AutomationRunStatus
    items_processed: int
    summary: str
    error_message: str | None = None


class ScheduledAutomationService:
    def __init__(
        self,
        automation_service: AutomationService | None = None,
        learning_service: LearningService | None = None,
    ) -> None:
        self.automation_service = automation_service or AutomationService()
        self.learning_service = learning_service or LearningService()

    def list_specs(self) -> list[ScheduledAutomationSpec]:
        return list(_SCHEDULED_AUTOMATIONS.values())

    def run(self, task_key: str) -> AutomationRun:
        spec = _SCHEDULED_AUTOMATIONS.get(task_key)
        if spec is None:
            raise ScheduledAutomationNotFoundError(f"Scheduled automation not found: {task_key}")

        definition = self._ensure_definition(spec)
        outcome = asyncio.run(self._run_task(task_key))
        return self.automation_service.create_run(
            definition.key,
            AutomationRunCreate(
                status=outcome.status,
                trigger_source=AutomationTriggerSource.scheduled,
                items_processed=outcome.items_processed,
                summary=outcome.summary,
                error_message=outcome.error_message,
            ),
        )

    def _ensure_definition(self, spec: ScheduledAutomationSpec) -> AutomationDefinition:
        try:
            return self.automation_service.get_definition(spec.key)
        except AutomationNotFoundError:
            return self.automation_service.create_definition(
                AutomationDefinitionCreate(
                    key=spec.key,
                    name=spec.name,
                    category=spec.category,
                    command_hint=spec.command_hint,
                    schedule_hint=spec.schedule_hint,
                    notes=spec.notes,
                    tags=list(spec.tags),
                )
            )

    async def _run_task(self, task_key: str) -> ScheduledAutomationOutcome:
        if task_key == "open-anki":
            return self._run_open_anki()
        if task_key == "anki-daily":
            return await self._run_anki_daily()
        if task_key == "close-anki":
            return await self._run_close_anki()
        raise ScheduledAutomationNotFoundError(f"Scheduled automation not found: {task_key}")

    def _run_open_anki(self) -> ScheduledAutomationOutcome:
        if settings.anki_desktop_path is None:
            return ScheduledAutomationOutcome(
                status=AutomationRunStatus.failed,
                items_processed=0,
                summary="Failed to launch desktop Anki.",
                error_message="ANKI_DESKTOP_PATH is not configured.",
            )

        desktop_path = Path(settings.anki_desktop_path)
        if not desktop_path.exists():
            return ScheduledAutomationOutcome(
                status=AutomationRunStatus.failed,
                items_processed=0,
                summary="Failed to launch desktop Anki.",
                error_message=f"Anki executable not found: {desktop_path}",
            )

        try:
            subprocess.Popen(
                [str(desktop_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError as error:
            return ScheduledAutomationOutcome(
                status=AutomationRunStatus.failed,
                items_processed=0,
                summary="Failed to launch desktop Anki.",
                error_message=str(error),
            )

        return ScheduledAutomationOutcome(
            status=AutomationRunStatus.success,
            items_processed=1,
            summary=f"Launched desktop Anki from {desktop_path}.",
        )

    async def _run_anki_daily(self) -> ScheduledAutomationOutcome:
        stats = await self.learning_service.import_anki_today()
        if not stats.enabled:
            return ScheduledAutomationOutcome(
                status=AutomationRunStatus.skipped,
                items_processed=0,
                summary="Skipped Anki daily import because ANKI_ENABLED=false.",
            )
        if stats.error:
            return ScheduledAutomationOutcome(
                status=AutomationRunStatus.failed,
                items_processed=0,
                summary="Anki daily import failed.",
                error_message=stats.error,
            )
        close_error = await self._close_anki_after_daily_import()
        summary = f"Imported {stats.reviews} Anki reviews across {len(stats.decks)} deck(s)."
        status = AutomationRunStatus.success
        if close_error is None and settings.anki_close_after_daily_import:
            summary = f"{summary} Closed desktop Anki."
        elif close_error:
            summary = f"{summary} Desktop Anki close failed."
            status = AutomationRunStatus.partial
        return ScheduledAutomationOutcome(
            status=status,
            items_processed=stats.reviews,
            summary=summary,
            error_message=close_error,
        )

    async def _run_close_anki(self) -> ScheduledAutomationOutcome:
        close_error = await self._close_anki_desktop()
        if close_error:
            return ScheduledAutomationOutcome(
                status=AutomationRunStatus.failed,
                items_processed=0,
                summary="Failed to close desktop Anki.",
                error_message=close_error,
            )

        return ScheduledAutomationOutcome(
            status=AutomationRunStatus.success,
            items_processed=1,
            summary="Closed desktop Anki.",
        )

    async def _close_anki_after_daily_import(self) -> str | None:
        if not settings.anki_close_after_daily_import:
            return None

        return await self._close_anki_desktop()

    async def _close_anki_desktop(self) -> str | None:
        anki_adapter = getattr(self.learning_service, "anki_adapter", None)
        close_desktop = getattr(anki_adapter, "close_desktop", None)
        if close_desktop is None:
            return "Learning service does not expose an Anki desktop close operation."

        try:
            await close_desktop()
        except Exception as error:
            return str(error)
        return None


_SCHEDULED_AUTOMATIONS: dict[str, ScheduledAutomationSpec] = {
    "open-anki": ScheduledAutomationSpec(
        key="open-anki",
        name="Open Desktop Anki",
        category=AutomationCategory.learning,
        command_hint=".venv\\Scripts\\python.exe -m app.cli automation run-scheduled open-anki",
        schedule_hint="daily",
        notes="Starts desktop Anki so its built-in sync and AnkiConnect can become available before later imports.",
        tags=("anki", "japanese", "scheduled"),
    ),
    "close-anki": ScheduledAutomationSpec(
        key="close-anki",
        name="Close Desktop Anki",
        category=AutomationCategory.learning,
        command_hint=".venv\\Scripts\\python.exe -m app.cli automation run-scheduled close-anki",
        schedule_hint="daily",
        notes="Closes desktop Anki through AnkiConnect. Schedule it after anki-daily as a fallback.",
        tags=("anki", "japanese", "scheduled"),
    ),
    "anki-daily": ScheduledAutomationSpec(
        key="anki-daily",
        name="Anki Daily Import",
        category=AutomationCategory.learning,
        command_hint=".venv\\Scripts\\python.exe -m app.cli automation run-scheduled anki-daily",
        schedule_hint="daily",
        notes="Runs the daily Anki import through LifeQuest, then closes desktop Anki when ANKI_CLOSE_AFTER_DAILY_IMPORT=true.",
        tags=("anki", "japanese", "scheduled"),
    ),
}
