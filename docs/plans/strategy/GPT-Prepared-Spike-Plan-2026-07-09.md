Below is a coding-agent-ready spike plan for all seven candidates. It is deliberately prescriptive: the agent should not choose alternative nulls, statistics, thresholds, or data reductions unless the run is explicitly blocked and the result is recorded as `BLOCKED`.

The key design correction is that MCbiF should be treated as a sequence-of-partitions method. Its Hilbert functions HF0 and HF1 measure non-hierarchy and higher-order cluster inconsistency across the triangular `(s,t)` grid; the paper also gives an equivalent nerve-based construction that is computationally advantageous when the number of scales is smaller than large cluster sizes. This directly addresses the current MCbiF employment memory failure.  The existing employment battery was stopped before the B=1000 null because even the 5,000-trajectory alternative exceeded the available WSL memory envelope before persistence computation was reached. 

# TDL AMENDMENTS (2026-07-10 session review) — NORMATIVE, OVERRIDE THE TEXT BELOW

These amendments were produced by a repo-side evidence review on 2026-07-09/10 and
take precedence over any conflicting statement in the original (GPT-prepared) text
below. The executing agent reads this section first.

## A1. C1 persistent-Laplacian status correction (affects Spike 5)

The original text describes C1 as "the already successful C1 persistent-Laplacian
route". That is stale. The full C1 Markov-1 null battery ran on 2026-07-07
(commit `2226f85c028ed10fddd68e6f5e33426ea818f1fd`,
`results/trajectory_tda_bhps/c1_pl_fiedler_null_2026-07-07.json`) and returned
**NEGATIVE**: IFA p = 0.241, 0/35 pointwise thresholds survive BH-FDR. C1 is
KILL/PARKed per its pre-registration.

Post-review diagnosis (to be verified empirically in Spike 5′): the test was
near-powerless **by construction**. The IFA statistic is a deterministic function
of the 9×9 transition-count matrix, and the Markov-1 null simulates from the
first-order model whose MLE *is* that count matrix — so E[null counts] ≈ observed
counts and the observed statistic sits near the centre of its own null (it landed
at the 76th percentile). A statistic computed on the order-k sufficient statistic
cannot reject a Markov-k parametric-bootstrap null.

## A2. Spike 5 is REPLACED by Spike 5′ (C1 post-mortem + Markov-0 redesigned probe)

Do NOT run Spike 5 as written below: its per-subgroup IFA-vs-Markov-1 design
inherits the centering defect five times over, its `full_sample` arm duplicates
the already-committed B=1000 run at B=99, and its PASS gate (any of 5 subgroups
at p ≤ 0.10) fires ~40% of the time under a global null. Replace with:

**Spike 5′ — slug `spike-05-c1-pl-postmortem-markov0`**

Part 1 (post-mortem, no new null batteries):
1. Load `results/trajectory_tda_bhps/c1_pl_fiedler_null_2026-07-07.json`. Report
   observed IFA vs null mean/median/std and the observed percentile.
2. Verify the centering argument empirically: regenerate ~20 null draws using the
   committed script's null mechanism
   (`trajectory_tda/scripts/c1_pl_fiedler_null_battery.py`) and measure the
   relative Frobenius deviation of the mean null count matrix from the observed
   count matrix. Expected: small (sampling noise only), confirming sufficiency.
3. Draft a permanent methodological note (vault path
   `02-Notes/Permanent/Markov-k-null-cannot-reject-statistics-of-the-order-k-sufficient-statistic.md`,
   staged in the worktree as a draft for User review before vault write):
   perturbation ≠ non-centering; invariance audits must check both.

Part 2 (one redesigned live probe, pilot_B = 99):
- Same observed substrate and Fiedler/IFA machinery (reuse
  `trajectory_tda/topology/persistent_laplacian.py`).
- Null = **Markov-0 / order-shuffle**: permute each trajectory's state sequence
  i.i.d. (preserves per-trajectory marginals and lengths, destroys first-order
  structure); rebuild the 9×9 counts per draw; recompute the Fiedler curve on the
  fixed 35-threshold grid; IFA via trapezoid.
- Baselines per draw: Markov-chain spectral gap, transition entropy.
- Decision rule: rejection (p ≤ 0.05) is EXPECTED (first-order structure is
  obviously real); the informative gate is redundancy —
  PASS only if |Spearman ρ(IFA, spectral gap)| < 0.95 AND
  |Spearman ρ(IFA, transition entropy)| < 0.95 across null-plus-observed rows.
  PASS ⇒ the PL spectrum carries information beyond standard chain summaries even
  against a weak null ⇒ a redesigned-substrate pre-reg (e.g. per-wave
  time-resolved transition graphs) is worth drafting.
  FAIL/redundant ⇒ strong PARK for persistent Laplacians on this substrate class;
  record in the [NEGATIVE]-companion note.

