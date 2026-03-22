# Agent Handoff: P3 Items 9 & 10 — Regional Stratification + Pipeline Sensitivity

## Context

You are working on the trajectory TDA paper in `c:\Projects\TDL`. The paper applies persistent homology to 27,280 employment-income trajectories from the British Household Panel Study (BHPS, 1991–2008) and Understanding Society (USoc, 2009–2023). The paper is at third-draft stage in `trajectory_tda/paper/third_draft.md` with an action plan in `trajectory_tda/paper/MISSING_ELEMENTS_ACTION_PLAN.md`.

All P1 and P2 items (1–8) are **completed**. You are implementing the final two P3 items:
- **Item 9**: Full regional stratification by Government Office Region (GOR)
- **Item 10**: Pipeline sensitivity checks

Read instructions from `.github/instructions/codacy.instructions.md` before editing code.

---

## Item 9: Regional Stratification by GOR

### Goal
Stratify the 27,280 trajectories by Government Office Region (GOR) and compute pairwise Wasserstein distances between regional persistence diagrams, following the exact pattern used for gender, parental NS-SEC, and birth cohort stratification. This is a full analysis, not a preliminary 2–3 region comparison.

### Data Availability

**USoc (UKDA-6614):** `trajectory_tda/data/UKDA-6614-tab/tab/ukhls/`
- Variable: `{wave}_gor_dv` in `{wave}_indresp.tab` (wave prefixes a–n)
- Codes: 1=North East, 2=North West, 3=Yorkshire & Humber, 4=East Midlands, 5=West Midlands, 6=East of England, 7=London, 8=South East, 9=South West, 10=Wales, 11=Scotland, 12=Northern Ireland
- Coverage: 50,994 respondents in wave a alone; all 12 regions represented (min ~2,060 in NE and NI)

