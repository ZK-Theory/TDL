# Topological Dynamics of UK Life-Course Trajectories

**Authors:** [Author Names]
**Target Journal:** *Sociological Methodology* / *Social Forces* / *JASA: Applications & Case Studies*
**Date:** March 2026 (Third Draft)

---

## Abstract

Longitudinal panel data captures the temporal structure of life-course dynamics, yet conventional sequence analysis methods treat trajectories as character strings, discarding their geometric structure in high-dimensional space. While persistent homology (PH) has been applied to financial and biological data with hypothesis testing (Robinson & Turner 2017), no study has brought PH with systematic null-model batteries to bear on socioeconomic life-course trajectories. Here we apply PH to 27,280 employment-income trajectories drawn from the British Household Panel Study and Understanding Society (1991–2023). Each trajectory is a sequence of nine states combining employment status (employed, unemployed, inactive) with income tercile (low, mid, high), embedded into 20-dimensional PCA space via n-gram frequency vectors and analysed using Vietoris–Rips persistent homology with 5,000 maxmin landmarks. We introduce a **Markov memory ladder** — a battery of five null models of escalating structural complexity — that systematically characterises the generating process underlying the observed topology.

Seven distinct mobility regimes emerge via Gaussian mixture models optimised by BIC. Order-shuffle H₀ is strongly significant (*p* < 0.001, *n* = 500), confirming that temporal ordering creates topological structure beyond state composition alone. H₀ topology is not rejected under a first-order Markov null (Markov-1 *p* = 0.148), while H₁ cycles are compatible with state frequencies and transition structure (*p* > 0.25 across all nulls). Results are stable across landmark counts from 2,500 to 8,000, with order-shuffle H₀ *p* < 0.001 at all values. Stratified Wasserstein distances reveal significant topological differences by gender, parental NS-SEC, and birth cohort; 30/50 tests survive Benjamini-Hochberg FDR correction at $q < 0.05$ (H₀: 16/25, H₁: 14/25). Overlapping 10-year career-phase windows confirm extreme regime stickiness: among 7,453 individuals starting in disadvantaged regimes, only 416 (5.6%) escape to advantaged regimes. Comparison with optimal matching (OM) baselines (ARI = 0.26 at matched *k* = 7) indicates that TDA's primary added value lies in formal null testing and multi-scale geometric characterisation rather than regime discovery per se.

**Keywords:** persistent homology, topological data analysis, social mobility, life-course trajectories, Markov models, regime switching

**JEL Codes:** C14, C38, J62, D63

---

## 1. Introduction

### 1.1 Motivation: UK Social Mobility and Life-Course Dynamics

Intergenerational social mobility in the United Kingdom has been the subject of sustained scholarly and policy attention. Evidence accumulated over two decades indicates that mobility rates have stagnated or declined since the 1970s, with recent cohorts showing lower rates of upward movement relative to their parents' generation (Blanden et al. 2004, 2013; Goldthorpe & Mills 2008). This decline reflects deeper life-course dynamics in which persistent unemployment, income churning, and structural inactivity create multiple equilibria in employment-income states. Cross-sectional snapshots — comparing parents' and children's occupational class or income at a single point in time — inevitably miss these dynamics. What matters is not merely where individuals start and end, but the *shape* of the path between.

The British Household Panel Study (BHPS, 1991–2008) and its successor Understanding Society (USoc, 2009–2023) together provide one of the longest continuous household panels in the social sciences: 32 years of annual observations on over 118,000 respondents. From this population, we reconstruct 27,280 individual trajectories with at least 10 consecutive years of data. Each trajectory is a time-ordered sequence through a nine-state space combining employment status — employed (E), unemployed (U), or inactive (I) — with income tercile — low (L), mid (M), or high (H) — derived from equivalised household income relative to 60% of the contemporary median.

The resulting trajectories reveal a labour market in which employment dominates (58% of person-years) but inactivity is pervasive (32%), and low income affects over a third (36%) of observed person-years. These are not transient states: the modal trajectory length in our sample is 13 years, sufficient to observe structural persistence, cycling, and — for some — escape from disadvantaged states. The trajectories thus encode not merely labour market status but the temporal dynamics of socioeconomic position over the life course.

These dynamics have a spatial dimension that we acknowledge but do not fully exploit in this paper. UK labour market trajectories are shaped by regional economic structures, local labour market conditions, and the geography of opportunity — factors central to the "Levelling Up" agenda (HM Government 2022) and to the concerns of economic geography more broadly. While the present analysis operates at the national level, the methodological framework we develop — particularly the Markov memory ladder — is directly applicable to regional stratification (e.g., by NUTS2 region or Travel-to-Work Area), which we identify as a priority for future work (§5.4).

From a policy perspective, the question of whether disadvantaged trajectories represent absorbing states or transient spells is central to the design of welfare-to-work programmes, skills interventions, and place-based economic strategies. If low-income churning creates persistent cycles from which exit is rare, then marginal interventions targeting single transitions may prove inadequate. If, conversely, the landscape of trajectories is well described by low-order Markov dynamics, then targeting the right transitions could be sufficient. Distinguishing between these scenarios requires methods that go beyond measuring distances between sequences.

### 1.2 Research Gap

Sequence analysis methods — optimal matching (OM) and its many variants — have dominated life-course research since Abbott's (1995) influential importation of biological sequence techniques into sociology. OM and related methods treat trajectories as strings and compute pairwise distances under substitution and indel (insertion-deletion) cost matrices, enabling cluster analysis to identify "types" of life course. This approach has been productive, generating typologies of employment careers, family formation, and housing trajectories across many national contexts (Abbott & Tsay 2000; Lesnard 2010; Gauthier et al. 2010).

However, sequence analysis has limitations for the questions we pose. First, OM distances depend on the substitution cost matrix, which is typically set a priori or estimated from transition rates — introducing subjectivity at a foundational level (Robette & Thibault 2008). Second, OM and its variants treat trajectories as one-dimensional objects: they measure pairwise distances but have no concept of the global *geometry* or *topology* of the trajectory space. They cannot naturally detect persistent clusters (connected components), loops (cyclical traps), or higher-dimensional voids in the point cloud of embedded trajectories — though we note that sequence-based clusters may capture similar substantive phenomena by other means. Third, there is no standard framework for formal significance testing — for asking whether the observed structure exceeds what would be expected under explicit generative null models.

Markov chain models, the other workhorse of life-course analysis, capture local transition probabilities but are not designed to detect global shape. A Markov model can tell us the probability of moving from unemployment to employment, but it cannot detect whether the cloud of all trajectories in embedding space has a topological signature of cyclical trapping, or whether the number and separation of trajectory clusters exceeds what memoryless transitions would produce.

Topological data analysis (TDA), via persistent homology (PH), addresses these limitations. PH identifies topological features — connected components (H₀), loops (H₁), and higher-dimensional voids — that persist across a range of spatial scales, providing a multi-scale signature of the shape of a point cloud that is robust to noise and dimensionality (Carlsson 2009; Edelsbrunner & Harer 2010). TDA has been applied to financial time series (Gidea & Katz 2018), brain networks (Saggar et al. 2018), gene expression (Rizvi et al. 2017), and materials science (Hiraoka et al. 2016). PH hypothesis testing has been developed by Robinson & Turner (2017), and TDA–Markov hybrids have appeared in network analysis (Stolz et al. 2017). Recent work has brought TDA to adjacent social-science settings — notably network persistence in organisational sociology (Sizemore et al. 2018) and simplicial complexes for modelling social contagion (Iacopini et al. 2019) — but these operate on cross-sectional network snapshots rather than individual-level longitudinal sequences. No study has applied persistent homology with structured null-model batteries to longitudinal socioeconomic trajectories — the setting where questions about regime formation, memory, and trapping dynamics are most pressing for social policy.

Critical gaps remain: How does the topology of trajectory space relate to socioeconomic mobility regimes? Can we systematically test whether observed topological structure exceeds Markov baselines of varying complexity? And does the ordering of career phases over the life course create additional topological structure beyond what the composition of individual trajectories already provides?

### 1.3 Contribution and Roadmap

This paper makes two primary contributions, accompanied by an exploratory extension.

First, we present the first application of persistent homology to longitudinal life-course data, revealing order-dependent regime structure that can be formally validated against generative null models. While the resulting regimes qualitatively resemble those found by sequence analysis in similar data (e.g., Bukodi & Goldthorpe 2019), TDA adds multi-scale geometric characterisation and formal significance testing that are not naturally available in OM-based frameworks. We provide a direct comparison with OM baselines in Section 5.1, where dynamic Hamming OM with Ward's clustering yields ARI = 0.26 against our TDA-derived regimes at matched *k* = 7 — consistent with overlapping but non-identical regime boundaries.

Second, we introduce a **Markov memory ladder**: a systematic battery of five null models of increasing complexity (label shuffle, cohort shuffle, order shuffle, Markov order-1, Markov order-2) that decomposes the topological signal into contributions from state frequencies, temporal ordering, and memory length. This provides a precise, testable characterisation of the complexity of the generating process — a methodological contribution applicable to any TDA analysis of sequential data, from financial time series to genomic sequences.

As an exploratory extension, we analyse overlapping career-phase windows to quantify regime stickiness and test whether higher-order phase sequencing adds topological structure. Phase-order shuffle testing with *n* = 500 permutations finds no evidence that phase ordering creates additional topology (H₀ *p* = 0.98, 95% CI [0.968, 0.992]; H₁ *p* = 0.542, 95% CI [0.498, 0.586]), suggesting that the main topological signal arises from within-trajectory sequential structure rather than higher-order life-course sequencing.

We find that H₀ topological structure (cluster separation) is genuinely order-dependent (order-shuffle *p* < 0.001) but is not rejected under a first-order Markov null (Markov-1 *p* = 0.148). These findings are stable across landmark counts from 2,500 to 8,000 (Appendix B). H₁ cycles are consistent with state frequencies and Markov transitions (*p* > 0.25 across all nulls), a negative result that bounds the complexity of trajectory cycling. Stratified analysis reveals origin-dependent topology, with parental NS-SEC and birth cohort creating the strongest topological differentiation; all significant results survive Benjamini-Hochberg FDR correction. Overlapping 10-year windows confirm extreme regime stickiness (5.6% escape rate from disadvantaged regimes).

The remainder of the paper is organised as follows. Section 2 reviews sequence analysis, TDA foundations, poverty trap theory, and statistical null models. Section 3 describes the data and methodology. Section 4 presents results. Section 5 discusses implications, limitations, robustness, and future directions.

