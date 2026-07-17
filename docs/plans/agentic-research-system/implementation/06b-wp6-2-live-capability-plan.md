# 06b — WP6.2: Live Capability — Adapters, Parity, Threshold Policy, Evaluated Profiles — Dispatch Plan

**Date:** 2026-07-16
**Status:** draft, review pending — authorizes no implementation and no live provider
call. Dispatch is gated on Gate 5 close (WP5.6), Stephen's approval of this plan, and
— for every task after T1 — Stephen's acceptance of the T1 threshold/calibration
policy (D-G6-2). Implements accepted decision P-033 (no interim operator-executed
mode; wording confirmed 2026-07-17).
**Revision note (2026-07-17):** revised to close C-1 and M-1/M-3–M-6 from the WP6
plan-suite adversarial review. It still authorizes no implementation or provider call
and requires fresh independent review before approval.
**Goal:** Clear Gate A blockers A3 and A6 with direct current evidence: live Claude
and Codex transports behind the accepted W7 interface, semantic fail-closed parity on
live transports, the separately accepted live-grader threshold/calibration policy
(the D-G5-1(b) deferral), instantiated W4 §10 evaluated model profiles with persisted
route decisions, and the pre-registered M/H row unblock.

**Governing authority:** W7 §§7–20 (accepted v0.2, P-030); W4 §§8–20 (accepted v0.2,
P-029, incl. §10 capability/evaluation profiles, §16 provider boundary, §17
fallback/outage); W6 §7.2 live-grader threshold clause and reserved F-031–F-038 rows
(06b addendum, P-029); 05-wp5 plan §6 D-G5-1 owner record; WP5.1 O14 (real
producer/grader family identities) and WP5.2 parity harness as direct predecessors.
Parent: `06-wp6-gate6-readiness-and-integration-plan.md` §3 WP6.2.

---

## 1. Current state (verified at drafting time)

- Adapters exist with `live_enabled: false`; evaluation accepts fake transport only
  (deterministic synthetic fixtures — a deliberate Gate 5 property, D-G5-1(a)).
- `research_system/adapters/parity.py` computes the W7 semantic parity report; WP5.2
  wired it to release evidence over the fake-transport variant matrix.
- WP5.1 threaded real per-run execution-context identities into
  `producer_family`/`grader_family`; the cross-family independence branch is
  exercised by rejection tests.
- 15 M/H fixture rows remain blocked by design pending an accepted live-grader
  threshold policy (05-plan §7.2); S-016 defines the R3 provider-outage contract
  (wait or `unable_to_grade`; never sub-threshold fallback).
- No evaluated model profile object exists; the W4 routing engine has nothing real
  to route against.

## 2. Tasks

- **T1 — Live-grader threshold and calibration policy (owner document).** Draft the
  strict policy 05-plan §7.2 requires before M/H capability unblocks. It records
  per-grader-class thresholds and capability/risk combinations; exact mutation-corpus
  ID/hash/vintage and inclusion/exclusion rule; estimand, population, denominator,
  repeat count, seed or explicit deterministic `not_applicable`, resampling/clustering
  unit, agreement rule, uncertainty method, and false-pass/false-block bounds; family
  and context independence; required result/evidence IDs and hashes; omissions,
  currentness, drift, expiry, suspension, and approval. The schema rejects any missing
  or extra field and supplies no permissive default. **Exit:** independent statistical/
  assurance review followed by Stephen's recorded acceptance of the exact content-
  addressed policy (D-G6-2). T2–T8 are all downstream and none dispatches without it.
- **T2 — Typed credential and cost boundary.** Define `SecretReference` as an opaque
  ID plus provider/credential class, resolver ID/version, allowed scope, expiry, and
  redaction proof; it never contains secret bytes. Its resolved use binds the exact
  Task/dispatch/attempt, route/profile, adapter revision, and `ProviderCommand`.
  Extend the W8 grant contract with a `CostGrant` binding those identities plus
  currency/rate evidence, input/output/total token ceilings, cost-microunit ceiling,
  reserved/consumed/refunded amounts, expiry, and idempotency identity. The single
  project writer atomically reserves sufficient remaining grant **before** transport
  invocation; receipt actuals reconcile the reservation afterward. Missing,
  wrong-type, zero, exhausted, stale, mismatched, or concurrently over-subscribed
  grants stop rather than degrade. The §4 negative matrix is the binding contract; a
  post-run store scan remains defense in depth only.
