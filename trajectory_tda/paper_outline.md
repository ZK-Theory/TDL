# Topological Dynamics of UK Life-Course Trajectories
## Paper Outline for Journal of Economic Geography

**Target Journal:** Journal of Economic Geography  
**Format:** Research Article  
**Target Word Count:** 9,000–10,000 words  
**Figures:** 11 main + 1 supplementary

---

## Abstract (250 words)

**Structure:**
- Context (2 sentences): Longitudinal panel data captures life-course dynamics, but sequence analysis methods lose topological structure
- Gap (1 sentence): No framework for detecting regime formation and cyclical traps in high-dimensional trajectory space
- Method (3 sentences): 27,280 employment×income state trajectories (BHPS/USoc 1991–2023), n-gram embedding + PCA-20D, Vietoris–Rips persistent homology (maxmin 2,500 landmarks), 5-null Markov memory ladder
- Results (3 sentences): 7 mobility regimes (GMM-BIC), order-shuffle H₀ strongly significant (p<0.001, n=500) confirming topology exceeds random relabelling, Markov(1) H₀ p=0.148 indicating regime structure consistent with first-order dynamics, 3,249 H₁ persistent cycles identifying recurrent churn traps
- Implications (2 sentences): TDA detects structural features invisible to sequence analysis; Markov memory ladder pins down generating-process complexity

**Key numbers:** 27,280 trajectories, 32 years, 9 states, 7 regimes, n=500 permutations, 5 null models

---

## 1. Introduction (1,800 words)

### 1.1 Motivation: UK Social Mobility and Life-Course Dynamics (600 words)
- UK mobility decline (Blanden et al. 2004, 2013; Goldthorpe & Mills 2008)
- Shift from cross-sectional to longitudinal: life-course as sequences of states
- BHPS + Understanding Society: 32-year panel enabling long trajectories
- Policy relevance: Levelling Up, welfare-to-work trap identification

### 1.2 Research Gap (500 words)
- Sequence analysis (Abbott 1995): optimal matching, cluster analysis — treats sequences as strings, loses geometry
- Limitation: No notion of "closeness in trajectory space", no topological invariants
- TDA applied to finance (Gidea & Katz 2018), neuroscience (Saggar et al. 2018), but NOT to life-course panels
- Markov chain models capture transitions but not global shape of trajectory clouds
- Gap: How does the *topology* of trajectory space relate to socioeconomic regimes?

### 1.3 Contribution & Roadmap (700 words)
- First application of persistent homology to longitudinal socioeconomic trajectories
- Novel "Markov memory ladder" — systematic null model battery characterising generating-process complexity
- 7 distinct mobility regimes discovered from topological structure
- Honest reporting: H₁ cycles consistent with state frequencies (order-shuffle non-significant), but regime structure (H₀) has genuine topological signal
- Paper structure preview

**Key Citations:**
- Abbott (1995): Sequence methods
- Carlsson (2009): Topology and data
- Edelsbrunner & Harer (2010): Computational topology
- Gidea & Katz (2018): TDA in finance
- Goldthorpe (2016): Social mobility and education
- Blanden et al. (2004, 2013): UK intergenerational mobility

---

## 2. Literature Review (2,200 words)

### 2.1 Sequence Analysis in Social Science (600 words)
- Optimal matching and variants (Abbott & Tsay 2000; Lesnard 2010)
- State-sequence representations, substitution costs
- Limitations: metric sensitivity, global geometry lost, no formal significance testing
- Multi-channel sequences (Gauthier et al. 2010)

### 2.2 Topological Data Analysis Foundations (600 words)
- Simplicial complexes, filtrations, persistent homology (Edelsbrunner et al. 2002)
- Vietoris–Rips complex, computational advances (Bauer 2021: Ripser)
- Persistence diagrams, landscapes, Betti curves as summary statistics
- Stability theorem: small perturbations → small changes in diagrams (Cohen-Steiner et al. 2007)

### 2.3 Poverty Traps and Mobility Regimes (500 words)
- Multiple equilibria and poverty traps (Azariadis & Stachurski 2005; Barrett & Carter 2013)
- Life-course typologies: stable/mobile/churn (Vandecasteele 2010)
- UK-specific: employment state persistence, income churning (Jenkins 2011)
- Connection to topology: regimes as connected components (H₀), traps as cycles (H₁)

