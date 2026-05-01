# Stratified Markov-1 Null — Bug Diagnosis and Fix

**Date:** 2026-05-01  
**Relates to:** Reviewer response plan §2 (ISSUE H2)  
**Status:** Fix implemented; corrected runs not yet executed.

---

## The Broken Result

`results/trajectory_tda_integration/stratified_markov/stratified_markov1_results.json`  
shows `regime_distribution: {0: 27252, 3: 28}` — only 2 of the 7 expected regimes were
active. Regime 3 (n=28 < min_regime_n=30) fell back to the global transition matrix, so
the "stratified" run was functionally identical to global Markov-1.

## Root Cause

Three compounding failures in the deleted `_run_stratified_markov.py` temp script:

### 1. Wrong data source for regime labels

The temp script attempted to load `05_gmm.joblib` or refit a GMM to obtain regime
assignments. `05_gmm.joblib` does not exist in the checkpoint directory. The correct
authoritative source is `05_analysis.json["gmm_labels"]`, which stores the 27,280
per-trajectory integer labels produced by the original pipeline.

### 2. sklearn version mismatch

The handoff doc notes "models saved with 1.8.0, loaded with 1.3.2 — warnings but loads
OK." *Loads without crashing* is not the same as *predicts correctly*. The cross-version
load produced predictions that collapsed all trajectories to regime 0, with 28 outliers
in regime 3 — exactly consistent with a GMM whose parameters were silently garbled.

### 3. `run_wasserstein_battery.py` had no `regime_labels` support

The standard battery script never populated `metadata["regime_labels"]`. Any attempt to
run `stratified_markov1` through it would have raised a `ValueError` at
`permutation_nulls.py:502`. The temp script was the only path, and it was broken.

## Correct Regime Label Distribution

From `results/trajectory_tda_integration/05_analysis.json["gmm_labels"]`:

| Regime | n_members |
|--------|-----------|
| R0     | 3,787     |
| R1     | 7,358     |
| R2     | 5,415     |
| R3     | 3,333     |
| R4     | 3,510     |
| R5     | 1,813     |
| R6     | 2,064     |
| **Total** | **27,280** |

All 7 regimes are above `min_regime_n=30`. Matches Table 2 of v1 draft exactly.

BHPS counterpart (`results/trajectory_tda_bhps/05_analysis.json`): k=8 regimes,
n=8,509 trajectories, all regimes above min_regime_n=30.

## Fix Applied

`trajectory_tda/scripts/run_wasserstein_battery.py` extended with:

- `load_regime_labels(analysis_json_path)` — reads `gmm_labels` from any pipeline
  analysis JSON; avoids any model pickle loading.
- `run_battery(..., regime_labels_path=...)` — passes labels into
  `metadata["regime_labels"]` when `stratified_markov1` is in `null_types`.
- `--regime-labels-path` CLI argument.

## Reproducibility: Commands to Run the Corrected Analysis

### USoc — stratified Markov-1 at L=5000, n=100 perms

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_integration `
    --null-types stratified_markov1 `
    --n-perms 100 --landmarks 5000 `
    --regime-labels-path results/trajectory_tda_integration/05_analysis.json `
    --output-name stratified_markov/stratified_markov1_W2_L5000_20260501.json `
    --seed 42
```

Estimated wall-clock: 5–8 h. Preserve the broken legacy file — do not overwrite it.

### BHPS — stratified Markov-1 at L=5000, n=100 perms

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_bhps `
    --null-types stratified_markov1 `
    --n-perms 100 --landmarks 5000 `
    --regime-labels-path results/trajectory_tda_bhps/05_analysis.json `
    --output-name stratified_markov/stratified_markov1_W2_L5000_20260501.json `
    --seed 42
```

Estimated wall-clock: 2–3 h.

## Pre-Registration of Analysis Design (per plan §2.4 step 6)

Committed to this design before running:
- L = 5,000 (matched to ISSUE H1 matched-L run)
- n_perms = 100, n_nullnull = 500 pairs (standard battery n)
- Both H₀ and H₁ reported
- Decision rule: p < 0.05 → reject (Outcome A); p ≥ 0.20 → fail to reject (Outcome B);
  0.05–0.20 → borderline (Outcome C)
- Regime distribution verified against Table 2 before interpreting results