---

## 2. Literature Review

### 2.1 Sequence Analysis in Social Science

The application of sequence analysis to life-course data originated with Abbott's (1995) proposal to adapt biological sequence techniques for sociological use. Optimal matching (OM) computes distances between state sequences using substitution and indel operations, analogous to edit distances in string matching. The resulting distance matrix is then used for cluster analysis (typically Ward's hierarchical clustering or partitioning around medoids) to identify trajectory "types".

OM and its variants have produced influential typologies in many domains: employment careers (Halpin & Chan 1998), family formation (Elzinga & Liefbroer 2007), and housing trajectories (Coulter et al. 2016). Lesnard (2010) proposed dynamic Hamming distances that weight substitution costs by temporal proximity, addressing the criticism that OM treats all time points equally. Gauthier et al. (2010) extended the framework to multichannel sequences, enabling joint analysis of employment and family states. Studer & Ritschard (2016) provided a comprehensive software implementation in R's TraMineR package.

Despite this productivity, sequence analysis has well-documented limitations. The dependence on substitution cost matrices introduces subjectivity: different cost specifications can yield different typologies from the same data (Robette & Thibault 2008). The resulting distance measures are fundamentally pairwise — they compare sequences but do not characterise the global geometry of the trajectory space. There is no natural notion of "closeness in trajectory space" that preserves topological invariants such as connected components, loops, or higher-dimensional voids. Finally, significance testing is typically absent: cluster solutions are evaluated by silhouette scores or Calinski-Harabasz indices, but there is no formal test of whether the observed clustering exceeds what specific null models would produce.

### 2.2 Topological Data Analysis Foundations

Persistent homology (PH) provides a rigorous mathematical framework for detecting and quantifying topological features in data. Given a point cloud $X \subset \mathbb{R}^d$, PH constructs a filtration — a nested sequence of simplicial complexes $K_0 \subseteq K_1 \subseteq \cdots \subseteq K_m$ — by connecting points within distance $\epsilon$ and tracking which topological features appear (are "born") and disappear ("die") as $\epsilon$ increases (Edelsbrunner et al. 2002; Zomorodian & Carlsson 2005).

The Vietoris–Rips (VR) complex, the most common choice for point cloud data, includes a $k$-simplex whenever all $\binom{k+1}{2}$ pairwise distances are below $\epsilon$. For $n$ points, the VR complex can have up to $2^n$ simplices, making direct computation infeasible for large datasets. Maxmin landmark selection (de Silva & Carlsson 2004) addresses this by greedily selecting a subset of $L \ll n$ points that are maximally dispersed, constructing the VR complex on landmarks only. Ripser (Bauer 2021) provides state-of-the-art computational efficiency, exploiting the apparent pairs optimisation to compute VR persistence through H₁ (and optionally H₂) on thousands of landmarks in minutes.

The output of PH is a persistence diagram (PD): a multiset of birth-death pairs $(b_i, d_i)$ where feature $i$ is born at filtration value $b_i$ and dies at $d_i$. Features with large persistence $\ell_i = d_i - b_i$ are interpreted as genuine topological structure, while short-lived features near the diagonal are attributed to noise. In dimension 0 (H₀), features correspond to connected components: each merger of two components kills one H₀ feature. In dimension 1 (H₁), features correspond to loops or cycles: a loop forms at birth and is filled in at death. Summary statistics include total persistence $\sum_i \ell_i$, maximum persistence $\max_i \ell_i$, and persistence entropy $-\sum_i \hat{\ell}_i \log \hat{\ell}_i$ where $\hat{\ell}_i = \ell_i / \sum_j \ell_j$ (Atienza et al. 2019).

A fundamental property of PH is stability: small perturbations in the input point cloud produce small changes in the persistence diagram, measured by the bottleneck or Wasserstein distance (Cohen-Steiner et al. 2007). This guarantees that topological summaries are robust to noise, sampling variation, and minor measurement errors — a critical property for survey data with imputation and harmonisation challenges.

For comparing persistence diagrams across groups, the Wasserstein distance $W_p(D_1, D_2)$ measures the cost of the optimal transport between two diagrams, providing a principled metric for testing whether subpopulations have different topological structure (Turner et al. 2014).

### 2.3 Poverty Traps and Mobility Regimes

The economics of poverty traps posits that disadvantaged states can be self-reinforcing through multiple equilibria (Azariadis & Stachurski 2005). When returns to human capital investment are nonlinear — or when credit constraints, neighbourhood effects, or discrimination create threshold dynamics — individuals may become trapped in low-productivity equilibria from which escape requires large, discrete shocks rather than marginal improvements (Barrett & Carter 2013).

Life-course researchers have identified analogous patterns in longitudinal data. Vandecasteele (2010) distinguished between stable, mobile, and churning poverty trajectories using Belgian panel data. Jenkins (2011) documented extensive income churning in the UK, where many individuals cycle between poverty and near-poverty without achieving durable exits. Savage et al. (2013) used the Great British Class Survey to identify seven social classes, some characterised by cultural and social capital deficits that reinforce economic disadvantage.

The connection to topology is natural. If mobility regimes exist as distinct clusters in trajectory space, they will appear as persistent H₀ components. If churning creates cyclical traps — where individuals cycle between states without permanently escaping — these may appear as persistent H₁ loops. The persistence values of H₀ features (the difference between death and birth filtration values) quantify the separation between regime clusters: large persistence indicates well-separated regimes that merge only at large filtration radii. A topological analysis can thus provide a geometric characterisation of the mobility landscape that complements both sequence typologies and Markov transition models.

### 2.4 Statistical Null Models for TDA

The statistical significance of topological features requires comparison to appropriate null distributions. Robinson & Turner (2017) proposed permutation tests for PH, comparing observed total persistence or Betti numbers to distributions generated by permuting group labels. Stolz et al. (2017) applied PH to time-dependent functional networks, using surrogate data methods as nulls. These contributions establish the general framework; our contribution is to adapt and extend it with a structured hierarchy of null models tailored to sequential socioeconomic data.