### 2.4 Statistical Null Models for TDA (500 words)
- Permutation tests for PH (Robinson & Turner 2017)
- Label shuffle, order shuffle, Markov nulls (Stolz et al. 2017)
- Higher-order Markov chains as structured nulls (Tong 1990)
- Gap: No systematic "memory ladder" comparing null strengths in applied TDA

---

## 3. Data and Methodology (2,000 words)

### 3.1 Data: BHPS + Understanding Society (400 words)
- BHPS waves 1–18 (1991–2008), USoc waves 1–14 (2009–2023)
- Sample: 118,000+ respondents → 27,280 with ≥10 consecutive years
- 9-state space: {E, U, I} × {L, M, H} (employment×income), derived from jbstat + equivalised household income relative to 60% median
- Imputation: forward-fill for gaps ≤2 years; 2.4% imputed person-years
- Covariates: sex, birth cohort, parental NS-SEC (for stratification)

### 3.2 Trajectory Embedding (400 words)
- N-gram frequency representation: unigrams + bigrams → 90-dimensional TF vector
- PCA dimensionality reduction: 90D → 20D (capturing >95% variance)
- **Figure 2:** Embedding point cloud (UMAP 2D projection of PCA-20D space, coloured by regime)
- UMAP-16D as sensitivity check (supplementary): ARI ≈ 0.31 between PCA-7 and UMAP-6 cluster assignments; three macro-types (secure employment, inactive/marginal, churn/mixed) are stable across embeddings, but finer regime boundaries shift — consistent with UMAP/PCA capturing different aspects of local vs global geometry
- Resulting point cloud: 27,280 points in ℝ²⁰

### 3.3 Persistent Homology (500 words)
- Maxmin landmark selection: 2,500 landmarks from 27,280 points (greedy farthest-point sampling)
- Vietoris–Rips complex via Ripser (Bauer 2021)
- Computed through H₁; H₀ = connected components (regimes), H₁ = loops (cycling/traps)
- Persistence diagram representation: birth-death pairs (b, d) with lifetime d − b

### 3.4 Null Model Battery (500 words)
- **Label shuffle:** Permute state labels globally — destroys all transition structure
- **Cohort shuffle:** Permute within birth cohort bins — tests cross-cohort signal
- **Order shuffle:** Random permutation of each trajectory's state sequence — preserves frequencies, destroys temporal order
- **Markov order-1:** Simulate from estimated first-order transition matrix — tests whether topology exceeds memoryless transitions
- **Markov order-2:** Simulate from second-order conditional transition matrix — tests higher-order memory
- Test statistic: total persistence (sum of lifetimes) for H₀ and H₁
- n=500 permutations for order_shuffle, Markov-1, Markov-2; n=100 for label/cohort
- "Markov memory ladder": systematic comparison of null strengths

### 3.5 Regime Discovery (200 words)
- Gaussian Mixture Model on PCA-20D embeddings, BIC model selection (k=3–15)
- Optimal k=7
- Regime profiling: employment composition, income distribution, transition rates, stability index

---

## 4. Results (2,400 words)

### 4.1 Descriptive Statistics (400 words)
- 27,280 trajectories, mean length 14.2 years, range 10–32
- State distribution: Employment dominant (EL 8%, EM 26%, EH 24%), high inactivity (IL 12%)
- Birth cohort range: 1916–1995 (analysis decades: 1940s–1980s)
- **Figure 1:** Trajectory heatmap showing exemplar sequences by regime
- **Table 1:** Sample characteristics by cohort decade

### 4.2 Topological Structure (500 words)
- H₀: 2,500 features; dominant component lifetime = 15.67 (much larger than mean 6.24)
- H₁: 3,249 features; maximum persistence = 3.77, total H₁ persistence = 1,285
- **Figure 3:** Persistence diagrams (H₀ + H₁)
- Interpretation: Multiple well-separated clusters (regimes) + substantial cycling

### 4.3 Null Model Validation (500 words)
- **Order shuffle:** H₀ p < 0.001 — temporal order of states matters for regime structure
- **Label/cohort shuffle:** H₀ p = 0.69, 0.66 — global relabelling and cohort structure are not the source of topology (as expected, they are trivial nulls)
- **Markov memory ladder (Table 2 / Figure 8):**
  - Markov-1 H₀: p = 0.148 — regime structure is consistent with first-order Markov dynamics
  - Markov-2 H₀: p = 0.108 — consistent with second-order dynamics too
  - Interpretation: The topological regime structure is well-captured by one-step transition probabilities
