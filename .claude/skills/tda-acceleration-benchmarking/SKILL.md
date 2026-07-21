---
name: tda-acceleration-benchmarking
description: Use when a TDL job is slow, memory-heavy, repeated at scale, or proposed for GPU, cloud, Dask, Polars, or vectorisation acceleration — to prove the acceleration is justified before adopting it.
metadata:
  version: "1.0.0"
  tier: specialist
  lanes: []
  roles:
    - implementer
    - operator
  runtime: agnostic
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

- the benchmark names the exact scheduled computational work unit and demonstrates
  stage parity: representative distinct inputs, identical preprocessing and
  postprocessing, concurrency topology, and cache state;
- wall-time improvement is material for that end-to-end unit at the realistic workload
  (n × B × L), not at toy scale;
- outputs match the baseline within a declared tolerance (repo precedent:
  the giotto backend was accepted on bit-for-bit finite persistence pairs,
  atol=1e-9);
- contracts still pass;
- checkpoint/resume behaviour survives (≥4 workers, chunked checkpoints);
- environment drift is recorded (new venv, interpreter, library versions);
- result artifacts are not silently overwritten.

## Procedure

1. Record the baseline command, environment, and the exact computational work unit the
   production scheduler invokes. List every timed stage.
2. Profile the baseline; identify the bottleneck: CPU, memory bandwidth,
   I/O, Python/GIL overhead, PH backend, or algorithmic complexity.
   Known repo case: exact W2 (gudhi) holds the GIL — threading gives zero
   parallelism; and ripser+loky degraded ~6.4x per-task under n_jobs=12
   concurrency (memory-bandwidth contention, not core count). A memory-
   bandwidth-bound kernel can scale *negatively* under joblib/loky (exact W2
   EMD did here, and loky repeatedly stalled): when it does, the reliable lever
   is not a parallel backend but **independent serial processes over disjoint
   input blocks** — block-partition the work, one process per block.
3. Try the lowest-risk improvement first (vectorise → process pool → out-of-
   core → new backend → GPU/cloud).
4. Benchmark the candidate at realistic scale, sweeping the worker count —
   a single-configuration timing is not a benchmark; and for a variable-cost
   kernel a two-sample timing is not one either — sample enough distinct inputs
   to capture the per-input cost distribution (repo case: exact W2 EMD solve
   time varied ~5× across pairs of one cache), or the projection rests on an
   unrepresentative sample. Verify stage parity against the
   production unit before extrapolating. Label kernel-only timings as component
   benchmarks; they cannot project pipeline wall time without measured stage composition.
   For thread-based candidates, build an execution-locus table (stage → holds the GIL?)
   before crediting a concurrency benefit — threads only parallelize GIL-releasing
   stages, and per-task parent-process CPU work is the throughput ceiling regardless of
   worker count (Amdahl), independent of core count.
5. Compare numerical outputs against the baseline at the declared tolerance.
6. Check contract and provenance impact (backend name and versions belong in
   `run_params`).
7. Accept or reject with recorded reasons; rejected candidates are findings
   too.

## Required Output Record

```text
baseline command · named scheduled work unit · stage-parity checklist ·
hardware/environment · profile result · bottleneck classification · candidate method ·
harness = production entry point (yes/no) · benchmark result (worker sweep) ·
execution-locus table (thread-based candidates only) ·
numerical equivalence check (tolerance stated) ·
provenance impact · accepted/rejected decision + reason
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
