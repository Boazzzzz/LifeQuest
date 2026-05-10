# LifeQuest

LifeQuest is a personal life operating system backend with a growing frontend. It is designed to connect learning, life admin, knowledge capture, existing automations, and future dashboards through one coherent local platform.

The first working slice was **Learning Core** for Python and Japanese, because those were the highest-priority life goals at the start. The more durable direction is broader: LifeQuest should become a daily control center for both learning and life management.

## Product Goal

LifeQuest should reduce administrative overhead and protect focus time. It should become the backend for daily learning, personal automation, future dashboards, and possible game-like frontend experiences.

Core principles:

- Do not reinvent the wheel. LifeQuest should orchestrate mature tools instead of replacing them.
- A local relational database is the source of truth for LifeQuest-owned metadata and learning history.
- Notion is the workspace for human-maintained content and the dashboard for generated summaries, not the canonical database.
- External integrations must be optional and mock-friendly.
- Existing automation projects should be integrated through adapters before being rewritten.
- Risky automations, especially file moves and media cleanup, should start in dry-run mode.

## Product Shape

The most reasonable long-term shape for LifeQuest is:

- One backend that stores and normalizes your personal operational data.
- One frontend that you can actually open every day without feeling buried.
- Several focused modules instead of one giant everything-app.

The core product should stay centered on five areas:

- `Learning`: sessions, Anki, GitHub activity, progress summaries, and review loops.
- `Life Admin`: subscriptions, recurring costs, small personal admin signals, and later reminders.
- `Knowledge`: work notes, personal references, and a future inbox/review flow.
- `Automation`: existing scripts, run history, integrations, and operational visibility.
- `Dashboard / Review`: a calm daily homepage plus a future weekly review surface.

This boundary matters. LifeQuest should be your integration and decision layer, not a full replacement for every specialized tool you already use.

## Frontend Direction

The frontend should eventually feel like a personal control center, not a generic CRUD panel.

It should prioritize:

- A homepage that explains today in one screen.
- Clear module entry points for learning, life admin, knowledge, and automation.
- A weekly review page that turns raw records into decisions.
- Enough visual personality that opening it feels motivating, not bureaucratic.

Current UI status:

- `GET /` and `GET /dashboard` serve a frontend prototype homepage.
- `GET /life-admin/subscriptions` serves a live subscription management page for review, create, edit, and lifecycle changes.
- `GET /japanese` serves a narrower Japanese-focused dashboard.
- The homepage is intentionally a direction-setting prototype: some sections use fallback content until every backend slice is wired to live data.

## Tool Responsibility Boundaries

LifeQuest should not become a duplicate Notion, Anki, GitHub, Raindrop, or script runner. The project should only build custom functionality when existing tools do not already solve the problem well.

Examples:

- Daily life journaling belongs in Notion unless LifeQuest needs structured metadata for automation.
- Spaced repetition belongs in Anki; LifeQuest should only read learning stats and summarize progress.
- Code history belongs in GitHub; LifeQuest should only derive learning signals from commits.
- Bookmark collection belongs in Raindrop; LifeQuest should only observe, classify, sync, or summarize where useful.
- Existing automation scripts should remain external until there is a clear reason to wrap them with an adapter.

Build inside LifeQuest only when the feature is orchestration, normalization, observability, cross-tool insight, or future game/frontend API support.

## Current Status

Implemented:

- Manual learning session logging for Python and Japanese.
- Daily `LearningPulse` generation.
- AnkiConnect status, configured-deck checks, daily snapshot import, accuracy estimate, and difficult-card capture.
- Anki history, difficult-card trends, due workload, and new/learn/review split for configured deck scopes.
- GitHub status, recent push activity import, and Python commit detection.
- Notion Learning Pulse sync with upsert by date.
- Automation registry and run ledger for existing external scripts/projects.
- Work Knowledge manual capture and Notion sync for sanitized system-engineer notes.
- Monthly subscription tracker with local API and CLI support.
- Notion schema/bootstrap support for a Japanese verb formality/tense reference table.
- CLI quick capture through `lifequest`.
- FastAPI routes for local API testing.
- Frontend prototype homepage for the full LifeQuest direction, plus a live subscription management page.

