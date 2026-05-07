# Stratified-Markov Regime-Label Collapse: Diagnosis and Fix

**Date:** 2026-05-07  
**Branch:** `pipe/tda-code-fixes`  
**Related file:** `trajectory_tda/topology/permutation_nulls.py`

---

## Symptom

The legacy stratified-Markov-1 null run collapsed to 2 effective regimes instead of the expected 7 (USoc era). Surrogate trajectories were not stratified by regime, making the null invalid for the P01-A §4.3 test.

## Root Cause

The original pipeline called `gmm_object.predict(embeddings)` by loading the fitted GMM from `05_gmm.joblib`. Two failure modes existed:

1. **sklearn version mismatch (confirmed as primary cause):** The GMM was fit under sklearn 1.3.2 and the pkl was reloaded under sklearn 1.8.0. Changes to sklearn's internal state schema caused `predict()` to return degenerate labels (effectively 2 distinct values instead of 7), silently corrupting the regime assignments.

2. **Field provenance error (latent, now guarded):** Code that passed `k_optimal` (integer 7) instead of the `gmm_labels` array to `metadata["regime_labels"]` would produce `_stratified_markov_shuffle` receiving a scalar, which `np.unique(7)` would reduce to a single-element array — collapsing to 1 effective regime.

## Fix Applied

### 1. `load_regime_labels` in `run_wasserstein_battery.py`

The authoritative regime labels are now loaded from `05_analysis.json` (key: `gmm_labels`) rather than by calling `gmm.predict()` on the loaded pkl. This completely bypasses the sklearn version-mismatch risk and is stable across Python/sklearn upgrades.

```python
def load_regime_labels(analysis_json_path: Path) -> np.ndarray:
    with open(analysis_json_path) as f:
        analysis = json.load(f)
    labels = analysis.get("gmm_labels")
    arr = np.array(labels, dtype=int)  # shape (N,), ints 0..k-1
    return arr
```

**Data verified:** `05_analysis.json` contains 27,280 regime labels with 7 unique values (0–6); counts match v1 P01-A Table 2:

| Regime | N      |
|--------|--------|
| R0     | 3,787  |
| R1     | 7,358  |
| R2     | 5,415  |
| R3     | 3,333  |
| R4     | 3,510  |
| R5     | 1,813  |
| R6     | 2,064  |

### 2. Input validation in `_stratified_markov_shuffle`

Added explicit guards to catch both collapse modes at the function boundary:

```python
regime_labels = np.asarray(regime_labels)
if regime_labels.ndim != 1:
    raise ValueError(
        f"regime_labels must be a 1-D array of per-trajectory integers, "
        f"got shape {regime_labels.shape}. "
        "Pass gmm_labels from 05_analysis.json, not the cluster count k."
    )
if len(regime_labels) != len(trajectories):
    raise ValueError(
        f"regime_labels length ({len(regime_labels)}) does not match "
        f"trajectories length ({len(trajectories)}). ..."
    )
```

## Verification

- **Unit tests:** 8 tests in `tests/trajectory/test_stratified_markov_labels.py` — all pass. Cover: scalar input raises, 2D input raises, misaligned length raises, 7-regime coverage, small-regime fallback, list coercion.
- **Real-data sanity check:** `_stratified_markov_shuffle` on 500-trajectory sample from `results/trajectory_tda_integration/` — all 7 regimes present in sample, surrogate shape (500, 20), no NaN.
- **Regime counts:** Match v1 Table 2 exactly (see table above).

## GMM Refit Status

No refit required. `05_analysis.json` already contains the authoritative `gmm_labels` array from the original pipeline run (fit under sklearn 1.3.2, saved as JSON before version mismatch affected the pkl). The JSON-based `load_regime_labels` function correctly reads these labels without pkl deserialization.

## Correct Usage

```bash
# Run stratified Markov-1 null via run_wasserstein_battery.py
uv run --env-file .env python -m trajectory_tda.scripts.run_wasserstein_battery \
    --checkpoint-dir results/trajectory_tda_integration \
    --null-types stratified_markov1 \
    --regime-labels-path results/trajectory_tda_integration/05_analysis.json \
    --n-perms 100 --landmarks 5000
```