Run Spike 5′ AFTER Spike 7 in the execution order (it is the lowest-urgency item
that still runs compute).

## A3. Spike 3 data prerequisite (LSOA adjacency)

An LSOA boundary/adjacency source is NOT on disk. Add as step 0 of Spike 3:
download the ONS LSOA (Dec 2021) boundaries generalised-clipped GeoJSON/GPKG from
the ONS Open Geography Portal (OGL v3.0) to a gitignored path under
`data/`; record URL, filename, download date, and SHA-256 in the spike result
note. If the download or queen-contiguity construction fails → status `BLOCKED`
(as the original text already provides). IMD 2025 File 7 is already on disk
(downloaded 2026-07-03) — record its SHA-256 in the result note.

## A4. Subgroup membership referent (Spikes 5′/7)

`results/panel_methodology/fdr/subgroup_checkpoints/*.json` contain **summary
statistics only** (t_ratio, p-values, n) — NOT trajectory membership. Subgroup
state sequences/transition counts must be rebuilt from the T1.28 stratification
pipeline (locate the covariate/stratifier assignment code used by the T1.28
per-subgroup battery; verify against the checkpoint `n` values, e.g.
bhps nssec Professional-Managerial n=335). Do not attempt to derive counts from
the checkpoints. If the stratification code cannot reproduce a subgroup's `n`,
mark that subgroup `MISSING` and continue.

## A5. Repo-convention layer (applies to every spike)

- Branch: `run/discovery-spikes-mcbif` (single branch, one continuous agent, one
  PR at the end; CodeRabbit review-then-merge — never merge before the review).
- Worktree: after `git worktree add`, immediately copy
  `c:\Users\steph\TDL\.env` into the worktree (mandatory; `uv run --env-file .env`
  fails silently without it). Never run two `uv run` invocations concurrently in
  the same worktree (venv corruption).
- Commits: `[EXPLORE] P01: <spike-slug> — <one-line outcome>` via a BOM-free
  `git commit -F` file; pre-commit hooks never skipped.
