# LifeQuest Codex Workflow Rules

## Purpose

This repository is actively developed with multiple Codex threads, VS Code, and local terminals in parallel.
To avoid branch churn, file conflicts, and mixed-context work, every Codex thread must follow the rules below.

This file lives at the repository root and is the default workflow contract for all Codex threads in this repo.
At the start of a thread, read this file before making meaningful edits.

## Core Rules

1. One Codex thread = one coherent unit of work.
2. One active coding thread = one dedicated git worktree.
3. Do not switch branches unless the user explicitly asks in that thread.
4. Do not assume another thread's branch is safe to reuse.
5. Never run live parallel threads against the same checkout when both may edit files.
6. Prefer small, reviewable commits and branch-scoped pull requests.
7. Completed work must be committed. Do not leave finished implementation, review-driven fixes, or workflow changes only as unstaged or uncommitted local edits.
8. This commit rule applies to every branch, not only `main`. Treat feature, optimization, integration-sandbox, and other working branches the same way.

## Stop Conditions

Stop and report back to the user before continuing if any of the following is true:

- the thread is not running in the intended worktree
- the current branch does not match the thread's role
- the worktree is on detached HEAD
- the branch is already checked out in another active worktree
- the task requires editing files primarily owned by another active thread
- the repo state is ambiguous enough that you cannot tell whether local changes are intentional

## Standard Thread Roles

### Integration thread

- Worktree role: local integration / final review
- Expected branch: `main`
- Responsibilities:
  - inspect current repo state
  - integrate or review finished feature work
  - prepare commits, pushes, and pull requests
  - maintain shared workflow documents
- Restrictions:
  - do not start large feature development here
  - do not take ownership of feature branches unless the user explicitly redirects this thread

### Integration sandbox thread

- Expected branch: `codex/integration`
- Responsibilities:
  - pre-integration diff review
  - isolated smoke testing before final integration
  - merge rehearsal or temporary integration experiments
- Restrictions:
  - do not treat this branch as the canonical integration branch
  - final merge-ready review, commit, and push should happen on `main` unless the user explicitly redirects

### Function development thread

- Expected branch: `function-development`
- Responsibilities:
  - active feature development when the user intentionally wants a broader working branch
  - implementation spikes that still need a dedicated worktree
- Restrictions:
  - treat this as a legacy/general-purpose branch, not the preferred default for new feature lines
  - for new substantial work, prefer a feature-specific `codex/...` branch instead
  - if this branch is used, define the scope clearly in the opening prompt before editing

### Project optimization thread

- Expected branch: `codex/project-optimization`
- Responsibilities:
  - migration groundwork
  - test infrastructure
  - exception hierarchy
  - configuration cleanup
  - performance and maintainability improvements

### Feature thread

- Expected branch: feature-specific `codex/...` branch
- Responsibilities:
  - one focused product or engineering feature
- Restrictions:
  - keep changes scoped to the feature's files when possible

## Branch and Worktree Policy

- `main` is reserved for integration, final verification, and merge-ready inspection.
- Each substantial feature or technical-debt stream should have its own branch and worktree.
- If a thread is opened on a detached HEAD worktree, stop and confirm the intended branch before continuing meaningful edits.
- If a branch is already checked out by another worktree, do not attempt to reuse it in this checkout. Use another worktree or handoff instead.
- If this chat is attached to the main worktree, treat it as the integration thread unless the user explicitly says otherwise.

## Local Folder Layout

Use a consistent local folder layout so worktrees are easy to find and do not get mixed into the main checkout.

- Main workspace: `F:\Documents\projects\LifeQuest`
- Shared worktree root: `F:\Documents\projects\_worktrees\LifeQuest`
- Integration worktree example: `F:\Documents\projects\_worktrees\LifeQuest\integration`
- Feature worktree examples:
  - `F:\Documents\projects\_worktrees\LifeQuest\function-development`
  - `F:\Documents\projects\_worktrees\LifeQuest\learning-feature`
  - `F:\Documents\projects\_worktrees\LifeQuest\dashboard-ui`
  - `F:\Documents\projects\_worktrees\LifeQuest\subscription-fix`

Layout rules:

