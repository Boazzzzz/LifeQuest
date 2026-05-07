# LifeQuest

LifeQuest is a personal automation command center. The long-term goal is to connect learning, knowledge capture, media organization, existing scripts, and Notion dashboards through one backend.

The first working slice is **Learning Core MVP** for Python and Japanese.

## Current Scope

- Record manual learning sessions.
- Generate today's learning pulse.
- Keep external integrations mock-friendly and optional.
- Prepare adapters for Anki, GitHub, and Notion without making them required.

## Run

```bash
cp .env.example .env
uvicorn app.main:app --reload
```

## Core Endpoints

- `GET /health`
- `POST /learning/sessions`
- `GET /learning/sessions`
- `GET /learning/pulse/today`
- `GET /integrations/anki/status`
- `GET /integrations/github/status`
- `POST /learning/import/anki/today`
- `POST /learning/import/github/today`
- `POST /learning/pulse/today/sync-notion`

## CLI

After installing the project in editable mode, you can log learning directly:

```bash
lifequest log python 45 "FastAPI dependency injection" --tag fastapi
lifequest log japanese 30 "N3 grammar review" --difficulty 3
lifequest pulse
lifequest import-anki
lifequest import-github
lifequest sync-notion
```

The module form also works:

```bash
python3 -m app.cli log python 25 "Small automation practice"
```

## AnkiConnect

To enable Anki stats:

1. Install the AnkiConnect add-on in Anki.
2. Keep Anki running.
3. Set `ANKI_ENABLED=true` in `.env`.
4. Optionally set `ANKI_DECKS=Deck One,Deck Two` to limit review analysis.

LifeQuest reads review counts from AnkiConnect and, when deck review rows are available, estimates accuracy and lists cards answered with Again.

## GitHub

To enable GitHub Python tracking:

1. Set `GITHUB_ENABLED=true`.
2. Set `GITHUB_USERNAME`.
3. Optionally set `GITHUB_TOKEN` for better rate limits and private access where GitHub allows it.

LifeQuest reads recent GitHub push events, inspects commit details, and counts commits that changed `.py` files as Python learning activity.

## Notion Learning Pulse

LifeQuest syncs one Notion row per date. It queries by the `Date` property first, then updates the existing page or creates a new one.

Current Notion API setups can use `NOTION_LEARNING_PULSE_DATA_SOURCE_ID`. Older database-based setups can use `NOTION_LEARNING_PULSE_DATABASE_ID`.

Recommended properties:

```text
Name: title
Date: date
Python Minutes: number
Japanese Minutes: number
Total Minutes: number
Session Count: number
Anki Reviews: number
Anki Accuracy: number
GitHub Commits: number
GitHub Python Commits: number
Focus Score: number
Summary: text
Tomorrow Priority: text
Anki Difficult Cards: text
GitHub Repositories: text
GitHub Python Files: text
Integration Warnings: text
```

## Philosophy

Notion is a dashboard, not the source of truth. LifeQuest keeps the canonical activity and learning data locally first, then syncs useful summaries outward.