Not implemented yet:

- Raindrop, Telegram queue, Stash, and mobile game script adapters.
- Knowledge inbox.
- ACG media library scanner.
- Unified live frontend beyond the current homepage prototype, subscription page, and Japanese slice.

## Architecture

```text
LifeQuest
  API Layer
    FastAPI routes for capture, dashboard reads, imports, and sync triggers.

  Domain Models
    Pydantic schemas that normalize data before SQLite storage or Notion sync.

  Repository Layer
    Database-backed persistence for learning sessions, activity events, and daily snapshots.

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

Status: MVP implemented.

- `AutomationDefinition` registry.
- `AutomationRun` ledger.
- API and CLI for manual registration and run logging.
- Last-run status and summary on automation lists.

Still pending:

- Adapters for existing Raindrop classifier, Telegram downloader, Stash sync, and mobile game script projects.
- Manual trigger endpoints for trusted scripts.
- Log file readers and status importers.

### Phase 3: Knowledge Inbox

Work Knowledge capture is implemented as the first work-related knowledge layer.

Still pending:

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
- Turn the homepage prototype into a fully live control center.
- Add dedicated pages for Learning, Life Admin, Knowledge, and Automation.
- Add a weekly review flow before any heavier game layer.
- Add quests, streaks, focus score, experience, and playful loops only after the core product is already useful without them.

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
http://127.0.0.1:8000/
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/life-admin/subscriptions
http://127.0.0.1:8000/japanese
```

The app uses `data/lifequest.db` by default with `DATABASE_BACKEND=sqlite`. The database file is ignored by git. Each machine can have its own local SQLite file unless you intentionally sync or migrate it.

## Database Backends

LifeQuest defaults to SQLite for local use, but it can also run against MSSQL when you want to practice a work-style database setup.

### SQLite mode

```env
DATABASE_BACKEND=sqlite
DATABASE_PATH=data/lifequest.db
```

### MSSQL mode

Install the optional dependency first:

```bash
python3 -m pip install -e '.[dev,mssql]'
```

Then configure:

```env
DATABASE_BACKEND=mssql
MSSQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=localhost,1433;Database=LifeQuest;UID=sa;PWD=YourStrong!Passw0rd;Encrypt=no;TrustServerCertificate=yes
```

Notes:

- SQLite remains the simplest default for personal daily use.
- MSSQL support is intended for learning and work-style practice.
- The current MSSQL schema keeps timestamp fields as ISO strings so the Python repository layer can stay backend-compatible while you learn the switching pattern.

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
- `POST /automations`
- `GET /automations`
- `GET /automations/{automation_ref}`
- `PATCH /automations/{automation_ref}`
- `POST /automations/{automation_ref}/runs`
- `GET /automations/{automation_ref}/runs`
- `GET /automations/runs/recent`
- `POST /automations/sync-notion`
- `POST /work-knowledge`
- `GET /work-knowledge`
- `GET /work-knowledge/{note_id}`
- `POST /work-knowledge/sync-notion`
- `POST /subscriptions`
- `GET /subscriptions`
- `GET /subscriptions/{subscription_ref}`
- `PATCH /subscriptions/{subscription_ref}`
- `GET /subscriptions/overview/monthly`

## Environment Variables

Copy `.env.example` to `.env` and fill only the integrations you want to test.

