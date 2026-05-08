from fastapi.testclient import TestClient

from app.cli import main as cli_main
from app.core.database import initialize_database
from app.main import app
from app.models.japanese import JapaneseVerbFormCreate, JapaneseVerbGroup
from app.services.japanese import JapaneseService


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    initialize_database()


def test_japanese_service_generates_ichidan_forms(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = JapaneseService()

    verb = service.create_verb_form(
        JapaneseVerbFormCreate(
            dictionary_form="食べる",
            reading="たべる",
            meaning="eat",
            verb_group=JapaneseVerbGroup.ichidan,
        )
    )

    assert verb.plain_nonpast == "食べる"
    assert verb.polite_nonpast == "食べます"
    assert verb.plain_past == "食べた"
    assert verb.polite_past == "食べました"
    assert verb.plain_negative == "食べない"
    assert verb.polite_negative == "食べません"
    assert verb.plain_negative_past == "食べなかった"
    assert verb.polite_negative_past == "食べませんでした"


def test_japanese_service_generates_godan_forms(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = JapaneseService()

    verb = service.create_verb_form(
        JapaneseVerbFormCreate(
            dictionary_form="書く",
            reading="かく",
            meaning="write",
            verb_group=JapaneseVerbGroup.godan,
        )
    )

    assert verb.polite_nonpast == "書きます"
    assert verb.plain_past == "書いた"
    assert verb.plain_negative == "書かない"
    assert verb.polite_negative_past == "書きませんでした"


def test_japanese_api_create_and_sync_skip(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    monkeypatch.setattr("app.core.config.settings.notion_enabled", False)

    with TestClient(app) as client:
        create_response = client.post(
            "/japanese/verbs",
            json={
                "dictionary_form": "する",
                "reading": "する",
                "meaning": "do",
                "verb_group": "suru",
            },
        )
        list_response = client.get("/japanese/verbs")
        sync_response = client.post("/japanese/verbs/sync-notion")

    assert create_response.status_code == 201
    assert create_response.json()["polite_nonpast"] == "します"
    assert list_response.json()[0]["dictionary_form"] == "する"
    assert sync_response.json() == {"status": "skipped", "reason": "notion_disabled"}


def test_japanese_cli_adds_verb(tmp_path, monkeypatch, capsys):
    use_temp_database(tmp_path, monkeypatch)

    exit_code = cli_main(
        [
            "japanese",
            "verb",
            "add",
            "読む",
            "--group",
            "godan",
            "--reading",
            "よむ",
            "--meaning",
            "read",
        ]
    )
    list_code = cli_main(["japanese", "verb", "list"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert list_code == 0
    assert "Added verb 読む" in captured.out
    assert "読む [godan]" in captured.out
