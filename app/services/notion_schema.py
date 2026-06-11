from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


NEW_NOTION_VERSION = "2025-09-03"
LEGACY_NOTION_VERSION = "2022-06-28"


class NotionSchemaPropertyStatus(BaseModel):
    name: str
    expected_type: str
    actual_type: str | None = None
    status: str


class NotionSchemaCheckResult(BaseModel):
    schema_key: str
    title: str
    status: str
    target_kind: str | None = None
    target_id: str | None = None
    missing_properties: list[NotionSchemaPropertyStatus] = Field(default_factory=list)
    type_mismatches: list[NotionSchemaPropertyStatus] = Field(default_factory=list)
    matching_properties: list[NotionSchemaPropertyStatus] = Field(default_factory=list)
    reason: str | None = None


class NotionSchemaBootstrapResult(BaseModel):
    schema_key: str
    title: str
    status: str
    target_kind: str | None = None
    target_id: str | None = None
    database_id: str | None = None
    data_source_id: str | None = None
    added_properties: list[str] = Field(default_factory=list)
    type_mismatches: list[NotionSchemaPropertyStatus] = Field(default_factory=list)
    reason: str | None = None
    next_steps: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class NotionDatabaseSchema:
    key: str
    title: str
    data_source_setting: str
    database_setting: str
    properties: dict[str, dict[str, Any]]


def text_prop() -> dict[str, Any]:
    return {"rich_text": {}}


def title_prop() -> dict[str, Any]:
    return {"title": {}}


def number_prop() -> dict[str, Any]:
    return {"number": {"format": "number"}}


def checkbox_prop() -> dict[str, Any]:
    return {"checkbox": {}}


def date_prop() -> dict[str, Any]:
    return {"date": {}}


def url_prop() -> dict[str, Any]:
    return {"url": {}}


def select_prop(options: list[str]) -> dict[str, Any]:
    return {"select": {"options": [{"name": option} for option in options]}}


def multi_select_prop(options: list[str] | None = None) -> dict[str, Any]:
    return {"multi_select": {"options": [{"name": option} for option in options or []]}}


NOTION_SCHEMAS: dict[str, NotionDatabaseSchema] = {
    "learning-pulse": NotionDatabaseSchema(
        key="learning-pulse",
        title="LifeQuest - Learning Pulse",
        data_source_setting="notion_learning_pulse_data_source_id",
        database_setting="notion_learning_pulse_database_id",
        properties={
            "Name": title_prop(),
            "Date": date_prop(),
            "Python Minutes": number_prop(),
            "Japanese Minutes": number_prop(),
            "Total Minutes": number_prop(),
            "Session Count": number_prop(),
            "Anki Reviews": number_prop(),
            "Anki Accuracy": number_prop(),
            "GitHub Commits": number_prop(),
            "GitHub Python Commits": number_prop(),
            "Focus Score": number_prop(),
            "Summary": text_prop(),
            "Tomorrow Priority": text_prop(),
            "Anki Difficult Cards": text_prop(),
            "GitHub Repositories": text_prop(),
            "GitHub Python Files": text_prop(),
            "Integration Warnings": text_prop(),
            "Reflection": text_prop(),
            "Mood / Energy": select_prop(["high", "medium", "low"]),
        },
    ),
    "automations": NotionDatabaseSchema(
        key="automations",
        title="LifeQuest - Automations",
        data_source_setting="notion_automations_data_source_id",
        database_setting="notion_automations_database_id",
        properties={
            "Name": title_prop(),
            "Key": text_prop(),
            "Category": select_prop(["knowledge", "media", "game", "learning", "system", "workflow", "other"]),
            "Enabled": checkbox_prop(),
            "Tags": multi_select_prop(),
            "External Project Path": text_prop(),
            "Command Hint": text_prop(),
            "Schedule Hint": text_prop(),
            "Log Path": text_prop(),
            "Owner": text_prop(),
            "Notes": text_prop(),
            "Last Run At": date_prop(),
            "Last Run Status": select_prop(["running", "success", "failed", "partial", "skipped"]),
            "Last Run Summary": text_prop(),
            "Updated At": date_prop(),
        },
    ),
    "work-knowledge": NotionDatabaseSchema(
        key="work-knowledge",
        title="LifeQuest - Work Knowledge",
        data_source_setting="notion_work_knowledge_data_source_id",
        database_setting="notion_work_knowledge_database_id",
        properties={
            "Name": title_prop(),
            "LifeQuest ID": text_prop(),
            "Category": select_prop(
                ["linux", "networking", "docker", "nginx", "database", "security", "monitoring", "cloud", "automation", "other"]
            ),
            "Sanitized Summary": text_prop(),
            "Commands": text_prop(),
            "Concepts": multi_select_prop(),
            "Source": select_prop(["manual", "company_copilot", "ticket", "incident", "reading"]),
            "Sensitivity": select_prop(["public", "personal", "company_internal", "confidential"]),
            "Systems": multi_select_prop(),
            "Follow Up": text_prop(),
            "Tags": multi_select_prop(),
            "Created At": date_prop(),
            "Updated At": date_prop(),
        },
    ),
    "japanese-verb-forms": NotionDatabaseSchema(
        key="japanese-verb-forms",
        title="LifeQuest - Japanese Verb Forms",
        data_source_setting="notion_japanese_verb_forms_data_source_id",
        database_setting="notion_japanese_verb_forms_database_id",
        properties={
            "Name": title_prop(),
            "Dictionary Form": text_prop(),
            "Reading": text_prop(),
            "Meaning": text_prop(),
            "Verb Group": select_prop(["ichidan", "godan", "suru", "kuru", "irregular"]),
            "JLPT": select_prop(["N5", "N4", "N3", "N2", "N1", "unknown"]),
            "Confidence": number_prop(),
            "Plain Nonpast": text_prop(),
            "Polite Nonpast": text_prop(),
            "Plain Past": text_prop(),
            "Polite Past": text_prop(),
            "Plain Negative": text_prop(),
            "Polite Negative": text_prop(),
            "Plain Negative Past": text_prop(),
            "Polite Negative Past": text_prop(),
            "Notes": text_prop(),
            "Tags": multi_select_prop(),
            "Updated At": date_prop(),
        },
    ),
    "inbox": NotionDatabaseSchema(
        key="inbox",
        title="LifeQuest - Inbox",
        data_source_setting="notion_inbox_data_source_id",
        database_setting="notion_inbox_database_id",
        properties={
            "Name": title_prop(),
            "Source": select_prop(["manual", "ai", "reading", "notion"]),
            "Payload Type": select_prop(["url", "note", "file", "task", "summary"]),
            "URL": url_prop(),
            "Summary": text_prop(),
            "Status": select_prop(["queued", "processing", "done", "failed", "skipped"]),
            "Target": select_prop(["notion", "read_later", "work_knowledge", "learning"]),
            "Tags": multi_select_prop(),
            "Created At": date_prop(),
            "Processed At": date_prop(),
        },
    ),
}