```env
APP_NAME=LifeQuest
ENVIRONMENT=development
DATABASE_BACKEND=sqlite
DATABASE_PATH=data/lifequest.db
MSSQL_CONNECTION_STRING=
LOG_LEVEL=INFO

ANKI_ENABLED=false
ANKI_CONNECT_URL=http://127.0.0.1:8765
ANKI_API_VERSION=6
ANKI_TIMEOUT_SECONDS=5
ANKI_DECKS=
ANKI_DESKTOP_PATH=

GITHUB_ENABLED=false
GITHUB_TOKEN=
GITHUB_USERNAME=
GITHUB_API_VERSION=2022-11-28
GITHUB_TIMEOUT_SECONDS=10

NOTION_ENABLED=false
NOTION_TOKEN=
NOTION_PARENT_PAGE_ID=
NOTION_LEARNING_PULSE_DATA_SOURCE_ID=
NOTION_LEARNING_PULSE_DATABASE_ID=
NOTION_AUTOMATIONS_DATA_SOURCE_ID=
NOTION_AUTOMATIONS_DATABASE_ID=
NOTION_WORK_KNOWLEDGE_DATA_SOURCE_ID=
NOTION_WORK_KNOWLEDGE_DATABASE_ID=
NOTION_JAPANESE_VERB_FORMS_DATA_SOURCE_ID=
NOTION_JAPANESE_VERB_FORMS_DATABASE_ID=
NOTION_INBOX_DATA_SOURCE_ID=
NOTION_INBOX_DATABASE_ID=
NOTION_API_VERSION=
NOTION_TIMEOUT_SECONDS=20
```

## CLI

After installing the project in editable mode, you can log learning directly:

```bash
lifequest log python 45 "FastAPI dependency injection" --tag fastapi
lifequest log japanese 30 "N3 grammar review" --difficulty 3
lifequest pulse
lifequest daily
lifequest anki-status
lifequest anki-today
lifequest anki-history --days 7
lifequest anki-difficult-history --days 14 --limit 10
lifequest import-anki
lifequest import-github
lifequest sync-notion
lifequest automation list
lifequest automation sync-notion
lifequest subscription add "ChatGPT Plus" --amount 20 --currency USD --billing-day 9 --category ai
lifequest subscription list
lifequest subscription overview --days-ahead 30
lifequest work capture "Nginx 502 troubleshooting pattern" --category nginx --summary "A 502 often means the proxy cannot reach upstream." --command "systemctl status" --concept upstream
lifequest work list
lifequest work sync-notion
lifequest notion schemas
lifequest notion check all
lifequest notion bootstrap learning-pulse
lifequest notion bootstrap japanese-verb-forms
```

The module form also works:

```bash
python3 -m app.cli log python 25 "Small automation practice"
```

## Automation Registry + Run Ledger

LifeQuest tracks existing external automation projects without rewriting them.

Use `AutomationDefinition` for the registry:

```text
key
name
category
external_project_path
command_hint
schedule_hint
log_path
owner
enabled
notes
tags
```

Use `AutomationRun` for execution history:

```text
automation_id
started_at
finished_at
status
trigger_source
items_processed
summary
error_message
external_run_id
log_excerpt
```

Example CLI workflow:

```bash
lifequest automation register raindrop-classifier "Raindrop Unsorted Classifier" \
  --category knowledge \
  --project-path "/path/to/raindrop-project" \
  --schedule-hint "daily" \
  --tag raindrop

lifequest automation log-run raindrop-classifier \
  --status success \
  --items-processed 42 \
  --summary "Tagged unsorted bookmarks by source domain"

lifequest automation list
lifequest automation runs raindrop-classifier
lifequest automation recent
lifequest automation scheduled-tasks
lifequest automation run-scheduled anki-daily
lifequest automation sync-notion
```

Current design boundary:

- LifeQuest records and observes existing automations.
- Existing scripts remain the source of their own behavior.
- Direct trigger/control should be added through narrow adapters after each script is trusted.
- Notion sync upserts by `Key` and writes registry fields plus latest run status.

Built-in scheduled tasks:

