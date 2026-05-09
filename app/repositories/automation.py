import json
from datetime import datetime

from app.core.database import execute, fetch_all, fetch_one, is_mssql_backend, select_limit_clause
from app.models.automation import AutomationDefinition, AutomationRun


class AutomationRepository:
    def create_definition(self, definition: AutomationDefinition) -> AutomationDefinition:
        execute(
            """
            INSERT INTO automation_definitions (
                id, key, name, category, external_project_path, command_hint,
                schedule_hint, log_path, owner, enabled, notes, tags,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._definition_values(definition),
        )
        return definition

    def update_definition(self, definition: AutomationDefinition) -> AutomationDefinition:
        execute(
            """
            UPDATE automation_definitions
            SET key = ?, name = ?, category = ?, external_project_path = ?,
                command_hint = ?, schedule_hint = ?, log_path = ?, owner = ?,
                enabled = ?, notes = ?, tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                definition.key,
                definition.name,
                definition.category.value,
                definition.external_project_path,
                definition.command_hint,
                definition.schedule_hint,
                definition.log_path,
                definition.owner,
                1 if definition.enabled else 0,
                definition.notes,
                json.dumps(definition.tags, ensure_ascii=False),
                definition.updated_at.isoformat(),
                definition.id,
            ),
        )
        return definition

    def list_definitions(self) -> list[AutomationDefinition]:
        rows = fetch_all(
            f"""
            SELECT
                d.*,
                r.started_at AS last_run_at,
                r.status AS last_run_status,
                r.summary AS last_run_summary
            FROM automation_definitions d
            LEFT JOIN automation_runs r
                ON r.id = (
                    {self._latest_run_id_subquery()}
                )
            ORDER BY d.enabled DESC, d.category ASC, d.name ASC
            """
        )
        return [self._row_to_definition(row) for row in rows]

    def get_definition(self, automation_id: str) -> AutomationDefinition | None:
        return self._get_definition("d.id = ?", automation_id)

    def get_definition_by_key(self, key: str) -> AutomationDefinition | None:
        return self._get_definition("d.key = ?", key)

    def get_definition_by_key_or_id(self, key_or_id: str) -> AutomationDefinition | None:
        return self.get_definition_by_key(key_or_id) or self.get_definition(key_or_id)

    def create_run(self, run: AutomationRun) -> AutomationRun:
        execute(
            """
            INSERT INTO automation_runs (
                id, automation_id, started_at, finished_at, status,
                trigger_source, items_processed, summary, error_message,
                external_run_id, log_excerpt, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.automation_id,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.status.value,
                run.trigger_source.value,
                run.items_processed,
                run.summary,
                run.error_message,
                run.external_run_id,
                run.log_excerpt,
                run.created_at.isoformat(),
            ),
        )
        return run

    def list_runs(self, automation_id: str, limit: int = 50) -> list[AutomationRun]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM automation_runs
            WHERE automation_id = ?
            ORDER BY started_at DESC
        """
        rows = fetch_all(query, (automation_id,)) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (automation_id, limit))
        return [self._row_to_run(row) for row in rows]

    def list_recent_runs(self, limit: int = 50) -> list[AutomationRun]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM automation_runs
            ORDER BY started_at DESC
        """
        rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (limit,))
        return [self._row_to_run(row) for row in rows]

    def _get_definition(self, predicate: str, value: str) -> AutomationDefinition | None:
        row = fetch_one(
            f"""
            SELECT
                d.*,
                r.started_at AS last_run_at,
                r.status AS last_run_status,
                r.summary AS last_run_summary
            FROM automation_definitions d
            LEFT JOIN automation_runs r
                ON r.id = (
                    {self._latest_run_id_subquery()}
                )
            WHERE {predicate}
            """,
            (value,),
        )
        return self._row_to_definition(row) if row else None

    def _latest_run_id_subquery(self) -> str:
        if is_mssql_backend():
            return """
                SELECT TOP 1 id FROM automation_runs
                WHERE automation_id = d.id
                ORDER BY started_at DESC
            """
        return """
            SELECT id FROM automation_runs
            WHERE automation_id = d.id
            ORDER BY started_at DESC
            LIMIT 1
        """

    def _definition_values(self, definition: AutomationDefinition) -> tuple:
        return (
            definition.id,
            definition.key,
            definition.name,
            definition.category.value,
            definition.external_project_path,
            definition.command_hint,
            definition.schedule_hint,
            definition.log_path,
            definition.owner,
            1 if definition.enabled else 0,
            definition.notes,
            json.dumps(definition.tags, ensure_ascii=False),
            definition.created_at.isoformat(),
            definition.updated_at.isoformat(),
        )

    def _row_to_definition(self, row) -> AutomationDefinition:
        return AutomationDefinition(
            id=row["id"],
            key=row["key"],
            name=row["name"],
            category=row["category"],
            external_project_path=row["external_project_path"],
            command_hint=row["command_hint"],
            schedule_hint=row["schedule_hint"],
            log_path=row["log_path"],
            owner=row["owner"],
            enabled=bool(row["enabled"]),
            notes=row["notes"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            last_run_status=row["last_run_status"],
            last_run_summary=row["last_run_summary"],
        )

    def _row_to_run(self, row) -> AutomationRun:
        return AutomationRun(
            id=row["id"],
            automation_id=row["automation_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=row["status"],
            trigger_source=row["trigger_source"],
            items_processed=row["items_processed"],
            summary=row["summary"],
            error_message=row["error_message"],
            external_run_id=row["external_run_id"],
            log_excerpt=row["log_excerpt"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
