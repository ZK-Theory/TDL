# 06b — WP6.2: Live Capability — Adapters, Parity, Threshold Policy, Evaluated Profiles — Dispatch Plan

**Date:** 2026-07-16
**Status:** draft, review pending — authorizes no implementation and no live provider
call. Dispatch is gated on Gate 5 close (WP5.6), Stephen's approval of this plan, and
— for every task after T1 — Stephen's acceptance of the T1 threshold/calibration
policy (D-G6-2). Implements accepted decision P-033 (no interim operator-executed
mode; wording confirmed 2026-07-17).
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
  policy 05-plan §7.2 requires before M/H capability unblocks: per-grader-class score
  thresholds, calibration procedure against the mutation corpus, repeat/agreement
  requirements, family-diversity rules (inheriting P-023), drift-recheck cadence, and
  the exact evidence a live grader result must carry. This is a policy/owner artifact
  in the W6 lineage, not code; it may be drafted while WP5.6 runs. **Exit:** Stephen's
  recorded acceptance (D-G6-2). Nothing downstream of T1 dispatches without it.
- **T2 — Credential and cost boundary.** Local secret handling for provider
  credentials (environment/config outside the ledger and outside tracked roots —
  a credential must never appear in an event, receipt, object, or fixture; binding
  test greps the control store after a live smoke); per-run token/cost budget fields
  on the W8 resource grant with fail-closed exhaustion (stop, not degrade); cost
  actuals recorded on receipts for W4 profile evidence.
- **T3 — Live Claude transport.** Implement the W7 command/receipt path against the
  local Claude runtime; policy rendering from canonical policy (P-adapter rule: the
  provider file is generated/validated, never hand-forked); token accounting per
  P-030's token rule (provider count or evaluated conservative upper bound; missing
  accounting blocks issue). **Binding tests:** a live echo/smoke fixture round-trips
  with a well-formed receipt; a response violating the receipt schema fails closed.
- **T4 — Live Codex transport.** Same contract, second family. The two-family
  coverage that P-029 makes load-bearing for R3 exists only when both transports pass
  their gates independently — neither inherits the other's evidence.
- **T5 — Live parity evidence.** Extend the WP5.2 variant harness with live rows:
  the W7 semantic, field-by-field, fail-closed parity report computed per live
  provider; one missing critical control blocks that provider's capability;
  aggregate percentages stay diagnostic-only. Determinism handling for live rows is
  declared in advance (live outputs are not byte-stable; parity grades the rendered
  *policy controls*, not the model prose — the report inputs must be the
  deterministic rendered surfaces). **Binding test:** removing one critical control
  from a rendered policy flips that provider to blocked.
- **T6 — Evaluated model profiles and persisted route decisions.** Instantiate W4 §10
  profiles for the initial model set actually intended for early ARS work (at
  minimum: one Claude-family and one Codex-family profile at the capability grades
  the SCALE-01 canary and its reviews require). Each profile records provider,
  family, model/version, reasoning setting, limitations, repeated-fixture results,
  runtime/cost evidence (from T2 receipts), context budget, and evaluation date;
  route decisions persist as canonical records with independence grades recomputed
  against actual producing attempts (P-029 routing rule). **Binding tests:** routing
  rejects a model with no current profile at the required grade
  (`r3_family_coverage_insufficient` surfaces when only one family qualifies);
  a stale profile (past its declared recheck) is ineligible.
- **T7 — M/H unblock run.** Re-run the blocked M/H rows under the accepted T1 policy
  with live graders where their rows require live judgment. Exact expected outcome
  set is pre-registered in this plan's final revision before dispatch (D-G6-3):
  which of the 15 blocked rows are expected to unblock, which remain blocked with
  reasons, and the new `blocked_fixture_count`/`result_count`. A row that fails its
  calibrated threshold stays blocked — the unblock is evidence-driven, never
  administrative.
- **T8 — P1 routing/assurance fixtures F-037–F-038.** Materialize the two reserved
  pre-pilot P1 rows (06b addendum) so the Gate 6 pilot cannot accept evidence or
  promote claims without them, per P-019/P-029.

## 3. Sequencing, branches, and review

```text
T1 (policy, owner) ──accepted──────────────────┐
                                               v
T2 (credentials/cost) ─> T3 (Claude live) ─┬─> T5 parity ─> T6 profiles ─> T7 unblock ─> T8
                          T4 (Codex live) ──┘
```

T1 acceptance is an additional gate on the T5→T6→T7→T8 chain, not an
alternative entry: T5 requires T2–T4 **and** T1; T6 requires T5; T7 requires
T6; T8 requires T7. No task after T1 is eligible from T1 alone.

- T1 may run alongside WP5.6; T2–T4 require Gate 5 closed.
- Branches: `pipe/ars-wp6-2-threshold-policy` (T1 doc), `pipe/ars-wp6-2-live-adapters`
  (T2–T4), `pipe/ars-wp6-2-parity-profiles` (T5–T6), `pipe/ars-wp6-2-mh-unblock`
  (T7–T8). Commits use the full repository convention: `[PIPELINE] P00:
  <description>` subject, body describing the change, and the `Co-Authored-By`
  trailer; pre-commit hooks run on every commit, never skipped. Review-then-merge
  with CodeRabbit concluded pre-merge on every PR; adversarial implementation
  review at tranche end.
- Live smoke runs are bounded and budgeted (T2 grant fields); no live call before T2
  merges.

## 4. Stop conditions

- Any live call outside a T2 cost grant, or any credential material observed in a
  canonical record.
- Any code path that defaults parity, a profile, or a threshold comparison to pass.
- T7 attempting to unblock a row administratively (config edit without the
  calibrated evidence path).
- Provider outage during T7: S-016 semantics apply — wait or `unable_to_grade`;
  never a sub-threshold substitute grader.
- Un-pre-registered invariant drift, as always.

## 5. Research assurance triage

- **Lanes:** Output/Provenance primary. Stochastic enters at T1/T7: threshold
  calibration against the mutation corpus is a statistical claim — the calibration
  procedure and its false-pass/false-block characterization are part of the T1 policy
  document and get independent review there, not just software tests.
- **Machine-checkable:** the binding tests per task above.
- **Human-review-only:** T1 policy adequacy (Stephen + independent review);
  the judgment that a specific model profile's evidence set is sufficient for the
  grade claimed (W4 §21 metrics inform, Stephen accepts).

## 6. Out of scope

- Any research computation, including SCALE-01 itself (Gate 6 territory).
- Ultra/third-family providers — the W4 interface stays provider-generic, but this
  tranche evaluates Claude and Codex only (P-029 first-release boundary). The
  programme's bounded-Ultra R3 lanes need their own profile evidence later.
- Autonomous cost optimization or model-downgrade logic (D-006 stands: eval evidence
  first).
- Changes to the S-016 outage contract or to Gate 5 acceptance artifacts.
