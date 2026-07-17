# 06b — WP6.2: Live Capability — Adapters, Parity, Threshold Policy, Evaluated Profiles — Dispatch Plan

**Date:** 2026-07-16
**Status:** exact plan content independently reviewed and owner-approved under P-036 at
`fe5f1d40bc8f05f061317c677b5891cea0711249`; authorizes no implementation and no live
provider call. T2–T4 additionally require Stephen's acceptance of the exact T1a protocol hash; T5–T8
and every M/H eligibility transition additionally require Stephen's acceptance of the
exact composite T1b-M/T1b-H evidence-bearing policy hash (D-G6-2/P-035). Implements accepted decision
P-033 (no interim operator-executed mode; wording confirmed 2026-07-17).
**Revision note (2026-07-17):** revised through the R3 remediation review to make T1b a
non-compensable model/human evidence union, pin literal 51-row and 54-obligation
expected-source annexes, require a strict P1 stage schema and independently accepted
descriptor-hash manifest, and separate W6 `gate_stage` from `evidence_stage`. It still
authorizes no implementation or provider call. R5 independently reviewed the exact
revision above with zero findings, and Stephen approved it under P-036; only the
plan-suite review gate is closed.
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

- **T1a — Pre-registered live-grader calibration protocol.** Before any provider call,
  freeze the strict protocol that 05-plan §7.2 requires: grader classes and capability/
  risk combinations; exact authored mutation-corpus IDs/hashes/vintage and inclusion/
  exclusion rule; estimand, population, denominator, repeat IDs/count, deterministic
  seed rationale, resampling/clustering unit, agreement rule, uncertainty method,
  proposed false-pass/false-block bounds and acceptance rule; family/context
  independence; required future result/evidence fields; omissions, drift, expiry,
  suspension, and approval mechanics. The protocol has separate exact expected sets
  for model and human calibration. The human set freezes rubric ID/version/hash and
  blinded positive, negative, ambiguous, and producer-correlated case IDs/hashes;
  attribution/context requirements; disagreement capture; adjudication and rubric-
  revision rules; and the named authority class permitted to grade. The protocol schema
  rejects missing or extra
  fields and supplies no permissive default. It labels thresholds and bounds as
  **pre-registered acceptance criteria**, never observed calibration. **Exit:**
  independent statistical/assurance review followed by Stephen's recorded acceptance
  of the exact protocol hash. That hash permits only T2–T4, not M/H grading or T5–T8.
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
- **T1b — Composite evidence-bearing live-grader policy.** T1b is the exact,
  non-compensable union `T1b-M ∪ T1b-H`. `T1b-M` executes the accepted model protocol
  through the merged T2 boundary and both independently passing T3/T4 transports; it
  records provider/model/adapter, command/receipt, grant/lease, producer/grader context,
  per-run results/evidence, uncertainty, false-pass/false-block summaries, omissions,
  family/context independence, currentness, expiry, suspension, and threshold
  decisions. `T1b-H` executes the separately frozen blinded human case set and records
  rubric/version/hash, exact positive/negative/ambiguous/producer-correlated cases,
  attributed human authority and context, per-case results/evidence, disagreements,
  adjudication, any rubric revision, currentness, expiry, suspension, and the H
  acceptance decision. Model runs cannot satisfy an H obligation and human judgments
  cannot repair an M gap. Protocol deviations require a new T1a revision.
  **Exit:** independent statistical/assurance review of T1b-M and independent human-
  evidence review of T1b-H, followed by Stephen's recorded acceptance of one composite
  hash that binds both complete sets. If either set is incomplete, that unsupported
  class remains ineligible and the composite T1b gate does not clear. Only the accepted
  composite hash may gate T5–T8 or make an M/H grader/profile eligible.
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
- **T7 — Immutable composite live M/H evidence closure.** Create the separate,
  content-addressed `live-capability-coverage.yaml` under the versioned schema and
  stage loader in §6.2; do not edit `p0-coverage.yaml`, any Gate 5 fixture/result, or
  the published Gate 5 decision. Its exact composition is 251 immutable
  `foundation_release` result references plus 51 new `live_capability` results. The
  exclusive expected replacement set is the literal 51-row annex
  `06e-wp6-2-live-replacement-map.md`, canonical UTF-8/LF SHA-256
  `a65c24624bb309558dd29a779b2db5b1c308b9fcd5caff4b5394e365b77e47b8`.
  Each
  live row has a one-to-one predecessor mapping from the corresponding unavailable
  M/H Gate 5 key and names actual provider/model/adapter identities and hashes; no
  frozen fake result is relabelled, copied as live, or silently replaced. Re-run those
  51 obligations across the 15 fixtures in §6 under the accepted T1b policy,
  real eligible model graders for M, and the named accepted human authority for H.
  Every row is expected `pass`; any `fail`, `unable_to_grade`, stale, missing,
  duplicate, or incompatible row leaves the affected capability blocked and stops.
  The evidence is derived from public grader/transport seams, never a config-only
  verdict replacement.
