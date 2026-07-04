# Lean 4 / Leanstral Integration — Scout & Plan

**Date:** 2026-07-04
**Status:** Scout/plan only — no implementation authorized; spikes gated on Stephen's PROMOTE decision
**Author:** Claude (Fable 5), interactive session with Stephen
**Scope decisions (Stephen, 2026-07-04):** Lean enters the ARS as BOTH an assurance lane and a research-strand agent (not an APM worker — APM is being retired for ARS). All three maths framings stay open pending spikes. Plan lives here; Nexus College adjunct is a secondary strand.

---

## 1. Purpose

Assess feasibility and value of adding a Lean 4 theorem-proving capability — driven by the locally installed specialist model **Leanstral 1.5** (`mistralai/Leanstral-1.5-119B-A6B`, launched via `vibe --agent lean`) — as:

1. a **formal-assurance lane** inside the ARS (W5) for mathematical claims;
2. a **pure-mathematics research strand** attacking the programme's core bottleneck: TDA on large complexes from large social-science panels, where almost all published TDA work stays on small, simple datasets;
3. an **adjunct to Nexus College** (`MathUni/docs/specs/2026-07-03-nexus-college-design.md`), whose assessment pillar is already "rigorously graded proofs" but which currently has no formal-verification strand.

## 2. Feasibility assessment

### 2.1 What exists (as of knowledge cutoff — spike S1 must re-verify)

- **Lean 4 + mathlib4** is mature and Windows-friendly (elan/lake toolchain; first mathlib build is heavy — use `lake exe cache get` for prebuilt oleans).
- mathlib4 contains: simplicial complexes, chain complexes, categorical (singular/simplicial) homology, extensive order/lattice/metric-space theory.
- mathlib4 does **not** contain (to my knowledge): persistent homology, persistence modules, interleaving/bottleneck distance, the stability theorem, discrete Morse theory in usable form, or strong-collapse theory. There are isolated external formalisation efforts, none merged at scale.
- **Implication:** the formalisation gap is the central fact of this plan. It is simultaneously the main **cost** (foundational build-out needed before "real" persistence theorems) and the main **opportunity** (formalised persistence theory is near-virgin territory — a genuine, publishable pure-maths contribution lane, distinct from and complementary to the empirical papers).

### 2.2 Leanstral 1.5 — unverified locally