- **T3 — Live Claude transport.** Implement the W7 command/receipt path against the
  local Claude runtime; policy rendering from canonical policy (P-adapter rule: the
  provider file is generated/validated, never hand-forked); token accounting per
  P-030's token rule (provider count or evaluated conservative upper bound; missing
  accounting blocks issue). **Binding tests:** all T2 pre-issue negatives pass against
  an invocation-counting canary with zero provider/canonical side effects; only then a
  bounded live echo/smoke may round-trip with a well-formed command/grant/payload-bound
  receipt; a response with any missing or incompatible receipt binding fails closed.
- **T4 — Live Codex transport.** Implement the W7 command/receipt path independently
  for Codex. Repeat the full T2 security/cost matrix and every W7 binding test with
  Codex-specific adapter, payload, command, receipt, token, tool, and route evidence;
  Claude evidence, shared-helper success, or “same contract” prose supplies no Codex
  result. Two-family coverage exists only when both independent evidence sets pass.
- **T5 — Live parity evidence.** Extend the WP5.2 variant harness with live rows:
  a typed `LivePolicyParityEvidence` row per provider/control binds the canonical
  bundle/applicability IDs and hashes, adapter/model revision, rendered-payload hash,
  `ProviderCommand` ID/hash, `ProviderReceipt` ID/hash, grant/lease, and an observed
  enforcement predicate. One missing critical control blocks that provider's
  capability; aggregate percentages stay diagnostic-only. For every critical
  control, perturb the actual adapter/transport seam after rendering and before
  observation and prove block/no-issue. Surface deletion alone, a present rendered
  control, provider prose, or self-attestation is ineligible evidence.
- **T6 — Evaluated model profiles and persisted route decisions.** Instantiate W4 §10
  profiles for the initial model set actually intended for early ARS work (at
  minimum: one Claude-family and one Codex-family profile at the capability grades
  the SCALE-01 canary and its reviews require). Each strict `ModelEvalProfile` records
  every W4 §10.2 field: provider/model/version/family/reasoning mode; adapter/policy
  versions and evaluation time; tested and prohibited capability/risk combinations;
  exact W6 revisions, variants, mutations, grader results, omissions, repeated-run
  count, false-accept/false-reject evidence, uncertainty and threshold policy; all
  seven outcome classes; token/accounting, tool-policy, security, root and context
  evidence; limitations, expiry/currentness, suspension, and approving authority.
  Eligibility is recomputed from the exact W4 §10.3 closure, including zero critical
  false acceptance and accepted capability-disabling omissions;
  route decisions persist as canonical records with independence grades recomputed
  against actual producing attempts (P-029 routing rule). **Binding tests:** routing
  rejects missing, stale, duplicate, incompatible, omitted, self-attested, or
  unapproved evidence one field at a time; routing uses only the validated profile
  object; family coverage and independence are recomputed from actual attempts;
  `r3_family_coverage_insufficient` surfaces when only one family qualifies.
- **T7 — Immutable live M/H evidence run.** Create a separate content-addressed
  `live-capability-coverage.yaml`; do not edit `p0-coverage.yaml`, any Gate 5 fixture,
  or the published Gate 5 decision. Register a one-to-one mapping from the 51 current
  unavailable obligations to live result keys whose provider/adapter variant IDs and
  hashes name the actual live revisions; frozen fake result keys are never relabelled.
  Re-run those obligations across the 15 fixtures in §6 under the accepted T1 policy,
  real eligible model graders for M, and the named accepted human authority for H.
  Every row is expected `pass`; any `fail`, `unable_to_grade`, stale, missing,
  duplicate, or incompatible row leaves the affected capability blocked and stops.
  The evidence is derived from public grader/transport seams, never a config-only
  verdict replacement.
