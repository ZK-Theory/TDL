---
description: Git workflow conventions and commit guidance for TDL.
alwaysApply: true
---

## Git Policy Guidance

This repository uses structured commit prefixes and branch naming to keep the repo-vault bridge consistent.

### Commit prefixes

Use one of the approved prefixes in every commit message subject.

- `[RESULT]` — Quantitative result worth logging
- `[DECISION]` — Parameter or method locked
- `[NEGATIVE]` — Informative negative result
- `[PIPELINE]` — Pipeline or infrastructure change
- `[DATA]` — Data processing change
- `[EXPLORE]` — Exploratory work, no vault action needed

### Branch naming

Follow the repository branch naming conventions:

- `paper/<desc>` — paper writing or draft work
- `run/<desc>` — computational experiments or analysis runs
- `pipe/<desc>` — pipeline and infrastructure changes
- `repo/<desc>` — repo maintenance or extraction work

### Hook enforcement

This repository requires commit prefixes on all commits. The tracked `.githooks/commit-msg`
enforces them, alongside `pre-commit`, `prepare-commit-msg` and `pre-push`. Git reads hooks
from `.githooks/` because the repository sets `core.hooksPath=.githooks`; anything placed in
`.git/hooks/` is silently ignored, so nothing is ever installed there. Verify the hooks are
live, and belong to this checkout, with:

```bash
uv run python .claude/hooks/install-git-hooks.py
```

A fresh clone with no `core.hooksPath` set is activated with `--install`, which sets the
clone-local `core.hooksPath=.githooks` and copies nothing.

### When to use this guidance

- Before committing any change, choose the prefix that matches the work type.
- Use branch names that reflect the task category.
- Keep vault-related workflow decisions in sync with `CLAUDE.md` and `.claude/instructions/workflow.instructions.md`.
- Put `.github/workflows/*` edits in their own PR unless the workflow change is the PR's subject. A store or code fix that also changes CI selection is refused by platform-order only after it has been built and reviewed (PR #283).
- Merge admission requires no review producer (`review_producers: []`, CONVENTIONS, 2026-10-17). Thread finality still blocks on every unresolved, non-outdated review thread, whoever wrote it: Codex (`chatgpt-codex-connector`, still installed and still reviewing new PRs), CodeRabbit or a person. The remedy is to reply on the thread and resolve it; the owner resolves any thread whose finding is declined. There is no waiver path (declined 2026-10-21, system review 2026-10-20 Group B), and agent sessions never bypass the gate. The sweep's `*/5` cron fires about every four hours in practice, so after resolving a thread, re-run merge-admission rather than waiting for the sweep.