I cannot verify the model or the `vibe` CLI from this session (post-cutoff release; no probe run under budget). **Spike S0 (smoke test) is the mandatory first step** and everything downstream is conditional on it. The claimed profile — a Lean-specialist MoE (119B total / ~6B active) run locally — is exactly right for this role: proof search is iterate-heavy and token-hungry, so pushing it onto a local specialist keeps the Claude budget for orchestration and statement design. Per the standing rule (skill-obs #19), treat the model-card claims as hypotheses to test, not capabilities to assume.

### 2.3 Why the token economics favour this

Proof development is the worst possible workload for a metered frontier model: long tactic-search loops, verbose error feedback, many dead ends. Division of labour:

| Work | Who | Cost |
|---|---|---|
| Statement design, referent check, spec authoring | Claude (Manager/human) | small, high-value |
| Proof search, tactic iteration, mathlib navigation | Leanstral (local) | zero API tokens |
| Verification | Lean kernel (`lake build`) | zero tokens, absolute |

The Lean kernel is the cheapest and strongest verifier in the entire programme: deterministic, fail-closed, non-LLM.

## 3. Value added

### 3.1 ARS assurance lane (W5)

W5 already defines proof obligations, domain assurance packs, two-key validity, and claim promotion. A Lean lane slots in without changing the architecture:

- **New evidence class `lean_proof`** in a domain pack: a claim of kind "mathematical" at R2/R3 can discharge its proof obligation with a Lean artefact instead of (or alongside) LLM review.
- **Two-key validity, strengthened:** the second key becomes the Lean kernel — verifier independence *by construction*, immune to correlated-reviewer failure (the exact worry skill-obs #24 raised about W5).
- **Acceptance contract for a `lean_proof` artefact** (all machine-checkable, fail-closed):
  1. `lake build` exits 0;
  2. no `sorry`/`admit` (grep + `#print axioms` on the theorem);
  3. axiom audit: only the standard mathlib axiom set (`propext`, `Classical.choice`, `Quot.sound`);
  4. **statement-referent check** — the formal statement provably matches the claim being promoted.
- **The critical risk is (4), not proof correctness.** A prover can flawlessly prove the *wrong statement* — the Lean analogue of skill-obs #13's referent trap. Mitigation mirrors the Manager-authors-contracts split (obs #7): the **statement is authored/reviewed independently of the prover** (Claude/human writes or signs off the `theorem` signature; Leanstral only fills the proof). This split should be stated in the W5 domain-pack spec when written.
- **Routing (W4/W7):** Leanstral is a new provider — a role profile (`lean-prover`), capability evidence via eval fixtures (S0/S2 outputs seed these), and a `vibe` CLI adapter generated from canonical policy per W7. Receipts are `.lean` files + build logs — ideal for W6 evaluation and replay.

### 3.2 Research strand — the large-complex problem

The hunch: the scaling wall is mathematical, not just computational, and the field's small-data habit means the maths of *large* complexes is under-exploited. Three framings, all retained (Stephen, 2026-07-04):

- **A. Approximation with guarantees.** Sparsification/subsampling/witness schemes with provable interleaving or bottleneck error bounds for the specific structure of panel-trajectory complexes. Proofs are the deliverable; Lean certifies the bounds.
- **B. Exact structure exploitation.** Compute exactly but cheaper: strong collapse, discrete Morse reductions, cohomology-based shortcuts. Lean's role: verify the reduction is homology-preserving — turning "we trust the collapse implementation" into a checked theorem, which then justifies aggressive preprocessing in the pipeline.
- **C. New invariants for scale.** Cheaper topological summaries designed for large categorical-state panel data, with proven stability. Highest novelty, highest risk; the MCbiF work (skill-obs #34 territory) is adjacent.

Differentiator: coupling **formal guarantees** to **large real social-science data** is a combination essentially absent from the literature — most scalability papers prove bounds on paper for geometric point clouds; most applied papers prove nothing.

### 3.3 Nexus College adjunct (secondary)

- Add an **optional Lean strand** to the Semester 1 proof workshop (Natural Number Game → mathlib exercises), becoming a graded lane by Semester 3. Lean grading is objective and zero-token (kernel checks; Leanstral available as hint-giver, not oracle — consistent with the hint-ladder design).
- Guard: Semester 1 already carries three courses + proof workshop for an ADHD learner. Lean must enter as *engagement variety* (unlockable DAG node), not additional mandatory load. Defer the decision to the first syllabus review; the design doc needs only a one-paragraph placeholder.
- Long-run convergence: by Semester 4, the capstone could *be* a piece of the research strand (formalise one lemma used by the pipeline) — mission-aligned in exactly the way `MISSION.md` demands.

## 4. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Leanstral/`vibe` doesn't work as claimed | Blocks everything | S0 smoke test first; nothing else spends effort until it passes |
| mathlib persistence gap larger than estimated | High (strand A/C) | S1 gap survey before choosing a framing; strand B needs least new foundation |
| Proving the wrong statement | High (assurance lane) | Statement/prover authorship split (§3.1); referent line in every result entry |
| Foundational formalisation becomes a time sink detached from the papers | Medium | Every spike is token/time-boxed with a kill criterion; formalisation targets must trace to a pipeline claim or paper lemma |
| Windows toolchain friction (build times, paths) | Low-Medium | `lake exe cache get`; keep Lean projects in a dedicated repo, not inside TDL |

## 5. Spike candidates (each gated on PROMOTE; run via /spike discipline — toy outputs never enter `results/`)

| ID | Spike | Question answered | Box | Priority |
|---|---|---|---|---|
| **S0** | Smoke test: `vibe --agent lean` proves a trivial + a mathlib-dependent lemma; kernel-verify; capture the interaction pattern | Does the tool work at all? What's the driving interface (CLI turnaround, context, mathlib access)? | ≤1 hr, near-zero Claude tokens | **First, mandatory** |
| **S1** | Formalisation gap survey (Leanstral-driven): what exists in mathlib4 for simplicial complexes / homology / persistence / Morse theory; map each framing A/B/C to "distance from mathlib frontier" | Which research framing is cheapest to enter formally? | ½ day | Second |
| **S2** | Micro-formalisation end-to-end: one small real lemma (candidate: the corrected max-achievable-ARI bound from T1.23d — small, combinatorial, and it was *actually wrong once*, so formalising it has genuine assurance value) | Can the full pipeline (statement by Claude → proof by Leanstral → kernel check → artefact contract) produce an assurance-grade object? | 1 day | Third — this is the assurance-lane pilot |
| **S3** | Strand-B probe: formalise homology-preservation for one concrete collapse/reduction actually usable in the TDL pipeline | Does the "verified preprocessing" path give practical licence to shrink complexes? | 2–3 days, post-S1 | Conditional on S1 |
| **S4** | Nexus College Lean-strand pilot (one NNG-style session, wired to `/today`) | Is the engagement cost/benefit right for Semester 1? | ½ day | Deferred — after ARS strands prove out |

**Sequencing:** S0 → S1 → S2, then decide between S3 and a strand-A/C spike using S1's frontier map. S0–S2 total well under one week of part-time effort and almost no metered tokens (Leanstral does the expensive iteration).

## 6. Integration next-actions (post-spike, for the ARS spec queue)

1. W5 domain-pack addendum: `lean_proof` evidence class + acceptance contract + statement/prover authorship split.
2. W4 role profile `lean-prover` with capability evidence seeded from S0/S2 receipts.
3. W7 adapter spec for the `vibe` CLI provider (receipts: `.lean` + build log + axiom audit).
4. One-paragraph Lean-strand placeholder in the Nexus College design doc (decision deferred to first syllabus review).
5. Decide the research-strand framing (A/B/C) from S1 evidence; write its pre-registration via the existing /assay → /spike → pre-reg funnel.

None of these start until Stephen accepts the spike results — consistent with the ARS rule that no implementation precedes its review gate.