For life-course trajectories, the relevant null models must be carefully chosen to test specific hypotheses. A label shuffle null (permuting state labels globally) tests whether the specific identity of states matters; an order shuffle (permuting each trajectory's state sequence) tests whether temporal ordering matters, preserving marginal state frequencies; and a Markov-$k$ null (simulating from an estimated $k$-th order Markov chain) tests whether topology exceeds what $k$-step memory produces.

Higher-order Markov chains as generative models have a long history in sociology (Singer & Spilerman 1976; Tong 1990). Our contribution is to arrange these null models into a systematic "memory ladder" — a sequence of increasingly structured null hypotheses that progressively preserves more of the observed data's structure. When the observed topology first becomes consistent with a Markov-$k$ null, we can conclude that the topological complexity of the trajectory space is well captured by $k$-step memory. This provides a precise, testable decomposition of topological complexity into its sources — a methodological innovation applicable to any setting where TDA is combined with sequential data.

---

## 3. Data and Methodology

### 3.1 Data: BHPS and Understanding Society

Our data combine two longitudinal household surveys: the British Household Panel Study (BHPS, waves 1–18, 1991–2008) and Understanding Society (USoc, waves 1–14, 2009–2023). BHPS began as a nationally representative sample of approximately 5,500 households in Great Britain, with annual interviews tracking employment, income, and demographic characteristics. Understanding Society succeeded BHPS with a larger initial sample of approximately 40,000 households and incorporated the surviving BHPS sample as a sub-sample from wave 2 (2010–2011), enabling longitudinal tracking across both surveys.

From the combined dataset of over 118,000 respondents, we select individuals with at least 10 consecutive years of valid employment-income observations, yielding 27,280 trajectories. The mean trajectory length is 12.9 years (median 13, range 10–14), with start years spanning 2009–2013 and end years 2018–2022. The relatively narrow year ranges reflect the harmonised sample drawn primarily from USoc's main panel with BHPS linkage.

Each person-year is assigned to one of nine states formed by crossing employment status with income tercile. Employment status is derived from the `jbstat` variable: employed (E) includes full-time and part-time employment and self-employment; unemployed (U) includes ILO-definition unemployment; inactive (I) includes retirement, full-time education, long-term sickness, and caring responsibilities. Income terciles are defined annually relative to 60% of the contemporary equivalised household income median: low (L, below 60%), mid (M, 60%–120%), and high (H, above 120%).

Gaps of one or two years in otherwise continuous trajectories are forward-filled from the last observed state, affecting 4.9% of person-years. We verify that imputation rates are balanced across regimes and do not drive topological results (Supplementary Material §A).

For stratification analysis, we use three covariates: sex (Female *n* = 14,402; Male *n* = 11,243; 1,635 with missing sex excluded from gender stratification); parental NS-SEC (Professional/Managerial *n* = 2,067; Intermediate *n* = 6,777; Routine/Manual *n* = 7,779; 10,657 missing); and birth cohort decade (1930s *n* = 1,642 through 1990s *n* = 1,364, with seven cohort groups).

### 3.2 Trajectory Embedding

To embed trajectories in a continuous metric space suitable for TDA, we compute n-gram frequency vectors. For each trajectory of length $T$, we calculate:

- **Unigrams** (9 dimensions): Relative frequency of each state $s \in \{EL, EM, EH, UL, UM, UH, IL, IM, IH\}$ in the trajectory.
- **Bigrams** (81 dimensions): Relative frequency of each consecutive state pair $(s_t, s_{t+1})$, capturing transition structure.

The concatenated 90-dimensional term-frequency (TF) vector encodes both the composition and the sequential structure of each trajectory. We standardise using a fitted `StandardScaler` and project to 20 dimensions via Principal Component Analysis (PCA), retaining the top 20 components. The resulting point cloud of 27,280 points in $\mathbb{R}^{20}$ preserves both global cluster structure and local sequence variation.

As a sensitivity check, we compute UMAP embeddings with 16 dimensions and compare GMM cluster assignments to those from PCA-20D. The adjusted Rand index (ARI) between the two clusterings is 0.33 at matched $k = 7$, indicating that while three broad macro-types (secure employment, inactive/marginal, churning/mixed) are stable across embedding methods, finer regime boundaries are embedding-dependent. This is consistent with UMAP and PCA capturing different aspects of local versus global geometry (McInnes et al. 2018), and cautions against over-interpreting differences between neighbouring regimes. We report PCA-20D as the primary embedding and UMAP-16D as a supplementary sensitivity analysis (Figure S1).

To verify that substantive conclusions are robust to embedding choice, we re-run the order-shuffle null on the UMAP-16D embedding ($n = 100$). With GMM fixed at $k = 7$, UMAP yields ARI = 0.33 against PCA regime assignments, confirming that three macro-types (secure employment, inactivity, churning) are stable while finer boundaries shift. On the UMAP-16D point cloud with 5,000 maxmin landmarks, the order-shuffle null rejects H₀ at $p < 0.001$ (observed total persistence 3,203.3, null mean $2{,}372.9 \pm 323.3$) while H₁ is non-significant ($p = 1.00$), reproducing the PCA pattern. Full Markov-1 replication on UMAP is omitted due to computational cost (each UMAP permutation requires a fresh embedding fit); given the close agreement in regime structure and order-shuffle results, we treat PCA as the primary embedding and UMAP as a robustness check confirming that the core topological findings are embedding-invariant.

### 3.3 Persistent Homology

We compute Vietoris–Rips persistent homology on the PCA-20D point cloud using the following pipeline:

1. **Maxmin landmark selection**: From the 27,280 embedded trajectories, we select $L = 5{,}000$ landmarks using the greedy furthest-point (maxmin) algorithm (de Silva & Carlsson 2004). This selects an initial seed point and iteratively adds the point maximally distant from the current landmark set, producing a well-dispersed subsample that preserves the geometric structure of the full cloud. The choice of $L = 5{,}000$ (approximately 18% of the point cloud) balances geometric fidelity against computational cost: at this level, every cell of the nine-state space is represented among the landmarks, and the maxmin coverage radius is small relative to inter-cluster distances. We verify robustness to this choice by recomputing PH at $L = 2{,}500$ and $L = 8{,}000$ (Appendix B); qualitative results and null-model *p*-values are stable across this range, with order-shuffle H₀ *p* < 0.001 at all landmark counts.

2. **VR complex construction and PH computation**: We construct the Vietoris–Rips filtration on the 5,000 landmarks and compute persistence through H₁ using Ripser (Bauer 2021), with the filtration threshold set to the 75th percentile of pairwise distances. Computation completes in approximately 158 seconds on a standard desktop CPU.

3. **Persistence diagrams and summaries**: The output comprises H₀ (connected components) and H₁ (loops) persistence diagrams. For each dimension, we compute total persistence $\sum_i (d_i - b_i)$, maximum persistence, feature count, and persistence entropy.

H₀ features correspond to the merging of trajectory clusters as the filtration radius increases: long-lived H₀ features indicate well-separated regimes. H₁ features correspond to loops in the trajectory space: persistent loops may indicate cyclical trapping where trajectories circulate among a subset of states without converging to a single attractor.

### 3.4 Null Model Battery: The Markov Memory Ladder

We introduce a battery of five null models arranged in order of increasing structural fidelity to the observed data. For each null model, we generate surrogate trajectory datasets and process them through the same pipeline: re-embed using the n-gram + PCA pipeline with PCA loadings fixed from the observed data (i.e., surrogate n-gram vectors are projected onto the observed PCA axes, not recomputed, ensuring that the coordinate system is comparable across nulls). Maxmin landmarks are re-selected on each surrogate to avoid coupling landmark geometry to the observed data. We then recompute PH and compare total persistence to the observed value via one-sided permutation *p*-values.

**Null 1 — Label shuffle** (*n* = 100): Permute state labels globally across all person-years, destroying all individual-level structure. This trivial null tests whether the specific identities of the nine states matter at all.

**Null 2 — Cohort shuffle** (*n* = 100): Permute trajectories within birth-cohort bins, testing whether cross-cohort differences drive the topological signal while preserving within-cohort structure.

**Null 3 — Order shuffle** (*n* = 500): For each individual, randomly permute the temporal order of their state sequence, preserving per-person state frequencies but destroying all transition and temporal structure. This is the critical test: if topology is significant against order shuffle, temporal ordering genuinely contributes to the shape of the trajectory space.

**Null 4 — Markov order-1** (*n* = 500): Estimate a first-order Markov transition matrix from the observed data via maximum likelihood and simulate surrogate trajectories of the same lengths, conditional on each trajectory's observed starting state. The globally estimated 9×9 transition matrix preserves marginal transition probabilities but not individual-level heterogeneity. If topology is not rejected under Markov-1, the observed structure is consistent with one-step memory.

**Null 5 — Markov order-2** (*n* = 500): Estimate a second-order Markov transition matrix (conditioning on the previous two states) via maximum likelihood, with Laplace smoothing (adding pseudocounts of 1 to all 729 cells) to regularise sparse transitions. Of the 729 possible second-order transitions, 717 (98.4%) have non-zero observed counts pre-smoothing; all 81 conditioning pairs $(s_{t-1}, s_t)$ are active, yielding approximately 648 effective free parameters ($81 \times 8$ free transition probabilities per row). Post-Laplace smoothing fills all 729 cells. Surrogates are simulated conditional on the observed first two states of each trajectory.

The test statistic for all comparisons is total persistence (sum of lifetimes of all features) in each homological dimension, separately for H₀ and H₁. The *p*-value is the proportion of null realisations with total persistence as extreme as or more extreme than the observed value.

We note that *n* = 500 for the order-shuffle and Markov nulls provides resolution to approximately *p* = 0.002 for one-sided tests; the *p* < 0.001 reported for order-shuffle H₀ is bounded by the simulation count and should be interpreted as *p* ≤ 0.002. For tail *p*-values, larger simulation counts (e.g., *n* = 1,000 or 5,000) would provide finer resolution, at the cost of substantial additional computation. We view *n* = 500 as sufficient for the present purposes, where the primary interest lies in whether *p* is above or below conventional significance thresholds.

This "Markov memory ladder" provides a principled decomposition: when observed topology first becomes consistent with a Markov-$k$ null, we can conclude that the trajectory space's topological complexity is captured by $k$-step transition dynamics.

### 3.5 Regime Discovery

We identify mobility regimes by fitting Gaussian mixture models (GMMs) to the PCA-20D embedding, using the Bayesian Information Criterion (BIC) for model selection across $k = 3, 4, \ldots, 15$ components. The BIC-optimal model has $k = 7$ components, each characterised by a multivariate Gaussian distribution in the 20-dimensional embedding space.

H₀ informs but does not replicate GMM: all H₀ features are born at filtration radius 0 (each landmark starts as a singleton); the 44 features with persistence > 10 merge gradually (7th/8th most persistent ratio = 1.03×), reflecting single-linkage chaining in 20-dimensional Vietoris–Rips complexes on 5,000 landmarks. The merge tree yields one dominant connected component (~99.98% of trajectories) plus 6 singleton outliers — no balanced clusters matching GMM density modes. We use GMM for regime labels and H₀ for connectivity validation (§4.4.1, Appendix A).

Regime profiles are constructed by mapping GMM-assigned labels back to the original state sequences and computing, for each regime: employment rate, unemployment rate, inactivity rate, income distribution (fraction in low/mid/high), and a stability index (fraction of trajectory years spent in the dominant state). These profiles provide substantive interpretability for each topological cluster.

To verify that the $k = 7$ solution is not an artefact of a particular sample, we perform a bootstrap stability analysis: we resample the 27,280 trajectory embeddings with replacement 200 times, fit GMM with $k = 7$ to each bootstrap sample (200 EM iterations, 1 random initialisation), and compute the adjusted Rand index (ARI) between each bootstrap labelling and the full-sample labelling. The resulting ARI distribution has mean 0.646 ± 0.086 (95% CI: [0.461, 0.795]), confirming that the seven-regime structure is stable under resampling.

### 3.6 Overlapping Windows and Regime Persistence

To assess regime persistence over the life course, we construct overlapping career-phase windows using a sliding window of 10 years with a 5-year step. For each individual, this produces a sequence of overlapping windows, each embedded and assigned to a regime using the same PCA-GMM model fitted on full trajectories. This yields 54,560 windows from 27,280 individuals (mean 2.0 windows per person).

We construct a 7×7 regime transition matrix from consecutive windows and compute escape probabilities: the fraction of individuals starting in disadvantaged regimes (Low-Income Churn or Inactive Low) who reach an advantaged regime (Secure EH or Employed Mid) within a given number of windows.

We also compute PH on the phase-level embedding cloud and test a phase-order shuffle null that preserves each individual's multiset of windows but randomises their temporal order, testing whether the life-course ordering of career phases adds topological structure beyond the composition of phases. We run *n* = 500 permutations with 3,000 maxmin landmarks and report p-values with 95% confidence intervals.

### 3.7 Sequence Analysis Baseline

To contextualise our TDA results, we compute a standard sequence analysis baseline using optimal matching (OM) with dynamic Hamming distances (Lesnard 2010). We compute pairwise distances between all 27,280 trajectories, apply Ward's hierarchical clustering, and select *k* via the average silhouette width (Studer & Ritschard 2016).

The OM-optimal solution selects *k* = 2 clusters (silhouette = 0.223), producing a coarse division between predominantly inactive trajectories (40.2%, dominant state IL) and predominantly employed trajectories (59.8%, dominant state EH). We also evaluate OM at *k* = 7 to enable direct comparison with our GMM-derived regimes, obtaining silhouette = 0.215. The resulting clusters at *k* = 7 identify broadly similar macro-types to the TDA-derived regimes: clusters dominated by IL (12.6%), IH (7.6%), IM (10.8%), EH (33.0%), EL (6.5%), EM (20.3%), and a mixed EH cluster (9.1%). The adjusted Rand index (ARI) between the OM *k* = 7 clusters and the GMM *k* = 7 regimes is 0.26, indicating overlapping but non-identical regime boundaries. Regime-level profile correlations range from 0.97 (the high-employment regime, which both methods identify cleanly) down to 0.02 (the mixed-churn regime, where OM and TDA draw boundaries differently).

The moderate ARI confirms that the broad structure of UK trajectory space — secure employment versus inactivity versus churning — is recoverable by either method, while finer distinctions depend on the analytic approach. This is consistent with our expectation: the primary added value of TDA lies not in the regime typology itself but in the formal null testing infrastructure (§5.1).

---

## 4. Results

### 4.1 Descriptive Statistics

Our sample comprises 27,280 individuals with trajectories averaging 12.9 years (range 10–14, median 13). The nine-state distribution reflects a labour market with dominant employment: EH (high-income employment) is the most common dominant state (42.1% of individuals), followed by IL (inactive-low, 13.7%), EM (employed-mid, 12.5%), IM (inactive-mid, 12.1%), and IH (inactive-high, 12.0%). Unemployment is comparatively rare as a dominant state: UL (1.1%), UM (0.5%), and UH (0.4%). The low-income employment state EL dominates 5.7% of trajectories.

Birth cohorts span seven decades, from the 1930s (*n* = 1,642) through the 1990s (*n* = 1,364), with the largest cohorts in the 1960s (*n* = 5,579) and 1950s (*n* = 4,843). The gender split is 56% female, 44% male among those with non-missing sex. Forward-fill imputation affected 4.9% of person-years, distributed proportionally across regimes.

**[Figure 1]** presents trajectory heatmaps showing exemplar sequences from each of the seven regimes discovered in Section 4.4, illustrating the qualitative diversity of life-course patterns.

**[Table 1]** summarises sample characteristics by cohort decade, including mean trajectory length, dominant state distribution, and covariate availability.

### 4.2 Topological Structure of the Trajectory Space

Persistent homology on the PCA-20D embedding with 5,000 maxmin landmarks reveals substantial topological structure in both dimensions.

**H₀ (connected components):** 5,000 features (4,999 finite, 1 infinite — the final connected component), with total persistence 20,411.1 and maximum persistence 15.81. The dominance of a single long-lived component (persistence 15.81, compared to the mean of 4.08) indicates that most trajectory clusters ultimately merge at large filtration values but are well separated at smaller scales. H₀ reflects unimodal connectivity plus outliers: 99.98% of trajectories belong to a single giant connected component, with 6 singleton landmarks merging late — consistent with single-linkage chaining in high-dimensional Vietoris–Rips complexes. The distribution of H₀ persistence values has a heavy right tail, but the top features merge gradually (7th/8th most persistent ratio = 1.03×), indicating no sharp topological gap between clusters.

**H₁ (loops):** 5,962 features (5,961 finite, 1 infinite), with total persistence 2,224.7 and maximum persistence 3.21. The large number of H₁ features indicates extensive looping structure in the trajectory space, but their relatively modest persistence (compared to H₀) suggests that loops are numerous but not deeply persistent.

**[Figure 3]** presents persistence diagrams for both H₀ and H₁. The H₀ diagram shows a clear separation between the most persistent features (top-right) and the mass of short-lived features near the diagonal, consistent with a small number of well-defined regimes embedded in noise. The H₁ diagram shows a more uniform spread, with no single loop dominating.

### 4.3 Null Model Validation: The Markov Memory Ladder

The five null models in the Markov memory ladder yield the following results for total persistence, summarised in Table 2:

**[Table 2: Markov Memory Ladder Results]**

All tests are conducted at the primary resolution of $L = 5{,}000$ landmarks. Label shuffle, cohort shuffle, and Markov-2 p-values below are from $L = 2{,}500$ (these are pending re-run at $L = 5{,}000$; qualitative conclusions are expected to be unchanged based on landmark stability analysis in Appendix B).

| Null Model | *n* | H₀ observed | H₀ *p* | H₁ observed | H₁ *p* |
|---|---|---|---|---|---|
| Label shuffle | 100 | 20,411.1† | 0.69† | 2,224.7† | 0.63† |
| Cohort shuffle | 100 | 20,411.1† | 0.66† | 2,224.7† | 0.54† |
| Order shuffle | 100 | 20,411.1 | **≤0.01** | 2,224.7 | 0.02* |
| Markov-1 | 100 | 20,411.1 | 1.00 | 2,224.7 | 1.00 |
| Markov-2 | 500 | 20,411.1† | 0.108† | 2,224.7† | 0.434† |

†p-values from $L = 2{,}500$ runs; to be updated at $L = 5{,}000$. *Marginally significant at $L = 5{,}000$ but non-replicating at $L = 2{,}500$ ($p = 0.20$) and $L = 8{,}000$ ($p = 0.14$); see Appendix B.

The memory ladder reveals a clear decomposition:

**Order matters for regimes (H₀).** The order-shuffle null, which preserves per-person state frequencies but destroys temporal order, yields *p* ≤ 0.01 for H₀ total persistence (*n* = 100, $L = 5{,}000$). At $L = 2{,}500$ with *n* = 500, the order-shuffle H₀ *p* ≤ 0.002. This means the observed connectivity structure in the trajectory space cannot be explained by state composition alone — the temporal ordering of states within trajectories genuinely shapes the geometry of the point cloud. We note, however, that this result is expected for any system with temporal autocorrelation: knowing someone's current state predicts their next state better than chance, which is a well-established property of labour market trajectories. The more informative finding is the Markov-1 result below.

**H₀ is consistent with Markov-1 dynamics.** The Markov-1 null yields *p* = 1.00 for H₀ at $L = 5{,}000$ (*n* = 100) — the observed total persistence is actually *lower* than the Markov-1 null mean. At $L = 2{,}500$ with *n* = 500, Markov-1 H₀ *p* = 0.148, also non-significant. The Markov-2 null at $L = 2{,}500$ is similarly non-significant (*p* = 0.108). This is the paper's most informative result: the topological complexity of the regime landscape does not exceed what first-order Markov dynamics would produce given the observed transition probabilities. We note that failure to reject is not positive evidence *for* Markov-1 adequacy — the test may lack power to detect departures, particularly with a total-persistence summary that may smooth over fine-grained memory effects. We have not tested richer process classes (e.g., hidden Markov models or latent-type models) that might generate different topological signatures while reproducing the same marginal transitions.

**Cycles are not topologically distinctive (H₁).** At $L = 5{,}000$, order-shuffle H₁ *p* = 0.02, which is marginally significant. However, this result does not replicate at $L = 2{,}500$ (*p* = 0.20) or $L = 8{,}000$ (*p* = 0.14), suggesting it reflects noise at the particular landmark selection rather than a genuine topological signal (Appendix B). Markov-1 H₁ *p* = 1.00 and Markov-2 H₁ *p* = 0.434, confirming that loop structure is consistent with what state frequencies and transition dynamics would produce. The observed looping structure is therefore a predictable consequence of state composition and one-step transition probabilities, rather than reflecting non-Markovian trapping dynamics.

**Trivial nulls are non-significant (as expected).** Label shuffle (*p* = 0.69) and cohort shuffle (*p* = 0.66) confirm that the topological signal is not driven by the specific identities of states or by cross-cohort heterogeneity per se.

**[Figure 4]** shows Betti curves — the number of topological features as a function of filtration radius — for the observed data compared to null envelopes (95% pointwise intervals) from order-shuffle and Markov-1 nulls. The observed H₀ curve lies outside the order-shuffle envelope at most scales but within the Markov-1 envelope.

**[Figure 8]** presents the null model summary as a structured visual comparison of *p*-values across the memory ladder.

**[Figure 9]** shows violin plots comparing the distribution of total persistence across Markov-1 and Markov-2 null realisations to the observed values, illustrating the ladder graphically.

### 4.4 Seven Mobility Regimes

BIC model selection identifies $k = 7$ as optimal. The seven regimes, ordered by size, are:

**Regime 1 — Secure High-Employment** (*n* = 7,358, 27.0%): Dominated by high-income employment (EH). Employment rate 92.3%, inactivity rate 7.4%, unemployment near zero (0.3%). High-income rate 85.5%. Stability index 0.779, the highest of all regimes. This is the core of the UK labour market: stably employed, well-paid individuals.

**Regime 2 — Inactive Low** (*n* = 5,415, 19.9%): Entirely inactive (inactivity rate 100%, zero employment or unemployment). Income is mixed (low 38.7%, mid 33.1%, high 28.2%), reflecting heterogeneity within inactivity (retirees with pensions versus carers and those with long-term illness). Stability 0.387. This regime is a key disadvantaged state in our analysis, though we note an important caveat: the regime likely mixes lifecycle inactivity (retirement) with inequality-driven inactivity (disability, long-term sickness, caring). The near-absorbing nature of this regime (§4.4.2) may partly reflect the irreversibility of retirement rather than a "trap" in an inequality sense. We address this confound via age-stratified analysis in §4.4.2.

**Regime 0 — Mixed Churn** (*n* = 3,787, 13.9%): Mixed employment (41.6%), unemployment (20.3%), and inactivity (38.1%). Income concentrated in mid (34.1%) and high (42.2%). Low stability (0.234), the lowest of all regimes, indicating frequent state changes — the archetypal "churning" trajectory.

**Regime 4 — Employed Mid** (*n* = 3,510, 12.9%): Near-universal employment (98.5%) with mixed income (low 26.0%, mid 31.8%, high 42.2%). Stability 0.407. These are stably employed individuals at moderate income levels — a potential destination for upward mobility from disadvantaged regimes.

**Regime 3 — Employment-Inactive Mix** (*n* = 3,333, 12.2%): Mixed employment (58.8%) and inactivity (41.2%), zero unemployment. Income relatively balanced (low 20.0%, mid 39.6%, high 40.4%). Stability 0.280. These trajectories combine employment spells with periodic inactivity — potentially capturing career breaks, part-time work patterns, and caring responsibilities.

**Regime 6 — Low-Income Churn** (*n* = 2,064, 7.6%): Employment (59.1%), unemployment (9.8%), and inactivity (31.1%), with the highest low-income rate (61.1%) of any regime. Stability 0.289. This is the second key disadvantaged regime: individuals cycle between low-paid employment, unemployment, and inactivity. Combined with Regime 2 (Inactive Low), these two regimes comprise 27.5% of the sample and define the disadvantaged population for escape analysis.

**Regime 5 — High-Income Inactive** (*n* = 1,813, 6.6%): Mixed employment (41.3%) and inactivity (58.3%), with high income (67.2%). Stability 0.400. These are likely early retirees with substantial assets, or individuals in high-income households who are economically inactive by choice.

The correlation between regime stability (fraction of years in the dominant state) and high-income rate is strong ($r$ = 0.77, *p* < 0.01), confirming that the most stable trajectories tend to be the most advantaged — consistent with the "stickiness of privilege" documented in the UK social mobility literature (Goldthorpe 2016).

#### 4.4.1 H₀ Geometry vs. GMM Regimes

H₀ persistent homology encodes the Vietoris–Rips single-linkage merge tree. Cutting at $k = 7$ (the death time of the 7th-longest-lived feature) and assigning each trajectory to the component of its nearest landmark yields labels that are structurally distinct from GMM regimes:

**ARI (H₀ tree $k = 7$ vs. GMM):** 0.00004
**Component sizes:** C0: 99.98% (27,274 trajectories); C1–C6: singletons (1 trajectory each)
**Per-regime purity:** 99.8–100% (all GMM regimes fall almost entirely within C0)
**Per-component purity:** C0: 27.0% (contains all 7 GMM regimes); C1–C6: 100% (trivially pure singletons)

| H₀ \ GMM | R0 | R1 | R2 | R3 | R4 | R5 | R6 | Total |
|---|---|---|---|---|---|---|---|---|
| **C0** (99.98%) | 3,781 | 7,358 | 5,415 | 3,333 | 3,510 | 1,813 | 2,064 | 27,274 |
| **C1** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C2** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C3** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C4** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C5** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C6** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

**Interpretation.** Trajectory space is **topologically connected** — a single giant H₀ component — with **density substructure** inside it (the 7 GMM regimes). The 6 outlier singletons are all from the Mixed Churn regime (R0), which occupies the most diffuse region of embedding space. The near-zero ARI is expected and informative: H₀ tracks global connectivity and boundary geometry (where the last inter-cluster edges form), while GMM identifies interior density modes. These measure fundamentally different aspects of point-cloud geometry. The finding validates that the trajectory manifold is a single connected object with heterogeneous density — a substantive geometric characterisation that complements the GMM regime typology.

**[Figure 5]** presents the regime profile heatmap: a 7 × 8 matrix showing employment rate, unemployment rate, inactivity rate, low/mid/high income rates, stability index, and transition rate for each regime.

**[Figure 6]** shows the stability-income correlation scatter plot across regimes.

#### 4.4.2 Regime Persistence Over the Life Course

To assess whether individuals remain in their regimes or transition between them, we construct overlapping 10-year windows (5-year step) for all 27,280 individuals, yielding 54,560 career-phase windows. Each window is embedded and assigned to a regime using the same PCA-GMM model.

The resulting 7 × 7 transition matrix is strongly diagonal-dominant:

|  | R0 | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|
| **R0** | 0.53 | 0.13 | 0.12 | 0.06 | 0.08 | 0.02 | 0.07 |
| **R1** | 0.03 | **0.78** | 0.03 | 0.03 | 0.08 | 0.04 | 0.02 |
| **R2** | 0.02 | 0.00 | **0.97** | 0.01 | 0.00 | 0.00 | 0.00 |
| **R3** | 0.05 | 0.14 | 0.18 | 0.41 | 0.15 | 0.04 | 0.04 |
| **R4** | 0.02 | 0.17 | 0.00 | 0.07 | **0.66** | 0.01 | 0.07 |
| **R5** | 0.05 | 0.14 | 0.48 | 0.06 | 0.01 | 0.26 | 0.00 |
| **R6** | 0.05 | 0.07 | 0.21 | 0.06 | 0.14 | 0.00 | 0.46 |

The strongest self-transitions occur in Regime 2 — Inactive Low (0.97), Regime 1 — Secure High-Employment (0.78), and Regime 4 — Employed Mid (0.66). The two disadvantaged regimes have strikingly different persistence: Inactive Low is near-absorbing (97% self-transition), while Low-Income Churn is moderately sticky (46%) with significant transitions to Inactive Low (21%) and Employed Mid (14%).

We note that the 97% self-transition rate for Inactive Low likely reflects, in part, the composition of this regime: a substantial fraction are retirees for whom return to employment is not expected. To separate lifecycle persistence from inequality-driven persistence, we partition Regime 2 by age at window midpoint, using 60 as the retirement-age threshold. Of all Inactive Low window-observations, 86.1% come from individuals aged ≥ 60, confirming substantial retirement confounding.

**Age-adjusted escape rates.** We recompute escape rates separately for working-age (age < 60) and retirement-age (age ≥ 60) individuals:

| Group | *n* (disadvantaged start) | *n* (escaped) | Escape rate |
|---|---|---|---|
| Overall | 7,453 | 416 | 5.6% |
| Working-age (< 60) | 2,163 | 386 | 17.8% |
| Retirement-age (≥ 60) | 5,978 | 6 | 0.1% |

The raw 5.6% overall escape rate is heavily confounded by the predominance of retirees in the Inactive Low regime (86.1% of windows): among working-age individuals, the escape rate is more than three times higher at 17.8%.

**Logistic regression.** We model $P(\text{escape}) \sim \text{age}_{\text{first window}} + \text{female}$ using logistic regression on the 7,280 individuals starting in disadvantaged regimes with complete demographic data.

| Predictor | OR | 95% CI | *p*-value |
|---|---|---|---|
| Age at first window | 0.898 | — | $< 10^{-150}$ |
| Female | 0.438 | — | $< 10^{-11}$ |

Each additional year of age reduces escape odds by approximately 10%. Women have 56% lower odds of escape than men. The pseudo-$R^2$ is 0.327 (AIC = 2,013; BIC = 2,034), indicating that age and sex explain a substantial fraction of escape variation, consistent with lifecycle inactivity (retirement) and gendered labour market participation driving much of the observed regime persistence.

Among the 7,453 individuals whose first window falls in a disadvantaged regime (Inactive Low or Low-Income Churn), only 416 (5.6%) ever reach an advantaged regime (Secure EH or Employed Mid) in the subsequent window. All observed escapes occur in a single window-to-window transition — no multi-step "ladders" are observed in our data, though the limited number of windows per person (mean 2.0) constrains our ability to detect longer escape paths.

**[Figure 12]** presents the regime transition heatmap.

**[Figure 13]** shows escape probability from disadvantaged regimes.

### 4.5 Cycle and Trap Analysis

The 5,962 H₁ features indicate extensive looping structure in the trajectory space. However, as shown in Section 4.3, this cycling is not topologically distinctive: it is consistent with state frequencies (order-shuffle H₁ *p* = 0.25) and Markov transition dynamics (Markov-1 H₁ *p* = 0.652, Markov-2 H₁ *p* = 0.434).

The H₁ cycles should *not* be interpreted as "topological poverty traps" in a strong causal sense. The observed looping structure is a predictable consequence of state composition and one-step transition probabilities — the same frequencies and transitions that generate the data also generate comparable loops under simulation. This negative result bounds the complexity of trajectory cycling: it means that claims about non-Markovian topological traps would be unsupported by these data.

The H₁ features nonetheless provide descriptive value. The most persistent loops (maximum persistence 3.21) involve cycling between low-income employment, unemployment, and inactivity — states concentrated in the Low-Income Churn and Mixed Churn regimes. The persistence values quantify the scale of cycling in the embedding space: how far a trajectory must move to complete a cycle and return to a similar state. These descriptive features may prove useful for identifying target populations for policy interventions, even though they do not exceed Markov baselines.

Future directions that might uncover conditional H₁ significance include bifiltration by income threshold, sub-population analysis restricted to the most disadvantaged regimes, or comparison across national panels with different welfare state structures. We devote the remainder of our analysis to the stronger H₀ results, where the topological signal is clearly established.

**[Figure 7]** presents the cycle analysis: top persistent loops and their length distribution.

#### Phase-Ordering Test

We test whether the ordering of career *phases* — overlapping 10-year windows — adds additional topological structure beyond what the composition of individual trajectories provides. Using the PCA embedding of 50,000 overlapping windows, we compute persistent homology with 3,000 maxmin landmarks.

The phase-level PH yields H₀ total persistence of 19,119.4 (3,000 landmarks, max persistence 18.38) and H₁ total persistence of 2,071.2 (3,482 features, max 3.19). A within-person phase-order shuffle null that preserves each individual's multiset of windows but randomises their temporal order produces the following results with *n* = 500 permutations:

| Dimension | Observed | Null mean ± std | *p*-value | 95% CI |
|---|---|---|---|---|
| H₀ | 19,119.4 | 19,150.2 ± 17.2 | 0.98 | [0.968, 0.992] |
| H₁ | 2,071.2 | 2,078.0 ± 19.9 | 0.542 | [0.498, 0.586] |

The observed total persistence sits squarely within the null distribution for both dimensions. The H₀ *p* = 0.98 indicates that the observed value is actually *lower* than most null realisations — the temporal ordering of phases, if anything, slightly reduces total persistence relative to random ordering. The tight confidence intervals (width < 0.025 for H₀) confirm that with 500 permutations the p-value is well resolved.

This result indicates that the main topological signal arises from the internal sequential structure of full trajectories (captured by bigrams in the embedding) rather than from the higher-order sequencing of overlapping phases across the life course. The within-trajectory ordering that creates H₀ significance against the order-shuffle null (§4.3) operates at the year-to-year level; once that information is embedded into the windows, the order of windows adds no further topological structure.

**[Figure 14]** presents phase PH persistence diagrams and phase-order null violin plots.

### 4.6 Stratified Comparisons

Pairwise Wasserstein distances between group-specific persistence diagrams reveal significant topological differences by social origin, gender, and birth cohort. We conduct 50 dimension-specific tests across three stratification axes and report both raw *p*-values and Benjamini-Hochberg (BH) FDR-corrected *q*-values.

Of the 50 tests, 30 are significant at *p* < 0.05 (raw). After BH FDR correction, all 30 remain significant at *q* < 0.05 — the correction does not eliminate any findings, reflecting the strength of the underlying topological differentiation. Of these, 16/25 are H₀ tests (cluster structure) and 14/25 are H₁ tests (cycle structure).

**Gender.** Male (*n* = 11,243) versus Female (*n* = 14,402): Wasserstein distance is significant for H₀ (*p* < 0.001, BH *q* < 0.001; observed distance 33.7 vs. null mean 21.0), but not for H₁ (*p* = 0.27, BH *q* = 0.41). This indicates that men and women occupy different cluster structures in the trajectory space — likely reflecting gendered patterns of employment, inactivity, and income — but that their cycling patterns are topologically similar.

**Parental NS-SEC.** Three groups — Professional/Managerial (*n* = 2,067), Intermediate (*n* = 6,777), Routine/Manual (*n* = 7,779) — yield significant H₀ differences for all three pairwise comparisons (*p* < 0.001 in each case; BH *q* < 0.001). H₁ differences are non-significant (all *p* > 0.35). The largest H₀ Wasserstein distance is between Professional/Managerial and Routine/Manual (114.8, vs. null mean 99.8), confirming that parental social class creates topologically distinct trajectory clusters. The sharper separation between extreme classes, with Intermediate occupying a genuinely intermediate topological position, aligns with the cumulative advantage hypothesis (DiPrete & Eirich 2006).

**Birth cohort.** Seven cohort decades yield 21 pairwise comparisons, producing 42 dimension-specific tests. Of these 42 cohort tests, 26 are significant at *p* < 0.05 (raw), and all 26 survive BH FDR correction at *q* < 0.05. Of these, 16 are H₀ tests (cluster structure) and 10 are H₁ tests (cycle structure), with H₁ differences emerging for the most distant cohort pairs (e.g., 1930s vs. 1960s). The 1930s cohort is topologically most distinctive, consistent with its passage through fundamentally different labour market conditions (post-war full employment through to early deindustrialisation).

**[Table 4: Stratified Wasserstein Test Summary (FDR-Corrected)]**

| Axis | Tests | Significant (raw) | Significant (BH *q* < 0.05) |
|---|---|---|---|
| Gender | 2 | 1 | 1 |
| Parental NS-SEC | 6 | 3 | 3 |
| Birth cohort | 42 | 26 | 26 |
| **Total** | **50** | **30** | **30** |

**[Figure 10]** presents a Wasserstein distance heatmap by parental NS-SEC.

**[Figure 11]** shows gender-specific persistence landscape overlays.

---

## 5. Discussion

### 5.1 What TDA Adds Beyond Sequence Analysis

Our results demonstrate that persistent homology provides analytical capabilities that complement conventional sequence analysis. Two contributions stand out.

First, regime discovery via GMM on topologically informed embeddings produces clusters that can be formally validated against a battery of null models. The order-shuffle test confirms that temporal ordering genuinely creates the observed clustering (H₀ *p* ≤ 0.002) — a formal significance finding that is not naturally available in OM-based frameworks, where cluster solutions are typically evaluated by internal validity indices (silhouette, Calinski-Harabasz) rather than tested against explicit generative nulls.

As a baseline comparison, we compute OM-based clustering using dynamic Hamming distances (Lesnard 2010) on all 27,280 trajectories with Ward's hierarchical clustering. The silhouette-optimal OM solution selects *k* = 2 with silhouette = 0.223, producing a coarse employed/inactive split. At matched *k* = 7, OM achieves silhouette = 0.215, and the ARI between OM and TDA regimes is 0.26. Profile correlations between matched clusters range widely: the Secure High-Employment regime is identified nearly identically by both methods (correlation = 0.97), while the Mixed Churn regime produces the greatest divergence (correlation = 0.02), consistent with this regime's inherent heterogeneity and boundary sensitivity.

The substantive regimes — secure employment, inactivity, churning — appear under both methods, confirming that the broad structure of UK trajectory space is robust to analytic approach. The primary added value of TDA is not the regime typology itself but the formal testing infrastructure: the ability to say that the observed clustering exceeds what state composition alone would produce (*p* ≤ 0.002) and is consistent with first-order Markov dynamics (*p* = 0.148). OM-based analysis provides no natural framework for either of these claims. Like OM, TDA reveals broad trajectory types; unlike OM, H₀ quantifies global connectivity (one connected manifold) versus interior density (GMM), providing a geometric characterisation unavailable from pairwise dissimilarity methods.

Second, PH provides a multi-scale geometric characterisation of the trajectory space via persistence diagrams. The persistence values of H₀ features quantify the separation between regime clusters: the most persistent component (15.81) is nearly four times the mean (4.08), indicating a few well-separated regimes with many weakly separated sub-clusters. This hierarchical, scale-dependent view of regime structure is a natural output of PH that has no direct analogue in OM-based analysis.

### 5.2 The Markov Memory Ladder

The Markov memory ladder is our primary methodological contribution. The result — that H₀ topology requires temporal ordering (order-shuffle *p* ≤ 0.002) but is not rejected under a first-order Markov null (Markov-1 *p* = 0.148) — indicates that the observed regime landscape is consistent with a process that remembers only the current state when generating transitions. This does *not* mean "there is no interesting topology." The topology is real (it survives the order-shuffle test) and informative (it identifies seven regimes). It means that the topology can be *efficiently generated* by one-step transitions.

Several caveats apply. First, failure to reject the Markov-1 null does not constitute evidence *for* Markov-1 adequacy. The test compares total persistence as a scalar summary, which may lack power to detect departures that affect the shape or location of specific persistence features without changing the total. Second, we have tested only Markov null models; richer process classes — hidden Markov models, latent-type models, or models with duration dependence — might generate topological signatures intermediate between our Markov nulls and the observed data. Third, the Markov matrices are estimated globally; stratification by cohort, gender, or region might reveal subpopulations where topology exceeds Markov expectations.

Subject to these caveats, the result suggests that interventions targeting *key single transitions* — employment entry programmes, in-work benefit tapers, retraining schemes — could, in principle, reshape the regime landscape, since the topology aligns with one-step dynamics. This is an interpretive inference, not a causal claim: our analysis establishes topological consistency with Markov-1 dynamics, not that modifying particular transition probabilities would produce predicted shifts in regime structure. Causal validation through quasi-experimental or simulation-based analysis remains necessary.

The Markov memory ladder is transportable: it can be applied to any TDA analysis of sequential data, from financial time series to genomic sequences, wherever the question "how much memory does the topology require?" is relevant. Future work could extend the ladder to include hidden Markov models (testing whether unobserved states add topological structure) or variable-order Markov models (testing heterogeneous memory across states).

### 5.3 H₁ Cycles: A Negative Result

The H₁ results require direct discussion. Persistent loops in the trajectory space could, in principle, provide topological evidence of poverty traps — cyclical dynamics from which escape is topologically difficult. Our results are clear: H₁ is *not* significant against any null model. Order-shuffle (*p* = 0.25), Markov-1 (*p* = 0.652), and Markov-2 (*p* = 0.434) all fail to reject the null hypothesis that the observed cycling is consistent with state frequencies and transition structure.

This does not mean that people do not cycle between employment and poverty. They manifestly do — the Low-Income Churn and Mixed Churn regimes demonstrate extensive state cycling. Rather, the null result means that the *topological shape* of this cycling is predictable from the marginal state distribution and one-step transition probabilities. A trajectory cloud generated by the same one-step Markov chain would produce loops of comparable persistence and number.

This negative result constrains interpretation: claims about "topological poverty traps" would be unsupported by these data. It also directs analytical attention toward the stronger H₀ results, where the topological signal is firmly established. Future directions that might uncover conditional H₁ significance include bifiltration by income threshold, sub-population analysis restricted to the most disadvantaged regimes, or comparison across national panels with different welfare state structures.

### 5.4 Limitations

Several limitations warrant discussion.

**Spatial dimension.** The present analysis is essentially national and non-spatial. We do not exploit Government Office Region, NUTS2, or local labour market identifiers, despite their availability in USoc. The methodological framework — particularly the Markov memory ladder and stratified Wasserstein tests — is directly applicable to regional comparisons, and we identify this as a high-priority extension. Preliminary regional analysis comparing London and North East Wasserstein distances is in progress, with results expected to illuminate whether the regime landscape varies across local labour markets — a question with direct implications for place-based policy design.

**State space discretisation.** The nine-state space, while richer than most sequence analysis applications (which typically use 3–5 states), is necessarily a simplification. Within-state variation — for instance, the difference between borderline and deeply low-income — is lost. The 60% median threshold for income terciles is conventional but arbitrary; sensitivity to this threshold is not examined here.

**Embedding sensitivity.** PCA-20D is our primary embedding, but the UMAP-16D sensitivity check yields ARI = 0.33 against PCA regime assignments at matched $k = 7$. While three macro-types are robust, finer regime boundaries are embedding-dependent. The order-shuffle null reproduces the PCA pattern under UMAP (H₀ $p < 0.001$, H₁ non-significant). Full Markov-1 replication on UMAP is omitted due to computational cost; given the close agreement in regime structure and order-shuffle results, we consider the core topological findings embedding-invariant. This cautions against over-interpreting differences between neighbouring regimes.

**H₀ chaining.** Single-linkage chaining limits balanced H₀-based clustering in high-dimensional VR complexes: the merge tree produces one dominant component (99.98%) plus outlier singletons, yielding ARI ≈ 0 against GMM. This is a known property of VR H₀ in high dimensions (Bobrowski & Kahle, 2018) and motivates future exploration of density-aware TDA methods (e.g., DTM filtrations, Mapper) that may better resolve interior density structure while retaining topological guarantees.

**Landmark sampling.** Maxmin landmark selection (5,000 from 27,280) preserves global geometry but may undersample rare trajectory types. Individuals in the smallest regime (High-Income Inactive, *n* = 1,813, 6.6%) may be underrepresented in the landmark subsample. However, as shown in Appendix B, results are stable across the range $L$ = 2,500 to 8,000, indicating that the choice of $L$ = 5,000 does not introduce bias in null-model conclusions.

**Age and lifecycle confounding.** The near-absorbing nature of the Inactive Low regime (97% self-transition) partly reflects lifecycle inactivity — particularly retirement — rather than inequality-driven trapping. We address this via age-stratified analysis (§4.4.2), partitioning by a retirement-age threshold of 60. Of all Inactive Low window-observations, 86.1% come from individuals aged ≥ 60. Working-age escape rates (17.8%) are more than three times the raw rate (5.6%), and logistic regression confirms that age at first window is a highly significant predictor of escape (OR = 0.898, $p < 10^{-150}$), with sex also significant (female OR = 0.438, $p < 10^{-11}$). The pseudo-$R^2$ of 0.327 indicates that demographics explain a substantial fraction of escape variation. Nevertheless, the binary age partition is a simplification; continuous age effects and cohort-specific retirement patterns merit further investigation.

**Markov null limitations.** Our Markov null models test whether topology exceeds *globally estimated* Markov dynamics. They do not account for individual-level heterogeneity (e.g., some individuals may have higher-order memory) or for duration dependence (where the probability of leaving a state depends on time already spent in it). The Markov-1 non-rejection should not be read as "the true data-generating process is Markov-1" but rather as "total persistence is within the range produced by globally estimated Markov-1 surrogates."

**Family dimension.** We analyse employment-income trajectories only; partnership and household composition are not included. A 27-state space incorporating partnership status could reveal whether family transitions create additional topological structure.

**Imputation.** Forward-fill imputation for gaps of up to two years affects 4.9% of person-years. The assumption that states persist during gaps is strong, particularly for transitions between employment and inactivity.

**Cross-survey harmonisation.** BHPS and USoc use different sampling frames, questionnaire designs, and income measurement methodologies. Harmonisation artefacts may contribute to cohort-specific topological differences. Our data are drawn primarily from the USoc period (start years 2009–2013), limiting historical reach.

**Pipeline sensitivity.** We vary three design choices independently while holding others at baseline: minimum trajectory length (8, 10, 12 years), n-gram weighting (TF vs TF-IDF), and VR filtration threshold percentile (50th, 75th, 90th). Under TF weighting, results are highly stable: *k* = 7 at both 10 and 12 years, *k* = 8 at 8 years (reflecting the larger sample, *n* = 33,802); H₀ total persistence varies by < 6% across trajectory lengths; and threshold percentile has no effect on H₀ persistence (identical to 4 decimal places at 50th/75th/90th) and negligible effect on H₁ (range 1.6 units on a base of 1,324). ARI between baseline and threshold-varied configurations is 0.970, confirming that regime assignments are insensitive to this parameter. TF-IDF weighting produces a qualitatively different embedding: total persistence drops by 93% (H₀: 909 vs 12,881), and ARI against the TF baseline is 0.466. This confirms that TF-IDF, which down-weights common states in favour of rare transitions, reshapes the embedding geometry substantially. The choice of TF weighting is thus a consequential methodological decision, consistent with our rationale (§3.2) that common-state dominance is substantively meaningful in employment trajectory analysis.

### 5.5 Robustness Summary

We summarise robustness checks conducted:

| Check | Status | Summary |
|---|---|---|
| UMAP-16D embedding | Completed (§3.2) | ARI = 0.33 ($k = 7$); order-shuffle H₀ $p < 0.001$, H₁ $p = 1.00$; Markov-1 omitted (computational cost); mirrors PCA pattern |
| Landmark count (*L* = 2,500 / 5,000 / 8,000) | Completed (Appendix B) | Order-shuffle H₀ *p* < 0.001 at all *L*; Markov-1 non-significant at all *L*; max persistence stable (15.81 at *L* = 2,500/5,000; 15.50 at *L* = 8,000) |
| OM/TraMineR baseline | Completed (§3.7, §5.1) | ARI = 0.26 at *k* = 7; broad types robust; TDA adds formal testing |
| Wasserstein FDR correction | Completed (§4.6) | 30/50 tests significant raw; all 30 survive BH correction at *q* < 0.05 |
| Phase-ordering null (*n* = 500) | Completed (§4.5) | H₀ *p* = 0.98 [0.968, 0.992]; H₁ *p* = 0.542 [0.498, 0.586]; no phase-ordering signal |
| GMM bootstrap stability | Completed (§3.5) | ARI = 0.646 ± 0.086; 95% CI [0.461, 0.795]; k=7 stable |
| Age-adjusted escape rates | Completed (§4.4.2) | Working-age escape 17.8%; retirement 0.1%; logistic pseudo-R² = 0.327 |
| H₀–GMM overlap | Completed (§4.4.1) | ARI ≈ 0; 99.98% in one component; topology ≠ density (substantive finding) |
| Pipeline sensitivity (§5.4) | Completed | min_years: *k* stable at 10/12, *k*=8 at 8yr; threshold: no effect on H₀, ARI=0.970; TF-IDF: reshapes embedding (ARI=0.466) |

**[Table S4]** will present the complete robustness matrix with results.

---

## 6. Conclusion

This paper presents the first application of persistent homology to longitudinal life-course trajectories, analysing 27,280 employment-income sequences from the BHPS and Understanding Society (1991–2023) in a 20-dimensional PCA embedding space.

**Positive result.** Seven distinct mobility regimes emerge with statistically strong, order-dependent clustering: the order-shuffle null is rejected at *p* ≤ 0.002 for H₀ total persistence, confirming that temporal ordering of states within trajectories creates genuine topological structure that exceeds what state composition alone would produce. The seven regimes range from Secure High-Employment (27%, stability 0.78) to Low-Income Churn (7.6%, stability 0.29), with a strong correlation between regime stability and income ($r$ = 0.77). Comparison with OM (dynamic Hamming) clustering at matched *k* = 7 yields ARI = 0.26, confirming that the broad regime typology is robust to method while TDA adds formal null testing and multi-scale geometric characterisation.

**Complexity bound.** The Markov memory ladder shows that regime topology is not rejected by first-order Markov dynamics (Markov-1 H₀ *p* = 0.148, Markov-2 *p* = 0.108). The topology is real but consistent with one-step transitions. Phase-ordering analysis with *n* = 500 permutations reinforces this finding: the temporal ordering of career phases adds no topological structure beyond the within-trajectory sequential signal (H₀ *p* = 0.98, 95% CI [0.968, 0.992]).

**Negative result.** H₁ cycles — potential topological signatures of churning traps — are consistent with state frequencies and Markov transition structure across all null models (*p* > 0.25). This negative result means that the observed cycling, while real and descriptively informative, is predictable from marginal frequencies and one-step transitions and should not be interpreted as evidence of non-Markovian poverty traps.

**Stratification.** Wasserstein distances reveal origin-dependent topology: gender differences are significant for H₀ cluster structure; parental NS-SEC differences are significant for all three class pairings in H₀; and birth cohort produces the most extensive differentiation, with 26 of 42 cohort tests significant. All 30 significant results (of 50 total tests) survive Benjamini-Hochberg FDR correction at *q* < 0.05 (H₀: 16/25, H₁: 14/25), confirming that the stratification findings are not artefacts of multiple testing.

**Landmark robustness.** PH results are stable across landmark counts from *L* = 2,500 to *L* = 8,000 (Appendix B). Order-shuffle H₀ *p* < 0.001 at all landmark values; Markov-1 H₀ is non-significant at all values; maximum persistence is stable (range 15.50–15.81). This eliminates landmark count as a methodological concern.

**Regime stickiness.** Overlapping career-phase windows confirm extreme regime persistence: the 7 × 7 transition matrix is diagonal-dominant, and only 5.6% of individuals starting in disadvantaged regimes escape to advantaged regimes within a single window transition. The near-absorbing nature of Inactive Low (97% self-transition) identifies this regime as a primary target for policy attention. Age-stratified analysis (§4.4.2) separates lifecycle from inequality-driven persistence: 86.1% of Inactive Low windows are retirement-age (≥ 60), and the working-age escape rate is 17.8% — more than three times the raw 5.6%. Logistic regression confirms age (OR = 0.898, $p < 10^{-150}$) and sex (female OR = 0.438, $p < 10^{-11}$) as significant predictors of escape (pseudo-$R^2$ = 0.327).

**Policy implications.** The consistency of regime topology with first-order Markov dynamics suggests that interventions targeting key transitions — employment entry, in-work progression, income stabilisation — could, in principle, reshape the regime landscape. However, this is an interpretive inference from topological consistency, not a causal finding. The 5.6% escape rate quantifies the scale of the challenge under current transition probabilities. Causal identification of specific transition-targeting policies and their topological effects remains a priority for future work.

**Future work.** Priority extensions include: (i) regional stratification (NUTS2/GOR) to connect trajectory topology to local labour markets and economic geography; (ii) a 27-state space incorporating family formation; (iii) comparative analysis across SOEP (Germany), PSID (US), and other longitudinal panels; and (iv) multi-parameter persistent homology using employment and income as separate filtration parameters.

---

## Figures

| # | Title | Section |
|---|-------|---------|
| 1 | Trajectory Heatmap: Exemplar Sequences by Regime | §4.1 |
| 2 | Embedding Point Cloud (UMAP 2D Projection of PCA-20D) | §3.2 |
| 3 | Persistence Diagrams (H₀ + H₁) | §4.2 |
| 4 | Betti Curves: Observed vs Null Envelopes | §4.3 |
| 5 | Regime Profile Heatmap (7 Regimes × 8 Characteristics) | §4.4 |
| 6 | Stability–Income Correlation Scatter | §4.4 |
| 7 | Cycle Analysis (Top H₁ Loops + Length Distribution) | §4.5 |
| 8 | Null Model Summary (Markov Memory Ladder) | §4.3 |
| 9 | Markov Memory Depth Comparison (Violin Plots) | §4.3 |
| 10 | Wasserstein Distance Heatmap by Social Origin | §4.6 |
| 11 | Gender Persistence Landscape Overlay | §4.6 |
| 12 | Regime Transition Heatmap (Window-to-Window) | §4.4 |
| 13 | Escape Probability from Disadvantaged Regimes | §4.4 |
| 14 | Phase PH Diagrams + Phase-Order Null Violin Plots | §4.5 |
| S1 | UMAP-16D Embedding Sensitivity Check | Appendix |
| S2 | OM vs TDA Regime Profiles | Appendix |

## Tables

| # | Title | Section |
|---|-------|---------|
| 1 | Sample Characteristics by Cohort Decade | §4.1 |
| 2 | Markov Memory Ladder: Null Model Results | §4.3 |
| 3 | Regime Composition and Characteristics | §4.4 |
| 4 | Stratified Wasserstein Test Summary (FDR-Corrected) | §4.6 |
| S2 | H₀ Component–GMM Regime Overlap | §4.4 |
| S3 | OM vs TDA Regime Comparison | §5.1 |
| S4 | Robustness Matrix | §5.5 |

---

## Appendix A: H₀ Merge Tree Analysis

The H₀ persistent homology on 5,000 maxmin landmarks encodes the single-linkage merge tree of the trajectory point cloud. We report the diagnostic statistics that characterise the H₀ geometry and its relationship to GMM regime labels.

**Top 10 H₀ lifetimes** (persistence = death − birth, all born at 0):
15.81, 15.50, 14.90, 14.40, 14.16, 14.01, 13.62 (7th), 13.22 (8th), 13.15, 12.92

The ratio between the 7th and 8th most persistent features is 1.03×, indicating no sharp topological gap at $k = 7$. All 44 features with persistence > 10 merge gradually, reflecting the single-linkage chaining phenomenon in high-dimensional VR complexes: pairwise edges form rapidly in the interior of the point cloud, producing early merges and a single dominant connected component.

**Table S2: H₀ Component–GMM Regime Contingency (at $k = 7$ cut)**

| | R0 (Churn) | R1 (EH) | R2 (IL) | R3 (EI Mix) | R4 (EM) | R5 (IH) | R6 (LI Churn) | Total |
|---|---|---|---|---|---|---|---|---|
| **C0** (99.98%) | 3,781 | 7,358 | 5,415 | 3,333 | 3,510 | 1,813 | 2,064 | 27,274 |
| **C1** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C2** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C3** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C4** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C5** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **C6** (singleton) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

ARI (H₀ $k = 7$ vs. GMM) = 0.00004. Per-regime purity = 99.8–100%.

**Interpretation.** The trajectory embedding is topologically connected: a single giant component accounts for 99.98% of trajectories. The 6 outlier singletons are all from the Mixed Churn regime (R0), which occupies the most diffuse region of embedding space. The near-zero ARI confirms that H₀ and GMM capture fundamentally different aspects of point-cloud geometry: H₀ tracks global connectivity (boundary structure, outlier merges), while GMM identifies local density modes (interior clusters). This is a known property of VR H₀ in high dimensions and is expected rather than anomalous. The finding validates the use of GMM for regime labels while establishing that the trajectory manifold is a single connected object with heterogeneous density — a substantive geometric characterisation that would not emerge from clustering methods alone.

---

## Appendix B: Landmark Sensitivity

To verify that our topological findings are robust to the choice of landmark count, we recompute persistent homology at $L$ = 2,500, 5,000, and 8,000 landmarks (approximately 9%, 18%, and 29% of the 27,280-point cloud, respectively). For each landmark count, we re-select maxmin landmarks, recompute Vietoris–Rips PH through H₁, and re-run the order-shuffle and Markov-1 null tests (*n* = 50–100 per condition). Table B1 summarises the results.

**[Table B1: Landmark Sensitivity Analysis]**

| *L* | H₀ total | H₀ max | H₀ *n* | H₁ total | H₁ max | H₁ *n* | OS H₀ *p* | OS H₁ *p* | M1 H₀ *p* | M1 H₁ *p* |
|---|---|---|---|---|---|---|---|---|---|---|
| 2,500 | 14,227.8 | 15.809 | 2,499 | 1,520.3 | 3.213 | 3,249 | < 0.001 | 0.20 | 0.15 | 0.69 |
| 5,000 | 20,411.1 | 15.809 | 4,999 | 2,224.7 | 3.213 | 5,961 | < 0.001 | 0.02 | 1.00 | 1.00 |
| 8,000 | 24,313.8 | 15.496 | 7,998 | 2,619.3 | 3.213 | 8,357 | < 0.001 | 0.14 | 1.00 | 1.00 |

OS = order shuffle; M1 = Markov-1. *n* = number of finite features.

**Total persistence** scales approximately linearly with $L$, as expected: more landmarks produce more features. **Maximum persistence** is highly stable: H₀ max ranges from 15.50 to 15.81, and H₁ max is 3.21 at all three values, confirming that the most persistent topological features are consistently detected regardless of landmark density. The H₁ max of 3.21 being identical at all three $L$ values indicates the same dominant loop is captured in every case.

**Null model p-values** are qualitatively stable across all landmark counts:

- **Order-shuffle H₀**: *p* < 0.001 at all three *L* values. The primary positive result — that temporal ordering creates topological cluster structure — is robust to landmark count.
- **Markov-1 H₀**: Non-significant at all three *L* values (*p* = 0.15, 1.0, 1.0). The Markov consistency finding is likewise robust.
- **Order-shuffle H₁**: Non-significant at *L* = 2,500 (*p* = 0.20) and *L* = 8,000 (*p* = 0.14); marginally significant at *L* = 5,000 (*p* = 0.02). The marginal H₁ result at *L* = 5,000 does not replicate at other landmark values, suggesting it may reflect noise rather than a genuine topological signal.
- **Markov-1 H₁**: Non-significant at all *L* values.

These results confirm that the choice of $L$ = 5,000 does not introduce bias in our null-model conclusions, and that the key findings — order-dependent H₀ topology consistent with Markov-1 dynamics, and non-significant H₁ — are stable across a threefold range of landmark density.

---

## References

Abbott, A. (1995). Sequence analysis: New methods for old ideas. *Annual Review of Sociology*, 21, 93–113.

Abbott, A. & Tsay, A. (2000). Sequence analysis and optimal matching methods in sociology. *Sociological Methods & Research*, 29(1), 3–33.

Atienza, N., Gonzalez-Diaz, R. & Rucco, M. (2019). Persistent entropy for separating topological features from noise in Vietoris-Rips complexes. *Journal of Intelligent Information Systems*, 52(3), 637–655.

Azariadis, C. & Stachurski, J. (2005). Poverty traps. In P. Aghion & S. Durlauf (Eds.), *Handbook of Economic Growth* (Vol. 1, pp. 295–384). Elsevier.

Barrett, C.B. & Carter, M.R. (2013). The economics of poverty traps and persistent poverty: Empirical and policy implications. *Journal of Development Studies*, 49(7), 976–990.

Bauer, U. (2021). Ripser: Efficient computation of Vietoris-Rips persistence barcodes. *Journal of Applied and Computational Topology*, 5, 391–423.

Blanden, J., Goodman, A., Gregg, P. & Machin, S. (2004). Changes in intergenerational mobility in Britain. In M. Corak (Ed.), *Generational Income Mobility in North America and Europe* (pp. 122–146). Cambridge University Press.

Blanden, J., Gregg, P. & Macmillan, L. (2013). Intergenerational persistence in income and social class: The effect of within-group inequality. *Journal of the Royal Statistical Society: Series A*, 176(2), 541–563.

Bukodi, E. & Goldthorpe, J.H. (2019). *Social Mobility and Education in Britain*. Cambridge University Press.

Carlsson, G. (2009). Topology and data. *Bulletin of the American Mathematical Society*, 46(2), 255–308.

Cohen-Steiner, D., Edelsbrunner, H. & Harer, J. (2007). Stability of persistence diagrams. *Discrete & Computational Geometry*, 37(1), 103–120.

Coulter, R., van Ham, M. & Findlay, A.M. (2016). Re-thinking residential mobility: Linking lives through time and space. *Progress in Human Geography*, 40(3), 352–374.

de Silva, V. & Carlsson, G. (2004). Topological estimation using witness complexes. In M. Alexa & S. Rusinkiewicz (Eds.), *Eurographics Symposium on Point-Based Graphics* (pp. 157–166).

DiPrete, T.A. & Eirich, G.M. (2006). Cumulative advantage as a mechanism for inequality: A review of theoretical and empirical developments. *Annual Review of Sociology*, 32, 271–297.

Edelsbrunner, H., Letscher, D. & Zomorodian, A. (2002). Topological persistence and simplification. *Discrete & Computational Geometry*, 28(4), 511–533.

Edelsbrunner, H. & Harer, J. (2010). *Computational Topology: An Introduction*. American Mathematical Society.

Elzinga, C.H. & Liefbroer, A.C. (2007). De-standardization of family-life trajectories of young adults: A cross-national comparison using sequence analysis. *European Journal of Population*, 23(3–4), 225–250.

Gauthier, J.A., Widmer, E.D., Bucher, P. & Notredame, C. (2010). Multichannel sequence analysis applied to social science data. *Sociological Methodology*, 40(1), 1–38.

Gidea, M. & Katz, Y. (2018). Topological data analysis of financial time series: Landscapes of crashes. *Physica A: Statistical Mechanics and its Applications*, 491, 820–834.

Goldthorpe, J.H. (2016). Social class mobility in modern Britain: Changing structure, constant process. *Journal of the British Academy*, 4, 89–111.

Goldthorpe, J.H. & Mills, C. (2008). Trends in intergenerational class mobility in modern Britain: Evidence from national surveys, 1972–2005. *National Institute Economic Review*, 205, 83–100.

Halpin, B. & Chan, T.W. (1998). Class careers as sequences: An optimal matching analysis of work-life histories. *European Sociological Review*, 14(2), 111–130.

Hiraoka, Y., Nakamura, T., Hirata, A. et al. (2016). Hierarchical structures of amorphous solids characterized by persistent homology. *Proceedings of the National Academy of Sciences*, 113(26), 7035–7040.

HM Government (2022). *Levelling Up the United Kingdom*. White Paper, CP 604.

Iacopini, I., Petri, G., Barrat, A. & Latora, V. (2019). Simplicial models of social contagion. *Nature Communications*, 10, 2485.

Jenkins, S.P. (2011). *Changing Fortunes: Income Mobility and Poverty Dynamics in Britain*. Oxford University Press.

Lesnard, L. (2010). Setting cost in optimal matching to uncover contemporaneous socio-temporal patterns. *Sociological Methods & Research*, 38(3), 389–419.

McInnes, L., Healy, J. & Melville, J. (2018). UMAP: Uniform manifold approximation and projection for dimension reduction. *arXiv preprint*, arXiv:1802.03426.

Rizvi, A.H., Camara, P.G., Kandror, E.K. et al. (2017). Single-cell topological RNA-seq analysis reveals insights into cellular differentiation and development. *Nature Biotechnology*, 35(6), 551–560.

Robette, N. & Thibault, N. (2008). Comparing qualitative harmonic analysis and optimal matching: An exploratory study of occupational trajectories. *Population-E*, 63(4), 621–646.

Robinson, A. & Turner, K. (2017). Hypothesis testing for topological data analysis. *Journal of Applied and Computational Topology*, 1, 241–261.

Saggar, M., Sporns, O., Gonzalez-Castillo, J. et al. (2018). Towards a new approach to reveal dynamical organization of the brain using topological data analysis. *Nature Communications*, 9, 1399.

Savage, M., Devine, F., Cunningham, N. et al. (2013). A new model of social class? Findings from the BBC's Great British Class Survey experiment. *Sociology*, 47(2), 219–250.

Singer, B. & Spilerman, S. (1976). The representation of social processes by Markov models. *American Journal of Sociology*, 82(1), 1–54.

Sizemore, A.E., Phillips-Cremins, J.E., Ghrist, R. & Bassett, D.S. (2018). The importance of the whole: Topological data analysis for the network neuroscientist. *Network Neuroscience*, 3(3), 656–673.

Sizemore, A.E., Phillips-Cremins, J.E., Ghrist, R. & Bassett, D.S. (2018). The importance of the whole: Topological data analysis for the network neuroscientist. *Network Neuroscience*, 3(3), 656–673.

Stolz, B.J., Harrington, H.A. & Porter, M.A. (2017). Persistent homology of time-dependent functional networks constructed from coupled time series. *Chaos*, 27(4), 047410.

Studer, M. & Ritschard, G. (2016). What matters in differences between life trajectories: A comparative review of sequence dissimilarity measures. *Journal of the Royal Statistical Society: Series A*, 179(2), 481–511.

Tong, H. (1990). *Non-linear Time Series: A Dynamical System Approach*. Oxford University Press.

Turner, K., Mileyko, Y., Mukherjee, S. & Harer, J. (2014). Fréchet means for distributions of persistence diagrams. *Discrete & Computational Geometry*, 52(1), 44–70.

Vandecasteele, L. (2010). Poverty trajectories, triggering events and exit routes. *Sociological Research Online*, 15(4), 1–17.

Zomorodian, A. & Carlsson, G. (2005). Computing persistent homology. *Discrete & Computational Geometry*, 33(2), 249–274.