- **T8 — Activate P1 routing/assurance fixtures F-037–F-038.** First materialize and
  independently accept the content-addressed 54-row expected manifest required by 06f
  §3; no descriptor build or observation may precede that boundary. Then materialize,
  calibrate, and activate both reserved packages under the exact §5 contract and
  normative annex
  `06f-wp6-2-p1-activation-contract.md`, canonical UTF-8/LF SHA-256
  `160f898837df14d3f22ba2592eb117766686b5d5d6e4004cb8669886ea8d670c`.
  Register both the
  eleven-row baseline-result set and the separate 43-referent activation closure; the
  atomic pilot/claim dependency is their 54-referent union at one expected event
  position. Missing, failed, `unable_to_grade`, stale, duplicate, incompatible,
  omitted-mutation, wrong-repeat, or unapproved-applicability evidence rejects the
  governing command atomically with no accepted result, Decision, or claim side
  effect. Package presence, validators, or eleven passing baseline rows alone establish
  nothing.

## 3. Exact dependency DAG

```text
T1a protocol — independent review — Stephen accepts exact protocol hash
  └─> T2 secret/cost pre-issue boundary
        ├─> T3 Claude canary + independent evidence ─┐
        └─> T4 Codex canary + independent evidence ──┴─> T1b-M model evidence
                                                           + T1b-H human evidence
                                                           — independent review
                                                           — Stephen accepts exact
                                                             composite evidence hash
                                                             └─> T5 live parity
                                                                  └─> T6 profiles
                                                                       └─> T7 composite M/H closure
                                                                            └─> T8 P1 activation
```

This is the sole WP6.2 dependency graph: accepted T1a gates T2–T4 only; T3 and T4
may run in parallel after T2; T1b requires both; accepted T1b gates T5–T8 and M/H
eligibility; every later edge is serial.
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
`.research-system/evals/p1-pilot-coverage.yaml` with valid W6
`gate_stage: pilot_promotion` and typed `evidence_stage: p1_activation`.
The P1 loader validates it against the dedicated strict schema
`.research-system/schemas/evals/p1-activation-manifest.schema.json` version `1.0.0`;
the T7 `live-coverage-manifest` schema and the frozen P0 coverage schema are not valid
substitutes or branches.

The P1 schema requires `schema_id`, `schema_version`, the two stage constants, and
`expected_event_position`. It requires the accepted 06f repository path/Git blob/
canonical UTF-8-LF SHA-256 and the independently accepted
`.research-system/contracts/wp6-2-p1-activation-expected.yaml` repository path, schema
ID/version, Git blob, and SHA-256. Its `baseline_bindings` array has exactly eleven
ordered `prefixItems`, with obligation IDs `B01`–`B11` fixed to their complete six-field
keys, literal descriptor hashes, verdicts, and result IDs/hashes. Its
`activation_bindings` array has exactly 43 ordered `prefixItems`, with IDs `A01`–`A43`
fixed to the complete 06f logical keys, descriptor hashes, and required observed
bindings. The arrays set `minItems`/`maxItems` to `11` and `43`, respectively, and both
set `items: false`; every schema object sets
`additionalProperties: false`. Thus missing, duplicate, extra, reordered, relabelled,
or incomplete obligations are structurally invalid before semantic comparison.

