---
paper: P01-A
title: "The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries"
status: in-progress
target-journal: "Journal of the Royal Statistical Society Series A"
submitted: null
deadline: null
priority: high
stage: 0
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, persistent-homology, mapper, career-inequality, jrss-a]
---

## Status

Phase 0 scaffolding created for the journal-targeted reorganisation. This paper
absorbs the applied VR-PH regime analysis from `papers/P01-VR-PH-Core/` and the
Mapper interior-structure analysis from `papers/P02-Mapper/`.

Authorship fixed by programme convention: single author Stephen Dorman
(The Open University, UK).

Planned submission strategy: simultaneous JRSS-A submission, JRSS-B companion
submission, and same-day arXiv posting (`stat.AP`).

## Target

Primary: *Journal of the Royal Statistical Society Series A*

## Source Papers

- `papers/P01-VR-PH-Core/` — global topology, regime identification,
  stratified analyses, BHPS replication
- `papers/P02-Mapper/` — within-regime anatomy, outcome geography,
  Mapper robustness analyses

## Draft History

**v1** — 2026-04-30 — ~9,800 words
Path: `papers/P01-A-JRSSA/drafts/v1-2026-04.md`
Assembled from P01-VR-PH-Core v8 and P02-Mapper v5; ~65% cut from ~29k source words.

## v2 revision under APM v1.0.1 management (locked 2026-05-05)

Comprehensive reviewer-response scope across three independent reviewers:

- **R1** (TDA methodologist): 11 issues H1–L3 plus embedded concerns 10.1–10.5
- **R2** (social scientist): 14 issues S1–S14
- **R3** (biostatistician): 13 issues B1–B13

Plus two prose-vs-code mismatches identified during code audit (Markov-2 Laplace
smoothing absent; ε*=0.70 derivation undocumented).

**Authoritative documents.** All issues itemised with strategy, artefacts, and
verification at:

- `notes/2026-05-01-reviewer-response-plan.md` — master integration
- `notes/2026-05-03-reviewer2-social-scientist-issues.md` — S1–S14 detail
- `notes/2026-05-03-reviewer3-biostatistician-issues.md` — B1–B13 detail

**APM execution.** Decomposed by the Planner into 4 Workers (TDA, Panel
Statistics, Reproducibility, Academic Writing), 5 Stages, 74 Tasks. Spec and
Plan at `.apm/spec.md` and `.apm/plan.md`; APM_RULES block in workspace
`CLAUDE.md`; Message Bus at `.apm/bus/`.

**Subsequent (post-v2 follow-on).** Option A full sample re-extraction (R2 §S1.5
Component 1 with full TDA pipeline rerun on the gap-tolerant 10-of-14 sample)
is in scope as APM Plan Stage 4; original 27,280 sample then demoted to
robustness check.

## Open Items

Detailed checklists are in the response plans (P01-A §12 acceptance criteria,
per-issue verification sub-sections) and in `.apm/plan.md` Tasks 0.x–4.x.
Headline categories:

- [ ] Write the integrated JRSS-A outline and argument arc
- [x] Assemble v1 from P01 v8 and P02 v5 — done 2026-04-30; v1 at ~9,800 words
- [ ] Stage 0: locked `uv` environment + two-machine determinism + code-side
      fixes (Markov-2 smoothing, ε* knee algorithm, W₂ test construction,
      regime-label bug) + harmonised-dataset verification (`jbstat`, income
      concept) + sibling clusters from `xhhrel`
- [ ] Stage 1: full null battery + Tier 1/2/3 GLMM + survey-methodology
      computations under locked environment (28 Tasks)
- [ ] Stage 2: v2 prose drafting (22 section-by-section Tasks), supplements,
      JRSS-spec figures, `/notation-check` per change, `/humanizer` at
      completion
- [ ] Stage 3: standalone reproducibility repo extraction
- [ ] Stage 4: Option A full sample re-extraction (post-v2 follow-on)
- [ ] Generate Supplementary A imputation balance by regime
- [ ] Generate Figure S1 from `embeddings_umap16.npy`
- [ ] Move Mapper sensitivity grid and heavy pipeline detail to the supplement
- [ ] Prepare JRSS-A submission package and arXiv metadata (LaTeX class
      `papers/style_guides/JRSS/statsoc.cls`)
