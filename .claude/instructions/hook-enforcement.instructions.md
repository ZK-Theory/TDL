---
description: Hook enforcement rules for repository PreToolUse and PostToolUse behavior.
alwaysApply: true
---

## Hook Enforcement

This repository uses `.claude/settings.json` to enforce quality checks through hook scripts.

### PreToolUse hooks

- `notation-guard.sh` validates paper-related Markdown edits for notation consistency against `papers/shared/notation.md`.
- `results-no-overwrite.sh` blocks in-place overwrite/edit of an existing date-suffixed results file (`results/**/*.{json,npy,npz}`).
- `dispatch-readiness-guard.sh` blocks a Manager Task Prompt bus write (`.apm/bus/<agent>/task.md`) whose `## Dispatch Readiness` block is absent or FAIL. The block is the pasted output of `shared/manager_dispatch_check.py` (worktree+`.env`, contracts, input-provenance, cleared report bus). This makes the dispatch-readiness discipline survive context compaction — the procedure in `task-assignment.md` §3.3 is lazy-loaded and may drop out of context, but the hook fires at the write regardless.
- `mirror-tree-guard.sh` blocks an agent `Write`/`Edit`/`MultiEdit` whose target resolves inside the Claude-side **mirror** skill tree (`.claude/skills/…`). Skills are authored only in `.agents/skills/` (the single source of truth) and byte-mirrored into `.claude/skills/` by `tools/sync_agent_skills.py` (pre-commit Gate 0); a direct edit to the mirror is silently overwritten — or reverses a newer authoring-tree fix — at the next sync. The match is separator-agnostic (`/` and `\`) and prefix-agnostic, so worktree paths (`.apm/worktrees/<wt>/.claude/skills/…`) and absolute Windows paths are caught. The sync tool itself writes via Python (`shutil.copy2`), not an agent tool, so it never reaches this hook and is unaffected. The hook converts a rule that previously lived only in skill prose (`tda-skill-authoring-workbench`, `tda-agent-safety-guardrails`) into a tool-call boundary — SKL-4, 2026-07-21.

### PostToolUse hooks

- Python file writes/edits trigger linting and formatting via `uv run ruff`.
- File writes trigger the mandatory research-context header check (`research-context-check.sh`).
- Writes under `results/` trigger a vault-sync reminder (`results-vault-reminder.sh`).

### Hook file locations

- `.claude/hooks/notation-guard.sh`
- `.claude/hooks/results-no-overwrite.sh`
- `.claude/hooks/dispatch-readiness-guard.sh`
- `.claude/hooks/mirror-tree-guard.sh`
- `.claude/hooks/research-context-check.sh`
- `.claude/hooks/results-vault-reminder.sh`

### Purpose

Keep policy enforcement declarative and separate from long-form guidance.
The root policy file should only describe active requirements and refer to these specialized instruction files.
