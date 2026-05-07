# LifeQuest

LifeQuest is a personal automation command center. It is designed to connect learning, knowledge capture, media organization, existing scripts, and Notion dashboards through one backend.

The first working slice is **Learning Core** for Python and Japanese, because those are the highest-priority life goals right now.

## Product Goal

LifeQuest should reduce administrative overhead and protect focus time. It should become the backend for daily learning, personal automation, future dashboards, and possible game-like frontend experiences.

Core principles:

- SQLite is the local source of truth for MVP metadata and learning history.
- Notion is a dashboard, not the canonical database.
- External integrations must be optional and mock-friendly.
- Existing automation projects should be integrated through adapters before being rewritten.
- Risky automations, especially file moves and media cleanup, should start in dry-run mode.

## Current Status

Implemented:

- Manual learning session logging for Python and Japanese.
- Daily `LearningPulse` generation.
- AnkiConnect status, daily review import, accuracy estimate, and difficult-card capture.
- GitHub status, recent push activity import, and Python commit detection.
- Notion Learning Pulse sync with upsert by date.
- CLI quick capture through `lifequest`.
- FastAPI routes for local API testing.

Not implemented yet:

- Automation registry and run ledger for existing scripts.
- Raindrop, Telegram queue, Stash, and mobile game script adapters.
- Knowledge inbox.
- ACG media library scanner.
- Frontend or game layer.

## Architecture

```text
LifeQuest
  API Layer
    FastAPI routes for capture, dashboard reads, imports, and sync triggers.

  Domain Models
    Pydantic schemas that normalize data before SQLite storage or Notion sync.

  Repository Layer
    SQLite persistence for learning sessions and activity events.

  Service Layer
    Business workflows such as pulse generation, import jobs, Notion sync, and future automation ledgers.

  Integration Adapters
    Thin wrappers around AnkiConnect, GitHub, Notion, Raindrop, Telegram, Stash, and existing scripts.

  Future UI Layer
    A custom frontend or game-like interface can call the FastAPI backend.
```

### Current Data Flow

```text
Manual CLI/API logging
        |
        v
LearningSession -> SQLite
        |
        v
LearningService builds LearningPulse
        |
        +-- AnkiAdapter reads AnkiConnect stats
        +-- GitHubAdapter reads recent GitHub activity
        |
        v
NotionSyncService upserts one Notion row per date
```

### Important Modules

```text
app/main.py
  FastAPI app entry point.

app/cli.py
  Command line interface for low-friction learning logs and imports.

app/core/
  Settings, database setup, and logging.

app/models/
  Pydantic domain models.

app/repositories/
  SQLite read/write layer.

app/services/
  Learning workflows and Notion sync.

app/integrations/
  External API adapters.

app/api/routes/
  FastAPI route definitions.

docs/architecture.md
  Longer architecture notes.
```

## Roadmap

### Phase 1: Learning Core

Status: mostly implemented.

- Manual learning sessions.
- Daily pulse for Python and Japanese.
- AnkiConnect integration.
- GitHub Python activity tracking.
- Notion Learning Pulse upsert.
- CLI quick capture.

### Phase 2: Automation Observability

- `AutomationDefinition` registry.
- `AutomationRun` ledger.
- Adapters for existing Raindrop classifier, Telegram downloader, Stash sync, and mobile game script projects.
- Manual trigger endpoints.
- Last-run status and error summaries.

### Phase 3: Knowledge Inbox

- Unified `InboxItem` model for URLs, notes, AI summaries, and reading items.
- Raindrop import and dead-link checks.
- Notion knowledge sync.
- Tagging and review status.

### Phase 4: ACG Media Library

- Scan only whitelisted ACG folders, not the full 3.2 TB cloud drive.
- Create dry-run duplicate and organization suggestions.
- Track work-level metadata with `MediaWorkNode`.
- Avoid automatic file moves until the suggestion system is trusted.

### Phase 5: Frontend / Game Layer

- Use LifeQuest API as the backend.
- Add quests, streaks, focus score, experience, and daily review loops.
- Keep game logic separate from core data ingestion.

## Setup On A New Machine

Clone the repo, then:

```bash
cp .env.example .env
python3 -m pip install -e '.[dev]'
python3 -m pytest
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

The app uses `data/lifequest.db` by default. The database is ignored by git. Each machine can have its own local SQLite file unless you intentionally sync or migrate it.

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

## Environment Variables

Copy `.env.example` to `.env` and fill only the integrations you want to test.

```env
APP_NAME=LifeQuest
ENVIRONMENT=development
DATABASE_PATH=data/lifequest.db
LOG_LEVEL=INFO

ANKI_ENABLED=false
ANKI_CONNECT_URL=http://127.0.0.1:8765
ANKI_API_VERSION=6
ANKI_TIMEOUT_SECONDS=5
ANKI_DECKS=

GITHUB_ENABLED=false
GITHUB_TOKEN=
GITHUB_USERNAME=
GITHUB_API_VERSION=2022-11-28
GITHUB_TIMEOUT_SECONDS=10

NOTION_ENABLED=false
NOTION_TOKEN=
NOTION_LEARNING_PULSE_DATA_SOURCE_ID=
NOTION_LEARNING_PULSE_DATABASE_ID=
NOTION_API_VERSION=
NOTION_TIMEOUT_SECONDS=20
```

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

If you mainly use Anki on mobile, sync mobile Anki to AnkiWeb, open desktop Anki on the Mac, sync desktop Anki, then run LifeQuest. AnkiConnect only runs inside desktop Anki.

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

## Development Handoff Notes

- Keep adapters thin. Business logic belongs in services, not integration clients.
- Do not make external APIs required for local development.
- Prefer adding tests with fake adapters instead of requiring real tokens.
- Do not commit `.env`, SQLite DB files, caches, or generated package metadata.
- Commit after each coherent feature so other machines and AI tools can resume safely.
- When adding file/media automation, start with scan and dry-run suggestions before any move/delete behavior.
