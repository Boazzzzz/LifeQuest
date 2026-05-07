# LifeQuest Architecture

## Product Direction

LifeQuest is the central backend for personal automation. It should integrate existing automations instead of immediately rewriting them.

Primary purpose:

- Protect focus for Python and Japanese learning.
- Reduce administrative overhead.
- Turn scattered automation outputs into observable events.
- Keep future frontend and game-like interfaces possible.

## System Layers

### 1. API Layer

FastAPI routes for manual capture, dashboards, integration callbacks, and future UI clients.

### 2. Domain Models

Stable Pydantic models that normalize external data before persistence or Notion sync.

Initial learning models:

- `LearningSession`
- `LearningPulse`
- `ActivityEvent`

Future general models:

- `UniversalNode`
- `InboxItem`
- `AutomationDefinition`
- `AutomationRun`
- `MediaWorkNode`

### 3. Repository Layer

SQLite-backed persistence. SQLite is the source of truth for MVP metadata and learning history.

### 4. Service Layer

Business workflows:

- learning pulse generation
- Notion sync
- automation run ledger
- asset/media indexing
- insight generation

### 5. Integration Adapters

Thin wrappers around external systems:

- AnkiConnect
- GitHub API
- Notion API
- Raindrop.io
- Telegram queue
- Stash
- mobile game script runners

Adapters should be optional, mock-friendly, and replaceable.

## Implementation Phases

### Phase 1: Learning Core

- Manual learning sessions.
- Daily pulse for Python and Japanese.
- AnkiConnect status, daily review import, accuracy estimate, and difficult-card capture.
- GitHub status, daily push activity import, and Python commit detection.
- Notion daily pulse upsert by date.
- CLI quick capture for low-friction manual logging.

### Phase 2: Automation Observability

- Automation registry.
- Run ledger.
- Adapters for existing Raindrop, Telegram, Stash, and game script projects.

### Phase 3: Knowledge Inbox

- Unified inbox for URLs, notes, AI summaries, and reading items.
- Notion knowledge sync.
- Raindrop dead-link checks.

### Phase 4: ACG Media Library

- Scan only whitelisted ACG folders.
- Dry-run duplicate and organization suggestions.
- Work-level metadata, not just file-level metadata.

### Phase 5: Frontend / Game Layer

- Use LifeQuest API as the backend.
- Add quests, streaks, experience, focus score, and daily review loops.
