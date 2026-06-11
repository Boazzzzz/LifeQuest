# Notion Schema And Sync Mapping

LifeQuest uses Notion as a dashboard and workspace layer. LifeQuest should not rebuild Notion. It should clean, normalize, summarize, and sync data into Notion only when that adds automation value.

## Global Rules

- Notion is the human-facing dashboard and workspace for Notion-native learning/reference tables.
- SQLite remains the MVP source of truth for LifeQuest-owned generated metadata and automation history.
- LifeQuest should upsert stable machine-generated records instead of creating duplicates.
- Notion-only notes can stay in Notion.
- Company-sensitive content must be sanitized before entering personal Notion.
- Avoid syncing raw logs, tokens, hostnames, internal IPs, customer names, ticket IDs, or full company Copilot conversations.

## Proposed Databases

Start with focused databases:

```text
LifeQuest - Learning Pulse
LifeQuest - Automations
LifeQuest - Work Knowledge
LifeQuest - Japanese Verb Forms
LifeQuest - Inbox
```

Build order:

1. `LifeQuest - Learning Pulse`
2. `LifeQuest - Automations`
3. `LifeQuest - Work Knowledge`
4. `LifeQuest - Japanese Verb Forms`
5. `LifeQuest - Inbox`

## Sync Ownership

Use these ownership labels when adding fields:

```text
LifeQuest
  Written by LifeQuest. Users can read or lightly annotate, but edits may be overwritten.

Notion
  Managed by the user in Notion. LifeQuest should not overwrite.

Shared
  LifeQuest can create defaults, but Notion edits should be preserved where possible.
```

## 1. LifeQuest - Learning Pulse

Purpose:

Daily learning health check for Python, Japanese, and lightweight career-growth signals.

Upsert key:

```text
Date
```

Current implementation:

`NotionSyncService.sync_learning_pulse` queries by `Date`, updates an existing page when found, and creates a new page when missing.

Recommended properties:

| Notion Property | Type | Source | LifeQuest Field | Notes |
| --- | --- | --- | --- | --- |
| Name | title | LifeQuest | `Learning Pulse {date}` | Generated display title. |
| Date | date | LifeQuest | `LearningPulse.date` | Upsert key. |
| Python Minutes | number | LifeQuest | `python_minutes` | Manual sessions for Python. |
| Japanese Minutes | number | LifeQuest | `japanese_minutes` | Manual sessions for Japanese. |
| Total Minutes | number | LifeQuest | `total_minutes` | Python + Japanese. |
| Session Count | number | LifeQuest | `session_count` | Count of manual learning sessions. |
| Anki Reviews | number | LifeQuest | `anki_reviews` | Requires desktop Anki + AnkiConnect sync. |
| Anki Accuracy | number | LifeQuest | `anki_accuracy` | Percentage when review rows are available. |
| Anki Difficult Cards | rich text | LifeQuest | `anki_difficult_cards` | Short sanitized card labels only. |
| GitHub Commits | number | LifeQuest | `github_commits` | All recent push commits for the day. |
| GitHub Python Commits | number | LifeQuest | `github_python_commits` | Commits that changed `.py` files. |
| GitHub Repositories | rich text | LifeQuest | `github_repositories` | Repo names from GitHub events. |
| GitHub Python Files | rich text | LifeQuest | `github_python_files` | Truncated list of `.py` files. |
| Focus Score | number | LifeQuest | `focus_score` | Calculated score from learning signals. |
| Summary | rich text | LifeQuest | `summary` | Short generated summary. |
| Tomorrow Priority | rich text | Shared | `tomorrow_priority` | Generated suggestion; user can revise in Notion if needed. |
| Integration Warnings | rich text | LifeQuest | `integration_warnings` | Non-fatal integration issues. |
| Reflection | rich text | Notion | none | Optional human note. LifeQuest should not overwrite. |
| Mood / Energy | select or number | Notion | none | Optional human context. |

Implementation notes:

- Preserve `Reflection` and other Notion-only fields.
- Do not sync raw Anki card HTML.
- Do not sync full GitHub diffs.
- If property names change in Notion, update `NotionSyncService._build_learning_pulse_properties`.

## 2. LifeQuest - Automations

Purpose:

Central view of LifeQuest-owned scheduled routines and their latest run status. External project observability can be added later as a read-only health signal if it becomes useful for daily review.

Upsert key:

```text
Key
```

LifeQuest models:

- `AutomationDefinition`
- latest `AutomationRun`

Recommended properties:

| Notion Property | Type | Source | LifeQuest Field | Notes |
| --- | --- | --- | --- | --- |
| Name | title | LifeQuest | `AutomationDefinition.name` | Human-readable automation name. |
| Key | rich text | LifeQuest | `key` | Stable upsert key. |
| Category | select | LifeQuest | `category` | `knowledge`, `media`, `game`, `learning`, `system`, `workflow`, `other`. |
| Enabled | checkbox | Shared | `enabled` | Notion edits can become future config changes. |
| Tags | multi-select | Shared | `tags` | Useful for grouping dashboards. |
| External Project Path | rich text | LifeQuest | `external_project_path` | Optional future path hint; avoid secrets. |
| Command Hint | rich text | LifeQuest | `command_hint` | Human hint, not auto-executed command yet. |
| Schedule Hint | rich text | LifeQuest | `schedule_hint` | Example: `daily`, `hourly`, `manual`. |
| Log Path | rich text | LifeQuest | `log_path` | Path hint only. |
| Owner | rich text | Shared | `owner` | Usually you. |
| Notes | rich text | Shared | `notes` | Human notes. |
| Last Run At | date | LifeQuest | `last_run_at` | From latest run. |
| Last Run Status | select | LifeQuest | `last_run_status` | `running`, `success`, `failed`, `partial`, `skipped`. |
| Last Run Summary | rich text | LifeQuest | `last_run_summary` | Latest run summary. |
| Updated At | date | LifeQuest | `updated_at` | Registry update time. |

Future sync behavior:

- Query by `Key`.
- Update registry fields and latest-run fields.
- Preserve Notion-only notes unless LifeQuest is explicitly asked to overwrite.
- Do not trigger external scripts from Notion.

## 3. LifeQuest - Work Knowledge

Purpose:

Sanitized personal learning notes from system-engineer work. This is for concepts and reusable techniques, not company data storage.

Initial LifeQuest model to add later:

```text
WorkKnowledgeNote
- id
- title
- category
- sanitized_summary
- commands
- concepts
- source
- sensitivity
- systems
- follow_up
- tags
- created_at
- updated_at
```

Recommended properties:

| Notion Property | Type | Source | LifeQuest Field | Notes |
| --- | --- | --- | --- | --- |
| Name | title | Shared | `title` | Human-readable note title. |
| LifeQuest ID | rich text | LifeQuest | `id` | Stable upsert key. |
| Category | select | Shared | `category` | `linux`, `networking`, `docker`, `nginx`, `database`, `security`, `monitoring`, `cloud`, `other`. |
| Sanitized Summary | rich text | Shared | `sanitized_summary` | No confidential details. |
| Commands | rich text | Shared | `commands` | Generic reusable commands only. |
| Concepts | multi-select or rich text | Shared | `concepts` | What was learned. |
| Source | select | LifeQuest | `source` | `manual`, `company_copilot`, `ticket`, `incident`, `reading`. |
| Sensitivity | select | Shared | `sensitivity` | `public`, `personal`, `company_internal`, `confidential`. |
| Systems | multi-select | Shared | `systems` | Generic systems only, not hostnames. |
| Follow Up | rich text | Shared | `follow_up` | Things to review later. |
| Tags | multi-select | Shared | `tags` | Dashboard grouping. |
| Created At | date | LifeQuest | `created_at` | Creation timestamp. |
| Updated At | date | LifeQuest | `updated_at` | Update timestamp. |

Safety rules:

- Do not store company Copilot conversation transcripts.
- Do not store raw production logs.
- Do not store internal IPs, hostnames, customer names, account IDs, tokens, or ticket IDs.
- Convert work details into generalized learning notes.

Example safe note:

```text
Title: Nginx 502 troubleshooting pattern
Summary: A 502 often means the reverse proxy cannot reach the upstream service.
Commands: systemctl status, journalctl -u, nginx -t
Concepts: reverse proxy, upstream health, service restart
Sensitivity: personal
```

## 4. LifeQuest - Japanese Verb Forms

Purpose:

Focused Notion-native table for verbs whose formality and tense/polarity forms need review.

Ownership:

```text
Notion is the source of truth for rows.
LifeQuest only creates/checks the database schema.
```

Recommended properties:

| Notion Property | Type | Source | LifeQuest Field | Notes |
| --- | --- | --- | --- | --- |
| Name | title | Notion | none | Display title, usually the dictionary form. |
| Dictionary Form | rich text | Notion | none | 辞書形. |
| Reading | rich text | Notion | none | Optional reading. |
| Meaning | rich text | Notion | none | Short meaning in English/Chinese. |
| Verb Group | select | Notion | none | `ichidan`, `godan`, `suru`, `kuru`, `irregular`. |
| JLPT | select | Notion | none | `N5`, `N4`, `N3`, `N2`, `N1`, `unknown`. |
| Confidence | number | Notion | none | 1-5 self-rating. |
| Plain Nonpast | rich text | Notion | none | 普通形・非過去・肯定. |
| Polite Nonpast | rich text | Notion | none | 丁寧形・非過去・肯定. |
| Plain Past | rich text | Notion | none | 普通形・過去・肯定. |
| Polite Past | rich text | Notion | none | 丁寧形・過去・肯定. |
| Plain Negative | rich text | Notion | none | 普通形・非過去・否定. |
| Polite Negative | rich text | Notion | none | 丁寧形・非過去・否定. |
| Plain Negative Past | rich text | Notion | none | 普通形・過去・否定. |
| Polite Negative Past | rich text | Notion | none | 丁寧形・過去・否定. |
| Notes | rich text | Notion | none | Mistake reason or nuance. |
| Tags | multi-select | Notion | none | Grouping. |
| Updated At | date | Notion | none | Optional manual update timestamp. |

