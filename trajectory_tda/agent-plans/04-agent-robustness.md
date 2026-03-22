# Agent 4: Robustness Code

**Core plan reference:** `trajectory_tda/plan-fourthDraftMajorRevision.md` — Phase 5A, 5B, 5C
**Orchestration:** `trajectory_tda/agent-plans/00-orchestration.md`

## Scope

Three robustness extensions: non-overlapping window analysis, embedding sensitivity (trigrams + dimensionality), and per-regime stratified Markov null.

## Files You Own (EXCLUSIVE WRITE)

- `trajectory_tda/embedding/ngram_embed.py` (EDIT — add trigrams)
- `trajectory_tda/topology/permutation_nulls.py` (EDIT — add stratified Markov)
- `trajectory_tda/scripts/run_nonoverlapping_windows.py` (NEW)
- `trajectory_tda/scripts/run_embedding_sensitivity.py` (NEW)

**DO NOT edit any other existing files.** You may READ `trajectory_tda/data/trajectory_builder.py` (Agent 1 owns it) — import `build_windows()` but do not modify it.

## Task A: Non-Overlapping Windows Script (Phase 5A, Concern #6)

**Create:** `trajectory_tda/scripts/run_nonoverlapping_windows.py`

**Purpose:** Run the window analysis with non-overlapping 5-year windows as a sensitivity check on the existing 10-year overlapping (5-year step) results.

**Algorithm:**
1. Load existing trajectories (from pipeline cache or rebuild)
2. Call `build_windows(trajectories, metadata, window_years=5, window_step=5, min_valid=3)`
   - Note: `build_windows()` already supports these parameters — no code change needed
3. Embed window states via `ngram_embed()`
4. Assign regimes (use existing GMM model or refit on windows)
5. Compute transition matrix (regime-to-regime across consecutive non-overlapping windows)
6. Compute escape rates from disadvantaged regimes

**Additionally — Overlap Baseline Calculation:**

