# P01-A v1 Reviewer-Response Plan

**Drafted:** 2026-05-01
**Target draft to revise:** [v1-2026-04.md](../drafts/v1-2026-04.md)
**Reviewer:** External TDA methodological reviewer (round 0, pre-submission)
**Status:** Planning only — no code changes or revisions executed.

---

## 0. Document Purpose

The reviewer raised nine numbered issues (two **High**, four **Medium**, three **Low–Medium/Low**) plus several embedded sub-points. This document is the master plan to address every one of them — fully and without exception — before producing v2.

For each issue we record: (i) what the reviewer said, (ii) the current state in the v1 draft and the codebase / results store, (iii) whether the gap is **prose-only**, **needs new computation**, or **both**, (iv) the concrete strategy to close it, (v) the artefacts and locations expected, and (vi) a verification check that confirms the issue is closed.

A consolidated work list with sequencing, blocking dependencies, and resource estimates is given in §11. Acceptance criteria for v2 are in §12.

This plan is deliberately exhaustive. Every reviewer claim — including secondary observations buried inside larger paragraphs — is itemised below so that nothing is silently dropped.

---

## 1. ISSUE H1 — Landmark count inconsistency (5,000 for total persistence vs 2,000 for Wasserstein)

### 1.1 Reviewer claim

> "Using different landmark counts for different test statistics on the same data means the two results — total persistence (p = 1.000) vs. W₂ (p = 0.002) — are not directly comparable. […] 2,000 vs. 5,000 landmarks can yield qualitatively different witness-complex approximations at filtration thresholds in high-dimensional spaces."

The reviewer correctly identifies this as **High severity** because it offers an alternative non-substantive explanation for the central methodological claim of the paper (the test-statistic discrepancy).

### 1.2 Current state

- **v1 draft §3.2:** "5,000 landmarks for total-persistence tests, 2,000 for Wasserstein tests" — stated without justification.
- **Computational-Log (vault, 2026-03-24):** explicitly attributes the choice to W2 cost: *"L = 2,000 chosen for Wasserstein tests (vs L = 5,000 for total-persistence tests) due to computational cost of per-null Wasserstein distance computation."*
- **Existing robustness data:** `results/trajectory_tda_robustness/landmark_sensitivity/` contains `ph_L{2500,5000,8000}.json`, `nulls_markov1_L{2500,5000,8000}.json`, `nulls_order_shuffle_L{2500,5000,8000}.json`, `nulls_markov2_L5000.json`, `nulls_label_shuffle_L5000.json`, `nulls_cohort_shuffle_L5000.json` — but `landmark_sensitivity_summary.json` only contains a single L=8000 row and reports only **total-persistence** statistics (no W₂ at any L).
- **Gap:** there is no W₂ run at L=5,000 (or anywhere except the legacy L=2,000 run), so the central claim cannot currently be defended against the landmark-count confound.

### 1.3 Classification

**Both** — needs new computation (W₂ at matched L) AND prose changes.

### 1.4 Strategy

1. **Make landmark count an explicit, single value across the paper's main result.**
   Choose L = 5,000 as the canonical value (matches the existing total-persistence battery, sufficient for diagram resolution per `landmark_sensitivity_summary.json` showing stability of total persistence and order-shuffle p-values across L ∈ {2500, 5000, 8000}).
2. **Recompute the Wasserstein null battery at L = 5,000** for all five rungs (label, cohort, order, Markov-1, Markov-2) on the USoc checkpoint. Use the existing `run_wasserstein_battery.py` with `--landmarks 5000`. Estimated wall-clock: ≈ 5–8 hours (extrapolating from the L=2000 reference: 471 s for order, 559 s for Markov-1 with 100 perms; W₂ scales roughly $O(L^{1.5})$ per pair × 500 null-null pairs).
3. **Cross-landmark sensitivity table** in supplement: add columns for W₂ at L ∈ {2500, 5000, 8000} alongside the existing total-persistence table, so reviewers can see the L-dependence of *both* statistics. This becomes Supplement §S4 (already reserved as "Landmark count robustness analysis (L = 2,500, 5,000, 8,000)" in v1 outline).
4. **If the W₂ Markov-1 H₀ rejection survives at L = 5,000** (expected, given the post-audit run at the original L showed mean obs-null W₂ ≈ 12.7 vs null-null ≈ 5.9 — a 2.1× ratio that is unlikely to be a landmark artefact), report the matched-L result as the headline number and demote the legacy L=2,000 result to the supplement.
5. **If the W₂ rejection weakens or disappears at L = 5,000**, the substantive claim must be reframed and §4.3 substantially rewritten to acknowledge that the discrepancy was partly a landmark-count effect. This is a contingent revision and the only acceptable outcome that does *not* require new headline computations is documenting it honestly.
6. **Replication on BHPS:** repeat the W₂ Markov-1 rerun at L = 5,000 on the BHPS checkpoint so the cross-survey replication §6.2 also rests on a matched-L comparison. Estimated wall-clock: ≈ 2 h (smaller cloud, n = 8,509).
7. **Justify the choice of L = 5,000 explicitly in §3.2** — cite the L sensitivity table, state that total-persistence statistics are stable in 2500–8000, and W₂ is computed at the same L as total persistence so the two results are directly comparable.

### 1.5 Artefacts to produce

- `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_<date>.json`
- `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_L5000_<date>.json`
- New supplement table S4.1 — total persistence and W₂ p-values at L ∈ {2500, 5000, 8000} for all five nulls, both H₀ and H₁.
- Vault entry: `[RESULT]` log entry to `04-Methods/Computational-Log.md`.

### 1.6 Verification

- §3.2 of v2 names a single L value used for both statistics in the headline result.
- §4.3 numerical p-values are derived from matched-L diagrams.
- Reviewer's specific concern ("not directly comparable") is addressed verbatim in the methods text.

---

## 2. ISSUE H2 — Global Markov-1 null misspecification (regime-stratified null missing)

### 2.1 Reviewer claim

> "The appropriate Markov null for a dataset with seven known mobility regimes would be a regime-stratified Markov chain: simulate trajectories by sampling initial regimes from the empirical distribution and applying regime-specific transition matrices. The paper does not explore this and does not justify why a global Markov null is the correct baseline given that the regimes are known."

Plus the deeper concern: *"the discrepancy is specifically a property of using a misspecified null… A regime-stratified Markov null might eliminate or substantially reduce the W₂ discrepancy, changing the substantive conclusion."*

This is a **High** severity issue because if a regime-stratified Markov null reproduces the observed diagram, the headline finding ("Markov-1 cannot reproduce the topology") collapses to "a *misspecified* Markov-1 cannot reproduce the topology."

### 2.2 Current state

