# /markov-null-design — Scaffold a Markov Null Model

Design and scaffold a correctly-specified Markov null model for the trajectory TDA
permutation test pipeline. Enforces the P01-B mandate that Markov order k is always
explicit. Generates the full `permutation_test_trajectories` call, result logging stub,
and Computational-Log reminder.

## Usage

```
/markov-null-design
/markov-null-design [null_type] [k]
```

Example: `/markov-null-design markov 2` (Markov-2 null scaffold)
Example: `/markov-null-design` (interactive — asks all questions)

---

## The Markov memory ladder (P01-B)

| Rung | `null_type` | Markov order k | Significant result means |
|---|---|---|---|
| 0 | `label_shuffle` | — | Topology is not noise |
| 1 | `order_shuffle` | — | Transitions carry signal beyond state frequencies |
| 2 | `markov` | **1** | Topology exceeds first-order Markov prediction |
| 3 | `markov` | **2** | Topology exceeds second-order Markov prediction |
| 4 | `stratified_markov1` | 1 | Within-regime topology exceeds regime Markov-1 |

**Minimum battery: rungs 0–2. Publication quality: rungs 0–3.**

---

## Function signature (trajectory_tda/topology/permutation_nulls.py)

```python
results = permutation_test_trajectories(
    embeddings=embeddings,       # (N, D) array
    trajectories=trajectories,   # list[list[str]] — required for markov/order_shuffle
    metadata=metadata,           # dict; needs 'regime_labels' for stratified_markov1
    null_type="markov",
    markov_order=1,              # ALWAYS explicit — never omit
    statistic="total_persistence",  # or "max_persistence" or "wasserstein"
    n_permutations=200,          # development: 100; publication: ≥200 (≥500 for wasserstein)
    n_landmarks=2000,            # development: 2000; publication: 5000
    max_dim=1,
    n_jobs=-1,
    seed=42,                     # record in Computational-Log
)
```

Null types that require `trajectories`: `order_shuffle`, `markov`, `stratified_markov1`
`stratified_markov1` requires `metadata['regime_labels']`; raises `ValueError` otherwise.

---

## Common design errors to flag

| Error | Fix |
|---|---|
| `null_type="markov"` without `markov_order=` | Always pass `markov_order=k` explicitly |
| `n_permutations < 200` for a published result | Increase to ≥500 (Wasserstein) or ≥200 |
| Seed not planned for Computational-Log | Always note seed before running |
| No `label_shuffle` or `order_shuffle` in battery | Add as negative-control rungs |
| Landmarks selected once from observed data | Re-select per permutation (maxmin_landmarks) |

---

## Results file naming convention

```
results/trajectory_tda_integration/YYYYMMDD_null_[null_type]_k[k].json
```

---

## After running

Use `/vault-sync` to log to Computational-Log:
- Commit prefix: `[RESULT]`
- Record: `null_type`, `markov_order`, `seed`, `n_permutations`, `statistic`, p-values per dim
- Note which ladder rungs are now complete for each data scope (USoc / BHPS)
