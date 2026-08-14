---
document_type: ars-experiment-contract
alias: SPEC-02
version: 1.1.0
status: proposed_inert_dependency_gated
authority_activation: forbidden
supersedes_lineage_file: ars-spec-02-spectral-distance-ph-micro-spike-template-v1.0.0-2026-07-16.md
supersedes_lineage_sha256: f9316c33844d77c9bde9506decb942354a28441e372a06c7abc2d9ed03d5bec5
decision_basis: owner_selected_spec_route_for_gate_6
---

# SPEC-02 — Synthetic spectral-distance PH micro-spike

## Entry gate and purpose

Run a bounded synthetic reproduction only after SPEC-01 has a schema-valid scorecard,
independent outcome review, an owner-resolved PROMOTE decision, and a later explicit
live-run approval. Accepted source, topology, fixture, method, output, resource,
attempt, lease, producer, reviewer, and authority relations must be current. Nothing in
this document activates them.

The historical file named in the lineage metadata is origin evidence only. This
successor is the governed experiment contract. It preserves the synthetic feasibility
question while removing unrelated predecessor dependencies.

The question is whether at least one fixed spectral configuration recovers the planted
noisy-circle loop materially better than Euclidean PH without producing a qualifying
loop on the sphere negative control.

## Frozen source and environment

Before start, bind the primary NeurIPS 2024 paper and exact reference-code commit,
licence, environment, manifold generators, graph symmetrisation, metric formulas,
filtration, score edge cases, heuristic guard, dtype, and tolerances. Any unresolved
paper/code discrepancy blocks execution. Windows local resources are limited to four
CPU slots, two hours, 12 GB memory, and 5 GB attempt scratch; no GPU or network is
assumed.

## Frozen synthetic fixtures

Use n=1,000, ambient d=50, seeds 0, 1, and 2, the pinned generator and isometric
mapping, and isotropic Gaussian noise:

- circle at sigma 0, 0.25, and 0.35; planted H1 count 1;
- sphere at sigma 0.25; planted H1 count 0 and negative-control role;
- torus at sigma 0 and 0.25; planted H1 count 2 and stress-only role.

Each `(manifold, sigma, seed)` array is written once to attempt scratch, hashed, and
reused across methods. Scientific seeds are isolated from benchmark ordering.

## Frozen method matrix

Run exactly seven methods for every fixture cell:

1. Euclidean distance baseline.
2. Corrected effective resistance on symmetric unweighted kNN, k=15.
3. Corrected effective resistance on symmetric unweighted kNN, k=100.
4. Diffusion distance, k=15, t=8.
5. Diffusion distance, k=15, t=64.
6. Diffusion distance, k=100, t=8.
7. Diffusion distance, k=100, t=64.

Graph construction, tie handling, Laplacian normalisation, eigenvalue handling, and
distance conventions match the pinned source. A disconnected graph or a non-finite,
asymmetric, or non-zero-diagonal distance matrix is retained as a blocked cell; it is
never repaired with arbitrary distances. No method or configuration may be added after
outcomes are visible.

Six cells × three seeds × seven methods gives 126 primary configurations. Determinism
reruns cover all 42 configurations for circle sigma 0.25 and sphere sigma 0.25. Input,
graph, distance, diagram, and score identities must match the accepted deterministic
contract.

## Persistent homology and score

Compute Vietoris–Rips persistence on the full distance matrix, coefficient field F2,
H1 only, with the source threshold policy. Sort finite pairs by persistence. For m
planted loops, use `s_m=(p_m-p_(m+1))/p_m` with all missing, zero, birth-zero, and
infinite-bar conventions copied from and tested against the pinned source. Set `s_m=0`
when all diagram features have death-to-birth ratio below 1.25. The sphere computes the
same adjusted s1 diagnostic; s1 at least 0.50 is a qualifying false loop.

## Primary decision gate

At circle sigma 0.25, at least one single prespecified spectral configuration must meet
all conditions:

1. median adjusted s1 across seeds is at least 0.50;
2. its adjusted s1 minus Euclidean adjusted s1 is at least 0.25 for every seed;
3. the same configuration has adjusted s1 below 0.50 on every sphere seed;
4. every required graph for that configuration is connected;
5. all required determinism reruns pass;
6. the attempt stays within the time and memory limits.

Report all six spectral configurations and the Euclidean baseline. Torus adjusted s2
is stress evidence and cannot alone fail the primary gate. The terminal result is PASS,
FAIL, or PARTIAL in `ars://portfolio/spike-verdict`; its mechanical recommendation is
PROMOTE, PARK, KILL, or NONE under the accepted truth table.

## Attempt outputs and restart

Write only beneath `{attempt_scratch}/spec-02/`: source/environment, fixture, method,
connectivity/distance, persistence/score, determinism, resource/progress, and decision
artefacts. Write no repository result file. Every artefact is synthetic/non-empirical,
content-addressed, and records permitted consumers and prohibited inferences.

Progress is monotone by completed configuration, checkpointed at least every 14 primary
configurations and after each determinism cell group. Restart replays the durable ledger,
requires the exact source/environment, fixture, method, plan, attempt, lease, and
completed-cell identities, and returns the same receipt for the same idempotency tuple.
A changed subject conflicts; it cannot silently resume.

## Stop and claim boundary

Stop on provider API use, provider process or command-line launch by ARS, credential or
OAuth access, survey data, leaked child or writer, unregistered object write,
disconnected-graph workaround, post-outcome matrix amendment, resource breach,
fabricated identity or grant, self-review, or automatic promotion. The recorded verdict
requires independent review and an explicit owner decision. No result authorizes survey
work or supports a labour-data, superiority, novelty, or paper claim.