- **Code exists but never properly run.** `trajectory_tda/topology/permutation_nulls.py` lines 246–362 implement `_stratified_markov_shuffle()` correctly: per-regime transition matrices estimated from regime-labelled trajectories with a `min_regime_n=30` fallback to global TM.
- **Existing run is broken.** `results/trajectory_tda_integration/stratified_markov/stratified_markov1_results.json` shows `regime_distribution: {0: 27252, 3: 28}` — only 2 regimes were active because the GMM regime labels were not loaded correctly (almost all trajectories collapsed to regime 0). `trajectory_tda/agent-plans/04-agent-robustness-handoff.md` documents this: *"GMM yields only 2 active regimes out of k=7: regime 0 (99.9% of trajectories) and regime 3 (0.1%). Regime 3 used global TM as fallback (n=28 < min_regime_n=30)."* So the stored "stratified Markov-1" result is functionally identical to the global Markov-1 null and answers nothing about regime stratification.
- **Vault `04-Methods/Markov-Memory-Ladder.md` table:** explicitly says "Markov-1 destroys regime substructure" — a known limitation that has never been tested.

### 2.3 Classification

**Both** — needs new computation (correctly stratified null) AND prose rewrite of §3.3 / §4.3 / §7.

### 2.4 Strategy

1. **Diagnose the regime-label loading bug.** Inspect the `_run_stratified_markov.py` (now a temp file marked for deletion in the handoff doc) and identify why regime labels collapsed. Likely candidates: (a) sklearn version mismatch (1.8.0 saved vs 1.3.2 loaded — explicitly flagged in handoff), causing `predict()` to return a single label; (b) the wrong checkpoint field was used (e.g., `cluster_label` rather than `regime_label`); (c) labels were generated against a different embedding than the checkpoint expected. The fix is to regenerate the GMM regime assignments from the canonical `embeddings.npy` and the saved GMM model (or refit the GMM under the current sklearn version), then write a fresh `regime_labels.npy` and pass that through to the null run.
2. **Run a correctly stratified Markov-1 null** at L = 5,000 (matching ISSUE H1), n_perms = 100 (matching the global Markov-1 n_perms in the post-audit), all seven regimes represented. Verify the regime-distribution sanity check: counts should approximately match Table 2 of the v1 draft (R1: 7,358; R2: 5,415; R0: 3,787; R4: 3,510; R3: 3,333; R6: 2,064; R5: 1,813).
3. **Compute W₂ obs-null and null-null distances** for the stratified Markov-1 null at H₀ and H₁. This is the critical comparison.
4. **Decision tree on outcome:**
   - **Outcome A — stratified Markov-1 still rejected (W₂ p < 0.05):** the headline finding strengthens. Add an explicit row to Table 1 showing both global and stratified Markov-1 p-values, explain why regime-stratification did not absorb the signal (the within-regime serial structure is itself non-Markovian), and reframe §7.1 to note that the result holds against the stronger null.
   - **Outcome B — stratified Markov-1 not rejected (W₂ p ≥ 0.05):** the headline finding must be reframed. The substantive conclusion shifts from *"trajectories carry non-Markovian structure that defeats a globally estimated null"* to *"the apparent non-Markovian structure in §4.3 is fully explained by regime-specific transition heterogeneity."* This is still a publishable finding — it locates the structural complexity at the *regime-stratification* level and makes the seven regimes the load-bearing object — but §1, §4.3, §7.1 and the abstract require substantial rewriting.
   - **Outcome C — borderline (0.05 ≤ p < 0.20):** report both results, discuss the methodological implication (the choice of null is the locus of the test-statistic discrepancy), and consider escalating to a stratified Markov-2 null to localise residual structure (matching the existing logic by which §4.3 uses Markov-2 to localise the Markov-1 rejection).
5. **Add stratified Markov-1 to the ladder formally.** The Markov memory ladder of v1 is: label → cohort → order → Markov-1 → Markov-2. Insert "stratified Markov-1" as a sixth rung between Markov-1 and Markov-2. This is the structurally honest way to present the result regardless of outcome.
6. **Pre-register the analysis.** Because outcome B would require a substantial reframing, pre-commit (in this plan, with timestamp) to the analysis design before running it: L = 5,000, n = 100 perms, both H₀ and H₁, decision rule p < 0.05 → reject, p ≥ 0.20 → fail to reject, 0.05–0.20 → borderline. This makes the post-hoc reframing in outcome B a transparent revision rather than HARKing.

### 2.5 Artefacts to produce

- Diagnostic note: `papers/P01-A-JRSSA/notes/2026-05-XX-stratified-markov-diagnosis.md` recording the regime-label loading bug, the fix, and a reproducibility-friendly description of the corrected pipeline.
- `results/trajectory_tda_integration/stratified_markov/stratified_markov1_results_FIXED_<date>.json` — preserve the broken legacy file, do not overwrite (CONVENTIONS rule: do not silently replace archived JSON).
- `results/trajectory_tda_integration/stratified_markov/stratified_markov1_W2_L5000_<date>.json` — new W₂ statistics at matched L.
- BHPS counterpart: `results/trajectory_tda_bhps/stratified_markov/stratified_markov1_W2_L5000_<date>.json`. (BHPS BIC selects k = 8 — need to verify the BHPS checkpoint also has working regime labels; if not, the same diagnosis-and-fix applies.)
- Vault entries: `[RESULT]` log + (depending on outcome) a `[DECISION]` lock or a `[NEGATIVE]` permanent note.

### 2.6 Verification

- The new "stratified Markov-1" rung appears in Table 1 of v2.
- The regime distribution used in stratification is reported and matches Table 2.
- §7.1 and the abstract honestly reflect outcome A, B, or C — no equivocation.

---

## 3. ISSUE H3 (reviewer's "Medium") — H₀ conflated with density-mode regime detection

### 3.1 Reviewer claim

> "Using VR H₀ to detect density clusters is fundamentally wrong — one should use sub-level set filtrations on a density estimator, not VR complexes on the point cloud. The seven GMM regimes are doing the structural identification work; persistent H₀ of the VR complex is measuring something orthogonal."

The reviewer accepts that the v1 draft *acknowledges* this, but is concerned that the framing — "expected and substantively meaningful" — under-states the orthogonality.

### 3.2 Current state

- v1 §4.2 and §4.4 do flag the conceptual gap and report ARI = 0.00004 between H₀ tree-cut and GMM, but the prose "*This is expected and substantively meaningful: the trajectory manifold is a single connected object with internal density structure*" elides what the reviewer wants stated explicitly: H₀ is not the right tool for density-mode detection at all.

### 3.3 Classification

**Prose-only**, with one optional computation (a sub-level-set filtration on a KDE) if we want to provide the *correct* density-mode topological analysis as a positive complement.

### 3.4 Strategy