- Keep the main `LifeQuest` folder reserved for the primary integration checkout.
- Create additional worktrees under `F:\Documents\projects\_worktrees\LifeQuest\`.
- Do not create nested worktrees inside the main repo directory.
- Do not create nested worktrees inside another worktree.
- Do not scatter alternate checkouts as sibling folders such as `LifeQuest-2` or `LifeQuest-test`.
- Name worktree folders by role or feature focus so their purpose is obvious.

## Run And Verify

Codex should prefer repository-native commands that are already documented or already work in this project.

Command environment preference:

- Prefer Linux/Ubuntu/WSL commands for day-to-day development, inspection, tests, and app startup.
- In this Windows checkout, the WSL repo path is `/mnt/f/Documents/projects/LifeQuest`.
- Avoid PowerShell for normal project work when WSL/Linux is available.
- Use PowerShell only for Windows-only integration points, such as Task Scheduler registration, existing `.ps1` runtime scripts, or when WSL/Linux access is blocked and the user approves the fallback.
- When using WSL against the Windows-mounted checkout, keep Git configured to avoid CRLF status noise; this checkout uses local `core.autocrlf=true`.

Environment setup:

- Create a venv when needed: `python -m venv .venv`
- Install dev dependencies: `python -m pip install -e ".[dev]"`
- Copy environment template on a fresh machine: `Copy-Item .env.example .env`

Run the app locally:

- API server: `python -m uvicorn app.main:app --reload`
- Daily runtime backend: `.\scripts\runtime\start-lifequest.ps1`
- Daily runtime status: `.\scripts\runtime\status-lifequest.ps1`
- Daily runtime dashboard: `.\scripts\runtime\open-dashboard.ps1`
- Daily runtime shutdown: `.\scripts\runtime\stop-lifequest.ps1`

Primary verification commands:

- Full test suite: `python -m pytest`
- Targeted test file: `python -m pytest tests/test_learning_service.py`
- Targeted test selection: `python -m pytest tests/test_subscription.py -k monthly`

Important verification notes:

- Use `--reload` only while actively developing. Daily always-on runtime should use the runtime scripts, which run uvicorn without reload mode.
- `pyproject.toml` currently defines pytest, but does not define a dedicated lint or typecheck command.
- Do not claim lint or typecheck passed unless the repo gains an explicit command and you actually run it.
- Prefer targeted tests for narrow changes and the full suite for cross-cutting changes when practical.
- If a change affects the local UI, also name the relevant page or route for manual verification.

Useful local routes:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/life-admin/subscriptions`
- `http://127.0.0.1:8000/life-admin/money`
- `http://127.0.0.1:8000/japanese`

## File Ownership Guidance

To reduce collisions, prefer these ownership boundaries:

- Integration thread: docs, workflow files, merge support, release prep
- Optimization thread: `app/core/*`, cross-cutting tests, infra docs
- Learning thread: `app/services/learning.py`, `app/api/routes/learning.py`, related models/tests
- Dashboard/UI thread: `app/static/*`, dashboard models/routes/services
- Subscription thread: subscription services, routes, and tests

If a task requires editing files owned by another active thread, call that out before proceeding.
If cross-thread edits are unavoidable, report the overlap first and wait for user confirmation before making broad changes.

## Start-of-Thread Checks

Before making changes, verify:

- current branch
- worktree cleanliness
- current working directory
- whether the thread is on `main`, a feature branch, or detached HEAD

Useful commands:

```powershell
git branch --show-current
git status -sb
git worktree list
pwd
```

Interpretation guidance:

- If branch, worktree, and directory all match the intended thread role, proceed.
- If `git status -sb` shows expected local edits in the current thread, proceed carefully without reverting unrelated work.
- If `git status -sb` includes only noisy warnings from known temp or permission-restricted directories, call out the warnings but do not treat them as a branch/worktree failure by themselves.
- If status output suggests unexpected tracked-file changes, detached HEAD, or branch confusion, stop and report first.

Recommended startup sequence:

1. Read this `AGENTS.md`.
2. Run the start-of-thread checks.
3. Identify whether the thread is integration, optimization, or feature-scoped.
4. Confirm that planned edits stay within the thread's ownership boundary.
5. Only then begin implementation or review work.

## Planning Expectations

- For complex, ambiguous, or multi-step changes, plan first before editing.
- A good task handoff or prompt should include: goal, context, constraints, and done-when conditions.
- Keep one Codex thread focused on one coherent unit of work.
- Use subagents mainly for bounded exploration, test analysis, log triage, or other read-heavy support tasks.
- Avoid parallel write-heavy subagent work on overlapping files.

## Done Means

Before calling work complete, make sure all of the following are true unless the user explicitly waives them:

- the change is scoped to the intended branch and worktree role
- relevant tests were run, or the reason they were not run is clearly stated
- any manual verification path is named for UI or integration-facing changes
- no unrelated user changes were reverted
- workflow or collaboration rule changes are reflected in `AGENTS.md`
- review-oriented tasks follow the repository review guidance in `code_review.md`
- finished work is committed on the current branch instead of being left only in the working tree

## Commit And Push Expectations

- If a coherent unit of work is finished, commit it before ending the task.
- Do not treat "implemented but not committed yet" as done unless the user explicitly asks to stop before commit.
- This expectation applies on every branch: `main`, `codex/integration`, feature branches, optimization branches, and any future working branch.
- Prefer small, reviewable commits over large mixed commits.
- If the user wants durable backup, handoff, PR preparation, or cross-machine continuity, also push the branch to the remote after committing.
- If a branch already has a remote counterpart, do not assume leaving work only on the local branch is sufficient for handoff safety.
- If you intentionally do not push, state that clearly in the final handoff.

## GitHub CLI Note

This environment may inject broken proxy variables into the shell session.
If `gh` fails with `127.0.0.1:9`, clear these variables in the current terminal session before retrying:

```powershell
$env:HTTP_PROXY=$null
$env:HTTPS_PROXY=$null
$env:ALL_PROXY=$null
$env:GIT_HTTP_PROXY=$null
$env:GIT_HTTPS_PROXY=$null
```

## Long-Running Context

- Keep durable repository rules here instead of re-explaining them in each thread.
- Keep review-specific guidance in `code_review.md` and reference it during reviews.
- If a workflow becomes repetitive, promote it into a repo skill or documented checklist.
- Use subagents mainly for read-heavy tasks such as exploration, triage, review, or test analysis.
- Be cautious with parallel write-heavy tasks because they increase merge and coordination risk.
