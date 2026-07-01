# W4/W5 Adversarial-Review Reconciliation

**Date:** 2026-06-30<br>
**Status:** Accepted by Stephen on 2026-06-30<br>
**Review:** `adversarial-W4-W5-review-2026-06-30.md` at commit `dc56ca07`<br>
**Subjects:** W4 v0.2, W5 v0.2, and proposed W6 addendum 06b<br>
**Implementation authority:** None

## 1. Reconciliation outcome

The review verdict `accept_with_required_changes` is technically supported. All four Major and four Minor findings were reconciled in W4/W5 v0.2 and addendum 06b. Stephen approved the reconciliation on 2026-06-30; P-029 records the authority changes and fixture reservation.

| Finding | Disposition | Reconciled location | Remaining authority |
|---|---|---|---|
| W45-M1 requirement-floor/lane-scope independence | Accept | W5 sections 6.2, 7, 9, 11.1, 20–23, 28; W4 sections 9, 11–12, 20–21; F-035 | Accepted under P-029 |
| W45-M2 verifier feasibility before producer dispatch | Accept | W4 sections 11–14, 17, 20–23, 26; W5 sections 16–17, 20–22, 25, 28; F-033/F-035 | Accepted under P-029 |
| W45-M3 under-specified/unreserved F-031–F-038 | Accept | Proposed W6 addendum 06b specifies every required fixture field | Reserved under P-029; executable calibration remains deferred |
| W45-M4 cross-family R3 routability | Accept | W4 sections 6.2, 13–16, 20–23, 26; F-031 | Accepted under P-029 |
| W45-m5 two-family suspension fragility | Accept | W4 sections 6.2 and 16.2 | Covered by M4 |
| W45-m6 risk-vocabulary alignment | Accept | W4 section 9.2; W5 sections 7 and 9 | No separate decision beyond W4/W5 acceptance |
| W45-m7 TDA-pack template boundary | Accept | W5 sections 15, 24; F-038 | No separate decision beyond W5/06b acceptance |
| W45-m8 determinism input set | Accept | W4 sections 6.1–6.3, 11, 13, 21–22; F-031 | No separate decision beyond W4/06b acceptance |

## 2. Major-finding closure

### W45-M1 — requirement integrity

W5 now treats requirement authorship and floor/lane-scope acceptance as a distinct R2/R3 authority. A producer may draft but cannot solely determine the bar:

- R2 requires an authority distinct from the prospective producer or an evidence-derived minimum-I1 confirmation; a pack may require I2;
- R3/P-005 requires I2 cross-family/context scope review plus Stephen's attributed acceptance;
- the complete core-lane universe is enumerated, and every `not_applicable` decision records rationale and authority;
- changing the prospective producer to an incompatible relationship stales requirement acceptance;
- W4 independently compares the requested action/transition with R3/P-005 triggers, so a lower submitted floor cannot suppress the human gate.

F-035 combines the producer-aligned under-floor/omitted-lane attack with two-key non-compensation.

### W45-M2 — verifier feasibility sequencing

W4 now evaluates a producer candidate against at least one currently eligible verifier route before R2/R3 dispatch. The witness binds the prospective producer relationship, verifier profile/eval/policy/snapshot revisions, required capability/grade, and expiry. Absence rejects the producer candidate with `independence_unavailable` before any producing command. Final review recomputes the grade against the actual attempt; the witness is neither review evidence nor dispatch authority.

F-033 calibrates the wasted-run and role-switch attacks. F-035 confirms that a structurally complete producer route cannot bypass the assurance/review half of validity.

### W45-M3 — fixture reservation completeness

Proposed addendum 06b follows the accepted 06a row schema. Every F-031–F-038 design has:

- priority and assurance lanes;
- incident-basis and input-fidelity provenance;
- pre-control setup and expected failure;
- post-control outcome plus required/forbidden trajectory;
- grader classes and dependencies;
- calibration and materialization boundaries.

The addendum remains a proposal until Stephen accepts it. It reserves designs only and creates no executable fixture.

### W45-M4 — R3 family coverage

W4 now publishes a capability-by-family eligibility map. Eligibility, expiry, suspension, or retirement changes recompute it. Fewer than two eligible families for an R3-required capability emits `r3_family_coverage_insufficient`, stales dependent feasibility evidence, and blocks affected R3 dispatch before task-level routing. The first-release Claude/Codex set is therefore explicitly load-bearing rather than assumed sufficient.

## 3. Cross-spec consistency checks

| Invariant | W4 | W5 | W6 proposal | Result |
|---|---|---|---|---|
| W5 sets a producer-independently confirmed bar; W4 cannot weaken it | Requirement acceptance is a hard route gate | Floor, full lane scope, applicability, and authority are immutable | F-035 | Closed in draft |
| R2/R3 producer work is not spent without a feasible verifier | Candidate witness before dispatch; final grade recomputed later | Witness required but cannot satisfy Key B | F-033/F-035 | Closed in draft |
| R3 action semantics cannot be hidden by an R2 label | Independent R3/P-005 action check | Canonical epistemic floor and Stephen gate | F-035 | Closed in draft |
| Deterministic routing has immutable inputs | `RoutingEvidenceSnapshot` binds changing estimates | No routing ownership added | F-031 | Closed in draft |
| Cross-family R3 loss is visible before dispatch | Capability-by-family coverage block | Required diversity remains non-compensable | F-031/F-033 | Closed in draft |
| TDL-private content cannot enter public packs | Route/profile remains domain-neutral | Per-pack distribution scope | F-038 | Closed in draft |
| Fixture enforcement is reservation-grade | Metrics point to 06b | Metrics point to 06b | Complete F-031–F-038 rows | Closed under P-029 |

No raw count from distinct units is compared, and no algorithm/state ordering inversion was introduced. Requirement acceptance precedes route selection; verifier feasibility precedes producer dispatch; final verification follows production; result acceptance remains separate from claim promotion.

## 4. Acceptance effect

Stephen's approval and P-029:

1. accept W4 v0.2 and W5 v0.2;
2. accept addendum 06b as the design reservation for F-031–F-038;
3. append a new decision record amending P-022 for requirement-scope independence and P-024 for the new reservations, while finalizing Q-005 with its two-family R3 coverage condition;
4. update package status documents from `review_pending` to `accepted`/`accepted_reservation`;
5. preserve the P-026 boundary: no runtime, profile, adapter, fixture materialization, migration, pilot, active APM mutation, result reinterpretation, or research claim is authorized.

Any future correction to an authority rule requires a versioned amendment; it cannot be recorded as a silent exception.

## 5. Verification boundary

This reconciliation uses only committed planning/review evidence and synthetic fixture designs. It does not inspect or mutate T1.28, current-paper state, `.apm/`, contracts, results, the research vault, provider credentials, or restricted data.

**Outcome:** `ACCEPTED_RECONCILIATION — W4/W5 v0.2 and 06b close the required review changes under P-029; implementation remains gated`.
