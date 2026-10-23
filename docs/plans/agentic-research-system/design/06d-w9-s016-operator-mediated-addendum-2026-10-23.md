# W6 Addendum — S-017, R3 second-family session unavailable (operator-mediated; W9-D12b)

**Date:** 2026-10-23<br>
**Status:** Draft, revision 3, `review_pending`. It reconciles the review `reviews/wp9-0-review-a427084e-2026-10-23.md`
and the re-review `reviews/wp9-0-re-review-185510bc-2026-10-23.md` (see `reviews/wp9-0-reconciliation-2026-10-23.md`).
It needs the reviewer's confirmation and Stephen's acceptance (P-065).<br>
**Applies to:** `06-evaluation-observability-and-audit.md` version 0.3 (accepted under P-030), and addenda `06a`
and `06b`<br>
**Design authority:**
- P-027 (the W6 catalogue, including S-016);
- P-029 (the two-family R3 rule);
- P-042 (operator-mediated external sessions; ARS never invokes a provider);
- W9 §§11.2 and 12.3 and W9-D12b, accepted on 2026-10-22;
- 06v WP9.0 and O-15;
- P-065 and P-066 (Stephen's decision to give the scenario a new ID, S-017).<br>

**Implementation authority:** None. This addendum creates no fixture directory, grader, trace, profile, route or
runtime. It materializes nothing.

The file name keeps `s016`, the name 06v O-15 gave this addendum. Its content reserves S-017.

## 1. Purpose and precedence

P-027 accepted S-016, "R3 provider outage", in the W6 conformance catalogue (W6 §7). Its premise is a provider-runtime
path: "Required evaluated cross-family provider is unavailable." P-042 removed live provider transports and evaluated
provider profiles from the first release, and ARS never invokes a provider. Gate 7 dispatch is therefore
operator-mediated (W9-D2), and the two-family rule applies at dispatch over P-005's R3 set (W9-D3, W9 §11.2).

W9 §12.3 assigns S-016 to Gate 7 items. It records that, because S-016 is in the P-027 catalogue, its re-specification
needs a dated W6 addendum, not only W9-D12b. This is that addendum.

**Current state of S-016.** S-016 already exists as an executed fixture, and this addendum leaves it unchanged.
- **Package.** `.research-system/evals/fixtures/S-016/` holds it: tree `af1c8691`; `fixture.yaml` blob `4898d9c2`;
  `fixture_id: S-016`; `fixture_revision: r1`; `gate_stage: foundation_release`; priority P1.
- **Graders.** D, T, O and H graders, the H grader being `s-016-human-authority`.
- **Mutation.** `allow_subthreshold_outage_fallback`.
- **History.** Materialized in `ec6be3f0` and `90638eea`.
- **Execution.** It runs in the release tranche: `research_system/evals/coverage.py` `RELEASE_TRANCHE_CASES` and
  `execute_s016` in `research_system/evals/executors/release_tranche.py`.
- **Pins.** The WP6.2 live-grader calibration protocol pins it by tree and blob, with the H-negative case
  `H-NEG-S-016-ALLOW-SUBTHRESHOLD-OUTAGE-FALLBACK`. That protocol is still an author candidate.
- **No provider.** Its stimulus is synthetic and needs no live provider. P-042 defers none of it.

**Precedence.** This addendum follows 06a and 06b. It leaves every existing fixture identity, priority, provenance and
oracle unchanged, and **adds a new ID**, as they did:
- **S-016 r1 stays** the materialized form of the original P-027 row. It stays in the release tranche, executed and
  unchanged, with its pins. Nothing here supersedes it.
- **S-017** is reserved for the operator-mediated scenario: an R3 second-family session is unavailable or ineligible
  at dispatch, or at grading. S-017 is the fixture that applies to Gate 7 items.
- **Reading of W9-D12b.** Stephen reads W9-D12b's words ("S-016's change lands as a dated W6 addendum") as satisfied
  by this addendum, which adds S-017 and records S-016 r1 as unchanged (P-066). W9 §12.3's S-016 row is therefore
  served by S-017 for Gate 7 items. S-016 r1 keeps its own release-tranche role.

The effective W6 catalogue would then contain F-001 to F-038 plus S-001 to S-017.

## 2. The reserved scenario

| ID | Priority / lanes; provenance | Pre-control setup and expected failure | Post-control outcome and trajectory oracle | Graders / dependency |
|---|---|---|---|---|
| S-017 R3 second-family session unavailable (operator-mediated) | P1; gate stage `pilot_promotion`; routing, authority, scientific review, operations; `specification` / `synthetic` | A Task in P-005's R3 set reaches dispatch. W9 §11.2 makes a named operator-mediated session an eligible verifier route only when the dispatch record shows: (a) its model family and version differ from the producer's, as the operator records them; (b) the W4 role profile it runs under declares the capability the item's lane requires; (c) its context is independent of the producer's at the item's required grade (P-022, P-029). The baseline path has no guard. It dispatches in each of these cases (§4): no second family is named; the named session fails (a), (b) or (c); the record is checked by an excluded actor; or the check is recorded after compute starts. In a separate case, the verifier is lost after dispatch, and the baseline substitutes another session at grading. | Dispatch records `r3_family_coverage_insufficient` **before any compute**, and the Task waits or blocks with that typed evidence. There is no same-family fallback, no lowered risk tier, no relabelled role, and no acceptance. The eligibility record is "checked before dispatch by someone other than both the producer and the second-family session itself: the item's independent reviewer, or Stephen" (W9 §11.2). This addendum adds one exclusion: the actor who requested or proposed the dispatch, including the migration analyst (W9 §8.6), never checks it. If the verifier is unavailable or ineligible at grading, the grade is blocking `unable_to_grade`, with no substitute session. A missing or ineligible second family is never a waived pass. | D,T,O,H; W4/W5/W8/W9 dependent |

**Graders.**
- **D:** the dispatch record, the eligibility record and the checker's identity hold the stated values and relations.
- **T:** the trajectory has the refusal before any compute event, and no dispatch, fallback, acceptance or
  substitute-session event.
- **O:** the Task's terminal state is waiting or blocked, with typed evidence and a stated resume condition.
- **H (`s-017-human-authority`):** a human confirms that no acceptance, risk-tier change, role relabel or substitute
  session followed the refusal. The question to the human is: "Did anything after the refusal turn it into a pass?"

**Evidence limit.** P-042 removed *evaluated* provider profiles from the first release. Condition (b)'s evidence is
therefore the accepted W4 role profile's declared capability, not an evaluation result. The fixture records that limit
on the item (W9 §11.2).

## 3. Priority and change-gate effect

- S-017 is P1. It blocks a Gate 7 R3 item's dispatch where it applies (§4), and it blocks release of the WP9.7
  dispatch guard if it fails.
- **Gate stage.** S-017's `gate_stage` is `pilot_promotion`, the stage of W9 §12.3's set, which lists S-016 for Gate 7
  items.
- **Change classes.** S-016 r1 belongs to W6's "provider adapter/hook/skill sync" and "resource/checkpoint operations"
  rows. On acceptance, S-017 is added to two rows of the W6 change-gate table:
  - the "event/task schema or reducer" row;
  - the "agent/model routing" row, **by name**. That row's own rule covers "all P0 fixtures relevant to permitted risk
    tier", and S-017 is P1, so naming it is an explicit addition beyond the rule. It covers dispatch and routing.
- A failed D, T or O grader, or the H grader, is non-compensable. Missing required independence returns blocking
  `unable_to_grade` (W6 §5.3).

## 4. Applicability to Gate 7, and the P01 F-024 exclusion

- **S-017.** For each Gate 7 item, the item's independent reviewer proposes S-017's applicability, and Stephen fixes it
  in the batch decision (W9 §12.3). For an item in P-005's R3 set (pre-registration changes, R3 dispatch, decision
  reversal, claim promotion and adoption) the only permitted outcome is "applicable" (W9-D3, W9 §11.2).
