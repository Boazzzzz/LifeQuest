# LifeQuest Code Review Guide

Use this file when the user asks for a review, when running `/review`, or when preparing a change for merge.

## Review Priorities

Findings come first.

- Lead with bugs, regressions, risky assumptions, and missing tests.
- Order findings by severity and impact, not by file order.
- Keep summaries brief after the findings, not before them.

## What To Check

### Product boundary checks

- LifeQuest should orchestrate mature tools, not casually replace them.
- Prefer adapters, summaries, normalization, and observability over rebuilding Notion, Anki, GitHub, or external automation projects.

### Data and persistence checks

- Verify SQLite behavior still makes sense, and call out MSSQL compatibility risks when a change touches shared repository logic.
- Be careful with timestamps, date handling, and recurrence calculations.
- Flag any migration or schema change that could strand existing local data.

### Integration safety checks

- External integrations must remain optional and mock-friendly.
- Do not require real tokens, live APIs, or user-specific services for default local development.
- Thin adapters are preferred; business logic should stay in services.

### Automation and side-effect checks

- Risky automation should start with scan, dry-run, or suggestion mode before file moves or destructive actions.
- Review changes that trigger external commands, scheduled tasks, or filesystem writes with extra skepticism.

### AI-specific checks

- AI output should be advisory, reviewable, or bounded before it becomes canonical data or triggers side effects.
- Flag designs that let an LLM silently overwrite trusted records without a clear approval or validation step.

### Tests and verification checks

- Look for missing unit tests, missing edge-case coverage, and missing regression coverage.
- If the repo has no lint or typecheck command for the affected area, say that explicitly instead of assuming coverage exists.
- For UI-facing changes, ask whether the relevant route or page was manually checked.

## Review Output Format

Use this structure when possible:

1. Findings
2. Open questions or assumptions
3. Short change summary

When there are no findings, say so explicitly and then mention any residual risk or verification gap.
