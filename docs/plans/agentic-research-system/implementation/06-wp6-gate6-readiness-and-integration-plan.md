# 06 — WP6: Gate 6 Readiness and End-to-End Integration — Scope and Sequencing Plan

**Date:** 2026-07-16
**Status:** draft, review pending — drafted at Stephen's direction (2026-07-16 session);
authorizes no implementation.
**Revision note (2026-07-17):** revised through the R3 remediation review to close the
strict P1 schema/oracle, versioned schema identity, universal authority, atomic claim,
correction-selector, and summary-cardinality findings while preserving Stephen's P-035
sequencing/composition decision and the R2 closures.
The suite remains non-dispatchable until a fresh independent review finds no open
Critical/Major item and Stephen approves the exact reviewed revision.
**Currency update (2026-07-17):** the Gate 5 foundation was accepted at merge
`f49a27f` (Computational-Log `[DECISION]` entry, 2026-07-17), with D-G5-1(a) M/H
restriction, D-G5-2/O15 deferral, and G5.3-B(a) attribution carried forward and the
candidate remaining `blocked`/`gate5_authorized=false`. Gate A blocker A1 is therefore
cleared and Gate 6 planning is eligible; every "Gate 5 close" dispatch gate in this
suite is satisfied by that event. Stephen confirmed the P-031–P-034 wording the same
day (D-G6-1 closed). Dispatch of any WP6 work still requires this suite's own review
gate and Stephen's approval of the dispatching plan revision.
**Goal:** Define the exact work standing between Gate 5 foundation acceptance and (a) a
Gate 6 preflight-eligible pilot, (b) a dispatchable first research programme (the
vault-side "Evidence-Led TDA Scale and Research Programme for ARS" v1.0.0), and (c) the
end-to-end integration objective recorded in P-034 — so each work package can be
dispatched as its own reviewed plan (04a/05a pattern) without re-derivation.

**Governing authority:** accepted W1–W8 designs and 06c interface manifest (P-027–P-030);
04-plan §4 (Gate 6) and §6 (pilot operating model); 05-wp5 plan §2 (Gate 5 acceptance
criteria) and §6 owner record; accepted decisions P-031–P-035
(03-decisions-and-open-questions.md, recorded/confirmed 2026-07-16–2026-07-17);
Gate A blockers A1–A8 of the TDA-scale programme v1.0.0 (vault:
`00-Meta/Research Direction Reports/Evidence-Led TDA Scale and Research Programme for
ARS - v1.0.0 - 2026-07-16.md`).

---

## 1. Position and problem statement

Gate 5 closed at accepted merge `f49a27f`. The accepted foundation is a control plane
with eval/release gating, authority grants, context compiler, routing engine, assurance
requirements, and operations modules — exercised by deterministic fixtures over fake
transports, with the M/H capability restriction explicit (D-G5-1 option (a)).

The first intended research input, the TDA-scale programme v1.0.0, fails closed on
eight blockers it verified itself (Gate A). Mapping them to this plan:

| Gate A | Blocker | Cleared by |
|---|---|---|
| A1 | Gate 5 unaccepted | **Cleared** at accepted Gate 5 merge `f49a27f` (WP5.6, outside this plan) |
| A2 | Gate 6 preflight ineligible | WP6.4 (after A1 and WP6.1–6.3) |
| A3 | Adapters `live_enabled: false`; fake transport only | WP6.2 |
| A4 | Task schema is identity/revision/status/hash only; no rich Task or ScopeDefinition runtime | WP6.1 |
| A5 | No complete operator lifecycle (issue/start/checkpoint/heartbeat/stop/resume/review/accept) | WP6.1 |
| A6 | No instantiated evaluated model profiles or persisted route decisions | WP6.2 |
| A7 | Only the generic assurance pack; no TDA/panel pack | WP6.3 |
| A8 | `foundation.yaml` null project/control-root binding | WP6.4 |