1. **Rewrite §4.2 and §4.4 to make the orthogonality explicit and structural, not incidental.** The new framing: VR H₀ on a point cloud measures single-linkage hierarchical merge structure of the *connectivity graph* of trajectories; it does not measure density modes. The seven GMM regimes are density modes. Both are real, both are derived from the same point cloud, and the ARI = 0.00004 is the predicted value because the two analyses target distinct topological objects. Cite the standard reference: Chazal & Michel (2021) *Frontiers in Artificial Intelligence* on the distinction between Rips H₀ and DTM/sublevel-set H₀ for density inference.
2. **Add a methodological caveat box (or in-line para) in §3.2** stating that VR H₀ is reported as a *connectivity / merge-tree summary*, not as a density-mode indicator. This pre-empts the reader from reading H₀ as evidence about regime structure.
3. **Optional but recommended: compute the sub-level-set persistence of a KDE on the embedding** (cubical filtration on a fixed grid, or DTM-Rips). Report the H₀ persistence diagram and its tree-cut at the prominence consistent with k = 7. If the resulting partition substantially recovers the GMM regimes, that is the *right* topological evidence for density-mode regime structure. This becomes a small new sub-section in §4 (e.g., §4.2.1 "Density-mode topology as a complement to single-linkage H₀") of ≤ 300 words.
4. **Demote H₀ from rhetorical centrality.** v1's abstract reads "Persistent H₀ topology encodes regime separation" — this should become "Persistent H₀ on the VR complex characterises hierarchical connectivity structure that a globally estimated Markov chain cannot reproduce under W₂ comparison." Density-mode regime structure is then attributed correctly to the GMM (and optionally to KDE sub-level-set H₀).
5. **Revisit Table 1's interpretation in §4.3.** The W₂ Markov-1 rejection is about the *connectivity merge structure*, not density modes. The substantive interpretation in v1 ("the real data has regime-specific substructure: components that form at particular filtration scales and merge in a particular hierarchy") is essentially correct; the prose in §4.4 is what needs sharpening.

### 3.5 Artefacts to produce

- Optional: `results/trajectory_tda_integration/density_topology/sublevel_kde_h0_<date>.json` and a new figure (Figure S? — "Sub-level-set persistence diagram for a KDE on the trajectory embedding").
- Updated §3.2, §4.2, §4.4 prose.

### 3.6 Verification

- The orthogonality is stated in §3.2 *before* H₀ results are reported in §4.
- The abstract no longer claims H₀ encodes regime separation; if any such claim is made about Mapper or GMM, it is correctly attributed.
- The reviewer's conflation concern cannot be re-raised on the same evidence.

---

## 4. ISSUE M1 — Surrogate generation algorithm deferred to companion paper

### 4.1 Reviewer claim

> "For the null results to be reproducible and peer-reviewable in this paper, the surrogate generation algorithm — how Markov-1 trajectories are resampled, the starting state distribution, whether trajectory length is preserved — must be present here or in an accessible supplement. The supplement outline lists §S1–S5 but does not include a null-model specification."

### 4.2 Current state

- v1 §3.3 says: *"Five null models of increasing structural fidelity — label shuffle, cohort shuffle, order shuffle, Markov order-1, Markov order-2 — are used to decompose the topological signal. […] Full testing details are reported in the companion paper; here we state results and focus on their substantive interpretation."*
- The companion paper P01-B is being written in parallel and not yet available to a reviewer assessing P01-A in isolation.
- Code is in `trajectory_tda/topology/permutation_nulls.py` and `trajectory_tda/scripts/run_wasserstein_battery.py`. The vault page `04-Methods/Markov-Memory-Ladder.md` provides a concise specification.

### 4.3 Classification

**Prose-only.** No new computation required; the algorithm specification needs to be transcribed into P01-A's supplement.

### 4.4 Strategy

1. **Add a new supplementary section S0 (before S1):** "Null-Model Specification". This must include, for each of the five rungs, plus the new stratified Markov-1 rung from ISSUE H2:
   - Exact algorithm (pseudocode, ≤ 20 lines per null).
   - What is preserved and what is destroyed (table — already in vault Markov-Memory-Ladder.md).
   - Trajectory length policy (preserved per-individual? padded? truncated?). For Markov-1: lengths preserved one-to-one with the observed trajectory list (per `_stratified_markov_shuffle()` line 350: `length = len(traj)`).
   - Initial-state distribution (empirical first-state frequencies, normalised — per `permutation_nulls.py` lines 281–298).
   - Random seed policy and how reproducibility is achieved (master seed + per-permutation seed schedule).
   - PCA loadings: are they refit per surrogate or held fixed at the observed fit? (Held fixed — `embed_kwargs` reuses the observed PCA.) State this explicitly because it is a non-trivial choice that affects null calibration.
   - Number of permutations and number of null-null pairs sampled for the W₂ p-value computation. Currently 100 obs-null pairs and 500 null-null pairs (per Computational-Log 2026-03-24).
2. **Reproducibility statement:** in §3.3 (main text) cite the supplement section explicitly; do not just point at the companion paper. Two cross-references are acceptable; one cross-reference to a paper that may not be on arXiv yet is not.
3. **Code DOI placeholder:** the CONVENTIONS doc requires a Zenodo DOI for each repo before submission. Reserve the DOI now and cite it in the supplement so the algorithm can be inspected at submission time even if the companion paper is held back.
4. **Specify the W₂ p-value formula explicitly** (this also covers ISSUE M2 below): given observed diagram $D_\text{obs}$ and null draws $\{D^{(j)}\}_{j=1}^{N}$, define the test statistic and the rule for $p$. The vault page describes it informally; the supplement must give the exact formula.

### 4.5 Artefacts to produce

- New supplement section `papers/P01-A-JRSSA/drafts/v2-supplement-S0-null-specification.md` (or integrated into the main supplement file when one is created).
- Cross-reference fix in §3.3.

### 4.6 Verification

- A reader who has P01-A but not P01-B can reproduce all five (six) null distributions from the supplement alone.
- §3.3 contains no instance of "see companion paper" without a corresponding "see Supplement §S0".

---

## 5. ISSUE M2 — Persistence landscape L² metric in keywords / Figure 14 not actually computed

### 5.1 Reviewer claim

> "Title says 'persistence landscape L²' but this metric is never used. The abstract keywords include 'persistence landscape L²' and Figure 14 is captioned 'gender-specific persistence landscape overlays, H₀ and H₁', but the methods section describes only total persistence scalars and W₂ diagram distances. […] The paper does not describe computing persistence landscapes anywhere."

### 5.2 Current state

- **Keywords (v1, abstract):** "persistent homology, topological data analysis, Mapper algorithm, social mobility, career inequality, life-course trajectories, Wasserstein distance, mobility regimes" — landscape L² is *not* in the keywords list. **Reviewer error on the keyword claim.** But the related issue is real:
- **Figure 14 caption (v1 §6.1):** "Gender-specific persistence landscape overlays, H₀ and H₁." There is a figure file `figures/trajectory_tda/fig11_landscape_comparison.{pdf,png}` (and an identical copy in `papers/P01-VR-PH-Core/figures/`), so the figure exists. But the methods section does not describe how landscapes are computed, what the L² distance is, or whether it was used as a test statistic.
- **CONVENTIONS rule (always):** *"ALWAYS use persistence landscape L² distance as a complementary metric alongside Wasserstein."* This is a locked methodological mandate that the v1 draft does **not** satisfy — landscape L² is required but not computed.
- **Code:** `trajectory_tda/topology/vectorisation.py:28` implements `persistence_landscape()` (Bubenik tent functions, k-th landscape via sorted tents) but it is not invoked anywhere in the P01-A pipeline.

### 5.3 Classification

