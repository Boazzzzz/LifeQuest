import logging
from datetime import date
from typing import Any

import httpx

from app.core.config import settings
from app.models.automation import AutomationDefinition
from app.models.learning import LearningPulse
from app.models.work_knowledge import WorkKnowledgeNote

logger = logging.getLogger(__name__)


class NotionSyncService:
    def __init__(self) -> None:
        self.enabled = settings.notion_enabled
        self.token = settings.notion_token
        self.learning_data_source_id = settings.notion_learning_pulse_data_source_id or None
        self.learning_database_id = settings.notion_learning_pulse_database_id
        self.automations_data_source_id = settings.notion_automations_data_source_id or None
        self.automations_database_id = settings.notion_automations_database_id
        self.work_knowledge_data_source_id = settings.notion_work_knowledge_data_source_id or None
        self.work_knowledge_database_id = settings.notion_work_knowledge_database_id
        self.api_version = settings.notion_api_version or self._default_api_version()
        self.timeout_seconds = settings.notion_timeout_seconds

    async def sync_learning_pulse(self, pulse: LearningPulse) -> dict[str, str]:
        if not self.enabled:
            logger.info("Notion sync skipped because NOTION_ENABLED=false")
            return {"status": "skipped", "reason": "notion_disabled"}

        parent = self._learning_pulse_parent()
        if not self.token or parent is None:
            logger.warning("Notion sync skipped because token or learning pulse parent id is missing")
            return {"status": "skipped", "reason": "missing_notion_config"}

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.api_version,
        }

        properties = self._build_learning_pulse_properties(pulse)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            page_id = await self._find_learning_pulse_page(client, headers, pulse.date)
            if page_id:
                response = await client.patch(
                    f"https://api.notion.com/v1/pages/{page_id}",
                    headers=headers,
                    json={"properties": properties},
                )
                response.raise_for_status()
                logger.info("Updated Notion learning pulse %s for %s", page_id, pulse.date.isoformat())
                return {"status": "updated", "page_id": page_id}

            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json={"parent": parent, "properties": properties},
            )
            response.raise_for_status()
            page_id = response.json().get("id", "")

        logger.info("Created Notion learning pulse for %s", pulse.date.isoformat())
        return {"status": "created", "page_id": page_id}

    async def sync_automations(self, automations: list[AutomationDefinition]) -> dict[str, Any]:
        if not self.enabled:
            logger.info("Notion automations sync skipped because NOTION_ENABLED=false")
            return {"status": "skipped", "reason": "notion_disabled"}

        parent = self._automations_parent()
        if not self.token or parent is None:
            logger.warning("Notion automations sync skipped because token or parent id is missing")
            return {"status": "skipped", "reason": "missing_notion_config"}

        headers = self._headers()
        created = 0
        updated = 0
        errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for automation in automations:
                properties = self._build_automation_properties(automation)
                try:
                    page_id = await self._find_automation_page(client, headers, automation.key)
                    if page_id:
                        response = await client.patch(
                            f"https://api.notion.com/v1/pages/{page_id}",
                            headers=headers,
                            json={"properties": properties},
                        )
                        response.raise_for_status()
                        updated += 1
                    else:
                        response = await client.post(
                            "https://api.notion.com/v1/pages",
                            headers=headers,
                            json={"parent": parent, "properties": properties},
                        )
                        response.raise_for_status()
                        created += 1
                except httpx.HTTPError as error:
                    logger.warning("Failed to sync automation %s to Notion: %s", automation.key, error)
                    errors.append({"key": automation.key, "error": str(error)})

        return {
            "status": "synced" if not errors else "partial",
            "created": created,
            "updated": updated,
            "errors": errors,
        }

    async def sync_work_knowledge(self, notes: list[WorkKnowledgeNote]) -> dict[str, Any]:
        if not self.enabled:
            logger.info("Notion work knowledge sync skipped because NOTION_ENABLED=false")
            return {"status": "skipped", "reason": "notion_disabled"}

        parent = self._work_knowledge_parent()
        if not self.token or parent is None:
            logger.warning("Notion work knowledge sync skipped because token or parent id is missing")
            return {"status": "skipped", "reason": "missing_notion_config"}

        headers = self._headers()
        created = 0
        updated = 0
        errors: list[dict[str, str]] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for note in notes:
                properties = self._build_work_knowledge_properties(note)
                try:
                    page_id = await self._find_work_knowledge_page(client, headers, note.id)
                    if page_id:
                        response = await client.patch(
                            f"https://api.notion.com/v1/pages/{page_id}",
                            headers=headers,
                            json={"properties": properties},
                        )
                        response.raise_for_status()
                        updated += 1
                    else:
                        response = await client.post(
                            "https://api.notion.com/v1/pages",
                            headers=headers,
                            json={"parent": parent, "properties": properties},
                        )
                        response.raise_for_status()
                        created += 1
                except httpx.HTTPError as error:
                    logger.warning("Failed to sync work knowledge note %s to Notion: %s", note.id, error)
                    errors.append({"id": note.id, "error": str(error)})

        return {
            "status": "synced" if not errors else "partial",
            "created": created,
            "updated": updated,
            "errors": errors,
        }

    async def _find_learning_pulse_page(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        target_date: date,
    ) -> str | None:
        parent_type, parent_id = self._learning_pulse_parent_ref()
        if parent_type == "data_source":
            endpoint = f"https://api.notion.com/v1/data_sources/{parent_id}/query"
        else:
            endpoint = f"https://api.notion.com/v1/databases/{parent_id}/query"

        response = await client.post(
            endpoint,
            headers=headers,
            json={
                "filter": {"property": "Date", "date": {"equals": target_date.isoformat()}},
                "page_size": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", []) if isinstance(data, dict) else []
        if not results:
            return None
        page = results[0]
        return str(page.get("id")) if isinstance(page, dict) and page.get("id") else None

    def _build_learning_pulse_properties(self, pulse: LearningPulse) -> dict[str, Any]:
        return {
            "Date": {"date": {"start": pulse.date.isoformat()}},
            "Name": {"title": [{"text": {"content": f"Learning Pulse {pulse.date.isoformat()}"}}]},
            "Python Minutes": {"number": pulse.python_minutes},
            "Japanese Minutes": {"number": pulse.japanese_minutes},
            "Total Minutes": {"number": pulse.total_minutes},
            "Session Count": {"number": pulse.session_count},
            "Anki Reviews": {"number": pulse.anki_reviews},
            "Anki Accuracy": {"number": pulse.anki_accuracy},
            "GitHub Commits": {"number": pulse.github_commits},
            "GitHub Python Commits": {"number": pulse.github_python_commits},
            "Focus Score": {"number": pulse.focus_score},
            "Summary": self._rich_text(pulse.summary),
            "Tomorrow Priority": self._rich_text(pulse.tomorrow_priority),
            "Anki Difficult Cards": self._rich_text("\n".join(pulse.anki_difficult_cards)),
            "GitHub Repositories": self._rich_text(", ".join(pulse.github_repositories)),
            "GitHub Python Files": self._rich_text("\n".join(pulse.github_python_files[:30])),
            "Integration Warnings": self._rich_text("\n".join(pulse.integration_warnings)),
        }

    async def _find_automation_page(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        key: str,
    ) -> str | None:
        parent_type, parent_id = self._automations_parent_ref()
        if parent_type == "data_source":
            endpoint = f"https://api.notion.com/v1/data_sources/{parent_id}/query"
        else:
            endpoint = f"https://api.notion.com/v1/databases/{parent_id}/query"

        response = await client.post(
            endpoint,
            headers=headers,
            json={
                "filter": {"property": "Key", "rich_text": {"equals": key}},
                "page_size": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", []) if isinstance(data, dict) else []
        if not results:
            return None
        page = results[0]
        return str(page.get("id")) if isinstance(page, dict) and page.get("id") else None

    def _build_automation_properties(self, automation: AutomationDefinition) -> dict[str, Any]:
        return {
            "Name": {"title": [{"text": {"content": automation.name}}]},
            "Key": self._rich_text(automation.key),
            "Category": self._select(automation.category.value),
            "Enabled": {"checkbox": automation.enabled},
            "Tags": self._multi_select(automation.tags),
            "External Project Path": self._rich_text(automation.external_project_path or ""),
            "Command Hint": self._rich_text(automation.command_hint or ""),
            "Schedule Hint": self._rich_text(automation.schedule_hint or ""),
            "Log Path": self._rich_text(automation.log_path or ""),
            "Owner": self._rich_text(automation.owner or ""),
            "Notes": self._rich_text(automation.notes or ""),
            "Last Run At": self._date(automation.last_run_at),
            "Last Run Status": self._select(automation.last_run_status.value if automation.last_run_status else None),
            "Last Run Summary": self._rich_text(automation.last_run_summary or ""),
            "Updated At": self._date(automation.updated_at),
        }

    async def _find_work_knowledge_page(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        note_id: str,
    ) -> str | None:
        parent_type, parent_id = self._work_knowledge_parent_ref()
        if parent_type == "data_source":
            endpoint = f"https://api.notion.com/v1/data_sources/{parent_id}/query"
        else:
            endpoint = f"https://api.notion.com/v1/databases/{parent_id}/query"

        response = await client.post(
            endpoint,
            headers=headers,
            json={
                "filter": {"property": "LifeQuest ID", "rich_text": {"equals": note_id}},
                "page_size": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", []) if isinstance(data, dict) else []
        if not results:
            return None
        page = results[0]
        return str(page.get("id")) if isinstance(page, dict) and page.get("id") else None

    def _build_work_knowledge_properties(self, note: WorkKnowledgeNote) -> dict[str, Any]:
        return {
            "Name": {"title": [{"text": {"content": note.title}}]},
            "LifeQuest ID": self._rich_text(note.id),
            "Category": self._select(note.category.value),
            "Sanitized Summary": self._rich_text(note.sanitized_summary),
            "Commands": self._rich_text("\n".join(note.commands)),
            "Concepts": self._multi_select(note.concepts),
            "Source": self._select(note.source.value),
            "Sensitivity": self._select(note.sensitivity.value),
            "Systems": self._multi_select(note.systems),
            "Follow Up": self._rich_text(note.follow_up or ""),
            "Tags": self._multi_select(note.tags),
            "Created At": self._date(note.created_at),
            "Updated At": self._date(note.updated_at),
        }

    def _learning_pulse_parent(self) -> dict[str, str] | None:
        parent_type, parent_id = self._learning_pulse_parent_ref()
        if not parent_id:
            return None
        if parent_type == "data_source":
            return {"type": "data_source_id", "data_source_id": parent_id}
        return {"database_id": parent_id}

    def _automations_parent(self) -> dict[str, str] | None:
        parent_type, parent_id = self._automations_parent_ref()
        if not parent_id:
            return None
        if parent_type == "data_source":
            return {"type": "data_source_id", "data_source_id": parent_id}
        return {"database_id": parent_id}

    def _work_knowledge_parent(self) -> dict[str, str] | None:
        parent_type, parent_id = self._work_knowledge_parent_ref()
        if not parent_id:
            return None
        if parent_type == "data_source":
            return {"type": "data_source_id", "data_source_id": parent_id}
        return {"database_id": parent_id}

    def _learning_pulse_parent_ref(self) -> tuple[str, str | None]:
        if self.learning_data_source_id:
            return "data_source", self.learning_data_source_id
        return "database", self.learning_database_id

    def _automations_parent_ref(self) -> tuple[str, str | None]:
        if self.automations_data_source_id:
            return "data_source", self.automations_data_source_id
        return "database", self.automations_database_id

    def _work_knowledge_parent_ref(self) -> tuple[str, str | None]:
        if self.work_knowledge_data_source_id:
            return "data_source", self.work_knowledge_data_source_id
        return "database", self.work_knowledge_database_id

    def _default_api_version(self) -> str:
        if self.learning_data_source_id or self.automations_data_source_id or self.work_knowledge_data_source_id:
            return "2025-09-03"
        return "2022-06-28"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": self.api_version,
        }

    def _rich_text(self, content: str) -> dict[str, list[dict[str, dict[str, str]]]]:
        return {"rich_text": [{"text": {"content": content[:1900]}}] if content else []}

    def _select(self, value: str | None) -> dict[str, dict[str, str] | None]:
        return {"select": {"name": value} if value else None}

    def _multi_select(self, values: list[str]) -> dict[str, list[dict[str, str]]]:
        return {"multi_select": [{"name": value} for value in values]}

    def _date(self, value) -> dict[str, dict[str, str] | None]:
        return {"date": {"start": value.isoformat()} if value else None}
