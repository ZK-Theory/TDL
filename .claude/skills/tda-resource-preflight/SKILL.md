---
name: tda-resource-preflight
description: Use before launching compute that may exceed ~30 minutes — bootstraps, permutation nulls, Markov batteries, MICE refits, per-cluster or per-individual batteries, PH at high landmark count, or large ETL / memory-sensitive dataframe work.
metadata:
  version: "1.0.0"
  tier: core
  lanes:
    - output-provenance
  roles:
    - operator
    - manager
  runtime: agnostic
---

# TDA Resource Preflight

Locked convention: long-running stochastic compute establishes and records its
**optimal safe worker count** before launch, with chunked checkpointing, progress
reporting, and an up-front wall-time budget. The count is selected from a measured
production-entry-point sweep; it is not a fixed minimum or the largest count that
fits in memory.
This skill produces the resource plan that makes a launch defensible. Skip it
for small deterministic unit tests and trivial calculations.

## Procedure

1. Capture the intended command and the workload scale: rows, trajectories,
   dimensions, diagrams, null draws B, permutations, bootstrap count,
   landmark count L.
2. **Benchmark the real statistic before trusting any estimate.** "The metric
   space loads" is not feasibility — time the actual statistic at realistic
   n × B. A benchmark probe sweeps the worker count 1→N; a single-configuration
   timing is not a benchmark. The benchmark must invoke the **production entry
   point** — the real script/task function at target concurrency — never a
   component kernel alone; a kernel-only timing measures a different program
   and cannot project pipeline wall time without measured stage composition.
   Record the sweep's call count as a percentage of the target run's B/duration
   in the preflight record; an estimate built from a sweep below full target
   scale is **PROVISIONAL** and must be labelled as such wherever it is
   written down (preflight record, Computational-Log, vault note) — some
   contention-bound workloads (memory bandwidth, cache, subprocess-pool
   growth) have no valid sub-scale predictor at all, only a full-scale canary.
   A timing estimate's precision reads as validated fact to anyone who later
   consults the artifact regardless of the sample size behind it, so encode
   PROVISIONAL at write time — do not rely on a later launcher to remember
   and re-caveat it verbally.
3. Apply known repo constraints:
   - Exact Wasserstein-2 (gudhi) holds the GIL — joblib's `threading` backend
     yields ZERO parallelism for it. Do not therefore assume `loky` will scale:
     this kernel can be memory-bandwidth-bound and showed negative process
     scaling. Measure serial first, then sweep a bounded process count with
     memory headroom recorded.
   - At L = 5000 scale, exact W2 runs ~5–10 s per diagram pair; multiply out
     before promising a wall time.
   - Before choosing a thread-based parallel design, build an execution-locus
     table (stage → runs where → holds the GIL?). Threads only parallelize
     GIL-releasing stages; per-task parent-process CPU work (null simulation,
     embedding, distance computation, `.tolist()` serialization) is the
     throughput ceiling regardless of worker count. Do not assume a stage is
     I/O-bound from intuition alone — check it, especially against any
     existing memory recording the opposite for that exact library call.
4. Select the strategy: serial / joblib-loky / multiprocessing / R
   future·parallel / Dask / out-of-core. Record the p75-projected wall time,
   observed process parallelism, and memory headroom for every feasible candidate
   count; select the feasible count with the lowest projected wall time. If a
   lower count wins because extra processes contend for RAM, CPU, I/O, or the
   backend, record that evidence rather than forcing a larger count.
   For a variable-cost kernel, time at least eight distinct units drawn from the
   actual inputs and report median, min/max, and p75. An inherited per-unit timing
   is a prior to re-measure, not a constant. If the new rate differs by more than
   2x, record the discrepancy in the preflight artifact.
   Do not repeatedly construct `joblib.Parallel` pools with NumPy arrays in
   `initializer` `initargs`: executor reuse compares those arrays and can fail
   only on the second batch. Use one reusable
   `concurrent.futures.ProcessPoolExecutor` for array-valued worker state.
5. Require, non-negotiably: the preflight-selected worker count and wall-time
   budget, chunked checkpointing with resume, progress reporting, date-suffixed
   outputs that never overwrite, recorded seeds, and a stated wall-time
   estimate BEFORE launch. Progress/checkpoint cadence must be **shorter than
   the operator's patience** — an interval longer than the operator will wait
   is indistinguishable from a stall and provokes destructive "fixes" (a kill,
   or a rewrite of a healthy run). Size the first-output expectation by result
   **ordering**, not rate alone: a cost-ordered queue that yields in submission
   order can delay the first progress line far past a rate-based estimate while
   the run is perfectly healthy, so emit an immediate heartbeat at launch,
   before the first unit completes. Record all three — operator patience,
   heartbeat cadence, and heartbeat delivery channel (log file, progress bar, or
   message-bus entry) — in the preflight record so responsiveness is auditable.
   When the run is a multi-condition grid/battery
   (multiple rungs, nulls, or parameters) under a budget that may truncate it,
   the loop order is part of the plan: sequence cells so the smallest
   COMPLETE, INTERPRETABLE design — every rung including any negative control,
   at the cheapest setting — finishes first, and every later block only adds
   resolution. A checkpoint preserves cells; only the ordering preserves an
   interpretable comparison if the run is killed mid-grid.
6. Emit the preflight record and the command template. For anything over
   ~10 minutes, prefer a background task or subagent and write handoff state
   first so a halted job resumes rather than restarts.

## Preflight Record