Two further gaps are not in Gate A but block the P-032/P-034 integration objective:
the portfolio/Discovery layer has no specification (master plan §6.1 is prose; the W1
portfolio catalogue has no schema, commands, or events; W4's role catalogue has no
Scout or Portfolio Steward profile), and there is no admission interface that turns a
promoted, hashed research package into canonical ScopeDefinitions — the v1.0.0 package
manifest is that interface performed by hand. WP6.5/WP6.6 close these.

## 2. Owner directions this plan implements

P-031–P-034 were recorded 2026-07-16 and confirmed by Stephen 2026-07-17
(D-G6-1 closed). P-035 records Stephen's direct 2026-07-17 approval of the remediation
review's sequencing and evidence-composition choices:

- **P-031** — Gate 6 pilot slot amended to the first ARS-native workflow; SCALE-01
  proposed as pilot; the first ARS paper (SPEC lane) inherits the paper-pilot criteria.
- **P-032** — full portfolio/Discovery integration via a new W11 specification;
  ARS becomes canonical for the Candidate → Assay → Spike → promotion lifecycle;
  vault becomes a projection surface for successor-owned objects only through the
  path-disjoint ARS namespace; the living legacy backlog stays legacy-owned until
  whole-path cutover.
- **P-033** — full live adapters and evaluated profiles before any R2 research
  dispatch; no interim operator-executed mode.
- **P-034** — end-to-end consolidation objective; legacy surfaces retire by explicit
  per-item ownership transitions after their W9 gates; P-026 legacy boundary unchanged.
- **P-035** — WP6.2 uses the non-circular
  `T1a → T2 → T3/T4 → T1b → T5–T8` lifecycle, and T7 uses the exact composite
  evidence model `251 immutable frozen references + 51 new live results = 302`.
  The R2 corrections refine evidence enforcement and remain pending exact-revision
  review/approval: T1b is the non-compensable `T1b-M ∪ T1b-H` union; 06e/06f supply
  independent expected sets; and W6 `gate_stage: pilot_promotion` is separate from
  `evidence_stage: live_capability`.

## 3. Work packages

### WP6.1 — Runtime Task lifecycle and operator surface (A4, A5)

Materialize the accepted W2 runtime (rich Task and ScopeDefinition records, dispatch/
claim/lease/attempt, messages, blockers/Partial, artefact manifests, reviews/decisions/
corrections) and the W8 typed operator command surface with receipts, replay reducers,
and durable human-readable projections. Detailed plan:
`06a-wp6-1-runtime-task-lifecycle-plan.md`.

### WP6.2 — Live capability: adapters, parity, threshold policy, evaluated profiles (A3, A6)

The D-G5-1(b) work deferred out of Gate 5, now scoped: a separately accepted
pre-registered calibration protocol (T1a); protected bounded Claude/Codex canaries;
a separately accepted composite model/human evidence-bearing threshold/calibration
policy (`T1b-M ∪ T1b-H`); semantic
fail-closed parity evidence on live transports;
instantiated W4 §10 evaluated model profiles with persisted route decisions; the
pre-registered M/H row unblock. Detailed plan: `06b-wp6-2-live-capability-plan.md`.

### WP6.3 — TDA/panel assurance pack (A7)

Author the `TDL_private` pack against the accepted W5 §15.1 specification: topology,
stochastic/null, statistical/panel, representation, output/provenance, and paper-claim
lanes; persistence construction, W2 (Wasserstein) convention, filtration/landmark
choices, Markov/null design, tested-object invariance, frozen representation, output
schema/provenance, benchmark validation, and topology-to-claim limits — referencing
existing TDL contracts and skills by version, not by copy. Per P-029, the pack's
epistemic floors, lane scopes, and every `not_applicable` rationale require an
authority distinct from the prospective producer. Small enough to run as one dispatch
with the standard adversarial review; no child plan needed unless review says otherwise.

### WP6.4 — Project binding and Gate 6 preflight package (A8, P-031)

- Bind `foundation.yaml` to the approved external control store and verified project
  identity (P-020 storage boundary); prove the binding with the existing restore/
  recovery checks.
