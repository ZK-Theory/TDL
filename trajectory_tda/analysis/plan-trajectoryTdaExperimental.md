## Plan: Trajectory TDA Publication Experimental Pipeline

Transform existing `trajectory_tda` pipeline results (27,280 UK life-course trajectories, 7 mobility regimes, significant order-shuffle null rejection, 1,840 H₁ cycles) into a publication-ready paper with robust statistical validation, stratified analyses, and 10–12 publication-quality figures. Four critical gaps must be addressed: (1) insufficient permutation count (n=10), (2) zero visualization infrastructure, (3) absent stratified group comparisons, and (4) unexplored Markov memory structure (both H₀ borderline at order-1 and untested order-2 for H₁ cycles).

---

### Phase 1: Statistical Robustness — Null Model Validation *(blocking)*

**Step 1.1 — Rerun order_shuffle + Markov(order-1) nulls at n=500**
- Load existing embeddings from `results/trajectory_tda_integration/embeddings.npy` to avoid re-embedding
- Use `permutation_nulls.py` with `joblib.Parallel(n_jobs=-1)` — infrastructure already exists
- **Critical:** Save raw null distribution arrays (not just summary stats) for Betti curve envelope plotting
- Output: Updated `results/trajectory_tda_integration/04_nulls.json` with refined p-values
- **Markov H₀ focus:** Current p=0.1 at n=10 is unresolvable. At n=500 this will either:
  - **Resolve significant (p < 0.05):** Second publishable claim — "topological structure exceeds first-order Markov memory"
  - **Resolve non-significant (p > 0.05):** Report as "regime structure consistent with first-order Markov for global components" — still informative, constrains the generating process

**Step 1.2 — Rerun label_shuffle + cohort_shuffle at n=100** *(parallel with 1.1)*
- Confirm non-significance (currently both p=0.6)
- Output: Complete null table (4 models × H₀/H₁)

**Step 1.3 — Markov order-2 null battery** *(new, depends on 1.1)*
- `permutation_nulls.py` already implements `markov_order=2` (second-order conditional: P(s_{t+1} | s_t, s_{t-1})) with first-order fallback for unseen bigrams
- Run at n=500 for **both H₀ and H₁**
- **H₁ rationale:** Order-shuffle H₁ was non-significant (p=0.4), meaning the 1,840 persistent loops may reflect state frequencies alone. But Markov-2 is a stronger null — if H₁ Markov-2 is significant, cycles have genuine higher-order memory beyond 2-step transitions
- **H₀ rationale:** If H₀ Markov-1 turns significant but H₀ Markov-2 does not, regime structure is captured by 2-step memory — this pins down the complexity of the generating process
- Add `--markov-order` CLI flag to `run_pipeline.py` (currently hardcoded to 1)
- Output: `04_nulls_markov2.json` — saved separately to preserve original results

**Step 1.4 — Interpret Markov ladder**
Construct a "Markov memory ladder" table comparing:

| Null | H₀ p-value | H₁ p-value | Interpretation |
|------|-----------|-----------|----------------|
| Order shuffle (memoryless) | p=0.0 | p=0.4 | Transition order matters for regimes, not cycles |
| Markov order-1 (n=500) | TBD | TBD | Does topology exceed 1-step memory? |
| Markov order-2 (n=500) | TBD | TBD | Does topology exceed 2-step memory? |

This table becomes a core paper contribution (Figure 8 extended) — it characterises the *memory depth* of life-course topology.

**Step 1.5 — Save raw persistence diagrams**
- Current `results/trajectory_tda_integration/03_ph.json` only stores summary stats (total persistence, max, entropy) — no birth/death pairs
- Modify `trajectory_tda/topology/trajectory_ph.py` checkpoint to save raw (birth, death) arrays as `03_ph_diagrams.npy`
- Needed for persistence diagram plots (Figure 3) and Wasserstein computations

**Step 1.6 — Save Betti curves + trajectory exemplars**
- Call `vectorise_diagram()` from `trajectory_tda/topology/vectorisation.py` on observed + each null permutation
- After regime discovery, export top-5 trajectories per regime (closest to GMM centroid) — needed for Figure 1 heatmaps

