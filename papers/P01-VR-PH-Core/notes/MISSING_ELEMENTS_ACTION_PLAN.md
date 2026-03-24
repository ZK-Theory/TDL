# Missing Elements Action Plan

Items that cannot be resolved by textual revision alone. Ordered by priority for publication readiness.

---

## Priority 1: Required Before Submission

### 1. OM/TraMineR Baseline Comparison
**What:** Run dynamic Hamming distance (Lesnard 2010) OM on all 27,280 trajectories using TraMineR. Cluster with Ward's, select k via silhouette. Compare to GMM regimes.
**Output:** ARI between OM and TDA regimes; regime-level profile correlation; Figure S2 (side-by-side profiles); Table S3 (comparison summary).
**Why critical:** Reviewers will ask "what does TDA add?" without a direct OM baseline. Both plans flagged this as highest priority.
**Section affected:** §3.7, §5.1, §6

### 2. Landmark Sensitivity (L = 2,500 / 5,000 / 8,000)
**What:** Recompute PH at L = 2,500 and L = 8,000. Report total/max H₀/H₁ persistence ± std dev. Re-run order-shuffle and Markov-1 nulls (n=100 each is sufficient for stability check).
**Output:** Appendix B table showing persistence statistics and p-values across L values.
**Why critical:** Single landmark count without sensitivity is a methodological gap.
**Section affected:** §3.3, Appendix B, §5.5

### 3. Wasserstein FDR Correction
**What:** Apply Benjamini-Hochberg correction to all 168 cohort-specific tests and the gender/NS-SEC tests. Report both raw and corrected counts.
**Output:** Updated §4.6 numbers; revised Table 4.
**Why critical:** 168 tests at p < 0.05 without correction will draw reviewer criticism.
**Section affected:** §4.6, §6

### 4. Phase-Ordering Null: Increase Permutations
**What:** Increase from n = 20 to n ≥ 200 (ideally 500). Re-report p-values with confidence intervals.
**Output:** Updated §4.5 results; updated Figure 14.
**Why critical:** n = 20 is too coarse for any publication claim, even "exploratory."
**Section affected:** §4.5

---

## Priority 2: Strongly Recommended

### 5. Age-Stratified Persistence / Escape Rates
**What:** Separate Inactive Low regime into under-60 and over-60 (or use actual retirement age). Compute escape rates for working-age disadvantaged only. Logistic regression on age at first window.
**Output:** Revised escape rate (raw vs. age-adjusted); discussion of lifecycle vs. inequality-driven persistence.
**Why critical:** Without this, the 97% self-transition and 5.6% escape rate are confounded by retirement.
**Section affected:** §4.4.1, §5.4, §6

### 6. UMAP Robustness: Re-run Key Results
**What:** Under UMAP-16D embedding, re-run: (a) order-shuffle null (n=100), (b) Markov-1 null (n=100), (c) GMM k=7 regime profiles, (d) escape rates. Report whether substantive conclusions change.
**Output:** Updated §3.2 and §5.5; additional robustness row in Table S4.
**Why critical:** ARI = 0.31 between PCA and UMAP is low. Reviewers will ask if TDA results are embedding-dependent.
**Section affected:** §3.2, §5.5

### 7. GMM Bootstrap Stability
**What:** Resample 27,280 trajectories with replacement 200 times. Fit GMM k=7 each time. Compute mean ARI between bootstrap and full-sample assignments.
**Output:** ARI ± std (expect 0.85+); report in §3.5.
**Why critical:** k=7 selected by BIC on one sample. Bootstrap validates this isn't a fragile solution.
**Section affected:** §3.5, §5.5

### 8. H₀ Component–GMM Regime Overlap
**What:** At the filtration scale producing 7 H₀ components, map each GMM regime to its dominant H₀ component. Report overlap (e.g., fraction of each regime falling in a single component).
**Output:** Table S2.
**Why critical:** The paper claims H₀ components "guide" GMM but never quantifies this.
**Section affected:** §4.4

---

## Priority 3: Desirable / Future Extensions

### 9. Regional/Spatial Stratification ✔️ COMPLETED
**What:** Stratify by Government Office Region or NUTS2. Compute Wasserstein distances between regions. Even a preliminary 2-3 region comparison (London vs. North East) would strengthen the JEG positioning.
**Output:** Standalone analysis document: `results/GOR_REGIONAL_ANALYSIS.md`. Full 12-region analysis with global-shuffle permutation test (50 perms, L=1,000). 39/132 pairwise tests survive BH FDR correction. London significant against all 11 regions in both H0 and H1. Results kept separate from third draft pending decision on integration vs separate paper.
**Section affected:** §1.1, §5.4, §6