- Prepare the Gate 6 preflight package for SCALE-01 as pilot under amended P-031:
  non-critical status, read-only content-addressed inputs (the programme's fixture
  manifest), rollback evidence, and the pilot promotion criteria mapped to the SPEC
  lane for the first ARS paper.
- Exit is Gate 6 preflight eligibility, not dispatch: SCALE-01 dispatches only after
  Gate A clears end-to-end and the programme's briefs are re-hashed against the real
  ScopeDefinition schema (its own v1.0.0 rule).

### WP6.5 — W11 portfolio and Discovery lifecycle specification (P-032)

Specification lane, not implementation. Write `design/11-portfolio-and-discovery-
lifecycle.md` covering:

- portfolio object records (programme, paper, hypothesis/candidate, method, dataset,
  claim) and their dependency edges — the W1 §5.1 catalogue given schemas;
- typed Discovery lifecycle: `CandidateRegistered`, `AssayScored` (axis scorecard as a
  typed artefact), `SpikeVerdict` (PASS/FAIL/PARTIAL with kill conditions),
  `PromotionDecision` (PROMOTE/PARK/KILL as authority-bearing Decision records —
  promotion remains human-locked per P-005/P-022);
- the admission interface: a command in the `AdmitResearchDossier` shape that validates
  component content hashes against a package manifest, creates portfolio objects, and
  instantiates ScopeDefinitions — formalizing what the v1.0.0 package manifest did by
  hand;
- Scout ingestion boundary (external literature surveillance producing Candidate
  records) and the W4 role-profile additions (Scout, Portfolio Steward) it requires;
- path-level projection contract: the living legacy
  `00-Meta/Discovery/_backlog.md` remains exclusively legacy-written until an explicit
  whole-path cutover after every item on that path transitions. Successor-owned
  generated views use the registered ARS-only namespace
  `00-Meta/ARS/Discovery/`; no legacy tool or human workflow writes it. Human
  annotations enter through the separate registered
  `00-Meta/ARS/Discovery-annotations/` inbox and become authority only through a typed
  ingestion command. An optional combined read-only view uses a third path and is
  never an input to either authority;
- a path/writer registry, per-item ownership-transition events, annotation-ingestion
  events, collision detection, deletion/rebuild tests, and a one-way whole-path
  cutover test before any legacy-named path can become generated (P-004/P-021).

Entry criteria per `design/README.md` apply; the spec passes its own adversarial
review and reconciliation before any WP6.6 implementation. This lane can start
immediately — P-026 authorizes specification work in parallel with everything else.

### WP6.6 — Dossier admission and first programme intake (post-W11)

Implement the W11 admission interface and Discovery lifecycle runtime; admit the
TDA-scale programme (re-versioned v1.0.x with re-computed hashes) as the first
canonical dossier; project it back to the vault. Requires WP6.5 accepted and WP6.1
merged. Its dispatch plan is written after W11 review — task decomposition before the
spec is accepted would be speculative.

### WP6.7 — Legacy consolidation sequencing (P-034; gated)

Sequencing document only, until its gates open: the W9 specification, T1.28 terminal
disposition and W0 addendum, per-item ownership transitions for active Discovery/APM
items, and the retirement checklist for APM orchestration surfaces. Nothing in WP6.7
dispatches while T1.28 or either current paper remains active; P-026's boundary holds.

## 4. Dependency DAG and dispatch sequencing

```text
Gate 5 close (WP5.6, outside this plan)
   ├─> WP6.1 runtime lifecycle ──────────┬─> WP6.4 binding + Gate 6 preflight
   ├─> WP6.2 live capability ────────────┤        │
   ├─> WP6.3 TDA/panel pack ─────────────┘        └─> Gate 6 preflight → Gate A clears
   │                                                   → SCALE-01 pilot dispatch
WP6.5 W11 spec (may start now, spec lane) ─review─> WP6.6 dossier admission
                                                        (also needs WP6.1)
WP6.7 legacy consolidation (gated on W9 + T1.28 closeout; sequencing doc only)
```

