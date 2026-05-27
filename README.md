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
- `.claude/hooks/install-git-hooks.py` — installs repository Git hooks

### Git hook installation

To enable commit prefix enforcement, run:

```bash
python .claude/hooks/install-git-hooks.py
```

