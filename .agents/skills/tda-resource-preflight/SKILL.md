---
name: tda-resource-preflight
description: Use before launching compute that may exceed ~30 minutes — bootstraps, permutation nulls, Markov batteries, MICE refits, per-cluster or per-individual batteries, PH at high landmark count, or large ETL / memory-sensitive dataframe work.
---

# TDA Resource Preflight

Locked convention: long-running stochastic compute runs on **at least 4
workers**, with chunked checkpointing, progress reporting, and an up-front
wall-time estimate. **Serial long stochastic compute is a reviewable defect.**
This skill produces the resource plan that makes a launch defensible. Skip it
for small deterministic unit tests and trivial calculations.

## Procedure

1. Capture the intended command and the workload scale: rows, trajectories,
   dimensions, diagrams, null draws B, permutations, bootstrap count,
   landmark count L.
2. **Benchmark the real statistic before trusting any estimate.** "The metric
   space loads" is not feasibility — time the actual statistic at realistic
   n × B. A benchmark probe sweeps the worker count 1→N; a single-configuration
   timing is not a benchmark.
3. Apply known repo constraints:
   - Exact Wasserstein-2 (gudhi) holds the GIL — joblib's `threading` backend
     yields ZERO parallelism for it. Use the default `loky` (process) backend
     and budget memory per worker.
   - At L = 5000 scale, exact W2 runs ~5–10 s per diagram pair; multiply out
     before promising a wall time.
4. Select the strategy: serial (written justification required) / joblib-loky /
   multiprocessing / R future·parallel / Dask / out-of-core.
5. Require, non-negotiably: workers ≥ 4 (or the written justification),
   chunked checkpointing with resume, progress reporting, date-suffixed
   outputs that never overwrite, recorded seeds, and a stated wall-time
   estimate BEFORE launch.
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
  "strategy": {"parallel_backend": "loky", "workers": 4,
                "checkpointing": true, "resume_supported": true,
                "progress_reporting": true},
  "risk_flags": [],
  "estimated_wall_time": null,
  "validation_commands": []
}
```

## Windows Runner Scripts

When wrapping a native executable in a Windows PowerShell 5.1 runner, do NOT
pipe its output under `$ErrorActionPreference = 'Stop'` — the first benign
stderr line becomes a `NativeCommandError` and aborts the run. Use
`Start-Process` with `-RedirectStandardOutput` / `-RedirectStandardError`
`-NoNewWindow -Wait -PassThru`, then check `ExitCode`.

## Completion Checklist

- [ ] Workload scale quantified (n × B × L, not adjectives).
- [ ] Real statistic benchmarked, worker count swept.
- [ ] Worker count ≥ 4 specified, or serial explicitly justified in writing.
- [ ] Checkpoint/resume strategy and progress reporting specified.
- [ ] Output overwrite protection and seeds specified.
- [ ] Wall-time estimate recorded before launch.
- [ ] Memory-per-worker × workers checked against the machine; disk checked.
- [ ] Preflight record written.

## Escalate Or Stop When

- The benchmark says the wall time is infeasible — surface it; never silently
  shrink B or L, they are pre-registered parameters.
- Memory per worker × workers exceeds the machine — reduce workers with a
  written note, or move to out-of-core.

## Related Skills

`spike` (feasibility probes own the benchmark discipline) ·
`contract-first-tdd` · `result-provenance-review` (output rules) ·
`tda-task-brief-from-plan` (runtime constraints in dispatched briefs).
