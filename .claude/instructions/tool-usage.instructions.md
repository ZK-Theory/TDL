---
description: Serena MCP tool usage for code exploration and repository navigation.
alwaysApply: true
---

## Serena Tool Usage

Use Serena's MCP tools for code navigation in this repository. Reserve `Read` for files about to be edited, and `Grep`/`Glob` for non-symbol text or filesystem inventory.

### Tool routing

| Need | Tool |
|---|---|
| Symbol by name / kind | `mcp__serena__find_symbol` |
| Overview of a file's symbols | `mcp__serena__get_symbols_overview` |
| Substring or regex inside source files | `mcp__serena__search_for_pattern` |
| Where a symbol is referenced | `mcp__serena__find_referencing_symbols` |
| Insert before / after a symbol | `mcp__serena__insert_before_symbol` / `insert_after_symbol` |
| Replace a symbol's body | `mcp__serena__replace_symbol_body` |
| Replace file contents (regex) | `mcp__serena__replace_content` |
| LSP-level diagnostics for a file | `mcp__serena__get_diagnostics_for_file` |
| Rename a symbol across the codebase | `mcp__serena__rename_symbol` |
| Find symbol implementations | `mcp__serena__find_implementations` |
| Find symbol declaration | `mcp__serena__find_declaration` |

### Discovery flow

1. Unfamiliar repo → `mcp__serena__check_onboarding_performed`; if `false`, run `mcp__serena__onboarding`.
2. New file → `mcp__serena__get_symbols_overview` first.
3. Specific symbol → `mcp__serena__find_symbol` (use `name_path_pattern` like `Class/method` for nested symbols; `include_body=true` to fetch source).
4. Cross-symbol relationships → `find_referencing_symbols` / `find_implementations`.

### Read / Grep / Glob — fallback discipline

- `Read` is permitted **only after** the target file has been identified — typically just before `Edit`/`Write`. The agent harness requires a prior `Read` for `Edit`/`Write` to succeed.
- `Grep` and `Glob` remain available for: non-symbol text (config values, comments, markdown, notation), filesystem inventories, and as a fallback when Serena returns empty for a query you have strong reason to believe should match.
- `Bash` for code search (`grep`/`find`/`rg`) is **not** appropriate — use the typed tools above instead.

### When Serena is unavailable

Inside a worktree where the language server has not indexed the branch's files, or during a transient MCP-disconnected state, fall back to `Read` + `Grep` and note the gap in the Task Log so the tooling can be brought back into shape.

### After editing

If a file's symbol structure changes substantially (function added, signature changed, class moved), the next `find_symbol` call on that name path picks up the change without manual reindex. No `register_edit` step is required.
