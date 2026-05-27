---
description: Code navigation policy — Read for known paths, Grep for content, Glob for filenames.
alwaysApply: true
---

## Code Navigation Policy

This repository uses the built-in `Read`, `Grep`, and `Glob` tools for code navigation. There is no symbol-level MCP server in use.

### Tool routing

| Need | Tool |
|---|---|
| Read a file with a known path | `Read` |
| Search file contents (symbol names, strings, regex) across the repo | `Grep` |
| List files by name pattern (e.g. `**/*.py`) | `Glob` |
| Filesystem inventory (directory listing) | `Glob` |
| Edit an existing file | `Edit` (must be preceded by `Read` of that file) |
| Create / fully overwrite a file | `Write` |

### Discovery flow

1. Unfamiliar repo → start with `Glob "**/*.py"` (or the relevant extension) plus `Glob "**/*.md"` for documentation.
2. Looking for a specific symbol → `Grep` for the symbol name with `type` filter (`type: "py"`, `type: "rust"`, etc.). Use `output_mode: "content"` with `-n` and `-C 2` for context.
3. About to edit a file → `Read` it first, then `Edit`.
4. Cross-symbol relationships (callers of a function, implementations of an interface) → `Grep` for the symbol name; review match list to identify call sites.

### Discipline

- `Read` is for files you already have a path for. Don't use it to "explore" — start with `Glob` / `Grep`.
- `Grep` is the canonical content-search tool. Do **not** use `Bash` (`grep` / `rg` / `find`) for code search — the typed tool is faster, sandboxed, and integrates with the agent harness.
- `Glob` matches by pathname only — for content matching, use `Grep` with the `glob` parameter to restrict by path pattern.
- For large multi-step searches (more than a few rounds of grep/read), spawn an `Explore` subagent rather than burning the main context.
