## Code Navigation Policy

Always use jcodemunch MCP tools for code navigation in this repository.
Do not use grep, glob, Bash, or manual filesystem search to explore the codebase.

Use the tool workflow documented in `.claude/instructions/tool-usage.instructions.md`.

`Read` is permitted only after the target source file has been identified and the file is being edited.

## Hook Enforcement

This repository enforces exploration and quality rules through `.claude/settings.json` and hook scripts.
See `.claude/instructions/hook-enforcement.instructions.md` for:
- PreToolUse guard rules
- PostToolUse linting and formatting
- research-context and results-vault hooks

It also includes Serena lifecycle support in `.claude/settings.json` for session activation, pretool reminders, and cleanup.

## Repository Workflow

Long-form workflow and research convention guidance has been moved out of the root policy.
See:
- `.claude/instructions/workflow.instructions.md` — testing, experiments, paper workflows
- `.claude/instructions/session-routing.instructions.md` — confidence-level code exploration
- `.claude/instructions/vault-integration.instructions.md` — Obsidian vault sync workflows
- `.claude/instructions/research-context.instructions.md` — script headers and metadata
- `.claude/instructions/git.instructions.md` — git workflow and branching

## Related files
- Global code exploration policy: `.cursor/rules/jcodemunch.mdc`
- Hook configuration: `.claude/settings.json`
- Guard hook: `.claude/hooks/jcodemunch-guard.sh`
- Notation guard: `.claude/hooks/notation-guard.sh`
- Research context check: `.claude/hooks/research-context-check.sh`
- Vault reminder: `.claude/hooks/results-vault-reminder.sh`
- Git policy guidance: `.claude/instructions/git.instructions.md`
- Git commit-msg helper: `.claude/hooks/git-commit-msg.sh`
