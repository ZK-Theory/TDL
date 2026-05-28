---
date: 2026-05-25T11:30:00Z
project: P01-A and P01-B Reviewer-Response Revision to v2
stages_completed: 0
total_tasks: 81
outcome: incomplete
---

# Session Summary — Manager Instance 1 (2026-05-25)

## Project Scope

The project produces v2 drafts of two companion academic papers — **P01-A** (JRSS-A applied: "The Geometry of UK Career Inequality") and **P01-B** (JRSS-B methods: "Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data") — that close every numbered reviewer issue from three independent reviewers per paper, then extract standalone reproducibility repositories and prepare simultaneous JRSS submission with same-day arXiv posting (`stat.AP` and `stat.ME`). Both papers are revised in lockstep because they share the same checkpoint, embedding, null battery, and Wasserstein audit. Single-author work; no deadline; patient cadence. Workers: TDA Agent (persistent homology, null batteries, Mapper, code-side fixes), Panel Statistics Agent (sample construction, weighting, MICE, GLMM, Firth, mediation), Reproducibility Agent (locked environment, seed propagation, two-machine determinism, repo extraction), Academic Writing Agent (v2 prose, supplements, figures, notation, humanizer).

## Stages and Outcomes

**Stage 0 — Foundation (13 tasks):** 12 of 13 Done before this session. T0.3 (two-machine determinism) remains paused on `pipe/two-machine-check` awaiting User's `canary_machine2_2026-05-07.json`. Only gates §5 reproducibility prose, not Stage 1.

**Stage 1 — Locked numerical and statistical results (32 tasks, expanded from 29 this session):** Active and the primary focus of the session. **No Tasks completed in this session by Workers.** Manager-side work in this session reframed the Stage 1 scope by:
- Closing T1.21 as Done-superseded (Tier 3 cross-classified GLMM structurally non-estimable on R2/R6 subsample, ~92% FOO singletons)
- Deferring T1.22 (formal mediation moved out of scope for this paper)
- Adding three new tasks (T1.33, T1.34, T1.35) that re-architect the FOO-effects analysis around a topology-side test (per-individual local persistence + sibling-pair coherence) as the substantive contribution, with regression-side defensive infrastructure

T1.2b–h batch continues overnight on `run/stage1-headline-batch` (commits b/c/d landed earlier; commits e/f landed during this session per `git log`; g/h pending). All Stage 1 results from this batch are now flagged **provisional** pending null-layer audit (see Known Issues).

**Stage 2 — v2 drafting (22 tasks):** T2.1, T2.2, T2.3 already merged before this session. T2.4 and T2.10 dependencies updated this session to reflect the new Stage 1 task structure. No new dispatches this session.

**Stage 3 — Reproducibility extraction (4 tasks):** Not started.

**Stage 4 — Option A full re-extraction (10 tasks):** Not started.

## Key Deliverables

This session produced no computational deliverables. All session output was Manager-side coordination, planning-document modifications, and methodological re-architecture:

- `.apm/spec.md` — three section edits + YAML `modified` field updated. §"Final regression specification" replaced (Tier 3 abandoned); §"Endogeneity / mediation framework" replaced (formal mediation deferred to descriptive framing); new §"Topological FOO Signature" section added after §"Panel-Data and Regression Decisions".
- `.apm/plan.md` — T1.21 + T1.22 STATUS UPDATE blocks added to Guidance fields; three new task definitions inserted (T1.33 TDA Agent, T1.34 + T1.35 Panel Statistics Agent); T2.4 + T2.10 dependencies updated; Mermaid dependency graph extended with 3 nodes + 9 new edges + 3 style entries; YAML `modified` field updated.
- `.apm/tracker.md` — Task Tracking updated for T1.21 (Done-superseded), T1.22 (Deferred), T1.32 (Done-reconciled), T1.33/T1.34/T1.35 (Ready, held); Worker Tracking updated (panel-statistics-agent-2 retired); three new Working Notes added (incoming-Manager reconciliation, FOO-strategy transition, critical null-layer finding).
- `.apm/memory/code-review-2026-05-25.md` — full 17-item triage of external code review with critical null-layer finding confirmed by Manager code read.
- `.apm/memory/handoffs/manager/handoff-01.log.md` — Handoff Log for incoming Manager 2 (past actions, working context).
- `.apm/bus/manager/handoff.md` — Handoff prompt for incoming Manager 2 (current state, immediate next actions).
- `papers/shared/literature/2025-benites-rudkin-topology-educational-outcome-inequality.md` — PDF-to-markdown conversion of a third-party paper (SSRN 5401815) used for methodological-strategy discussion.
- **5 vault entries** filed via `vault_observe` to `04-Methods/Computational-Log`: `[NEGATIVE]` for T1.21 cross-classified non-estimability + `[DECISION]` pre-regs for T1.33, T1.34c, T1.35 + T1.33 pre-reg amendment (simpler-method comparators C1/C2).
- Stale local branch `run/sensitivity-independence` deleted (already merged at `3b0fc74`).
- Stale `panel-statistics-agent-2/task.md` bus contents cleared.

## Codebase State

The codebase state is **largely unchanged this session.** All five Spec/Plan/Tracker/memory/handoff edits are uncommitted on `main` at session end. The two external Workers (tda-agent on overnight batch + paused T0.3) produced commits on their feature branches that have not been merged to `main`.