- [x] **T1.33 — FOO topology signature (complete 2026-06-02, PR #30).**
      SUPPORT + SIGNAL_NOT_TOPOLOGY_SPECIFIC (p=1/5001, constrained-shuffle,
      B=5000). All 3 local-PH ICCs strictly above zero. Comparator arms
      (raw 90-D bigram, 10-D occupancy) match the topological arm — signal
      is detectable but not topology-specific. §4.5.x prose direction locked:
      "detectable FOO trajectory-geometry signal that topology captures but
      does not uniquely identify." Vault [RESULT] + [DECISION] 2026-06-02.
- [x] **T1.34 — Tier-2 escape regression (complete 2026-06-03, PR #31).**
      GLMM headline withdrawn (pathological sigma_u=35.6066, ICC=0.9974 — IPW
      absorption). Fallback to design-based svyglm (Option A). Rubin-pooled
      (m=20): `regime_initR6` log-OR = 3.5516; OR gate accepted (>1);
      direction consistent with T1.20 baseline. T1.34b: NS-SEC x regime
      cross-tab N=7,275, no sparse cells. T1.34c: full-sample FOO
      sigma_foo = 0.1702, 95% CI [0.0001, 36.9459] — strictly above zero
      but too wide for a strong variance-component claim. §S8 reports this as
      fragile, specification-sensitive disclosure; the main family-origin
      contribution rests on local trajectory-geometry analysis plus
      non-topology-specific comparator checks.
      Vault [RESULT]×2 + [DECISION] 2026-06-03.
- [x] **T1.35 — FOO transparency supplement (complete 2026-06-03, PR #31).**
      Corrected power simulation (boundary-mixture reference, ICC=0
      calibration). Engine not calibrated (type-I=0.951 at ICC=0): no
      minimum-detectable-ICC claim reported. Corrected sibling concordance:
      κ=0.0445, 95% bootstrap CI [−0.0552, 0.1952]; 396 pairs (was 342
      before ordered-pairs correction). σ_foo=6.23 flagged as separation
      artifact. §S8 framing: non-estimability — T1.21/T1.34/T1.35 are one
      consistent story. Vault [RESULT] 2026-06-03c.
- [x] **Pre-reg #5 redo amendment closure — Outcome A locked (2026-05-31).**
      Both length-matching strategies reject H₁ W₂ at α=0.05 under the
      external-indexing dedup methodology (truncate p=0.001 vs the
      2026-05-29 no-dedup p=0.350; first13 p=0.001 first time under
      frozen-loadings). The BHPS-vs-USoc H₁ signal is not a length-of-
      observation artefact. Vault [DECISION] 2026-05-31 (Computational-Log)
      + CONVENTIONS entry (always-rule for external-indexing dedup) +
      Pipeline-Overview entry + PR #28 (branch `run/length-matched-dedup-rerun`,
      commits `707571d` → `18ce018`). Closure artefact:
      `results/trajectory_tda_integration/stage1/dedup_amendment_comparison_2026-05-31.json`.
- [ ] **Auto-thresh sanity probe — length-matched cells covered; T1.36
      BHPS headline frozen still pending.** Partially closed 2026-05-31:
      probe (3) `pinned_thresh` on T1.2f truncate confirmed the
      `compute_rips_ph` auto-thresh divergence is not the driver of the
      H1 W2 rejection direction (S/N drift <1% under pinned thresh =
      enclosing radius of observed landmarks). Remaining work: same probe
      against T1.36 BHPS headline frozen (the headline cell in the
      production W2 + landscape battery, not under length-matching).
      Sequencing: at next natural opportunity; not blocking any
      submission-critical work. Applies equally to P01-B headline cells.
- [~] **SI methodological-disclosure paragraph for the dedup amendment —
      DRAFTED 2026-06-21, pending User per-section review.** Section file:
      `papers/P01-A-JRSSA/drafts/sections/supplement-S6-length-matched-dedup.md`
      (working §S6; final number at v2 assembly). Covers (a) the rationale
      for external-indexing dedup, (b) the H1 W2 flip from p=0.350 to
      p=0.000999 and why it is mechanistic (mean_obs_null 202.84→6.63 once
      the ~139 near-zero-scale phantom H1 features are stripped; S/N
      1.006→1.867), (c) the two robustness probes. **Drafted from the
      CORRECTED 2026-06-01 comparison JSON, not the 2026-05-31 draft field:
      the pinned_thresh H0 cell drifts +6.7% (T-ratio 7.87→8.40), not "<1%
      everywhere" — rejection preserved in every cell regardless, Outcome A
      unaffected.** notation-check: 1 borderline obs/null-superscript leakage
      flag (kept, consistent with §S0 precedent). Applies equally to P01-B
      headline cells (cross-reference from P01-B, do not duplicate).
