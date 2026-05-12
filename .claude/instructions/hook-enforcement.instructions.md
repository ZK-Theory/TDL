---
description: Hook enforcement rules for repository PreToolUse and PostToolUse behavior.
alwaysApply: true
---

## Hook Enforcement

This repository uses `.claude/settings.json` to enforce exploration and quality checks through hook scripts.

### PreToolUse hooks

- `jcodemunch-guard.sh` blocks `Grep|Glob|Regex` when code exploration is attempted.
- `notation-guard.sh` validates paper-related Markdown edits for notation consistency.

### PostToolUse hooks

- Python file writes/edits trigger linting and formatting via `uv run ruff`.
- File writes trigger the mandatory research context header check.
- Writes under `results/` trigger a vault-sync reminder.

### Hook file locations

- `.claude/hooks/jcodemunch-guard.sh`
- `.claude/hooks/notation-guard.sh`
- `.claude/hooks/research-context-check.sh`
- `.claude/hooks/results-vault-reminder.sh`

### Purpose

Keep policy enforcement declarative and separate from long-form guidance.
The root policy file should only describe active requirements and refer to these specialized instruction files.
