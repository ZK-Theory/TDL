# Employment Status × Income Band: State-Space TDA Pipeline

Build a reusable TDA pipeline: 9-state life-course trajectories → n-gram embedding → persistent homology → regime/cycle/group discovery.

## Decisions Locked

| Decision | Choice |
|----------|--------|
| Data format | TAB-delimited UKDS, `data/SN5151` (BHPS) + `data/SN6614` (USoc) |
| Package | `trajectory_tda/` (top-level, parallel to `poverty_tda/`) |
| Null models | All 4: label shuffle, cohort-conditional, order-preserving, Markov |
| Subsampling | Hybrid witness (primary) + maxmin VR (fallback), multi-subsample validation |
| Embedding | N-gram (default) with TF-IDF + UMAP options |
| Parallelisation | `joblib.Parallel` for permutation nulls |

---

## Project Structure

```
trajectory_tda/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── employment_status.py    # E/U/I from BHPS+USoc jbstat
│   ├── income_band.py          # L/M/H vs HBAI medians (BHC)
│   └── trajectory_builder.py   # Merge, filter ≥10yr, attach covariates
├── embedding/
│   ├── __init__.py
│   └── ngram_embed.py          # Unigram(9D)+bigram(81D), TF-IDF, PCA/UMAP
├── topology/
│   ├── __init__.py
│   ├── trajectory_ph.py        # Witness (primary) + maxmin VR (fallback)
│   ├── permutation_nulls.py    # 4 nulls, joblib-parallelised
│   └── vectorisation.py        # Betti curves, landscapes, persistence images
├── analysis/
│   ├── __init__.py
│   ├── regime_discovery.py     # H₀ components + GMM + characterisation
│   ├── cycle_detection.py      # H₁ loops + representative trajectories
│   └── group_comparison.py     # Wasserstein + landscape stats by group
└── scripts/
    └── run_pipeline.py         # CLI orchestrator with checkpointing
```

---

## Component 1: Data Layer

### [NEW] [employment_status.py](file:///c:/Projects/TDL/trajectory_tda/data/employment_status.py)

Per-person-year employment status from BHPS + USoc TAB files.

- **BHPS** (`data/SN5151`): `jbstat` (waves a–r)
  - **E**: codes 1 (self-emp), 2 (employed), 10 (govt training)
  - **U**: code 3 (unemployed)
  - **I**: codes 4–9, 97 (retired, maternity, family care, student, sick, other)
- **USoc** (`data/SN6614`): Harmonised `jbstat` (waves a–n) — same coding

> [!NOTE]
> BHPS/USoc `jbstat` codes are harmonised in SN6614 user guide. Pre-harmonised BHPS waves (a–p) verified for alignment. If multiple spells/year, use modal status; attach `fflag='mixed'` when >1 distinct status in the reference year.

Returns `pd.DataFrame[pidp, year, emp_status, fflag]`

### [NEW] [income_band.py](file:///c:/Projects/TDL/trajectory_tda/data/income_band.py)

Per-household-year income band (HBAI standard, BHC equivalised):

- `fihhmnnet1_dv` (USoc), `fihhmn` (BHPS) — monthly net HH income
- Medians computed on **full sample per wave** (not panel-only, avoids selection bias)
- Negative incomes → clipped to zero
- **L** < 60% median | **M** 60–100% | **H** > 100%
- Configurable `threshold=0.6` for sensitivity analysis (e.g., 0.5 for severe poverty)

Returns `pd.DataFrame[pidp, year, income_band]`

### [NEW] [trajectory_builder.py](file:///c:/Projects/TDL/trajectory_tda/data/trajectory_builder.py)

- Join on `(pidp, year)` → 9 states `{EL, EM, EH, UL, UM, UH, IL, IM, IH}`
- Filter: ≥10 consecutive years; ≤2-year gaps (NN interpolation, log % imputed)
- Covariates: birth cohort (decade), gender, parental NS-SEC, region

Returns `(trajectories: list[list[str]], metadata: pd.DataFrame)`

---

## Component 2: Embedding

### [NEW] [ngram_embed.py](file:///c:/Projects/TDL/trajectory_tda/embedding/ngram_embed.py)

```python
STATES = ['EL', 'EM', 'EH', 'UL', 'UM', 'UH', 'IL', 'IM', 'IH']

def ngram_embed(
    trajectories: list[list[str]],
    include_bigrams: bool = True,
    tfidf: bool = False,        # TF-IDF weighting for rare transitions
    pca_dim: int | None = 20,   # PCA reduction (None = raw 90D)
    umap_dim: int | None = None, # Alternative: UMAP (better local H₁)
) -> tuple[np.ndarray, dict]:
    """Returns (N, K) point cloud + state_to_idx dict for null reproducibility."""
```

- Unigrams (9D) + bigrams (81D) = 90D raw
- TF-IDF optional: downweights dominant states, upweights rare transitions (UH→IL)
- PCA default 20D; UMAP alternative for local structure preservation

