# Implementation Issues

## Issue 1: Adopt a real database migration workflow

- Priority: P1
- Status: Groundwork started
- Problem: schema upgrades are currently embedded in runtime initialization, which makes versioned upgrades harder to reason about as the database evolves.
- Current groundwork:
  - SQLite upgrade logic now runs through `app/core/migrations.py`
  - applied SQLite migrations are tracked in `schema_migrations`
  - tests cover fresh migration recording and legacy SQLite upgrade behavior
- Scope:
  - introduce a migration tool and baseline revision
  - move SQLite upgrade logic out of `initialize_database`
  - make local/test database setup run migrations explicitly
- Acceptance criteria:
  - a new database can be initialized from migrations
  - an older SQLite database can be upgraded without manual SQL edits
  - schema history is tracked in versioned migration files

## Issue 2: Harden Notion sync against transient failures

- Priority: P1
- Problem: Notion sync currently lacks retry/backoff and treats partial failure as a thin reporting concern.
- Scope:
  - add retry handling for timeout, `429`, and `5xx`
  - classify retryable vs non-retryable failures
  - return clearer `skipped` / `partial` / `failed` outcomes
  - improve structured logging context
- Acceptance criteria:
  - transient Notion failures are retried with bounded backoff
  - exhausted retries produce an observable failure result
  - partial syncs identify which records failed

## Issue 3: Add conflict protection for Notion sync

- Priority: P2
- Problem: local sync can overwrite manual Notion edits because there is no sync fingerprint or last-synced comparison.
- Scope:
  - record a local sync timestamp or fingerprint in Notion
  - compare local state with remote sync metadata before patching
  - report conflicts instead of auto-overwriting them
- Acceptance criteria:
  - manual remote edits can be detected
  - conflicting records are surfaced without silent overwrite

## Issue 4: Add pagination to learning session listing

- Priority: P1
- Status: Implemented
- Problem: `GET /learning/sessions` previously supported `limit` only, which does not scale once the table grows.
- Scope:
  - add `offset` support in the route, service, and repository
  - keep ordering deterministic for page boundaries
  - cover the API and repository flow with tests
- Acceptance criteria:
  - callers can request `limit` and `offset`
  - pagination returns stable descending results
  - tests cover first-page and next-page behavior

## Issue 5: Define subscription date semantics around user timezone

- Priority: P2
- Problem: subscription charge calculations currently derive the reference date from UTC, which can drift from the user's intended local billing date.
- Scope:
  - define a single application timezone policy
  - compute charge dates from local reference dates
  - cover month-end and leap-year edge cases
- Acceptance criteria:
  - subscription dates follow documented local-date semantics
  - cross-boundary dates do not shift by surprise

## Issue 6: Introduce a shared exception hierarchy

- Priority: P2
- Status: Groundwork started
- Problem: the codebase already has some custom errors, but they do not share a common base and some modules still raise raw `ValueError`.
- Current groundwork:
  - shared base exceptions live in `app/core/exceptions.py`
  - existing not-found, conflict, external-service, and configuration errors keep their public class names while inheriting shared bases
- Scope:
  - add shared base exceptions for validation, not-found, conflict, and external-service errors
  - update service and validation layers to raise domain-specific exceptions
  - tighten API-to-HTTP mapping
- Acceptance criteria:
  - routes can distinguish validation, conflict, not-found, and external integration failures
  - raw `ValueError` usage is reduced to framework-level validation only

## Issue 7: Expand coverage around boundary conditions

- Priority: P3
- Status: Groundwork started
- Problem: current tests miss several behavioral edges even though the overall suite is growing.
- Current groundwork:
  - `tests/conftest.py` provides temp SQLite database fixtures for cross-cutting tests
  - migration upgrade-path and shared exception hierarchy coverage lives in `tests/test_core_foundations.py`
- Scope:
  - add Notion sync retry/conflict tests
  - add subscription leap-year and month-end coverage
  - add migration upgrade-path tests
- Acceptance criteria:
  - each high-risk path has at least one edge-case test
  - regression risk is reduced for date and sync logic

## Issue 8: Remove machine-specific configuration defaults

- Priority: P3
- Status: Implemented
- Problem: a hard-coded local Anki executable path makes the default config personal-machine specific.
- Scope:
  - remove the baked-in path from settings defaults and `.env.example`
  - make the scheduled automation fail with a clear message when the path is unset
  - document the optional environment variable
- Acceptance criteria:
  - new environments do not require source edits to remove personal paths
  - `open-anki` reports a clear configuration error when the path is missing
