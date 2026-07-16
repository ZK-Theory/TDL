# TDL
<!-- 
GitHub Actions CI Badge (uncomment when workflow is active):
[![CI](https://github.com/stephendor/TDL/actions/workflows/ci.yml/badge.svg)](https://github.com/stephendor/TDL/actions/workflows/ci.yml)
-->

## Repository policy

This repository uses the built-in `Read`/`Grep`/`Glob` tools for code navigation and enforces quality checks through `.claude/settings.json` and hook scripts.

Key files:

- `.claude/CLAUDE.md` — root policy file for active guidance
- `.claude/instructions/tool-usage.instructions.md` — tool routing for code navigation
- `.claude/instructions/hook-enforcement.instructions.md` — enforcement hook rules
- `.claude/hooks/install-git-hooks.py` — verifies the repository's Git hooks are live

### Git hooks

Git hooks are tracked in `.githooks/` and the repository sets
`core.hooksPath=.githooks`, so every clone and linked worktree gets them from the
working tree — there is nothing to install. **Anything placed in `.git/hooks/` is
ignored by git: it does not error, it silently never runs.**

To verify the gate is actually live (exit 1 on any problem):

```bash
uv run python .claude/hooks/install-git-hooks.py
```

