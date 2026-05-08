import sqlite3
from datetime import datetime, timezone

from app.models.automation import (
    AutomationDefinition,
    AutomationDefinitionCreate,
    AutomationDefinitionUpdate,
    AutomationRun,
    AutomationRunCreate,
    AutomationRunStatus,
)
from app.repositories.automation import AutomationRepository


class AutomationNotFoundError(ValueError):
    pass


class AutomationConflictError(ValueError):
    pass


class AutomationService:
    def __init__(self, repository: AutomationRepository | None = None) -> None:
        self.repository = repository or AutomationRepository()

    def create_definition(self, payload: AutomationDefinitionCreate) -> AutomationDefinition:
        now = datetime.now(timezone.utc)
        definition = AutomationDefinition(
            key=payload.key,
            name=payload.name,
            category=payload.category,
            external_project_path=payload.external_project_path,
            command_hint=payload.command_hint,
            schedule_hint=payload.schedule_hint,
            log_path=payload.log_path,
            owner=payload.owner,
            enabled=payload.enabled,
            notes=payload.notes,
            tags=payload.tags,
            created_at=now,
            updated_at=now,
        )

        try:
            return self.repository.create_definition(definition)
        except sqlite3.IntegrityError as error:
            raise AutomationConflictError(f"Automation key already exists: {payload.key}") from error

    def list_definitions(self) -> list[AutomationDefinition]:
        return self.repository.list_definitions()

    def get_definition(self, key_or_id: str) -> AutomationDefinition:
        definition = self.repository.get_definition_by_key_or_id(key_or_id)
        if definition is None:
            raise AutomationNotFoundError(f"Automation not found: {key_or_id}")
        return definition

    def update_definition(self, key_or_id: str, payload: AutomationDefinitionUpdate) -> AutomationDefinition:
        current = self.get_definition(key_or_id)
        updates = payload.model_dump(exclude_unset=True)

        for field_name, value in updates.items():
            setattr(current, field_name, value)
        current.updated_at = datetime.now(timezone.utc)

        try:
            return self.repository.update_definition(current)
        except sqlite3.IntegrityError as error:
            raise AutomationConflictError(f"Automation key already exists: {current.key}") from error

    def create_run(self, key_or_id: str, payload: AutomationRunCreate) -> AutomationRun:
        definition = self.get_definition(key_or_id)
        now = datetime.now(timezone.utc)
        started_at = payload.started_at or now
        finished_at = payload.finished_at
        if finished_at is None and payload.status != AutomationRunStatus.running:
            finished_at = now

        run = AutomationRun(
            automation_id=definition.id,
            started_at=started_at,
            finished_at=finished_at,
            status=payload.status,
            trigger_source=payload.trigger_source,
            items_processed=payload.items_processed,
            summary=payload.summary,
            error_message=payload.error_message,
            external_run_id=payload.external_run_id,
            log_excerpt=payload.log_excerpt,
            created_at=now,
        )
        return self.repository.create_run(run)

    def list_runs(self, key_or_id: str, limit: int = 50) -> list[AutomationRun]:
        definition = self.get_definition(key_or_id)
        return self.repository.list_runs(definition.id, limit=limit)

    def list_recent_runs(self, limit: int = 50) -> list[AutomationRun]:
        return self.repository.list_recent_runs(limit=limit)

