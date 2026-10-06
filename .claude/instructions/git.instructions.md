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
- Merge admission needs Codex to reach a terminal state on the exact head: a review naming the head, or a +1 reaction left after the head's first check started. If the gate reports the head untriggered, or reports a stale +1 or a usage limit, comment `@codex review` (after the quota resets); record an owner waiver rather than bypass the gate. A +1 that arrives after the check failed triggers nothing itself; the merge-admission sweep re-runs the check once it sees it. The sweep's `*/5` cron fires about every four hours in practice (126 runs in 20.6 days), so a bare +1 can wait hours; a Codex comment (its "no major issues" note or its usage-limit reply) starts the sweep at once.
