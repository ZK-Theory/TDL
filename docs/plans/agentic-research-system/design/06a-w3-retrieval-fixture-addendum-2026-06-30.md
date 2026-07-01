# W6 Addendum — W3 Retrieval Fixture Reservations

**Date:** 2026-06-30<br>
**Status:** Accepted design reservation under P-028; executable materialization deferred<br>
**Applies to:** `06-evaluation-observability-and-audit.md` revision 0.2<br>
**Design authority:** Accepted W3 v0.2, adversarial W3 review at `1d6ade22`, approved reconciliation, and P-028<br>
**Implementation authority:** None; this addendum creates no fixture directories, graders, traces, runtime, migration, or research-state changes

## 1. Purpose and precedence

P-027 accepted the original 40-fixture W6 catalogue: F-001–F-024 and S-001–S-016. This dated addendum preserves that historical acceptance and reserves six W3-derived designs, F-025–F-030, so the context contract has explicit W6 enforcement points.

For W3 retrieval coverage, this addendum replaces the phrase “later W3 retrieval fixtures” in W6 with the exact IDs below. It does not alter the identity, provenance, priority, or oracle of an existing fixture.

## 2. Reserved fixtures

| ID | Priority / lanes; provenance | Pre-control setup and expected failure | Post-control outcome and trajectory oracle | Graders / dependency |
|---|---|---|---|---|
| F-025 Orchestrator scope-collapse retrieval | P0; context, governance, claim; `historical` incident / `reconstructed` input | A minimized Stage-2 scope-collapse reconstruction supplies a 22-member ScopeDefinition, stronger Wave-1-only acceptance evidence, W0 precedence, P-026/P-027/P-028 boundaries, and stale Tracker/memory completion prose. Baseline retrieval omits or subordinates the stronger governing material. | Mandatory closure retains the exact scope revision, all members, current acceptance boundary, source precedence, unresolved status, and amendment authority. Stale completion prose is labeled lower-authority conflict and cannot produce a full-stage completion recommendation. | D,T,M,H; W3/W4/W5/W7 dependent |
| F-026 Implementer frozen-representation/null/vintage retrieval | P0; context, representation, stochastic, topology, provenance; `domain_coverage` / `synthetic` | A minimized synthetic bundle derived from F-011–F-013 includes the frozen transform, null-operation/no-op preflight, coherent input vintage, parameters/seeds/roots/schema, stop rules, and distractor refit/stale-input/producer-pass material. Baseline retrieves a plausible but superseded shortcut. | The packet includes every governing transform, invariance, vintage, parameter, provenance, and stop requirement; rejects refit/approximation shortcuts; and does not trust the producer-emitted pass flag. | D,T,R,M,P; W3/W5/W7 dependent |
| F-027 Optional-index deletion equivalence | P0; context, provenance; `specification` / `synthetic` | A complete optional index initially proposes supplementary candidates and is then deleted or marked stale. Baseline changes the mandatory packet or treats index absence as weaker authority. | Direct-source retrieval produces the identical mandatory fragment set, order, versions, and hashes; the manifest records index loss and fallback without changing authority. | D,T; W3/W7 dependent |
| F-028 Budget overflow fails closed | P0; context, governance, operations; `specification` / `synthetic` | Mandatory closure exceeds either the reference-token profile ceiling or the bound-provider capacity gate. Baseline omits, truncates, or summarizes governing material to issue a packet. | Compilation returns `context_budget_exceeded`, required-source/size evidence, and safe options; no packet is issued and no readiness/review gate is satisfied. | D,T,O; W3/W4/W7 dependent |
| F-029 Safe-distractor invariance | P1; context, provenance; `specification` / `synthetic` | Safe optional distractors vary in order, wording, or presence. Baseline changes mandatory selection or the terminal decision. | Mandatory fragments, governing versions/hashes, and terminal decision remain invariant; optional differences and omissions remain explicit. | D,T,M; W3 dependent |
| F-030 Addendum lineage and cumulative-budget conformance | P1; context, provenance, operations; `specification` / `synthetic` | Later retrieval attempts to mutate the base packet, hide cumulative size, or patch a missing mandatory source through an addendum. | Base and addenda retain distinct immutable IDs/hashes; cumulative counts satisfy both gates; a missing mandatory base source supersedes/fails the base and requires a new complete packet. | D,T,O; W3/W7 dependent |

The incident-basis and input-fidelity values are separate axes. Historical motivation does not make reconstructed or synthetic inputs preserved evidence. Materialization must bind each fixture to a minimized source manifest, reconstruction method, redaction record, and calibration oracle.

## 3. Priority and change-gate effect

The context compiler/memory change gate now includes:

```text
F-003–F-006, F-011–F-019, F-021–F-022, F-025–F-030
```

F-025–F-028 are P0 implementation/release blockers for the context compiler and applicable provider routes. F-029–F-030 are P1 gates before a research pilot promotes evidence or claims. Existing priorities remain unchanged.

## 4. Mandatory-closure sizing precondition

Before a context compiler or provider/profile combination can pass Gate 1, W6 materialization must measure the exact mandatory closure for F-025, F-026, F-021, and F-022 under both W3 token gates:

1. versioned reference-token count against the W3 risk-profile ceiling;
2. exact bound-provider token count, or a W7-evaluated conservative upper bound, against 80% of provider usable input.

An over-ceiling closure is a blocking design signal, not fixture noise. Resolution requires either:

- a versioned, retrieval-evidence-backed ceiling/profile change; or
- explicit task decomposition that demonstrates preservation of cross-cutting governing evidence.

Mandatory material may not be omitted, truncated, or silently summarized to obtain a passing fixture.

## 5. Materialization order and boundary

After W3–W5 and the necessary W7 accounting interface are available:

1. materialize and calibrate P0 F-025–F-028;
2. record both token counts, mandatory-source recall, amendment recall, omission behavior, and provider-capacity outcome;
3. block compiler/profile release on any required failure;
4. materialize P1 F-029–F-030 before the greenfield research pilot;
5. retain all W6 privacy, independent-property, non-compensable-grader, and no-live-task constraints.

No fixture may use T1.28, active APM state, raw restricted data, full transcripts, secrets, or hidden reasoning. This reservation does not materialize fixtures or authorize foundation implementation.

## 6. Outcome

**Outcome:** `ACCEPTED_RESERVATION — F-025–F-030 close the W3-to-W6 catalogue seam; executable evidence remains deferred`.