Compute the analytical expected self-transition rate under the overlap artefact:
- In the overlapping design (10-year windows, 5-year step), consecutive windows share 5/10 = 50% of their years (not 9/10 — that's for a 1-year step)
- Actually verify the exact overlap: if `window_years=10, window_step=5`, then consecutive windows overlap by `window_years - window_step = 5` years, sharing 5/10 = 50% of years
- Under random assignment: if 50% of state observations are shared, the expected same-regime probability depends on how much the regime assignment is driven by shared vs unshared states
- Empirical approach: for each pair of consecutive windows, compute the fraction of shared years, then compute the correlation between regime assignments as a function of shared fraction

**Output:** JSON with:
- Non-overlapping transition matrix (7×7)
- Overlapping transition matrix (existing, for comparison)
- Escape rates: overlapping vs non-overlapping
- Per-regime self-transition rates: overlapping vs non-overlapping
- Overlap baseline analysis

**Note on trajectory_builder.py:** You import from this file but Agent 1 is editing it (adding `survey_era` column). Agent 1's edit is additive and does not change the `build_windows()` API. However, after Agent 1 is done, verify your imports still work. If Agent 1 has not yet committed, you can write and test your script against the current (unmodified) version — it will be forward-compatible.

## Task B: Embedding Sensitivity (Phase 5B, Concern #8)

### Step 1: Add Trigram Support to ngram_embed.py

**Edit:** `trajectory_tda/embedding/ngram_embed.py`

Add trigram computation alongside existing unigrams and bigrams:
- New parameter: `include_trigrams=False` (default preserves backward compatibility)
- Trigram dimensions: 9³ = 729 (all ordered triples of states)
- When `include_trigrams=True`: output vector = unigrams (9) + bigrams (81) + trigrams (729) = 819 dimensions pre-PCA
- Trigram computation: for each trajectory, count all consecutive state triples, normalise by (len-2)
- If `tfidf=True`, apply TF-IDF weighting to trigrams as well

**Do not change existing default behaviour.** All existing calls with `include_trigrams` unspecified must produce identical output.

### Step 2: Create Sensitivity Script

**Create:** `trajectory_tda/scripts/run_embedding_sensitivity.py`

**Sensitivity grid:**

| Config | N-grams | Weighting | PCA dim |
|--------|---------|-----------|---------|
| 1 (baseline) | bigram | TF | 20 |
| 2 | bigram | TF-IDF | 20 |
| 3 | trigram | TF | 20 |
| 4 | trigram | TF-IDF | 20 |
| 5 | bigram | TF | 10 |
| 6 | bigram | TF | 30 |

For each configuration:
1. Compute embedding with specified parameters
2. Run VR PH at L=5000
3. Run order-shuffle null (n=100)
4. Record: H₀ total persistence, H₁ total persistence, order-shuffle H₀ p-value, H₁ p-value, number of PCA components explaining 90% variance

**Output:** JSON with per-configuration results table

### Trigram–Markov-2 Interpretive Note

Include in output metadata a note for Agent 5 (Paper):

> The trigram embedding directly encodes three-state transition memory. If trigram-based topology differs significantly from bigram-based topology (e.g., different total persistence or different null-model p-values), this indicates that third-order sequential structure is geometrically detectable in the point cloud. This has implications for the Markov-2 null: a trigram embedding that produces substantially different PH would suggest the Markov-2 null is testing against a richer structural hypothesis embedded in the representation itself.

## Task C: Per-Regime Stratified Markov Null (Phase 5C, Concern #9) — RECOMMENDED

**Edit:** `trajectory_tda/topology/permutation_nulls.py`

**Purpose:** Add a stratified Markov-1 null that estimates transition matrices separately per GMM regime, then generates synthetic trajectories per stratum.

**Implementation:**

Add a new function (do not modify existing functions):

```python
def _stratified_markov_shuffle(trajectories, regime_labels, markov_order=1):
    """Generate synthetic trajectories using per-regime Markov chains.
    
    For each regime k:
      1. Select trajectories assigned to regime k
      2. Estimate Markov-order transition matrix from those trajectories only
      3. Generate synthetic trajectories of same lengths using regime-specific chain
    
    Concatenate all regime-specific synthetic trajectories.
    Return re-embedded synthetic point cloud.
    """
```

**Key design decisions:**
- Regime labels come from GMM assignments on the observed data
- Each regime's transition matrix is estimated from trajectories assigned to that regime
- Synthetic trajectory lengths match original trajectory lengths within each regime
- Initial state distribution is estimated per-regime
- Fallback: if a regime has too few trajectories (< 30) for reliable estimation, use the global transition matrix for that regime and log a warning

**Integration:** Add `"stratified_markov1"` as a new null type in the main null dispatch function. It should be callable via the same interface as existing nulls.

**Output format:** Same as existing Markov-1 null (observed persistence, null distribution, p-values) but labelled as `stratified_markov1`.

**Run:** After implementing, run the stratified Markov-1 null with n=500 permutations at L=5000. Save results.

## Handoff Summary (produce when complete)

Report to Agent 5 (Paper):

**From Task A (non-overlapping windows):**
- Non-overlapping transition matrix (or key diagonal entries)
- Escape rates: overlapping vs non-overlapping
- Self-transition rates by regime: overlapping vs non-overlapping
- Overlap baseline analysis result

**From Task B (embedding sensitivity):**
- 6-row sensitivity table: config, H₀ total, H₁ total, OS H₀ p, OS H₁ p
- Whether results are qualitatively stable across configurations
- Whether trigram differs meaningfully from bigram (and Markov-2 implications)

**From Task C (stratified Markov):**
- Stratified Markov-1 p-values for H₀ and H₁
- Whether non-rejection holds (strengthens paper) or rejection occurs (paper must qualify claims)
- Per-regime transition matrix summaries used in the stratified null

## Verification

- Task B step 1: verify backward compatibility — run existing pipeline with default parameters, confirm identical output
- Task B step 2: verify all 6 configurations complete without errors
- Task C: verify that per-regime trajectory counts sum to total n; verify synthetic trajectory lengths match originals
- All tasks: `python -m pytest tests/ -v` (if tests exist for embedding/topology modules)