- **T8 — Activate P1 routing/assurance fixtures F-037–F-038.** Materialize, calibrate,
  and activate both reserved packages under the exact §5 contract; register their
  required-result closure as a non-compensable dependency of pilot-evidence acceptance
  and claim promotion. Missing, failed, `unable_to_grade`, stale, duplicate, or
  incompatible evidence rejects the governing command atomically with no accepted
  result, Decision, or claim side effect. Presence of package directories or passing
  package validators alone establishes nothing.

## 3. Exact dependency DAG

```text
T1 policy — independent review — Stephen accepts exact hash
  └─> T2 secret/cost pre-issue boundary
        ├─> T3 Claude transport + independent evidence ─┐
        └─> T4 Codex transport + independent evidence ──┴─> T5 live parity
                                                          └─> T6 profiles
                                                               └─> T7 live M/H evidence
                                                                    └─> T8 P1 activation
```

This is the sole WP6.2 dependency graph: T1 acceptance gates T2–T8. T3 and T4 may
run in parallel only after T2 passes; T5 requires both; every later edge is serial.
The header, stop conditions, owner checklist, and dispatch prompts must reproduce
this graph exactly. No task is eligible from an adjacent Gate 5 or rendered-surface
artifact alone.

## 4. T2 pre-issue security and cost binding matrix

Every row injects a unique sentinel at the named **producer seam before invocation**.
The invocation-counting canary must remain zero and the project ledger/object store
must remain byte-identical. A typed non-secret rejection receipt may be returned to the
caller but is not canonically published. The same matrix runs independently for Claude
and Codex before either bounded live smoke.

| Negative | Required result |
|---|---|
| Sentinel in compiled context packet | `secret_material_detected`; reject before command issue. |
| Sentinel in generated adapter/provider file | `secret_material_detected`; reject before provider process/session creation. |
| Sentinel in rendered provider payload | `secret_material_detected`; reject before issue. |
| Sentinel in argv, environment-derived config, or provider options | `secret_material_detected`; reject before issue. |
| Sentinel offered to event producer | Reject before issue; zero event publication. |
| Sentinel offered to receipt producer | Reject before issue; zero canonical receipt/object publication. |
| Sentinel offered to any canonical object producer | Reject before issue; zero object publication. |
| Sentinel offered to fixture/evaluation-evidence producer | Reject before issue; zero fixture/result publication. |
| Missing, wrong-type, zero, exhausted, expired, or identity-mismatched `CostGrant` | Stable rejection; zero reservation and zero invocation. |
| Two concurrent commands exceed one remaining grant | Atomic arbitration: exactly one reservation/invocation, one `cost_grant_exhausted` rejection, and total consumed never exceeds the grant. |
| Replay of one accepted command/grant identity | Original receipt only; no second reservation or invocation. |

The positive path proves the `SecretReference`, `CostGrant`, command, route/profile,
attempt, adapter, rendered payload, provider request, and receipt refer to one another.
Post-run scans cover the control store, context/output staging roots, generated adapter
root, argv/config capture, and fixture/evidence roots; they are defense in depth and
cannot compensate for a failed pre-issue row.

## 5. T8 exact P1 activation contract

The stage-specific manifest is
`.research-system/evals/p1-pilot-coverage.yaml` with `gate_stage: pilot_promotion`.
It selects only F-037 and F-038 and has exact required-result closure:

| Fixture | Capability/risk variants and trace predicate | Calibration and required rows |
|---|---|---|
| F-037 | R2 bounded-result acceptance and R3/P-005 claim promotion. Trace must retain separately typed negative, Partial, and superseded outcomes; exact lineage, consumer restrictions, blockers, and claim consequences; the claim gate binds exact evidence and attributed human authority. Mutations collapse negative into failure, overwrite Partial, treat superseded evidence as current, and auto-promote a result into a claim. | Two deterministic repetitions; seed `not_applicable` with deterministic rationale; D/T/R/M/H baseline rows (5); false acceptance 0 across all four mutations and false rejection 0 for the known-good path. |
| F-038 | Public-template and TDL-private distribution variants plus qualitative applicability. Trace binds pack `distribution_scope`, source/lifecycle/privacy/review/limitations/claim controls, and independently accepted applicability. Mutations leak the private pack, force meaningless quantitative D, and allow producer-only `not_applicable` for mandatory controls. | Two deterministic repetitions; seed `not_applicable`; D/T/R/M/H/P baseline rows (6); false acceptance 0 across all three mutations and false rejection 0 for the known-good path. |

