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
| 1.12 | Active | panel-statistics-agent | run/bic-ipw-mice-income |
| 1.13 | Active | panel-statistics-agent | run/bic-ipw-mice-income |
| 1.14 | Active | panel-statistics-agent | run/bic-ipw-mice-income |
| 1.15 | Pending | panel-statistics-agent | |
| 1.16 | Pending | panel-statistics-agent | |
| 1.17 | Pending | panel-statistics-agent | |
| 1.18 | Pending | panel-statistics-agent | |
| 1.19 | Pending | panel-statistics-agent | |
| 1.20 | Pending | panel-statistics-agent | |
| 1.21 | Pending | panel-statistics-agent | |
| 1.22 | Pending | panel-statistics-agent | |
| 1.23 | Pending | panel-statistics-agent | |
| 1.24 | Pending | panel-statistics-agent | |
| 1.25 | Pending | panel-statistics-agent | |
| 1.26 | Pending | panel-statistics-agent | |
| 1.27 | Pending | panel-statistics-agent | |
| 1.28 | Pending | panel-statistics-agent | |

## Worker Tracking

| Agent | Instance | Notes |
|-------|----------|-------|
| reproducibility-agent | 1 | active (T0.3) |
| tda-agent | 1 | active (T1.1–T1.3 batch) — worktree run-core-tda-battery |
| panel-statistics-agent | 1 | active (T1.12–T1.14 batch) — worktree run-bic-ipw-mice-income |
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
- T0.9/T0.10/T0.11 batch Done (commits ea6f657/de724f6/74e147d). Key findings: (a) jbstat locked recoding: E={1,2,5,11,12,13,14,15}, U={3,9}, I={4,6,7,8,10,97}; codes 11/13/14/15 corrected from initial guesses. (b) Canonical income variable `fihhmngrs_dv`; BHPS cohort enrolls from wave b; 10,992 spanning individuals; tercile concordance 68.9% (FLAG <80%); TERCILE BOUNDARY LOCKED: Option A (within-era). (c) FOO clusters: 27,972 components, 99.94% coverage, ICC=0.899 upper bound; CSV at `data/derived/foo_clusters_2026-05-06.csv` (gitignored, on disk).
- Stage 1 parallel dispatch completed 2026-05-13. TDA Agent: T1.1–T1.3 batch on branch `run/core-tda-battery` (worktree `.apm/worktrees/run-core-tda-battery`). Panel-Statistics Agent: T1.12–T1.14 batch on branch `run/bic-ipw-mice-income` (worktree `.apm/worktrees/run-bic-ipw-mice-income`). `.env` copied to both worktrees. Stage-01 memory directory created at `.apm/memory/stage-01/`.
- `pot` optional extras gap: `pot>=0.9.0` is under `[project.optional-dependencies] wasserstein` in pyproject.toml; `uv sync` alone does not install it. Main venv fixed with `uv sync --extra wasserstein` (pot==0.9.6.post1 installed). Worktrees require `uv pip install pot` separately. Consider moving to core deps to avoid recurrence.