- **H₁ results:** Order-shuffle H₁ p = 0.25, Markov-1 H₁ p = 0.652, Markov-2 H₁ p = 0.434 — cycles are consistent with state frequencies and transition structure
- **Figure 4:** Betti curves observed vs null envelopes
- **Figure 9:** Markov memory depth comparison (violin plots)

### 4.4 Seven Mobility Regimes (500 words)
- BIC-optimal k=7; regime profiles:
  - Stable High-Employment: EM/EH dominated, low transitions
  - Secure High-Income: predominantly EH, stability index >0.85
  - Low-Income Churn: cycling between EL, UL, IL; high transition rate
  - Inactive-to-Employment: IL→EM/EH transitions; upward mobility
  - [remaining 3 from actual data]
- **Figure 5:** Regime profile heatmap (7 × [employment rate, unemployment rate, inactivity rate, low/mid/high income, stability, transition rate])
- **Figure 6:** Stability–income correlation scatter

### 4.5 Cycle and Trap Analysis (300 words)
- 3,249 H₁ features — but non-significant vs order shuffle (p=0.25), Markov-1 (p=0.65), Markov-2 (p=0.43)
- Honest interpretation: cycles are compatible with state frequencies and Markov transition structure — should **not** be presented as "topological poverty traps" in a strong causal sense
- However: characteristic cycle lengths and dominant loop states provide descriptive value
- Top persistent loops involve Low-Income ↔ Unemployment cycling
- **Figure 7:** Cycle analysis (top loops + length distribution)

### 4.6 Stratified Comparisons (200 words)
- Gender: Wasserstein distance + permutation p-values
- Parental NS-SEC: Professional/Managerial vs Routine/Manual
- Cohort decade: secular change in trap structure
- **Figure 10:** Wasserstein heatmap by social origin
- **Figure 11:** Gender persistence landscape overlay

---

## 5. Discussion (1,500 words)

### 5.1 What TDA Adds Beyond Sequence Analysis (400 words)
- Formal significance testing via null models (vs ad-hoc clustering)
- Regime discovery from shape rather than string distance
- Memory characterisation: "topology is first-order Markov" is a precise, testable claim
- Comparison: k=7 regimes qualitatively resemble sequence analysis typologies but are derived geometrically

### 5.2 The Markov Memory Ladder (400 words)
- Novel methodological contribution: systematic null strength comparison
- Result: regime structure decomposes into first-order transition probabilities
- Does NOT mean "there is no interesting topology" — it means topology is efficiently described by one-step transitions
- Implication for policy: interventions targeting single transitions (e.g., employment entry programs) can reshape the regime landscape
- Comparison to higher-order Markov literature (Singer & Spilerman 1976)

### 5.3 Honest Assessment of H₁ (300 words)
- H₁ cycles non-significant vs all nulls — cycles arise from state composition
- Does not mean people don't cycle — it means the *topological shape* of cycling is predictable from frequencies
- Future direction: bifiltration by income threshold may reveal conditional cycle significance
- Contrast with Markov chain mixing time analysis

### 5.4 Limitations (400 words)
- 9-state discretisation loses within-state variation
- PCA dimensionality choice: UMAP-16D sensitivity check yields ARI ≈ 0.31 vs PCA regime assignments (Fig S1), indicating that while three macro-types are robust, fine-grained regime boundaries are embedding-dependent — cautions against over-interpreting differences between neighbouring regimes
- Maxmin landmark sampling may miss rare trajectory types
- No family dimension (27-state space deferred)
- Imputation assumptions for gap-filling
- Cross-wave harmonisation between BHPS and USoc

---

## 6. Conclusion (500 words)

### Summary
- First persistent homology analysis of UK life-course trajectories
- 7 regimes with formal topological validation
- **Positive claim**: statistically strong, order-dependent mobility regimes (H₀ vs order-shuffle p<0.001)
- **Bound**: regime structure requires at most 1–2 step memory to generate (Markov-1 p=0.148, Markov-2 p=0.108)
- **Negative result**: H₁ cycles are consistent with state frequencies and Markov structure — descriptively valuable but not evidence of non-Markovian traps
- Stratified differences by gender (1/2 significant), NS-SEC (3/6), cohort (26/42)