- **F-024, qualitative artefact lifecycle, is excluded for P01 only** (W9-D12b). P01 holds no qualitative legacy
  artefact (W9 §12.3). This exclusion is an owner-accepted applicability record, not a catalogue change. F-024 is
  reassessed at P04's intake.
- **W9 §12.3 erratum.** W9 §12.3's closing sentence gives "S-016's H row" as an example of an exclusion. Its own S-016
  row says the H row stays. The H row is not excluded; the row governs. This is recorded as an erratum in the register
  (P-066), with no edit to W9's bytes. Here the H row is S-017's H grader.

## 5. Materialization

Candidate home: WP9.7, alongside the dispatch guard W9-T12 tests (06v WP9.7, after U-2). The home is fixed at WP9.7's
dispatch, where it is added as an obligation; it is not in 06v's WP9.7 scope today.

**Normalized trace.** S-017's normalized trace binds:
- the dispatch record;
- the named session's recorded family, version and role profile;
- the eligibility record, with its checker's identity and the check's time;
- the first compute event's time, if any;
- the `r3_family_coverage_insufficient` evidence, or the `unable_to_grade` grade.

**Pre-control failures.** Each case below is one stimulus. The baseline path, which has no guard, fails each one:
1. **No second family.** The R3 item is dispatched on a same-family session, or accepted with no second family named.
2. **Condition (b).** The named session's role profile does not declare the lane's capability, and dispatch proceeds.
3. **Condition (c).** The named session's context is not independent at the required grade, and dispatch proceeds.
4. **Excluded checker.** The eligibility record is checked by the producer, by the named session, or by the requester
   of the dispatch, and dispatch proceeds.
5. **Late check.** The check is recorded after the first compute event, and the item is treated as covered.
6. **Lost verifier.** After dispatch, the verifier is unavailable or ineligible at grading. The baseline substitutes
   another session, or passes the grade.

**Post-control outcome.** Cases 1 to 5 are refused before compute, with typed evidence. Case 6 records blocking
`unable_to_grade`, with no substitute.

**Privacy.** No fixture uses T1.28, active APM state, raw restricted data, full transcripts, secrets or hidden
reasoning (W6 privacy and no-live-task constraints).

## 6. Outcome

**Outcome:** `DRAFT — S-017 reserved for the operator-mediated R3 second-family scenario; S-016 r1 unchanged and
executed; F-024 excluded for P01 only`. On Stephen's acceptance, the status becomes `accepted_reservation`, and the
design README lists this file.
