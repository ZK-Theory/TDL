---
name: markov-null-design
version: 1.0.0
description: |
  Scaffold a correctly-specified Markov null model and permutation test for
  the trajectory TDA pipeline. Enforces the project mandate that the Markov
  order k is always explicit, generates the permutation test call with correct
  arguments, seeds all stochastic components, and produces the null battery
  structure expected by P01-B's Markov memory ladder. Use whenever designing
  or reviewing a new null hypothesis test on trajectory topology.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - AskUserQuestion
---

# Markov Null Design: Scaffold Well-Specified Null Models for Trajectory TDA

You are helping design a Markov null model for a permutation test on persistent
homology of trajectory data. The core principle of P01-B's Markov memory ladder
is: **each rung of the ladder tests whether observed topology exceeds what a
k-th order Markov process produces**. The Markov order k must always be stated
explicitly — "Markov null" alone is ambiguous and violates project convention.

## Step 1 — Clarify the test design

Ask the user:

1. **What is the research question?** (e.g., "Does the observed topology of
   employment trajectories exceed what a memoryless Markov-1 process produces?")
2. **Which ladder rung is this?** See table below.
3. **What is the Markov order k?** (1, 2, or stratified-1)
4. **What test statistic?** `total_persistence`, `max_persistence`, or `wasserstein`
5. **What data scope?** USoc era only, BHPS era only, or both?
6. **Stratified by regime?** If yes, use `stratified_markov1`; specify how regimes
   are assigned.
7. **How many permutations?** (development: 100; publication: ≥500 for Wasserstein,
   ≥200 for total persistence)
8. **Random seed?** Must be specified and recorded.

## Step 2 — Select the null type

The `permutation_test_trajectories` function in
`trajectory_tda/topology/permutation_nulls.py` accepts these `null_type` values:

| `null_type` | What it destroys | What it preserves | Markov order |
|---|---|---|---|
| `label_shuffle` | Group-to-trajectory correspondence | Embedding set | N/A |
| `cohort_shuffle` | Between-cohort assignment | Within-cohort structure | N/A |
| `order_shuffle` | Temporal transition structure | State frequencies (unigrams) | N/A (negative control) |
| `markov` | Higher-order memory beyond k | k-th order transition patterns | k=1 or k=2 |
| `stratified_markov1` | Cross-regime topology | Per-regime first-order transitions | k=1 only |

### The Markov memory ladder

| Rung | Null type | k | What a significant result means |
|---|---|---|---|
| 0 | `label_shuffle` | — | Topology is not random noise |
| 1 | `order_shuffle` | — | Transitions carry topological signal beyond state frequencies |
| 2 | `markov` | 1 | Topology exceeds first-order Markov prediction |
| 3 | `markov` | 2 | Topology exceeds second-order Markov prediction |
| 4 | `stratified_markov1` | 1 | Within-regime topology exceeds regime-specific Markov-1 |

**Always run rungs 0–2 as a minimum battery.** Rung 3 is publication-quality.
Rung 4 is used for stratified analyses only.

## Step 3 — Check existing null results

Before scaffolding new code, check whether the relevant null results already exist:
- `results/trajectory_tda_integration/` — search for JSON files with `null_type` matching
- Review `papers/P01-B-JRSSB/_project.md` open items for whether this test is pending

Read any relevant existing results file to understand the expected output shape.

## Step 4 — Generate the permutation test call

Produce a complete, runnable code block:

```python
# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: [research question stated by user]
# Null type: [null_type], Markov order k=[k], Statistic: [statistic]
# Seed: [seed] — record this in Computational-Log

import numpy as np
from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

SEED = [seed]  # Log in vault: Computational-Log YYYY-MM-DD entry
N_PERMUTATIONS = [n]  # development: 100; publication: ≥500 (Wasserstein), ≥200 (total_persistence)
N_LANDMARKS = [landmarks]  # standard: development=2000, publication=5000

results = permutation_test_trajectories(
    embeddings=embeddings,          # (N, D) numpy array
    trajectories=trajectories,      # list[list[str]] — required for order_shuffle / markov
    metadata=metadata,              # dict; include 'regime_labels' for stratified_markov1
    null_type="[null_type]",
    markov_order=[k],               # ALWAYS explicit — never omit
    statistic="[statistic]",
    n_permutations=N_PERMUTATIONS,
    n_landmarks=N_LANDMARKS,
    max_dim=1,
    n_jobs=-1,
    seed=SEED,
)

# Results structure:
# results["H0"]["p_value"]   — one-sided p-value for H₀ features
# results["H1"]["p_value"]   — one-sided p-value for H₁ features
# results["H0"]["observed"]  — observed statistic value
# results["null_type"]       — echoes null_type (verify this matches intent)
```

## Step 5 — Flag design issues

Check for and flag these common errors:

| Issue | Description | Fix |
|---|---|---|
| Unspecified Markov order | Code calls `null_type="markov"` without explicit `markov_order=` | Always pass `markov_order=k` |
| Seed not logged | Seed is set but not noted in Computational-Log plan | Add seed to vault entry |
| Wrong null for question | Using `label_shuffle` to test memory when `order_shuffle` is needed | Match null to research question |
| Publication count too low | `n_permutations < 200` for a result being reported in the paper | Increase to ≥500 |
| Missing negative control | No `order_shuffle` or `label_shuffle` in the battery | Add rung 0 or 1 as sanity check |
| Stratified without regime labels | `stratified_markov1` called without `metadata['regime_labels']` | Will raise ValueError — fix now |
| Landmarks re-coupled to observed | Landscape landmarks selected once from observed data and reused in null | Use `maxmin_landmarks` per permutation |

## Step 6 — Produce the results logging stub

```python
import json
from pathlib import Path
from datetime import date

output = {
    "metadata": {
        "experiment": "[experiment name]",
        "paper": "P01-B",
        "null_type": "[null_type]",
        "markov_order": [k],
        "statistic": "[statistic]",
        "n_permutations": N_PERMUTATIONS,
        "n_landmarks": N_LANDMARKS,
        "seed": SEED,
        "date": str(date.today()),
        "data_scope": "[USoc|BHPS|both]",
    },
    "results": results,
}

out_path = Path("results/trajectory_tda_integration/[YYYYMMDD]_null_[null_type]_k[k].json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
```

## Step 7 — Vault entry reminder

Remind the user to log using `/vault-sync` after running:
- Commit prefix: `[RESULT]` if run, `[EXPLORE]` if scaffolding only
- Record seed, n_permutations, statistic, and key p-values
- Note which rungs of the ladder have now been completed for this data scope