It selects only F-037 and F-038. Eleven baseline grader results and the complete
activation evidence are different sets and must never be conflated. The exclusive
expected-side source for both is `06f-wp6-2-p1-activation-contract.md`, SHA-256
`160f898837df14d3f22ba2592eb117766686b5d5d6e4004cb8669886ea8d670c`.
The accepted expected manifest fixed by 06f §3 records that identity, every complete
logical obligation, and every literal descriptor hash. Runtime manifests and
ledger/execution records are observed-side inputs only and cannot generate or repair
expectations.

### 5.1 Exact baseline-result set (11)

The literal canonical six-field keys are:

```text
(F-037, 1.0.0, f-037-outcome, D, assurance-claim-v1, baseline)
(F-037, 1.0.0, f-037-trajectory, T, assurance-claim-v1, baseline)
(F-037, 1.0.0, f-037-research-quality, R, assurance-claim-v1, baseline)
(F-037, 1.0.0, f-037-independent-model, M, assurance-claim-v1, baseline)
(F-037, 1.0.0, f-037-human-authority, H, assurance-claim-v1, baseline)
(F-038, 1.0.0, f-038-outcome, D, domain-pack-applicability-v1, baseline)
(F-038, 1.0.0, f-038-trajectory, T, domain-pack-applicability-v1, baseline)
(F-038, 1.0.0, f-038-research-quality, R, domain-pack-applicability-v1, baseline)
(F-038, 1.0.0, f-038-independent-model, M, domain-pack-applicability-v1, baseline)
(F-038, 1.0.0, f-038-human-authority, H, domain-pack-applicability-v1, baseline)
(F-038, 1.0.0, f-038-privacy-security, P, domain-pack-applicability-v1, baseline)
```

Each key binds its result ID and content hash. These eleven rows prove only the
baseline grader outcomes; they do not prove calibration or activation.

### 5.2 Exact activation closure (43 referents)

The accepted 06f annex declares these independently hashed expected referents; the
manifest carries only observed bindings to them:

| Referent class | Exact identities | Count |
|---|---|---:|
| Fixture revisions | `F-037@1.0.0`, `F-038@1.0.0` | 2 |
| F-037 mutations | `F-037-M01-negative-collapsed-to-failure`, `F-037-M02-partial-overwrite`, `F-037-M03-superseded-treated-current`, `F-037-M04-auto-promote-result-to-claim` | 4 |
| F-038 mutations | `F-038-M01-private-pack-leak`, `F-038-M02-meaningless-quantitative-D`, `F-038-M03-producer-only-not-applicable` | 3 |
| Known-good cases | `F-037-KG-01`, `F-038-KG-01` | 2 |
| Safe-variation cases | `F-037-SV-01`, `F-038-SV-01` | 2 |
| Per-case execution evidence | Exact Cartesian product of the preceding 11 case IDs (7 mutations + 2 known-good + 2 safe-variation) with literal repetition IDs `rep-01` and `rep-02`; each of the 22 entries has verdict, result ID/hash, trace ID/hash, and retained evidence ID/hash | 22 |
| Error summaries | `F-037-error-summary-v1` binds its 12 execution hashes; `F-038-error-summary-v1` binds its 10 execution hashes; each binds denominator, false-pass count/rate/bound, false-block count/rate/bound, and uncertainty method/result; their combined closure is exactly 22 | 2 |
| Threshold policy | `wp6-live-grader-evidence-policy-v1`, exact accepted composite T1b-M/T1b-H ID/hash | 1 |
| F-038 applicability | `F-038-applicability-qualitative-v1`, exact independently accepted evidence and authority ID/hash | 1 |
| Calibration records | `F-037-calibration-v1`, `F-038-calibration-v1`, each supplying `calibration_record_id` and hash | 2 |
| Activation records | `F-037-activation-v1`, `F-038-activation-v1`, each supplying activation event ID/hash and accepted event position | 2 |
| **Complete activation closure** | Literal union above | **43** |

The mutation definitions are the known-bad cases. Both known-good and safe-variation
cases run twice as well; a calibration implementation cannot reduce the 22 execution
entries to the fourteen mutation executions. Every descriptor/revision row carries its
own content hash, so an unchanged logical name cannot mask changed bytes.

### 5.3 Fixture predicates and atomic consumer contract

