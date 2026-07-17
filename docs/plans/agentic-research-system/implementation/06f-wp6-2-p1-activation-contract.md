# 06f — WP6.2 P1 activation expected-source contract

**Date:** 2026-07-17<br>
**Status:** normative plan annex approved under P-036 at exact reviewed plan revision
`fe5f1d40bc8f05f061317c677b5891cea0711249`; authorizes no implementation, activation,
pilot evidence, or claim transition<br>
**Authority:** accepted F-037/F-038 reservation under P-029; parent plan 06b §5;
P-036 plan-revision approval; future expected-manifest acceptance under D-G6-3

This annex is the exclusive expected-side producer for the P1 F-037/F-038 activation
closure. Runtime manifests, ledger records, execution records, and result stores are
observed-side inputs only. They may attach observed IDs and hashes to the obligations
below, but they must not generate, omit, filter, repair, or rename the expected set.

## 1. Canonical baseline result obligations (11)

Each result key is the literal six-tuple
`(fixture_id, fixture_revision, grader_id, grader_class, grader_version, variant_id)`.
The accepted machine-readable row also carries a literal `descriptor_sha256`; the
observed side must supply a passing `grader_result_id` and canonical content hash for
the same tuple. No class-only alias is a result key.

| # | Canonical result key | Required observed binding |
|---:|---|---|
| B01 | `(F-037, 1.0.0, f-037-outcome, D, assurance-claim-v1, baseline)` | `pass`; result ID/hash |
| B02 | `(F-037, 1.0.0, f-037-trajectory, T, assurance-claim-v1, baseline)` | `pass`; result ID/hash |
| B03 | `(F-037, 1.0.0, f-037-research-quality, R, assurance-claim-v1, baseline)` | `pass`; result ID/hash |
| B04 | `(F-037, 1.0.0, f-037-independent-model, M, assurance-claim-v1, baseline)` | `pass`; eligible cross-family model result ID/hash |
| B05 | `(F-037, 1.0.0, f-037-human-authority, H, assurance-claim-v1, baseline)` | `pass`; attributed human result ID/hash |
| B06 | `(F-038, 1.0.0, f-038-outcome, D, domain-pack-applicability-v1, baseline)` | `pass` or independently authorized scientific-D `not_applicable`; result ID/hash |
| B07 | `(F-038, 1.0.0, f-038-trajectory, T, domain-pack-applicability-v1, baseline)` | `pass`; result ID/hash |
| B08 | `(F-038, 1.0.0, f-038-research-quality, R, domain-pack-applicability-v1, baseline)` | `pass`; result ID/hash |
| B09 | `(F-038, 1.0.0, f-038-independent-model, M, domain-pack-applicability-v1, baseline)` | `pass`; eligible cross-family model result ID/hash |
| B10 | `(F-038, 1.0.0, f-038-human-authority, H, domain-pack-applicability-v1, baseline)` | `pass`; attributed human result ID/hash |
| B11 | `(F-038, 1.0.0, f-038-privacy-security, P, domain-pack-applicability-v1, baseline)` | `pass`; result ID/hash |

The exact grader IDs, versions, and fixture revisions above are authoritative plan
contract identities under P-036 at the exact reviewed revision. The future
machine-readable expected manifest containing their literal descriptor hashes still
requires independent review and exact-hash owner acceptance under D-G6-3 before
observation; implementation may not substitute locally convenient aliases.

## 2. Activation obligations (43)

Every activation obligation has its own literal descriptor hash in the accepted
expected manifest defined in §3.
Observed execution/evidence IDs and hashes are populated only from immutable ledger and
execution records after the descriptor has been accepted.

### 2.1 Fixture and case descriptors (13)

| # | Expected logical key | Obligation |
|---:|---|---|
| A01 | `fixture/F-037@1.0.0` | exact accepted F-037 fixture revision and package hash |
| A02 | `fixture/F-038@1.0.0` | exact accepted F-038 fixture revision and package hash |
| A03 | `case/F-037-M01-negative-collapsed-to-failure` | known-bad mutation descriptor/hash |
| A04 | `case/F-037-M02-partial-overwrite` | known-bad mutation descriptor/hash |
| A05 | `case/F-037-M03-superseded-treated-current` | known-bad mutation descriptor/hash |
| A06 | `case/F-037-M04-auto-promote-result-to-claim` | known-bad mutation descriptor/hash |
| A07 | `case/F-038-M01-private-pack-leak` | known-bad mutation descriptor/hash |
| A08 | `case/F-038-M02-meaningless-quantitative-D` | known-bad mutation descriptor/hash |
| A09 | `case/F-038-M03-producer-only-not-applicable` | known-bad mutation descriptor/hash |
| A10 | `case/F-037-KG-01` | known-good descriptor/hash |
| A11 | `case/F-038-KG-01` | known-good descriptor/hash |
| A12 | `case/F-037-SV-01` | safe-variation descriptor/hash |
| A13 | `case/F-038-SV-01` | safe-variation descriptor/hash |

### 2.2 Literal case/repetition executions (22)

Each execution must bind verdict, result ID/hash, trace ID/hash, retained-evidence
ID/hash, producing command/receipt, and exact descriptor hash.