**BHPS (UKDA-5151):** `trajectory_tda/data/UKDA-5151-tab/tab/bhps_w{N}/`
- Variable: `{wave}region` in `{wave}indresp.tab` (wave prefixes a–r for waves 1–18)
- Codes: 1–18 (finer than USoc GOR — Inner London, Outer London separate, etc.)
- You will need to map BHPS 18-region codes → 12-region USoc GOR codes. The mapping is:
  - 1 (Inner London) + 2 (Outer London) → 7 (London)
  - 3 (Rest of South East) → 8 (South East)
  - 4 (South West) → 9 (South West)
  - 5 (East Anglia) → 6 (East of England)
  - 6 (East Midlands) → 4 (East Midlands)
  - 7 (West Midlands Conurbation) + 8 (Rest of West Midlands) → 5 (West Midlands)
  - 9 (Greater Manchester) + 10 (Merseyside) + 11 (Rest of North West) → 2 (North West)
  - 12 (South Yorkshire) + 13 (West Yorkshire) + 14 (Rest of Yorkshire & Humber) → 3 (Yorkshire & Humber)
  - 15 (Tyne & Wear) + 16 (Rest of North) → 1 (North East)
  - 17 (Wales) → 10 (Wales)
  - 18 (Scotland) → 11 (Scotland)
  - Northern Ireland (12) is USoc-only (BHPS didn't cover NI until late waves)

**BHPS→USoc pidp cross-walk:** BHPS respondents have both a `pid` (BHPS-era) and a `pidp` (USoc-era) identifier. The cross-reference file is at `trajectory_tda/data/UKDA-6614-tab/tab/ukhls/xwavedat.tab` — it contains both `pid` and `pidp` columns.

### Implementation Plan

**Step 1: Add GOR extraction to `trajectory_tda/data/covariate_extractor.py`**

Add a function `extract_gor(data_dir, pidps)` that:
1. Reads `a_gor_dv` from USoc wave a `a_indresp.tab` for the primary match
2. Falls back to BHPS wave 1 `aregion` (mapped to GOR codes) via the xwavedat cross-walk
3. For respondents found in neither, tries later USoc waves (b, c, ...)
4. Returns a DataFrame: `pidp → gor_code (int 1–12)` with `gor_label` (str)

GOR labels dict:
```python
GOR_LABELS = {
    1: "North East", 2: "North West", 3: "Yorkshire & Humber",
    4: "East Midlands", 5: "West Midlands", 6: "East of England",
    7: "London", 8: "South East", 9: "South West",
    10: "Wales", 11: "Scotland", 12: "Northern Ireland",
}
```

**Step 2: Add `run_gor` function to `trajectory_tda/scripts/run_stratified.py`**

Follow the exact pattern of `run_gender`, `run_cohort`, `run_nssec`:
1. Call `_load_shared_data(args)` to get embeddings, pidp_array, cov_lookup
2. Call `extract_gor(args.data_dir, pidp_array)` to get GOR labels
3. Filter to regions with ≥ 200 trajectories (expect all 12 to qualify if coverage is ~60%+)
4. Call `compare_groups(embeddings, gor_labels, n_permutations=args.n_perms, n_landmarks=args.landmarks)`
5. Save results to `06_stratified.json` under key `"gor"`
6. Add `"gor"` to the `STRAT_RUNNERS` dict

**Step 3: Run the analysis**

```bash
cd c:\Projects\TDL
python -m trajectory_tda.scripts.run_stratified --strat gor \
    --data-dir trajectory_tda/data \
    --results-dir results/trajectory_tda_integration \
    --n-perms 100 --landmarks 2000
```

**Step 4: Apply FDR correction**

With 12 regions, there are $\binom{12}{2} = 66$ pairs × 2 dimensions = 132 tests. Apply BH FDR at q < 0.05 to all 132 tests (or pool with existing 50 tests for a global correction of 182). Follow the pattern in `trajectory_tda/scripts/run_fdr_correction.py`.

**Step 5: Update the third draft**

Add a **Regional** paragraph to §4.6, after the Birth Cohort paragraph:

> **Region.** Twelve Government Office Regions yield 66 pairwise comparisons (132 dimension-specific tests). Report how many are significant raw and after BH correction. Highlight the London vs. North East contrast (largest expected geographic inequality) and any other notable patterns. Note the north–south divide if it appears topologically.

Update Table 4 to add a `Region` row. Add a brief mention in §5.4 (Limitations) noting that GOR is a coarse spatial unit and neighbourhood-level analysis would require geocoded data beyond what BHPS/USoc provide at standard access levels.

Update the `MISSING_ELEMENTS_ACTION_PLAN.md` item 9 status to Completed with results summary.

---

## Item 10: Pipeline Sensitivity Checks

### Goal
Vary three pipeline parameters and show that substantive conclusions (order-shuffle H₀ significance, Markov-1 non-rejection, regime structure) are stable. Report results in an appendix table.

### Parameters to Vary

| Parameter | Baseline | Alternatives | How to vary |
|---|---|---|---|
| Minimum trajectory length | 10 years | 8, 12 years | `build_trajectories(min_years=X)` in `trajectory_tda/data/trajectory_builder.py` |
| N-gram weighting | TF (raw) | TF-IDF | `ngram_embed(tfidf=True)` in `trajectory_tda/embedding/ngram_embed.py` |
| VR filtration threshold | 75th percentile | 50th, 90th | `compute_rips_ph(thresh=np.percentile(dists, P))` — set in `poverty_tda/topology/multidim_ph.py` line ~235 |

### Implementation Plan

**Step 1: Create `trajectory_tda/scripts/run_pipeline_sensitivity.py`**

A script that runs a grid of pipeline configurations. For each configuration:

1. **Rebuild trajectories** (min_years varies): Call `build_trajectories_from_raw(data_dir, min_years=X)` 
2. **Re-embed** (tfidf varies): Call `ngram_embed(trajectories, tfidf=Y, pca_dim=20)`
3. **Select landmarks**: `maxmin_landmarks(embeddings, 5000)`
4. **Compute PH** (threshold varies): `compute_rips_ph(landmarks, max_dim=1, thresh=np.percentile(dists, P))`
5. **Fit GMM k=7**: `GaussianMixture(n_components=7).fit(embeddings)`
6. **Run order-shuffle null** (n=100): `permutation_test_trajectories(embeddings, trajectories, null_type="order_shuffle", n_permutations=100)`
7. **Record**: total persistence H₀/H₁, order-shuffle p-value, GMM k=7 ARI vs baseline labels, number of trajectories

The grid has 3 (min_years) × 2 (tfidf) × 3 (threshold) = 18 configurations total. However, since VR threshold only affects PH (not embedding/GMM), we can optimise by computing 6 embedding variants and running PH 3 times on each = 18 PH runs but only 6 embedding + 6 GMM + 6 null-model runs.

**Step 2: Run the grid**

```bash
cd c:\Projects\TDL
python -m trajectory_tda.scripts.run_pipeline_sensitivity \
    --data-dir trajectory_tda/data \
    --output-dir results/trajectory_tda_robustness/pipeline_sensitivity
```

Save results as `pipeline_sensitivity_results.json`.

**Step 3: Update the third draft**

Add **Appendix C: Pipeline Sensitivity** with a table:

| min_years | weighting | threshold | N trajectories | H₀ total pers | H₁ total pers | OS H₀ *p* | GMM ARI vs baseline |
|---|---|---|---|---|---|---|---|
| 8 | TF | 50th | ... | ... | ... | ... | ... |
| 8 | TF | 75th | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |
| 12 | TF-IDF | 90th | ... | ... | ... | ... | ... |

Add a brief paragraph in §5.5 (or wherever pipeline robustness is discussed):

> Pipeline sensitivity analysis (Appendix C) shows that [key result: order-shuffle H₀ significance is stable across all 18 configurations / regime structure ...]. The number of trajectories ranges from [N at min=8] to [N at min=12], demonstrating that conclusions are not sensitive to minimum length cutoff. TF-IDF weighting [increases/decreases/does not affect] topological structure relative to raw TF.

Update `MISSING_ELEMENTS_ACTION_PLAN.md` item 10 to Completed.

---

## Key Files to Read Before Starting

1. `trajectory_tda/paper/third_draft.md` — current draft (read §3.2, §3.3, §3.7, §4.6, §5.4, §5.5, Appendix B)
2. `trajectory_tda/paper/MISSING_ELEMENTS_ACTION_PLAN.md` — action plan tracking
3. `trajectory_tda/scripts/run_stratified.py` — existing stratification runners (follow this pattern for GOR)
4. `trajectory_tda/data/covariate_extractor.py` — existing covariate extraction (add GOR here)
5. `trajectory_tda/analysis/group_comparison.py` — `compare_groups()` function signature
6. `trajectory_tda/data/trajectory_builder.py` — `build_trajectories()` with `min_years` param
7. `trajectory_tda/embedding/ngram_embed.py` — `ngram_embed()` with `tfidf` param
8. `poverty_tda/topology/multidim_ph.py` — `compute_rips_ph()` with `thresh` param (line ~201)
9. `trajectory_tda/topology/permutation_nulls.py` — `permutation_test_trajectories()` for null models
10. `trajectory_tda/scripts/run_fdr_correction.py` — FDR correction pattern
11. `.github/instructions/codacy.instructions.md` — coding standards

## Key Results Files

- `results/trajectory_tda_integration/01_trajectories.json` — trajectory metadata (pidp dict, keyed by str index)
- `results/trajectory_tda_integration/embeddings.npy` — (27280, 20) PCA embeddings
- `results/trajectory_tda_integration/06_stratified.json` — existing gender/cohort/nssec results
- `results/trajectory_tda_robustness/fdr_correction_results.json` — existing FDR results (50 tests)

## Execution Order

1. **Item 9 first** (regional stratification) — this only adds a new stratification axis with no pipeline changes
2. **Item 10 second** (pipeline sensitivity) — this reruns the full pipeline under varied parameters

## Important Notes

- The venv is at `c:\Projects\TDL\.venv` — activate before running
- Use `n_jobs=1` for any parallel computation to avoid OOM (the UMAP Markov-1 run crashed with `n_jobs=-1`)
- Raw BHPS data is at `trajectory_tda/data/UKDA-5151-tab/`, USoc at `trajectory_tda/data/UKDA-6614-tab/`
- GOR variable: USoc = `{wave}_gor_dv` in `{wave}_indresp.tab`; BHPS = `{wave}region` in `{wave}indresp.tab`
- The existing `_load_shared_data` already loads embeddings, pidps, and covariates — extend it or call GOR extraction separately
- For pipeline sensitivity: the baseline configuration is min_years=10, tfidf=False, thresh=75th percentile
- All text edits to third_draft.md should be concise and follow the style of existing paragraphs in §4.6