Discrepancies between `.apm/` planning state and codebase:
- **`trajectory_tda/topology/permutation_nulls.py` contains code that does not match the planning documents' inferential claims.** Specifically, `_label_shuffle` and `_cohort_shuffle` (lines 53-92) are pure row permutations of an already-computed embedding matrix, which is PH-invariant. The planning documents and existing Stage 1 vault entries assume these nulls perform real label-shuffle and cohort-shuffle tests. The codebase implementation does not. This gap was discovered during this session's code-review triage; no fix has been dispatched.
- **Three new Stage 1 task definitions are in the Plan but no implementation work has begun.** T1.33 requires a new TDA-side script (per-individual local persistence on the 90-D bigram embedding via k-NN sub-cloud PH); T1.34 requires a new R script (`svyglm` + cluster-robust SE column added to the Tier 2 regression); T1.35 requires three new scripts (power simulation, singleton decomposition, sibling-pair concordance).
- **All Stage 3 and Stage 4 task code is absent** (these stages have not begun).

## Notable Findings

**Methodological:**
- The Tier 3 cross-classified GLMM specification in `.apm/spec.md` (pre-amendment) was structurally non-estimable on the disadvantaged-starter (R2/R6) subsample due to ~92% FOO singleton dominance. T1.21's diagnostic run (commit `ddc7efb` on `run/tier3-regression`) confirmed this empirically. The User-led methodological discussion produced a tightened replacement strategy that centers a topology-side FOO test (T1.33) as the substantive finding, rather than expanding the regression apparatus.
- The initial proposed FOO strategy (10 analytical units across Phase A/B/C plus formal Imai-Keele-Tingley mediation) was reduced to 3 units after User pushed back on regression-methodology drift away from the paper's TDA-centric brand. Formal causal mediation was deferred to a follow-up paper. The tighter strategy preserves the substantive FOO contribution while keeping the regression layer minimal.
- The User added a pre-reg amendment to T1.33 requiring simpler-method comparators (C1 bigram-coordinate ICC + C2 summary trajectory feature ICC) to be run in parallel, with an interpretation rule that distinguishes "topology-distinctive finding" from "topology recovers what simpler methods also find." This defends the methodology against the "you could have got this from cheaper stats" reviewer line.

**Operational:**
- The Handoff Bus was empty at session start despite the project being in flight. Reconstruction-from-Tracker worked but missed nuance. Future Manager handoffs should not leave the Handoff Bus empty — even in-flight session endings should produce a Handoff Log per the standard procedure. This session ends with a proper Handoff Log written to address this gap.
- Three Tracker-vs-git divergences existed at session start and were reconciled: (1) T1.32 marked Active but actually merged 2026-05-16 at `11eb993`; (2) panel-statistics-agent-2 marked active but its sole task was Done; (3) `run/sensitivity-independence` was a stale local branch never deleted post-merge. Worth checking for similar drift at the start of each new Manager session.

**Code review (critical):**
- External static review of `trajectory_tda/` flagged 17 findings at P0/P1/P2 severity. Phase 1 triage performed in session; one critical Phase 2 investigation completed: the label-shuffle and cohort-shuffle null implementations in `permutation_nulls.py` are pure row permutations of an already-computed embedding matrix, which is mathematically PH-invariant. **Every reported label-shuffle and cohort-shuffle p-value in the project record is methodologically vacuous, including the 2026-05-22 BHPS L=5000 "clean negative controls" finding that triggered a recent CONVENTIONS edit.** Observed p ≈ 0.5 for these nulls is landmark-subsampling variance, not a label-shuffle test.
- Whether the Markov-1 / stratified-Markov-1 nulls (T1.2/T1.3 headline tests) are also corrupted depends on whether `ngram_embed()` re-fits PCA per call (coordinate-frame mismatch). This is the top-priority Phase 2 investigation for the incoming Manager session.

## Known Issues

- **Null-layer audit unresolved.** Critical methodological issue documented in `.apm/memory/code-review-2026-05-25.md`. Hold on T1.33/T1.34/T1.35 dispatch. Vault `[NEGATIVE]` filing deferred to fresh Manager session per User direction.
- **CONVENTIONS edit needs reversal/restatement.** The 2026-05-22 vault `[DECISION]` entry that replaced the original "NEVER treat BHPS shuffles as assumed negative controls" rule is invalidated by the null-layer finding. The original rule may have been correct in spirit (wrong technical reason). Decision deferred to fresh Manager session.
- **T1.2b–h batch results arriving from `run/stage1-headline-batch` are provisional.** Already vault-logged: T1.2b BHPS headline (commit `75ea678`), T1.2c USoc L=2500 (commit `37bff84`), T1.2d USoc L=8000 (commit `e354b9a`). T1.2e/f appear to have landed during this session (2 new commits on the branch); T1.2g/h pending. None of these should be treated as final until null-layer audit completes.
- **Spec/Plan/Tracker/memory edits uncommitted on `main`.** The Manager session ends with all five `.apm/` artefact edits uncommitted. The incoming Manager should decide whether to commit before further work (recommended: yes, with a `[PIPELINE] APM:` prefix per the project's commit convention).
- **T0.3 two-machine determinism check still paused** awaiting `canary_machine2_2026-05-07.json` from the User.
- **Pending Phase 2 code-review investigations** beyond the null-layer audit: P0-4 BHPS ID resolution, P1-8 Firth/L1 misnomer in `age_stratified.py`, P0-1/P0-2 zigzag dormancy, P2-5 stability SE metric mismatch.

## Snapshot Notice

This summary reflects the session state as of 2026-05-25T11:30:00Z. The codebase may have diverged since this summary was created — in particular, the T1.2b–h overnight batch is still running on `run/stage1-headline-batch` and may produce additional commits before the incoming Manager session begins.