**Both** — landscape L² needs to be computed (for the headline null-test result, not just for Figure 14), and the methods/results prose needs to describe it.

### 5.4 Strategy

1. **Compute persistence landscape L² distances for the same null battery as W₂.** For each null, compute landscape representations of the observed diagram and each null draw using `persistence_landscape()` with k_max = 5, n_points = 200 (defaults), then compute pairwise L² distances on the (5 × 200)-dimensional landscape vectors. The test statistic is then the mean obs-null L² vs null-null L², matching the W₂ permutation logic.
2. **Add a column to Table 1** in §4.3: "L² landscape distance" alongside total persistence and W₂. This satisfies the CONVENTIONS mandate and provides genuine triangulation.
3. **Compute landscape L² for the gender comparison** that Figure 14 illustrates. Report the test statistic and p-value in §6.1, replacing the current implicit-only mention.
4. **Verify Figure 14 actually shows landscapes.** If the figure is in fact a persistence diagram plotted as curves (the reviewer raises this as a possibility), regenerate it from `persistence_landscape()` output using the standard landscape-overlay format (Bubenik 2015, Fig 1 style: x-axis = filtration parameter, y-axis = $\lambda_k$, with k = 1, 2, 3 overlaid by colour). Otherwise relabel the figure correctly.
5. **Update §3.3 (methods)** to describe persistence landscapes:
   - Definition (tent function, k-th landscape).
   - Resolution and number of landscapes (k_max = 5, n_points = 200 — choices to be justified by the L² stability across landscape resolution; report a small sensitivity analysis with k_max ∈ {3, 5, 10} and n_points ∈ {100, 200, 500} in supplement).
   - Stability statement: cite Bubenik (2015, *JMLR*) on the 1-Wasserstein-stable landscape representation.
6. **Update keywords list** to include "persistence landscape L²" if the reviewer's incorrect-as-stated concern reflects a real expectation that the keyword should be there. Adding it commits us to the analysis above; consistent with CONVENTIONS.
7. **Outcome triangulation logic:** if W₂ rejects Markov-1 H₀ (p ≈ 0.002 in v1) but landscape L² does not, that is itself a methodological finding (landscape representations smooth out the kind of discrepancy W₂ detects). Either way, the result is reportable.

### 5.5 Artefacts to produce

- `results/trajectory_tda_integration/post_audit/04_nulls_landscape_L2_L5000_<date>.json` — five (six) nulls × two dimensions.
- `results/trajectory_tda_bhps/post_audit/04_nulls_landscape_L2_L5000_<date>.json`.
- Regenerated `figures/P01-A/fig14_landscape_overlays.{pdf,png}` (or relabelled if the existing figure is already a landscape).
- Supplement table for landscape resolution sensitivity.
- Updated §3.3, §4.3 (Table 1), §6.1 prose.

### 5.6 Verification

- Every claim implying landscape L² has a numeric reference in the results.
- Figure 14 is what its caption says it is.
- The CONVENTIONS landscape rule is satisfied for P01-A as well as P01-B.

---

## 6. ISSUE M3 — 75th-percentile filtration threshold unjustified

### 6.1 Reviewer claim

> "The 75th-percentile filtration threshold is stated without justification. In 20-dimensional Euclidean space, the VR complex can grow combinatorially at filtration radii well below the 75th percentile of pairwise distances; a threshold based solely on the distance distribution rather than on topological stability (e.g., the 'elbow' in total persistence, or a scale justified by the data's estimated intrinsic dimension) is an underspecified choice."

### 6.2 Current state

- v1 §3.2: "filtration threshold at the 75th percentile of pairwise distances" — no justification given.
- `trajectory_tda/topology/trajectory_ph.py` uses a default of 95th percentile of squared distance to nearest landmark for alpha-cubical computations; the 75th percentile choice for the maxmin VR pipeline appears to be set in `run_pipeline.py` or downstream of it. Need to confirm exact provenance — see verification.
- No threshold-sensitivity analysis exists in `results/`.

### 6.3 Classification

**Both** — needs a sensitivity sweep over thresholds AND a justification paragraph.

### 6.4 Strategy

1. **Identify the threshold provenance.** Grep `trajectory_tda/scripts/` for `percentile`, `threshold`, `thresh=`, `max_filtration` in the active pipeline (run_pipeline.py + run_wasserstein_battery.py + run_landmark_sensitivity.py) and find where 75% is set. Confirm the value in the actual numerical output by reading the `thresh` field in the stored Ripser results.
2. **Estimate intrinsic dimension** of the PCA-20D point cloud using two complementary methods: (i) MLE estimator (Levina & Bickel 2004), (ii) two-NN estimator (Facco et al. 2017). Report a single intrinsic-dimension estimate $\hat d$ in §3.2 (likely $\hat d \in [4, 10]$ for n-gram career data). This contextualises the claim that the 20D embedding contains substantial low-dimensional structure.
3. **Threshold sensitivity sweep.** Compute persistence diagrams (and re-run the W₂ Markov-1 null) at three thresholds: 50th percentile, 75th percentile, 90th percentile. The 50th percentile is conservative (fewer features, faster); 90th admits more late-merging components; 75th is the v1 default. Report:
   - H₀ and H₁ feature counts and total persistence at each threshold.
   - W₂ Markov-1 p-value at each threshold.
   - The "elbow" in cumulative total persistence as a function of filtration scale (Carlsson 2009 elbow heuristic).
4. **Justify the chosen threshold in §3.2.** The justification should appeal to:
   - The L=5000 maxmin diameter (compute and report — sets an upper bound on meaningful filtration).
   - The intrinsic-dimension estimate.
   - The plateau behaviour of total persistence above the chosen threshold (the elbow argument).
   - A short sentence on the well-known curse-of-dimensionality concentration of pairwise distances in 20D (Beyer et al. 1999) and why a low-percentile threshold may suppress meaningful long-lived features.
5. **Compare against landmark-set diameter.** Report the maxmin landmark-set diameter (the maximum minimum distance after L=5000 maxmin selection) as a principled upper bound on the meaningful filtration scale. The 75th-percentile threshold should be compared to this diameter.

### 6.5 Artefacts to produce

- `results/trajectory_tda_robustness/threshold_sensitivity/ph_thresh_{p50,p75,p90}_L5000_<date>.json`.
- Intrinsic-dimension estimate file: `results/trajectory_tda_robustness/intrinsic_dimension/id_estimates_<date>.json`.
- Supplement subsection — "Filtration-threshold sensitivity" (~ 200 words + one table).
- Updated §3.2 prose with the justification paragraph.

### 6.6 Verification

- §3.2 reports the threshold value as a fraction (75%) AND as an absolute distance in PCA units.
- The chosen threshold is at or beyond the elbow in cumulative total persistence.
- A reader who disagrees with the choice can see the consequences at 50% and 90%.

---

## 7. ISSUE M4 / L1 — H₂ and higher homology not computed

### 7.1 Reviewer claim

