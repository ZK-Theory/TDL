# W6 Addendum — S-016 under operator-mediated sessions (W9-D12b)

**Date:** 2026-10-23<br>
**Status:** Draft, revision 1, `review_pending`. It needs an independent review and Stephen's acceptance (P-065).<br>
**Applies to:** `06-evaluation-observability-and-audit.md` revision 0.2, and addenda `06a` and `06b`<br>
**Design authority:** P-027 (the W6 catalogue, including S-016); P-042 (operator-mediated external sessions; ARS never
invokes a provider); P-029 (the two-family R3 rule); W9 §§11.2 and 12.3 and W9-D12b, accepted on 2026-10-22; 06v WP9.0;
P-065<br>
**Implementation authority:** None. This addendum creates no fixture directory, grader, trace, profile, route or
runtime. It materializes nothing.

## 1. Purpose and precedence

P-027 accepted S-016, "R3 provider outage", in the W6 conformance catalogue (`06-…audit.md` §7). Its premise is a
provider-runtime path: "Required evaluated cross-family provider is unavailable." P-042 removed live provider transports
and evaluated provider profiles from the first release, and ARS never invokes a provider. Gate 7 dispatch is therefore
operator-mediated (W9-D2), and the two-family rule applies at dispatch over P-005's R3 set (W9-D3, W9 §11.2).

W9 §12.3 assigns S-016 to Gate 7 items. It records that, because S-016 is in the P-027 catalogue, its re-specification
needs a dated W6 addendum and not only W9-D12b. This is that addendum.

**Precedence.** The addendum follows 06a and 06b and **does not rewrite** the P-027 identity of S-016:
- the original row stays as the **provider-runtime variant** `S-016/PR`, deferred with WP6.2 provider automation
  under P-042;
- this addendum adds the **operator-mediated variant** `S-016/OM`, which is the variant that applies to the first
  release and to Gate 7 items.

## 2. The operator-mediated variant

| ID | Scenario | Required oracle | Graders |
|---|---|---|---|
| S-016/OM R3 second-family session unavailable | A Task in P-005's R3 set reaches dispatch. No operator-mediated session is available that meets W9 §11.2's eligibility test: (a) model family and version differ from the producer's, as the operator records them; (b) the W4 role profile it runs under declares the capability the item's lane requires; (c) its context is independent of the producer's at the required grade (P-022, P-029). Either no session is named, or the named session fails (a), (b) or (c). | Dispatch records `r3_family_coverage_insufficient` **before any compute**. The Task waits or blocks with that typed evidence. There is no same-family fallback, no lowered risk tier, no relabelled role, and no acceptance. The eligibility record is checked by someone other than both the producer and the named session (W9 §11.2). The `unable_to_grade` H row stays: a missing or ineligible second family is never a waived pass. | D,T,O,H |

**Evidence limit.** P-042 removed *evaluated* provider profiles from the first release. Condition (b)'s evidence is
therefore the accepted W4 role profile's declared capability, not an evaluation result. The fixture records that limit
on the item (W9 §11.2).

## 3. Applicability to Gate 7 and the P01 F-024 exclusion

- **S-016/OM** binds every Gate 7 item in P-005's R3 set: pre-registration changes, R3 dispatch, decision reversal,
  claim promotion and adoption (W9 §11.2, §12.3). The item's independent reviewer proposes it as applicable, and
  Stephen fixes it in the batch decision (W9 §12.3).
- **F-024, qualitative artefact lifecycle, is excluded for P01 only** (W9-D12b). P01 holds no qualitative legacy
  artefact (W9 §12.3). This exclusion is an owner-accepted applicability record, not a catalogue change. F-024 is
  reassessed at P04's intake.

## 4. Materialization

- S-016/OM is materialized and calibrated together with the WP9.7 dispatch guard that W9-T12 tests (06v WP9.7, after
  U-2). Its normalized trace binds:
  - the dispatch record;
  - the named session's recorded family, version and role profile;
  - the eligibility checker's identity;
  - the `r3_family_coverage_insufficient` evidence.
- **Pre-control failure:** a dispatch path without the guard dispatches the R3 item on a same-family session, or
  accepts it when no second family is named.
- **Post-control outcome:** refusal before compute, with typed evidence.
- No fixture uses T1.28, active APM state, raw restricted data, full transcripts, secrets or hidden reasoning (W6
  privacy and no-live-task constraints).

## 5. Outcome

**Outcome:** `DRAFT — S-016/OM proposed as the first-release variant of S-016; the provider-runtime variant S-016/PR is
retained and deferred under P-042; F-024 is excluded for P01 only`. On Stephen's acceptance, the status becomes
`accepted_reservation` and the design README lists this file.
