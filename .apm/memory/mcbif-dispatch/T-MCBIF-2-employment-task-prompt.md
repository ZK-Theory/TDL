# Task Prompt — T-MCBIF-2: MCbiF wave-indexed employment-state null battery

**Branch:** `run/mcbif-employment`
**Pre-registration JSON:** `results/trajectory_tda_mcbif/pre_registrations_2026-07-03.json`
**Vault pre-reg:** `vault/00-Meta/Discovery/mcbif-employment-clustering-dispatch-prereg.md`
**Paper target (ADDITIVE outcome only):** P01-B (Track C — trajectory_tda extension)

---

## Objective

Run the full MCbiF bifiltration + wave-label-permutation null battery on the frozen
27,280-trajectory PCA-20 BHPS/USoc embedding, using categorical employment-state
partitions (9 states: EH/EL/EM/IH/IL/IM/UH/UL/UM) at each wave position. Determine
whether MCbiF H1 rank in the observed bifiltration exceeds the 95th percentile of a
B=1000 wave-label-permutation null (FDR-corrected, Benjamini-Hochberg), and whether the
signal is not reproduced by ARI-across-waves or conditional entropy at the same
significance level.

Emit a date-suffixed result JSON at
`results/trajectory_tda_mcbif/mcbif_employment_battery_<YYYY-MM-DD>.json` and a
`[RESULT]` vault entry. No paper prose until the ADDITIVE decision is in.

---

## Environment

MCbiF and RIVET run under WSL only. All compute scripts are staged to WSL and invoked
via `wsl <script_path>`. Confirmed working environment (Gate 0, 2026-07-03):

- **RIVET binary:** `/home/nexusstephen/projects/rivet/rivet_console`
- **MCbiF venv:** `/home/nexusstephen/projects/MCbiF/.venv/bin/python`
- **pyrivet monkey-patch (mandatory before any mcbif import):**
  `import pyrivet.rivet as _rivet_mod; _rivet_mod.rivet_executable = "/home/nexusstephen/projects/rivet/rivet_console"`
- **Python flags:** use `python -u` (unbuffered) so background-task output is visible mid-run
- **numpy, json:** confirmed available in MCbiF venv

---

## Data (frozen — no re-embedding permitted)

| File | Path | Role |
|------|------|------|
| PCA-20 embedding | `results/trajectory_tda_integration/embeddings.npy` | 27,280 × 20 array; frozen |
| State sequences | `results/trajectory_tda_integration/01_trajectories_sequences.json` | list of 27,280 state-sequence lists |

**Provenance gate (pre-flight step 1):** compute SHA-256 of both files and record in the
result JSON before any analysis. These files are frozen at the P01 PCA-20 checkpoint.
If either file is absent, STOP and escalate — do not regenerate.

**Note:** the PCA-20 embedding is NOT used as input to MCbiF. The categorical state
sequence at each wave IS the partition. The embedding file is verified for provenance only.

---

## Pre-flight (before launching the battery)

1. Verify RIVET binary exists at `/home/nexusstephen/projects/rivet/rivet_console`.
2. Verify MCbiF venv exists at `/home/nexusstephen/projects/MCbiF/.venv/bin/python`.
3. Compute SHA-256 of `embeddings.npy` and `01_trajectories_sequences.json`.
4. Determine the valid wave positions: count, for each wave index w, how many trajectories
   have `len(seq) > w`. Record `n_valid[w]` for all w. Use only wave positions where
   `n_valid[w] >= n_trajectories / 2` (at least 50% coverage).
5. **Cost estimate (mandatory):** time one full bifiltration build (all 27,280 trajectories,
   all valid wave positions). If a single build takes > 5 minutes, the B=1000 battery at
   ≥4 workers may exceed the 8-hour wall time. Surface the timing to Manager before launch.
   Include an alternative down-scope if needed: BHPS-only (waves 1-18, ~18,000 trajectories)
   or a random sample of 5,000 trajectories with all waves. **Do not launch the full battery
   without a timing estimate.**