> "Only H₀ and H₁ are computed. No justification is given for stopping at dimension 1, particularly since the embedding is 20-dimensional PCA space. […] Without a rigorous filtration stability analysis and without computing H₂ (to rule out higher-dimensional voids), the significance of H₁ non-rejection cannot be evaluated."

### 7.2 Current state

- `trajectory_tda/topology/permutation_nulls.py` and `trajectory_tda/scripts/run_wasserstein_battery.py` use `max_dim=1` throughout. No H₂ has been computed.
- v1 §3.2 does not justify the H₁ ceiling.
- Computational concern: H₂ on a 5,000-landmark VR in 20D is expensive (Ripser scales steeply in higher dimensions; expect a 5–20× wall-clock multiplier over H₁).

### 7.3 Classification

**Both** — needs an H₂ computation (at minimum at L = 2,000 to keep cost down) AND a justification in §3.2.

### 7.4 Strategy

1. **Compute observed H₂ at L = 2,000** with `maxdim=2` in Ripser. Report the H₂ feature count, total persistence, max persistence, and persistence-entropy as a descriptive summary in §4.2. Estimated wall-clock: 4–24 hours single-machine; if it exceeds budget, fall back to L = 1,000 with a note.
2. **Run the H₂ null comparison against Markov-1 only**, n_perms = 50, at the same L. This is the smallest acceptable test of "are there higher-dimensional voids that the Markov-1 null fails to reproduce?" Higher n is unaffordable in H₂; the small n is justified by the high computational cost and the narrow purpose of the test.
3. **If H₂ is non-significant under Markov-1 (expected outcome):** add one paragraph to §4.2 reporting the result and stating that the v1 cap at H₁ for the main results is empirically justified — H₂ does not carry additional information against the null.
4. **If H₂ is significant under Markov-1:** the substantive picture changes. Higher-dimensional voids in the trajectory cloud would indicate something topologically richer than the v1 framing of "regime clusters and within-regime cycles". This is unlikely on the n-gram embedding — voids in 20D with n = 27,280 are unusual — but the analysis must run before we can rule it out. Outcome would require new sub-section §4.2.2 and a brief discussion in §7.
5. **Justify the H₁ ceiling in §3.2** explicitly: cite the practical landscape (Robinson & Turner 2017; Edelsbrunner & Harer 2010) on H_q for q > 1 in social-science point clouds and reference the empirical H₂ check below.

### 7.5 Artefacts to produce

- `results/trajectory_tda_integration/h2_check/ph_H2_L2000_<date>.json`.
- `results/trajectory_tda_integration/h2_check/nulls_markov1_H2_L2000_<date>.json`.
- New subsection in §4.2 (~ 150 words) reporting the H₂ result.

### 7.6 Verification

- §3.2 has an explicit H₂ justification, not silent omission.
- The reviewer's "without computing H₂ … the significance of H₁ non-rejection cannot be evaluated" is addressed by reporting the H₂ comparison.

---

## 8. ISSUE M5 / L2 — W₂ diagonal projection / stabilisation constant unreported

### 8.1 Reviewer claim

> "The stabilisation constant for the diagonal projection is not reported. W₂ between persistence diagrams requires choosing how off-diagonal points are matched to the diagonal. The paper uses Ripser output without specifying whether the standard 'death minus birth' diagonal projection is applied, and whether the W₂ computation uses a quadratic cost or an L^∞ bottleneck. These choices change the numerical distances and thus the p-values."

Also embedded:

> "The permutation distribution is not described: how many null surrogates, how is the p-value computed (rank-based? parametric?), and what is the variance of the obs-null distances? Without confidence intervals on the W₂ values, the p = 0.002 is not fully interpretable."

### 8.2 Current state

