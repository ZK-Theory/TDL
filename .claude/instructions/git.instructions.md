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

This repository recommends using a git hook to enforce commit prefixes.
A `commit-msg` hook can validate prefixes for this repository.
Install the provided helper script with:

```bash
python .claude/hooks/install-git-hooks.py
```

This installs `.claude/hooks/git-commit-msg.sh` as `.git/hooks/commit-msg` and makes it executable.

### When to use this guidance

- Before committing any change, choose the prefix that matches the work type.
- Use branch names that reflect the task category.
- Keep vault-related workflow decisions in sync with `CLAUDE.md` and `.claude/instructions/workflow.instructions.md`.