---

## Component 3: PH Pipeline

### [NEW] [trajectory_ph.py](file:///c:/Projects/TDL/trajectory_tda/topology/trajectory_ph.py)

Dual-method PH with adaptive landmarks:

```python
def compute_trajectory_ph(
    embeddings: np.ndarray,
    max_dim: int = 1,
    n_landmarks: int | None = None,  # Default: min(5000, N//4)
    method: Literal['witness', 'maxmin_vr', 'both'] = 'both',
) -> dict[str, PHResult]:
```

- **Primary: Witness** (gudhi `strong_witness_persistence`) — better H₁ (local cycles)
- **Fallback: Maxmin VR** (ripser on landmarks) — robust H₀ (global components)
- **Validation**: 20 random maxmin subsamples (2k each) → averaged Betti curves
- Adaptive: `n_landmarks = min(5000, N // 4)`

### [NEW] [permutation_nulls.py](file:///c:/Projects/TDL/trajectory_tda/topology/permutation_nulls.py)

| Null | Preserves | Destroys | Tests |
|------|-----------|----------|-------|
| `label_shuffle` | Embedding marginals | Group assignment | Group labels carry topo info |
| `cohort_shuffle` | Within-cohort structure | Between-cohort | Cohort differences significant |
| `order_shuffle` | Unigram frequencies | Temporal order | Bigrams carry topo signal |
| `markov` | 1st-order transitions | Higher-order | Topology > memoryless |

- `markov_order` param: default 1, testable at 2 for cycle detection
- `joblib.Parallel(n_jobs=-1)` for 1000 permutations
- Same subsampling applied to permuted data

### [NEW] [vectorisation.py](file:///c:/Projects/TDL/trajectory_tda/topology/vectorisation.py)

- Betti curves (reuse `betti_curve` from `multidim_ph.py`)
- Persistence landscapes (L₁…L_k)
- **Persistence images** (scalable ML input, resolution-parameterised)
- Wasserstein distance between diagrams

---

## Component 4: Analysis

### [NEW] [regime_discovery.py](file:///c:/Projects/TDL/trajectory_tda/analysis/regime_discovery.py)

H₀ + H₁ hybrid: persistent components → regimes, labelled by avg state composition (% EL, % UH, etc.) + GMM comparison (BIC-selected K, ARI).

### [NEW] [cycle_detection.py](file:///c:/Projects/TDL/trajectory_tda/analysis/cycle_detection.py)

H₁ loops → poverty/unemployment traps. Extract via `persistence_pairs`; identify representative trajectories near generators; test significance vs order_shuffle + Markov nulls.

### [NEW] [group_comparison.py](file:///c:/Projects/TDL/trajectory_tda/analysis/group_comparison.py)

Per-stratum PH (parental class / gender / cohort) → Wasserstein distances + persistence landscape statistics + permutation p-values.

---

## Component 5: Integration

### [MODIFY] [pyproject.toml](file:///c:/Projects/TDL/pyproject.toml)

Add `trajectory_tda*` to packages, `ripser>=0.6.0` to deps, coverage + isort config.

### [NEW] [run_pipeline.py](file:///c:/Projects/TDL/trajectory_tda/scripts/run_pipeline.py)

```bash
python -m trajectory_tda.scripts.run_pipeline \
  --data-dir data --min-years 10 --n-perms 1000 \
  --landmarks 5000 --embed pca20 --nulls all --checkpoint results/
```

- CLI flags for all configurable params
- Checkpointing: save embeddings, PH results, null distributions (restartable)
- Compute estimate: N=15k → 5k landmarks → ~2min PH + ~30min nulls (16 cores)

---

## Verification Plan

### Automated Tests (`tests/trajectory/`)

All tests use synthetic data with **known structure**:

```python
# Synthetic generators for testing
def make_synthetic_trajectories(n, T, n_states=9)   # Random baseline
def make_clustered_trajectories(n, k=3)              # Known regimes
def make_cyclic_trajectories(n, cycle=['EL','UL','IL','IM','EM','EL'])  # Known H₁
def make_churn_regimes(n, T)                         # AR(1) Markov + churn
```

```bash
python -m pytest tests/trajectory/ -v --cov=trajectory_tda
ruff check trajectory_tda/ tests/trajectory/
```

### Integration Test (requires UKDS data)
```bash
python -m trajectory_tda.scripts.run_pipeline --data-dir data --min-years 10 --n-perms 100
```

---

## Future Scaling

| Extension | Change required |
|-----------|----------------|
| Family dim (→ 27 states) | Expand `STATES` vocab, retrain embed |
| Autoencoder embed | New `embedding/vae_embed.py` (32D latent) |
| Multi-param PH | New `topology/mp_ph.py` (time × hardship bifiltration) |
| Time use dim | Append paid-work hours band |
