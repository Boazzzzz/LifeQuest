import asyncio

from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.main import app
from app.services.notion_schema import NOTION_SCHEMAS, NotionSchemaService


def test_notion_schema_service_lists_expected_schemas():
    schemas = NotionSchemaService().list_schemas()
    keys = {schema["key"] for schema in schemas}

    assert keys == {"learning-pulse", "automations", "work-knowledge", "inbox"}


def test_notion_schema_check_skips_when_disabled(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.notion_enabled", False)

    result = asyncio.run(NotionSchemaService().check("learning-pulse"))

    assert result.status == "skipped"
    assert result.reason == "notion_disabled"


def test_notion_schema_bootstrap_reports_missing_parent(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.notion_enabled", True)
    monkeypatch.setattr("app.core.config.settings.notion_token", "secret")
    monkeypatch.setattr("app.core.config.settings.notion_parent_page_id", None)
    monkeypatch.setattr("app.core.config.settings.notion_learning_pulse_data_source_id", None)
    monkeypatch.setattr("app.core.config.settings.notion_learning_pulse_database_id", None)

    result = asyncio.run(NotionSchemaService().bootstrap("learning-pulse"))

    assert result.status == "missing_parent"
    assert result.reason == "set_NOTION_PARENT_PAGE_ID_or_target_id"


def test_notion_schema_compare_detects_missing_and_type_mismatch():
    service = NotionSchemaService()
    schema = NOTION_SCHEMAS["learning-pulse"]

    result = service._compare_properties(
        schema,
        "data_source",
        "source-id",
        {
            "Name": {"type": "title", "title": {}},
            "Date": {"type": "rich_text", "rich_text": {}},
            "Python Minutes": {"type": "number", "number": {}},
        },
    )

    assert any(item.name == "Date" for item in result.type_mismatches)
    assert any(item.name == "Japanese Minutes" for item in result.missing_properties)
    assert any(item.name == "Name" for item in result.matching_properties)


def test_notion_schema_api_lists_schemas():
    with TestClient(app) as client:
        response = client.get("/notion/schemas")

    assert response.status_code == 200
    assert {schema["key"] for schema in response.json()} == {"learning-pulse", "automations", "work-knowledge", "inbox"}


def test_notion_schema_cli_lists_schemas(capsys):
    exit_code = cli_main(["notion", "schemas"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "learning-pulse: LifeQuest - Learning Pulse" in captured.out
