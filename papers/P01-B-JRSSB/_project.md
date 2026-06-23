---
paper: P01-B
title: "Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data"
status: in-progress
target-journal: "Journal of the Royal Statistical Society Series B"
submitted: null
deadline: null
priority: high
stage: 0
domain: trajectory_tda
data: [USoc, BHPS]
tags: [paper, tda, hypothesis-testing, wasserstein, zigzag, jrss-b]
---

## Status

Phase 0 scaffolding created for the JRSS-B methodology paper. This paper
combines the Markov memory ladder and diagram-level testing material from
`papers/P01-VR-PH-Core/` with the survey-design diagnostic toolkit from
`papers/P03-Zigzag/`.

Authorship fixed by programme convention: single author Stephen Dorman
(The Open University, UK).

Planned submission strategy: simultaneous JRSS-B submission, JRSS-A companion
submission, and same-day arXiv posting (`stat.ME`).

Post-audit W2 insert and repo extraction note prepared in
`papers/P01-B-JRSSB/notes/2026-04-07-post-audit-w2-insert.md` and
`papers/P01-B-JRSSB/notes/2026-04-07-post-audit-w2-repo-note.md`.

## Target

Primary: *Journal of the Royal Statistical Society Series B*

## Source Papers

- `papers/P01-VR-PH-Core/` — null hierarchy, scalar vs diagram-level testing,
  UK application results
- `papers/P03-Zigzag/` — survey-design diagnostics, pool-draw nulls,
  spanning-individual decomposition

## v2 revision under APM v1.0.1 management (locked 2026-05-05)

Comprehensive reviewer-response scope across three independent reviewers:

- **R1** (TDA methodologist): 12 issues C1–C2 (Critical), H1–H4, M1–M5, L1
- **R2** (data/empirical reviewer): 11 issues D1–D11
- **R3** (biostatistician): 13 issues B1–B13 — shared with P01-A; many [P01-A
  SHARED] computations execute once and feed both papers

Plus two prose-vs-code mismatches identified during code audit:

- `permutation_nulls.py:168–234` does no Laplace smoothing on Markov-2 (uniform
  fallback only) — §3.2 prose says it does. Fix in APM Stage 0 Task 0.4.
- ε*=0.70 used in §4.3.2 does not match `knee_analysis.json` (median=0.54,
  mean=0.51). Knee algorithm formalised in APM Stage 0 Task 0.6.

**Authoritative documents.** All issues itemised with strategy, artefacts, and
verification at:

- `notes/2026-05-01-reviewer-response-plan.md` — master integration
- `notes/2026-05-03-reviewer2-data-empirical-issues.md` — D1–D11 detail
- companion P01-A reviewer plans for shared R3 issues

**APM execution.** Decomposed by the Planner into 4 Workers (TDA, Panel
Statistics, Reproducibility, Academic Writing), 5 Stages, 74 Tasks (most P01-B
issues are shared with P01-A; standalone P01-B coverage in Stage 2 §3.1–§3.4
methods rewrites + §4.2/§4.3 results + §5 reproducibility + supplement). Spec
and Plan at `.apm/spec.md` and `.apm/plan.md`; APM_RULES block in workspace
`CLAUDE.md`; Message Bus at `.apm/bus/`.

**JRSS-B repo + Zenodo.** Standalone repo extraction is APM Plan Stage 3
Task 3.2; Zenodo DOI applied at submission, post-v2 (or v3) draft. JRSS-B's
"public archived code with persistent DOI before acceptance" requirement is met
by Stage 3 + DOI registration at submission.

## Open Items

Detailed checklists are in the response plans (P01-B §15 acceptance criteria,
per-issue verification sub-sections) and in `.apm/plan.md` Tasks 0.x–4.x.
Headline categories:

- [x] Formalise the spanning-individual decomposition and pool-draw null model
      — completed 2026-04-30; see `notes/formalised-survey-toolkit.md`
- [x] Insert the post-audit W2 table and paragraph — folded into §4.2.1–4.2.3
      of v1 (will be regenerated under locked environment in v2 per APM Plan)
- [x] Update the draft text to reflect the resolved W2 audit and replay caveat
      — §4.2.1 of v1 (replaced by reproducibility statement in v2 per APM
      Plan Task 2.18)
- [x] Assemble v1 from P01 v8 and P03 v2+ — completed 2026-04-30; v1 at ~9,100
      words
