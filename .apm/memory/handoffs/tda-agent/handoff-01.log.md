---
agent: tda-agent
outgoing: 1
incoming: 2
handoff: 1
stage: 1
---

# Tda Agent Handoff 1 (Tda Agent 1 to Tda Agent 2)

## Summary

This instance worked on Stage 1, Task 1.37, the frozen-loadings rerun batch for P01-A/P01-B. It completed the setup of individual job tracking, launched and monitored jobs 00 through 05, stopped job-05 after the User identified correctness defects, and applied a corrective code/test patch before handoff.

Task 1.37 was not completed. The current state was mid-Task: jobs 00 through 04 had completed, job-05 had been stopped, and no later job had been started. The next Worker should continue from the active Task Bus after reviewing the logs listed in the handoff prompt.

Auto-compaction occurred during this instance. Earlier work context was reconstructed from the compaction summary, then verified against the live Task Bus, job tracker, job status JSON, git status, and vault log before this handoff was written.

## Working Context

The User corrected the execution pattern for this rerun: use individual jobs with individual outputs/logs wherever possible, because monolithic long-running batches are too fragile. The active tracker is `C:\Users\steph\TDL\.apm\memory\stage-01\task-01-37.jobs.md`.

The active compute worktree is outside the Codex writable root: `C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun`. Commands and edits there required escalated execution. The project `.apm` artifacts live under the main project root `C:\Users\steph\TDL`.

The Task Bus remains intact at `C:\Users\steph\TDL\.apm\bus\tda-agent\task.md`. It still contains Task 1.37 and should be read directly by the incoming Worker.

Job status before handoff:

- job-00 USoc smoke completed and produced `usoc_headline_smoke_2026-05-26.json`.
- job-01 USoc headline frozen completed, but its p-values were produced under the old denominator and are superseded.
- job-02 BHPS headline frozen completed, but its p-values were produced under the old denominator and are superseded.
- job-03 USoc LM L=2500 frozen completed, but its final JSON both used the old p-value denominator and dropped T/d/mean aggregate fields.
- job-04 USoc LM L=8000 frozen completed, with the same denominator/schema caveats as job-03.
- job-05 BHPS length-matched truncate frozen was started, then stopped by User request after the p-value denominator and LM schema defects were confirmed. Its status file records `stopped` at `2026-05-27T09:49:35.8217041+01:00`.
- job-06 through job-08 were not started.

The corrective code patch was applied before handoff:

- `trajectory_tda/scripts/stage1/_battery_core.py` now separates p-value null draws from effect-size null pairs. P-values use `n_pvalue_pairs = min(B, total_pairs)`, so standard runs use denominator `B + 1`. T/d diagnostics retain the configured null-null pair cap.
- `trajectory_tda/scripts/run_stage1_battery.py` received the same denominator fix so the legacy reference path does not validate the old math.
- `run_lm_sensitivity_single_L()` now returns the full `aggregate_combined()` payload instead of reducing cells to `w2_pvalue` and `landscape_l2_pvalue` only.
- `tests/trajectory_tda/test_stage1_battery_core_regressions.py` was added to pin the split path, legacy path, and LM schema behavior.

Validation performed before handoff:

- `uv run ruff check trajectory_tda/scripts/run_stage1_battery.py trajectory_tda/scripts/stage1/_battery_core.py tests/trajectory_tda/test_stage1_battery_core_regressions.py` passed.
- `uv run pytest tests/trajectory_tda/test_frozen_loadings.py tests/trajectory_tda/test_stage1_battery_core_regressions.py` passed 7/7.

APM and vault artifacts were updated:

- `C:\Users\steph\TDL\.apm\memory\stage-01\task-01-37.log.md` was created/updated with active Task status and important findings.
- `C:\Users\steph\TDL\.apm\memory\stage-01\task-01-37.jobs.md` was appended with the corrective stop/fix section.
- `C:\Users\steph\Documents\TDA-Research\04-Methods\Computational-Log.md` received a top-of-page `[PIPELINE]` entry dated 2026-05-27.

## Working Notes

Do not start job-05 or later jobs until the User chooses a rerun/repair strategy. The already-completed job-01 through job-04 JSONs remain on disk as untracked files, but their p-values are superseded by the denominator fix. The LM JSONs are also schema-incomplete for the comparison table unless repaired from partial artifacts/logs or rerun.

The correct statistical interpretation is now: for B=1000, the minimum p-value is `1/1001 = 0.000999...`, not `1/501 = 0.001996...`. The old code used the diagnostic pair cap as the denominator, which was mathematically inconsistent with the metadata and intended test.

Serena/jCodemunch routing was not reliable for the assigned APM compute worktree. Direct targeted file operations were used in the assigned worktree after verifying the mismatch. Record this tooling gap if further code edits happen under Task 1.37.

Current git status in the compute worktree included modified tracked files:

- `trajectory_tda/scripts/run_stage1_battery.py`
- `trajectory_tda/scripts/stage1/_battery_core.py`

and untracked files including completed result JSONs, job logs, and `tests/trajectory_tda/test_stage1_battery_core_regressions.py`. The code/test fix has not been committed.
