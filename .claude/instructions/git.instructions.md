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
