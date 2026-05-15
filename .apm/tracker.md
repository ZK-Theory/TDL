---
title: P01-A and P01-B Reviewer-Response Revision to v2
---

# APM Tracker

## Task Tracking

**Stage 0:**

| Task | Status | Agent | Branch |
|------|--------|-------|--------|
| 0.1 | Done | reproducibility-agent | |
| 0.2 | Done | reproducibility-agent | |
| 0.3 | Active | reproducibility-agent | pipe/two-machine-check |
| 0.4 | Done | tda-agent | |
| 0.5 | Done | tda-agent | |
| 0.6 | Done | tda-agent | |
| 0.7 | Done | tda-agent | |
| 0.8 | Done | tda-agent | |
| 0.9 | Done | panel-statistics-agent | |
| 0.10 | Done | panel-statistics-agent | |
| 0.11 | Done | panel-statistics-agent | |

**Stage 1:**

| Task | Status | Agent | Branch |
|------|--------|-------|--------|
| 1.1 | Active | tda-agent | run/core-tda-battery |
| 1.2 | Active | tda-agent | run/core-tda-battery |
| 1.3 | Active | tda-agent | run/core-tda-battery |
| 1.4 | Pending | tda-agent | |
| 1.5 | Pending | tda-agent | |
| 1.6 | Pending | tda-agent | |
| 1.7 | Pending | tda-agent | |
| 1.8 | Pending | tda-agent | |
| 1.9 | Pending | tda-agent | |
| 1.10 | Pending | tda-agent | |
| 1.11 | Pending | tda-agent | |
| 1.12 | Done | panel-statistics-agent | run/bic-ipw-mice-income |
| 1.13 | Done | panel-statistics-agent | run/bic-ipw-mice-income |
| 1.14 | Done | panel-statistics-agent | run/bic-ipw-mice-income |
| 1.15 | Done | panel-statistics-agent | |
| 1.16 | Done | panel-statistics-agent | |
| 1.17 | Done | panel-statistics-agent | |
| 1.18 | Done | panel-statistics-agent | |
| 1.19 | Done | panel-statistics-agent | |
| 1.20 | Done | panel-statistics-agent | run/tier2-regression |
| 1.21 | Ready (held) | panel-statistics-agent | run/tier3-regression |
| 1.22 | Waiting: 1.21 | panel-statistics-agent | |
| 1.23 | Ready (held) | panel-statistics-agent | |
| 1.24 | Done | panel-statistics-agent | |
| 1.25 | Ready (held — spec ambiguity) | panel-statistics-agent | |
| 1.26 | Waiting: 1.2 | panel-statistics-agent | |
| 1.27 | Ready (held) | panel-statistics-agent | |
| 1.28 | Waiting: 1.2 | panel-statistics-agent | |
| 1.29 | Done | panel-statistics-agent | |
| 1.30 | Done | panel-statistics-agent | |
| 1.31 | Done | panel-statistics-agent | |
| 1.32 | Active | panel-statistics-agent | pipe/coderabbit-batch3 |

## Worker Tracking

| Agent | Instance | Notes |
|-------|----------|-------|
| reproducibility-agent | 1 | active (T0.3) |
| tda-agent | 1 | active (T1.1–T1.3 batch) — worktree run-core-tda-battery |
| panel-statistics-agent | 1 | idle (T1.30 Done + merged 2026-05-15) — awaiting next dispatch; T1.21 deferred pending all fix batches |
| panel-statistics-agent | 2 | active (T1.32 Batch 3 — IPW SMD+overlap, NSSEC propagation-skip, ~15 script/style fixes) — worktree pipe-coderabbit-batch3 |
| academic-writing-agent | 1 | uninitialized |

## Version Control

