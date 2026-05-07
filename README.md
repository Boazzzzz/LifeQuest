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
- `POST /learning/import/anki/today`
- `POST /learning/pulse/today/sync-notion`

## AnkiConnect

To enable Anki stats:

1. Install the AnkiConnect add-on in Anki.
2. Keep Anki running.
3. Set `ANKI_ENABLED=true` in `.env`.
4. Optionally set `ANKI_DECKS=Deck One,Deck Two` to limit review analysis.

LifeQuest reads review counts from AnkiConnect and, when deck review rows are available, estimates accuracy and lists cards answered with Again.

## Philosophy

Notion is a dashboard, not the source of truth. LifeQuest keeps the canonical activity and learning data locally first, then syncs useful summaries outward.
