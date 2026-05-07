import logging

import httpx

from app.core.config import settings
from app.models.learning import LearningPulse

logger = logging.getLogger(__name__)


class NotionSyncService:
    def __init__(self) -> None:
        self.enabled = settings.notion_enabled
        self.token = settings.notion_token
        self.learning_database_id = settings.notion_learning_pulse_database_id

    async def sync_learning_pulse(self, pulse: LearningPulse) -> dict[str, str]:
        if not self.enabled:
            logger.info("Notion sync skipped because NOTION_ENABLED=false")
            return {"status": "skipped", "reason": "notion_disabled"}

        if not self.token or not self.learning_database_id:
            logger.warning("Notion sync skipped because token or database id is missing")
            return {"status": "skipped", "reason": "missing_notion_config"}

        payload = self._build_learning_pulse_payload(pulse)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
            response.raise_for_status()

        logger.info("Synced learning pulse to Notion for %s", pulse.date.isoformat())
        return {"status": "synced"}

    def _build_learning_pulse_payload(self, pulse: LearningPulse) -> dict:
        return {
            "parent": {"database_id": self.learning_database_id},
            "properties": {
                "Date": {"date": {"start": pulse.date.isoformat()}},
                "Name": {"title": [{"text": {"content": f"Learning Pulse {pulse.date.isoformat()}"}}]},
                "Python Minutes": {"number": pulse.python_minutes},
                "Japanese Minutes": {"number": pulse.japanese_minutes},
                "Total Minutes": {"number": pulse.total_minutes},
                "Focus Score": {"number": pulse.focus_score},
                "Summary": {"rich_text": [{"text": {"content": pulse.summary}}]},
                "Tomorrow Priority": {"rich_text": [{"text": {"content": pulse.tomorrow_priority}}]},
            },
        }

