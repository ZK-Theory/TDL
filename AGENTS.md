## Code Exploration Policy

Use Serena's MCP tools for code navigation. Reserve `Read` for files about to be edited, and `Grep`/`Glob` for non-symbol text or filesystem inventory.

**Exception:** `Read` is permitted only after the target file has been identified — typically just before `Edit`/`Write`. The agent harness requires a prior `Read` for `Edit`/`Write` to succeed.

**Finding code:**
- symbol by name / kind → `mcp__serena__find_symbol` (use `name_path_pattern` like `Class/method`; `include_body=true` for source; `include_kinds` to filter by LSP kind)
- overview of a file's symbols → `mcp__serena__get_symbols_overview`
- substring or regex inside source files → `mcp__serena__search_for_pattern` (or `Grep` for non-code text such as markdown, configs, notes)
- where a symbol is referenced → `mcp__serena__find_referencing_symbols`
- implementations of an interface / abstract method → `mcp__serena__find_implementations`
- symbol declaration → `mcp__serena__find_declaration`

**Editing code via symbols:**
- insert before / after a symbol → `mcp__serena__insert_before_symbol` / `insert_after_symbol`
- replace a symbol's body → `mcp__serena__replace_symbol_body`
- rename a symbol across the codebase → `mcp__serena__rename_symbol`
- replace file contents via regex → `mcp__serena__replace_content`

**Repo orientation:**
- new file → `mcp__serena__get_symbols_overview` before any detailed inspection
- unfamiliar repo → `mcp__serena__check_onboarding_performed`; if `false`, run `mcp__serena__onboarding`

**LSP diagnostics:**
- `mcp__serena__get_diagnostics_for_file` returns LSP-level warnings/errors for a file (more accurate than running the linter manually for type/import issues).

## When Serena is unavailable

Inside a worktree where the language server has not indexed the branch's files, or during a transient MCP-disconnected state, fall back to `Read` + `Grep` and note the gap in the Task Log so the tooling can be brought back into shape.

## Fallbacks

- `Grep` and `Glob` remain available for: non-symbol text (config values, comments, markdown, notation), filesystem inventories, and as a fallback when Serena returns empty for a query you have strong reason to believe should match.
- `Bash` for code search (`grep`/`find`/`rg`) is **not** appropriate — use the typed tools above instead.
