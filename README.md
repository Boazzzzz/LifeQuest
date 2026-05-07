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
- `POST /learning/pulse/today/sync-notion`

## Philosophy

Notion is a dashboard, not the source of truth. LifeQuest keeps the canonical activity and learning data locally first, then syncs useful summaries outward.