6. Run `uv run --env-file .env python tools/apm_task_prompt_check.py .apm/bus/<agent>/task.md`.

---

## Method

```python
import json, numpy as np
from pathlib import Path

import pyrivet.rivet as _rivet_mod
_rivet_mod.rivet_executable = "/home/nexusstephen/projects/rivet/rivet_console"
from mcbif import MultiscaleClusteringBifiltration

sequences = json.loads(Path(SEQUENCES_PATH).read_text())
STATE_MAP = {s: i for i, s in enumerate(sorted(
    {s for seq in sequences for s in seq}))}

# Determine valid wave positions (>= 50% coverage)
n = len(sequences)
valid_waves = [w for w in range(max_wave)
               if sum(1 for s in sequences if len(s) > w) >= n // 2]

# Build observed partition sequence
partitions_obs = [
    np.array([STATE_MAP[seq[w]] for seq in sequences if len(seq) > w])
    for w in valid_waves
]
# NOTE: MCbiF requires all partitions to cover the same point set.
# Filter to trajectories present in ALL valid wave positions.
eligible = [i for i, seq in enumerate(sequences) if len(seq) > max(valid_waves)]
partitions_obs = [
    np.array([STATE_MAP[sequences[i][w]] for i in eligible])
    for w in valid_waves
]

mcbif_obs = MultiscaleClusteringBifiltration(max_dim=2)
mcbif_obs.load_data(partitions_obs)
mcbif_obs.build_filtration(tqdm_disable=True)
mcbif_obs.compute_persistence(dimensions=[0, 1], tqdm_disable=True)
observed_h1 = int(mcbif_obs.betti_1_rank_.sum())

# Null: wave-label permutation
def one_null_draw(b, valid_waves, eligible, sequences, STATE_MAP, seed):
    rng = np.random.default_rng(seed + b)
    perm_waves = rng.permutation(valid_waves).tolist()
    parts = [np.array([STATE_MAP[sequences[i][w]] for i in eligible])
             for w in perm_waves]
    m = MultiscaleClusteringBifiltration(max_dim=2)
    m.load_data(parts)
    m.build_filtration(tqdm_disable=True)
    m.compute_persistence(dimensions=[0, 1], tqdm_disable=True)
    return int(m.betti_1_rank_.sum())

# Parallel: joblib.Parallel(n_jobs=-1, backend='loky')
# Checkpoint every 100 draws; wall-time flag at 8h
```

---

## Baselines

**ARI-across-waves:**
For every pair of adjacent and non-adjacent wave positions (i, j), compute
`adjusted_rand_score(partitions_obs[i], partitions_obs[j])`. Record mean and max ARI.

**Conditional entropy:**
For each consecutive wave pair (w, w+1), compute conditional entropy
H(state_at_{w+1} | state_at_w). Record per-pair values and mean.

**Consensus clustering matrix:**
Compute the n_eligible × n_eligible co-assignment matrix (mean over wave positions of
indicator[same_cluster(i,j)]). Record the mean and variance of off-diagonal entries.

---

## Decision rule (locked — do not alter)

```python
percentile_95 = np.percentile(null_h1, 95)  # after BH correction if multiple contrasts
additive = (observed_h1 > percentile_95) and not_reproduced_by_ari_and_entropy
redundant = (observed_h1 > 0) and reproduced_by_ari
infeasible = (observed_h1 <= percentile_95)

verdict = "additive" if additive else ("redundant" if redundant else "infeasible")
```

---

## Output schema (contract `mcbif-employment-result`)

Result JSON at `results/trajectory_tda_mcbif/mcbif_employment_battery_<YYYY-MM-DD>.json`:

```json
{
  "schema_version": "mcbif-employment/v1",
  "generated_at": "<ISO timestamp>",
  "task": "T-MCBIF-2",
  "pre_registration": "results/trajectory_tda_mcbif/pre_registrations_2026-07-03.json",
  "embeddings_sha256": "<64-char hex>",
  "sequences_sha256": "<64-char hex>",
  "null_model_construction_verified": true,
  "params": {
    "n_trajectories_eligible": "<int>",
    "n_wave_positions": "<int>",
    "valid_waves": ["<list of int>"],
    "B": 1000,
    "seed": 42,
    "null_model": "wave-label-permutation",
    "partition_method": "categorical",
    "parallel_workers": "<int>",
    "wall_time_hours_budget": 8
  },
  "observed": {
    "h1_rank": "<int>",
    "h0_rank": "<int>"
  },
  "null_distribution": {
    "draws": 1000,
    "percentile_95": "<float>",
    "percentile_99": "<float>",
    "mean": "<float>",
    "std": "<float>"
  },
  "baselines": {
    "ari_across_waves": {
      "mean": "<float>",
      "max": "<float>",
      "per_pair": {}
    },
    "conditional_entropy": {
      "mean": "<float>",
      "per_pair": {}
    },
    "consensus_clustering": {
      "mean_coassignment": "<float>",
      "var_coassignment": "<float>"
    }
  },
  "decision": {
    "verdict": "<additive|redundant|infeasible>",
    "rationale": "<one sentence>"
  }
}
```

---

## Research Assurance Requirements

**Lanes touched:** Topology · Stochastic / Null Model · Representation · Paper Claim

**Governing pre-registration:**
- Vault: `vault/00-Meta/Discovery/mcbif-employment-clustering-dispatch-prereg.md`
- JSON: `results/trajectory_tda_mcbif/pre_registrations_2026-07-03.json`
- Registered: 2026-07-03. No amendments. First-dispatch clean design.

**Locked parameters (do not change without a pre-reg amendment):**
- partition_method = categorical (employment state label; NOT k-means)
- B = 1000
- seed = 42
- null_model = "wave-label-permutation" (permute wave ordering BEFORE bifiltration construction)
- parallel_workers ≥ 4, backend = loky (NOT threading — gudhi GIL constraint)
- significance threshold = 95th percentile (BH FDR-corrected)
- frozen embedding: no re-embedding permitted

**Machine-checkable claims:**
1. Result JSON validates against `contracts/discovery-harness/mcbif-employment-result.yaml`
   (Manager materialises at dispatch from `planned_contracts` in pre-reg JSON).
2. `null_model_construction_verified = true` (Worker asserts; binding test in
   `tests/discovery/test_mcbif_employment_contract.py`).
3. `embeddings_sha256` and `sequences_sha256` match on-disk SHA-256 (binding test).
4. `verdict` in `{additive, redundant, infeasible}` (binding test).
5. `partition_method == "categorical"` and `params.seed == 42` and `params.B >= 1000`
   (binding test). `refit_pca` absent (binding test).

**Human-review-only claims:**
- Interpretation of ARI vs H1 comparison.
- Conditional entropy vs H1 comparison.
- Decision if cost pre-flight requires scope reduction (Manager call, not Worker).

**Partial criteria:** if the single-bifiltration build exceeds 5 minutes at full scale
(27,280 trajectories × all valid waves), surface to Manager with timing data before
launching B=1000. The Manager decides scope (full / BHPS-only / 5k-sample).

**Vault obligation:** write a `[RESULT]` entry to `04-Methods/Computational-Log.md`
(top-of-page, reverse-chronological) after battery completes.

**Validation commands:**
```bash
uv run --env-file .env python -m pytest tests/discovery/test_mcbif_employment_contract.py -v
uv run --env-file .env python tools/apm_task_prompt_check.py .apm/bus/<agent>/task.md
```

---

## Commit message prefix

`[RESULT] T-MCBIF-2: MCbiF employment battery — <verdict> (H1=<n>, p<95th=<x>)`
