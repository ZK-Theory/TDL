# 05 — WP5: Gate 5 Foundation Acceptance — Scope and Sequencing Plan

**Date:** 2026-07-10
**Status:** scope proposed — awaiting owner approval before any WP5 dispatch
**Goal:** Close Gate 4 formally, then define the exact work standing between the current
state (all WP4 tranches merged; aggregate P0 candidate `blocked`) and Gate 5 foundation
acceptance, so each work package can be dispatched as its own plan (following the
04a/04b pattern) without re-derivation.

**Governing authority:** 04-plan §4 (Gate 5 definition), 05-plan §4.4 (release tranche),
§5 (checkpoints 5–7), §7 (retention/backup-restore extension), §7.2 (live-grader
threshold-policy clause, Gate 5 deferred-scenario row); 06-evaluation §S-014–S-016 rows;
07-runtime-adapters (W7 parity semantics); 04a obligation register O10–O16; 04b register
R8/R12. This plan authorizes no implementation.

---

## 1. Gate 4 close-out record (verified 2026-07-10)

Gate 4's exit ("Stephen approves the implementation plan and its exact foundation
scope") occurred 2026-07-01; the *execution* of that approved scope is what closes now.
Verified on `main` this session:

- **WP4.9 merged** (PR #71, merge `118fcfe`, 2026-07-09). CodeRabbit review concluded
  before merge; all four findings (1 Major: `build_release_decision` doc signature; 3
  Minor) addressed in `770c3f6..83cb7f5`. Codacy SUCCESS.
- **Invariant smoke on `main`:** `eval calibrate` → `blocked_fixture_count: 14`,
  `fixture_count: 37`, `fixtures_with_uncalibrated_mutations: 0`,
  `mutation_calibration: "calibrated"`; `eval run` → `candidate_status: "blocked"`,
  `result_count: 122`. Matches the 04a/04b stop-condition invariants exactly.
- **Test suite:** 338 passed on `main` (`uv run --no-sync pytest tests/research_system`).
- **Registers:** 04a O7/O8 marked delivered by WP4.9 (R10 executed); O9 closed
  (renormalization, 2026-07-08); O13 delivered (WP4.8 Task 7 authorizer binding).
- **O10 partially closed:** `release_gate_decision: rgd` is registered in
  `.research-system/config/id-kind-registry.yaml`. Residual: WP1-reviewer confirmation,
  folded into WP5.6 bounded review (§4 intake table).

**Residual non-gate items (machine-local, not Gate-blocking):**

- `.venv` sync still blocked by open handles (now `coverage-7.13.0.dist-info`; `cfgv`
  RECORD damaged by prior partial attempts). `uv run --no-sync` fully functional.
  Recommended fix when convenient: stop MCP-server sessions, delete `.venv`, fresh
  `uv sync` (repairs the damaged dist-infos too).
- Worktree sweep (manual trigger only): `.apm/worktrees/ars-p0-wp4-8-verdict-derivation`
  and the WP4.9 worktree are sweep-eligible once CodeRabbit conclusions are confirmed;
  three stale detached Codex worktrees likewise.

Gate 4 is **closed**. Everything below is Gate 5 scope.

## 2. Gate 5 acceptance criteria (assembled from governing text)

Gate 5 (04-plan §4): *"The foundation passes its required deterministic tests, P0
fixtures, recovery cases, adapter parity checks, and bounded independent review.
Failures produce revision or stop; they do not weaken the acceptance set."*

Decomposed against the P0 state, Gate 5 requires:

1. **Deterministic tests + P0 fixtures** — already green (338 tests; 37 fixtures
   calibrated; 14 M/H rows blocked by design). The blocked rows *block the affected
   capability*, not the gate per se (05-plan checkpoint 7) — but whether foundation
   acceptance may occur with M/H capabilities still restricted is an owner decision
   (D-G5-1, §6).
2. **Release tranche** — 05-plan §4.4: *"Before Gate 5 foundation release, a follow-on
   release tranche must add at least S-014 backup/restore, S-015 supersession-cycle
   rejection, and S-016 R3 provider-outage handling."* → WP5.4.
3. **Adapter parity checks** — W7 semantic field-by-field fail-closed parity evidence;
   `parity_status` currently `"not_evaluated"` (fails closed; O11). Plus 04b R8: the
   fake-claude/fake-codex variant-matrix rows registered `execution_stage: gate5` must
   actually execute. → WP5.2.
4. **Recovery cases** — Gate-3 scenarios A–E already execute in the harness; S-014
   backup/restore extends recovery coverage and requires the 05-plan §7 deletion-
   verification extension to the registered backup/restore topology before it can pass.
   → WP5.4.
5. **Canonical publication** — the `ReleaseGateDecision` must become a canonical W2
   event (06c §7 step 11; O12); the sentinel `canonical_event_ref="unpublished:p0"`
   must be gone before the decision counts as release evidence. → WP5.3.
6. **Grading-integrity preconditions** — O14 (cross-family independence branch must be
   reachable) and O16 (canonical `current_policy_revision` source) are registered
   Gate 5 dependencies: both must be real before any live M/H grading or live deletion
   path relies on them. → WP5.1.
7. **Bounded independent review** — an adversarial review of the integrated foundation
   (pattern: the 2026-07-07 WP4 full review) whose findings produce revision or stop.
   → WP5.6.

## 3. Obligation intake table

| Source | Obligation | WP5 home |
|---|---|---|
| 04a O10 | `release_gate_decision_id` ID-kind confirmation by WP1 reviewer | WP5.6 (review checklist item; kind already registered) |
| 04a O11 | parity wiring before any `pass` is reachable | WP5.2 |
| 04a O12 | publish release decision as canonical event | WP5.3 |
| 04a O14 | cross-family independence branch reachable (real producer/grader family identities) | WP5.1 |
| 04a O15 | `DeleteEvidenceObject` registration — **owner-gated W1/W6 decision** (name specified at 04-plan:517; payload schema + event semantics are not; design anchor `DeleteEvidenceObject → EvidenceDeletionPending`) | WP5.5 decision D-G5-2; implementation joins WP5.4 (S-014 touches the same deletion surface) once decided |
| 04a O16 | `current_policy_revision` from canonical `retention-policy.yaml` via `validate_retention_policy`, not `registry.policy_revision` | WP5.1 |
| 04b R8 | execute fake-claude/fake-codex variant rows (variant-aware harness) | WP5.2 |
| 04b R12 | two provider-specific sizing rows — deviation flagged in PR #71 body, **owner confirmation not yet recorded** | WP5.5 decision D-G5-4 |
| 05-plan §4.4 | S-014/S-015/S-016 release tranche | WP5.4 |
| 05-plan §7 | deletion verification extended to registered backup/restore topology (S-014 precondition) | WP5.4 |
| 05-plan §7.2 | live-grader threshold policy separately accepted before M/H capability unblocks | WP5.5 decision D-G5-1 |

No other open rows exist in either register. O1–O9, O13 delivered; R1–R7, R9–R11 delivered.

## 4. Work packages

### WP5.1 — Grading-integrity closure (O14, O16)

Small, code-side, no owner input; unblocks the integrity story every later WP relies on.

- **O14:** thread real per-run execution-context identities into `producer_family` /
  `grader_family` at the `graders.validate_grader_result` call sites, replacing the
  never-equal literals (`"reference-subject"` vs `"live-judgment-pending"` /
  `"deterministic-package-grader"`). Binding test: a synthetic same-family
  producer/grader pair under a `cross_family` independence requirement **must be
  rejected** — the branch is exercised, not just present.
- **O16:** in the deletion-manifest authorizer binding
  (`research_system/evals/retention_authorizer.py` + service wiring), source
  `current_policy_revision` from canonical `.research-system/evals/retention-policy.yaml`
  via `validate_retention_policy(...)`. Binding test: a registry loaded with a stale
  `policy_revision` no longer self-validates against its own manifest.
- **Invariants unchanged:** `blocked/14`, `fixture_count 37`, `result_count 122` —
  any drift is a stop condition.
- Branch: `pipe/ars-gate5-grading-integrity`. Commit prefix `[PIPELINE] P00:`.

### WP5.2 — Variant execution and adapter parity evidence (R8, O11)

- **Variant-aware harness:** `run_p0_coverage` (or a sibling entry point) executes the
  `execution_stage: gate5` rows of `.research-system/evals/p0-variant-matrix.yaml`
  (fake-claude / fake-codex adapter, rendering, and F-021 sizing rows) against their
  bound fixture revisions. Determinism per 05-plan §7.3: each variant row run twice,
  byte-identical normalized decisions.
- **Parity evidence:** compute the W7 policy-parity report (semantic, field-by-field,
  fail-closed; one row per normalized semantic control; one missing critical control
  blocks the capability — aggregate percentages diagnostic only) using
  `research_system/adapters/parity.py`; wire the result into release evidence so
  `parity_status` reflects a real report. `pass` stays unreachable until parity is
  evaluated **and** passes; no code path may default parity to pass.
- **Invariant change:** variant execution adds results → `result_count` grows.
  New values must be **pre-registered** (§7) in the WP5.2 dispatch plan before the run,
  with the old values retired explicitly. `blocked_fixture_count` must not change.
- Branch: `pipe/ars-gate5-variant-parity`.

### WP5.3 — Canonical release-decision publication (O12 + O10 residual)

- Register the command/event path that publishes the `ReleaseGateDecision` as a
  canonical W2 event (registered command → emitted event → replay/projection); replace
  the sentinel `canonical_event_ref="unpublished:p0"` with the real event reference.
  The `rgd_` ID kind is already registered.
- Fail-closed rule: `eval release` verification must reject a decision document whose
  `canonical_event_ref` does not resolve to a stored event.
- Branch: `pipe/ars-gate5-release-event`.

### WP5.4 — Release tranche: S-014 / S-015 / S-016 (05-plan §4.4)

The largest package. Three W2 scenarios materialized with the same package/executor/
grader discipline as the F-corpus (06-evaluation §S rows):

- **S-014 backup/restore and machine move** (graders D,T,O,P): dedicated control store
  restored "on another machine"; store/project identity, chain, snapshot, endpoint, and
  external-artefact availability verify before writer lease. Precondition (05-plan §7):
  deletion verification extended to the **registered backup/restore topology** — S-014
  cannot pass before that extension exists. If D-G5-2 has resolved `DeleteEvidenceObject`
  by dispatch time, its registration lands here (same surface); otherwise S-014 scopes
  around it and O15 stays open.
- **S-015 supersession cycle** (D,T): a command introducing a cycle in supersession
  lineage is rejected atomically; prior authority unchanged. Control-plane cycle
  detection in the reducer/command path.
- **S-016 R3 provider outage** (D,T,O,H): required evaluated cross-family provider
  unavailable → task waits or records blocking `unable_to_grade`; **no sub-threshold
  fallback or acceptance**. The H row blocks by the same policy as the existing 14
  M/H rows unless D-G5-1 has landed a live-grader threshold policy — S-016 is expected
  to land **blocked-by-design**, and that is a pass condition for the tranche, not a
  defect.
- **Invariant re-baseline (pre-registered, §7):** `fixture_count 37 → 40`;
  `blocked_fixture_count 14 → 15` (S-016's H grader) unless D-G5-1 changes the M/H
  posture first; `result_count` recomputed from the materialized packages. Exact new
  values are stated in the WP5.4 dispatch plan **before** execution.
- Branch: `pipe/ars-gate5-release-tranche`.

### WP5.5 — Owner-decision batch (no code until decided)

Prepares decision documents; produces vault `[DECISION]` entries, not merges. See §6.

### WP5.6 — Bounded independent review and Gate 5 acceptance run

- Full gates: deterministic test suite, all P0 fixtures (40), scenarios A–E + release
  tranche, variant/parity evidence, retention checks — one integrated run emitting a
  single non-aggregated `ReleaseGateDecision`, published canonically (WP5.3 path).
- **Bounded independent review:** adversarial review of the integrated foundation
  (pattern and depth of `reviews/adversarial-wp4-full-review-2026-07-07.md`), including
  the O10 ID-kind confirmation and verification that no acceptance-set item was
  weakened en route. Findings produce revision or stop — never a relaxed criterion.
- **Exit:** Stephen's recorded acceptance = Gate 5 passed; Gate 6 (greenfield paper
  preflight) becomes eligible.

## 5. Dependency DAG and dispatch sequencing

```text
WP5.1 grading integrity ──┬─> WP5.2 variant + parity ──┐
                          ├─> WP5.3 release event ─────┤
                          └─> WP5.4 release tranche ───┴─> WP5.6 review + acceptance
WP5.5 owner decisions (parallel; D-G5-1/2/4) ─────────────^
```

- WP5.1 first (small; the integrity fixes should exist before parity/tranche evidence
  is generated against them).
- WP5.2/WP5.3/WP5.4 parallelizable after WP5.1 (worktrees, concurrency cap 3–4);
  WP5.4 is the long pole — dispatch it first among the three.
- WP5.5 runs alongside; **D-G5-1 must be decided before WP5.6** (it determines whether
  acceptance is capability-restricted); D-G5-2 before or during WP5.4; D-G5-4 anytime
  before WP5.6.
- WP5.6 last, after all merges land and CodeRabbit reviews conclude.

## 6. Owner-decision points (explicit; do not guess, do not block other lanes)

| ID | Decision | Options / anchor |
|---|---|---|
| D-G5-1 | **M/H grading posture at Gate 5.** 05-plan §7.2: M/H capability stays blocked until a separately accepted live-grader threshold policy exists. | (a) Accept foundation with explicit capability restriction — the 14 (→15) M/H rows stay blocked, restriction recorded in the ReleaseGateDecision; live-grader policy becomes a Gate 6-adjacent follow-on. (b) Draft + accept the live-grader threshold policy first, unblock M/H rows before WP5.6. Option (a) is consistent with 05-plan's "explicit capability restriction" wording and does not weaken the acceptance set; (b) delays Gate 5 behind live-provider work. |
| D-G5-2 | **`DeleteEvidenceObject` registration (O15).** Name specified (04-plan:517); payload schema + emitted event are not. | Design anchor: `DeleteEvidenceObject → EvidenceDeletionPending` (the event `replay.py:90` already consumes but nothing emits). Confirm name+schema+event, or defer past Gate 5 with the capability restriction recorded. |
| D-G5-3 | **Invariant re-baseline approvals.** WP5.2 and WP5.4 change `result_count`/`fixture_count`/`blocked_fixture_count`. | Each dispatch plan pre-registers exact new values; owner approves the plan (and thereby the re-baseline) before execution. Silent drift remains a stop condition. |
| D-G5-4 | **R12 confirmation.** Two provider-specific F-021 sizing rows instead of the plan's single `variant` scalar (no-wildcard rule made one row impossible). Flagged in PR #71 body; merge ≠ recorded confirmation. | Confirm the two-row form (recommended — it is the only spec-consistent shape) and record a `[DECISION]` closing R12. |

## 7. Invariant re-baseline rule

The Gate 4 invariants (`blocked_fixture_count: 14`, `candidate_status: "blocked"`,
`result_count: 122`) are stop conditions **until a WP5 dispatch plan explicitly retires
them**: the plan states old value → new value, why, and the recomputation method; the
owner approves the plan; the task's smoke asserts the new values. `candidate_status`
stays `"blocked"` through every WP5 tranche — only the WP5.6 acceptance run may change
it, and only if D-G5-1 and the full acceptance set permit.

## 8. Research assurance requirements

- **Lanes:** Output/Provenance primary throughout; Stochastic/Topology/Representation
  only at the control boundaries the fixtures encode (unchanged from 05-plan §6).
- **Machine-checkable claims → enforcement artifacts (per WP dispatch plan):**
  - "cross-family branch reachable" → rejection test on a same-family pair (WP5.1);
  - "policy revision canonically sourced" → stale-registry rejection test (WP5.1);
  - "variant rows executed deterministically" → twice-run byte-equality assertions (WP5.2);
  - "parity fail-closed" → missing-critical-control blocks capability test (WP5.2);
  - "decision published canonically" → unresolvable `canonical_event_ref` rejected (WP5.3);
  - "S-tranche invariants" → pre-registered smoke values (WP5.4);
  - "no weakened acceptance set" → WP5.6 review checklist against this §2.
- **Human-review-only:** adequacy of the bounded review itself; D-G5-1 posture.
- Passing software tests remains insufficient — each WP5 dispatch plan carries its own
  research-assurance triage per APM_RULES.

## 9. Out of scope for WP5

- Live provider adapters / live M/H grading implementation (enters only if D-G5-1
  chooses option (b), as its own planned tranche).
- P1 fixtures beyond the release tranche (F-006, F-015–F-019, F-021 promotion,
  F-023–F-024, F-029–F-030, F-037–F-038, S-005, S-007).
- Gate 6 pilot-paper selection and preflight (eligible only after Gate 5 exit).
- Any research-paper computation (P01/P04 lanes are unaffected).

## 10. Gate 5 exit checklist

- [ ] WP5.1–WP5.4 merged via review-then-merge (CodeRabbit concluded pre-merge, every PR).
- [ ] D-G5-1, D-G5-2, D-G5-4 recorded as vault `[DECISION]` entries.
- [ ] All invariant re-baselines pre-registered and approved (D-G5-3 process).
- [ ] Integrated acceptance run: one `ReleaseGateDecision`, canonically published,
      parity evaluated, S-tranche present, capability restrictions (if any) explicit.
- [ ] Bounded independent review delivered; findings dispositioned (revision or stop).
- [ ] Stephen's recorded acceptance.
