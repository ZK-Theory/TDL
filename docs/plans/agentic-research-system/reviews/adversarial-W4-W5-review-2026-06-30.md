# Adversarial Review — W4 Routing and W5 Assurance Specifications (joint)

**Reviewer:** Independent adversarial review (Claude Opus 4.8), commissioned by Stephen
**Date:** 2026-06-30
**Subjects:** `design/04-agent-roles-and-model-routing.md` (W4 v0.1) and
`design/05-research-assurance-and-independent-review.md` (W5 v0.1), both introduced at
commit `f1e2986a`, reviewed jointly as the specifications themselves require.
**Baseline:** accepted W1 v0.3, W2 v0.3, **W3 v0.2** (`eb8ed821`, P-028), W6 catalogue +
addendum `06a` (F-025–F-030), D-001–D-008, P-001–P-028.
**Method:** `adversarial-design-review` skill; fresh-context attack against direct evidence.
**Verdict:** **`accept_with_required_changes`**

---

## 0. Executive summary

W4 and W5 are well-constructed and visibly absorbed the two prior rounds. They pre-propose
fixture IDs (F-031–F-038) rather than leaving the seam unassigned — the exact W3-M4 mistake,
now avoided; they encode the project's hardest-won lessons as first-class obligations
(degenerate-fallback guard W5 §13.3, null-operation invariance §13.4, anchoring/expected-
value-is-not-a-target §13.2, frozen-representation/vintage §14.4); and they are honest about
solo independence ("one human may occupy several roles … the system records contextual/model
separation honestly and does not claim independent humans", W5 §11.1). The central
architectural claim — W5 sets the bar, W4 proves a route clears it, neither can weaken or
absorb the other — holds at almost every point I attacked.

It accepts subject to required changes. **No Critical, no rework.** The strongest attack
that lands is upstream of everything both specs protect: the two-key edifice rests on the
`AssuranceRequirement`, and **nothing requires the actor who sets that requirement's risk
floor and lane scope to be independent of the producer** (W45-M1) — so an under-scoped or
under-classified requirement can defeat the whole apparatus before any verifier runs, and an
R3-consequence task mis-floored as R2 silently skips Stephen's gate. The other Majors are at
the routing seam: independence feasibility is not proven on the *producer* route before an
expensive run (W45-M2), the F-031–F-038 fixtures that enforce the entire design are not yet
specified to their own gate's standard (W45-M3), and cross-family R3 routability is asserted
without confirming the evaluated set can supply it (W45-M4).

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — |
| Major | 4 | W45-M1 … W45-M4 |
| Minor | 4 | W45-m5 … W45-m8 |

No reviewed document was edited (proposals only, per the W1/W2/W6 and W3 precedent). Change
log in §11.

---

## 1. Scope, authority, currency, and evidence verified

**Authority respected:** D-001–D-008 and P-001–P-028 are Stephen-approved; W4 §13–§14 and
W5 §11–§17 operationalise P-022/P-023/P-028 and I challenge none by preference. W4/W5 are
explicitly `review_pending` and invite this joint review (W4 §27, W5 §29). I created only the
review deliverable; touched no `.apm/`, contract, result, vault, T1.28, or no-migration
artefact, and used no active task as an experiment.

**Currency (clean):** HEAD is `f1e2986a`; both specs are committed and clean. The acceptance
chain is coherent — `1d6ade22` (my W3 review) → `eb8ed821` (accept W3 v0.2 + P-028 + 06a
addendum) → `f1e2986a` (W4/W5). W4/W5 consume the *accepted* W3 v0.2, not the v0.1 I
reviewed. No dated addendum needed.

**Direct-evidence citation checks (verified, not taken from summaries):**

| Claim | Verified against | Result |
|---|---|---|
| W4/W5 cite "W1 §§5,8,9,14,16,18" | `design/01` | **Accurate.** W1 §18 W4 constraint ("fail closed when no evaluated profile satisfies") and W5 constraint ("two-key research validity") match verbatim intent |
| W4 cites "W3 §§6–17"; W5 "W3 §§5–17"; "two token gates" | `design/03` v0.2; P-028 | **Accurate.** P-028 token rule = reference-token ceiling + bound-provider gate; W4 §17/§20 and W5 §5.3 consume it |
| W4 cites "F-001–F-005, F-007–F-020, F-022–F-023, F-025–F-030, S-016"; W5 cites "F-007–F-019, F-021–F-024, F-026, F-028–F-029" | W6 §6 + addendum `06a` | **Accurate.** F-026 = implementer frozen-rep/null/vintage retrieval; F-028 = budget overflow fails closed; F-029 = safe-distractor invariance — all as cited |
| "P-001–P-028", "accepted W3 v0.2" | register; `eb8ed821` | **Accurate.** P-028 exists exactly once; W3 v0.2 accepted |
| Q-005 = generic interface, Claude+Codex first release | register Q-005 | **Accurate.** W4 §16 records the boundary |

No miscitation found, in either spec. Evidence fidelity is again a strength.

---

## 2. Major findings

### W45-M1 — The `AssuranceRequirement` floor and lane scope can be set by the producer; two-key validity has no independent foundation *(Major; headline; Critical on the R3-escape path)*

**Claim.** W5 makes the `AssuranceRequirement` the root object of all validity: it carries
"requested and W5 epistemic risk floor with raising rationale", "assurance lanes and
domain-pack IDs", and per-lane `not_applicable` declarations (W5 §7). Its lifecycle is
`draft → review_pending → accepted` via "attributed authority" (§6.2). But **§6.2 and §11.1
never require that authority to be independent of the producing actor.** §11.1 carefully
separates six authorities (design ownership, contract implementation, producing, verification,
review, acceptance) — and the `AssuranceRequirement` author is *not among them*. So the actor
who will produce the work (or a Manager acting for it) may author the requirement that defines
how its own work will be judged.

**Why it crosses a boundary (the R3-escape path).** The epistemic floor determines the
human gate: R2 → Manager acceptance; R3/P-005 → Stephen (W5 §9, §17.4; W4 §15.2). If a
producer-aligned author classifies an R3-consequence task (a methodology change, a claim
promotion, a causal/novelty step — W4 §9.3 triggers) as R2, or marks the paper-claim or
representation lane `not_applicable`, the task routes to **Manager acceptance and never
reaches Stephen**. Every downstream protection the specs are proud of — distinct verifier,
two-key, cross-family — then operates on a *deliberately weakened bar*. W5 §21 catches a
*missing* pack (`assurance_requirement_incomplete`) but not a *wrongly-omitted lane* or an
*under-stated floor*; §9 says "ambiguity blocks or raises" but says nothing about a confident
mis-classification by a non-independent author. This is the same class of failure as F-014
(self-approved contract) but one level upstream — self-*definition* of the bar rather than
self-*approval* of the result — and it is currently unguarded.

**Failure scenario.** An implementer-aligned Manager authors an `AssuranceRequirement` for a
new harmonisation rule, marks the `paper claim` lane `not_applicable` ("internal method
only") and sets the floor at R2. The work proceeds with a distinct-context verifier and
Manager acceptance; the result later grounds a manuscript claim. Stephen's P-005 claim gate
was never triggered because the lane that would have required it was declared inapplicable by
the party that benefited.

**Disposition: amend (required before any R2/R3 dispatch is implemented).** Add the
`AssuranceRequirement` author/acceptor to the §11.1 separation-of-authorities and require, for
R2/R3, that the floor classification and every lane `not_applicable` rationale be set or
independently confirmed by an authority distinct from the producing actor — with the same
evidence-derived independence the specs already demand for verification. Add a W6 fixture
(extend F-035 two-key or add F-039): *an under-scoped / wrongly-`not_applicable` /
under-floored `AssuranceRequirement` authored by a producer-aligned actor is rejected, and an
R3-consequence task floored as R2 fails the human-gate check.* Add to W5 §21:
"`AssuranceRequirement` floor/lane scope set without required independence from the producer
→ block acceptance."

**Affected:** W5 §6.2, §7, §9, §11.1, §21; W4 §9.2/§15; P-022; W6 (new/extended fixture).

---

### W45-M2 — Independence feasibility is not gated on the producer route, risking wasted R2/R3 compute *(Major; W4 routing seam)*

**Claim.** Required independence (I1/I2/I3, W4 §14) is a property of the producer↔verifier
*relationship*, but W4 routes one `RouteRequest` at a time. §12 step 5 says W4 verifies "every
W5 lane, reviewer relationship, proof-obligation support, and human gate **can be satisfied**"
— but "can be satisfied" is not defined as "an eligible verifier route at the required grade
provably exists in the registered catalogue," and §14 computes a grade from
"actor/session/context/model/trace relationships" that do not yet exist when only the producer
is being routed.

**Why it matters (the wasted-run failure).** If verifier feasibility is deferred to
verifier-routing time, a long R2/R3 *producing* run can complete and only then hit
`independence_unavailable` (§17) — because, e.g., the only family that passes the required
capability gate is the producer's own family, leaving no eligible cross-/distinct-family
verifier. The producing evidence then cannot be accepted, and re-running with a different
family wastes the compute. This is precisely the costly-rework / long-run-guardrail class the
programme is built to prevent (cf. F-009 long-run, S-016 outage, the project's "no speculative
paths" rule).

**Failure scenario.** An R2 topology implementation is dispatched to the only profile that
passes `topology_reasoning`; a 10-hour run completes; verifier routing then finds no
distinct-context eligible verifier at the required grade for that capability →
`independence_unavailable` → the result is unacceptable and the run is wasted.

**Disposition: amend.** Make §12 step 5 explicit: for R2/R3, producer-route eligibility
**requires a demonstrated eligible independent-verifier route** (satisfying the W5-required
grade and capability) in the registered catalogue at the policy revision, evaluated as a hard
gate *before* producer dispatch; absence returns `independence_unavailable` with no producer
dispatch. Record the candidate verifier route's existence in the `RouteDecision`. Add this to
the F-033 oracle (independence cannot be manufactured) and the F-035 two-key fixture.

**Affected:** W4 §12, §14, §17, §20; W5 §16, §17.4; W6 F-033/F-035.

---

### W45-M3 — F-031–F-038 are unreserved and under-specified relative to their own acceptance gate *(Major; W4/W5↔W6 enforcement backbone)*

**Claim.** The entire W4/W5 design is enforced by the proposed fixtures F-031–F-038 (W4 §21,
W5 §22). The §26/§28 review gates require they have "complete priorities, provenance,
**oracles, graders**, and W6 reservation dispositions." But W4 §21's table supplies only a
one-line *design*, priority, and provenance per fixture — **no per-fixture pre/post oracle or
grader set**, unlike the accepted `06a` addendum (which gives every F-025–F-030 row a
pre-control setup, post-control oracle, and grader list). W5 §22 lists graders only in
aggregate. So the gates that certify W4/W5 cannot, as written, be ticked, and the fixtures
that are supposed to make the whole design machine-checkable are not yet specifiable as tests.

**Why it matters.** A design whose enforcement points are one-line sketches is asserting,
not demonstrating, that its guarantees are testable — the W3-M4 lesson, half-applied: the IDs
are pre-proposed (good) but not specified to reservation standard.

**Disposition: defer with dependency (required follow-through, mirrors 06a).** As part of this
review's reconciliation, produce a dated W6 addendum (e.g. `06b`) reserving F-031–F-038 with,
per fixture, a pre-control setup, post-control + trajectory oracle, grader classes, priority,
two-axis provenance, and dependency — to the `06a` standard. Fold W45-M1's requirement-capture
fixture and W45-M2's verifier-feasibility oracle into that addendum. Until reserved, the
affected W4/W5 metrics (W4 §21, W5 §22) and the §26/§28 gate items remain unmet.

**Proposed reservations (to be completed in the addendum):**

| ID | Owner | Design (W4 §21 / W5 §22) | Priority |
|---|---|---|---:|
| F-031 | W4 | Deterministic eligibility-first routing + candidate explanations | P0 |
| F-032 | W4 | Outage/fallback preserves risk/assurance/context/independence | P0 |
| F-033 | W4 | Role-switch/producer-correlation cannot manufacture independence (+ verifier feasibility, M-2) | P0 |
| F-034 | W4 | Permission/root/sensitivity + unsafe multi-agent fail closed | P0 |
| F-035 | W5 | Two-key non-compensable (+ requirement-capture, M-1) | P0 |
| F-036 | W5 | Proof-obligation anti-gaming: anchoring, degenerate fallback, no-op null | P0 |
| F-037 | W5 | Partial/negative/superseded distinct from claim promotion | P1 |
| F-038 | W5 | Domain-pack + qualitative `not_applicable` boundary | P1 |

**Affected:** W4 §21, §26; W5 §22, §28; W6 (new dated addendum); P-024/P-028 precedent.

---

### W45-M4 — Cross-family R3 routability is asserted, not confirmed against the evaluated set *(Major; W4 practicality/residual)*

**Claim.** R3 and every P-005 transition require grade I3 = cross-family review (W4 §14;
P-022). The first-release evaluated set is exactly two families, Claude and Codex (W4 §16.2).
Cross-family R3 review therefore requires that **two different families each pass the same
high-risk capability gate** for the work in question. Nothing in W4 confirms the evaluated set
can supply this for the project's actual R3 capabilities (e.g. `topology_reasoning` or
`mathematical_reasoning` at R3).

**Why it matters.** If only one family is eval-eligible for a core R3 capability, *all* R3
work in that capability is unroutable — correctly fails closed (§17 `independence_unavailable`),
but the condition is discovered only at dispatch, and for a solo TDA programme it could mean a
whole class of methodological/claim work cannot proceed under ARS at all. Worse, a routine
profile suspension (W4 §6.2 `eligible → suspended`) of either family silently drops the
project below the cross-family R3 floor with no early signal.

**Disposition: defer with dependency + add a coverage metric.** W4/W6 must track and surface a
**capability × family eligibility coverage** map, and treat "fewer than two eligible families
for a required R3 capability" as a visible blocking condition raised at evaluation/suspension
time, not at dispatch. Add to W4 §21 metrics: "R3-required capabilities with < 2 eligible
families: surfaced as blocking, not silent." Note in §16.2 that suspending one family's
eligibility may invalidate R3 routability and must raise the alert.

**Affected:** W4 §14, §16.2, §6.2, §21; P-022; W6 evaluation coverage.

---

## 3. Why the strongest attacks on the W4/W5 seam *fail* (demonstrated)

Per method, showing where the strongest attacks fail rather than inflating them:

- **"Can availability or cost lower risk/assurance/independence?"** (W4 Q1, W5 Q2) No.
  Eligibility is hard-gated *before* ranking (W4 §12, §13); cost/latency rank only
  already-eligible routes (§13: "cost never precedes adequacy, independence, privacy, or
  authority"); fallback re-evaluates under the *original* immutable request (§17). The residual
  is the *floor itself* (M-1), not the routing.
- **"Can W5 encode a preferred provider and turn validity into selection?"** (W4 Q3) No —
  §5.3 bars W5 from naming a provider/model; capability classes (§10.1) are provider-neutral.
- **"Can role-switching manufacture independence?"** (W4 Q2, W5 Q4) Not for *verification/
  acceptance* — grades are evidence-derived from session/context/family/trace and prior roles
  on the same subject (§14, §8). The gap is requirement *authoring* (M-1), which §11.1 doesn't
  cover.
- **"Can a structural pass satisfy both keys without scientific review?"** (W5 Q3) No —
  §17.3 makes Key B (R/M/H) non-compensable; §12 "a D/T pass cannot substitute for R/M/H."
- **"Can a negative/Partial result be lost?"** (W5 Q5) No — §18 makes them durable,
  immutable, consumer-restricted; §18.2 "does not become failure merely because the expected
  effect … is absent." Directly encodes the project's negative-result discipline.
- **"Can an accepted result auto-promote to a stronger claim?"** (W5 Q6) No — §19 separates
  acceptance from promotion; promotion requires Stephen under P-005 (§19.3).

The pattern: the routing/assurance *machinery* is sound; the unguarded point is the human-
authored *requirement* that seeds it (M-1) and the *sequencing* of independence proof (M-2).

---

## 4. Minor findings and editorial

- **W45-m5 — single-family-suspension fragility (W4 §16.2, §6.2).** Tied to M-4: a generic
  interface with exactly two evaluated families means either family's suspension can break
  cross-family R3. State that the two-family minimum is load-bearing for R3 independence and
  that dropping below it is a tracked blocking condition, not a silent capability loss.
- **W45-m6 — risk-vocabulary alignment (W4 §9.2, W5 §9).** W4's `effective_risk = max(task,
  W5_epistemic_floor, W8_operational_floor, human_raise)` and W5's "epistemic risk floor"
  should be stated as the *same* component under one name; confirm W5 owns only the epistemic
  term and W8 only the operational term, so "floor" is never ambiguous between them.
- **W45-m7 — TDA-pack template boundary (W5 §15.1, §24).** The TDA pack "references existing
  contracts/skills by version"; make explicit it is TDL-private, while the statistical (§15.2)
  and qualitative (§15.3) packs are the template-safe ones, so §24's "no TDL-private paths in
  public template packs" is mechanically checkable per pack.
- **W45-m8 — determinism input-set (W4 §13, §21).** "Deterministic decision equality for
  identical immutable inputs: 1.0" (§21) is unachievable while ranking uses time-varying
  cost/latency/reliability estimates (§13 ranks 4–6) unless those estimates are drawn from a
  **versioned evidence snapshot that is part of the immutable `RouteRequest` inputs**. §6.3
  expiry implies this; state it explicitly so determinism is well-defined.

No broken links or malformed markup found in either spec.

---

## 5. Answers to the specs' own joint review questions (W4 §25, W5 §27)

The user flagged these as key. Post-fix answers:

- **W4 Q1 / W5 Q2 (availability lowers a requirement?)** No via routing; **yes via the
  requirement floor itself unless M-1 is fixed.**
- **W4 Q2 / W5 Q4 (role-switch manufactures independence?)** No for verify/accept; **the
  requirement-author path is unguarded (M-1).**
- **W4 Q3 / W5 Q1 (W5 encodes provider preference?)** No (§5.3).
- **W4 Q4 (capable model, invalid grant?)** No — §12 step 4 + §19 default-deny; tool/root/
  sensitivity are hard gates.
- **W4 Q5 / W5 Q3 (aggregate hides a critical false accept?)** No — non-compensable gates
  (W4 §10.3, §21; W5 §17.3).
- **W4 Q6 (multi-agent ambiguous ownership?)** No — §18 refusal rules are concrete and
  checkable; **but verifier-route feasibility timing is M-2.**
- **W4 Q7 (schema overstates unevaluated providers?)** No — §16.1 "missing features are
  explicit absences, not emulated"; reinforce with m5.
- **W5 Q5/Q6 (negative lost / auto-promotion?)** No (§18, §19).
- **W5 Q7 (pack weakens core?)** No — §8.2 prohibitions are explicit.
- **W5 Q8 (quantitative imposed on qualitative?)** No — §15.3 + `not_applicable` with
  authority (§7); **the `not_applicable`-by-producer path is M-1 again.**

Every "yes/conditional" reduces to M-1 or M-2.

---

## 6. Decision audit

| Decision | W4/W5 interaction | Disposition |
|---|---|---|
| D-001–D-004, D-008 | Domain-general, local, inspectable; W4 capability classes + W5 packs are provider/domain-neutral | **Keep** |
| D-005 | Phase boundary; W4/W5 §3.3 bar T1.28 as experiment | **Keep** |
| D-006 | High-reasoning on risky work; W4 §10/§13 evaluate capability, never downgrade by cost | **Keep** |
| D-007 | Separate scientific authorities; W5 §11.1 separates six authorities — **but not the requirement author (M-1)** | **Keep; tighten via M-1** |
| P-001/P-020/P-021 | Canonical storage / single writer / non-shared paths — W4/W5 emit records via W2 commands, never mutate state (W4 §5.2, W5 §5.4) | **Keep** |
| P-005 | Human-reserved transitions; W4 §15.2, W5 §19.3 enforce — **M-1 is the bypass route (R3 mis-floored as R2)** | **Keep; M-1 closes the bypass** |
| P-011 | Multidimensional artefact authority; W5 §18.4 supersession is multidimensional | **Keep** |
| P-013 | Review binds subject hash; W5 §16.1, W4 §14 | **Keep** |
| P-022 | Graded independence (R0/R1 delegated, R2 verifier, R3 Stephen); W4 §14 I0–I3, §15.1, W5 §17.4 map exactly | **Keep** |
| P-023 | Independent scientific-property grading; W5 §13.3/§13.4, §12 (D/T can't certify property without recompute) | **Keep** |
| P-024 | Fixture provenance + reserved IDs; W4 §21/W5 §22 propose F-031–F-038 **unreserved (M-3)** | **Amend — reserve via dated addendum (M-3)** |
| P-025 | Proportional profiles; W4 §9.1 R0/R1, W5 §17.4 "only applicable keys"; honest qualitative `not_applicable` | **Keep** |
| P-026 | Successor sequence; W4/W5 advance the lane, authorize no implementation | **Keep** |
| P-027 | W1/W2/W6 acceptance; unchanged | **Keep** |
| P-028 | W3 v0.2 + token gates + F-025–F-030; W4 §17/§20 + W5 §5.3 consume the two token gates correctly | **Keep** |
| A-001/A-002 | T1.28 / Phase-2 pending; W4/W5 do not depend on them | **No action (out of scope)** |
| Q-004 | Independence diversity = P-022/P-023; W4 §14 supplies the grade machinery | **Keep** |
| Q-005 | Generic interface, Claude+Codex first release; W4 §16 records it — **M-4 flags the R3 two-family dependency** | **Keep; surface via M-4** |
| Q-006 | Human approval points; W4 §15.2 list matches P-005 | **Keep** |
| Q-001/Q-002/Q-003/Q-007 | Out of W4/W5 scope | **No action** |

W4 §1 ten choices and W5 §1 ten choices: all **Keep**, except W5 choice 6 (no sole
self-certification) must extend to requirement *authoring* (M-1), and the fixture-backed
choices depend on M-3 reservation.

---

## 7. Cross-spec consistency matrix

Invariant → enforcement point → fixture/test. Gaps flagged.

| Invariant | W4 enforcement | W5 enforcement | Fixture | Status |
|---|---|---|---|---|
| W5 sets bar; W4 cannot weaken; W4 selects; W5 cannot route | §1.1, §5.3 | §1.1, §5.1–5.2 | F-031, F-035 | **OK (routing); M-1 (requirement foundation)** |
| Eligibility-first; cost ranks only eligible | §12, §13 | — | F-031 | **OK** |
| Risk monotone; floor never lowered | §9.2 | §9 | F-035 | **OK except who sets the floor (M-1)** |
| Independence is evidence-derived, never attested | §14 | §16.2, §17.2 | F-022, F-033 | **OK for verify; M-1 (author), M-2 (feasibility timing)** |
| Two-key non-compensable | §10.3, §21 | §17.3 | F-035 | **OK** |
| Two W3 token gates fail before issue | §17, §20 | §5.3 | F-028 | **OK (inherits accepted W3 v0.2)** |
| Self-approval prohibited (result + contract) | §8 (Manager not own work) | §11.1 | F-014 | **OK for result/contract; M-1 for requirement** |
| Negative/Partial/superseded durable & restricted | — | §18 | F-037 | **OK (needs F-037 reservation, M-3)** |
| Result acceptance ≠ claim promotion | §15.2 | §19 | F-019, F-037 | **OK** |
| Provider-neutral; only Claude/Codex evaluated | §16 | — | F-020 | **OK; R3 two-family dependency (M-4)** |
| Routing/assurance metrics gated on fixtures | §21 | §22 | **F-031–F-038 unreserved/under-spec** | **GAP — M-3** |

---

## 8. Practicality and proportionality

- **R0/R1:** W4 delegated acceptance + W5 "only applicable keys" + honest `not_applicable`.
  Proportional. The one risk is record-authoring overhead, amortised by domain-pack templates
  (W5 §8.2) — acceptable.
- **R2:** `AssuranceRequirement` + distinct-verifier route + both keys + Manager acceptance.
  Heavy but matches the programme's values; M-2 must be fixed so the verifier cost isn't
  discovered after the producing run.
- **R3:** cross-family + Stephen. Appropriate, but M-4: confirm the evaluated set can actually
  supply cross-family review for the project's core capabilities, or R3 work is blocked.
- **Solo-researcher reality:** "Manager acceptance" for R2 is Stephen-as-Manager with a
  distinct-*context* verifier — honestly disclosed (W5 §11.1, W4 §14: "the same human
  operating two model sessions remains one human authority"). This is the accepted solo model,
  not a defect. The real human cost is authoring the `AssuranceRequirement`; M-1's independence
  requirement adds a second authoring/confirming pass for R2/R3 — proportionate to the risk it
  closes, and reusable via packs.
- **Non-TDA / qualitative:** W5 §15.2/§15.3 + Q-005 generic interface + `not_applicable`
  handle these; m7 keeps the template boundary clean.

No bureaucracy-driven bypass risk beyond the requirement-authoring cost, which packs amortise.

---

## 9. Proposed revision plan

**Immediate corrections (wording/structure; spec owners can apply):**
- m5 (single-family fragility), m6 (risk-vocabulary), m7 (TDA-pack boundary), m8 (determinism
  input-set).

**Stephen / Manager decisions (touch authority or the frozen interface):**
- **M-1** — add the `AssuranceRequirement` author/acceptor to W5 §11.1 separation and require
  producer-independent floor/lane scoping for R2/R3. (Authority change — needs sign-off.)
- **M-2** — require a demonstrated eligible verifier route on the producer route for R2/R3
  before dispatch (W4 §12). (Routing-interface change — affects W6/W7/W8 consumers.)
- **M-4** — adopt a capability×family eligibility coverage metric and a below-two-families
  blocking condition.

**Later-work dependencies (block the §26/§28 gates and the W4/W5 metrics, not the conceptual
direction):**
- **M-3** — produce a dated W6 addendum (`06b`) reserving and fully specifying F-031–F-038
  (oracles + graders + provenance to the `06a` standard), incorporating the M-1 requirement-
  capture fixture and the M-2 verifier-feasibility oracle.

---

## 10. Residual risks after proposed changes

1. **Requirement integrity (M-1)** is the load-bearing fix; even with independent floor/lane
   scoping, mis-classification risk is reduced, not eliminated — the W4 §9.3 risk-raising
   trigger list must stay current with the methods the programme actually uses.
2. **Verifier-pool depth (M-2/M-4)** depends on W6 evaluating ≥2 families per core R3
   capability; until then, R3 routability is a real constraint, correctly fail-closed.
3. **Fixture realisation (M-3)** is deferred executable work; the design is only as checkable
   as the eventual F-031–F-038 oracles, which must be calibrated (pre-control fails,
   post-control passes, degenerate mutations fail) like every other W6 fixture.
4. Everything the routing/assurance machinery covers (eligibility-first, two-key, fallback
   equivalence, negative durability, promotion separation) is closed by the existing design.

---

## 11. Change log and verification evidence

- **Files created:** this review (`reviews/adversarial-W4-W5-review-2026-06-30.md`).
- **Reviewed documents edited:** none (proposals only, per precedent).
- **Currency check:** `git` — HEAD `f1e2986a`; W4/W5 committed and clean; acceptance chain
  `1d6ade22 → eb8ed821 (P-028, 06a) → f1e2986a` verified.
- **Citation verification:** W1 §§5/8/9/14/16/18, W3 v0.2 §§5–17, P-028, and W6 addendum
  `06a` (F-025–F-030, esp. F-026/F-028/F-029) read directly; results in §1.

**Verdict: `accept_with_required_changes`.** Close M-1 (requirement-author independence) and
M-2 (verifier-route feasibility before producer dispatch) before R2/R3 routing is implemented;
reserve and fully specify F-031–F-038 via a dated W6 addendum (M-3); adopt the capability×family
coverage condition (M-4). The two specifications are otherwise sound, non-circular, and ready
to govern W6–W8 across the shared interface once these changes land.