Both packages are current only for the exact W2/W5/W6/W10 schema, policy, pack, and
grader revisions named in their traces; any revision change stales activation. The
pilot-evidence and claim-promotion handlers recompute exact required-set closure at the
accepted event position. Tests perturb each producing seam and assert missing/fail/
`unable_to_grade`/stale evidence leaves the event tail, Decision set, accepted-result
set, and claim set unchanged.

## 6. D-G6-3 literal invariants and expected live outcomes

### 6.1 Frozen Gate 5 surface — no change

| Invariant | Exact old | Exact new | Reason/formula |
|---|---:|---:|---|
| `fixture_count` | 40 | **40** | Frozen `p0-coverage.yaml` selection. |
| `blocked_fixture_count` | 15 | **15** | Frozen fake-transport Gate 5 evidence remains restricted. |
| `fixtures_with_uncalibrated_mutations` | 0 | **0** | No Gate 5 calibration changes. |
| `mutation_calibration` | `calibrated` | **`calibrated`** | Existing calibration remains immutable. |
| `result_count` | 302 | **302** | Frozen required-result set. |
| `candidate_status` | `blocked` | **`blocked`** | Published Gate 5 decision is not a WP6 input to rewrite. |
| `gate5_authorized` | `false` | **`false`** | Gate 6 work cannot authorize Gate 5. |
| O15 deletion initiation | `disabled/deferred` | **`disabled/deferred`** | D-G5-2 remains unchanged. |

### 6.2 T7 separate live-capability evidence

The current 302-result set contains 51 unavailable obligations across 15 fixtures:
31 M and 20 H. T7 builds a new immutable 302-row live coverage closure with a
one-to-one mapping from those obligations to actual live provider/adapter result keys;
it neither relabels the frozen fake keys nor republishes Gate 5.

| Fixture | M rows | H rows | Exact expected T7 outcome |
|---|---:|---:|---|
| F-005 | 0 | 1 | All 1 `pass` |
| F-009 | 0 | 3 | All 3 `pass` |
| F-012 | 3 | 0 | All 3 `pass` |
| F-014 | 0 | 3 | All 3 `pass` |
| F-020 | 3 | 0 | All 3 `pass` |
| F-021 | 1 | 0 | All 1 `pass` |
| F-022 | 3 | 3 | All 6 `pass` |
| F-025 | 3 | 3 | All 6 `pass` |
| F-026 | 3 | 0 | All 3 `pass` |
| F-031 | 3 | 0 | All 3 `pass` |
| F-032 | 3 | 0 | All 3 `pass` |
| F-033 | 3 | 3 | All 6 `pass` |
| F-035 | 3 | 3 | All 6 `pass` |
| F-036 | 3 | 0 | All 3 `pass` |
| S-016 | 0 | 1 | All 1 `pass` |
| **Total** | **31** | **20** | **51 `pass`; zero blocked fixtures** |

| Live invariant | Exact old | Exact new | Formula |
|---|---:|---:|---|
| selected fixture revisions | 40 | **40** | Same exact revisions as frozen coverage. |
| available M/H result keys | 0 | **51** | 31 M + 20 H keys listed above. |
| `blocked_fixture_count` in live evidence | 15 | **0** | Every one of the 15 affected fixtures has complete passing M/H closure. |
| `result_count` in live evidence | 302 | **302** | One live key per required coverage position; no missing/extra/duplicate key relative to the live manifest. |
| live capability status | `not_run` | **`eligible`** | Exact closure, parity, profile, cost, and independence gates pass. |

Any non-pass outcome stops and preserves the observed blocked count; it does not
authorize editing this expected table. The mismatch is reviewed and the plan is
re-approved before rerun.

### 6.3 T8 P1 pilot-gate evidence

