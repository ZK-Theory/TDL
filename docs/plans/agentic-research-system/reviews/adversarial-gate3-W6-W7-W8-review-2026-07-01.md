# Adversarial Review — Gate 3: W6 v0.3, W7 v0.1, W8 v0.1, and manifest 06c (joint)

**Reviewer:** Independent adversarial review (Claude Opus 4.8), commissioned by Stephen
**Date:** 2026-07-01
**Subjects:** `design/06-evaluation-observability-and-audit.md` (W6 v0.3 interface extension),
`design/07-runtime-adapters-and-policy-parity.md` (W7 v0.1),
`design/08-resource-checkpoint-and-operations.md` (W8 v0.1), and
`design/06c-gate3-foundation-critical-interface-manifest-2026-07-01.md` (06c v0.1) —
all introduced at commit `a4fd774`, reviewed jointly as they require.
**Baseline:** accepted W1 v0.3, W2 v0.3, W3 v0.2, W4 v0.2, W5 v0.2; addenda `06a`
(F-025–F-030) and `06b` (F-031–F-038); D-001–D-008, P-001–P-029.
**Method:** `adversarial-design-review` skill; fresh-context attack against direct evidence.
**Verdict:** **`accept_with_required_changes`**

---

## 0. Executive summary

The three underlying specifications are strong and fail closed. W6 v0.3 cleanly separates
`FixtureDefinition`/`TraceEnvelope`/`GraderResult`/`EvaluationRun`/`CoverageManifest`/
`ReleaseGateDecision`, keeps critical D/T/P and required R/M/H non-compensable, and refuses
to install a permissive threshold default. W7 makes parity semantic and fail-closed, requires
a complete provider receipt before any dispatch/review satisfaction, and forbids a poorer
projection from overwriting richer policy (the sync hazard, correctly generalised). W8 turns
resources, feasibility, leases, process identity, checkpoints, stop-confirmation, orphans, and
restore into typed evidence and never lets operational success stand in for science. The
classic attacks all fail (§3).

It accepts subject to required changes. **No Critical, no rework.** The striking result is
*where* the cracks are: not in W6/W7/W8, but in the **06c manifest whose entire purpose is
seam coherence** — and which currently violates three of its own freeze criteria. It
linearizes two genuinely two-stage dependencies into single steps, hiding real upstream
dependencies and creating apparent temporal inversion (G3-M1); it defines the `gate_stage`
field with a **different enumeration than W6**, the field's sole owner (G3-M2); and its
shared-identity list **drifts from the owning specs' identifiers**, including one identity
(`routing_snapshot_id`) that is consumed but never defined (G3-M3). The underlying specs are
right; the joint contract that is supposed to prove they fit needs the fixes.

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — |
| Major | 3 | G3-M1 … G3-M3 (all in 06c) |
| Minor | 4 | G3-m4 … G3-m7 |

No reviewed document was edited (proposals only, per precedent). Change log in §10.

---

## 1. Scope, authority, currency, and evidence verified

**Authority respected:** D-001–D-008 and P-001–P-029 are Stephen-approved; I challenge none.
The four docs are explicitly `review_pending` and invite this joint review (06c §19, W6 §30,
W7 §26, W8 §27). I created only the review deliverable; touched no `.apm/`, contract, result,
vault, T1.28, or no-migration artefact, and used no active task as an experiment.

