# LifeQuest Architecture

## Product Direction

LifeQuest is the central backend for personal learning, life admin, knowledge capture, and review. It should integrate only the external tools that directly support those goals.

Primary purpose:

- Protect focus for Python and Japanese learning.
- Reduce administrative overhead.
- Turn learning and life-admin signals into useful review surfaces.
- Keep future frontend interfaces possible without expanding into a general script runner.

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

- `InboxItem`
- `AutomationDefinition`
- `AutomationRun`

### 3. Repository Layer

SQLite-backed persistence. SQLite is the source of truth for MVP metadata and learning history.

### 4. Service Layer

Business workflows:

- learning pulse generation
- Notion sync
- scheduled task run ledger
- insight generation

### 5. Integration Adapters

Thin wrappers around external systems:

- AnkiConnect
- GitHub API
- Notion API

Adapters should be optional, mock-friendly, and replaceable.

## Implementation Phases

### Phase 1: Learning Core

- Manual learning sessions.
- Daily pulse for Python and Japanese.
- AnkiConnect status, daily review import, accuracy estimate, and difficult-card capture.
- GitHub status, daily push activity import, and Python commit detection.
- Notion daily pulse upsert by date.
- CLI quick capture for low-friction manual logging.

### Phase 2: Daily Routine Observability

- Scheduled task registry for LifeQuest-owned routines.
- Run ledger for Anki and future review/admin routines.
- API and CLI for manual registration and run logging.
- Optional future read-only health checks for external projects if they become relevant to daily review.

### Phase 3: Knowledge Inbox

- Unified inbox for URLs, notes, AI summaries, and reading items.
- Notion knowledge sync.

### Phase 4: Frontend / Review Layer

- Use LifeQuest API as the backend.
- Add weekly review, focus score, and daily review loops.
