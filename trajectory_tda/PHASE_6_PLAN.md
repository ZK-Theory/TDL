Here is a ready‑to‑drop `PHASE_6_PLAN.md` that assumes your existing trajectory_tda setup and Phase 1–5 outputs.

***

```markdown
# Phase 6 Plan: Regime Stickiness and Escape Paths

This plan extends the **Phase 1–5 Trajectory TDA pipeline** documented in:

- `plan-trajectoryTdaExperimental.md` (Phase 1–5 nulls, viz, stratification, paper 1)  
- `paper_outline.md` (current “regimes + nulls + stratification” manuscript)

The Phase 1–5 work established:

- A production-ready `trajectory_tda` pipeline for 9‑state employment×income trajectories.  
- 7 BIC-optimal mobility regimes via GMM on PCA‑20D n‑gram embeddings (`05_analysis.json`).  
- Strong H₀ signal vs order‑shuffle nulls, Markov‑consistent H₀ vs Markov‑1/2, non-significant H₁ vs all nulls (`03_ph.json`, `03_ph_diagrams.json`, `04_nulls.json`, `04_nulls_markov2.json`).  
- Stratified differences in regime topology by gender, cohort, and parental NS‑SEC (`06_stratified.json`).  
- 12 publication figures for the **“regimes paper”** (`fig1_…`–`fig11_…`, `figS1_…`).

**Phase 6** is a *follow‑on* analysis focused on **stickiness and escape between regimes**, using *local CPU only* (no cloud/GPU assumptions) and reusing all existing embeddings and PH infrastructure.

---

## Objectives

1. **Regime switching**: Quantify how often individuals move between regimes over overlapping 10‑year windows (especially escape from Low‑Income Churn / Inactive Low).  
2. **Phase topology**: Test whether the *ordering of career phases* adds additional topological structure beyond state composition (phase‑order shuffle null).  
3. **Escape archetypes**: Identify a small number of typical “escape paths” for those who move from disadvantaged to advantaged regimes.

No changes are made to the core 9‑state space or existing null models. This is an extension, not a replacement, of the Phase 1–5 analysis.

---

## Files and Modules Reused

Phase 6 agents MUST rely on the following existing artefacts:

- **Embeddings / regimes**  
  - `results/trajectory_tda_integration/02_embedding.json` – PCA/embedding metadata.  
  - `results/trajectory_tda_integration/embeddings.npy` – PCA‑20D embeddings (full sample).  
  - `results/trajectory_tda_integration/05_analysis.json` – regime GMM parameters and regime profiles (k=7).  

- **Topology / nulls**  
  - `results/trajectory_tda_integration/03_ph.json` – PH summaries for trajectories.  
  - `results/trajectory_tda_integration/03_ph_diagrams.json` – raw birth/death pairs for VR (H₀, H₁).  
  - `results/trajectory_tda_integration/04_nulls.json` – order/label/cohort/Markov‑1 nulls (n up to 500).  
  - `results/trajectory_tda_integration/04_nulls_markov2.json` – Markov‑2 nulls (n=500).

- **Stratification / viz / scripts**  
  - `results/trajectory_tda_integration/06_stratified.json` – gender, cohort, NS‑SEC stratified PH and Wasserstein.  
  - `trajectory_tda/scripts/run_pipeline.py` – CLI orchestrator (Phase 1–5).  
  - `trajectory_tda/analysis/regime_discovery.py` – GMM regimes (already trained/used).  
  - `trajectory_tda/analysis/group_comparison.py` – used in Phase 3 stratification.  
  - `trajectory_tda/topology/trajectory_ph.py` – VR PH computation.  
  - `trajectory_tda/topology/vectorisation.py` – Betti curves, landscapes, Wasserstein.  
  - `trajectory_tda/viz/paper_figures.py` – Phase 1–5 figures.

Phase 6 must **not** recompute the global regimes or base PH unless absolutely necessary; it builds on those results.

---

## Step 6.1 – Overlapping Windows and Regime Sequences

**Goal:** Construct regime time-series per individual using overlapping 10‑year windows.

### 6.1.1 Implement windowing in `trajectory_builder.py`

- Add CLI options:

  ```bash
  --window-years 10   # window length
  --window-step 5     # step between windows (years)
  --windows-enabled   # flag to enable overlapping window construction
  ```

- For each `pidp`:

  1. Extract the sorted sequence of 9‑state life‑course codes (as in Phase 1 building 27,280 trajectories from BHPS/USoc).  
  2. Slide a window of `window-years` across the sequence in steps of `window-step` years.  
  3. Keep only windows with ≥`window-years` valid (non-gap) observations.  
  4. Record for each window:

     ```json
     {
       "pidp": ...,
       "window_id": ...,
       "start_year": ...,
       "end_year": ...,
       "states": ["EL","EL",...],
       "age_start": ...,
       "age_end": ...
     }
     ```

- Output: `results/trajectory_tda_phase6/01_windows.json`.

### 6.1.2 Reuse embedding + GMM to assign regimes

- Load PCA transform and GMM from the original Phase 1–5 checkpoints (or from `02_embedding.json` / `05_analysis.json`).  
- For each window in `01_windows.json`:

  1. Build the n‑gram (unigram+bigram) vector exactly as for full trajectories.  
  2. Transform with PCA‑20D.  
  3. Apply the fitted GMM to get a regime label (0–6).

- Save window-level embeddings and labels:

  - `results/trajectory_tda_phase6/02_window_embeddings.npy`  
  - `results/trajectory_tda_phase6/02_window_regimes.json` (maps window → regime, includes age/years).

### 6.1.3 Build regime sequences and transition matrices

- For each `pidp`, sort windows by time and construct a regime sequence:

  ```python
  sequence = [r1, r2, ..., rk]  # 7-regime labels
  ```

- Compute:

  - Empirical transition matrix \(P(r_{t+1} \mid r_t)\) across windows.  
  - For individuals whose **first** window is:

    - Low‑Income Churn  
    - Inactive Low  

    compute:

    - Probability of reaching Secure EH or Employed Mid within the next 1 window and within 2 windows.  
    - Distribution of path lengths (number of windows) to first “good” regime.

- Save:

  - `results/trajectory_tda_phase6/03_regime_sequences.json`  
  - `results/trajectory_tda_phase6/03_regime_transitions.json`

**Verification:** Basic counts (e.g. how many individuals have multiple windows, distribution of sequence lengths) logged in the JSON.

---

## Step 6.2 – PH on Career Phase Space

**Goal:** Test whether the *ordering* of windows across the life course creates additional topological structure, beyond the composition of windows alone.

### 6.2.1 Construct phase embedding dataset

- Use `02_window_embeddings.npy` (20D vectors).  
- Optionally filter to:

  - All windows from individuals who ever visit Low‑Income Churn or Inactive Low,  
  - Plus a stratified random sample of other windows,  
  to keep the total number of windows manageable (e.g. ≤ 50–70k).

- Save the filtered embedding array as `results/trajectory_tda_phase6/04_phase_embeddings.npy`.

### 6.2.2 Compute PH (VR via existing pipeline)

- Implement a new function `compute_phase_ph()` in `trajectory_tda/topology/trajectory_ph.py` that:

  - Takes `04_phase_embeddings.npy`.  
  - Selects `n_landmarks` (e.g. 2,500–3,000) via MaxMin (same method as Phase 1–5).  
  - Computes VR PH (H₀, H₁) using Ripser.  
  - Saves:

    - `results/trajectory_tda_phase6/05_phase_ph.json` – PH summaries.  
    - `results/trajectory_tda_phase6/05_phase_ph_diagrams.json` – raw diagrams (birth/death pairs).

### 6.2.3 Phase-order shuffle nulls

- New null model: **within-person phase shuffle**.

  For each permutation \(b=1,\dots,B\) (B≈200):

  - For each `pidp`, randomly permute the order of its windows.  
  - Rebuild a shuffled embedding array (same points, same counts, different “person–time” mapping).  
  - Re-run PH (or at least vectorised summaries) using the same landmark set, and compute:

    - Total persistence (H₀, H₁).  
    - Optionally Betti curves.

- Implement this in `trajectory_tda/topology/permutation_nulls.py` as `phase_order_shuffle`, reusing the joblib Parallel logic from Phase 1–5.

- Save:

  - `results/trajectory_tda_phase6/06_phase_nulls.json` – full null distributions and p‑values.

**Key comparison:** Is phase H₀/H₁ for the observed ordering significantly different from phase‑order shuffled nulls?

---

## Step 6.3 – Escape Path Archetypes

**Goal:** Identify a small number of canonical patterns by which individuals escape from Low‑Income Churn / Inactive Low to Secure EH / Employed Mid.

### 6.3.1 Select escaper cohort

- From `03_regime_sequences.json`, select individuals whose:

  - First window is Low‑Income Churn or Inactive Low, and  
  - Some later window is Secure EH or Employed Mid.

- For each such individual, extract the regime sequence up to the first “good” regime:

  ```python
  path = [r_start, r2, ..., r_escape]
  ```

### 6.3.2 Define escape features

For each path, compute:

- `path_length`: number of windows until first good regime.  
- `n_regime_changes`: count of regime changes (r_t ≠ r_{t+1}).  
- `%unemployment_windows`: share of windows in regimes with high unemployment share (e.g. Mixed Churn, Low‑Income Churn).  
- `%inactive_windows`: share in Inactive Low / High‑Income Inactive / Emp‑Inactive Mix.  
- `min_income_grade`: lowest income level visited (based on regime profiles).  
- `age_at_escape`: age at `r_escape` window start (if available).

Save as:

- `results/trajectory_tda_phase6/07_escape_features.csv`.

### 6.3.3 Cluster escape paths (TDA-light)

- In `trajectory_tda/analysis/escape_paths.py`:

  - Cluster the feature vectors using k‑means or hierarchical clustering, trying k=2–5 and picking k based on interpretability / silhouette.  
  - Compute descriptive stats per cluster (mean path length, composition, age at escape).  
  - Optionally, compute simple 1D persistent homology on the feature vectors to see if multiple “lobes” exist; this is purely exploratory and not required.

- Output: `results/trajectory_tda_phase6/08_escape_clusters.json`.

---

## Step 6.4 – Minimal Visualisation for Phase 6

New figures (optional for Paper 1, core for a follow‑on Paper 2):

1. **Regime switching heatmap**: Window‑to‑window transition matrix \(P(r_{t+1} \mid r_t)\).  
2. **Escape probability plots**: Probability of ever reaching Secure EH / Employed Mid from Low‑Income Churn / Inactive Low by cohort / gender / NS‑SEC.  
3. **Phase PH figure**: H₀/H₁ PDs for phase embeddings + phase‑order null violin plots.  
4. **Escape archetype panel**: barplots or Sankey diagrams of typical paths per cluster.

These can be implemented in a new module:

- `trajectory_tda/viz/phase6_figures.py`

reusing the style and constants from `trajectory_tda/viz/paper_figures.py`.

---

## Out of Scope for Phase 6

- No change to the 9‑state discretisation.  
- No Witness complexes (dropped earlier due to combinatorial explosion; VR with landmarks is sufficient for H₀/H₁).  
- No alternative PH backends (Ripser/Gudhi stack from Phase 1–5 remains).  
- No GPU or cloud compute assumptions (all runs may be slow but should complete on a multi‑core local CPU with careful landmarking and, if needed, subsampling of windows).

---

## Verification Checklist (Phase 6)

1. `01_windows.json` contains overlapping 10‑year windows with correct counts and age/year metadata.  
2. `02_window_regimes.json` regime labels are consistent with Phase 1–5 GMM (e.g. distribution of regimes similar to original, up to sampling differences).  
3. `03_regime_transitions.json` yields a valid stochastic matrix, plus escape probabilities from Low‑Income Churn / Inactive Low are non‑trivial but <50%.  
4. `05_phase_ph.json` + `06_phase_nulls.json` compute successfully; p‑values for phase‑order nulls are interpretable (significant or clearly non‑significant).  
5. `07_escape_features.csv` + `08_escape_clusters.json` produce 2–5 reasonably distinct escape archetypes.  
6. All Phase 6 scripts run using **existing** embeddings/PCA/GMM; no retraining unless explicitly requested.

---

## Relationship to Phase 1–5 Paper

Phase 6 results are **not required** for the current “regimes + nulls + stratification” manuscript. They are intended for:

- A follow‑on methodological/policy paper on **regime stickiness and escape**, and/or  
- A future extension of the current paper’s Discussion/Future Work section.

Agents working on Phase 6 should **not** modify Phase 1–5 artefacts in place; all new outputs live under `results/trajectory_tda_phase6/` and `trajectory_tda/analysis/escape_paths.py` / `trajectory_tda/viz/phase6_figures.py`.

```

---