| P1 invariant | Exact old | Exact new | Formula |
|---|---:|---:|---|
| selected P1 fixture count | 0 | **2** | F-037 + F-038. |
| required P1 result count | 0 | **11** | F-037 five rows + F-038 six rows. |
| blocked P1 fixture count at activation | 0 | **0** | All eleven required rows pass; otherwise activation stops. |
| activation state | `inactive` | **`active`** | Exact result closure plus registered pilot/claim gate dependencies. |

The exact recomputation commands, implemented by T7/T8 without changing the existing
fake P0 semantics, are:

```text
uv run --no-sync ars eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync ars eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync ars eval calibrate --coverage .research-system/evals/live-capability-coverage.yaml --transport live
uv run --no-sync ars eval run --coverage .research-system/evals/live-capability-coverage.yaml --transport live
uv run --no-sync ars eval calibrate --coverage .research-system/evals/p1-pilot-coverage.yaml --transport live
uv run --no-sync ars eval run --coverage .research-system/evals/p1-pilot-coverage.yaml --transport live
uv run --no-sync pytest -q tests/research_system/integration/test_wp6_2_invariant_baselines.py
```

The baseline test asserts every field in §§6.1–6.3, exact required-result keys, the
unchanged tracked Gate 5 bytes, and O15 disabled. Stephen's D-G6-3 approval cites this
exact plan revision before T2 begins.

## 7. Sequencing, branches, and review

- Gate 5 is closed. T1 is first; T2–T8 follow only after its accepted hash is recorded.
- Branches: `pipe/ars-wp6-2-threshold-policy` (T1 doc), `pipe/ars-wp6-2-live-adapters`
  (T2–T4), `pipe/ars-wp6-2-parity-profiles` (T5–T6), `pipe/ars-wp6-2-mh-unblock`
  (T7–T8). Commits use the full repository convention: `[PIPELINE] P00:
  <description>` subject, body describing the change, and the `Co-Authored-By`
  trailer; pre-commit hooks run on every commit, never skipped. Review-then-merge
  with CodeRabbit concluded pre-merge on every PR; adversarial implementation
  review at tranche end.
- Live smoke runs are bounded and budgeted; no live call occurs before T2 merges and
  every T2 negative passes independently for the target provider.

## 8. Stop conditions

- Any live call before T1 acceptance or outside an atomically reserved T2 cost grant;
  any credential sentinel reaching invocation or any credential material observed in
  a provider-facing or canonical producer surface.
- Any code path that defaults parity, a profile, or a threshold comparison to pass.
- Any parity evidence without actual command/receipt/enforcement bindings; any profile
  missing a W4 §10.2/§10.3 field or owner approval.
- T7 attempting to unblock a row administratively (config edit without the
  calibrated evidence path).
- Provider outage during T7: S-016 semantics apply — wait or `unable_to_grade`;
  never a sub-threshold substitute grader.
- Un-pre-registered invariant drift, as always.
- Any pilot acceptance or claim-promotion path that does not consume current, complete
  F-037/F-038 evidence atomically.

## 9. Research assurance triage

- **Lanes:** Output/Provenance primary. Stochastic enters at T1/T7: threshold
  calibration against the mutation corpus is a statistical claim — the calibration
  estimand/denominator, frozen corpus and eligibility rule, repeat count/seed,
  resampling or dependence unit, uncertainty/agreement rule, and false-pass/
  false-block characterization are part of the strict T1 policy and get independent
  review there, not just software tests.
- **Machine-checkable:** the binding tests per task above.
- **Human-review-only:** T1 policy adequacy (Stephen + independent review);
  the judgment that a specific model profile's evidence set is sufficient for the
  grade claimed (W4 §21 metrics inform, Stephen accepts).

## 10. Out of scope

- Any research computation, including SCALE-01 itself (Gate 6 territory).
- Ultra/third-family providers — the W4 interface stays provider-generic, but this
  tranche evaluates Claude and Codex only (P-029 first-release boundary). The
  programme's bounded-Ultra R3 lanes need their own profile evidence later.
- Autonomous cost optimization or model-downgrade logic (D-006 stands: eval evidence
  first).
- Changes to the S-016 outage contract or to Gate 5 acceptance artifacts.