| Fixture | Capability/risk variants and trace predicate | Calibration and required rows |
|---|---|---|
| F-037 | R2 bounded-result acceptance and R3/P-005 claim promotion. Trace must retain separately typed negative, Partial, and superseded outcomes; exact lineage, consumer restrictions, blockers, and claim consequences; the claim gate binds exact evidence and attributed human authority. | Five baseline rows; four mutation, one known-good, and one safe-variation cases each at `rep-01` and `rep-02`; false pass 0 across mutations and false block 0 across both non-attack cases. |
| F-038 | Public-template and TDL-private distribution variants plus qualitative applicability. Trace binds pack `distribution_scope`, source/lifecycle/privacy/review/limitations/claim controls, and independently accepted applicability. | Six baseline rows; three mutation, one known-good, and one safe-variation cases each at `rep-01` and `rep-02`; false pass 0 across mutations and false block 0 across both non-attack cases. |

Both packages are current only for the exact W2/W5/W6/W10 schema, policy, pack, and
grader revisions named in their traces; any revision change stales activation. The
pilot-evidence and claim-promotion commands consume the exact 54-referent union
(11 baseline + 43 activation) at one expected event position. Each command loads the
complete expected logical set only from the accepted 06f expected manifest and loads
observed IDs/hashes only from canonical ledger/execution records; the command payload
cannot declare its own expected set. The single writer either publishes
the governing event with all referents or publishes nothing. One-at-a-time tests cover
missing, failed, `unable_to_grade`, stale, duplicate, incompatible, omitted mutation,
wrong repetition, changed descriptor hash, incomplete error summary, unaccepted T1b
policy, and unapproved F-038 applicability. Each omission is also injected at the
public producer seam before observation so omission from both expected and observed
dictionaries cannot pass. The summary validator separately asserts F-037 has exactly
12 hashes, F-038 exactly 10, and their disjoint union exactly 22. A coordinated mutation
replaces both descriptor bytes and a candidate expected manifest with a self-consistent
changed pair; the immutable D-G6-3 manifest blob/SHA binding rejects it. Every rejection
leaves the event tail,
accepted-result set, Decision set, activation set, and claim set unchanged.

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

### 6.2 T7 composite live-capability evidence

The approved model is exactly `251 frozen references + 51 new live results = 302`.
The current 302-position Gate 5 set contains 51 unavailable obligations across 15
fixtures (31 M and 20 H) and 251 otherwise available positions. T7 builds a new
immutable composite closure; it does not claim 302 live executions, relabel a fake
result, or republish Gate 5.

The exclusive expected replacement map is `06e-wp6-2-live-replacement-map.md`, SHA-256
`a65c24624bb309558dd29a779b2db5b1c308b9fcd5caff4b5394e365b77e47b8`.
The new schema is
`.research-system/schemas/evals/live-coverage-manifest.schema.json` version `1.0.0`.
The manifest is `.research-system/evals/live-capability-coverage.yaml`, has
valid W6 `gate_stage: pilot_promotion` plus typed
`evidence_stage: live_capability`, and declares literal counts
`referenced_frozen: 251`, `new_live: 51`, and `aggregate_closure: 302`. Each of its 302
entries has:

- `closure_key`, `entry_kind` (`frozen_reference` or `live_result`), source artifact
  ID/hash, source result key/hash, lifecycle stage, and fixture revision ID/hash;
- grader ID/revision/hash and variant ID/revision/hash (or typed `not_applicable`);
- provider, model, and adapter IDs/revisions/hashes, retaining the original fake
  identity for a frozen reference and the observed live identities for a live result;
- provider command and receipt IDs/hashes, cost-grant and execution-lease IDs/hashes,
  or—only for a frozen Gate 5 reference—a typed `not_applicable` execution binding with
  reason `foundation_release_fake_transport`; and
- explicit predecessor/replacement fields. A frozen reference has both fields
  explicitly null. A live result names exactly one unavailable Gate 5 predecessor key,
  has `replacement_scope: live_capability_only`, and does not mutate that predecessor.

Schema conditionals require all live bindings for `live_result`, prohibit them from
being asserted by a frozen row, and enforce a bijection between the 51 unavailable
predecessor keys and 51 new result keys. The expected 251 frozen keys come from accepted
Gate 5 coverage and the expected 51 predecessor/successor bindings come only from 06e,
never from loaded rows or a live manifest.

The existing P0 commands and fake-only loader remain byte/behavior compatible:

```text
ars eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
ars eval run       --coverage .research-system/evals/p0-coverage.yaml --transport fake
```

T7/T8 add a separate stage-aware boundary; it does not route the P0 manifest:

```text
ars eval stage validate --gate-stage pilot_promotion --evidence-stage live_capability --manifest .research-system/evals/live-capability-coverage.yaml
ars eval stage run      --gate-stage pilot_promotion --evidence-stage live_capability --manifest .research-system/evals/live-capability-coverage.yaml
ars eval stage validate --gate-stage pilot_promotion --evidence-stage p1_activation --manifest .research-system/evals/p1-pilot-coverage.yaml
ars eval stage run      --gate-stage pilot_promotion --evidence-stage p1_activation --manifest .research-system/evals/p1-pilot-coverage.yaml
```

The stage loader validates `gate_stage` against the closed W6 enumeration and routes on
the separate closed `evidence_stage`; neither field aliases the other. It rejects
missing, duplicate, extra, stale, incompatible, relabelled,
wrong-provider, wrong-model, wrong-adapter, absent-command/receipt/grant/lease, broken
predecessor bijection, and mixed-lifecycle rows before capability or activation state
changes. Tests also prove that passing a P0 manifest to `eval stage`, or a live/P1
manifest to the existing P0 command, fails without invoking a provider or weakening
the fake-only exact-set checks.

P1 schema/loader negatives separately cover a cross-stage row, a P0 manifest, wrong or
missing `gate_stage`/`evidence_stage`, each missing/duplicate/extra baseline or activation
obligation, incomplete six-field baseline keys, missing descriptor hashes, stale or
substituted 06f path/blob/SHA, stale or substituted expected-manifest path/blob/SHA, and
a stale expected event position. Every case rejects before provider invocation, event
allocation, or activation/claim state change.

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
| referenced frozen Gate 5 positions | 0 | **251** | Exact immutable references to otherwise-available `foundation_release` results; original identities/hashes retained. |
| new live result positions | 0 | **51** | One new result for each unavailable M/H predecessor; exact bijection. |
| aggregate composite closure | 0 | **302** | `251 referenced_frozen + 51 new_live`; no missing/extra/duplicate key. |
| live capability status | `not_run` | **`eligible`** | Exact closure, parity, profile, cost, and independence gates pass. |

Any non-pass outcome stops and preserves the observed blocked count; it does not
authorize editing this expected table. The mismatch is reviewed and the plan is
re-approved before rerun.

### 6.3 T8 P1 pilot-gate evidence

| P1 invariant | Exact old | Exact new | Formula |
|---|---:|---:|---|
| selected P1 fixture count | 0 | **2** | F-037 + F-038. |
| baseline grader-result count | 0 | **11** | F-037 five rows + F-038 six rows; not the activation closure. |
| activation-closure referent count | 0 | **43** | Exact §5.2 identities and hashes. |
| atomic pilot/claim referent count | 0 | **54** | 11 baseline + 43 activation referents at one expected event position. |
| calibration execution count | 0 | **22** | Eleven literal cases × repetitions `rep-01`, `rep-02`. |
| blocked P1 fixture count at activation | 0 | **0** | The 54-referent union validates and every required verdict is `pass` or the one independently authorized F-038 scientific-D `not_applicable`; otherwise activation stops. |
| activation state | `inactive` | **`active`** | Exact atomic union plus accepted activation events. |

The exact recomputation commands, implemented by T7/T8 without changing the existing
fake P0 semantics, are:

```text
uv run --no-sync ars eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync ars eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run --no-sync ars eval stage validate --gate-stage pilot_promotion --evidence-stage live_capability --manifest .research-system/evals/live-capability-coverage.yaml
uv run --no-sync ars eval stage run --gate-stage pilot_promotion --evidence-stage live_capability --manifest .research-system/evals/live-capability-coverage.yaml
uv run --no-sync ars eval stage validate --gate-stage pilot_promotion --evidence-stage p1_activation --manifest .research-system/evals/p1-pilot-coverage.yaml
uv run --no-sync ars eval stage run --gate-stage pilot_promotion --evidence-stage p1_activation --manifest .research-system/evals/p1-pilot-coverage.yaml
uv run --no-sync pytest -q tests/research_system/integration/test_wp6_2_invariant_baselines.py
```

