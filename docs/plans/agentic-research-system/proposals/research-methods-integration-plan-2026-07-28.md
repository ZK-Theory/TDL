# Research-Methods Integration Plan — Gemini paper × ARS

**Created:** 2026-07-28
**Status:** ANALYSIS RECORD — D-1/D-2/D-3 accepted by Stephen 2026-07-28; superseded for
execution by the RM plan suite (`../implementation/rm-00-research-methods-lane-master-plan.md`
and RM-01..RM-04, with decision-entry drafts in `rm-decision-entry-drafts-2026-07-28.md`).
Retained unchanged below as the adversarial-review and analysis provenance.
Originally: PROPOSED — planning input only. Per folder change discipline, nothing here is
assumed by a specification until a decision entry exists in
`../03-decisions-and-open-questions.md`, and no implementation begins without its own
reviewed plan. This document confers no runtime, provider, or claim authority.
**Inputs reviewed:**
1. `Gemini For Research.md` — Woodruff et al., *Accelerating Scientific Research with
   Gemini* (the paper itself, 148 pp.)
2. `ars-plus-deep-research-report.md` — external deep-research report, **no** repo access
3. `ars-plus-deep-research-report-2.md` — external deep-research report, partial
   planning-doc access
**Repo ground truth verified at:** working tree on 2026-07-28 (`origin/main` = `449b0d00`,
PR #173 merge; handoffs 20–26 present untracked)

---

## 1. Adversarial review of the two reports

### Report 1 (no repo access) — mostly superseded, two findings survive

The report reconstructs ARS by inference from the public repo skeleton and proposes
building a typed orchestration layer (`state.py`, `execution.py`, `review.py`,
`retrieval.py`, claim graphs, review dockets). **Verdict: the proposed architecture
already exists in stronger form.** W2 defines typed immutable records and deterministic
replay; W5 defines review lifecycles, proof obligations, counterexamples-as-falsification-
inputs, two-key validity, and claim promotion; W3 defines bounded context packets. Its
roadmap also ignores the governance regime entirely — it assumes ARS calls models
directly, which P-042 prohibits for first release. Its Gantt chart and module list should
not be executed.

Two findings survive contact with the repo:

- **F1-A (valid, confirmed today):** `research_system` is packaged and CLI-exposed but
  absent from pytest coverage (`pyproject.toml:103`) and from ruff `known-first-party`
  (`pyproject.toml:96`). The operationally most central package has the weakest automated
  accounting. Cheap to fix, worth fixing.
- **F1-B (valid as framing):** "the bottleneck is verification, not generation" — correct,
  and ARS is already built around it; the report independently re-derives ARS's own thesis,
  which is useful confirmation, not new work.

Its two "radical" directions — TDA on proof-state trajectories, sheaf-theoretic claim
consistency — are speculative foundations under APM_RULES. **Route to the Discovery
Harness** (`/assay` scorecard, then `/spike` only on PROMOTE), not to any roadmap.

### Report 2 (partial doc access) — architecturally sound, three corrections

The two-track recommendation (**import the methodology now via operator-mediated
briefs; gate the transport**) is correct and consistent with P-042. Its mapping of paper
primitives to W3/W5/W6 rather than W7 is the right reading. Corrections from direct
repo access:

- **F2-A: it should not be a "Gemini" pack.** The operator's sessions are Claude and
  Codex (P-029/P-042); the paper's value is provider-independent method patterns. Naming
  the deliverable `GeminiReviewProtocol` etc. bakes a provider into a provider-neutral
  core — exactly what W1/W7 forbid. Everything in Track 1 below is provider-neutral; the
  paper is *evidence*, not a vendor requirement. (Its Gemini API/privacy analysis is good
  reference material for the deferred Track 3 adapter and should be kept.)
- **F2-B: it is unaware of current-state blockers.** `tests/research_system` is red on
  `main` (handoff 26: SchemaRegistry N+1; date-time format fallback bug; 86 generated
  WP6.1 event schemas requiring `command_schema_*` fields no producer emits). The full
  suite has never been observed to complete. No method-import work should land on a red,
  unaffordable suite.
- **F2-C: stale status.** The WP6.3 assurance-pack contract and schema were owner-accepted
  exact-byte at `449b0d00` on 2026-07-28 (handoff 25) — after the report's evidence
  snapshot. The active dependency path is WP6.1 + WP6.3 → WP6.4 → Gate 6 (P-042).

### The paper — what it actually adds that ARS lacks

ARS already institutionalizes most of the paper's playbook at the *assurance* layer
(adversarial review culture, counterexample/falsification inputs, two-key validity, a
Lean evidence-class addendum `design/05a`). What ARS does **not** yet have is the
*procedural* layer and the *operational loop*:

| Paper primitive | ARS status | Gap |
|---|---|---|
| Adversarial self-correction review protocol (review → self-critique for hallucinated findings → iterate) | Review lifecycle exists (W5); protocol content ad hoc per handoff prompt | Reusable protocol pack |
| Counterexample search, neutral "prove or refute" framing (anti-confirmation-bias) | W5 names counterexamples as falsification inputs | Brief templates that *operationalize* the framing |
| Context de-identification (strip "this is open/conjecture" framing) | Nowhere | Brief-compilation transform with provenance retention |
| Cross-domain theorem retrieval with external verification of statements | Nowhere (vault/Zotero exist but unwired) | Retrieval step in brief templates + typed citation binding on import |
| Neuro-symbolic execution loop (model proposes, code verifies, traceback feeds back) | W8 leases/ops exist; no verification-execution lane | Track 2 |
| Structured reviewer output | W2 typed records exist | Import schemas + fail-closed importer |
| Autoformalization | Lean lane exists (`lean-proof`, Leanstral, 05a) | Extend later, don't build new |

**And the operational loop:** P-042 says "ARS prepares and records bounded briefs …
an authorized operator starts the external model session." Verified today: **no brief
exporter or result importer exists anywhere in `research_system/`**. The operator-mediated
workflow is specified but untooled. That is the single highest-leverage build.

---

## 2. The plan

Four tracks, strictly ordered. Track 0 is prerequisite engineering; Track 1 is the core
deliverable; Track 2 extends it; Track 3 is design-only. Every implementation item below
follows the standing pipeline: decision entry → bounded plan → adversarial review →
implementation on a `pipe/` branch → review-then-merge.

### Track 0 — Unblock (prerequisite; no new decision needed except D-1)

| # | Item | Notes |
|---|---|---|
| 0.1 | Land the in-flight handoff-26 fixes: SchemaRegistry N+1 (cache keyed on schema root) and the date-time format fallback (`schema_registry.py:31` — return `True` for non-strings) | Already briefed; an agent is assigned. Verify against handoff 26's measured baselines. |
| 0.2 | **D-1 (owner decision):** WP6.1 currency gap — 86 generated event schemas require `command_schema_id/version/sha256`; no producer emits them. Either the command/ledger producer populates them, or the generated schemas relax. | Governance call, not mechanical. Populating the producer is the direction consistent with WP6.1's binding intent (the fields exist to bind events to command schema identities); relaxing weakens an accepted materialization. Recommend **producer emits**, as its own bounded task. |
| 0.3 | After 0.1, run the full `tests/research_system` suite once to completion and record the complete failure inventory (unknown past test 74; nobody has seen the suite finish). | The affordability recovered by 0.1 makes this possible for the first time. |
| 0.4 | Add `--cov=research_system` to pytest addopts and `research_system` to ruff `known-first-party` (report 1 F1-A). | One-line each in `pyproject.toml`. |
| 0.5 | Add a bounded smoke slice of the runtime append path (CommandService → ledger → generated event schemas) to pre-merge checks, so producer/schema divergence fails at the introducing PR — the class of Defect 3. | Observation 137 in the observer log; ships with a negative control per gate discipline. |

### Track 1 — Research Methods Pack + operator-mediated loop (the core)

Provider-neutral. Fits inside P-042 exactly: ARS compiles and records; the operator runs
the session; ARS imports typed results fail-closed. Proposed as one bounded work package
(naming suggestion: **WP-RM1**; whether it becomes WP6.6 or an independent lane like
WP6.5 is sequencing decision D-2).

| # | Deliverable | Content |
|---|---|---|
| 1.1 | **Research Methods Pack v1** — versioned procedural-memory assets selected through W3, stored under `.research-system/` with schema-validated manifests | (a) adversarial review protocol (the paper's 3-stage: initial review → self-critique findings for hallucinations → iterative refinement), (b) counterexample-search brief template with mandatory neutral prove-or-refute framing, (c) context de-identification transform spec — de-identified problem statement + provenance sidecar retaining what was stripped, (d) theorem-retrieval brief requiring external verification of any retrieved statement before it may be cited in an import, (e) decomposition/scaffolding template. Each asset carries the paper section it derives from as evidence lineage. |
| 1.2 | **Brief exporter** — `ars brief export` | Compiles a W3-bounded packet + selected pack assets + import schema + explicit prohibitions (no claim promotion, no transcript ingestion, session metadata required) into a single operator-ready brief. This materializes the P-042 sentence that currently has no tooling. |
| 1.3 | **Typed importer** — `ars brief import` | Fail-closed: validates returned output against import schemas (`ReviewFindingSet`, `CounterexampleCandidate`, `TheoremCitation` with verification status, `ExploratoryMemo`), records operator/session metadata, lands results as W2/W5 artifacts **below claim-promotion authority** — an imported counterexample is a falsification *candidate* until ARS-side verification (Track 2) or human review confirms it. |
| 1.4 | **W6 import-validation fixtures** | Prove mechanically: schema-invalid imports rejected; silent claim promotion impossible; missing session metadata blocks; a de-identified brief's provenance sidecar round-trips; Partial/negative outcomes preserved. |

Effort in report 2's terms: 2–5 person-weeks; no live-provider work; rollback = disable
the two CLI commands (imported artifacts stay immutable, superseding not deleting).

**First pilot use, deliberately not TDA-bound** (per Stephen's steer): the P01-A/P01-B
methods sections and one Markov-ladder null-model design are natural first briefs — the
review-protocol asset applied to a real draft, the counterexample template applied to a
real conjecture-shaped claim — but every asset is written STEM-generic, with the TDA
usage as *its fixture*, not its definition. This is the open-source posture: core pack
generic, TDA appears only in the domain assurance packs that already exist for that
purpose (W5 pack layering).

### Track 2 — Verification-execution lane (after Track 1)

The paper's neuro-symbolic loop, split at the P-042 boundary: the *model* half stays in
the operator's external session; the *execution* half is ARS's — and executing code is
something ARS is fully authorized to do.

| # | Deliverable | Content |
|---|---|---|
| 2.1 | **`VerificationRequest`/`VerificationResult` artifact pair** | A brief import may carry proposed check code (e.g. "this counterexample violates the bound — here is the script"). ARS executes it under existing W8 lease/ops machinery in a controlled environment, records stdout/stderr/traceback/metrics as a typed result bound to the candidate artifact. |
| 2.2 | **Round-trip support** | The exporter can include a prior `VerificationResult` (including the traceback) in the next brief — the paper's automated-feedback step, with the human operator as the relay. Cycle time is minutes, not seconds; that is the accepted P-042 cost, and it preserves a human checkpoint the paper itself says current models need. |
| 2.3 | **Manuscript-review lane** | The PAT-style pre-submission audit as a W5 review lane: a draft section exported with the adversarial-review asset, findings imported as a typed `ReviewFindingSet` feeding the existing review lifecycle. Immediate consumer: P01-A/P01-B drafts; generalizes to any STEM manuscript for the open-source framework. |

### Track 3 — Design-only, explicitly gated (no implementation authority sought)

| # | Item | Status |
|---|---|---|
| 3.1 | Direct provider adapter (Gemini or any other) | Deferred. Requires a new owner decision superseding the relevant part of P-042 plus W4 eligibility evidence, W7 parity, W6 calibration. Keep report 2's §"Full-featured direct-adapter design" (structured-output adapter, receipt normalizer, privacy envelope with `store=false`/no-grounding/no-caching defaults) as the reference design when that day comes. |
| 3.2 | Formalization bridge expansion | Extend the existing Lean lane (05a evidence class, `lean-proof` skill) with proof-obligation export from W5 typed claims. Do not build a new formal subsystem; sequence after Track 2 shows which claims are worth formalizing. |
| 3.3 | TDA-on-proof-states; sheaf-theoretic claim consistency | Speculative. Route through Discovery Harness: `/assay` first; PROMOTE required before any spike. |
| 3.4 | Remote MCP exposure, fine-tuning/distillation | Rejected for now (W1 first release excludes network services; legal/governance-sensitive). |

---

## 3. Decision points for Stephen

- **D-1 (Track 0.2, blocking the suite):** WP6.1 event-schema currency gap — producer
  emits `command_schema_*` vs relax the generated schemas. Recommendation: producer emits.
- **D-2 (Track 1 sequencing):** Does WP-RM1 join the active Gate 6 path (risk: widens
  Gate 6) or run as an independent specification lane like WP6.5 (recommendation:
  independent lane; Gate 6 stays narrow, and the pack is useful before Gate 6 closes)?
- **D-3 (naming/posture confirmation):** Confirm the provider-neutral naming
  ("Research Methods Pack", not "Gemini pack") given the open-source intention.

## 4. What this plan explicitly does not do

No provider invocation, credential handling, or OAuth interaction (P-042). No migration
of active paper artifacts. No claim promotion from imported model output. No adoption of
report 1's module architecture. No speculative research tracks outside the Discovery
Harness. No W11/WP6.5 interaction (independent lane, own review chain).