| # | Expected logical key |
|---:|---|
| A14 | `execution/F-037-M01-negative-collapsed-to-failure/rep-01` |
| A15 | `execution/F-037-M01-negative-collapsed-to-failure/rep-02` |
| A16 | `execution/F-037-M02-partial-overwrite/rep-01` |
| A17 | `execution/F-037-M02-partial-overwrite/rep-02` |
| A18 | `execution/F-037-M03-superseded-treated-current/rep-01` |
| A19 | `execution/F-037-M03-superseded-treated-current/rep-02` |
| A20 | `execution/F-037-M04-auto-promote-result-to-claim/rep-01` |
| A21 | `execution/F-037-M04-auto-promote-result-to-claim/rep-02` |
| A22 | `execution/F-038-M01-private-pack-leak/rep-01` |
| A23 | `execution/F-038-M01-private-pack-leak/rep-02` |
| A24 | `execution/F-038-M02-meaningless-quantitative-D/rep-01` |
| A25 | `execution/F-038-M02-meaningless-quantitative-D/rep-02` |
| A26 | `execution/F-038-M03-producer-only-not-applicable/rep-01` |
| A27 | `execution/F-038-M03-producer-only-not-applicable/rep-02` |
| A28 | `execution/F-037-KG-01/rep-01` |
| A29 | `execution/F-037-KG-01/rep-02` |
| A30 | `execution/F-038-KG-01/rep-01` |
| A31 | `execution/F-038-KG-01/rep-02` |
| A32 | `execution/F-037-SV-01/rep-01` |
| A33 | `execution/F-037-SV-01/rep-02` |
| A34 | `execution/F-038-SV-01/rep-01` |
| A35 | `execution/F-038-SV-01/rep-02` |

### 2.3 Summary, policy, applicability, calibration, and activation (8)

| # | Expected logical key | Obligation |
|---:|---|---|
| A36 | `summary/F-037-error-summary-v1` | denominator; false-pass/false-block counts, rates, bounds; uncertainty; exactly the 12 F-037 execution hashes |
| A37 | `summary/F-038-error-summary-v1` | denominator; false-pass/false-block counts, rates, bounds; uncertainty; exactly the 10 F-038 execution hashes; disjoint A36/A37 union exactly 22 |
| A38 | `policy/wp6-live-grader-evidence-policy-v1` | exact accepted composite T1b ID/hash |
| A39 | `applicability/F-038-applicability-qualitative-v1` | independent evidence, attributed authority, decision ID/hash |
| A40 | `calibration/F-037-calibration-v1` | calibration record ID/hash and complete execution-set binding |
| A41 | `calibration/F-038-calibration-v1` | calibration record ID/hash and complete execution-set binding |
| A42 | `activation/F-037-activation-v1` | activation event ID/hash and accepted event position |
| A43 | `activation/F-038-activation-v1` | activation event ID/hash and accepted event position |

The exact activation closure is `13 + 22 + 8 = 43`; the complete atomic dependency is
the disjoint union of B01–B11 and A01–A43, totaling 54 obligations.

## 3. Independently frozen expected manifest and atomic consumer

T8 is split into contract materialization and observation. Before the first descriptor
build or execution observation, the contract author produces
`.research-system/contracts/wp6-2-p1-activation-expected.yaml`, validated by
`.research-system/schemas/evals/p1-activation-expected.schema.json` version `1.0.0`.
The contract author is not the descriptor builder, executor, receipt producer, ledger
loader, or live-evidence producer. A reviewer independent of both author and runtime
implementation checks all rows against this annex and recomputes every descriptor hash;
Stephen accepts the exact manifest repository path, schema ID/version, Git blob ID, and
canonical UTF-8/LF SHA-256 in D-G6-3 before observation is enabled.

The strict manifest contains exactly 54 closed rows: eleven `baseline_result` rows and
43 `activation` rows. Every row contains `obligation_id`, its complete literal logical
key, `obligation_kind`, `descriptor_path`, and literal `descriptor_sha256`, plus the
complete binding requirements stated in §§1–2. It also records this annex's repository
path, Git blob ID, and canonical UTF-8/LF SHA-256. Keys, kinds, paths, hashes, and
requirements are required; `additionalProperties` is `false` at every object level.
Missing, duplicate, extra, relabelled, or observed-derived rows are invalid.

The accepted manifest identity is an immutable expected-side input to the P1 stage
manifest and to pilot-evidence and claim-promotion commands. Those commands read
observed descriptor/result/evidence IDs and hashes only from canonical descriptor,
ledger, and execution stores, then compare the exact sorted 54-row bindings at one
expected event position. The descriptor builder, executor, receipts, live ledger, and
P1 stage manifest may neither produce nor amend the expected manifest. Runtime stores
are comparison input only; neither command nor an observed manifest may declare its own
expected set.

Before observation, one-at-a-time mutations at the public producer seam must omit or
alter each obligation class: baseline result, fixture revision, mutation, known-good,
safe variation, repetition, summary, policy, applicability decision, calibration, and
activation event. Additional mutations cover stale grader version, same-class grader
substitution, duplicate result ID, changed descriptor hash, and expected-set generation
from observed rows. A coordinated-source mutation replaces both descriptor bytes and a
candidate expected manifest with a self-consistent changed hash; it still rejects
because the candidate manifest's Git blob/SHA-256 differs from the D-G6-3 accepted
identity. Every rejection publishes no governing event and leaves the event
tail, accepted-result set, Decision set, activation set, capability state, and claim set
unchanged.
