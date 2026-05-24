---
description: Hook enforcement rules for repository PreToolUse and PostToolUse behavior.
alwaysApply: true
---

## Hook Enforcement

This repository uses `.claude/settings.json` to enforce quality checks through hook scripts.

### PreToolUse hooks

- `notation-guard.sh` validates paper-related Markdown edits for notation consistency against `papers/shared/notation.md`.

### PostToolUse hooks

- Python file writes/edits trigger linting and formatting via `uv run ruff`.
- File writes trigger the mandatory research-context header check (`research-context-check.sh`).
- Writes under `results/` trigger a vault-sync reminder (`results-vault-reminder.sh`).

### Hook file locations

- `.claude/hooks/notation-guard.sh`
- `.claude/hooks/research-context-check.sh`
- `.claude/hooks/results-vault-reminder.sh`

### Purpose

Keep policy enforcement declarative and separate from long-form guidance.
The root policy file should only describe active requirements and refer to these specialized instruction files.