The baseline test asserts every field in §§6.1–6.3, the literal 251/51 composition and
06e hash, all 54 P1 referent keys/hashes, accepted expected-manifest identity and 06f
hash, producer-seam omissions and the coordinated descriptor/manifest mutation,
`gate_stage`/`evidence_stage` routing negatives, unchanged P0 loader behavior,
unchanged tracked Gate 5 bytes, and O15 disabled. Stephen's D-G6-3 approval cites this
exact plan revision before T2 begins. The P1 limb remains closed to descriptor build and
observation until the later T8 contract-materialization output in 06f §3 is independently
reviewed and accepted by its exact path/schema/blob/SHA identity.

## 7. Sequencing, branches, and review

- Gate 5 is closed. T1a is first. Its accepted protocol hash gates T2, then T3/T4 in
  parallel. Composite T1b follows both provider canaries and completes separate T1b-M
  and T1b-H evidence; its accepted composite evidence-policy hash
  gates the serial T5–T8 chain.
- Branches: `pipe/ars-wp6-2-threshold-protocol` (T1a),
  `pipe/ars-wp6-2-live-adapters` (T2–T4),
  `pipe/ars-wp6-2-evidence-policy` (T1b),
  `pipe/ars-wp6-2-parity-profiles` (T5–T6), `pipe/ars-wp6-2-mh-unblock`
  (T7–T8). Commits use the full repository convention: `[PIPELINE] P00:
  <description>` subject, body describing the change, and the `Co-Authored-By`
  trailer; pre-commit hooks run on every commit, never skipped. Review-then-merge
  with CodeRabbit concluded pre-merge on every PR; adversarial implementation
  review at tranche end.
- Live smoke runs are bounded and budgeted; no live call occurs before T2 merges and
  every T2 negative passes independently for the target provider.

## 8. Stop conditions

- Any live call before accepted T1a protocol and merged/passing T2, or outside an
  atomically reserved T2 cost grant; any credential sentinel reaching invocation or
  any credential material observed in a provider-facing or canonical producer surface.
- Any T5–T8 dispatch, M/H eligibility transition, or observed-calibration claim before
  Stephen accepts the exact composite T1b-M/T1b-H evidence-policy hash; any model-only
  evidence used to unblock an H row or human evidence used to repair an M gap.
- Any code path that defaults parity, a profile, or a threshold comparison to pass.
- Any parity evidence without actual command/receipt/enforcement bindings; any profile
  missing a W4 §10.2/§10.3 field or owner approval.
- T7 attempting to unblock a row administratively; any count-only, relabelled,
  mixed-lifecycle, non-bijective, wrong-provider, or wrong-adapter 302-row closure; any
  06e hash mismatch or expected replacement derived from the observed manifest.
- Provider outage during T7: S-016 semantics apply — wait or `unable_to_grade`;
  never a sub-threshold substitute grader.
- Un-pre-registered invariant drift, as always.
- Any pilot acceptance or claim-promotion path that does not consume the current exact
  54-referent F-037/F-038 union atomically at one expected event position; any 06f hash
  mismatch; any expected-manifest path/blob/SHA mismatch; any descriptor build or
  observation before independent expected-manifest acceptance; or any expected set
  derived from observed results.

## 9. Research assurance triage

- **Lanes:** Output/Provenance primary. Stochastic enters at T1a/T1b-M/T7: T1a is a
  preregistered protocol and makes no observed claim; T1b-M calibration against the
  mutation corpus is a statistical claim — the calibration
  estimand/denominator, frozen corpus and eligibility rule, repeat count/seed,
  resampling or dependence unit, uncertainty/agreement rule, and false-pass/
  false-block characterization are part of the strict T1b-M policy and get independent
  review there, not just software tests. T1b-H is a separate human-evidence lane with
  rubric/disagreement/adjudication review rather than a statistical substitute.
- **Machine-checkable:** the binding tests per task above.
- **Human-review-only:** T1a protocol adequacy; T1b-M statistical evidence adequacy;
  T1b-H rubric, blinded-case, disagreement/adjudication, and attributed-authority
  adequacy; and the composite T1b policy (Stephen + independent review at both gates);
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