**Currency (clean):** HEAD is `a4fd774`; all four docs committed and clean. The reconciliation
loop is working: my W4/W5 review (`dc56ca07`) was accepted as W4/W5 v0.2 (`cc27a86`, P-029),
which **integrated all four W4/W5 findings** — W45-M1 (P-029 "the AssuranceRequirement
epistemic floor, complete lane scope, and every `not_applicable` rationale must be set by an
authority distinct from the prospective producer"; fixture F-035), W45-M2 (P-029 "before
R2/R3 producer dispatch, W4 must demonstrate at least one eligible verifier route"; F-033),
W45-M3 (the `06b` addendum reserving F-031–F-038 with full oracles/graders), W45-M4 (P-029
`r3_family_coverage_insufficient`; F-031). Gate 3 builds on that reconciled baseline. No dated
addendum needed.

**Direct-evidence citation checks (verified, not from summaries):**

| Claim | Verified against | Result |
|---|---|---|
| W7 cites "F-020, F-028, F-031–F-034, S-006/S-007/S-013/S-016" | W6 §6/§7 + `06b` | **Accurate** |
| W8 cites "F-003, F-007–F-010, F-032–F-034, S-003–S-004/S-009–S-012/S-014/S-016" | W6 §6/§7 | **Accurate** |
| W6 §14 "routing/assurance fixtures F-031–F-036" P0, "F-037–F-038" P1 | `06b` §3; P-029 | **Accurate** |
| 06c/W6/W7/W8 cite "P-029", "W4/W5 v0.2 accepted" | register P-029 | **Accurate** (P-029 exists once; amends P-022/P-024, finalizes Q-005) |
| `06b` F-033 = "producer-correlation + pre-dispatch verifier feasibility"; F-035 = "requirement-scope integrity + two-key" | `06b` §2 | **Accurate** — my W45-M1/M2 became named P0 fixtures |

No miscitation found in any of the four documents. Evidence fidelity is again a strength.

---

## 2. Major findings (all in the 06c manifest)

### G3-M1 — 06c linearizes two-stage dependencies into single steps, hiding upstream dependencies and creating apparent temporal inversion *(Major; headline)*

**Claim.** 06c §3 (dependency direction) and §7 (lifecycle ordering) present a single linear
chain. Two participants that are genuinely **two-stage** are shown once, and in the wrong
place:

- **(i) The W3 bound-provider token gate.** §7 step 2 asserts "current W3 context candidate
  and **both token gates**", then step 3 is W4 route and step 6 is the W7 provider command.
  But the *second* gate — exact bound-provider count ≤ 80% capacity (P-028) — depends on the
  W4-**selected** provider and the W7 **adapter tokenizer**, which the same ordering places at
  steps 3 and 6. It cannot be satisfied at step 2. This contradicts W3 v0.2's own accepted
  lifecycle (`compiled` → W4/W7 route+count → `validated` → `issued`, per the W3 v0.2
  delta-review §3.2) and W7 §13/§20 ("provider accounting unavailable/stale → block the W3
  provider gate and issue"), which re-evaluate the provider gate at the W7 command, not at the
  context candidate.
- **(ii) The W8 operational risk floor.** §3/§7 place *all* of W8 downstream of W4 (§7 step 5,
  after step 3 W4). But W4 eligibility and `effective_risk = max(task, W5_floor,
  W8_operational_risk_floor, human_raise)` (W4 §9.2) **consume** a W8 operational-risk input
  (W4 §5.1: "W8 operational constraints that raise risk or make a route unavailable"; W8 §11:
  "W8 owns `W8_operational_risk_floor`… W4 computes the maximum"). So W8's risk-floor/
  feasibility must **precede** W4 routing; only the resource *grant/lease* follows the route.
  The manifest shows W8 once, as the downstream grant, omitting the upstream floor.

**Why it crosses a boundary.** 06c's freeze criteria (§17) require "algorithm ordering matches
state-machine ordering" and "no temporal inversion" (§18 Q2). As written, a reader/implementer
following §7 would (i) treat the provider gate as satisfied before the provider is known, and
(ii) route before the operational risk floor is set — the exact inversions the manifest exists
to prevent. The individual specs fail closed (W7 re-checks the gate; W4 consumes the W8 floor),
so this is a **coherence defect in the contract**, not a hole in the guarantees — but it is a
Major because the manifest is the artefact Gate 3 freezes as the source of ordering truth.

**Failure scenario.** A P0-plan author implements §7 literally: the compiler validates only the
reference-token gate at candidate time, routes, and issues without a W7 exact-provider re-check
(because §7 marked "both token gates" done at step 2); an oversized packet reaches a denser-
tokenizer provider. W7 §13 would catch it — but the manifest told the author both gates were
already satisfied.

**Disposition: amend (required before freeze).** Rewrite §3/§7 so each two-stage participant
appears at both stages: W8 **feasibility/operational-risk-floor before W4** and **grant/lease
after the route**; the W3 provider gate as **conservative upper-bound over the eligible
provider set before routing** and **exact bound-provider re-check at the W7 command, before
issue**. Add these two evaluation points to the §16 units row and the §17 freeze criteria.

**Affected:** 06c §3, §7, §16, §17; W3 v0.2 §8/§10; W4 §9.2; W7 §13; W8 §11.

---

### G3-M2 — `gate_stage` has two incompatible enumerations across the two documents that define it *(Major)*

**Claim.** 06c §5 assigns the `gate_stage` field solely to W6. Yet the two documents enumerate
it differently:

- **06c §9:** `gate3_spec_review`, `gate3_interface_evidence`, `gate5_foundation_release`,
  `pre_pilot`.
- **W6 §26:** `interface_review`, `p0_materialization`, `foundation_release`, `pilot_promotion`.

These are not a rename: the **partitions differ**. 06c splits Gate 3 into two sub-stages
(`spec_review` + `interface_evidence`) and has **no** materialization stage; W6 has a single
`interface_review` plus a `p0_materialization` stage that 06c lacks. Coverage/release logic
(W6 §24/§25) and the 06c priority-vs-stage rule both consume `gate_stage`, so a consumer using
one vocabulary cannot interpret the other.

**Why it matters.** 06c §5 states: "If two documents define the same semantic field
differently, the joint gate fails; 06c does not choose a winner silently." By its own rule this
is a joint-gate-fail — introduced by the manifest itself. §18 Q1 ("does any field have two
owners or no owner?") and the freeze criterion "W6 priority and `gate_stage` are
non-overlapping" are both unmet, because the field has one owner (W6) but two definitions.

**Disposition: fix now.** W6 owns `gate_stage` (per §5); make W6 §26's enumeration canonical
and have 06c §9 reference it, adding an explicit gate-number → stage-name mapping (e.g.
Gate 3 = `interface_review`; Gate 4/5 = `foundation_release`) rather than inventing
`gate3_`/`gate5_` values. Reconcile the missing `p0_materialization` stage into the shared set.

**Affected:** 06c §9, §17; W6 §26; P-024/P-028/P-029 fixture staging.

---

### G3-M3 — 06c §4 shared-identity bindings drift from the owning specs; `routing_snapshot_id` is consumed but undefined *(Major)*

**Claim.** The manifest's central value is one canonical identity per binding. Yet 06c §4
drifts from the owning specs:

- `trace_envelope_id` (06c §4) vs **`trace_id`** (W6 §19/§21);
- `grader_result_ids` (06c §4) vs **`grader_result_id`** (W6 §19/§22);
- `profile_eval_id` (06c §4) vs **`model_eval_profile_id` / `mep_`** (W4 §6.1);
- **`routing_snapshot_id`** is consumed by 06c §4, W7 §9 ("routing-snapshot IDs/hashes"), and
  `06b` F-031 ("routing-evidence snapshot"), but **has no defining entry in W4's identity
  catalogue** (W4 §6.1 defines `rrq/rcd/rte/rtf/ind`, no snapshot ID/prefix).

**Why it matters.** 06c §17 requires "every shared field has one semantic owner and all
consumers reference it consistently." Naming drift breaks "consistently"; an undefined-but-
consumed identity breaks "one semantic owner." An implementer wiring the trace envelope or the
routing evidence has no single authoritative name/prefix to bind.

**Disposition: fix now + one erratum.** Reconcile 06c §4 to the owning specs' exact identifiers
(`trace_id`, `grader_result_id`, `model_eval_profile_id`). Define the routing-evidence snapshot
identity and prefix in W4 (a small W4 v0.2 erratum, e.g. `routing_snapshot_id` / `rsn_`, owner
W4) so W7/06c/06b reference a real definition. Add a manifest self-check: every §4 binding
resolves to a defining spec section.

**Affected:** 06c §4; W6 §19/§21/§22; W4 §6.1 (erratum); W7 §9; `06b` F-031.

---

## 3. Why the strongest attacks on the guarantees *fail* (demonstrated)

Per method — the manifest's own §18 questions, answered against the underlying specs:

- **"Later receipt repairs an earlier missing authority?"** (§18 Q2) No — 06c §7 "no later
  success repairs an earlier absent authority"; W6 §18 "must not repair or reinterpret";
  W7/W8 receipts are evidence-to-validate, never state. (The *ordering presentation* is M-1,
  not a repair path.)
- **"W7/W8 self-grade evidence consumed by W6?"** (§18 Q4) No — 06c §5 "producer/provider/ops
  cannot self-grade"; W7 §4 "never declare fixture pass"; W8 §4 "never self-grade."
- **"W6 infers a provider/resource fact absent from evidence?"** (§18 Q5) No — W6 §21 trace is
  "complete only when every issued command/grant has a terminal receipt or explicit
  missing-evidence record"; missing critical evidence → `unable_to_grade` (blocking).
- **"Provider success satisfies ARS without a normalized receipt?"** (W7 §25 Q3) No — W7 §10
  "incomplete receipts … cannot satisfy dispatch, delivery or review gates"; §19 "if exact
  bytes/model identity/receipt cannot be proven, dispatch/review satisfaction fails even when
  output exists."
- **"Operational success substitutes for scientific validity?"** (W8 §26 Q8) No — W8 §4/§11/
  §17.4; 06c §8 "operational evidence cannot decide science."
- **"Sleep/reboot/PID reuse preserves a false process identity?"** (W8 §26 Q3) No — W8 §13/§14
  bind host/boot/PID-start/executable identity; PID reuse breaks identity.
- **"Blind sync erases a richer safeguard?"** (W7 §25 Q6) No — W7 §14 "a richer destination
  cannot be overwritten by a poorer source"; divergence blocks eligibility.
- **"`gate_stage` demotes a P0 failure?"** (§18 Q6) No — priority is a separate, non-editable
  field (W6 §26); but the enum split (M-2) must be fixed so coverage logic reads it correctly.

The pattern: the guarantees hold; the manifest's *coherence* (ordering, field names, enum) is
what needs the fixes.

---

## 4. Minor findings and editorial

- **G3-m4 — provider-token-gate ownership is split (06c §5).** §5 assigns "token gates" to W3,
  but the provider token **count** is a W7 receipt field (W7 §10) and the exact re-check happens
  at the W7 command. Distinguish, in §5, the token-gate **rule** (W3) from the provider-count
  **evidence** (W7). Sub-point of M-1; keep for the field-ownership matrix.
- **G3-m5 — W8 has no minimal R0/R1 operational fast-path.** Every provider command needs a W8
  grant + lease + heartbeat cadence policy (W8 §1.2, §12: "missing accepted values blocks lease
  activation"). For a seconds-long R0 model call this is heavy (P-025 proportionality). Define a
  minimal operational profile (trivial grant, no benchmark, default-but-declared cadence). Note
  the W3-m9 precedent: this may be resolved as *one* schema with explicit empty/inapplicable
  groups rather than a separate R0 variant — Stephen's call.
- **G3-m6 — provider wrapper/system tokens vs the 20% reserve (W7 §13).** W7 records "whether
  any provider wrapper/system material is included" but does not state that wrapper/system
  tokens are counted and **reduce usable input before the 80% managed gate**. A large provider
  wrapper could push wrapper+managed over capacity while each is individually "within budget."
  State that wrapper/system tokens are accounted against the reserve and fail closed. Ties to
  M-1's provider-gate accounting.
- **G3-m7 — F-010 double-owning (W8 §24 vs W6 §6/W5).** W8 §24 claims F-010 (downstream
  correction overreach) "where operational scope expands." F-010's oracle is primarily a
  scientific/assurance scope fixture (W6 §6: topology/provenance; graders D,T,R). Scope W8's
  claim to the *operational* sub-case only, so F-010's oracle is not split across W5 and W8
  owners. Minor clarity.

No broken links or malformed markup found in any of the four documents.

---

## 5. Answers to the manifest's joint review questions (06c §18)

The user-relevant "key questions." Post-fix:

1. **Field with two owners / no owner?** Yes — `gate_stage` has two definitions (M-2);
   `routing_snapshot_id` has none (M-3).
2. **Later receipt repairs earlier authority?** No (design); but the *ordering* misrepresents
   two-stage participants (M-1).
3. **Token/work-unit counts compared across incompatible units?** Not in the specs (W3/W7 keep
   tokenizers separate; W8 declares units) — but 06c §7's "both token gates at step 2" obscures
   the provider gate's dependency on the later provider/tokenizer (M-1).
4. **W7/W8 self-grade W6 evidence?** No.
5. **W6 infers absent facts?** No.
6. **`gate_stage` demotes a P0 failure?** No (priority separate) — fix the enum (M-2).
7. **Outage/sleep/crash/restore weakens independence/context/authority?** No — scenarios B/D +
   W7 §19 + W8 §13/§19 preserve every requirement.
8. **Do scenarios A–E expose every material seam?** Mostly — but none exercises the **two-stage
   ordering** of M-1 (provider-gate re-check; W8 floor-before-route). Add an ordering assertion
   to scenario A (R2 production) so the P0 plan tests it.

Every "yes/partial" reduces to M-1, M-2, or M-3 — all in 06c.

---

## 6. Decision audit

| Decision | Gate 3 interaction | Disposition |
|---|---|---|
| D-001–D-008 | Domain-general, local, separated authorities; W6/W7/W8 uphold via typed evidence + non-compensable gates | **Keep** |
| P-001/P-020/P-021 | Canonical storage / single writer / non-shared paths — W7 §4/§9 submit via W2, never write events; W8 §4 same | **Keep** |
| P-005 / P-022 | Human-reserved + graded independence — W6 §5.3/§25, 06c §7 step 10 keep claim promotion on the P-005 path | **Keep** |
| P-011 | Multidimensional artefact authority — W6 grader classes + W8 orphan/late-artefact handling | **Keep** |
| P-023 | Independent property grading — W6 §5.1 (D/T recompute), §22 (no pass from producer attestation) | **Keep** |
| P-024 | Fixture provenance + reserved IDs — W6 §20 carries two-axis provenance; `06a`/`06b` intact | **Keep** |
| P-025 | Proportional profiles — **W8 lacks a minimal R0 operational path (m5)** | **Keep; address via m5** |
| P-026 | Successor sequence — Gate 3 advances specs, authorizes no implementation | **Keep** |
| P-027 | W1/W2/W6-catalogue acceptance — W6 §16 first-pass gate preserved as history | **Keep** |
| P-028 | W3 v0.2 + two token gates — **06c ordering misrepresents the provider gate (M-1)**; W7 §13 correct | **Keep; fix 06c (M-1)** |
| P-029 | W4/W5 v0.2 + F-031–F-038 + verifier-feasibility + `r3_family_coverage_insufficient` — W6/W7/W8 consume correctly | **Keep** |
| A-001/A-002 | T1.28 / Phase-2 pending — Gate 3 does not depend on them; W6 §14/W8 §3.2 bar them | **No action** |
| Q-005 | Generic interface, Claude+Codex first release — W7 §4/§16, "Codex absence is a parity finding, not permission to drop control" | **Keep (finalized by P-029)** |
| Q-001/Q-002/Q-003/Q-004/Q-006/Q-007 | Out of Gate 3 scope or already dispositioned upstream | **No action** |

Fixtures F-001–F-038 + S-001–S-016: all **carried unchanged**; W6 v0.3 adds only the
`gate_stage` field (fix its enum, M-2) and the executable-interface contracts (§§19–29). W6 §30,
W7 §26, W8 §27, 06c §19 review gates: dispositioned in §7 below.

---

## 7. Cross-spec consistency matrix

Invariant → owner/enforcement → consumer/test. Gaps flagged.

| Invariant | Owner (06c §5) | Enforcement | Consumer/fixture | Status |
|---|---|---|---|---|
| One semantic owner per shared field | 06c §5 | §5 matrix | scenarios A–E | **GAP — `gate_stage` two defs (M-2); `routing_snapshot_id` none (M-3)** |
| Algorithm ordering = state-machine ordering | 06c §7/§17 | §7 chain | §11 scenario A | **GAP — two-stage participants linearized (M-1)** |
| Provider/ops success ≠ canonical state | W2 | W7 §4, W8 §4, 06c §8 | F-020, S-013 | **OK** |
| Provider gate exact re-check before issue | W3/W7 | W7 §13/§20 | F-028 | **OK in specs; 06c ordering hides it (M-1)** |
| W8 floor feeds W4 risk | W8 §11 → W4 §9.2 | W4 max() | F-009 | **OK in specs; 06c omits the upstream step (M-1)** |
| Non-compensable critical graders | W6 | §5.3, §25, §27 | all P0 | **OK** |
| Complete receipt before satisfaction | W7 | §10, §19 | F-032, S-016 | **OK** |
| Checkpoint compatibility predicate | W8 | §16 | S-004 | **OK** |
| No self-grade | 06c §5 | W6 §18, W7 §4, W8 §4 | F-014 | **OK** |
| Priority ⟂ gate_stage | W6 §26 | — | catalogue crosswalk | **OK conceptually; enum split blocks it (M-2)** |

---

## 8. Practicality and proportionality

- **R0/R1:** W6 evidence overhead is machine-generated (traces/receipts). The live cost is the
  W8 grant/lease/heartbeat machinery for trivial work (m5) — the one proportionality gap; fix
  with a minimal operational profile or the one-schema/empty-groups pattern (per W3-m9).
- **R2:** the Gate 3 flow (route → parity → grant → receipt → trace → grade) is heavy but every
  step is a real control the programme wants; 06c scenario A drives it. Fix M-1 so the P0 plan
  tests the ordering.
- **R3:** cross-family + `r3_family_coverage_insufficient` (P-029/F-031) is now surfaced early —
  a genuine improvement from the W4/W5 round.
- **Long-run compute:** W8 (benchmark counts hidden prerequisites, checkpoint predicate, stop
  confirmation, sleep/resume) is the strongest part of Gate 3 and directly encodes the
  T1.6/T1.28/T1.9 lessons. No proportionality concern beyond m5.
- **Non-TDA / template:** W7 §24/W8 §25 keep TDL paths/hosts out of templates; W6 §12 separates
  private/public fixtures; F-038 tests the distribution-scope boundary. Sound.

---

## 9. Proposed revision plan

**Immediate corrections (fix now):**
- M-2 (`gate_stage` single canonical enum, owned by W6, with a gate-number mapping in 06c §9).
- M-3 (reconcile 06c §4 identity names to the owning specs; W4 erratum defining
  `routing_snapshot_id`/`rsn_`).
- m4 (rule-vs-evidence ownership in 06c §5), m6 (W7 wrapper-token accounting), m7 (F-010
  operational sub-scope).

**Stephen / Manager decisions (touch the frozen ordering / a proportionality policy):**
- **M-1** — rewrite 06c §3/§7 to show W8 (floor before route, grant after) and the provider
  token gate (conservative-then-exact) as two-stage, and add the ordering assertion to scenario
  A. (Changes the interface ordering the manifest freezes — needs sign-off before the P0 plan.)
- **m5** — decide the minimal R0/R1 operational profile vs the one-schema pattern (P-025).

**Later-work dependencies (do not block the conceptual set, do block the freeze):**
- The 06c freeze criteria (§17) cannot all be ticked until M-1/M-2/M-3 land; the P0
  materialization plan must not start until 06c is frozen.

---

## 10. Residual risks after proposed changes

1. **Ordering realism (M-1):** even corrected, the two-stage provider-gate/W8-floor flow is the
   subtlest part of the foundation; the P0 plan must include an explicit ordering fixture
   (extend scenario A / F-028 / F-032) so an implementation cannot collapse the stages again.
2. **`gate_stage` semantics (M-2):** once unified, coverage/release logic depends on every
   fixture carrying the correct stage; a stale or mis-assigned stage silently mis-schedules
   evidence — worth a deterministic validator in the P0 plan.
3. **Identity coherence (M-3):** the manifest should carry a self-check that every §4 binding
   resolves to a defining spec section, or the drift recurs as specs revise.
4. Everything the underlying specs cover — parity, receipt-completeness, checkpoint
   compatibility, non-compensable grading, no-self-grade, restricted-data denial — is closed.

---

## 11. Change log and verification evidence

- **Files created:** this review (`reviews/adversarial-gate3-W6-W7-W8-review-2026-07-01.md`).
- **Reviewed documents edited:** none (proposals only, per precedent).
- **Currency check:** `git` — HEAD `a4fd774`; W6/W7/W8/06c committed and clean; reconciliation
  chain `dc56ca07 → cc27a86 (P-029, 06b) → a4fd774` verified; W4/W5 findings confirmed
  integrated (F-033/F-035, `r3_family_coverage_insufficient`).
- **Citation verification:** W6 §6/§7/§14/§19/§26, W7 §5/§9/§13, W8 §5/§11, `06b` §2/§3, and
  register P-029 read directly; results in §1.

**Verdict: `accept_with_required_changes`.** The three underlying specifications (W6 v0.3, W7,
W8) are sound and ready. Fix the manifest before freezing it: M-1 (two-stage ordering), M-2
(`gate_stage` enum), M-3 (identity coherence). The 06c manifest is doing exactly the right job
— it just needs to pass its own freeze criteria before it can certify the seam.