**Verification:**
- Order-shuffle H₀ p-value remains < 0.01 at n=500; confidence interval ≤ ±0.02
- Markov-1 H₀ p-value resolves clearly (either < 0.05 or > 0.1 — not stuck in ambiguous 0.05–0.1 zone)
- Markov-2 results available for both H₀ and H₁ — even null results are publishable as they constrain the process

---

### Phase 2: Visualization Module *(parallel with Phase 1 compute)*

**Step 2.1 — Create `trajectory_tda/viz/` module**
- New files: `__init__.py`, `paper_figures.py`, `constants.py`
- Follow conventions from `poverty_tda/viz/ttk_plots.py` and `financial_tda/viz/ttk_plots.py`: Matplotlib, `figsize`/`title`/`save_path` signature, returns `Figure`
- Adhere to `poverty_tda/figures_specification.md`: PDF vector + PNG 300 DPI, full-width 190mm, perceptually uniform colormaps

**Step 2.2 — Implement 10 publication figures**

| # | Title | Type | Source Data | Paper Section |
|---|-------|------|-------------|---------------|
| **Fig 1** | Data Overview & Trajectory Heatmap | Panel: (A) sample flowchart 118k→27,280; (B) state-sequence heatmap, 5 exemplars/regime, 9-state categorical palette, x=year y=trajectory | `01_trajectories.json` + regime labels | §4.1 Data |
| **Fig 2** | Embedding Point Cloud | UMAP 2D projection of PCA-20D embeddings, colored by regime, convex hulls/density contours per regime, centroids labeled | `embeddings.npy` + regime labels | §4.2 Method |
| **Fig 3** | Persistence Diagrams (H₀ + H₁) | Panel: (A) H₀ birth-vs-death scatter + diagonal; (B) H₁ with top 50 features highlighted and significance threshold | Raw diagrams (Step 1.3) | §5.2 Results |
| **Fig 4** | Betti Curves: Observed vs Null Envelopes | Panel: (A) H₀ observed vs order-shuffle null (mean ± 2σ shaded band); (B) H₁ vs Markov-1 null | Raw null distributions (Step 1.1) | §5.3 Validation |
| **Fig 5** | Regime Profiles Table-as-Figure | Heatmap or grouped bar: 7 regimes × (employment, unemployment, inactivity, low/mid/high income, stability, transition rate) with N and % as row headers | `05_analysis.json` `regimes.profiles` | §5.4 Regimes |
| **Fig 6** | Stability–Income Correlation | Scatter: stability (x) vs high_income_rate (y), sized by n_members, colored by regime; annotate Regime 1 "Secure EH" and Regime 6 "Low-Income Churn"; Pearson r + p | `05_analysis.json` | §5.4 Regimes |
| **Fig 7** | Cycle/Trap Analysis | Panel: (A) top 10 persistent H₁ loops as transition diagrams; (B) cycle length distribution histogram for 1,840 loops | `cycle_detection.py` output | §5.2 Results |
| **Fig 8** | Null Model Summary Table (Markov Ladder) | Table-as-figure: 5 nulls (4 original + Markov-2) × (H₀ obs, null mean, null std, p, sig) + (H₁ same); bold significant; include effect size z-scores; rows ordered by null strength | `04_nulls.json` + `04_nulls_markov2.json` | §5.3 Validation |
| **Fig 9** | Markov Memory Depth Comparison | Panel: (A) H₀ total persistence distributions for observed vs Markov-1 vs Markov-2 (overlapping histograms or violin plots); (B) Same for H₁ — visually shows whether higher-order memory adds explanatory power | Raw null distributions (Steps 1.1 + 1.3) | §5.3 Validation |
| **Fig 10** | Wasserstein Distance by Social Origin | Heatmap: pairwise Wasserstein between parental NS-SEC strata; annotated with permutation p-values | `group_comparison.py` output | §5.5 Stratification |
| **Fig 11** | Gender Persistence Landscape Overlay | L₁ landscapes Male vs Female on same axes, shaded difference region, KS test p-value | `vectorisation.py` per gender | §5.5 Stratification |
| **Fig S1** | UMAP Embedding Sensitivity Check *(supplementary)* | Same as Fig 2 but with UMAP-16D embedding instead of PCA-20D; verify regime structure is qualitatively preserved | `ngram_embed(umap_dim=16)` + regime labels | Appendix |

