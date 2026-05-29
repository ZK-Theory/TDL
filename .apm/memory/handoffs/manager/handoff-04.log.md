---
agent: manager
outgoing: 4
incoming: 5
handoff: 4
stage: 1
---

# Manager Handoff 4 (Manager 4 -> Manager 5)

## Summary

This Manager 4 instance picked up from Manager 3's handoff with T1.37
reissue pending after the T1.36 frozen-loadings and p-value-denominator
corrective work had landed. The session then covered three broad threads:

- T1.37 reissue setup and continuation.
- APM + Superpowers + TDL research-assurance workflow design.
- Tooling cleanup around LSP/Serena/jCodemunch remnants and Repowise MCP setup.

Auto-compaction occurred before this handoff was written. The late-session
state was reconstructed from the compaction summary, then verified against the
live Tracker, current Task Bus, T1.37 Task Logs, git state, and active job
status files before this handoff was created.

**Stages coordinated:** Stage 1 remained active throughout. Stage 0 T0.3
remained paused and did not block Stage 1. Stage 2/3/4 work was not dispatched
in this instance.

**Tasks reviewed:** No completed Worker report was reviewed by this Manager
instance. T1.37 remained active, and `.apm/bus/tda-agent/report.md` was empty at
handoff creation.

**Dispatch / continuation cycles completed:**

- T1.37 was recreated from a clean worktree after the User selected
  remove/recreate rather than preserving the stale dirty worktree.
- The T1.37 Task Prompt was updated to include the T1.2/T1.36 p-value
  denominator cleanup layer, frozen rerun requirements, comparison-table
  requirements, and contract/schema obligations.
- Incoming `tda-agent` instance 2 picked up from the staged Worker handoff and
  continued T1.37 execution.

## Working Context

### Tracked Worker Handoffs

| Agent | Handoff Stage | Current-Stage logs loaded | Notes |
|---|---|---|---|
| tda-agent | 1 -> 2 processed by Worker side | `.apm/memory/stage-01/task-01-37.log.md`, `.apm/memory/stage-01/task-01-37.jobs.md` | Worker instance 2 rebuilt from `.apm/memory/handoffs/tda-agent/handoff-01.log.md`, cleared the Worker Handoff Bus, and continued T1.37. The old handoff described stale dirty-worktree state; the active Task Prompt corrected it by stating that the worktree had been removed/recreated fresh. |

No other Worker handoffs were processed. `panel-statistics-agent`,
`academic-writing-agent`, and `reproducibility-agent` remained idle.

### T1.37 Work Performed During This Instance

The Manager updated the active T1.37 prompt so the Worker would execute:

- frozen-loadings reruns for T1.2a/b/c/d/f and T1.3;
- cache-based p-value denominator cleanup for provisional pre-fix outputs;
- a three-layer provisional/cache-corrected/frozen comparison table;
- P01-A and P01-B disclosure note drafts;
- vault `[RESULT]` and `[DECISION]` entries;
- active binding tests for the T1.37 contracts.

The Worker then advanced T1.37 materially:

- Cleared pending flags from T1.37 contracts after adding bindings.
- Patched stratified Markov-1 runner support for `--frozen-loadings`.
- Patched frozen Stage-1 output/cache naming so `_frozen_` paths were explicit.
- Completed smoke validation.
- Completed cache-based denominator cleanup:
  `results/trajectory_tda_integration/stage1/pvalue_denominator_cleanup_2026-05-28.json`.
  It included 12 recomputed cells, 8 unrecoverable LM cells, and 0 rejection
  direction changes at alpha 0.05.
- Committed intermediate branch state at `2d1b21b`
  (`[RESULT] P01: denominator cleanup and frozen rerun contracts`).
- Reran corrected frozen job-01 USoc headline:
  `results/trajectory_tda_integration/stage1/usoc_headline_frozen_2026-05-28.json`.
  It recorded `frozen_loadings=true`, `B=1000`, `pvalue_null_draws=1000`,
  and all four headline p-values at `0.000999000999000999`.
- Reran corrected frozen job-02 BHPS headline:
  `results/trajectory_tda_bhps/stage1/bhps_headline_frozen_2026-05-28.json`.
  It recorded `frozen_loadings=true`, `B=1000`, `pvalue_null_draws=1000`,
  H0 W2 / H0 landscape / H1 landscape at `0.000999000999000999`, and H1 W2
  at `0.01898101898101898`.
- Reran corrected frozen job-03 USoc LM L=2500:
  `results/trajectory_tda_integration/stage1/lm_sensitivity_L2500_frozen_2026-05-28.json`.
  It recorded `frozen_loadings=true`, `B=1000`, `pvalue_null_draws=1000`,
  and all four LM p-values at `0.000999000999000999`.
- Committed corrected job-01/job-02/job-03 outputs at `f3ae454`
  (`[RESULT] P01: frozen headline and L2500 reruns`).
- Launched corrected frozen job-04 USoc LM L=8000 at 2026-05-28 14:25:19
  as PID `29600`.

The Worker had not yet produced the job-04 output or a Task Report when this
handoff was written.

### APM / Superpowers / Research-Assurance Framework Work

The session preserved and committed the broader workflow architecture for
integrating APM with Superpowers and TDL research assurance.

Committed mainline work:

- `59b0c16` added local APM skills/guides and related handoff/session artifacts.
- `80ee41b` (`[PIPELINE] APM: add research assurance workflow plans`) added:
  - `.agents/skills/research-assurance-triage/SKILL.md`;
  - `.apm/memory/plans/2026-05-28-apm-research-assurance-integration.md`;
  - `.apm/memory/plans/2026-05-28-manager-research-assurance-workflow.md`;
  - `.apm/memory/plans/2026-05-28-worker-research-assurance-workflow.md`;
  - `.apm/memory/plans/2026-05-28-tdl-research-skillset-design.md`;
  - matching `docs/superpowers/plans/...` mirrors;
  - APM guide updates in `.codex/apm-guides/task-assignment.md`,
    `.codex/apm-guides/task-review.md`,
    `.codex/apm-guides/task-execution.md`, and
    `.codex/apm-guides/task-logging.md`;
  - a `CLAUDE.md` pointer to the research-assurance workflow.

The durable recovery anchor was:

` .apm/memory/plans/2026-05-28-apm-research-assurance-integration.md`

The intended next incremental test was T1.37 review. The hook backlog was
deliberately deferred until after T1.37 exposed which review gaps were recurring
and expensive to check manually.

### Tooling Cleanup And Repowise Work

Earlier cleanup removed the LSP enforcement kit and Serena remnants. In this
session, additional stale jCodemunch sources were removed after the User noticed
the old tool being mentioned again:

- User-level Claude hooks in `C:\Users\steph\.claude\settings.json` had seven
  `jcodemunch-mcp` hook commands removed.
- User-level `C:\Users\steph\.claude.json` had the `jcodemunch` MCP server
  entry removed.
- The TDL Claude project memory entry that instructed agents to use
  jCodemunch/vexp was removed.
- User-level Codex hooks in `C:\Users\steph\.codex\hooks.json` had three
  `jcodemunch-mcp` hook commands removed.
- Active config searches found no remaining active jCodemunch references after
  cleanup. Historical `.apm` logs, backups, and session histories were left
  untouched.

Repowise troubleshooting established:

- `repowise` was on PATH at `C:\Users\steph\.local\bin\repowise.exe`, version
  `0.13.0`.
- Direct MCP stdio handshake succeeded; the server reported `repowise`
  version `1.27.1` and exposed tools such as `get_answer`, `get_context`,
  `get_symbol`, `get_risk`, `search_codebase`, `get_overview`, `get_why`,
  `get_dead_code`, and `get_health`.
- This already-running Codex session still could not expose Repowise tools
  natively; the likely cause was that native MCP tools are loaded at session
  start. Fresh sessions should see the configured server.
- `repowise status .` was up to date at `80ee41b`, with `1137 files`,
  `4768 symbols`, and `303 docs`.
- `repowise doctor .` still reported coordinator drift
  (`SQL=303`, `Vector=379`, `Drift=25.1%`), but after reindex the vector count
  corresponded to 303 wiki pages plus 76 decision records, so this looked like
  a doctor-count mismatch rather than missing vector data.
- `repowise reindex` initially failed because proxy environment variables
  pointed to `127.0.0.1:9`; with proxies cleared it completed and indexed
  379 items.
- `.repowise-workspace.yaml` was created and `.repowise/mcp.json` existed as
  the shareable MCP config.

## Version Control Snapshot

Base branch `main` was at `80ee41b` when this handoff was written.

Active branches/worktrees observed:

| Branch | Worktree | Status |
|---|---|---|
| `main` | `C:\Users\steph\TDL` | Dirty with Repowise/tooling edits and LSP-kit deletion. |
| `run/headline-batch-frozen-pca-rerun` | `.apm/worktrees/run-headline-batch-frozen-pca-rerun` | Active T1.37 branch at `f3ae454`, two commits ahead of main; job-04 running. |
| `pipe/two-machine-check` | `.apm/worktrees/pipe-two-machine-check` | T0.3 paused awaiting second-machine canary file. |
| `run/tier3-regression` | `.apm/worktrees/run-tier3-regression` | Historical T1.21 diagnostic branch retained. |

Dirty main worktree files:

- `.claude/CLAUDE.md` modified by Repowise generated block and navigation
  wording.
- `.gitignore` modified to ignore `.repowise/*` while keeping
  `.repowise/mcp.json` trackable.
- `.mcp.json` modified to add the Repowise MCP server.
- `AGENTS.md` modified to describe Repowise as available when exposed by the
  runtime.
- `CLAUDE.md` modified to mention Repowise MCP rather than "no MCP".
- `claude-code-lsp-enforcement-kit` deleted from the working tree.
- `.repowise-workspace.yaml` untracked.
- `.repowise/` untracked as a directory because `.repowise/mcp.json` was
  intentionally unignored; generated `.repowise` database/cache files remained
  ignored.

The dirty Repowise/tooling state had not been committed.

## Working Notes

- The User wanted compact but durable architecture first, then deeper plans.
  The resulting plans now live in `.apm/memory/plans/` and should be treated as
  canonical recovery anchors.
- The User wanted the Manager workflow examined first, then concrete Manager
  steps, then Worker workflow and skillset design at matching depth. All three
  strategic files were created and committed.
- The User explicitly wanted T1.36 p-value cleanup folded into the T1.37
  handoff/task. This was done in the active T1.37 prompt and the Worker produced
  `pvalue_denominator_cleanup_2026-05-28.json`.
- The User remembered why T1.2g was removed from the schedule: the same-L
  first13 strategy was computationally infeasible and revival would require a
  Pre-reg #5 amendment for asymmetric L. T1.2g remained out of T1.37 scope.
- The User no longer used jCodemunch. Active jCodemunch hooks/instructions were
  removed; future mentions should be treated as stale context unless found in
  active configuration.
- For T1.37 long jobs, the User preferred polling consistent with multi-hour
  runtimes: job-01 every 15 minutes; later long jobs by status JSON every
  30 minutes, shortening only when phase-status indicates aggregation/DONE or
  an output file appears.
