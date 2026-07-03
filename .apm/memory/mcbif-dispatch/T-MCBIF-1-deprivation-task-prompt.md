# Task Prompt — T-MCBIF-1: MCbiF multiscale deprivation null battery

**Branch:** `run/mcbif-deprivation`
**Pre-registration JSON:** `results/poverty_tda_mcbif/pre_registrations_2026-07-03.json`
**Vault pre-reg:** `vault/00-Meta/Discovery/mcbif-deprivation-dispatch-prereg.md`
**Paper target (ADDITIVE outcome only):** P04 (Track A — poverty_tda extension)

---

## Objective

Run the full MCbiF bifiltration + spatial-permutation null battery on IMD 2025 English
LSOAs (33,755) at five k-means resolution levels (k∈{3,5,7,10,15}). Determine whether
MCbiF H1 rank in the observed bifiltration exceeds the 95th percentile of a B=1000
spatial-permutation null (FDR-corrected, Benjamini-Hochberg), and whether the signal
is not reproduced by ARI-across-resolutions or Moran's I at the same significance level.

Emit a date-suffixed result JSON at
`results/poverty_tda_mcbif/mcbif_deprivation_battery_<YYYY-MM-DD>.json` and a
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
- **sklearn, numpy:** confirmed available in MCbiF venv (sklearn 1.9.0)

---

## Data

- **Source:** IMD 2025 File 7 CSV
  URL: `https://assets.publishing.service.gov.uk/media/691ded56d140bbbaa59a2a7d/File_7_IoD2025_All_Ranks_Scores_Deciles_Population_Denominators.csv`
  Licence: OGL v3.0
- **Local path:** download to a gitignored path (e.g. `data/imd2025_file7.csv` or the user's
  preferred data location). Do NOT commit the CSV.
- **SHA-256:** compute and record in the result JSON before any analysis.
- **n_LSOAs:** 33,755. All LSOAs included (no regional filter in the full run).
- **Domain score columns (7):**
  - `Income Score (rate)`
  - `Employment Score (rate)`
  - `Education, Skills and Training Score`
  - `Health Deprivation and Disability Score`
  - `Crime Score`
  - `Barriers to Housing and Services Score`
  - `Living Environment Score`

---

## Pre-flight (before launching the battery)

1. Verify RIVET binary exists at `/home/nexusstephen/projects/rivet/rivet_console`.
2. Verify MCbiF venv exists at `/home/nexusstephen/projects/MCbiF/.venv/bin/python`.
3. Download the IMD 2025 CSV; compute and record its SHA-256.
4. Run a single bifiltration build (one k-value, all 33,755 LSOAs) and time it.
   If a single build exceeds 20 minutes, surface to Manager before launching B=1000.
5. Run `uv run --env-file .env python -m apm_task_prompt_check .apm/bus/<agent>/task.md`
   on the bus file before any compute.

---

## Method

```
for each draw b in 1..B:
    perm_idx = rng.permutation(n_LSOAs, seed=42+b)  # deterministic per draw
    X_perm = imd_raw[perm_idx]
    X_scaled = StandardScaler().fit_transform(X_perm)
    partitions = []
    for k in [3, 5, 7, 10, 15]:
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_scaled)
        partitions.append(labels)
    mcbif = MultiscaleClusteringBifiltration(max_dim=2)
    mcbif.load_data(partitions)
    mcbif.build_filtration(tqdm_disable=True)
    mcbif.compute_persistence(dimensions=[0,1], tqdm_disable=True)
    null_h1[b] = mcbif.betti_1_rank_.sum()

# Observed:
X_obs_scaled = StandardScaler().fit_transform(imd_raw)
partitions_obs = [KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X_obs_scaled)
                  for k in [3, 5, 7, 10, 15]]
mcbif_obs = MultiscaleClusteringBifiltration(max_dim=2)
mcbif_obs.load_data(partitions_obs)
mcbif_obs.build_filtration(tqdm_disable=True)
mcbif_obs.compute_persistence(dimensions=[0,1], tqdm_disable=True)
observed_h1 = mcbif_obs.betti_1_rank_.sum()
```

**Parallelisation:** run the B=1000 null draws with `joblib.Parallel(n_jobs=-1, backend='loky')`.
Do NOT use `threading` backend (MCbiF/RIVET spawns subprocesses; loky is correct).

**Checkpointing:** write `mcbif_deprivation_null_checkpoint_<b>.json` (or append to a
checkpoint array) every 100 draws. On resume, skip already-completed draws.

**Wall-time flag:** abort and write a partial result if wall time exceeds 8 hours.
Record `wall_time_exceeded: true` in the result JSON if triggered.

---

## Baselines

