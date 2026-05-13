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
| 1.14 | Done | panel-statistics-agent | run/bic-ipw-mice-income || 1.15 | Active (supplement) | panel-statistics-agent | run/regression-manski-nssec |
| 1.16 | Ready | panel-statistics-agent | |
| 1.17 | Ready | panel-statistics-agent | |
| 1.18 | Done (proxy confirmed) | panel-statistics-agent | run/regression-manski-nssec |
| 1.19 | Active (rerun) | panel-statistics-agent | run/regression-manski-nssec |
| 1.20 | Waiting: 1.19 | panel-statistics-agent | |
| 1.21 | Waiting: 1.20, 1.18 | panel-statistics-agent | |
| 1.22 | Waiting: 1.21 | panel-statistics-agent | |
| 1.23 | Ready | panel-statistics-agent | |
| 1.24 | Ready | panel-statistics-agent | |
| 1.25 | Ready | panel-statistics-agent | |
| 1.26 | Waiting: 1.2 | panel-statistics-agent | |
| 1.27 | Ready | panel-statistics-agent | |
| 1.28 | Waiting: 1.2 | panel-statistics-agent | |
| 1.29 | Waiting: 1.13 | panel-statistics-agent | |

## Worker Tracking

| Agent | Instance | Notes |
|-------|----------|-------|
| reproducibility-agent | 1 | active (T0.3) |
| tda-agent | 1 | active (T1.1–T1.3 batch) — worktree run-core-tda-battery |
| panel-statistics-agent | 1 | active (T1.15/T1.18/T1.19 batch) — worktree run-regression-manski-nssec |
| academic-writing-agent | 1 | uninitialized |

## Version Control

| Repository | Base Branch | Branch Convention | Commit Convention |
|-----------|-------------|-------------------|-------------------|
| `c:\Users\steph\TDL` | `main` | `pipe/<desc>` for pipeline code-side fixes; `run/<desc>` for computational Tasks; `paper/<desc>` for prose Tasks; `repo/<desc>` for repo-extraction Tasks | `[PREFIX] PXX: <description>` with PREFIX ∈ `{RESULT, DECISION, NEGATIVE, PIPELINE, DATA, EXPLORE}`; Co-Authored-By trailer; pre-commit hooks run (no `--no-verify`) |

> Note: worktree directory names are derived from branch names by replacing `/` with `-`. Branch names remain slash-form for git semantics, while the corresponding `.apm/worktrees` folder uses the hyphenated slug.

## Working Notes

- `.apm/` git-tracking is Option B: planning artefacts tracked, runtime (`bus/`, `memory/stage-NN/`, `worktrees/`) gitignored. Pre-existing tracked bus files were untracked via `git rm --cached`.
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