| Repository | Base Branch | Branch Convention | Commit Convention |
|-----------|-------------|-------------------|-------------------|
| `c:\Users\steph\TDL` | `main` | `pipe/<desc>` for pipeline code-side fixes; `run/<desc>` for computational Tasks; `paper/<desc>` for prose Tasks; `repo/<desc>` for repo-extraction Tasks | `[PREFIX] PXX: <description>` with PREFIX ∈ `{RESULT, DECISION, NEGATIVE, PIPELINE, DATA, EXPLORE}`; Co-Authored-By trailer; pre-commit hooks run (no `--no-verify`) |

> Note: worktree directory names are derived from branch names by replacing `/` with `-`. Branch names remain slash-form for git semantics, while the corresponding `.apm/worktrees` folder uses the hyphenated slug.

## Working Notes

- **2026-05-14 (afternoon): panel-stats workers held pending coordinated code-review fix batch.** panel-statistics-agent-1 is idle (T1.21 dispatched to bus but not yet started; HOLD issued); panel-statistics-agent-2 is mid-batch on `run/sensitivity-independence` and will pause after current dispatch (HALT-after-batch in bus). T1.21 deferred until post-fix because it consumes T1.18 NS-SEC proxy values that B4 fixes may alter. Workers stay idle/halted until both have reported and User has reviewed the fix-batch dispatch plan.
- **2026-05-14 (afternoon): Three-batches-by-file-domain fix plan (User-confirmed structure).** Batches branch off main as separate dispatch units to keep merges clean. Detailed task scoping deferred until dispatch time. High-level batch composition: **Batch 1 (`pipe/coderabbit-manski`)** — A3 undefined `%||%` in `manski_bounds.R`; B1 WA full-pessimism allocation + portability + JSON-load safety in `manski_bounds_conditional.R`. **Batch 2 (`pipe/coderabbit-mice`)** — B2 Rubin's-rules SE/FMI in `mice_income.R`; B4(a)/B4(b) NS-SEC field rename + per-cluster heterogeneity diagnostic in `nssec_sibling_mice.R`; B4(c) L imputed/observed divergence is a User-decision point surfaced after the per-cluster diagnostic lands (may force MICE respec). **Batch 3 (`pipe/coderabbit-ipw-port`)** — B3 zero-income tercile inclusion + B5 SMD-before/after + propensity-density overlap by cohort × analytical-status in `ipw_construction.R`; cosmetic p-value display in regression JSONs; Python-script style fixes (assert→raise, max_iter centralisation, repo-marker path walks). Each batch ends with re-run + new dated JSONs + commit on its branch; Manager merges sequentially after Task Review.
- **2026-05-14 (afternoon): Working-tree contamination identified and triaged.** Four files modified locally without commit: `manski_bounds_conditional.R`, `regression_tier1.R`, `check_pidp_crosswalk.R`, `run_w2_internal_p_audit.py`. Source confirmed by User: CodeRabbit IDE-plugin "apply suggestion" clicks against the bundle being processed. Two parse errors introduced in `manski_bounds_conditional.R` (lines 16 and 82 — newline lost between substitution and following statement). Decision: discard working-tree edits via `git checkout --` (User will execute); CodeRabbit suggestions to be re-applied properly through the three batches above with full review. Committed reproducibility at HEAD is intact; only the dirty working tree was affected.- `.apm/` git-tracking is Option B: planning artefacts tracked, runtime (`bus/`, `memory/stage-NN/`, `worktrees/`) gitignored. Pre-existing tracked bus files were untracked via `git rm --cached`.
- Multi-terminal compute is User-confirmed; expect Stage 1 to dispatch parallel TDA + Panel-Statistics work in worktrees.
- Vault access is MCP-only via `vault-engine`; never attempt direct filesystem reads of `C:\Users\steph\Documents\TDA-Research\`.
- `.apm-archive/` is reference-only historical APM v0.5.3 state; Workers must not modify or extract from it.
- UKDA T&Cs prohibit redistribution of `data/UKDA-6614-tab/`; Stage 3 standalone repos use pointers + extraction scripts only.
- Stage-boundary holistic checks: Stage 0 → 1 (verify all four pre-registrations on file); Stage 1 → 2 (verify every outcome lock has `[DECISION]` vault entry before prose dispatch); Stage 2 → 3 (T2.22 humanizer + final notation as v2-completion gate); Stage 3 (T3.3 two-machine repo verification as milestone acceptance check).
- T0.1 Done (commit `214586e`): sklearn 1.8.0 is the confirmed pin — sklearn 1.3.x has no Python 3.13 cp313 wheels. giotto-tda removed from locked environment (no cp313 wheels); TDA pipeline uses gudhi/ripser/persim directly. Any `gtda.*` imports in pipeline code will fail under the locked env.
- numpy 2.x now in use: deprecated `np.bool`, `np.int`, `np.float` aliases raise errors; T0.2 RNG audit should flag any such usage encountered. TDA Agent Tasks 0.4–0.8 should be aware.
- BLAS env loading is manual: `uv run --env-file .env python script.py`; `[tool.uv] env-file` not supported in the installed uv version.
- T0.2 Done (commit `b8ef1cb`): 1 unseeded production-path call fixed (`markov_ladder.simulate_markov_trajectories`); 2 entry-point scripts threaded (`run_pipeline.py --seed`, `bhps_tda_pipeline.py MASTER_SEED=42`). Canary reference values: H0=1138.24331880, H1=78.97751522 (L=500, n_perms=20, seed=42) — used as reference for T0.3 two-machine comparison.
- T0.3 Blocked at second-machine coordination step (commit `1991de2` on `pipe/two-machine-check`). Local canary matches T0.2 reference exactly (H0=1138.24331880, H1=78.97751522). Awaiting `canary_machine2_2026-05-07.json` placed at `results/trajectory_tda_integration/repro/` in the worktree. T0.3 only blocks T2.18 (Stage 2 prose); Stage 1 is unaffected. Resume via `/apm-4-check-tasks` once file is placed.
- T0.4/T0.5/T0.6 batch Done (commits 15fa9a3/043f0b0/4c73a1a). Key findings: (a) Markov-2 Laplace smoothing implemented (alpha=1 default, 13 tests in tests/trajectory/). (b) T0.5 root cause confirmed: sklearn 1.3.2 pkl corrupt under 1.8.0; fix already in codebase — `load_regime_labels` reads from `05_analysis.json` (27,280 labels, 7 regimes, v1 Table 2 match); input validation guards added. (c) T0.6: `detect_eps_star_knee()` extracted; median ε*=0.54 from knee_analysis.json (LOCKED: Option A, data-driven); 4 degenerate years (2003/2005/2011/2019).
- T0.7/T0.8 batch Done (commits 2bed613/4bda7ef+335dbf9, branch `pipe/w2-fixes` merged). Key findings: (a) T0.7 W₂ ground-metric audit: canonical call locked as `gudhi.wasserstein.wasserstein_distance(dgm1, dgm2, order=2, internal_p=2)`; ℓ∞ sensitivity confirmed qualitative agreement with ℓ² (H0: ℓ∞ p=0.008, ℓ² p=0.002 — both reject; H1: ℓ∞ p=0.224, ℓ² p=0.086 — both fail to reject); DECISION vault entry filed pre-run. (b) T0.8 W₂ test construction: `compute_w2_ratio_bca_ci()` added to `vectorisation.py` using `scipy.stats.bootstrap(method='BCa')`; `t_ratio`, `bca_ci_lower`, `bca_ci_upper` now recorded in per-dimension wasserstein results; 16 unit tests pass; latent `gudhi.wasserstein` import bug fixed (was silently falling to greedy approximation via bare `import gudhi`). `pot` optional-extras gap surfaced by both tasks.
- T0.9/T0.10/T0.11 batch Done (commits ea6f657/de724f6/74e147d). Key findings: (a) jbstat locked recoding: E={1,2,5,11,12,13,14,15}, U={3,9}, I={4,6,7,8,10,97}; codes 11/13/14/15 corrected from initial guesses. (b) Canonical income variable `fihhmngrs_dv`; BHPS cohort enrolls from wave b; 10,992 spanning individuals; tercile concordance 68.9% (FLAG <80%); TERCILE BOUNDARY LOCKED: Option A (within-era). (c) FOO clusters: 27,972 components, 99.94% coverage, ICC=0.899 upper bound; CSV at `data/derived/foo_clusters_2026-05-06.csv` (gitignored, on disk).
- Stage 1 parallel dispatch completed 2026-05-13. TDA Agent: T1.1–T1.3 batch on branch `run/core-tda-battery` (worktree `.apm/worktrees/run-core-tda-battery`). Panel-Statistics Agent: T1.12–T1.14 batch on branch `run/bic-ipw-mice-income` (worktree `.apm/worktrees/run-bic-ipw-mice-income`). `.env` copied to both worktrees. Stage-01 memory directory created at `.apm/memory/stage-01/`.
- `pot` optional extras gap: `pot>=0.9.0` is under `[project.optional-dependencies] wasserstein` in pyproject.toml; `uv sync` alone does not install it. Main venv fixed with `uv sync --extra wasserstein` (pot==0.9.6.post1 installed). Worktrees require `uv pip install pot` separately. Consider moving to core deps to avoid recurrence.
- T1.12/T1.13/T1.14 Done (commits 9e6fb67/6d6fd65/4d4861c, merged 2026-05-13). Key findings: (a) BIC global minimum k=14 (ΔBIC=504,751 vs k=7, very strong); k=7 is locally optimal in k=6–8 neighbourhood; paper sections on k-selection MUST include this BIC disclosure. (b) `lwtresp` does not exist in UKDA-6614 data — corrected to `{wave}_indinub_lw` (UKHLS c+) / `{wave}_indin91_lw` (BHPS bb+); wave ba has no longitudinal weight (lw_base=1). AUC=0.714, ESS=57,035. (c) MICE FMI 2–5% throughout; strong income-regime alignment: R1=72.7% H, R2=63.9% L, R6=77.0% L (external validation of GMM regimes). T1.14 deduplication fix: first non-NA row per (pidp, wave) before dcast.
- panel-statistics-agent task log protocol deviation: T1.12/T1.13/T1.14 logs not written by agent; Manager wrote them from batch report content. Task logs verified against committed result files. Resolved — no action needed from agent.
- T1.13 vault entry type error: agent filed `[PIPELINE]` but correct type is `[RESULT]` (AUC=0.714, ESS=57,035 are citable numerical results). Plan corrected to `[RESULT]`. Vault entry already filed as `[PIPELINE]` — supplementary `[RESULT]` entry filed 2026-05-13 via vault_observe.
- T1.15/T1.18/T1.19 batch reviewed 2026-05-13. T1.18 (sibling MICE NS-SEC): Done — proxy is dominant parental class: `pasoc90_cc` (father's SOC90) falling back to `masoc90_cc` (mother's SOC90) when father missing; agent correctly implemented this (76.3% → 83.3% combined → 91.5% post-propagation); no direct parental NS-SEC in UKDA-6614 confirmed via documentation search; proxy approach confirmed acceptable by Manager. T1.19 (Tier 1 regression): rerun required — outcome was applied to all 27,280 individuals (72.6% "escape" = regime prevalence) not conditional on starting in R2/R6 (5.6% conditional escape in v1). T1.15 (Manski bounds): regime share bounds correct; conditional escape rate bounds (5.6% → pessimistic lower bound) missing — supplement required. T1.19 rerun + T1.15 supplement dispatched as follow-up batch on same branch.
- T1.13 IPW extreme weight (raw max=535.89) explained by birth cohort structure: `birth_cohort_group1990+` coefficient=−6.196 → propensity≈0.002 for recent entrants who cannot satisfy the 10-year continuity criterion by construction. This conflates structural impossibility with differential attrition in the eligible population (n=113,411). p1–p99 trimming is correct per reviewer spec (trimmed max=42.78, CV 1.36→0.99). T1.29 added as structural-eligibility sensitivity (restrict eligible population to individuals enrolled early enough to have ≥10 waves available). Vault `[RESULT]` and `[DECISION]` entries filed 2026-05-13.
- T1.15-supplement/T1.19-rerun follow-up batch reviewed 2026-05-13. Root-cause confirmed (two compounding errors in Manager's prior clarification): (1) escape was defined as last-observed jbstat ∈ E — WRONG; v1 escape is window-based (first window ∈ {R2,R6} → any subsequent window ∉ {R2,R6}), implemented in `run_priority2.py::run_age_stratified()`; (2) n=4,832 regression sample was attributed to an age_at_entry<60 filter — WRONG; it is the complete-case (NS-SEC observed) subset of 7,453 first-window R2/R6 starters. v1 source-of-record confirmed: `results/trajectory_tda_priority2/p2_5_age_stratified.json` (n_starters=7,453, n_escaped=416, escape_rate=5.59%, regression n_obs=4,832, OR(R6)=20.56). Additional complication: `05_gmm.joblib` unreadable under sklearn 1.8.0 (T0.5 known) — agent must refit GMM (k=7, full covariance, n_init=5, seed=42) before window prediction. Corrected guidance dispatched 2026-05-13; task bus fully rewritten with window-based methodology and explicit reference to `run_priority2.py`.
- T1.15-supplement/T1.19-rerun (second follow-up) reviewed 2026-05-14 (commit 5c06be2, merged to main). Key outcomes: (a) T1.15-supplement DONE — Manski conditional escape bounds: full-pessimism 0.44%, partial-pessimism 1.3% overall; (b) T1.19-rerun DONE — 5 bugs fixed by agent; critical finding: GOOD_REGIMES={1,4} not just "any ∉ {R2,R6}" — v1 escape requires reaching R1 or R4 specifically (from run_priority2.py); T1.20 must use window_escape_assignments_2026-05-14.json for the escape indicator; ESC-1 ACCEPTED (irrecoverable pkl causes 10% escape_rate boundary deviation); ESC-2 ACCEPTED Option B (n_cc=6,173 vs 4,832 — T1.18 proxy has better coverage, correct v2 improvement); GMM refit pkl at 05_gmm_refit_2026-05-14.pkl. PCA artifacts (02_scaler.joblib, 02_pca.joblib) permanently lost — all downstream tasks requiring GMM prediction must use svd_solver='full' refit approach. Pipe/w2-fixes worktree cleaned up (was merged but not removed). Two new worktrees created: run-tier2-regression (T1.20) and run-sensitivity-independence (T1.16/17/23/24/25/27/29). Second panel-statistics-agent instance (instance 2) dispatched to sensitivity worktree via bus panel-statistics-agent-2.
- T1.27 and T1.25 both require PCA re-embedding: use svd_solver='full' (deterministic LAPACK) to match T1.19 rerun approach. Original PCA pkl unrecoverable — document in each task's output. T1.27 "frozen PCA loadings" means the T1.19-refit PCA (not the original), maintaining comparability within v2.
- T1.20 Done (commit 0ae5398, merged 68f0513): σ²_u=0.208, ICC=0.060, marginal McFadden R²=0.486. regime_6 OR=21.3 dominates (vs T1 Firth OR=18.6). Conditional R²=−0.176 (artefact; paper cites marginal only). All 11 key predictors direction-consistent T1→T2. T1.21 dispatched to run/tier3-regression.
- IPW individual weights gap (2026-05-14): ipw_construction.R only saves diagnostics JSON — no individual weights RDS ever written. Fix: add saveRDS block to ipw_construction.R, re-run, commit on run/sensitivity-independence. Required before T1.16 can run. Clarification added to panel-statistics-agent-2 bus.
- H0 tree-cut labels gap (2026-05-14): H0 components at eps*=0.54 not pre-computed anywhere. T1.23 derives them from embeddings.npy via sklearn radius_neighbors_graph + connected_components (or AgglomerativeClustering linkage=single). GMM labels in 05_analysis.json[gmm_labels][27280]. Clarification in agent-2 bus.