### Policy Implications
- Single-transition interventions are sufficient for regime change (Markov-1 result)
- Trap identification: which states are absorbing, which have cycling topology
- Targeting: regimes with high churn (Low-Income Churn regime) for intervention

### Future Work
- Family dimension: 27-state space (employment×income×partnership)
- Autoencoder embeddings for richer trajectory representations
- Multi-parameter persistent homology (employment and income as separate filtrations)
- Comparative: apply same methodology to German SOEP, US PSID panels
- Agent-based model calibration from topological targets

---

## Figure List

| # | Title | Section |
|---|-------|---------|
| 1 | Trajectory Heatmap: Exemplars by Regime | §4.1 |
| 2 | Embedding Point Cloud (UMAP 2D projection) | §3.2 |
| 3 | Persistence Diagrams (H₀ + H₁) | §4.2 |
| 4 | Betti Curves: Observed vs Null Envelopes | §4.3 |
| 5 | Regime Profiles (7 × characteristics heatmap) | §4.4 |
| 6 | Stability–Income Correlation | §4.4 |
| 7 | Cycle Analysis (H₁ loops + length distribution) | §4.5 |
| 8 | Null Model Summary Table (Markov Ladder) | §4.3 |
| 9 | Markov Memory Depth Comparison (violin plots) | §4.3 |
| 10 | Wasserstein Distance by Social Origin | §4.6 |
| 11 | Gender Persistence Landscape Overlay | §4.6 |
| S1 | UMAP-16D Embedding Sensitivity Check | Appendix |

---

## Table List

| # | Title | Section |
|---|-------|---------|
| 1 | Sample Characteristics by Cohort Decade | §4.1 |
| 2 | Markov Memory Ladder: Null Model Results | §4.3 |
| 3 | Regime Composition and Characteristics | §4.4 |
| 4 | Pairwise Wasserstein Distances by Social Origin | §4.6 |

---

## Key References

- Abbott, A. (1995). Sequence analysis: new methods for old ideas. *Annual Review of Sociology*, 21, 93-113.
- Azariadis, C. & Stachurski, J. (2005). Poverty traps. *Handbook of Economic Growth*, 1, 295-384.
- Barrett, C. & Carter, M. (2013). The economics of poverty traps and persistent poverty. *Journal of Development Studies*, 49(7), 976-990.
- Bauer, U. (2021). Ripser: efficient computation of Vietoris-Rips persistence barcodes. *Journal of Applied and Computational Topology*, 5, 391-423.
- Blanden, J. et al. (2004). Changes in intergenerational mobility in Britain. *Generational Income Mobility in North America and Europe*.
- Carlsson, G. (2009). Topology and data. *Bulletin of the American Mathematical Society*, 46(2), 255-308.
- Cohen-Steiner, D. et al. (2007). Stability of persistence diagrams. *Discrete & Computational Geometry*, 37(1), 103-120.
- Edelsbrunner, H. & Harer, J. (2010). *Computational Topology: An Introduction*. AMS.
- Gauthier, J.A. et al. (2010). Multichannel sequence analysis applied to social science data. *Sociological Methodology*, 40(1), 1-38.
- Gidea, M. & Katz, Y. (2018). Topological data analysis of financial time series. *PLoS ONE*, 13(1), e0190348.
- Goldthorpe, J.H. (2016). Social class mobility in modern Britain. *Journal of the British Academy*, 4, 89-111.
- Jenkins, S.P. (2011). *Changing Fortunes: Income Mobility and Poverty Dynamics in Britain*. Oxford University Press.
- Lesnard, L. (2010). Setting cost in optimal matching to uncover contemporaneous socio-temporal patterns. *Sociological Methods & Research*, 38(3), 389-419.
- Robinson, A. & Turner, K. (2017). Hypothesis testing for topological data analysis. *Journal of Applied and Computational Topology*, 1, 241-261.
- Saggar, M. et al. (2018). Towards a new approach to reveal dynamical organization of the brain using topological data analysis. *Nature Communications*, 9, 1399.
- Singer, B. & Spilerman, S. (1976). The representation of social processes by Markov models. *American Journal of Sociology*, 82(1), 1-54.
- Stolz, B.J. et al. (2017). Persistent homology of time-dependent functional networks constructed from coupled time series. *Chaos*, 27(4), 047410.
- Vandecasteele, L. (2010). Poverty trajectories, triggering events and exit routes. *Sociological Research Online*, 15(4), 1-17.