### 10. Pipeline Sensitivity Checks ✔️ COMPLETED
**What:** Vary minimum trajectory length (8, 10, 12 years), n-gram weighting (TF vs. TF-IDF), VR filtration threshold (50th, 75th, 90th percentile). Report which results are stable.
**Output:** `results/trajectory_tda_robustness/pipeline_sensitivity.json`. Threshold insensitive (ARI=0.970); min_years stable at 10/12yr (k=7), k=8 at 8yr; TF-IDF reshapes embedding (ARI=0.466). Third draft §5.4 updated with results.
**Section affected:** §5.4, §5.5

### 11. Markov Sparsity Reporting
**What:** Report the number of non-zero cells in the order-2 transition matrix (before and after Laplace smoothing). Report the effective number of parameters.
**Output:** 1-2 sentences in §3.4.
**Why important:** Reviewer may question whether order-2 Markov surrogates are well-specified with sparse data.
**Section affected:** §3.4

---

## Tracking

| # | Item | Priority | Status | Assigned |
|---|------|----------|--------|----------|
| 1 | OM/TraMineR baseline | P1 | **Completed** | §3.7, §5.1 — ARI = 0.26 at k=7; silhouette k=2: 0.223, k=7: 0.215; script `run_om_baseline.py`; results in `results/trajectory_tda_robustness/om_baseline/` |
| 2 | Landmark sensitivity | P1 | **Completed** | Appendix B — L=2,500/5,000/8,000; OS H₀ p<0.001 at all L; null n=50–100 per condition; script `run_landmark_sensitivity.py`; results in `results/trajectory_tda_robustness/landmark_sensitivity/` |
| 3 | Wasserstein FDR | P1 | **Completed** | §4.6 — 30/50 survive BH at q<0.05 (H₀: 16/25, H₁: 14/25); script `run_fdr_correction.py`; results in `results/trajectory_tda_robustness/fdr_correction_results.json` |
| 4 | Phase-ordering n increase | P1 | **Completed** | §4.5 — n=500; H₀ p=0.98 CI [0.968,0.992], H₁ p=0.542 CI [0.498,0.586]; script `run_phase_ordering.py`; results in `results/trajectory_tda_robustness/phase_ordering/` |
| 5 | Age-stratified persistence | P2 | **Completed** | §4.4.2, §5.4 — Working-age escape 17.8%, retirement 0.1%, retirement fraction 86.1%; logistic: age OR=0.898 (p<10⁻¹⁵⁰), female OR=0.438 (p<10⁻¹¹), pseudo-R²=0.327; module `age_stratified.py`; results in `results/trajectory_tda_priority2/p2_5_age_stratified.json` |
| 6 | UMAP robustness re-run | P2 | **Completed** | §3.2 — GMM at k=7: ARI=0.33 vs PCA. Order-shuffle H₀ p<0.001 (obs=3203.3, null=2373.0±323.3), H₁ p=1.00. Markov-1 omitted (computational cost; each UMAP perm requires fresh embedding fit, OOM at n_jobs=-1). Documented as limitation in §5.4. Module `run_priority2.py`; results in `results/trajectory_tda_priority2/` |
| 7 | GMM bootstrap stability | P2 | **Completed** | §3.5 — ARI = 0.646 ± 0.086, 95% CI [0.461, 0.795], n=200 bootstraps; module `gmm_bootstrap.py`; results in `results/trajectory_tda_priority2/p2_7_gmm_bootstrap.json` |
| 8 | H₀–GMM overlap | P2 | **Completed** | §4.4.1, Appendix A — ARI = 0.00004; 99.98% in one component; 6 singletons from R0; per-regime purity 99.8–100%; module `h0_gmm_overlap.py`; results in `results/trajectory_tda_priority2/p2_8_h0_gmm_overlap.json` |
| 9 | Regional stratification | P3 | Not started | |
| 10 | Pipeline sensitivity | P3 | Not started | |
| 11 | Markov sparsity reporting | P3 | **Completed** | §3.4 — 717/729 (98.4%) non-zero pre-smoothing; 81/81 conditioning pairs active; ~648 effective free parameters. Updated in third_draft.md |

**P1 status:** All 4 items completed. All values verified against result files and populated in third_draft.md.
**P2 status:** All 4 items completed (items 5, 6, 7, 8). Item 6 UMAP robustness: order-shuffle completed (n=100), Markov-1 omitted due to computational cost (documented as explicit limitation). All [RESULT] placeholders removed from third_draft.md.
**P3 status:** Item 11 (Markov sparsity) completed. Items 9–10 remain not started.
