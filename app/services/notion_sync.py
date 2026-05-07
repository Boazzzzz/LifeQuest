import logging
from datetime import date
from typing import Any

import httpx

from app.core.config import settings
from app.models.learning import LearningPulse

logger = logging.getLogger(__name__)


class NotionSyncService:
    def __init__(self) -> None:
        self.enabled = settings.notion_enabled
        self.token = settings.notion_token
        self.learning_data_source_id = settings.notion_learning_pulse_data_source_id or None
        self.learning_database_id = settings.notion_learning_pulse_database_id
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

    def _learning_pulse_parent(self) -> dict[str, str] | None:
        parent_type, parent_id = self._learning_pulse_parent_ref()
        if not parent_id:
            return None
        if parent_type == "data_source":
            return {"type": "data_source_id", "data_source_id": parent_id}
        return {"database_id": parent_id}

    def _learning_pulse_parent_ref(self) -> tuple[str, str | None]:
        if self.learning_data_source_id:
            return "data_source", self.learning_data_source_id
        return "database", self.learning_database_id

    def _default_api_version(self) -> str:
        if self.learning_data_source_id:
            return "2025-09-03"
        return "2022-06-28"

    def _rich_text(self, content: str) -> dict[str, list[dict[str, dict[str, str]]]]:
        return {"rich_text": [{"text": {"content": content[:1900]}}] if content else []}