- `anki-daily` runs the daily Anki import through LifeQuest and records the result in the automation ledger.
- More built-in scheduled tasks should be added one by one as stable entrypoints, instead of pointing Windows Task Scheduler at many unrelated raw commands.

Recommended Windows Task Scheduler pattern:

```powershell
.venv\Scripts\python.exe -m app.cli automation run-scheduled anki-daily
```

This keeps the scheduler responsible only for *when* to run. LifeQuest stays responsible for:

- what task key means
- how the task runs
- how success/failure is recorded
- how future scheduled items are added consistently

For Anki on Windows, a low-risk staged rollout is:

1. Schedule `open-anki` at 18:00.
2. Watch it for a few days and confirm desktop Anki opens and syncs cleanly.
3. Then schedule `anki-daily` at 18:10 so the import runs after desktop Anki is already open.

Example task commands:

```powershell
.venv\Scripts\python.exe -m app.cli automation run-scheduled open-anki
.venv\Scripts\python.exe -m app.cli automation run-scheduled anki-daily
```

If you want to use `open-anki`, set `ANKI_DESKTOP_PATH` in `.env` to your local Anki executable path.

## Subscriptions

LifeQuest can track recurring monthly subscriptions in the local database.

Use `Subscription` for the tracker:

```text
key
name
amount
currency
billing_day
category
status
notes
tags
```

Current MVP:

- Add and update subscriptions through API or CLI.
- Show active monthly totals grouped by currency.
- Calculate the next charge date for each active subscription.
- Support fixed monthly schedules, fixed-day intervals such as every 30 days, and unknown schedules you want to fill later.
- Support lifecycle states for `active`, `paused`, and `cancelled` subscriptions.
- Separate scheduled subscriptions from items that still need billing-date review.
- Show category totals and missing-schedule items in the overview.
- List upcoming charges in a configurable forward-looking window.
- Provide a dedicated frontend page for subscription review, creation, editing, filtering, and lifecycle changes.

Example CLI workflow:

```bash
lifequest subscription add "ChatGPT Plus" \
  --amount 20 \
  --currency USD \
  --billing-day 9 \
  --category ai \
  --tag work

lifequest subscription add "YouTube Premium" \
  --amount 199 \
  --currency TWD \
  --billing-day 28 \
  --category entertainment

lifequest subscription add "Vtuber Member" \
  --amount 75 \
  --currency TWD \
  --billing-day 28 \
  --category membership

lifequest subscription add "Bahamut Anime" \
  --amount 390 \
  --currency JPY \
  --recurrence unknown \
  --status paused \
  --category entertainment

lifequest subscription list
lifequest subscription overview --days-ahead 30
lifequest subscription update chatgpt-plus --recurrence unknown --notes "Primary AI tool"
```

## Work Knowledge

Work Knowledge is for sanitized system-engineer learning notes. It should capture reusable concepts and commands, not company data.

Example:

```bash
lifequest work capture "Nginx 502 troubleshooting pattern" \
  --category nginx \
  --summary "A 502 often means the reverse proxy cannot reach the upstream service." \
  --command "systemctl status" \
  --command "journalctl -u <service>" \
  --concept "reverse proxy" \
  --concept "upstream health" \
  --system linux \
  --tag troubleshooting

lifequest work list
lifequest work sync-notion
```

Safety boundary:

- Store generalized learning, not company records.
- Do not store raw production logs, internal IPs, hostnames, tokens, customer names, ticket IDs, or full company Copilot transcripts.
- Use `sensitivity` to mark whether a note is `public`, `personal`, `company_internal`, or `confidential`.

## Japanese Verb Forms

This table is intentionally Notion-native: one verb per row, focused only on formality and tense/polarity. LifeQuest only creates/checks the database structure; the actual rows live in Notion and should be edited there.

Create or repair the Notion table:

```bash
lifequest notion bootstrap japanese-verb-forms
lifequest notion check japanese-verb-forms
```

Recommended columns:

```text
Name
Dictionary Form
Reading
Meaning
Verb Group
JLPT
Confidence
Plain Nonpast
Polite Nonpast
Plain Past
Polite Past
Plain Negative
Polite Negative
Plain Negative Past
Polite Negative Past
Notes
Tags
Updated At
```

Useful Notion views:

- By JLPT level.
- Low confidence first.
- Missing form cells.
- Recently updated.

## AnkiConnect

To enable Anki stats:

1. Install the AnkiConnect add-on in Anki.
2. Keep Anki running.
3. Set `ANKI_ENABLED=true` in `.env`.
4. Optionally set `ANKI_DECKS=Deck One,Deck Two` to limit review analysis.

LifeQuest uses Anki in a read-only mode:

- `anki-status` checks connectivity and shows which configured decks are actually available.
- `import-anki` captures a daily snapshot into the local database.
- `anki-today` shows a daily report with reviews, button distribution, non-Again rate, streak, due workload, and a next-step recommendation.
- `anki-history` shows recent snapshot history, total reviews, button distribution trends, average non-Again rate, and current streak.
- `anki-difficult-history` shows which difficult cards repeated across recent snapshots.
- `daily` runs the common local check flow: import today's Anki snapshot, then print the learning pulse.

If `ANKI_DECKS` is set, LifeQuest filters the analysis to those decks only, automatically includes child decks underneath each configured parent deck, and reports any configured deck names that are missing in Anki.

If you mainly use Anki on mobile, sync mobile Anki to AnkiWeb, open desktop Anki on the Mac, sync desktop Anki, then run LifeQuest. AnkiConnect only runs inside desktop Anki.

Recommended mobile-first workflow:

1. Review on your phone as usual.
2. When you get back to your computer, sync phone Anki to AnkiWeb.
3. Open desktop Anki and sync it.
4. Run `lifequest daily` or `lifequest import-anki`.
5. Run `lifequest anki-today` later if you want to re-check today's snapshot and sync hint.

## GitHub

To enable GitHub Python tracking:

1. Set `GITHUB_ENABLED=true`.
2. Set `GITHUB_USERNAME`.
3. Optionally set `GITHUB_TOKEN` for better rate limits and private access where GitHub allows it.

LifeQuest reads recent GitHub push events, inspects commit details, and counts commits that changed `.py` files as Python learning activity.

## Notion Learning Pulse

LifeQuest syncs one Notion row per date. It queries by the `Date` property first, then updates the existing page or creates a new one.

Current Notion API setups can use `NOTION_LEARNING_PULSE_DATA_SOURCE_ID`. Older database-based setups can use `NOTION_LEARNING_PULSE_DATABASE_ID`.

The full Notion database plan and sync mapping lives in [docs/notion_schema.md](docs/notion_schema.md).

Schema tooling:

```bash
lifequest notion schemas
lifequest notion check all
lifequest notion check learning-pulse
lifequest notion bootstrap learning-pulse
lifequest notion bootstrap automations
lifequest notion bootstrap work-knowledge
lifequest notion bootstrap japanese-verb-forms
```

`check` only reads Notion schema. `bootstrap` can add missing properties to an existing data source/database, or create a new database under `NOTION_PARENT_PAGE_ID` when no target id is configured. It does not automatically convert mismatched property types.

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

- Before adding a feature, check whether Notion, Anki, GitHub, Raindrop, Stash, or an existing project already handles it well.
- Prefer integration, adapter, sync, or summary layers over rebuilding another app inside LifeQuest.
- Keep adapters thin. Business logic belongs in services, not integration clients.
- Do not make external APIs required for local development.
- Prefer adding tests with fake adapters instead of requiring real tokens.
- Do not commit `.env`, SQLite DB files, caches, or generated package metadata.
- Commit after each coherent feature so other machines and AI tools can resume safely.
- When adding file/media automation, start with scan and dry-run suggestions before any move/delete behavior.