**Step 2.3 — Define shared constants**
- 9-state categorical palette: EL/EM/EH = greens, UL/UM/UH = reds/oranges, IL/IM/IH = blues
- `plt.rcParams`: font 10pt, axes 11pt, title 12pt
- Output directory: `figures/trajectory_tda/`
- Dual save: PDF + PNG

**Verification:** All 11 main + 1 supplementary figures render from checkpoint data; spot-check regime values against JSON

---

### Phase 3: Stratified Group Comparisons *(depends on Phase 1)*

**Step 3.1 — Wire `group_comparison.py` into pipeline**
- `trajectory_tda/analysis/group_comparison.py` exists but is NOT called from `trajectory_tda/scripts/run_pipeline.py`
- Add `--stratify` CLI flag accepting covariate names from trajectory metadata
- Covariates available: `parental_nse`, `gender`, `cohort_decade`

**Step 3.2 — Run three stratified analyses**
- **Parental NS-SEC**: Professional/Managerial vs Routine/Manual → separate PH → Wasserstein + permutation p-value
- **Gender**: Male vs Female → test H₁ differences (care penalty hypothesis: women's loops longer?)
- **Cohort decade**: 1950s/1960s/1970s/1980s → secular change in trap structure

**Step 3.3 — Generate Figures 10 + 11** (see Phase 2 table)

**Verification:** At least 2 of 3 stratifications show significant Wasserstein difference (p < 0.05)

---

### Phase 4: Pipeline Modifications *(supports Phases 1–3)*

**Step 4.1** — Modify `trajectory_tda/topology/trajectory_ph.py` to return + checkpoint raw birth/death pair arrays

**Step 4.2** — Modify `trajectory_tda/scripts/run_pipeline.py` to:
- Save raw null distribution arrays alongside summary stats
- Save trajectory exemplars per regime (5 closest to centroid)
- Add `--stratify` flag calling `group_comparison.compare_groups()`
- Add `--markov-order` CLI flag (default 1) passed through to `permutation_nulls.py`

**Step 4.3** — Call `vectorise_diagram()` in pipeline and save Betti curve arrays

**Step 4.4** — UMAP sensitivity embedding
- `ngram_embed()` already supports `umap_dim` parameter
- Re-embed with `umap_dim=16` → save as `embeddings_umap16.npy`
- Re-run regime discovery on UMAP embeddings → compare cluster assignments (ARI vs PCA regimes)
- Generate Figure S1 (supplementary) — if regime structure is qualitatively preserved, validates PCA choice

---

### Phase 5: Paper Outline *(parallel with Phases 2–3)*

Following `poverty_tda/paper_outline.md` conventions for Journal of Economic Geography (~9,000–10,000 words):

1. **Abstract** (250 words) — 27k trajectories, TDA on UK life-course, 7 regimes, order-shuffle significance, Markov memory characterisation, poverty trap cycles
2. **Introduction** (1,800 words) — UK mobility crisis, gap in life-course methodology, TDA contribution, Markov memory question
3. **Literature Review** (2,200 words) — sequence analysis limitations, TDA foundations, poverty trap theory, Markov chains in life-course research
4. **Methodology** (2,000 words) — BHPS/USoc 9-state space, n-gram + PCA, maxmin VR PH, 5 null models (4 original + Markov-2), GMM regimes
5. **Results** (2,400 words) — descriptive stats, topological structure, null validation including Markov memory ladder, regime profiles, H₁ cycle analysis (with honest reporting of order-shuffle H₁ non-significance), stratified comparisons
6. **Discussion** (1,500 words) — trap identification, Markov memory depth implications, policy implications, comparison to optimal matching / sequence analysis, limitations of H₁ interpretation
7. **Conclusion** (500 words) — summary, limitations, future work (family dimension, bifiltration, higher-order Markov)

---

### Relevant Files

**Existing pipeline (reuse)**
- `trajectory_tda/scripts/run_pipeline.py` — 6-stage CLI orchestrator with JSON checkpointing
- `trajectory_tda/topology/permutation_nulls.py` — 4 null models, joblib-parallelised
- `trajectory_tda/topology/vectorisation.py` — `persistence_landscape()`, `persistence_image()`, `wasserstein_distance()`
- `trajectory_tda/analysis/regime_discovery.py` — GMM + BIC → regime profiles
- `trajectory_tda/analysis/cycle_detection.py` — H₁ loop extraction
- `trajectory_tda/analysis/group_comparison.py` — `compare_groups()` (NOT yet wired to pipeline)

**Results (data for figures)**
- `results/trajectory_tda_integration/` — all 7 checkpoint files (`01_trajectories.json`, `02_embedding.json`, `embeddings.npy`, `03_ph.json`, `04_nulls.json`, `05_analysis.json`, `results_full.json`)

**To create**
- `trajectory_tda/viz/__init__.py`
- `trajectory_tda/viz/paper_figures.py`
- `trajectory_tda/viz/constants.py`
- `figures/trajectory_tda/` (output directory)
- `trajectory_tda/paper_outline.md`
- `results/trajectory_tda_integration/04_nulls_markov2.json` (Markov order-2 results)
- `results/trajectory_tda_integration/03_ph_diagrams.npy` (raw persistence diagrams)
- `results/trajectory_tda_integration/embeddings_umap16.npy` (UMAP sensitivity embedding)

**To modify**
- `trajectory_tda/scripts/run_pipeline.py` — add `--stratify` flag, `--markov-order` flag, raw checkpointing
- `trajectory_tda/topology/trajectory_ph.py` — raw diagram export

---

### Verification

1. Order-shuffle H₀ p < 0.01 at n=500 permutations
2. Markov-1 H₀ p-value resolves unambiguously (< 0.05 or > 0.1)
3. Markov-2 null results computed for both H₀ and H₁ at n=500
4. All 11 main + 1 supplementary figures render from checkpoint data without errors
5. Full pipeline re-runnable from CLI with `--checkpoint` flag producing identical results
6. PDF export at 190mm width renders clean in LaTeX
7. At least 2/3 stratifications show significant group differences (Wasserstein p < 0.05)
8. Every figure maps to a specific paper section — no orphans
9. UMAP regime assignments show ARI > 0.3 and qualitative macro-regime stability vs PCA assignments (embedding robustness); deviations discussed in Limitations

---

### Decisions

- **PH method:** maxmin VR only — witness complex caused memory explosion at 27k scale (documented in `trajectory_tda/antigravity docs/task.md`)
- **Regime count:** K=7 (BIC-selected) — final unless stratified analysis reveals sub-structure
- **Null targets:** n=500 for order_shuffle/Markov-1/Markov-2; n=100 for label/cohort (confirmation only)
- **Markov investigation:** Both order-1 and order-2 at full permutation count — this is a first-class research question, not a sensitivity check
- **Scope exclusions:** Family 27-state dimension, autoencoder embedding, multi-parameter PH, ABM simulation — all deferred to Paper 2/3
- **Journal target:** Journal of Economic Geography

---

### Contingency Matrix: Interpreting Markov Results

The Markov null results determine the paper's framing. All outcomes are publishable:

| Markov-1 H₀ | Markov-2 H₀ | Markov-2 H₁ | Paper Framing |
|-------------|-------------|-------------|---------------|
| **p < 0.05** | **p < 0.05** | **p < 0.05** | **Strongest:** Topology captures higher-order memory in both regimes and cycles; life-course complexity exceeds 2-step Markov |
| **p < 0.05** | **p < 0.05** | p > 0.05 | Regime structure has deep memory; cycles are consistent with 2-step dynamics (focus paper on regime novelty) |
| **p < 0.05** | p > 0.05 | any | Topology exceeds memoryless but is captured by 2-step memory — pins down generating process complexity |
| p > 0.05 | p > 0.05 | any | Regime structure is first-order Markov; H₀ signal comes purely from temporal ordering (order-shuffle) not memory depth. Still novel: "TDA detects Markov structure that sequence analysis misses" |

**H₁ cycle interpretation** (regardless of Markov outcome):
- Order-shuffle H₁ p=0.4 means cycles arise from state frequencies, not transition order
- If Markov-2 H₁ also non-significant: report honestly, focus novelty on H₀ regimes
- If Markov-2 H₁ significant: cycles have genuine memory structure beyond what random transitions produce — strong trap evidence