class NotionSchemaService:
    def __init__(self) -> None:
        self.enabled = settings.notion_enabled
        self.token = settings.notion_token
        self.parent_page_id = settings.notion_parent_page_id
        self.timeout_seconds = settings.notion_timeout_seconds

    def list_schemas(self) -> list[dict[str, str]]:
        return [{"key": schema.key, "title": schema.title} for schema in NOTION_SCHEMAS.values()]

    async def check(self, schema_key: str) -> NotionSchemaCheckResult:
        schema = self._schema(schema_key)
        target_kind, target_id = self._target_ref(schema)
        if not self.enabled:
            return self._check_result(schema, "skipped", target_kind, target_id, reason="notion_disabled")
        if not self.token:
            return self._check_result(schema, "skipped", target_kind, target_id, reason="missing_notion_token")
        if not target_id:
            return self._check_result(schema, "missing_target", target_kind, target_id, reason="missing_target_id")

        properties = await self._retrieve_properties(target_kind, target_id)
        result = self._compare_properties(schema, target_kind, target_id, properties)
        if result.type_mismatches:
            result.status = "type_mismatch"
        elif result.missing_properties:
            result.status = "missing_properties"
        else:
            result.status = "ok"
        return result

    async def check_all(self) -> list[NotionSchemaCheckResult]:
        return [await self.check(schema_key) for schema_key in NOTION_SCHEMAS]

    async def bootstrap(self, schema_key: str) -> NotionSchemaBootstrapResult:
        schema = self._schema(schema_key)
        target_kind, target_id = self._target_ref(schema)
        if not self.enabled:
            return self._bootstrap_result(schema, "skipped", target_kind, target_id, reason="notion_disabled")
        if not self.token:
            return self._bootstrap_result(schema, "skipped", target_kind, target_id, reason="missing_notion_token")

        if target_id:
            check = await self.check(schema_key)
            if check.status == "ok":
                return self._bootstrap_result(schema, "ok", target_kind, target_id)
            if check.type_mismatches:
                return self._bootstrap_result(
                    schema,
                    "type_mismatch",
                    target_kind,
                    target_id,
                    type_mismatches=check.type_mismatches,
                    reason="fix_type_mismatches_manually",
                )
            added = await self._add_missing_properties(schema, target_kind, target_id, check.missing_properties)
            return self._bootstrap_result(schema, "updated", target_kind, target_id, added_properties=added)

        if not self.parent_page_id:
            return self._bootstrap_result(
                schema,
                "missing_parent",
                target_kind,
                target_id,
                reason="set_NOTION_PARENT_PAGE_ID_or_target_id",
            )
        return await self._create_database(schema)

    async def bootstrap_all(self) -> list[NotionSchemaBootstrapResult]:
        return [await self.bootstrap(schema_key) for schema_key in NOTION_SCHEMAS]

    async def _retrieve_properties(self, target_kind: str, target_id: str) -> dict[str, Any]:
        if target_kind == "data_source":
            endpoint = f"https://api.notion.com/v1/data_sources/{target_id}"
            headers = self._headers(NEW_NOTION_VERSION)
        else:
            endpoint = f"https://api.notion.com/v1/databases/{target_id}"
            headers = self._headers(LEGACY_NOTION_VERSION)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data.get("properties", {}) if isinstance(data, dict) else {}

    async def _add_missing_properties(
        self,
        schema: NotionDatabaseSchema,
        target_kind: str,
        target_id: str,
        missing_properties: list[NotionSchemaPropertyStatus],
    ) -> list[str]:
        if not missing_properties:
            return []

        properties = {item.name: schema.properties[item.name] for item in missing_properties}
        if target_kind == "data_source":
            endpoint = f"https://api.notion.com/v1/data_sources/{target_id}"
            headers = self._headers(NEW_NOTION_VERSION)
        else:
            endpoint = f"https://api.notion.com/v1/databases/{target_id}"
            headers = self._headers(LEGACY_NOTION_VERSION)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.patch(endpoint, headers=headers, json={"properties": properties})
            response.raise_for_status()
        return list(properties)

    async def _create_database(self, schema: NotionDatabaseSchema) -> NotionSchemaBootstrapResult:
        payload = {
            "parent": {"type": "page_id", "page_id": self.parent_page_id},
            "title": [{"text": {"content": schema.title}}],
            "initial_data_source": {"properties": schema.properties},
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.notion.com/v1/databases",
                headers=self._headers(NEW_NOTION_VERSION),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        database_id = data.get("id") if isinstance(data, dict) else None
        data_source_id = self._extract_initial_data_source_id(data)
        next_steps = [f"Set {schema.database_setting.upper()}={database_id}"] if database_id else []
        if data_source_id:
            next_steps.insert(0, f"Set {schema.data_source_setting.upper()}={data_source_id}")

        return NotionSchemaBootstrapResult(
            schema_key=schema.key,
            title=schema.title,
            status="created",
            target_kind="database",
            target_id=database_id,
            database_id=database_id,
            data_source_id=data_source_id,
            next_steps=next_steps,
        )

    def _extract_initial_data_source_id(self, data: Any) -> str | None:
        if not isinstance(data, dict):
            return None
        data_sources = data.get("data_sources")
        if isinstance(data_sources, list) and data_sources:
            first = data_sources[0]
            if isinstance(first, dict) and first.get("id"):
                return str(first["id"])
        initial_data_source = data.get("initial_data_source")
        if isinstance(initial_data_source, dict) and initial_data_source.get("id"):
            return str(initial_data_source["id"])
        return None

    def _compare_properties(
        self,
        schema: NotionDatabaseSchema,
        target_kind: str | None,
        target_id: str | None,
        actual_properties: dict[str, Any],
    ) -> NotionSchemaCheckResult:
        result = self._check_result(schema, "unknown", target_kind, target_id)
        for property_name, expected_schema in schema.properties.items():
            expected_type = self._property_type(expected_schema)
            actual_schema = actual_properties.get(property_name)
            actual_type = actual_schema.get("type") if isinstance(actual_schema, dict) else None
            status = "ok" if expected_type == actual_type else "missing" if actual_schema is None else "type_mismatch"
            item = NotionSchemaPropertyStatus(
                name=property_name,
                expected_type=expected_type,
                actual_type=actual_type,
                status=status,
            )
            if status == "ok":
                result.matching_properties.append(item)
            elif status == "missing":
                result.missing_properties.append(item)
            else:
                result.type_mismatches.append(item)
        return result

    def _target_ref(self, schema: NotionDatabaseSchema) -> tuple[str | None, str | None]:
        data_source_id = getattr(settings, schema.data_source_setting) or None
        database_id = getattr(settings, schema.database_setting) or None
        if data_source_id:
            return "data_source", data_source_id
        if database_id:
            return "database", database_id
        return None, None

    def _schema(self, schema_key: str) -> NotionDatabaseSchema:
        if schema_key not in NOTION_SCHEMAS:
            available = ", ".join(NOTION_SCHEMAS)
            raise ValueError(f"Unknown Notion schema '{schema_key}'. Available: {available}")
        return NOTION_SCHEMAS[schema_key]

    def _check_result(
        self,
        schema: NotionDatabaseSchema,
        status: str,
        target_kind: str | None,
        target_id: str | None,
        reason: str | None = None,
    ) -> NotionSchemaCheckResult:
        return NotionSchemaCheckResult(
            schema_key=schema.key,
            title=schema.title,
            status=status,
            target_kind=target_kind,
            target_id=target_id,
            reason=reason,
        )

    def _bootstrap_result(
        self,
        schema: NotionDatabaseSchema,
        status: str,
        target_kind: str | None,
        target_id: str | None,
        reason: str | None = None,
        added_properties: list[str] | None = None,
        type_mismatches: list[NotionSchemaPropertyStatus] | None = None,
    ) -> NotionSchemaBootstrapResult:
        return NotionSchemaBootstrapResult(
            schema_key=schema.key,
            title=schema.title,
            status=status,
            target_kind=target_kind,
            target_id=target_id,
            reason=reason,
            added_properties=added_properties or [],
            type_mismatches=type_mismatches or [],
        )

    def _headers(self, api_version: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": api_version,
        }

    def _property_type(self, property_schema: dict[str, Any]) -> str:
        return next(iter(property_schema))
