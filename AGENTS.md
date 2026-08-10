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

Before any worktree write, resolve authority from the complete runtime permission
model and the user's exact instruction:

- A runtime permission profile that explicitly disables filesystem sandboxing or
  declares unrestricted filesystem access authorizes writes in a resolved linked
  worktree. In that runtime, `workspace_roots` / `writable_roots` describe the
  task's primary context; absence from those lists is not an edit denial.
- When sandbox/root enforcement is active, the exact linked-worktree root must be
  present in the enforced writable roots (or be separately granted by the
  runtime) before code, test, or result writes.
- An instruction merely to create a named worktree authorizes `git worktree add`
  and environment bootstrap only. An owner instruction that explicitly calls the
  named linked worktree **writable**, directs implementation in it, or says to
  create or use it for the assigned delivery grants task and scope authority for
  the requested code, test, and result writes. It does not expand an enforced
  filesystem sandbox; when enforcement is active, the runtime must separately
  grant write capability for the exact linked-worktree root.

1. Verify the resolved cwd, symbolic branch, HEAD, required ancestry, status,
   runtime permission profile, and the exact wording of the owner instruction.
   Do not infer a denial from contextual root lists when sandbox enforcement is
   explicitly disabled or unrestricted access is declared.
2. If enforced roots genuinely exclude the worktree and no explicit runtime
   grant covers implementation there, route code or test remediation to a
   task whose workspace is that exact worktree. The owning task must verify cwd,
   branch, and edit readiness before changing files. A Manager may inspect a
   genuinely foreign, non-writable worktree read-only, but must send fixes back
   to its owner or start a correctly rooted task.
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

- For stacked or dependent work, verify both the symbolic branch and its
  ancestry before any write. Require
  `git merge-base --is-ancestor <expected-base> HEAD` to exit zero; a plausible
  branch name does not prove that prerequisite work is present.
- Use the project research prefix convention for every commit subject: `[RESULT]`, `[DECISION]`, `[NEGATIVE]`, `[PIPELINE]`, `[DATA]`, or `[EXPLORE]`, followed by the paper identifier such as `P01-A:`. Never use a bare task-management or generic implementation subject when committing Worker output.
- When a task prompt specifies an allowed prefix family, choose from that family and keep the subject within the same project convention.

## Capability-first delivery

For implementation and operational campaigns, the user's named end-to-end
capability is the governing deliverable. A slice, foundation, mechanism, schema,
test harness, review, PR, or handoff is an internal delivery unit; completing one
does not make the capability complete.

### Capability contract and status

- Begin with one observable outcome through the real production or public seam.
  Name the entry point, durable effects, returned result, and decisive failure
  behavior. Build the thinnest real positive path before expanding assurance.
- Use these campaign states: `NOT RUNNABLE`, `RUNNABLE`, `PROVEN`, `INTEGRATED`,
  and `OWNER-BLOCKED`. `OWNER-BLOCKED` is not success; use it only after all
  safe authorized work is exhausted and name the exact missing owner action.
- Until the capability is `INTEGRATED`, every progress report and handoff must
  lead with `Capability status: INCOMPLETE - <exact functional gap>`. If
  integration is outside the authorized task boundary, `PROVEN` may close that
  task, but the campaign remains incomplete and the handoff must say so.
- Qualify local words such as "complete", "accepted", "ready", and "done" with
  their object. For example, "schema slice accepted; capability NOT RUNNABLE" is
  valid; an unqualified "complete" is not.

### Execution and scope

- Slices and PRs may bound edits or external review size, but the same campaign
  continues across them until the named capability reaches its terminal state.
- A dependency discovered to be necessary for the capability remains part of
  the campaign. Classify discoveries as required capability work, owner-only,
  external, or unrelated. Implement required work within the authorized scope;
  a PR comment, plan, handoff, or unnamed successor is not its disposition.
- Start a fresh semantic subject only when observable behavior materially
  changes, accepted or protected bytes change, authority expands, the work is
  genuinely outside the named capability, or final review independence requires
  it. Do not manufacture a new subject merely because another construction step
  or defect was found.
- Missing code, mappings, producers, writers, reducers, projections, records,
  tests, or recovery paths are implementation work, not owner stops. Stop only
  for a missing owner decision, missing authority for destructive or external
  action, required mutation of protected bytes, an unresolved writable-root or
  exact-subject boundary, or a demonstrated contradiction in authoritative
  contracts.