**ARI-across-resolutions:**
Compute `sklearn.metrics.adjusted_rand_score(partitions_obs[i], partitions_obs[j])` for
all 10 pairs of k-values. Record the 10 ARI values in the result JSON.

**Moran's I:**
For each of the 7 domain scores, compute Moran's I spatial autocorrelation using
`libpysal.weights` (Queen or Rook contiguity) on the LSOA adjacency. Record per-domain I
and p-value. (Use `esda.Moran` from the `esda` package, or equivalent.)

---

## Decision rule (locked — do not alter)

Evaluate after the battery completes:

```python
percentile_95 = np.percentile(null_h1, 95)  # after BH correction if multiple tests
additive = (observed_h1 > percentile_95) and not_reproduced_by_ari_and_morans_i
redundant = (observed_h1 > 0) and reproduced_by_ari
infeasible = (observed_h1 <= percentile_95)

verdict = "additive" if additive else ("redundant" if redundant else "infeasible")
```

Record `percentile_95`, `percentile_99`, `observed_h1`, `verdict` in the result JSON.

---

## Output schema (contract `mcbif-deprivation-result`)

Result JSON at `results/poverty_tda_mcbif/mcbif_deprivation_battery_<YYYY-MM-DD>.json`:

```json
{
  "schema_version": "mcbif-deprivation/v1",
  "generated_at": "<ISO timestamp>",
  "task": "T-MCBIF-1",
  "pre_registration": "results/poverty_tda_mcbif/pre_registrations_2026-07-03.json",
  "imd_sha256": "<64-char hex>",
  "null_model_construction_verified": true,
  "params": {
    "k_values": [3, 5, 7, 10, 15],
    "B": 1000,
    "seed": 42,
    "null_model": "spatial-permutation",
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
    "ari_across_resolutions": {
      "(3,5)": "<float>", "(3,7)": "<float>",
      "(3,10)": "<float>", "(3,15)": "<float>",
      "(5,7)": "<float>", "(5,10)": "<float>",
      "(5,15)": "<float>", "(7,10)": "<float>",
      "(7,15)": "<float>", "(10,15)": "<float>"
    },
    "morans_i": {
      "Income": {"I": "<float>", "p": "<float>"},
      "Employment": {"I": "<float>", "p": "<float>"},
      "Education": {"I": "<float>", "p": "<float>"},
      "Health": {"I": "<float>", "p": "<float>"},
      "Crime": {"I": "<float>", "p": "<float>"},
      "Barriers": {"I": "<float>", "p": "<float>"},
      "LivingEnv": {"I": "<float>", "p": "<float>"}
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
- Vault: `vault/00-Meta/Discovery/mcbif-deprivation-dispatch-prereg.md`
- JSON: `results/poverty_tda_mcbif/pre_registrations_2026-07-03.json`
- Registered: 2026-07-03. No amendments. First-dispatch clean design.

**Locked parameters (do not change without a pre-reg amendment):**
- k_values = [3, 5, 7, 10, 15]
- B = 1000
- seed = 42
- null_model = "spatial-permutation" (permute BEFORE clustering)
- parallel_workers ≥ 4, backend = loky
- significance threshold = 95th percentile (BH FDR-corrected)

**Machine-checkable claims:**
1. Result JSON validates against `contracts/discovery-harness/mcbif-deprivation-result.yaml` (Manager materialises from `planned_contracts` in pre-reg JSON at dispatch).
2. `null_model_construction_verified = true` in result JSON (Worker asserts this; binding test in `tests/discovery/test_mcbif_deprivation_contract.py`).
3. `imd_sha256` matches SHA-256 recomputed from the actual file (binding test).
4. `verdict` in `{additive, redundant, infeasible}` (binding test).
5. `params.seed == 42` and `params.B >= 1000` (binding test).

**Human-review-only claims:**
- Interpretation of ARI vs H1 comparison (does H1 add information beyond ARI?).
- Moran's I vs H1 spatial-autocorrelation comparison.
- Prose-direction choice if outcome is PARTIAL (ambiguous signal).

**Partial criteria:** if `null_h1` distribution is bimodal or has long tails that make
the 95th percentile ambiguous, record this in the result JSON and surface to Manager
before emitting a verdict.

**Vault obligation:** write a `[RESULT]` entry to `04-Methods/Computational-Log.md`
(top-of-page, reverse-chronological) after the battery completes, recording the verdict,
key numbers, and the result JSON path.

**Validation commands:**
```bash
uv run --env-file .env python -m pytest tests/discovery/test_mcbif_deprivation_contract.py -v
uv run --env-file .env python tools/apm_task_prompt_check.py .apm/bus/<agent>/task.md
```

---

## Commit message prefix

`[RESULT] T-MCBIF-1: MCbiF deprivation battery — <verdict> (H1=<n>, p<95th=<x>)`
