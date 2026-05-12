---
description: jcodemunch MCP tool usage for code exploration and repository navigation.
alwaysApply: true
---

## jcodemunch Tool Usage

Use jcodemunch MCP tools for all code navigation in this repository.

### Session-Aware Routing

**Opening move for any task:**
1. `plan_turn { "repo": "...", "query": "your task description", "model": "claude-sonnet-4-20250514" }`
2. Obey the confidence level:
   - `high` → go directly to recommended symbols, max 2 supplementary reads
   - `medium` → explore recommended files, max 5 supplementary reads  
   - `low` → the feature likely doesn't exist. Report the gap to the user.

### Primary Workflow

1. `resolve_repo { "path": "." }` — confirm project is indexed
2. `suggest_queries` — when repo is unfamiliar
3. `plan_turn(...)` — get confidence + recommended files
4. `search_symbols(...)` — symbol by name (add `kind=`, `language=`, `file_pattern=`, `decorator=`)
5. `search_text(...)` — string, comment, config value (supports regex, `context_lines`)
6. `get_file_outline(...)` — before opening any file
7. `get_skeleton(...)` — compact file inspection 
8. `get_context_bundle(...)` — symbol + its imports
9. `Read(...)` — only when editing a specific file

### Complete Tool Inventory

**Discovery & Planning:**
- `resolve_repo` — confirm project indexed
- `suggest_queries` — get orientation suggestions
- `plan_turn` — task planning with confidence levels
- `get_repo_outline` — dirs, languages, symbol counts
- `get_file_tree` — file layout, filter with `path_prefix`

**Symbol Search:**
- `search_symbols` — find symbols by name, decorator, kind, language
- `search_text` — full-text search with regex support
- `search_columns` — database columns (dbt/SQLMesh)

**Code Reading:**
- `get_file_outline` — symbol overview before reading
- `get_skeleton` — compact symbol signatures 
- `get_symbol_source` — full symbol source code
- `get_context_bundle` — symbol + imports in one call
- `get_file_content` — specific line ranges only

**Relationships & Impact:**
- `find_importers` — what imports this file
- `find_references` — where is this identifier used
- `check_references` — is this identifier used anywhere
- `get_dependency_graph` — file dependency relationships
- `get_blast_radius` — what breaks if I change X
- `get_changed_symbols` — what symbols changed since last commit
- `find_dead_code` — find unreachable/unused code
- `get_class_hierarchy` — inheritance relationships

**Analysis & Validation:**
- `get_call_hierarchy` — caller/callee relationships
- `get_impact_preview` — what breaks if symbol removed
- `find_implementations` — concrete implementations of interface/abstract

### After Editing Files

- If PostToolUse hooks are installed, edited files are auto-reindexed
- Otherwise, call `register_edit` with edited file paths to invalidate caches
- For bulk edits (5+ files), always use `register_edit` with all paths

### Token Efficiency

- If `_meta` contains `budget_warning`: stop exploring, work with what you have
- If `auto_compacted: true`: results were compressed due to turn budget
- Use `get_session_context` to check what you've already read

### Disallowed Exploration

- grep
- glob  
- Bash search
- manual file system traversal
- direct `cat`/`less` for code discovery

### Interpreting Search Results

- If `search_symbols` returns `negative_evidence` with `verdict: "no_implementation_found"`:
  - Do NOT re-search with different terms
  - DO report: "No existing implementation found for X. This would need to be created."
- If `verdict: "low_confidence_matches"`: examine matches critically
