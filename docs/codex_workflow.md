# LifeQuest Codex Workflow

This file is the human-facing operating guide for using Codex on LifeQuest without branch chaos.

## Goal

Preserve the benefits of long-lived Codex threads while preventing:

- accidental branch switching across tasks
- multiple threads editing the same checkout
- mixed commits from unrelated work
- confusion between Codex, VS Code, and local terminal states

## Recommended Setup

Keep a small number of long-lived threads, each with a fixed role:

1. Integration thread
2. Project optimization thread
3. One active feature thread

Each of those threads should use a separate git worktree.

## Suggested Mapping

### Integration

- Purpose: merge-ready inspection, repo-wide coordination, workflow upkeep
- Branch: `main`
- Worktree: dedicated integration checkout

### Project optimization

- Purpose: migrations, tests, config, exceptions, performance, cleanup
- Branch: `codex/project-optimization`
- Worktree: dedicated optimization checkout

### Feature work

- Purpose: one focused product or engineering feature
- Branch: feature-specific `codex/...`
- Worktree: dedicated feature checkout

## Daily Rules

### Before starting work in any thread

Run:

```powershell
git branch --show-current
git status -sb
git worktree list
pwd
```

If the branch or worktree is wrong, fix that before asking Codex to edit files.

### When opening a new Codex thread

Define the thread clearly:

- what role it serves
- which branch it should stay on
- which kinds of files it owns
- which kinds of work it must avoid

### When using VS Code

- Use VS Code for hands-on editing, visual review, and local app runs.
- Use Codex threads for planning, broad code changes, repetitive analysis, and structured implementation.
- Remember that VS Code terminals may have a different shell session state than Codex-managed terminals.

## Branch Hygiene

- Do not do substantial feature development on `main`.
- Do not let two active writing threads share one checkout.
- Do not check out the same branch in multiple worktrees.
- Use small commits with one topic per commit.
- Prefer one branch per pull request.

## GitHub CLI Hygiene

If `gh` fails with a proxy error to `127.0.0.1:9`, clear proxy variables in the current shell:

```powershell
$env:HTTP_PROXY=$null
$env:HTTPS_PROXY=$null
$env:ALL_PROXY=$null
$env:GIT_HTTP_PROXY=$null
$env:GIT_HTTPS_PROXY=$null
```

Then retry:

```powershell
gh auth status
gh pr status
gh repo view
```

## Recommended Cleanup After Chaos

If multiple old threads have been switching branches unpredictably:

1. Keep one thread as the integration thread.
2. Manually archive or close other stale Codex threads in the app.
3. Check `git worktree list`.
4. Identify worktrees that are detached or no longer needed.
5. Prune or remove unused worktrees only after confirming they contain no uncommitted work.
6. Re-open future Codex threads only from the correct worktree for that role.

## When to Use Subagents

Good uses:

- codebase exploration
- finding test gaps
- review categorization
- triage and summaries

Avoid using parallel subagents for overlapping write-heavy tasks unless the ownership boundaries are explicit.