- WP6.5 starts immediately (specification lane; no Gate 5 dependency).
- WP6.1 and WP6.2 are the long poles and are parallelizable after Gate 5 close
  (worktrees, concurrency cap 3–4). Within WP6.2 the only graph is
  `T1a → T2 → T3/T4 → T1b → T5 → T6 → T7 → T8`: Stephen's accepted T1a protocol
  hash gates T2–T4, T3/T4 may run in parallel after T2, and Stephen's accepted T1b
  composite T1b-M/T1b-H evidence-policy hash gates T5–T8 and every M/H eligibility
  transition. No child
  prompt may reproduce either superseded unified-T1 graph.
- WP6.3 is small and independent; slot it into spare capacity.
- WP6.4 last before Gate 6 preflight; it consumes WP6.1–6.3 outputs.
- SPEC-01 (the programme's first greenfield Assay, R3) is dispatchable only after
  WP6.2 makes its cross-family review requirements satisfiable — do not schedule it
  earlier.

## 5. Owner-decision points

| ID | Decision | Anchor |
|---|---|---|
| D-G6-1 | **Closed 2026-07-17** — exact wording of P-031–P-034 confirmed by Stephen | 03-decisions §"Post-Gate-5 owner directions" |
| D-G6-2 | **Structure closed 2026-07-17 under P-035.** Two exact-hash owner gates remain at execution time: accept T1a's independently reviewed preregistered protocol before T2–T4; after protected T3/T4 calibration and the separate human-rubric/blinded-case run, accept T1b's independently reviewed composite `T1b-M ∪ T1b-H` policy before T5–T8 or any M/H eligibility transition. T1a makes no observed-calibration claim and neither T1b branch compensates for the other. | 05-plan §7.2; W6 §§13/27; D-G5-1; P-035; 06b §§2–3 |
| D-G6-3 | Approve the literal WP6.1/WP6.2 invariant tables and pre-execution expected manifests. Every changed and unchanged field has exact old/new values, reason/formula, recomputation command, and smoke assertion. Approval cites the exact dispatching revision plus the independently reviewed WP6.1 catalogue/schema-identity manifests and WP6.2 54-row descriptor-hash manifest by repository path, schema ID/version, Git blob, and SHA-256 before runtime implementation or observation. | 05-wp5 plan §7; 06a §§3–4; 06b §§5–6; 06d §§1/5; 06f §3 |
| D-G6-4 | Accept W11 after adversarial review and approve the first ownership-transition batch. No migration begins until W11 proves path/writer exclusivity and the batch disposition is recorded. | WP6.5/WP6.6; P-004/P-021/P-032 |
| D-G6-5 | Gate 6 preflight acceptance for SCALE-01 as pilot | WP6.4; P-031 |

## 6. Research assurance requirements

- **Lanes:** Output/Provenance primary throughout WP6.1/WP6.2/WP6.4/WP6.6;
  Topology/Stochastic/Statistical enter only through WP6.3 pack content and are
  human-review-only there (pack adequacy is not machine-checkable).
- **Machine-checkable claims → enforcement artifacts (per WP dispatch plan):**
  - "rich Task/ScopeDefinition and operator lifecycle are complete" → exact-set
    complete-record multiset equality against the accepted, content-addressed W2/W8
    literal catalogue, exact versioned command/event schema identities, semantic
    command/event/discriminator/reducer/projection/authority-subject/receipt bindings,
    atomic Task-plus-Dispatch claim write set, closed correction selector, and
    one-field/illegal-transition/
    conflicting-payload atomic negatives (WP6.1 §§2–3);
  - "live issue is secret-safe and cost-bounded" → sentinel injection at every
    context/adapter/payload/argv/canonical producer seam plus atomic missing/zero/
    exhausted/concurrent grant negatives, all before provider invocation (WP6.2 §4);
  - "live parity fail-closed" → each critical control is bound to the actual rendered
    payload, provider command/receipt, grant/lease, and observed enforcement; an
    adapter/transport-seam perturbation blocks with no issue (WP6.2 T5);
  - "profiles are evidence, not names" → strict W4 §10.2/§10.3 exact closure and
    one-field missing/stale/duplicate/incompatible/omitted/self-attested/unapproved
    negatives (WP6.2 T6);
  - "P1 pilot blockers are active" → the canonical six-tuple 11 baseline rows and separate
    43-referent calibration/activation closure are consumed as one 54-referent atomic
    union from the independently accepted content-addressed 54-row descriptor-hash
    manifest under the strict P1 stage schema by pilot-evidence acceptance and claim
    promotion; presence-only packages, baseline-only success, a stale 06f/manifest
    identity, or observed-side generation of expectations cannot pass (WP6.2 T8);
  - "admission validates content addresses" → exact manifest-required-set closure;
    missing, duplicate, extra, stale-revision, incompatible, or tampered components
    block admission atomically with zero object/ScopeDefinition publication (WP6.6);
  - "vault is projection-only for successor objects" → path/writer registry proves
    successor projection and legacy authority paths are disjoint; projection mutation,
    legacy collision, deletion/rebuild, and one-way cutover tests pass (WP6.5/WP6.6).
- Passing software tests remains insufficient; each WP dispatch plan carries its own
  research-assurance triage per APM_RULES.

## 7. Forward-obligation register

The master retains every non-local obligation; child plans may refine but not silently
retire these rows.

| Source | Exact obligation and owner | Trigger | Disposition |
|---|---|---|---|
| W1 §9.6; W7 §§9/21 | No credential/`.env` content crosses context, generated adapter, payload, argv/config, event, receipt, object, or fixture; WP6.2 implementer, independently reviewed | Before any provider invocation | WP6.2 T2/T3/T4 and §4 pre-issue matrix; post-run scan is defense in depth only. |
| W2 §§10–21; W8 §§7–21 | Exact accepted lifecycle/catalogue, not an implemented subset; WP6.1 implementer and reviewer | Before WP6.1 runtime implementation/merge | 06a §3 plus content-addressed 06d literal 104-row complete-binding catalogue and independently accepted schema-identity manifest; complete versioned identity propagation; exact authority subjects on all rows; atomic Task-plus-Dispatch claim; closed correction selector; row-cardinality/effect checks; one-field and race mutations. |
| W4 §§10.2–10.3 | Complete current evaluation evidence and eligibility; T6 producer, distinct reviewer, Stephen approval | Before any route relies on a profile | 06b T6 and master exit checklist. |
| W6 addendum F-037/F-038 | Independently freeze, then materialize, calibrate, activate, and consume the exact 54-referent union as P1 blockers; expected-manifest producer, distinct reviewer, runtime producer | Expected manifest before descriptor build/observation; evidence before pilot acceptance or claim promotion | Strict P1 stage schema plus content-addressed 54-row descriptor-hash expected manifest under 06f §3 and 06b §§5–6; baseline rows and activation evidence are separate non-compensable sets; producing-seam omissions and coordinated descriptor/manifest replacement reject. |
| P-018/P-030/P-035 | T7 closure is exactly 251 immutable `foundation_release` references plus 51 new `live_capability` results with a bijective predecessor map; WP6.2 implementer and reviewer | Before any M/H capability becomes eligible | Content-addressed literal 06e map; 06b §6.2 schema with valid W6 `gate_stage`, separate `evidence_stage`, stage-aware loader/CLI, provenance negatives, and invariant smoke. |
| D-G5-3/D-G6-3 | Literal old/new/reason/formula/command/smoke, including unchanged fields; Stephen | Before WP6.1 or WP6.2 execution | 06a §4 and 06b §6; approval cites exact revision. |
| P-004/P-021/P-032 | Legacy and successor writers never share a mutable path; W11 author and migration authority | Before W11 acceptance or any transition | WP6.5 registered paths, writer sets, ingestion, collision and one-way cutover tests. |
| S-016 | Provider outage preserves requirements: wait/block/`unable_to_grade`, never a lower-grade substitute; WP6.2 | Any T7/T8 provider outage | 06b stop condition and fixture evidence. |
| Adversarial review §11 | Fresh independent re-review with no open Critical/Major, then exact-revision owner approval | Before WP6.1/WP6.2 approval | Final two rows of §9 checklist. |

## 8. Out of scope for WP6

- Any research-paper computation, empirical claim, or UKHLS Wave 15 usage (programme-
  side gates; the programme's own §5 data boundary governs).
- Migration or reinterpretation of T1.28 or the two current papers (P-026).
- Cloud execution, WSL memory changes, or GPU adoption (programme boundaries; W8
  benchmark rule stands).
- P1 fixture promotion beyond the rows named in the WP6.1/WP6.2 child plans.
- Autonomous promotion of any Discovery candidate — PROMOTE/PARK/KILL stay
  human-locked (P-005).

## 9. Exit checklist

Owner-touchpoint preconditions from the child plans are hoisted here explicitly —
this checklist is the acceptance procedure, and a precondition that lives only in
sub-plan prose is not enforced by it.

- [x] P-031–P-034 confirmed by Stephen (2026-07-17) — D-G6-1 closed.
- [ ] Exact content-addressed T1a calibration protocol independently reviewed and
      accepted by Stephen (D-G6-2/P-035) **before** T2–T4; it records no observed
      calibration claim.
- [ ] Exact content-addressed composite T1b-M/T1b-H evidence-bearing policy independently
      reviewed and accepted by Stephen after protected T3/T4 model calibration and the
      separate blinded human rubric/disagreement/adjudication evidence run
      (D-G6-2/P-035) **before** T5–T8 or any M/H row unblocks.
- [ ] Every WP6.1/WP6.2 changed and unchanged invariant has literal old/new values,
      reason/formula, recomputation command, and smoke in the exact dispatching plan
      revision; Stephen approves that revision before execution (D-G6-3; 06a §4,
      06b §6).
- [ ] Before WP6.1 runtime implementation, Stephen accepts the independently reviewed
      104-row catalogue and per-row command/event schema-identity manifests by exact
      path, schema ID/version, Git blob, and SHA-256. They bind every authority subject,
      the atomic two-stream claim, and the closed correction selector (06a §3; 06d).
- [ ] Before any P1 descriptor build or observation, Stephen accepts the independently
      produced/reviewed 54-row expected manifest containing every literal descriptor
      hash; the strict P1 schema and coordinated-pair mutation pass (06b §5; 06f §3).
- [ ] Evaluated model profiles accepted by Stephen at their claimed capability
      grades (06b T6 human-review item) before any route relies on them.
- [ ] Stephen records the WP6.1 operator-usability disposition after tranche review;
      a technically complete but routinely bypassable surface does not clear A5.
- [ ] WP6.1 and WP6.2 merged via review-then-merge; Gate A A3–A6 cleared with
      direct current evidence, including the content-addressed literal W2/W8 complete-
      binding catalogue with exact versioned command/event identities and authority,
      provider-specific
      pre-issue secret/cost negatives, execution-bound live parity, complete W4
      profiles, the exact 251+51 composite closure from 06e, and the active 54-referent
      F-037/F-038 pilot/claim gates from 06f.
- [ ] WP6.3 pack accepted with distinct-authority review; A7 cleared.
- [ ] WP6.4 binding verified and Gate 6 preflight package accepted; A8 cleared;
      D-G6-5 recorded.
- [ ] WP6.5 W11 specification accepted after adversarial review with the legacy
      `_backlog.md`, ARS generated namespace, annotation inbox, writer sets, and
      one-way cutover physically disjoint; D-G6-4 records the first transition batch
      before any migration.
- [ ] TDA-scale programme re-hashed (v1.0.x) against the real ScopeDefinition schema
      and admitted via WP6.6 — Gate A clears end-to-end; SCALE-01 becomes
      dispatchable as the Gate 6 pilot.
- [ ] WP6.7 sequencing document exists with its gates explicit (no dispatch).
- [ ] This revised WP6 suite receives a fresh independent adversarial review with no
      open Critical/Major finding and every failed/partial binding row closed.
- [ ] Stephen explicitly approves the exact commit reviewed in the preceding row;
      only that commit may supply WP6.1/WP6.2 dispatch prompts.
