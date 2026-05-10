# LifeQuest Codex Workflow Rules

## Purpose

This repository is actively developed with multiple Codex threads, VS Code, and local terminals in parallel.
To avoid branch churn, file conflicts, and mixed-context work, every Codex thread must follow the rules below.

## Core Rules

1. One Codex thread = one coherent unit of work.
2. One active coding thread = one dedicated git worktree.
3. Do not switch branches unless the user explicitly asks in that thread.
4. Do not assume another thread's branch is safe to reuse.
5. Never run live parallel threads against the same checkout when both may edit files.
6. Prefer small, reviewable commits and branch-scoped pull requests.

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

## File Ownership Guidance

To reduce collisions, prefer these ownership boundaries:

- Integration thread: docs, workflow files, merge support, release prep
- Optimization thread: `app/core/*`, cross-cutting tests, infra docs
- Learning thread: `app/services/learning.py`, `app/api/routes/learning.py`, related models/tests
- Dashboard/UI thread: `app/static/*`, dashboard models/routes/services
- Subscription thread: subscription services, routes, and tests

If a task requires editing files owned by another active thread, call that out before proceeding.

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
- If a workflow becomes repetitive, promote it into a repo skill or documented checklist.
- Use subagents mainly for read-heavy tasks such as exploration, triage, review, or test analysis.
- Be cautious with parallel write-heavy tasks because they increase merge and coordination risk.