- `vectorisation.py` line 232: `gudhi.wasserstein.wasserstein_distance(dgm1, dgm2, order=p, internal_p=2)` with `p=2` (default). This means: order = 2 (so the *outer* p in $W_p$ is 2), internal_p = 2 (so the *ground metric* on $\mathbb{R}^2$ is $\ell^2$). Diagonal projection: gudhi's standard implementation projects unmatched off-diagonal points $(b, d)$ to their nearest diagonal point $((b+d)/2, (b+d)/2)$ at cost $((d-b)/2) \sqrt 2$ under $\ell^2$ ground metric, raised to the power 2 in the $W_2$ sum.
- None of this is in the v1 manuscript.
- Permutation-distribution details: 100 obs-null and 500 null-null pairs (vault Computational-Log 2026-03-24). p-value rule is rank-based: $p = \frac{1}{N+1} \sum_j \mathbb{1}\{\bar W_2(\text{obs}, \text{null}) \le W_2(\text{null}^{(j)}, \text{null}^{(j')})\}$ — but the exact formula needs to be confirmed against `run_wasserstein_battery.py` and stated in the supplement.

### 8.3 Classification

**Prose-only** for the W₂ definition; **prose + small computation** for the variance/CI on the obs-null distances (the obs-null distribution is already computed and stored, but the CI is not reported).

### 8.4 Strategy

1. **Add a one-paragraph formal definition of W₂** to §3.3 or to a new methods sub-subsection: $W_2(D_1, D_2) = \inf_\gamma \left(\sum_{x \in D_1} \|x - \gamma(x)\|_2^2 \right)^{1/2}$ where $\gamma$ ranges over partial matchings between $D_1 \cup \Delta$ and $D_2 \cup \Delta$, $\Delta$ is the diagonal, and $\|x - \Delta\|_2 = (d - b) / \sqrt 2$ for $x = (b, d)$. State `internal_p = 2` and `order = 2` explicitly. Cite gudhi documentation.
2. **State the diagonal projection rule** (matched orthogonally to the diagonal) and the implication that this is the unique stable projection for $W_2$ with $\ell^2$ ground metric (Cohen-Steiner et al. 2007).
3. **Report the permutation algorithm** in the supplement (overlaps with ISSUE M1):
   - $N_\text{null} = 100$ surrogates, $N_\text{nullnull} = 500$ pairs of null-null distances.
   - Test statistic: $\bar W_2(D_\text{obs}, \{D^{(j)}_\text{null}\})$ — mean obs-null distance.
   - Reference distribution: empirical CDF of pairwise $W_2(D^{(j)}_\text{null}, D^{(j')}_\text{null})$ over 500 random pairs.
   - $p$-value: $\hat p = (1 + \#\{(j, j') : W_2 \ge \bar W_\text{obs}\}) / (1 + N_\text{nullnull})$ (one-sided, upper tail).
4. **Report the variance and 95% CI of the obs-null W₂ in §4.3:** mean ± SD ± 95% CI from the obs-null distribution. The post-audit JSON already contains the `obs_null_distribution` array (see results file at `04_nulls_wasserstein_w2_20260407.json`); compute SD and bootstrap 95% CI from it. This costs nothing computationally.
5. **Add a small Monte-Carlo sanity check.** Recompute the W₂ Markov-1 p-value with $N_\text{null} = 200$ (doubled) and $N_\text{nullnull} = 2000$ (quadrupled), to confirm the p-value is stable. If p remains $\le 0.005$ with both n's, report both. (One reason: a p = 0.002 from $N_\text{nullnull} = 500$ has a binomial 95% CI of approximately [0.0006, 0.0073] — non-trivial Monte Carlo error.)

### 8.5 Artefacts to produce

- New supplement subsection "W₂ definition, diagonal projection, and p-value algorithm" (~ 250 words plus one equation block).
- Optional re-run with doubled n: `04_nulls_wasserstein_w2_L5000_doublen_<date>.json`.
- Updated §4.3 numerical reporting: every W₂ value reported with mean ± SD and a 95% CI.

### 8.6 Verification

- §3.3 contains an unambiguous formal definition of the W₂ used.
- Every numeric W₂ in §4.3 has an associated SD or CI.
- The reviewer's concerns on "variance of the obs-null distances" and "stabilisation constant" cannot be re-raised.

---

## 9. ISSUE L3 — BHPS H₁ rejection uninterpretable without window-length control

### 9.1 Reviewer claim

> "BHPS H₁ rejection. The paper reports that BHPS-era trajectories reject Markov-1 H₁ under W₂ (p = 0.000) while USoc does not (p = 0.086), attributing this to window length (14.5 vs. 12.9 years). This is a plausible but unverified explanation — the paper explicitly states 'whether it reflects genuinely different cycling dynamics… or solely the longer observation window is a question for future work.' This is scientifically honest but means the H₁ BHPS result is uninterpretable without further analysis and should not be given the inferential weight it implicitly receives."

### 9.2 Current state

- v1 §6.2 acknowledges the confound openly but reports the BHPS H₁ rejection as part of the cross-survey replication evidence.
- BHPS post-audit run in vault Computational-Log: BHPS Markov-1 W₂ H₁ p = 0.002 (mean obs-null = 151.99 vs null-null = 139.20). USoc post-audit: H₁ p = 0.226 (note: v1 cites p = 0.086, drawn from the legacy battery; need to reconcile).

### 9.3 Classification

**Both** — needs a length-matched sub-analysis on BHPS AND a careful rewording of §6.2.

### 9.4 Strategy

1. **Length-matched sub-analysis.** Construct a sub-sample of BHPS trajectories truncated to 12.9 years (matching USoc mean trajectory length). Two strategies:
   - **(a) Truncation:** for each BHPS trajectory of length T, randomly drop trailing years until length ≤ 13. Re-embed, recompute persistence at L = 5,000, run Markov-1 W₂ H₁ test.
   - **(b) Windowing:** within each BHPS trajectory of length T ≥ 13, take the first 13 years. This is more reproducible but loses late-window information.

   Run both. If both give H₁ p ≈ 0.000 — the rejection is *not* due to window length, and §6.2's "future work" hedge can be replaced with a positive statement. If both give H₁ p > 0.05 — the rejection *is* due to window length, and §6.2 should be reframed as "BHPS H₁ rejection is a window-length artefact and is not a finding about era-specific cycling dynamics."
2. **Reciprocal length-extension on USoc** is impossible (we cannot make USoc trajectories longer than the data permit), so the asymmetry has to be addressed by the BHPS length-down match alone.
3. **Power calculation.** Report a back-of-the-envelope power calculation for the W₂ H₁ test as a function of n trajectories and trajectory length, so the reader can see how much of the BHPS-USoc difference is explained by power.
4. **Reconcile the v1 USoc H₁ p = 0.086 with the post-audit p = 0.226.** Likely explanation: v1 quotes the legacy (pre-2026-04-07) battery; the post-audit is the authoritative number. Update §4.3 to use the post-audit value and add a note on the change.
5. **Reword §6.2 conditionally** based on outcome of (1). If window-length explains the rejection, the paragraph becomes: *"The BHPS H₁ rejection in §6.2 is consistent with a window-length effect: when BHPS trajectories are truncated to USoc length, the rejection disappears (W₂ H₁ p_truncated = X.XX, p_first13 = X.XX). We therefore report no era-specific H₁ finding."* If not, the opposite. Either way, the v1 hedge ("a question for future work") is replaced with a definitive answer.

### 9.5 Artefacts to produce

- `results/trajectory_tda_bhps/length_matched/ph_truncated13_L5000_<date>.json`.
- `results/trajectory_tda_bhps/length_matched/ph_first13_L5000_<date>.json`.
- `results/trajectory_tda_bhps/length_matched/nulls_markov1_W2_truncated13_L5000_<date>.json` (and first13).
- Reconciliation note in §4.3 on the USoc H₁ p-value.
- Reworded §6.2.

### 9.6 Verification

- §6.2 contains no "future work" hedge on the H₁ window confound.
- Whichever conclusion is reached is explicitly attributed to the length-matched comparison and given as a tested claim, not a conjecture.

---

## 10. EMBEDDED CONCERNS — issues raised inside the reviewer text but not in the issues table

These need to be addressed even though they are not separately tabulated.

### 10.1 Negative-control interpretation: label shuffle p ≈ 0.31 vs expected ≈ 0.5

**Reviewer:** *"The paper states that label shuffle produces p > 0.31 under both statistics and interprets this as confirming that 'specific identity of states does not drive diagram geometry when structure is otherwise intact'. But a correctly specified negative control for TDA should produce p ≈ 0.5 (null not rejected), while the observation of p > 0.31 is consistent with a weak positive signal that fails to reach significance — this is not the same as confirming null behaviour."*

**Strategy:**
- **Reconcile against post-audit numbers.** Computational-Log: USoc label-shuffle W₂ H₀ p = 0.452 and H₁ p = 0.538. These are very close to 0.5, not 0.31. The "> 0.31" wording in v1 §4.3 appears to come from the *total-persistence* numbers (label-shuffle: 0.315; cohort-shuffle: 0.405 — see vault Computational-Log P01 total persistence table).
- **Update §4.3** to report W₂ label-shuffle and cohort-shuffle p-values (≈ 0.45) as the negative-control evidence, and demote the total-persistence label-shuffle numbers to the supplement. The W₂ values straightforwardly satisfy the reviewer's "should be near 0.5" criterion.
- **Note BHPS asymmetry.** Vault CONVENTIONS note: *"NEVER treat BHPS label-shuffle and cohort-shuffle as assumed negative controls in P01-B §4."* The BHPS post-audit gives label-shuffle H₀ p = 0.036, cohort-shuffle p = 0.034 — not negative controls. Mention this in §6.2 as an empirical finding (consistent with CONVENTIONS).

### 10.2 Positive control absent

**Reviewer:** *"No positive control (a dataset where the null *is* known to be true) is reported."*

**Strategy:**
- **Add a positive-control simulation to the supplement.** Generate $n_\text{sim} = 27,280$ trajectories from the *fitted global* Markov-1 chain (the very model used as the null), embed them via the same n-gram + PCA-20D pipeline (frozen loadings), and run the full Markov-1 W₂ test. Expected: $p \approx 0.5$ for both H₀ and H₁. If observed, this is the positive control.
- **Computation cost:** essentially one extra null run (~1 hour at L = 5,000); free.
- **Report in supplement (new section S?), referenced from §3.3 and §4.3.**

### 10.3 Mapper-vs-PH framing of "topology" claims

**Reviewer:** *"The permutation test for sub-regime nodes (358 observed vs. null mean 86.3, p < 0.01) is framed as a TDA result but is actually a Mapper geometry result, not a persistence homology result. […] The framing within a TDA methods paper risks overstating their topological status."*

**Strategy:**
- Audit §5.2, §5.3, §5.4 of v1 and reword every claim that uses the word "topology" or "topological" in connection with a Mapper result. Replace with "Mapper graph property", "Mapper geometry", or "graph-based summary" as appropriate.
- Add a short caveat in §5.1: *"Mapper is a cover-nerve construction, not a homological invariant. Sub-regime node counts and bridge nodes are properties of the Mapper graph and depend on the cover and clustering choices documented in §3.4."*
- Keep the Mapper findings as substantive sociological evidence; only the topological-vocabulary attribution needs adjustment.

### 10.4 Paper's claim that the test-statistic discrepancy is a *general* methodological lesson

**Reviewer:** *"However, the claim is overstated in one respect: the paper presents this as a general lesson for TDA methodology, but the discrepancy is specifically a property of using a *misspecified* null (global vs. regime-stratified Markov)."*

**Strategy:** dependent on the outcome of ISSUE H2 (§2 above).
- **Outcome A (stratified Markov-1 still rejected under W₂):** the "general lesson" framing is defensible but should be qualified: the discrepancy persists against the better-specified null, suggesting that scalar-vs-diagram statistics genuinely measure different aspects of the diagram.
- **Outcome B (stratified Markov-1 not rejected):** the "general lesson" framing is wrong and must be rewritten. The lesson becomes "scalar persistence statistics can mask null misspecification that diagram-level statistics expose."
- Either way, the §4.3 final paragraph and the §7.1 framing must be rewritten after H2 results are in.

### 10.5 Conflation in §4.2 of "loops are numerous but not deeply persistent" as a substantive finding

**Reviewer:** *"In high-dimensional VR complexes H₁ features are commonly induced by sampling artefacts and metric distortion in PCA projections."*

**Strategy:**
- **Rephrase §4.2's H₁ paragraph** to be descriptive rather than substantive. "Loops are numerous but not deeply persistent" is reported, not interpreted as a finding about the data-generating process. The paragraph adds a sentence: *"In 20-dimensional VR complexes, low-persistence H₁ features can arise from sampling and projection artefacts; the substantive H₁ analysis is the null-comparison in §4.3 and the BHPS length-matched comparison in §6.2 (cf. Issue 9)."*

---

## 11. Sequencing, Dependencies, and Resource Estimates

### 11.1 Dependency graph

```
[ISSUE H1: matched-L W₂]              ─┐
[ISSUE H2: stratified Markov-1]       ─┤── must complete before §4.3 / abstract rewrite
[ISSUE M5: landscape L²]              ─┘
[ISSUE M3: threshold sensitivity]   ── must complete before §3.2 rewrite
[ISSUE M4: H₂ check]                ── must complete before §3.2 / §4.2 rewrite
[ISSUE L2: W₂ formal definition]    ── prose only, can run any time
[ISSUE M1: null-spec supplement]    ── prose only
[ISSUE H3: H₀-density orthogonality] ── prose-only (with optional KDE-PH computation)
[ISSUE L3: BHPS length match]       ── independent computation, can run in parallel
[10.2 positive control]             ── tiny computation, can run in parallel with H1
```

### 11.2 Critical path

The longest chain is: **diagnose stratified-Markov bug → run stratified Markov-1 W₂ → decide outcome A/B/C → rewrite §4.3, §7.1, abstract.** Best estimate: 3–5 working days.

### 11.3 Wall-clock estimates (i7 / 32 GB / no GPU per CONVENTIONS)

| Task | n_perms | L | Estimate |
|---|---|---|---|
| Matched-L W₂ Markov-1 (USoc) | 100 | 5000 | 5–8 h |
| Matched-L W₂ Markov-1 (BHPS) | 100 | 5000 | 2–3 h |
| Stratified Markov-1 W₂ (USoc) | 100 | 5000 | 5–8 h |
| Stratified Markov-1 W₂ (BHPS) | 100 | 5000 | 2–3 h |
| Landscape L² battery (USoc) | 100 | 5000 | 6–10 h |
| Landscape L² battery (BHPS) | 100 | 5000 | 2–4 h |
| Threshold sensitivity sweep | 50 | 5000 × 3 | 6–10 h |
| H₂ observed + Markov-1 null | 50 | 2000 | 10–24 h (or fall back to L=1000) |
| BHPS length-matched | 100 | 5000 | 4–6 h |
| Positive control simulation | 100 | 5000 | 5–8 h |
| Doubled-n W₂ sanity check | 200/2000 | 5000 | 12–20 h |
| Intrinsic-dimension estimate | — | 27,280 | <1 h |
| KDE sub-level set H₀ (optional) | — | 27,280 | 2–4 h |
| **Total (sequential, no parallel)** | | | **~70–110 h** |

If runs are parallelised across multiple terminals (the i7 has enough RAM for 2–3 concurrent VR PH runs at L = 5,000), wall-clock can be roughly halved. AoAS / JRSS revision deadline allows for cloud A100 use only for P04 (per CONVENTIONS resource map); P01-A is local-feasible.

### 11.4 Per-rung permutation budget

- Headline tests (W₂ Markov-1, stratified Markov-1, landscape L² Markov-1): n_perms = 100, n_nullnull pairs = 500. Matches the existing post-audit n.
- Sensitivity / robustness tests (H₂, threshold sweep): n_perms = 50, justified by the high computational cost and the descriptive (not headline-determining) nature of the test.
- Sanity-check doubled-n run on the headline W₂ Markov-1: n_perms = 200, n_nullnull = 2000.

### 11.5 Suggested execution order (sequential, ~ 2 weeks at typical workload)

1. **Day 1:** Diagnose stratified-Markov regime-label bug (small focused debugging session). Reproduce the `_run_stratified_markov.py` invocation, identify why only 2 regimes were active, fix, write a new run script. Confirm regime distribution matches Table 2.
2. **Day 2:** Kick off in parallel: matched-L W₂ Markov-1 (USoc) + stratified Markov-1 W₂ (USoc) + positive-control simulation. ~ 5–8 h each, can run concurrently.
3. **Day 3:** Kick off in parallel: BHPS counterparts (matched-L + stratified) + landscape L² battery (USoc).
4. **Day 4:** Kick off threshold sensitivity sweep and BHPS length-matched. While these run, write supplement S0 (null specification) and the W₂ formal-definition paragraph (both prose-only).
5. **Day 5:** Kick off H₂ observed + Markov-1 null at L = 2,000 (longest single job).
6. **Day 6–7:** Compile all results, decide outcome on H2 (stratified Markov-1), rewrite §4.3, §7.1, and abstract accordingly.
7. **Day 8–10:** Rewrite §3.2 (filtration justification, intrinsic dimension, H₂ caveat, landmark-count justification, threshold justification), §4.2 (H₀ orthogonality, H₂ result, H₁ caveat), §6.1 (landscape L² for gender), §6.2 (length-matched BHPS), and the Mapper-vocabulary audit in §5.
8. **Day 11–12:** Generate / regenerate Figure 14 if it is in fact a persistence diagram and not a landscape; produce the new figures (intrinsic-dim plot if useful, density-mode KDE H₀ if computed).
9. **Day 13:** Internal /humanizer pass on the rewritten sections; check CONVENTIONS compliance (W₂, landscape L², Markov order labelling, BHPS wave range explicit).
10. **Day 14:** Produce v2 draft.

---

## 12. Acceptance Criteria for v2

The v2 draft is ready to circulate (pre-submission) only when **every** item below holds. This is the checklist a future reviewer-of-the-revision should be able to verify against the manuscript alone, without recourse to the codebase.

### 12.1 Methodological completeness

- [ ] §3.2 reports a single landmark count $L$ used for both total-persistence and W₂ headline statistics, with justification by reference to the L sensitivity sweep.
- [ ] §3.2 reports the filtration threshold as a fraction *and* an absolute distance, with a justification paragraph that cites the elbow / intrinsic-dimension / landmark-set diameter argument.
- [ ] §3.2 contains an explicit justification for the H₁ ceiling, supported by the empirical H₂ check reported in §4.2.
- [ ] §3.3 contains a formal one-paragraph definition of $W_2$ including order, internal_p, and diagonal projection rule.
- [ ] §3.3 cross-references the supplement section S0 (null specification) explicitly.
- [ ] §3.3 describes persistence landscapes and the L² distance, and Table 1 in §4.3 includes a landscape L² column.

### 12.2 Result completeness

- [ ] Table 1 includes rows for stratified Markov-1 (new rung) and a column for landscape L².
- [ ] Every W₂ value reported in §4.3 has an associated SD or 95% CI.
- [ ] The positive control simulation result is reported in §3.3 or §4.3 (≈ 0.5 expected).
- [ ] The H₂ result (observed + Markov-1 null) is reported in §4.2.
- [ ] The BHPS length-matched H₁ result is reported in §6.2 with a definitive (not "future work") interpretation.
- [ ] The USoc H₁ p-value in §4.3 is reconciled against the post-audit number.

### 12.3 Framing fixes

- [ ] §4.2 and §4.4 do not conflate VR H₀ with density-mode regime detection.
- [ ] §4.3 and §7.1 framing of the test-statistic discrepancy is consistent with the outcome of the stratified Markov-1 test (outcome A / B / C as defined in §2.4).
- [ ] §5 does not call any Mapper-derived quantity a "topological" finding.
- [ ] §4.3 negative-control claim cites W₂ label-shuffle p ≈ 0.45 (≈ 0.5), not the legacy total-persistence p ≈ 0.31.
- [ ] Abstract reflects all the above and does not overstate the "general lesson" framing.

### 12.4 CONVENTIONS compliance

- [ ] W₂ used throughout — no bare "Wasserstein" without order.
- [ ] Landscape L² included as a complementary metric.
- [ ] Every Markov null is labelled with its order $k$.
- [ ] BHPS wave range stated explicitly wherever BHPS is mentioned.
- [ ] Random seeds reported wherever new computations are described.

### 12.5 Reproducibility

- [ ] Supplement §S0 contains pseudocode for every null model.
- [ ] All new results files exist under the `results/` tree under date-suffixed names; no legacy file overwritten.
- [ ] Each new result file is referenced from the manuscript by name (in supplement) and has a corresponding `[RESULT]` entry in the vault Computational-Log.

---

## 13. Open questions to resolve before execution begins

These are not for the reviewer; they are for the author / co-thinking before the work in §11 begins.

1. **L target.** Is L = 5,000 truly the right matched-L value, or should we go to L = 8,000 (where total-persistence stability is even better, at ~ 2× the W₂ runtime)? The case for L = 8,000 is methodological purity; the case for L = 5,000 is the pre-existing total-persistence battery and runtime budget. **Recommendation: L = 5,000 unless a quick L = 8,000 W₂ pilot at n = 20 perms shows materially different p-values.**
2. **Stratified Markov-1 bug root cause.** Is the bug a sklearn version mismatch (1.8.0 saved vs 1.3.2 loaded), a wrong checkpoint field, or a misalignment between the embedding used to fit GMM and the embedding used by the null run? This determines how invasive the fix is. Resolving this is the first step on Day 1 of the execution plan in §11.5.
3. **Should the stratified-null result be published in P01-A or held back for P01-B?** Vault CONVENTIONS rule on the BHPS split says: applied findings → P01-A; methodology → P01-B. The stratified Markov-1 result is *both* — it is both an applied finding (does the regime structure absorb the Markov-1 W₂ rejection?) and a methodological finding (about null misspecification in TDA). **Recommendation: publish the result in both papers, with P01-A reporting the substantive outcome (does the regime stratification kill the W₂ discrepancy?) and P01-B reporting the methodological framework (the stratified Markov-1 as a new rung in the ladder).** Coordinate the wording to avoid double-counting.
4. **Figure 14: regenerate or relabel?** Need to inspect the existing figure file (`figures/trajectory_tda/fig11_landscape_comparison.pdf`) and decide whether it actually shows landscapes or is a relabelled persistence diagram. Quick check via image inspection should resolve this.
5. **H₂ budget.** If H₂ at L = 2,000 takes longer than 24 hours (plausible), is it acceptable to fall back to L = 1,000? **Recommendation: yes, but only if the smaller L still produces a stable, interpretable H₂ feature count (≥ 50 features).** If even L = 1,000 is unaffordable, document the limit and explicitly defer H₂ to P01-B's robustness section.

---

## 14. References to add to v2 if not already cited

- **Beyer, K., Goldstein, J., Ramakrishnan, R., & Shaft, U. (1999).** When is "nearest neighbor" meaningful? *ICDT.* — for the curse-of-dimensionality justification of the filtration threshold (§3.2).
- **Bubenik, P. (2015).** Statistical topological data analysis using persistence landscapes. *JMLR* 16, 77–102. — for the landscape L² metric (§3.3, §4.3).
- **Chazal, F., & Michel, B. (2021).** An introduction to topological data analysis: fundamental and practical aspects for data scientists. *Frontiers in AI* 4. — for the H₀-vs-density orthogonality (§4.2).
- **Facco, E., d'Errico, M., Rodriguez, A., & Laio, A. (2017).** Estimating the intrinsic dimension of datasets by a minimal neighborhood information. *Scientific Reports* 7. — for the intrinsic-dimension estimate (§3.2).
- **Levina, E., & Bickel, P. J. (2004).** Maximum likelihood estimation of intrinsic dimension. *NeurIPS* 17. — same as above.
- **Carrière, M., Cuturi, M., & Oudot, S. (2017).** Sliced Wasserstein kernel for persistence diagrams. *ICML.* — citable backstop for $W_2$ on diagrams (§3.3).

---

*End of plan. No code or revisions executed; this document is the input to the next planning conversation, not the output.*