- [ ] Stage 0: P01-B H3 reproducibility lock-in — pinned `uv.lock`,
      two-machine bit-for-bit determinism, deterministic seed propagation
- [ ] Stage 0: code-side prose-vs-code fixes (Markov-2 Laplace smoothing α=1;
      ε* knee algorithm formalisation; W₂ test construction mean-vs-mean BCa)
- [ ] Stage 1: matched-L W₂, stratified Markov-1, landscape L², Markov-2 α
      sensitivity, BHPS H4 negative-control three-hypothesis diagnostics, all
      under locked environment (shared with P01-A)
- [ ] Stage 2: v2 §3.1–§3.4 methods rewrites (ground-metric formula correction,
      stratified rung formal definition, W₂ test construction + landscape +
      effect sizes, knee algorithm + spanning AUC/W₂ + identification check),
      §4.2/§4.3 results, §5 reproducibility, abstract reframing per C2 outcome
- [ ] Stage 3: standalone P01-B repo extraction with locked env, code subset,
      data pointer, replication script, headline-number provenance table
- [ ] Keep zigzag exposition brief and explicitly subordinate to the testing
      framework
- [ ] Use `notes/2026-04-07-post-audit-w2-repo-note.md` when building the
      standalone paper repo (treats `post_audit` W2 JSONs as authoritative —
      will be superseded by locked-env JSONs in v2)
- [ ] Prepare JRSS-B submission package and arXiv metadata (LaTeX class
      `papers/style_guides/JRSS/statsoc.cls`)
- [x] **§4.3 spanning identification — DRAFTED 2026-06-22; Manager-ACCEPTED
      2026-06-22 (2.17-A: §4.3 inherits the 2026-06-20 prose-direction [DECISION], commit
      `acb7f8a3` — no separate §4.3 lock needed; STANDS). Matched/age-stratified Betti
      rerun stays a separate low-priority TDA task (held vs T1.6) — keep §4.3's "pending
      robustness check" framing.** Section file:
      `papers/P01-B-JRSSB/drafts/sections/results-spanning-identification.md`.
      Headline is the T1.9b inferential result (`spanning_betti_inference_2026-06-20.json`,
      outcome `newcomers_robust`): windowed β₀-AUC ratio robust across all four ε*
      (1.127–1.129, p=0.001, bootstrap CI excludes parity) + matched W₂=2.536 (p=0.001),
      direction newcomers>spanning; single-ε ratio fragile (sig only at locked ε*=0.54).
      Resolves the earlier T1.9 "divergent" point estimate (full-interval AUC artefact).
      Table 4 = 3 statistics × 4 ε*. Balance table from `balance_2026-05-14.json` (age
      SMD −0.617, hiqual 0.300, employed 0.193, sex 0.002) + matched/age-strat design
      from `matched_subset_2026-05-14.json`. notation-check clean (W₂ order explicit;
      landscape correctly omitted per response-plan §10). **Two dependencies flagged:**
      (a) matched/age-stratified Betti rerun escalated to TDA agent, not yet committed —
      stated as pending, not fabricated; (b) manuscript prose-direction lock Manager-deferred
      per the result file — file the vault [DECISION] before v2 assembly.
- [x] **§5 reproducibility statement (replay-drift → reproducibility) — DRAFTED
      2026-06-22; Manager-ACCEPTED AS DRAFTED 2026-06-22 (2.18-A single-machine scope
      correct, STANDS; cross-machine upgrade to the response-plan wording is a future task
      when T0.3 two-machine check completes).** Section file:
      `papers/P01-B-JRSSB/drafts/sections/results-reproducibility-statement.md`.
      Replaces the v1 §4.2.1/§5.3 replay-drift disclosure with a positive statement:
      locked env + `uv.lock` (Python 3.13 + gudhi/ripser/sklearn pinned), deterministic
      seed propagation, single-machine run-to-run determinism verified by
      `trajectory_tda/scripts/canary_rng.py`. No "drift"/"discrepancy"/"may not exactly
      reproduce" in the main-text framing; legacy replay-provenance moved to supplement
      (W1-ruling-out reworded as "order-1 Wasserstein" to satisfy the notation guard).
      **Honesty constraint honored:** the two-machine bit-for-bit check (T0.3) is PAUSED
      (second machine pending; `pipe/two-machine-check` worktree live), so cross-machine
      determinism is framed as achievable/in-progress, NOT verified — deliberately weaker
      than response-plan §5.4(5), flagged inline for upgrade when T0.3 completes.