- Existing accepted plans govern execution. Do not create another plan or
  mechanics-only package when the next production action is known.

### Review and validation

- During construction, use direct tests and review proportionate to the changed
  behavior. Do not require an independent acceptance review for every foundation
  step. Form an integrated capability candidate, exercise the end-to-end path,
  then perform the required final independent review and bounded remediation.
- Multiple PRs are allowed when dependency boundaries or external-review caps
  require them. PR acceptance is an integration milestone, not campaign
  completion; verify the assembled capability after the final seam lands.
- Synthetic harnesses and mechanics proofs may support assurance but cannot
  substitute for a real positive path. Validate in this order: real positive
  path, decisive no-corruption negatives, shared-seam regression, then any
  explicitly mandated final gate suite once at candidate head.
- Preserve exact-head review identity and owner-controlled external-review
  operations. A later commit invalidates prior exact-head review evidence, but
  that identity rule must not be used to force unrelated repeated reviews during
  construction.

### Delivery budget and anti-stall rule

- Default at least 80% of campaign effort to production capability and direct
  tests, at most 10% to orthogonal assurance without a concrete failure path,
  and at most 10% to planning, handoff, and review administration. Audit actual
  efficiency from session and billing telemetry; do not rely on producer
  self-estimates.
- If two hours pass without an observable production, integration, or real-
  operation delta, stop meta-work and take the next production action. If that
  action is truly blocked, report the exact blocker and the authority needed.
- Plans, schemas without an active producer, mechanics-only harnesses, synthetic
  evidence, green tests that do not exercise the named outcome, accepted
  fragments, intermediate PRs, and handoffs receive no capability-completion
  credit.
- Progress reports must state, in order: capability state, completed end-to-end
  path, exact remaining functional gap, and next production action.

## Jira work control

Jira is the live work-control surface, not a dumping ground or retrospective
activity log. Repository contracts define the technical truth; the canonical
Jira capability issue must translate that truth into current executable
direction and be updated whenever evidence changes.

- Organise delivery as campaign/program -> named capability -> bounded job.
  Keep the capability issue open across all slices, PRs, reviews, and jobs.
- Every open capability issue begins with: `Capability status`, observable
  outcome through the real seam, completed production path, exact remaining
  functional gap, next production action, authoritative repository sources,
  required closure evidence, and owner-only actions.
- `In Progress` means a named production or integration job is actively being
  executed. If work is stopped or owner-paused, transition it out of
  `In Progress` immediately, label the pause, and record the exact resume action.
- `Done` on a capability means `INTEGRATED`: the real path and decisive
  negatives passed, required review/owner evidence is linked, and no required
  child or blocker remains open. A completed assessment, plan, schema, harness,
  foundation, PR, or review is a typed milestone, not a completed capability.
- Mark non-capability terminal work explicitly as `MILESTONE`, `SUPERSEDED`,
  `NEGATIVE ASSESSMENT`, `DUPLICATE`, or `CANCELLED` in its summary/labels and
  point to the live canonical capability. Never use an unqualified `Done` to
  carry these different meanings.
- Required work discovered during delivery becomes a visible bounded job under
  the same capability. A comment, review finding, handoff, or "later subject"
  does not dispose it; name an owner and next action or keep the capability gap
  explicit.
- Treat descriptions and structured parent/dependency fields as one authority.
  Validate `Blocks` direction by reading both endpoints after writes. Do not
  leave a parent terminal while required descendants remain open, and do not
  preserve contradictory links as harmless history.
- Jira comments are chronological evidence only. They cannot override the
  current description, capability state, acceptance contract, or repository
  authority. Fold decisions into the description and retain the comment as
  provenance.
- After Jira edits or transitions, read back every changed issue and its links.
  Report exact failures; never claim a hierarchy, status, or dependency update
  from an attempted write alone.

## Large-workflow context discipline

Use `tda-large-workflow-supervision` as the single canonical operating procedure
for standalone multi-stage, review-heavy campaigns. The guide at
`docs/guides/large-workflow-supervision.md` contains examples only. Do not treat
estimated token thresholds, fixed skill counts, or producer self-reporting as
evidence of token efficiency; audit that separately from session JSONL and
billing/token telemetry.

## After editing

If a file's structure changes substantially (function added, signature changed, class moved), no re-index step is needed — the next `Grep` or `Read` picks up the change directly from disk.
