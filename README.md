# TDL
<!-- 
GitHub Actions CI Badge (uncomment when workflow is active):
[![CI](https://github.com/stephendor/TDL/actions/workflows/ci.yml/badge.svg)](https://github.com/stephendor/TDL/actions/workflows/ci.yml)
-->

## Repository policy

This repository uses the `jcodemunch` MCP toolchain for code navigation and enforces code exploration policy through `.claude/settings.json` and hook scripts.

Key files:

- `.claude/CLAUDE.md` — root policy file for active guidance
- `.claude/instructions/tool-usage.instructions.md` — tool usage workflow
- `.claude/instructions/hook-enforcement.instructions.md` — enforcement hook rules
- `.cursor/rules/jcodemunch.mdc` — global code exploration policy
- `.claude/hooks/jcodemunch-guard.sh` — PreToolUse guard for Grep/Glob/Regex