- New modules under `trajectory_tda/topology/` carry the research-context header,
  type hints on public APIs (`numpy.typing.NDArray`), Google docstrings, and at
  least one deterministic unit test each (the original text's test list stands).
- Scratch outputs: `scratch/discovery_spikes/<spike_slug>/` (gitignored). NOTHING
  under `results/` — spikes are toy/feasibility compute. The only exception
  remains a resource-preflight record if a preflight is actually run at scale.
- Pre-registration-before-compute: before each spike's compute, write the result
  note skeleton (`vault/00-Meta/Discovery/<spike_slug>-result-YYYY-MM-DD.md`)
  containing the spike's parameters and decision rule verbatim from this plan and
  a `registered_at` timestamp; fill outcome fields after the run.
- WSL invocations (Spike 1 toy validation): use the Bash tool with
  `run_in_background: true` and `python -u` — `wsl bash -c "... &"` and
  Start-Process variants silently die with the parent session.
- Wall-time guardrail: any single computation projected > 2 h is benchmarked
  first (worker sweep, > worker-count units); > 12 h projected → STOP and
  escalate, do not launch.

## A6. Spike 1 validation gate is mandatory

The toy cross-validation against the existing MCbiF/RIVET implementation (WSL,
confirmed working on this machine 2026-07-03) is the correctness anchor for the
nerve backend and MUST be attempted. The paper's 3-element worked example is
necessary but not sufficient. Only if the WSL environment genuinely fails after
a real attempt does the spike cap at `PARTIAL` (record the failure mode).

## A7. Execution order (amended)

```text
1. Spike 1  (nerve-MCbiF employment backend)
2. Spike 2  (order-sensitive statistic audit)
3. Spike 4  (zigzag/Sankey fallback)
4. Spike 3  (spatialised deprivation MCbiF)
5. Spike 7  (sheaf/cellular Laplacian)
6. Spike 5′ (C1 post-mortem + Markov-0 probe)   ← replaces Spike 5
7. Spike 6  (Mapper/Reeb fallback — timeboxed 4 h; drop if the session is long)
```

---

# Global rules for all seven spikes

Each spike is a feasibility spike, not a paper run. Do not write paper prose. Do not run B=1000 null batteries. Do not write final results into `results/` unless an existing project convention explicitly requires a resource-preflight record; otherwise use a gitignored scratch directory and a vault discovery note.

Use:

```text
seed = 42
pilot_B = 99
alpha = 0.05
permutation_p = (1 + number_of_null_statistics_ge_observed) / (1 + B)
```

Use these output locations:

```text
scratch/discovery_spikes/<spike_slug>/
vault/00-Meta/Discovery/<spike_slug>-result-YYYY-MM-DD.md
```

Every result note must contain:

```yaml
type: discovery-spike-result
spike_slug: <slug>
date: <YYYY-MM-DD>
status: PASS | PARTIAL | FAIL | BLOCKED
seed: 42
pilot_B: 99
wall_time_seconds: <float>
peak_rss_gib: <float>
git_commit: <current commit>
wrote_to_results: false
```

Before ending each spike, run:

```bash
git status --short
python -m pytest tests/topology -q
```

If a spike introduces new code, add at least one deterministic unit test. If the spike depends on another spike and that dependency failed, record `BLOCKED`, not `FAIL`.

# Shared implementation task: exact finite-field topology utilities

Complete this before Spikes 1, 2, 3, and 4.

Create:

```text
trajectory_tda/topology/f2_betti.py
trajectory_tda/topology/mcbif_nerve.py
tests/topology/test_f2_betti.py
tests/topology/test_mcbif_nerve.py
```

Implement the following.

```python
def rank_mod2(matrix: np.ndarray) -> int:
    """
    Return rank over F2.
    Input is a uint8/bool 2D array. Mutate a copy, not the input.
    """

def betti_0_1_from_skeleton(
    n_vertices: int,
    edges: list[tuple[int, int]],
    triangles: list[tuple[int, int, int]],
) -> tuple[int, int]:
    """
    Compute beta0, beta1 for a finite 2-skeleton over F2.

    beta0 = n_vertices - rank(B1)
    beta1 = n_edges - rank(B1) - rank(B2)

    Edge orientation is arbitrary but fixed by sorted vertex IDs.
    Triangle boundary is the three incident edges, mod 2.
    """
```

For MCbiF nerve:

```python
def masks_from_partitions(partitions: list[np.ndarray]) -> dict[tuple[int, int], int]:
    """
    partitions[m][i] is the cluster label of unit i at scale/wave m.
    Return Python-int bit masks keyed by (m, label).
    """

def nerve_cell_skeleton(
    masks: dict[tuple[int, int], int],
    start: int,
    end: int,
    max_dim: int = 2,
) -> tuple[list[tuple[int, int]], list[tuple[int, int, int]], list[tuple[int, int]]]:
    """
    Build the nerve cell K_{start,end}.

    Vertices are cluster vertices (m,label) for start <= m <= end.
    Include an edge when mask_a & mask_b != 0.
    Include a triangle when mask_a & mask_b & mask_c != 0.
    Return vertices, edges, triangles.
    """

def hilbert_grid_h0_h1(partitions: list[np.ndarray]) -> dict[str, np.ndarray]:
    """
    Return triangular M x M arrays HF0 and HF1.
    Cells with start > end should be np.nan.
    """

def hf_statistics(hf0: np.ndarray, hf1: np.ndarray) -> dict[str, float]:
    """
    Return:
    h1_total_area
    h1_lag1_area
    h1_lag2_area
    h1_lag3_area
    h1_lag_weighted_area where weight = 1 / (1 + lag)
    h1_endpoint
    h1_max
    h0_total_area
    h0_lag1_area
    """
```

Tests must include:

1. Empty-discrete partitions: all singleton labels at every scale should have HF1 total area 0.
2. Fully constant one-cluster partition at every scale should have HF0 = 1 and HF1 = 0.
3. Three-element MCbiF example from the paper: `theta(0) = {{1},{2},{3}}`, `theta(1) = {{1,2},{3}}`, `theta(2) = {{1},{2,3}}`, `theta(3) = {{1,3},{2}}`, `theta(4) = {{1,2,3}}`. At least one H1 cell must be positive, matching the paper's description of a 1-conflict example. 

The agent must not implement full multiparameter barcodes. For these spikes, HF0 and HF1 grids are sufficient.

# Spike 1: exact nerve-MCbiF backend for employment

Slug:

```text
spike-01-nerve-mcbif-employment
```

Purpose: replace the memory-heavy individual-level MCbiF construction with the exact nerve construction. This is the main rescue spike for the resource-blocked employment battery.

Inputs:

```text
results/trajectory_tda_integration/01_trajectories_sequences.json
results/trajectory_tda_integration/embeddings.npy
```

Use the hashes from the resource preflight as expected hashes:

```text
embeddings.npy:
69b2ba55902565960e8009004d2c21332d3786e2af3e83edc4ac0a2d3a5f5540

01_trajectories_sequences.json:
7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8
```

The frozen design has 27,280 source trajectories, 13 valid wave positions under the 50 percent coverage rule, 19,912 trajectories present at every valid wave position, and 9 employment states: `EH, EL, EM, IH, IL, IM, UH, UL, UM`. 

Implementation steps:

1. Load state sequences.
2. Restrict to wave positions `0..12`.
3. Keep only trajectories with valid state labels at every wave `0..12`.
4. Encode states as integers in this fixed order:

```python
STATE_ORDER = ["EH", "EL", "EM", "IH", "IL", "IM", "UH", "UL", "UM"]
```

5. Build `partitions`, a list of 13 integer arrays of length 19,912.
6. Compute HF0/HF1 using `hilbert_grid_h0_h1`.
7. Compute `hf_statistics`.
8. Measure wall time and peak RSS.

Validation against existing MCbiF/RIVET:

Run the existing MCbiF/RIVET implementation on the old toy setting only:

```text
seed = 42
n_trajectories = 500
waves = 0..4
```

Then run the new nerve backend on the identical sample and wave range.

Required comparison:

```text
HF0 grids must match cellwise.
HF1 grids must match cellwise.
```

If existing MCbiF/RIVET cannot be invoked, status is `PARTIAL`, not `PASS`, even if the new backend runs.

Success criteria:

```text
PASS if:
1. Toy nerve HF0/HF1 matches existing MCbiF/RIVET cellwise.
2. Full 19,912 x 13 employment object completes with peak RSS <= 2.0 GiB.
3. Full object wall time <= 300 seconds on one worker.
4. Tests pass.
```

Failure criteria:

```text
FAIL if:
1. Toy HF0/HF1 disagrees with existing MCbiF/RIVET.
2. Full object peak RSS > 4.0 GiB.
3. Full object does not complete within 900 seconds.
```

Output JSON:

```json
{
  "spike_slug": "spike-01-nerve-mcbif-employment",
  "n_eligible": 19912,
  "n_waves": 13,
  "n_cluster_vertices": 117,
  "toy_match_hf0": true,
  "toy_match_hf1": true,
  "full_hf0": [[...]],
  "full_hf1": [[...]],
  "statistics": {...},
  "wall_time_seconds": 0.0,
  "peak_rss_gib": 0.0,
  "status": "PASS"
}
```

Do not run any null battery in this spike.

# Spike 2: order-sensitive MCbiF statistic audit

Slug:

```text
spike-02-mcbif-order-sensitive-statistics
```

Purpose: determine whether the employment MCbiF null should use wave-order permutations, and identify a statistic that is actually order-sensitive. The MCbiF paper explicitly notes invariance to swaps of partitions inside a fixed interval, so global endpoint or full-area statistics can be weak null targets. 

Dependency:

```text
Requires Spike 1 PASS.
If Spike 1 is not PASS, record BLOCKED.
```

Inputs:

Use the full 19,912 x 13 employment partition sequence from Spike 1.

Generate these sequences:

```text
observed
reverse_order
99 uniform random wave permutations
99 adjacent-block permutations with block size 2
99 adjacent-block permutations with block size 3
```

For block permutations:

```python
# block size 2 example
blocks = [(0,1), (2,3), ..., (12,)]
shuffle block order with seed 42 + b
flatten blocks without reordering inside block
```

Compute these statistics for every sequence:

```text
h1_total_area
h1_lag1_area
h1_lag2_area
h1_lag3_area
h1_lag_weighted_area
h1_endpoint
h1_max
h0_total_area
h0_lag1_area
```

Compute baselines for every sequence:

```text
mean_adjacent_ARI
mean_adjacent_conditional_entropy
mean_all_pair_ARI
mean_all_pair_conditional_entropy
```

Use `sklearn.metrics.adjusted_rand_score` for ARI. Implement conditional entropy directly from contingency tables.

Statistic classification rule:

A statistic is `ORDER_INFORMATIVE` if all are true:

```text
1. Across the 99 uniform random permutations, n_unique >= 20.
2. Across the 99 uniform random permutations, std > 1e-9.
3. observed value != reverse_order value.
4. abs(Spearman rho with mean_adjacent_ARI) < 0.95.
5. abs(Spearman rho with mean_adjacent_conditional_entropy) < 0.95.
```

Candidate primary statistic priority order:

```text
1. h1_lag1_area
2. h1_lag2_area
3. h1_lag3_area
4. h1_lag_weighted_area
5. h1_total_area
```

Choose the first statistic in this list classified as `ORDER_INFORMATIVE`.

Success criteria:

```text
PASS if at least one H1 statistic is ORDER_INFORMATIVE.
PARTIAL if only H0 statistics are ORDER_INFORMATIVE.
FAIL if no statistic is ORDER_INFORMATIVE.
```

Output JSON:

```json
{
  "spike_slug": "spike-02-mcbif-order-sensitive-statistics",
  "chosen_primary_statistic": "h1_lag2_area",
  "statistic_table": [
    {
      "name": "h1_lag1_area",
      "observed": 0.0,
      "reverse": 0.0,
      "uniform_perm_mean": 0.0,
      "uniform_perm_std": 0.0,
      "n_unique": 0,
      "rho_adjacent_ari": 0.0,
      "rho_adjacent_ce": 0.0,
      "classification": "ORDER_INFORMATIVE | INVARIANT | REDUNDANT"
    }
  ],
  "status": "PASS"
}
```

If `PASS`, write a draft pre-registration amendment saying that any future employment MCbiF null must use the selected order-sensitive statistic, not raw global H1 rank.

# Spike 3: spatialised deprivation MCbiF

Slug:

```text
spike-03-spatialised-deprivation-mcbif
```

Purpose: repair the deprivation null by making geography enter the object before clustering. The current deprivation pre-registration uses IMD 2025 seven-domain LSOA vectors and a spatially permuted null, but the single toy null draw had H1 rank 8 compared with observed H1 rank 6, so the null requires stronger scrutiny before dispatch. 

Inputs:

```text
IMD 2025 File 7 CSV
IMD 2025 LSOA spatial geopackage or equivalent LSOA boundary/adjacency source
```

Use the seven columns fixed in the existing pre-registration:

```text
Income Score (rate)
Employment Score (rate)
Education, Skills and Training Score
Health Deprivation and Disability Score
Crime Score
Barriers to Housing and Services Score
Living Environment Score
```

The IMD source and 33,755 LSOA scope are already specified in the existing dispatch pre-registration. 

Deterministic LAD selection:

```text
1. Include Leeds LAD if present.
2. Add the five LADs with the largest number of LSOAs.
3. If Leeds is already in the top five, use the top six LADs by LSOA count.
```

Do not hand-pick cities.

Observed construction for each selected LAD:

1. Extract LSOAs in LAD.
2. Standardise the seven domain columns within the LAD.
3. Build queen-contiguity adjacency from the spatial geometry.
4. For each LSOA `i`, compute closed-neighbourhood feature:

```python
local_x_i = mean(raw_zscore_x_j for j in {i} union neighbours(i))
```

5. For each `k in [3, 5, 7, 10, 15]`, run k-means on `local_x_i`.

```python
KMeans(n_clusters=k, n_init=50, random_state=42)
```

6. Treat the five k-means outputs as the partition sequence.
7. Compute HF0/HF1 grid using the nerve backend.

Null construction:

For each null draw `b = 0..98`:

1. Permute the raw seven-dimensional LSOA vectors across fixed spatial nodes using seed `42 + b`.
2. Recompute closed-neighbourhood local features using the unchanged adjacency graph.
3. Re-standardise local features within LAD.
4. Re-run k-means for all k values.
5. Recompute HF0/HF1.

This is not post-construction relabelling. It changes the spatially localised data before clustering. This directly addresses the existing invariance warning that post-construction permutation collapses the null. 

Statistics:

```text
primary: h1_total_area
secondary: h1_lag1_area, h1_lag2_area, h1_max
baselines:
  mean_ARI_across_k
  Moran_I for each of the seven raw domains
  Moran_I for PC1 of the seven-domain z-score matrix
```

Implement Moran's I on the adjacency graph:

```python
I = (n / W) * sum_ij w_ij (x_i - mean_x)(x_j - mean_x) / sum_i (x_i - mean_x)^2
```

Decision rule per LAD:

```text
signal_lad = observed h1_total_area > 95th percentile of the 99 null values
```

Overall spike status:

```text
PASS if at least two selected LADs satisfy signal_lad.
PARTIAL if exactly one selected LAD satisfies signal_lad.
FAIL if zero selected LADs satisfy signal_lad.
BLOCKED if adjacency cannot be constructed.
```

Redundancy flag:

For each LAD, compute Spearman correlation across null-plus-observed rows between `h1_total_area` and:

```text
mean_ARI_across_k
Moran_I_PC1
```

If both absolute correlations are `>= 0.95`, mark the LAD as `REDUNDANT_EVEN_IF_SIGNAL`.

Final `PASS` requires at least one signal LAD not marked redundant.

Output JSON:

```json
{
  "spike_slug": "spike-03-spatialised-deprivation-mcbif",
  "selected_lads": [...],
  "lad_results": [
    {
      "lad_code": "...",
      "lad_name": "...",
      "n_lsoas": 0,
      "observed_h1_total_area": 0.0,
      "null_h1_total_area": [...],
      "p_value": 0.0,
      "signal_lad": true,
      "rho_h1_ari": 0.0,
      "rho_h1_moran_pc1": 0.0,
      "redundant": false
    }
  ],
  "status": "PASS"
}
```

If `PASS`, draft a replacement deprivation pre-registration. It must replace the old raw spatial-permutation null with this local-neighbourhood spatial null.

# Spike 4: zigzag/Sankey adjacent-conflict persistence for employment

Slug:

```text
spike-04-employment-zigzag-sankey-conflicts
```

Purpose: provide a cheaper, order-sensitive fallback to full MCbiF for employment. The MCbiF paper states that the Sankey diagram can be retrieved from a zigzag subfiltration of the nerve-based MCbiF, and that in a single adjacent layer a 1-conflict exists iff there is a cycle in the bipartite Sankey graph. 

Dependency:

```text
Can run after Spike 1 PASS or independently using the same partition-loading code.
```

Inputs:

Same 19,912 x 13 employment partitions as Spike 1.

For each adjacent wave pair `(m, m+1)`:

1. Create bipartite graph with left vertices `(m,state)` and right vertices `(m+1,state)`.
2. Add edge `(state_a, state_b)` if at least one trajectory has state_a at wave m and state_b at wave m+1.
3. Compute graph beta1:

```python
beta1 = n_edges - n_vertices + n_connected_components
```

4. Also compute weighted edge counts, but do not use weights for beta1.

Observed statistics:

```text
adjacent_beta1_sum
adjacent_beta1_max
adjacent_beta1_positive_count
adjacent_beta1_weighted_sum where weight = number of trajectories on edge
```

Nulls:

```text
99 uniform wave-order permutations
99 adjacent-block permutations with block size 2
```

For each permuted order, recompute adjacent Sankey graphs and statistics.

Baselines:

For each adjacent pair:

```text
ARI(partition_m, partition_m+1)
conditional_entropy(partition_{m+1} | partition_m)
transition_entropy
```

Aggregate by mean across adjacent pairs.

Decision rule:

```text
PASS if:
1. observed adjacent_beta1_sum > 0;
2. adjacent_beta1_sum has >= 20 unique values across 99 uniform permutations;
3. abs(Spearman rho(adjacent_beta1_sum, mean_adjacent_ARI)) < 0.95;
4. abs(Spearman rho(adjacent_beta1_sum, mean_adjacent_conditional_entropy)) < 0.95.

PARTIAL if beta1 is positive but redundant with both baselines.

FAIL if observed adjacent_beta1_sum == 0 or statistic is invariant under permutations.
```

Output JSON:

```json
{
  "spike_slug": "spike-04-employment-zigzag-sankey-conflicts",
  "adjacent_wave_results": [
    {
      "wave_pair": [0, 1],
      "n_vertices": 18,
      "n_edges": 0,
      "n_components": 0,
      "beta1": 0
    }
  ],
  "observed_statistics": {...},
  "null_statistics": {...},
  "baseline_correlations": {...},
  "status": "PASS"
}
```

If this passes while Spike 2 fails, recommend zigzag/Sankey conflict summaries as the employment fallback instead of full MCbiF.

# Spike 5: subgroup Markov-chain persistent-Laplacian topology

Slug:

```text
spike-05-subgroup-markov-persistent-laplacian
```

Purpose: extend the already successful C1 persistent-Laplacian route from one full-sample transition graph to a controlled subgroup family, without running the full C1 dispatch. The full C1 draft already specifies the observed 35-threshold Fiedler curve, B=1000 Markov-1 shuffles, IFA statistic, and BH-FDR pointwise comparisons, but that is a separate dispatch, not this spike. 

Inputs:

Use existing transition-count construction from C1. Do not refit embeddings. Do not build VR complexes. Use only 9-state employment transition graphs.

Subgroups, fixed order:

```text
full_sample
nssec_prof_mgr
nssec_routine
cohort_1960s
cohort_1980s
```

If a subgroup checkpoint is missing, mark that subgroup `MISSING` and continue. Do not replace it with another subgroup.

Implementation:

1. Ensure `trajectory_tda/topology/persistent_laplacian.py` exposes:

```python
def fiedler_curve_from_transition_counts(
    counts_9x9: np.ndarray,
    dtype: np.dtype = np.float32,
) -> dict:
    """
    Return thresholds, lambda1 curve, beta1 kernel dimensions if available.
    Edge weights = float32(1 / (count_ij + count_ji + 1)).
    """
```

2. For each subgroup, build observed 9 x 9 directed transition counts.
3. Compute lambda1 curve at all distinct thresholds.
4. Compute IFA using trapezoidal rule.
5. Run `pilot_B = 99` Markov-1 null draws for each subgroup.
6. Compute pilot p-value for IFA.

Null:

Use the same Markov-1 mechanism as C1:

```text
shuffle trajectories under first-order Markov model preserving empirical state-marginal distribution;
rebuild 9 x 9 transition counts;
recompute Fiedler curve;
compute IFA.
```

Do not compute lambda1 on cached scalar summaries. The C1 documents explicitly warn that the null graph must be rebuilt. 

Baselines per subgroup:

```text
ordinary Markov-chain spectral gap
transition entropy
H1 barcode count
persistence entropy if available
total persistence if available
```

Spike decision rule:

```text
PASS if:
1. At least three subgroup graphs complete.
2. At least one subgroup has pilot IFA p <= 0.10.
3. Across completed subgroups, IFA is not perfectly redundant with all baselines:
   not all abs(Spearman rho(IFA, baseline)) >= 0.95.

PARTIAL if all complete but no subgroup has p <= 0.10.

FAIL if fewer than three subgroup graphs complete or persistent-Laplacian validation fails.
```

Output JSON:

```json
{
  "spike_slug": "spike-05-subgroup-markov-persistent-laplacian",
  "subgroups": [
    {
      "name": "nssec_prof_mgr",
      "n_trajectories": 0,
      "observed_ifa": 0.0,
      "null_ifa": [...],
      "p_value": 0.0,
      "status": "COMPLETE"
    }
  ],
  "baseline_correlations": {...},
  "status": "PASS"
}
```

If `PASS`, draft a follow-up pre-registration for subgroup C1 extension. Do not modify the existing full C1 dispatch pre-registration.

# Spike 6: Mapper/Reeb graph fallback for deprivation and employment

Slug:

```text
spike-06-mapper-reeb-fallback
```

Purpose: test a less frontier but scalable topological summary route. This is a fallback, not a replacement for C1 or MCbiF.

Run two fixed substrates:

```text
A. Deprivation: selected LADs from Spike 3.
B. Employment: full eligible 19,912 trajectories using frozen PCA-20 embedding.
```

If either substrate is blocked, run the other and mark the blocked substrate accordingly.

Mapper implementation:

Create:

```text
trajectory_tda/topology/mapper_graph.py
tests/topology/test_mapper_graph.py
```

Function:

```python
def mapper_graph(
    X: np.ndarray,
    filter_values: np.ndarray,
    n_intervals: int,
    overlap: float,
    min_samples: int,
) -> nx.Graph:
    """
    Use deterministic Mapper:
    1. Cover each filter dimension with intervals.
    2. For each non-empty cover bin, cluster points in original X using DBSCAN.
    3. Each cluster becomes a node.
    4. Nodes are connected if their point memberships overlap.
    """
```

Fixed Mapper settings:

```text
filter dimension = 2
n_intervals = 10
overlap = 0.40
DBSCAN min_samples = 5
DBSCAN eps = median 5th-nearest-neighbour distance within the bin
```

Deprivation filter:

```text
PCA1 and PCA2 of the LAD-standardised seven-domain IMD vectors.
```

Employment filter:

```text
PC1 and PC2 of the frozen PCA-20 embedding, using columns 0 and 1 directly.
```

Graph statistics:

```text
n_nodes
n_edges
beta0
beta1 = n_edges - n_nodes + beta0
largest_component_fraction
mean_degree
degree_gini
```

Stability audit:

Run Mapper on this fixed parameter grid:

```text
(n_intervals, overlap) in:
(8, 0.30)
(10, 0.40)
(12, 0.50)
```

For each pair of settings, compute relative beta1 change:

```text
abs(beta1_a - beta1_b) / max(1, beta1_a, beta1_b)
```

Nulls:

Deprivation null:

```text
Use the same spatialised raw-vector permutation from Spike 3, B=99, per selected LAD.
```

Employment null:

```text
Permute employment-state labels across trajectories within each wave, B=99.
Do not permute embedding rows.
```

Decision rule:

```text
PASS if:
1. At least one substrate has observed beta1 above the 95th percentile of its null.
2. Median relative beta1 change across the three cover settings <= 0.50.
3. beta1 is not redundant with the relevant baseline:
   deprivation: abs(rho(beta1, Moran_I_PC1)) < 0.95;
   employment: abs(rho(beta1, mean_adjacent_ARI)) < 0.95.

PARTIAL if signal exists but stability fails.

FAIL if no substrate has null-exceeding beta1.
```

Output JSON:

```json
{
  "spike_slug": "spike-06-mapper-reeb-fallback",
  "deprivation": {...},
  "employment": {...},
  "status": "PASS"
}
```

Do not use UMAP or t-SNE filters. PCA filters only.

# Spike 7: sheaf/cellular Laplacian on the employment transition graph

Slug:

```text
spike-07-sheaf-cellular-laplacian-employment
```

Purpose: test a Topological Deep Learning-adjacent graph/sheaf route on the 9-state employment transition graph. This is intentionally small and exact.

Substrate:

```text
9 employment states as vertices.
Undirected support edge {i,j} exists if count_ij + count_ji > 0 in full sample.
Edge weight w_ij = count_ij + count_ji.
```

Group stalks:

Use these groups, fixed order:

```text
full_sample
nssec_prof_mgr
nssec_routine
cohort_1960s
cohort_1980s
```

For each group `g` and state `v`, compute:

```text
x_g(v) = proportion of all observed wave positions in group g assigned to state v
```

Construct a vertex signal:

```text
x(v) = [x_1(v), x_2(v), ..., x_G(v)] in R^G
```

Sheaf model:

Use identity restrictions from each vertex stalk to each edge stalk:

```text
R_{e,u} = I_G
R_{e,v} = I_G
```

Coboundary on edge `e = {u,v}`:

```text
delta_x(e) = sqrt(w_e) * (x(u) - x(v))
```

Sheaf energy:

```text
E_sheaf = sum_edges ||delta_x(e)||_2^2
```

This is a cellular sheaf Laplacian with identity restrictions. It is deliberately simple. Do not introduce learned restrictions in this spike.

Null:

For `b = 0..198`:

1. Permute subgroup labels across trajectories within strata defined by:

```text
trajectory length
first observed employment state
```

2. Recompute group state-occupancy signals.
3. Recompute `E_sheaf`.

Use `B = 199` here because the graph is tiny.

Baselines:

```text
ordinary graph Laplacian energy using full-sample scalar occupancy only
chi-square test statistic for subgroup x state contingency table
mean pairwise Jensen-Shannon divergence between subgroup state distributions
```

Decision rule:

```text
PASS if:
1. observed E_sheaf has p <= 0.10 against the 199-draw null;
2. abs(Spearman rho over null-plus-observed rows between E_sheaf and chi-square statistic) < 0.95;
3. abs(Spearman rho between E_sheaf and mean pairwise JS divergence) < 0.95.

PARTIAL if p <= 0.10 but redundancy correlations fail.

FAIL if p > 0.10.
```

Output JSON:

```json
{
  "spike_slug": "spike-07-sheaf-cellular-laplacian-employment",
  "n_vertices": 9,
  "n_edges": 0,
  "groups": [...],
  "observed_E_sheaf": 0.0,
  "null_E_sheaf": [...],
  "p_value": 0.0,
  "rho_chi_square": 0.0,
  "rho_js": 0.0,
  "status": "PASS"
}
```

If `PASS`, draft a new pre-registration for a sheaf-Laplacian employment-transition analysis. Do not describe it as a learned TDL model unless a later spike adds learned restrictions.

# Recommended execution order

Use this order:

```text
1. Spike 1: exact nerve-MCbiF employment backend
2. Spike 2: order-sensitive MCbiF statistic audit
3. Spike 4: zigzag/Sankey adjacent-conflict fallback
4. Spike 3: spatialised deprivation MCbiF
5. Spike 5: subgroup persistent-Laplacian topology
6. Spike 7: sheaf/cellular Laplacian employment graph
7. Spike 6: Mapper/Reeb fallback
```

Reason: Spike 1 unlocks or kills the MCbiF employment route. Spike 2 determines whether the employment null is meaningful. Spike 4 gives a cheaper fallback if Spike 2 exposes invariance. Spike 3 repairs the deprivation null. Spike 5 leverages the already strong C1 route. Spike 7 is small and methods-forward. Spike 6 is useful but less theoretically distinctive, so it should not consume early effort.

# Minimal backlog state transitions

Use these exact transitions:

```text
Spike 1 PASS:
  "MCbiF employment resource block resolved by exact nerve backend."

Spike 1 FAIL:
  "MCbiF employment remains resource/representation blocked; proceed to Spike 4 fallback."

Spike 2 PASS:
  "Employment MCbiF has order-sensitive H1 statistic; draft pre-reg amendment."

Spike 2 FAIL:
  "Wave-order MCbiF null is invariant or redundant; do not dispatch employment MCbiF as originally designed."

Spike 3 PASS:
  "Spatialised deprivation MCbiF null repaired; draft replacement deprivation pre-reg."

Spike 3 FAIL:
  "Deprivation MCbiF H1 does not exceed spatialised null at spike scale; park or kill."

Spike 4 PASS:
  "Zigzag/Sankey adjacent conflict is viable fallback."

Spike 5 PASS:
  "Subgroup persistent-Laplacian route merits pre-registered extension."

Spike 6 PASS:
  "Mapper/Reeb graph fallback viable but secondary."

Spike 7 PASS:
  "Sheaf/cellular Laplacian employment graph merits separate pre-registration."
```

The highest-value near-term outcome is a `PASS` on Spike 1 plus a `PASS` on Spike 2. That would turn the current MCbiF employment result from resource-blocked into a scalable, exact, order-audited design.
