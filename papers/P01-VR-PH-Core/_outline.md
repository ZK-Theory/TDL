# P01 Argument Structure

See `drafts/v5-2026-03.md` for current full draft. This file tracks the high-level argument.

## Core Claim

UK employment-income trajectories have topology that exceeds first-order Markov dynamics — but the conclusion depends on how you compare persistence diagrams. Total persistence says Markov-1 is sufficient; Wasserstein distance says it is not. The discrepancy is a methodological finding.

## Structure (v5)

1. **Introduction** — motivation (UK social mobility stagnation), research gap (sequence analysis lacks formal null testing and geometric characterisation), contributions
2. **Literature** — sequence analysis (OM), TDA foundations (PH, Wasserstein), mobility regimes, statistical null models for TDA
3. **Data & Methods** — BHPS/USoc, 9-state space, n-gram PCA embedding, VR PH, Markov memory ladder (5 models × 2 test statistics)
4. **Results**
   - §4.1 Descriptive statistics
   - §4.2 Topological structure (H₀, H₁ raw features)
   - §4.3 Null model validation — **core section**: Table 2 (total persistence), Table 2b (Wasserstein), test-statistic discrepancy
   - §4.4 Seven mobility regimes (GMM + H₀ geometry + regime stickiness)
   - §4.5 Cycle analysis (H₁ negative result)
   - §4.6 Stratified comparisons (Wasserstein by gender/NS-SEC/cohort)
   - §4.7 BHPS cross-era validation
5. **Discussion** — TDA vs OM, Markov ladder + discrepancy, H₁ negative, limitations, robustness
6. **Conclusion** — topology is real; Markov conclusion depends on measurement; H₁ robust negative; stratification; stickiness
