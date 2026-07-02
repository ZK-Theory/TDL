---
name: tda-acceleration-benchmarking
description: Use when a TDL job is slow, memory-heavy, repeated at scale, or proposed for GPU, cloud, Dask, Polars, or vectorisation acceleration — to prove the acceleration is justified before adopting it.
---

# TDA Acceleration Benchmarking

"Prove acceleration is justified", not "move it to GPU". Never accelerate
before profiling. This skill is subordinate to `tda-resource-preflight`: the
preflight decides workers/checkpointing/wall-time for a launch; this skill
evaluates whether a *different execution strategy* should replace the current
one, and gates the swap on numerical equivalence.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Acceptance Gate

Accept an acceleration only if ALL hold:

- wall-time improvement is material at the realistic workload (n × B × L),
  not at toy scale;
- outputs match the baseline within a declared tolerance (repo precedent:
  the giotto backend was accepted on bit-for-bit finite persistence pairs,
  atol=1e-9);
- contracts still pass;
- checkpoint/resume behaviour survives (≥4 workers, chunked checkpoints);
- environment drift is recorded (new venv, interpreter, library versions);
- result artifacts are not silently overwritten.

## Procedure

1. Record the baseline command and environment.
2. Profile the baseline; identify the bottleneck: CPU, memory bandwidth,
   I/O, Python/GIL overhead, PH backend, or algorithmic complexity.
   Known repo case: exact W2 (gudhi) holds the GIL — threading gives zero
   parallelism; and ripser+loky degraded ~6.4x per-task under n_jobs=12
   concurrency (memory-bandwidth contention, not core count).
3. Try the lowest-risk improvement first (vectorise → process pool → out-of-
   core → new backend → GPU/cloud).
4. Benchmark the candidate at realistic scale, sweeping the worker count —
   a single-configuration timing is not a benchmark.
5. Compare numerical outputs against the baseline at the declared tolerance.
6. Check contract and provenance impact (backend name and versions belong in
   `run_params`).
7. Accept or reject with recorded reasons; rejected candidates are findings
   too.

## Required Output Record

```text
baseline command · hardware/environment · profile result · bottleneck
classification · candidate method · benchmark result (worker sweep) ·
numerical equivalence check (tolerance stated) · provenance impact ·
accepted/rejected decision + reason
```

## Self-Test Prompts

- *"This is slow, let's move it to GPU."* → Expected: refuse until profiled;
  the bottleneck class decides the remedy, and GPU is not the first rung.
- *A candidate backend matches on a 100-trajectory toy but is untested at
  L=5000.* → Expected: benchmark and equivalence-check at realistic scale
  before acceptance.

## Escalate Or Stop When

- Numerical outputs drift beyond tolerance — that is a defect investigation
  (`tda-diagnosing-computational-defects`), not an acceptable cost.
- The acceleration would change a pre-registered parameter (B, L) — never;
  surface instead.

## Related Skills

`tda-resource-preflight` (launch discipline — always upstream) · `spike`
(feasibility probes) · `tda-diagnosing-computational-defects` ·
`result-provenance-review` (recording environment drift).
