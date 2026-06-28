# AGENTS.md — Code Navigation Policy

This repository uses the built-in `Read`, `Grep`, and `Glob` tools for baseline code navigation. It also configures a Repowise MCP server for codebase intelligence when the agent runtime exposes those tools.

## Tool routing

| Need | Tool |
|---|---|
| Read a file with a known path | `Read` |
| Search file contents (symbol names, strings, regex) across the repo | `Grep` |
| List files by name pattern (e.g. `**/*.py`) | `Glob` |
| Filesystem inventory (directory listing) | `Glob` |
| Edit an existing file | `Edit` (must be preceded by `Read` of that file) |
| Create / fully overwrite a file | `Write` |
| Architecture/context/risk when Repowise MCP tools are available | Repowise MCP (`get_overview`, `get_answer`, `get_context`, `get_symbol`, `get_risk`, etc.) |

## Repowise MCP

Repowise is configured in `.mcp.json`, `.repowise/mcp.json`, and the relevant Claude user/desktop MCP configs.

Use Repowise when the current runtime exposes its MCP tools and the task benefits from repository-level context:

- unfamiliar area orientation → `get_overview`
- conceptual questions → `get_answer`
- file/module/symbol context → `get_context`
- bounded symbol source → `get_symbol`
- architectural rationale → `get_why`
- risky changes or review → `get_risk`
- cleanup planning → `get_dead_code`

If Repowise MCP tools are not exposed in the current session, continue with the built-in navigation tools. Do not invent tool calls. Repowise output is an index, so verify against actual files before editing or making claims about precise source behavior.

## Discovery flow

1. Unfamiliar repo → use Repowise `get_overview` when available; otherwise start with `Glob "**/*.py"` plus `Glob "**/*.md"` for orientation.
2. Looking for a specific symbol → use Repowise `get_context` / `get_symbol` when available; otherwise `Grep` for the symbol name with context.
3. About to edit a file → `Read` it first, then `Edit`.
4. Cross-symbol relationships (callers, implementations) → `Grep` for the symbol name; the match list identifies the call sites.

## Discipline

- `Read` is for files you already have a path for. Don't use it to "explore" — start with `Glob` / `Grep`.
- `Grep` is the canonical content-search fallback when Repowise MCP tools are unavailable. Avoid shell search for code navigation when typed navigation tools are available.
- `Glob` matches by pathname only — for content matching, use `Grep` with the `glob` parameter to restrict by path pattern.
- For large multi-step searches (more than a few rounds of grep/read), spawn an `Explore` subagent rather than burning the main context.

## Version control

- Use the project research prefix convention for every commit subject: `[RESULT]`, `[DECISION]`, `[NEGATIVE]`, `[PIPELINE]`, `[DATA]`, or `[EXPLORE]`, followed by the paper identifier such as `P01-A:`. Never use a bare task-management or generic implementation subject when committing Worker output.
- When a task prompt specifies an allowed prefix family, choose from that family and keep the subject within the same project convention.

## After editing

If a file's structure changes substantially (function added, signature changed, class moved), no re-index step is needed — the next `Grep` or `Read` picks up the change directly from disk.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **TDL** (14245 symbols, 23644 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/TDL/context` | Codebase overview, check index freshness |
| `gitnexus://repo/TDL/clusters` | All functional areas |
| `gitnexus://repo/TDL/processes` | All execution flows |
| `gitnexus://repo/TDL/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
