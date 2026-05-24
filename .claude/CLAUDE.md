## Code Navigation Policy

Use Serena's MCP tools for code navigation in this repository. Reserve `Read` for files about to be edited, and `Grep`/`Glob` for non-symbol text or filesystem inventory.

See `.claude/instructions/tool-usage.instructions.md` for the tool routing table and fallback rules.

`Read` is permitted only after the target source file has been identified — typically just before `Edit`/`Write`. The agent harness requires a prior `Read` for `Edit`/`Write` to succeed.

## Hook Enforcement

This repository enforces quality rules through `.claude/settings.json` and hook scripts.
See `.claude/instructions/hook-enforcement.instructions.md` for:
- PostToolUse linting and formatting
- research-context and results-vault hooks

`.claude/settings.json` also provides Serena lifecycle support for session activation, pretool reminders, and cleanup.

## Repository Workflow

Long-form workflow and research convention guidance has been moved out of the root policy.
See:
- `.claude/instructions/workflow.instructions.md` — testing, experiments, paper workflows
- `.claude/instructions/vault-integration.instructions.md` — Obsidian vault sync workflows
- `.claude/instructions/research-context.instructions.md` — script headers and metadata
- `.claude/instructions/git.instructions.md` — git workflow and branching

## Related files
- Hook configuration: `.claude/settings.json`
- Notation guard: `.claude/hooks/notation-guard.sh`
- Research context check: `.claude/hooks/research-context-check.sh`
- Vault reminder: `.claude/hooks/results-vault-reminder.sh`
- Git policy guidance: `.claude/instructions/git.instructions.md`
- Git commit-msg helper: `.claude/hooks/git-commit-msg.sh`