Write `resource_preflight_<task>_<YYYY-MM-DD>.json` alongside the run plan:

```json
{
  "task_id": "...",
  "paper_id": "...",
  "command": "...",
  "data_scale": {"n_rows": null, "n_trajectories": null,
                  "landmark_count": null, "null_draws": null},
  "resources": {"cpu_cores": null, "memory_gb": null, "disk_free_gb": null},
  "strategy": {"parallel_backend": "loky", "worker_candidates": [],
                "selected_workers": null,
                "selection_criterion": "lowest safe p75-projected wall time",
                "checkpointing": true, "resume_supported": true,
                "progress_reporting": true,
                "operator_patience_s": null,
                "progress_cadence_s": null,
                "checkpoint_cadence_s": null,
                "heartbeat_cadence_s": null,
                "heartbeat_delivery": null,
                "launch_heartbeat": {"emitted_at": null, "status": null}},
  "benchmark": {"harness_is_production_entry_point": null,
                 "candidate_results": [],
                 "sweep_call_count": null,
                 "target_call_count": null,
                 "scale_pct": null},
  "risk_flags": [],
  "estimated_wall_time": null,
  "provisional": false,
  "validation_commands": []
}
```

Responsiveness fields are self-auditing: `*_s` values are integer **seconds**;
`progress_cadence_s` and `checkpoint_cadence_s` are recorded separately (a shared
value may be repeated) so an audit sees both without external context.
`heartbeat_cadence_s` must be `< operator_patience_s`. `launch_heartbeat.emitted_at`
is an ISO-8601 UTC timestamp and `launch_heartbeat.status` is one of
`emitted` / `missing` — the run is auditable for responsiveness only when both
are populated.

## WSL Background Compute

WSL 2 processes are tied to their parent session's lifecycle and die silently
when it exits — `wsl bash -c "... &"`, `Start-Process wsl ... -PassThru`, and
PowerShell `Start-Job { Start-Process wsl ... }` all detach in appearance but
the WSL process dies with the parent; the output file stays empty with no
error. The only mechanism that survives across tool invocations is the Bash
tool's own `run_in_background: true`. Even then, an inner `wsl bash -c '...'`
can fail exit-127 with a misleading "No such file or directory" — the
background wrapper breaks single-quoted `bash -c` payloads, and MSYS rewrites
absolute POSIX paths into Git-Bash-rooted Windows paths. Launch as a direct
exec instead: `MSYS_NO_PATHCONV=1 wsl.exe <absolute-wsl-python> -u
<script-via-/mnt/c/...>`, no inner shell. Separately, run WSL Python probes
with `python -u` (or explicit flush): stdout is fully buffered off a tty, so
a mid-run `Read` on the output file will show only WSL's startup stderr (e.g.
an `fstab` warning) and look stalled even though the process is healthy —
output otherwise arrives in one batch at exit. `-u` only unbuffers Python's
own stdout; a PowerShell `*>` redirect reading that pipe can still buffer it,
so for a budget decision that depends on mid-run timings, have the script
self-log (append + `flush()` to a plain file) and read that file rather than
the shell-redirected log.

## Windows Runner Scripts

When wrapping a native executable in a Windows PowerShell 5.1 runner, do NOT
pipe its output under `$ErrorActionPreference = 'Stop'` — the first benign
stderr line becomes a `NativeCommandError` and aborts the run. Use
`Start-Process` with `-RedirectStandardOutput` / `-RedirectStandardError`
`-NoNewWindow -Wait -PassThru`, then check `ExitCode`.

## Completion Checklist

- [ ] Workload scale quantified (n × B × L, not adjectives).
- [ ] Real statistic benchmarked via the production entry point (not a
      component kernel), worker count swept.
- [ ] Benchmark scale vs. target run recorded; PROVISIONAL flagged if the
      sweep is below full target scale.
- [ ] Candidate worker counts, measured outcomes, and the optimal safe selected
      count are recorded; no fixed worker floor was assumed.
- [ ] Checkpoint/resume strategy and progress reporting specified.
- [ ] Output overwrite protection and seeds specified.
- [ ] Wall-time estimate recorded before launch.
- [ ] Progress cadence shorter than operator patience; an immediate launch
      heartbeat emitted (a cost-ordered / in-order-yield queue delays first real output).
- [ ] Memory-per-worker × workers checked against the machine; disk checked.
- [ ] Preflight record written.

## Escalate Or Stop When

- The benchmark says the wall time is infeasible — surface it; never silently
  shrink B or L, they are pre-registered parameters.
- Memory per worker × workers exceeds the machine — reject that candidate and
  select a safe lower count, or move to out-of-core.
- `heartbeat_cadence_s` is absent, equals or exceeds `operator_patience_s`, or
  `launch_heartbeat` has no `emitted_at`/`status` recorded — the run is not
  auditable for responsiveness; fix the preflight record before dispatching.

## Related Skills

`spike` (feasibility probes own the benchmark discipline) ·
`contract-first-tdd` · `result-provenance-review` (output rules) ·
`tda-task-brief-from-plan` (runtime constraints in dispatched briefs) ·
`tda-acceleration-benchmarking` (when a different execution strategy
should replace the current one).
## Coordinator failure handling

- Persist the complete preflight evidence record before raising a stop condition, including checks already completed and the precise failing trigger.
- Treat native stderr as diagnostic data unless the child exit code, protocol, or explicit rule declares failure. Long-run coordinators must not terminate solely because a successful native process wrote stderr.