Lifecycle:

- Use `lifequest notion bootstrap japanese-verb-forms` to create or repair columns.
- Fill and review verb rows directly in Notion.
- Add local LifeQuest sync later only if there is a clear automation value.

## 5. LifeQuest - Inbox

Purpose:

Unified triage queue for manual notes, URLs, AI summaries, and review items that should flow into learning or work-knowledge review.

Initial LifeQuest model to add later:

```text
InboxItem
- id
- title
- source
- payload_type
- url
- summary
- status
- target
- tags
- created_at
- processed_at
```

Recommended properties:

| Notion Property | Type | Source | LifeQuest Field | Notes |
| --- | --- | --- | --- | --- |
| Name | title | Shared | `title` | Item title. |
| Source | select | LifeQuest | `source` | `manual`, `ai`, `reading`, `notion`. |
| Payload Type | select | LifeQuest | `payload_type` | `url`, `note`, `file`, `task`, `summary`. |
| URL | url | LifeQuest | `url` | Optional. |
| Summary | rich text | Shared | `summary` | Short summary. |
| Status | select | Shared | `status` | `queued`, `processing`, `done`, `failed`, `skipped`. |
| Target | select | Shared | `target` | `notion`, `read_later`, `work_knowledge`, `learning`. |
| Tags | multi-select | Shared | `tags` | Auto and manual tags. |
| Created At | date | LifeQuest | `created_at` | Creation timestamp. |
| Processed At | date | LifeQuest | `processed_at` | Completion timestamp. |

Future sync behavior:

- Start with manual capture.
- Keep external bookmark and message systems outside LifeQuest unless a narrow review workflow needs a read-only signal.
- Notion should be the triage dashboard, not the canonical crawler.

## Implementation Plan

### Step 1: Complete Learning Pulse Mapping

- Keep current upsert by `Date`.
- Verify Notion database properties match this document.
- Add tests for property mapping if schema changes.
- Use `lifequest notion check learning-pulse` before syncing.
- Use `lifequest notion bootstrap learning-pulse` to add missing properties or create the database under `NOTION_PARENT_PAGE_ID`.

### Step 2: Sync Automations

- Add Notion settings for automations database/data source id.
- Implement `sync_automations`.
- Upsert by `Key`.
- Include latest run status from `AutomationDefinition`.
- Use `NOTION_AUTOMATIONS_DATA_SOURCE_ID` or `NOTION_AUTOMATIONS_DATABASE_ID`.
- Use `lifequest notion check automations` before syncing.
- Treat external project observability as future optional scope, not a default integration target.

### Step 3: Work Knowledge Capture

- Add `WorkKnowledgeNote` model, table, repository, service, API, and CLI.
- Start with manual capture only.
- Add Notion sync after capture is stable.
- Use `NOTION_WORK_KNOWLEDGE_DATA_SOURCE_ID` or `NOTION_WORK_KNOWLEDGE_DATABASE_ID`.
- Use `lifequest notion check work-knowledge` before syncing.

### Step 4: Japanese Verb Forms

- Keep this as a Notion-native table.
- LifeQuest only owns schema check/bootstrap for now.
- Use `NOTION_JAPANESE_VERB_FORMS_DATA_SOURCE_ID` or `NOTION_JAPANESE_VERB_FORMS_DATABASE_ID`.
- Use `lifequest notion check japanese-verb-forms` after Notion changes.

### Step 5: Inbox

- Add `InboxItem` model, table, repository, service, API, and CLI.
- Start manual.
- Use `lifequest notion check inbox` before syncing once Inbox is implemented.

## Schema Tooling

Supported CLI:

```bash
lifequest notion schemas
lifequest notion check all
lifequest notion check learning-pulse
lifequest notion bootstrap learning-pulse
```

Behavior:

- `check` retrieves the target data source or legacy database and compares property names and property types.
- `bootstrap` adds missing properties when a target id is configured.
- `bootstrap` creates a database under `NOTION_PARENT_PAGE_ID` when no target id is configured.
- `bootstrap` does not automatically convert mismatched property types; fix those manually in Notion.

Required capabilities:

- Reading/checking requires the Notion integration to have access to the target page/database.
- Creating databases requires insert content capability.
- Updating data source/database properties requires update content capability.
