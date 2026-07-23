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
(Note: The legacy "Graphify" / "Graphifyy" tool has been uninstalled. Do not attempt to use or refer to Graphifyy; always use Repowise.)

Use Repowise when the current runtime exposes its MCP tools and the task benefits from repository-level context:

- unfamiliar area orientation → `get_overview`
- conceptual questions → `get_answer`
- file/module/symbol context → `get_context`
- bounded symbol source → `get_symbol`
- architectural rationale → `get_why`
- risky changes or review → `get_risk`
- cleanup planning → `get_dead_code`

If Repowise MCP tools are not exposed in the current session, continue with the built-in navigation tools. Do not invent tool calls. Repowise output is an index, so verify against actual files before editing or making claims about precise source behavior.

### New linked-worktree Repowise bootstrap

Every newly created linked worktree must initialize its own Repowise index
before repository-level navigation. Run this from the new worktree root after
copying `.env` and verifying the attached branch:

```powershell
repowise init --index-only --yes --no-agents --no-codex --no-onboarding
repowise status
```

Use the explicit flags: plain `repowise init` opens an interactive selector and
aborts in non-interactive agent sessions. Before initialization, capture
`git status --short`. Repowise may rewrite worktree-local integration paths in
`.claude/CLAUDE.md`, `.mcp.json`, and `.repowise/mcp.json` even with the
suppression flags. Treat those rewrites as setup state, never task output: do
not stage or commit them, and restore only files proven clean before the init
once the worktree session has loaded its MCP configuration.

The MCP configuration uses the current working directory, so Repowise will automatically serve the main branch's index when started in a newly created worktree. This main-branch index is perfectly valid and encouraged for read-only codebase navigation, orientation, and symbol lookup, as the vast majority of the architecture remains identical.

You do not need to re-initialize Repowise or verify binding just to read the codebase. Only run `repowise init` if you are about to make sweeping architectural changes in the worktree and need the index to reflect those local, uncommitted changes.

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

## Windows linked-worktree sandbox routing

On Windows, treat every linked Git worktree as a separate sandbox root even
when its path is lexically inside an allowed checkout such as
`C:\Users\steph\TDL\.apm\worktrees\...`. Parent-directory containment does
not prove edit authority.

Before any worktree write:

An explicit user instruction to create a named worktree is authority for that
requested `git worktree add` and environment bootstrap only. Code, test, and
result writes inside the new worktree remain subject to the exact-root
authorization checks below.

1. Compare the resolved target worktree with the runtime's declared
   `workspace_roots` / `writable_roots`. If the exact worktree is not an
   authorized root, do **not** call `Edit`, `Write`, `apply_patch`, or perform
   a disposable write probe; that failure is predictable and is not useful
   diagnostics.
2. Route code or test remediation to a task whose workspace is that exact
   worktree. The owning task must verify cwd, branch, and edit readiness before
   changing files. A Manager may inspect a foreign worktree read-only, but must
   send fixes back to its owner or start a correctly rooted task.
3. For a bounded text-only change on an existing remote branch, when remote
   mutation is already authorized, the Manager may use an exact-SHA GitHub
   Contents transaction: fetch branch/file SHA, update that one path, refetch,
   and compare. Do not use this route for changes whose validation requires
   local code execution.
4. Never bypass the split-root denial with shell redirection, base64 payloads,
   `git apply`, or another write mechanism. If neither an owning task nor the
   bounded remote-text route is available, stop once and report the routing
   requirement instead of retrying editors.

### Codex app detached-start protocol

Codex app-created worktrees commonly start at a detached `HEAD`, including
when the task was created from an existing branch ref. A matching starting ref
selects the commit; it does not guarantee symbolic branch attachment.

For every Codex worktree dispatch that will write:

1. The dispatcher should pre-create one unique task branch at the intended
   commit when practical, so the Worker never needs to invent or rename a
   branch inside the linked worktree.
2. The startup prompt must **not** require the worktree to be already attached
   and must **not** forbid the exact attachment operation. It must permit one
   deterministic `git switch <pre-created-task-branch>` attempt when `HEAD` is
   detached, after verifying that detached `HEAD` and the branch ref resolve to
   the same required commit.
3. After the switch, verify the symbolic branch, `HEAD`, cwd, and status before
   any file write. Do not create a fallback branch, rename a branch, or switch
   to a different commit.
4. If that single attachment attempt fails because the linked-worktree Git
   metadata is not writable, stop and report the exact Git path/error. Do not
   mistake the normal detached start itself for a blocker, and do not retry or
   bypass an actual metadata denial.

## Version control

- Use the project research prefix convention for every commit subject: `[RESULT]`, `[DECISION]`, `[NEGATIVE]`, `[PIPELINE]`, `[DATA]`, or `[EXPLORE]`, followed by the paper identifier such as `P01-A:`. Never use a bare task-management or generic implementation subject when committing Worker output.
- When a task prompt specifies an allowed prefix family, choose from that family and keep the subject within the same project convention.

## After editing

If a file's structure changes substantially (function added, signature changed, class moved), no re-index step is needed — the next `Grep` or `Read` picks up the change directly from disk.

