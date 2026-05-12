---
description: jcodemunch MCP tool usage for code exploration and repository navigation.
alwaysApply: true
---

## jcodemunch Tool Usage

Use jcodemunch MCP tools for all code navigation in this repository.

### Primary workflow

1. `resolve_repo { "path": "." }`
2. `suggest_queries`
3. `search_symbols(...)`
4. `search_text(...)`
5. `get_skeleton(...)`
6. `get_context_bundle(...)`
7. `read_file(...)` only when editing a specific file

### Allowed tools

- `resolve_repo`
- `suggest_queries`
- `search_symbols`
- `search_text`
- `get_skeleton`
- `get_context_bundle`
- `read_file` only for direct edits
- `run_in_terminal` only for implementation tasks, not codebase exploration

### Disallowed exploration

- grep
- glob
- Bash search
- manual file system traversal
- direct `cat`/`less` for code discovery

### Rationale

A dedicated toolchain keeps code navigation consistent and reduces context overload.
Detailed policy and enforcement are stored separately from the root CLAUDE file.
