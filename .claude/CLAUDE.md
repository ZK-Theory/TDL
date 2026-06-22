## Code Navigation Policy

Use the built-in `Read`, `Grep`, and `Glob` tools for code navigation in this
repository. `Read` is permitted once the target source file has been
identified — typically just before `Edit`/`Write` (the agent harness requires
a prior `Read` for `Edit`/`Write` to succeed). Do not use Bash
`grep`/`rg`/`find` for code search. For large multi-step searches, spawn an
`Explore` subagent.

See `.claude/instructions/tool-usage.instructions.md` for the tool routing
table and discipline notes.

## Hook Enforcement

This repository enforces quality rules through `.claude/settings.json` and
hook scripts. See `.claude/instructions/hook-enforcement.instructions.md` for
PostToolUse linting/formatting and the research-context and results-vault
hooks.

## Repository Workflow

Long-form workflow and research convention guidance:

- `.claude/instructions/workflow.instructions.md` — testing, experiments, paper workflows
- `.claude/instructions/vault-integration.instructions.md` — Obsidian vault sync
- `.claude/instructions/research-context.instructions.md` — script headers and metadata
- `.claude/instructions/git.instructions.md` — git workflow and branching

Path-scoped rules (lazy-loaded): `.claude/rules/` — `papers.md`,
`vault-templates.md`, `python.md`, `apm-outputs.md`, `deep-learning.md`.

## Related files

- Hook configuration: `.claude/settings.json`
- Hook scripts: `.claude/hooks/` (notation-guard, results-no-overwrite,
  dispatch-readiness-guard, research-context-check, results-vault-reminder,
  git-commit-msg)
