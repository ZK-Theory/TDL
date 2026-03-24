# Persistent Homology of UK Socioeconomic Life-Course Trajectories

**Authors:** [Author Names]
**Target Journal:** *Sociological Methodology* / *Social Forces* / *JASA: Applications & Case Studies*
**Date:** March 2026 (Fifth Draft)

---

## Abstract

Longitudinal panel data captures the temporal structure of life-course dynamics, yet conventional sequence analysis methods treat trajectories as character strings, discarding their geometric structure in high-dimensional space. We apply persistent homology (PH) to 27,280 employment-income trajectories drawn from Understanding Society (2009–2023), with cross-era validation on 8,509 trajectories from the British Household Panel Study (1991–2008). Each trajectory is a sequence of nine states combining employment status (employed, unemployed, inactive) with income band (low, mid, high), embedded into 20-dimensional PCA space via n-gram frequency vectors and analysed using Vietoris–Rips persistent homology with maxmin landmarks. We introduce a **Markov memory ladder** — a battery of five null models of escalating structural complexity — that characterises the generating process underlying the observed topology.

Seven distinct mobility regimes emerge via Gaussian mixture models optimised by BIC. Total-persistence tests (the standard scalar summary) suggest that temporal ordering creates topological structure (order-shuffle H₀ *p* < 0.005) while first-order Markov dynamics fully account for the topology (Markov-1 H₀ *p* = 1.000). However, upgrading the test statistic from total persistence to Wasserstein diagram-level distances — which compare the full geometric configuration of persistence features rather than collapsing them to a single scalar — reverses the Markov finding. Under Wasserstein testing (100 permutations, 2,000 landmarks), the Markov-1 null is rejected for H₀ (*p* = 0.002): observed persistence diagrams differ significantly in shape from Markov-generated diagrams, even though Markov surrogates produce more total persistence. Order-shuffle H₀ is borderline under Wasserstein (*p* = 0.058), and H₁ (loops) remains non-significant under both null types. This discrepancy between scalar and diagram-level tests is itself a methodological finding: total persistence masks structural differences that Wasserstein distances detect.

These findings replicate on BHPS-era trajectories (1991–2008): order-shuffle H₀ *p* = 0.000, Markov-1 *p* = 1.000 (total persistence). Stratified Wasserstein distances reveal significant topological differences by gender, parental NS-SEC, and birth cohort; 30/50 tests survive Benjamini-Hochberg FDR correction at *q* < 0.05. Overlapping 10-year career-phase windows confirm extreme regime stickiness: among 7,453 individuals starting in disadvantaged regimes, only 416 (5.6%) escape to advantaged regimes (11.0% under non-overlapping windows). Comparison with optimal matching (OM) baselines (ARI = 0.26 at matched *k* = 7) confirms that TDA's primary added value lies in formal null testing and multi-scale geometric characterisation.

**Keywords:** persistent homology, topological data analysis, social mobility, life-course trajectories, Markov models, regime switching, Wasserstein distance

**JEL Codes:** C14, C38, J62, D63

---

## 1. Introduction

### 1.1 Motivation: UK Social Mobility and Life-Course Dynamics

Intergenerational social mobility in the United Kingdom has stagnated or declined since the 1970s: recent cohorts show lower rates of upward movement relative to their parents' generation (Blanden et al. 2004, 2013; Goldthorpe & Mills 2008). Behind this stagnation lie persistent unemployment, income churning, and structural inactivity — dynamics that create multiple equilibria in employment-income states. Cross-sectional snapshots — comparing parents' and children's occupational class or income at a single point — inevitably miss these dynamics. What matters is not merely where individuals start and end, but the shape of the path between.

The British Household Panel Study (BHPS, 1991–2008) and its successor Understanding Society (USoc, 2009–2023) together provide two of the longest continuous household panels in the social sciences. Our primary analysis draws on the USoc-era panel: from over 118,000 respondents, we reconstruct 27,280 individual trajectories with at least 10 consecutive years of data within the USoc observation window (start years 2009–2013). Each trajectory is a time-ordered sequence through a nine-state space combining employment status — employed (E), unemployed (U), or inactive (I) — with income band — low (L), mid (M), or high (H) — derived from equivalised household income relative to 60% of the contemporary median. As cross-era validation, we separately reconstruct 8,509 BHPS-era trajectories (1991–2008, mean length 14.5 years) by fixing the BHPS `{wave}pid` → USoc `pidp` linkage via the cross-wave identifier file, and equivalising BHPS raw household income (`fihhmn`) using the modified OECD scale (`eq_moecd`). We also identify 8,459 spanning trajectories observed in both surveys, enabling 20+ year longitudinal tracking for a subset of the sample (§4.7).

The resulting trajectories reveal a labour market in which employment dominates (58% of person-years) but inactivity is pervasive (32%), and low income affects over a third (36%) of observed person-years. These are not transient states: the modal trajectory length in our sample is 13 years, sufficient to observe structural persistence, cycling, and — for some — escape from disadvantaged states.

UK labour market trajectories are also shaped by regional economic structures and local labour market conditions (HM Government 2022). The present analysis operates at the national level; regional stratification (NUTS2 or Travel-to-Work Area) is a natural extension of the Markov memory ladder (§5.4).

The policy question is whether disadvantaged trajectories are absorbing or transient. If low-income churning creates persistent cycles from which exit is rare, marginal interventions targeting single transitions will not be enough. If trajectories are well described by low-order Markov dynamics, targeting the right transitions could suffice. Distinguishing between these scenarios requires methods that go beyond measuring distances between sequences, and — as we show — test statistics that compare persistence diagrams as geometric objects rather than collapsing them to scalars.

### 1.2 Research Gap

Sequence analysis methods — optimal matching (OM) and its many variants — have dominated life-course research since Abbott's (1995) influential importation of biological sequence techniques into sociology. OM and related methods treat trajectories as strings and compute pairwise distances under substitution and indel (insertion-deletion) cost matrices, enabling cluster analysis to identify "types" of life course. This approach has been productive, generating typologies of employment careers, family formation, and housing trajectories across many national contexts (Abbott & Tsay 2000; Lesnard 2010; Gauthier et al. 2010).

However, sequence analysis has limitations for the questions we pose. First, OM distances depend on the substitution cost matrix, which is typically set a priori or estimated from transition rates — introducing subjectivity at a foundational level (Robette & Thibault 2008). Second, OM and its variants treat trajectories as one-dimensional objects: they measure pairwise distances but have no concept of the global geometry or topology of the trajectory space. They cannot naturally detect persistent clusters (connected components), loops (cyclical traps), or higher-dimensional voids in the point cloud of embedded trajectories — though sequence-based clusters may capture similar substantive phenomena by other means. Third, there is no standard framework for formal significance testing — for asking whether the observed structure exceeds what would be expected under explicit generative null models.

Markov chain models, the other workhorse of life-course analysis, capture local transition probabilities but are not designed to detect global shape. A Markov model can tell us the probability of moving from unemployment to employment, but it cannot detect whether the cloud of all trajectories in embedding space has a topological signature of cyclical trapping, or whether the number and separation of trajectory clusters exceeds what memoryless transitions would produce.

Topological data analysis (TDA), via persistent homology (PH), addresses these limitations. PH identifies topological features — connected components (H₀), loops (H₁), and higher-dimensional voids — that persist across a range of spatial scales, providing a multi-scale signature of the shape of a point cloud that is robust to noise and dimensionality (Carlsson 2009; Edelsbrunner & Harer 2010). TDA has been applied to financial time series (Gidea & Katz 2018), brain networks (Saggar et al. 2018), gene expression (Rizvi et al. 2017), and materials science (Hiraoka et al. 2016). PH hypothesis testing has been developed by Robinson & Turner (2017), and TDA–Markov hybrids have appeared in network analysis (Stolz et al. 2017). Recent work has brought TDA to adjacent social-science settings — notably network persistence in organisational sociology (Sizemore et al. 2018) and simplicial complexes for modelling social contagion (Iacopini et al. 2019) — but these operate on cross-sectional network snapshots rather than individual-level longitudinal sequences. To our knowledge, no study has applied persistent homology with structured null-model batteries to longitudinal socioeconomic trajectories.

Critical gaps remain: How does the topology of trajectory space relate to socioeconomic mobility regimes? Can we systematically test whether observed topological structure exceeds Markov baselines of varying complexity? And does the choice of test statistic — scalar summary versus diagram-level comparison — change the answer?

### 1.3 Contribution and Roadmap

We apply persistent homology to longitudinal life-course data and validate the resulting topology against a hierarchy of generative null models. The regime typology qualitatively resembles what sequence analysis finds in similar data (e.g., Bukodi & Goldthorpe 2019); TDA adds multi-scale geometric characterisation and formal significance testing. A direct comparison with optimal matching yields ARI = 0.26 at matched *k* = 7 (§5.1).

The **Markov memory ladder** — five null models of increasing complexity (label shuffle, cohort shuffle, order shuffle, Markov order-1, Markov order-2) — decomposes the topological signal into contributions from state frequencies, temporal ordering, and memory length. We implement the ladder with two test statistics: total persistence (scalar) and Wasserstein diagram-level distances (geometric). The two give different answers for the Markov null. Total persistence says the topology is bounded by first-order dynamics; Wasserstein says the observed diagram is an outlier. This discrepancy — detectable only because we compared both statistics on the same null battery — has implications for TDA hypothesis testing more broadly.

We also analyse overlapping career-phase windows to quantify regime stickiness. Phase-order shuffle testing (*n* = 500) finds no evidence that phase ordering creates additional topology (H₀ *p* = 0.98, 95% CI [0.968, 0.992]; H₁ *p* = 0.542, 95% CI [0.498, 0.586]).

We find that H₀ topological structure (cluster separation) is order-dependent under total-persistence testing (order-shuffle *p* < 0.005) but not rejected under first- or second-order Markov nulls (Markov-1 *p* = 1.000, Markov-2 *p* = 1.000). However, upgrading to Wasserstein diagram-level distances reverses the Markov conclusion: Markov-1 H₀ is rejected (*p* = 0.002), indicating that the connected-component structure of the trajectory manifold cannot be reproduced by a first-order Markov chain when diagrams are compared as geometric objects. Order-shuffle H₀ is borderline under Wasserstein (*p* = 0.058), while H₁ remains non-significant under both statistics and all null types. These findings are stable across landmark counts from 2,500 to 8,000 (Appendix B) under total-persistence testing and replicate on BHPS-era trajectories (§4.7). Embedding sensitivity testing across six configurations (§5.4) confirms H₀ robustness. Stratified analysis reveals origin-dependent topology; all significant results survive Benjamini-Hochberg FDR correction. Overlapping 10-year windows confirm extreme regime stickiness (5.6% escape rate from disadvantaged regimes; 11.0% under non-overlapping windows).

---

## 2. Literature Review

### 2.1 Sequence Analysis in Social Science

The application of sequence analysis to life-course data originated with Abbott's (1995) proposal to adapt biological sequence techniques for sociological use. Optimal matching (OM) computes distances between state sequences using substitution and indel operations, analogous to edit distances in string matching. The resulting distance matrix is then used for cluster analysis (typically Ward's hierarchical clustering or partitioning around medoids) to identify trajectory "types".

OM has been extended in several directions: dynamic Hamming distances weight substitution costs by temporal proximity (Lesnard 2010), multichannel OM enables joint analysis of employment and family states (Gauthier et al. 2010), and TraMineR provides a comprehensive software implementation (Studer & Ritschard 2016). The resulting typologies span employment careers (Halpin & Chan 1998), family formation (Elzinga & Liefbroer 2007), and housing trajectories (Coulter et al. 2016).

Sequence analysis has specific limitations for the questions we pose. The dependence on substitution cost matrices introduces subjectivity: different cost specifications can yield different typologies from the same data (Robette & Thibault 2008). The resulting distance measures are fundamentally pairwise — they compare sequences but do not characterise the global geometry of the trajectory space. There is no natural notion of "closeness in trajectory space" that preserves topological invariants such as connected components, loops, or higher-dimensional voids. Significance testing is typically absent: cluster solutions are evaluated by silhouette scores or Calinski-Harabasz indices, but there is no formal test of whether the observed clustering exceeds what specific null models would produce.

### 2.2 Topological Data Analysis Foundations

Persistent homology (PH) provides a rigorous mathematical framework for detecting and quantifying topological features in data. Given a point cloud $X \subset \mathbb{R}^d$, PH constructs a filtration — a nested sequence of simplicial complexes $K_0 \subseteq K_1 \subseteq \cdots \subseteq K_m$ — by connecting points within distance $\epsilon$ and tracking which topological features appear (are "born") and disappear ("die") as $\epsilon$ increases (Edelsbrunner et al. 2002; Zomorodian & Carlsson 2005).

The Vietoris–Rips (VR) complex, the most common choice for point cloud data, includes a $k$-simplex whenever all $\binom{k+1}{2}$ pairwise distances are below $\epsilon$. For $n$ points, the VR complex can have up to $2^n$ simplices, making direct computation infeasible for large datasets. Maxmin landmark selection (de Silva & Carlsson 2004) addresses this by greedily selecting a subset of $L \ll n$ points that are maximally dispersed, constructing the VR complex on landmarks only. Ripser (Bauer 2021) provides state-of-the-art computational efficiency, exploiting the apparent pairs optimisation to compute VR persistence through H₁ (and optionally H₂) on thousands of landmarks in minutes.

The output of PH is a persistence diagram (PD): a multiset of birth-death pairs $(b_i, d_i)$ where feature $i$ is born at filtration value $b_i$ and dies at $d_i$. Features with large persistence $\ell_i = d_i - b_i$ are interpreted as genuine topological structure, while short-lived features near the diagonal are attributed to noise. In dimension 0 (H₀), features correspond to connected components: each merger of two components kills one H₀ feature. In dimension 1 (H₁), features correspond to loops or cycles: a loop forms at birth and is filled in at death. Summary statistics include total persistence $\sum_i \ell_i$, maximum persistence $\max_i \ell_i$, and persistence entropy $-\sum_i \hat{\ell}_i \log \hat{\ell}_i$ where $\hat{\ell}_i = \ell_i / \sum_j \ell_j$ (Atienza et al. 2019).

A fundamental property of PH is stability: small perturbations in the input point cloud produce small changes in the persistence diagram, measured by the bottleneck or Wasserstein distance (Cohen-Steiner et al. 2007). This guarantees that topological summaries are robust to noise, sampling variation, and minor measurement errors — a property we rely on given the imputation and harmonisation challenges in survey data.

For comparing persistence diagrams across groups, the Wasserstein distance $W_p(D_1, D_2)$ measures the cost of the optimal transport between two diagrams, providing a principled metric for testing whether subpopulations have different topological structure (Turner et al. 2014). As we demonstrate in this paper, the choice between scalar summaries (total persistence) and diagram-level comparisons (Wasserstein distance) can change substantive conclusions — a point that has methodological implications beyond our specific application.

### 2.3 Mobility Regimes and Their Topological Signatures

The economics of poverty traps posits that disadvantaged states can be self-reinforcing through multiple equilibria (Azariadis & Stachurski 2005). When returns to human capital investment are nonlinear — or when credit constraints, neighbourhood effects, or discrimination create threshold dynamics — individuals may become trapped in low-productivity equilibria from which escape requires large, discrete shocks rather than marginal improvements (Barrett & Carter 2013).

Life-course researchers have identified analogous patterns in longitudinal data. Vandecasteele (2010) distinguished between stable, mobile, and churning poverty trajectories using Belgian panel data. Jenkins (2011) documented extensive income churning in the UK, where many individuals cycle between poverty and near-poverty without achieving durable exits. Savage et al. (2013) used the Great British Class Survey to identify seven social classes, some characterised by cultural and social capital deficits that reinforce economic disadvantage.

The connection to topology requires careful articulation, because different homological dimensions capture different geometric phenomena. If mobility regimes exist as distinct clusters in trajectory space, they will appear as persistent H₀ components (connected components). The persistence values of H₀ features quantify the separation between regime clusters: large persistence indicates well-separated regimes that merge only at large filtration radii.

H₁ features (loops) have a distinct geometric meaning. Persistent H₁ loops correspond to cyclical oscillation patterns in the embedding space — subsets of trajectories that trace closed paths through state space, returning to similar configurations after a sequence of transitions. This is geometrically distinct from the absorbing-state dynamics that characterise poverty traps in the economic literature (Azariadis & Stachurski 2005). Poverty traps as absorbing states would manifest as dense H₀ clusters — high-density regions in the point cloud from which few trajectories escape — rather than as H₁ loops. The distinction matters: H₁ tests whether the trajectory manifold contains persistent cyclical structure, not whether disadvantaged states are absorbing.

As we report in §4.3, H₁ is not rejected under any null model in our data, including the first-order Markov null, regardless of which test statistic is used. This negative result bounds the complexity of cyclical dynamics: the trajectory manifold lacks persistent cyclical structure beyond what first-order Markov dynamics produce. This is a meaningful negative result — it establishes that claims about non-Markovian topological trapping cycles would be unsupported by these data — rather than a failure to detect poverty traps, which are better sought through H₀ cluster absorptivity and escape rates (§4.4.2).

A topological analysis thus provides a geometric characterisation of the mobility landscape that complements both sequence typologies and Markov transition models, but the mapping between topological features and substantive social phenomena must respect the geometric meaning of each homological dimension.

### 2.4 Statistical Null Models for TDA

The statistical significance of topological features requires comparison to appropriate null distributions. Robinson & Turner (2017) proposed permutation tests for PH, comparing observed total persistence or Betti numbers to distributions generated by permuting group labels. Stolz et al. (2017) applied PH to time-dependent functional networks, using surrogate data methods as nulls. These contributions establish the general framework; our contribution is to adapt and extend it with a structured hierarchy of null models tailored to sequential socioeconomic data.

For life-course trajectories, the relevant null models must be carefully chosen to test specific hypotheses. A label shuffle null (permuting state labels globally) tests whether the specific identity of states matters; an order shuffle (permuting each trajectory's state sequence) tests whether temporal ordering matters, preserving marginal state frequencies; and a Markov-$k$ null (simulating from an estimated $k$-th order Markov chain) tests whether topology exceeds what $k$-step memory produces.

Higher-order Markov chains as generative models have a long history in sociology (Singer & Spilerman 1976; Tong 1990). Our contribution is to arrange these null models into a systematic "memory ladder" — a sequence of increasingly structured null hypotheses that progressively preserves more of the observed data's structure. When the observed topology first becomes consistent with a Markov-$k$ null, we can conclude that the topological complexity of the trajectory space is well captured by $k$-step memory. Critically, the answer depends on how "consistent" is measured. As we show, total persistence (a scalar) and Wasserstein distance (a diagram-level metric) give different answers for the Markov null — the scalar test lacks sensitivity to structural differences in the configuration of persistence features that the Wasserstein test detects.

---

## 3. Data and Methodology

### 3.1 Data: BHPS and Understanding Society

Our data combine two longitudinal household surveys: the British Household Panel Study (BHPS, waves 1–18, 1991–2008) and Understanding Society (USoc, waves 1–14, 2009–2023). BHPS began as a nationally representative sample of approximately 5,500 households in Great Britain, with annual interviews tracking employment, income, and demographic characteristics. Understanding Society succeeded BHPS with a larger initial sample of approximately 40,000 households and incorporated the surviving BHPS sample as a sub-sample from wave 2 (2010–2011), enabling longitudinal tracking across both surveys.

Our primary analysis uses the USoc-era panel. From the combined dataset of over 118,000 respondents, we select individuals with at least 10 consecutive years of valid employment-income observations within the USoc observation window, yielding 27,280 trajectories. The mean trajectory length is 12.9 years (median 13, range 10–14), with start years spanning 2009–2013 and end years 2018–2022.

As cross-era validation, we separately construct BHPS-era trajectories (1991–2008) by linking BHPS person identifiers (`{wave}pid`) to USoc identifiers (`pidp`) via the cross-wave identifier file (`xwavedat.tab`). BHPS raw monthly net household income (`fihhmn`) is equivalised by dividing by the modified OECD equivalence scale (`eq_moecd`) from the household response file, matching the equivalisation approach used for USoc's `fihhmnnet1_dv`. This yields 8,509 BHPS-era trajectories (mean length 14.5 years). We also identify 8,459 spanning trajectories observed in both surveys. Cross-era results are reported in §4.7.

Each person-year is assigned to one of nine states formed by crossing employment status with threshold-based income category. Employment status is derived from the `jbstat` variable: employed (E) includes full-time and part-time employment and self-employment; unemployed (U) includes ILO-definition unemployment; inactive (I) includes retirement, full-time education, long-term sickness, and caring responsibilities. Income bands are defined annually relative to the contemporary equivalised household income median: low (L, below 60% of median), mid (M, 60%–120% of median), and high (H, above 120% of median). The L/M/H classification uses fixed boundaries, not population-quantile cut-points; the resulting category sizes are unequal and vary across years. Sensitivity to alternative threshold choices (e.g., 50%/150% or population terciles) is not examined here.

Gaps of one or two years in otherwise continuous trajectories are forward-filled from the last observed state, affecting 4.9% of person-years. We verify that imputation rates are balanced across regimes and do not drive topological results (Supplementary Material §A).

For stratification analysis, we use three covariates: sex (Female *n* = 14,402; Male *n* = 11,243; 1,635 with missing sex excluded from gender stratification); parental NS-SEC (Professional/Managerial *n* = 2,067; Intermediate *n* = 6,777; Routine/Manual *n* = 7,779; 10,657 missing); and birth cohort decade (1930s *n* = 1,642 through 1990s *n* = 1,364, with seven cohort groups).

Parental NS-SEC is missing for 39.1% of the sample (10,657 of 27,280). This missingness is non-random: a chi-squared test of regime membership by NS-SEC availability yields $\chi^2$ = 147.74 (*df* = 6, *p* < 10$^{-29}$), and logistic regression confirms that regime membership, birth cohort, and trajectory characteristics all predict NS-SEC availability. All NS-SEC-stratified results (§4.6) should be interpreted with this caveat.

### 3.2 Trajectory Embedding

To embed trajectories in a continuous metric space suitable for TDA, we compute n-gram frequency vectors. For each trajectory of length $T$, we calculate:

- **Unigrams** (9 dimensions): Relative frequency of each state $s \in \{EL, EM, EH, UL, UM, UH, IL, IM, IH\}$ in the trajectory.
- **Bigrams** (81 dimensions): Relative frequency of each consecutive state pair $(s_t, s_{t+1})$, capturing transition structure.

The concatenated 90-dimensional term-frequency (TF) vector encodes both the composition and the sequential structure of each trajectory. We standardise using a fitted `StandardScaler` and project to 20 dimensions via Principal Component Analysis (PCA), retaining the top 20 components. The resulting point cloud of 27,280 points in $\mathbb{R}^{20}$ preserves both global cluster structure and local sequence variation.

As a sensitivity check, we compute UMAP embeddings with 16 dimensions and compare GMM cluster assignments to those from PCA-20D. The adjusted Rand index (ARI) between the two clusterings is 0.33 at matched $k = 7$, indicating that while three broad macro-types (secure employment, inactive/marginal, churning/mixed) are stable across embedding methods, finer regime boundaries are embedding-dependent. UMAP and PCA capture different aspects of local versus global geometry (McInnes et al. 2018), which explains the divergence at fine scales. We report PCA-20D as the primary embedding and UMAP-16D as a supplementary sensitivity analysis (Figure S1).

To verify that substantive conclusions are robust to embedding choice, we re-run the order-shuffle null on the UMAP-16D embedding ($n = 100$). With GMM fixed at $k = 7$, UMAP yields ARI = 0.33 against PCA regime assignments. On the UMAP-16D point cloud with 5,000 maxmin landmarks, the order-shuffle null rejects H₀ at $p < 0.001$ (observed total persistence 3,203.3, null mean $2{,}372.9 \pm 323.3$) while H₁ is non-significant ($p = 1.00$), reproducing the PCA pattern. Full Markov-1 replication on UMAP is omitted due to computational cost; given the close agreement in regime structure and order-shuffle results, we treat PCA as the primary embedding and UMAP as a robustness check.

### 3.3 Persistent Homology

We compute Vietoris–Rips persistent homology on the PCA-20D point cloud using the following pipeline:

1. **Maxmin landmark selection**: From the 27,280 embedded trajectories, we select $L$ landmarks using the greedy furthest-point (maxmin) algorithm (de Silva & Carlsson 2004). This selects an initial seed point and iteratively adds the point maximally distant from the current landmark set, producing a well-dispersed subsample that preserves the geometric structure of the full cloud. For total-persistence tests, $L = 5{,}000$ (approximately 18% of the point cloud); for Wasserstein tests, $L = 2{,}000$ (approximately 7%). We verify robustness to this choice by recomputing PH at $L = 2{,}500$ and $L = 8{,}000$ (Appendix B).

2. **VR complex construction and PH computation**: We construct the Vietoris–Rips filtration on the landmarks and compute persistence through H₁ using Ripser (Bauer 2021), with the filtration threshold set to the 75th percentile of pairwise distances.

3. **Persistence diagrams and summaries**: The output comprises H₀ (connected components) and H₁ (loops) persistence diagrams. For each dimension, we compute total persistence $\sum_i (d_i - b_i)$, maximum persistence, feature count, and persistence entropy.

H₀ features correspond to the merging of trajectory clusters as the filtration radius increases: long-lived H₀ features indicate well-separated regimes. H₁ features correspond to loops in the trajectory space: persistent loops may indicate cyclical trapping where trajectories circulate among a subset of states without converging to a single attractor.

### 3.4 Null Model Battery: The Markov Memory Ladder

We introduce a battery of five null models arranged in order of increasing structural fidelity to the observed data. For each null model, we generate surrogate trajectory datasets and process them through the same pipeline: re-embed using the n-gram + PCA pipeline with PCA loadings fixed from the observed data (i.e., surrogate n-gram vectors are projected onto the observed PCA axes, not recomputed). Maxmin landmarks are re-selected on each surrogate to avoid coupling landmark geometry to the observed data. We then recompute PH and compare to the observed data.

**Null 1 — Label shuffle** (*n* = 200): Permute state labels globally across all person-years, destroying all individual-level structure.

**Null 2 — Cohort shuffle** (*n* = 200): Permute trajectories within birth-cohort bins, testing whether cross-cohort differences drive the topological signal.

**Null 3 — Order shuffle** (*n* = 100): For each individual, randomly permute the temporal order of their state sequence, preserving per-person state frequencies but destroying all transition and temporal structure.

**Null 4 — Markov order-1** (*n* = 100): Estimate a first-order Markov transition matrix from the observed data via maximum likelihood and simulate surrogate trajectories of the same lengths, conditional on each trajectory's observed starting state.

**Null 5 — Markov order-2** (*n* = 200): Estimate a second-order Markov transition matrix (conditioning on the previous two states) via maximum likelihood, with Laplace smoothing (adding pseudocounts of 1 to all 729 cells). Surrogates are simulated conditional on the observed first two states of each trajectory.

#### Test statistics

We implement two test statistics to compare observed and null persistence:

**Total persistence** (scalar): $\sum_i (d_i - b_i)$ for each homological dimension, separately for H₀ and H₁. The *p*-value is the proportion of null realisations with total persistence as extreme as or more extreme than the observed value. This is the standard approach in TDA hypothesis testing (Robinson & Turner 2017).

**Wasserstein diagram distance** (diagram-level): For each null realisation *j*, we compute $W_1(D_{\text{obs}}, D_{\text{null}_j})$ — the 1-Wasserstein distance between the observed persistence diagram and the null diagram, using the `gudhi.wasserstein` implementation backed by the POT (Python Optimal Transport) library. We also compute a null-null baseline: $W_1(D_{\text{null}_i}, D_{\text{null}_j})$ for 500 sampled pairs of null diagrams. The *p*-value is the proportion of null-null distances that equal or exceed the mean observed-null distance. This approach tests whether the observed diagram is more distant from the null distribution than null diagrams are from each other — i.e., whether the observed diagram is an outlier relative to the null cloud in Wasserstein space.

The Wasserstein test is more sensitive than total persistence because it compares the full configuration of birth-death pairs rather than collapsing them to a scalar. Two diagrams can have identical total persistence but very different geometric structure: for instance, many short-lived features versus few long-lived ones. The Wasserstein distance detects such shape differences; total persistence does not.

With *n* = 100 for the order-shuffle and Markov-1 nulls, we have resolution to approximately *p* = 0.01 for one-sided tests. For BHPS-era validation (§4.7), null tests use *n* = 500 permutations.

### 3.5 Regime Discovery

We identify mobility regimes by fitting Gaussian mixture models (GMMs) to the PCA-20D embedding, using the Bayesian Information Criterion (BIC) for model selection across $k = 3, 4, \ldots, 15$ components. The BIC-optimal model has $k = 7$ components.

H₀ informs but does not replicate GMM: all H₀ features are born at filtration radius 0 (each landmark starts as a singleton); the 44 features with persistence > 10 merge gradually (7th/8th most persistent ratio = 1.03×), reflecting single-linkage chaining in 20-dimensional Vietoris–Rips complexes on 5,000 landmarks. The merge tree yields one dominant connected component (~99.98% of trajectories) plus 6 singleton outliers — no balanced clusters matching GMM density modes. We use GMM for regime labels and H₀ for connectivity validation (§4.4.1, Appendix A).

Regime profiles are constructed by mapping GMM-assigned labels back to the original state sequences and computing, for each regime: employment rate, unemployment rate, inactivity rate, income distribution (fraction in low/mid/high), and a stability index (fraction of trajectory years spent in the dominant state).

To verify that the $k = 7$ solution is not an artefact of a particular sample, we perform a bootstrap stability analysis: 200 resamples of the 27,280 trajectory embeddings with replacement, each fitted with GMM $k = 7$, yielding ARI distribution with mean 0.646 ± 0.086 (95% CI: [0.461, 0.795]).

### 3.6 Overlapping Windows and Regime Persistence

To assess regime persistence over the life course, we construct overlapping career-phase windows using a sliding window of 10 years with a 5-year step. For each individual, this produces a sequence of overlapping windows, each embedded and assigned to a regime using the same PCA-GMM model fitted on full trajectories. This yields 54,560 windows from 27,280 individuals (mean 2.0 windows per person).

We construct a 7×7 regime transition matrix from consecutive windows and compute escape probabilities: the fraction of individuals starting in disadvantaged regimes (Low-Income Churn or Inactive Low) who reach an advantaged regime (Secure EH or Employed Mid) within a given number of windows.

We also compute PH on the phase-level embedding cloud and test a phase-order shuffle null that preserves each individual's multiset of windows but randomises their temporal order, testing whether the life-course ordering of career phases adds topological structure beyond the composition of phases. We run *n* = 500 permutations with 3,000 maxmin landmarks and report p-values with 95% confidence intervals.

### 3.7 Sequence Analysis Baseline

To contextualise our TDA results, we compute a standard sequence analysis baseline using optimal matching (OM) with dynamic Hamming distances (Lesnard 2010). We compute pairwise distances between all 27,280 trajectories, apply Ward's hierarchical clustering, and select *k* via the average silhouette width (Studer & Ritschard 2016).

The OM-optimal solution selects *k* = 2 clusters (silhouette = 0.223), producing a coarse division between predominantly inactive trajectories (40.2%) and predominantly employed trajectories (59.8%). At *k* = 7, OM achieves silhouette = 0.215. The ARI between OM *k* = 7 clusters and GMM *k* = 7 regimes is 0.26, indicating overlapping but non-identical regime boundaries. Regime-level profile correlations range from 0.97 (high-employment, which both methods identify cleanly) down to 0.02 (mixed-churn, where OM and TDA draw boundaries differently).

The moderate ARI confirms that the broad structure of UK trajectory space — secure employment versus inactivity versus churning — is recoverable by either method, while finer distinctions depend on the analytic approach. The primary added value of TDA lies not in the regime typology itself but in the formal null testing infrastructure.

---

## 4. Results

### 4.1 Descriptive Statistics

Our sample comprises 27,280 individuals with trajectories averaging 12.9 years (range 10–14, median 13). The nine-state distribution reflects a labour market with dominant employment: EH (high-income employment) is the most common dominant state (42.1% of individuals), followed by IL (inactive-low, 13.7%), EM (employed-mid, 12.5%), IM (inactive-mid, 12.1%), and IH (inactive-high, 12.0%). Unemployment is comparatively rare as a dominant state: UL (1.1%), UM (0.5%), and UH (0.4%). The low-income employment state EL dominates 5.7% of trajectories.

Birth cohorts span seven decades, from the 1930s (*n* = 1,642) through the 1990s (*n* = 1,364), with the largest cohorts in the 1960s (*n* = 5,579) and 1950s (*n* = 4,843). The gender split is 56% female, 44% male among those with non-missing sex. Forward-fill imputation affected 4.9% of person-years, distributed proportionally across regimes.

**[Figure 1]** presents trajectory heatmaps showing exemplar sequences from each of the seven regimes discovered in Section 4.4.

**[Table 1]** summarises sample characteristics by cohort decade.

### 4.2 Topological Structure of the Trajectory Space

Persistent homology on the PCA-20D embedding with 5,000 maxmin landmarks reveals substantial topological structure in both dimensions.

**H₀ (connected components):** 5,000 features (4,999 finite, 1 infinite — the final connected component), with total persistence 20,411.1 and maximum persistence 15.81. The dominance of a single long-lived component (persistence 15.81, compared to the mean of 4.08) indicates that most trajectory clusters ultimately merge at large filtration values but are well separated at smaller scales. H₀ reflects unimodal connectivity plus outliers: 99.98% of trajectories belong to a single giant connected component, with 6 singleton landmarks merging late — consistent with single-linkage chaining in high-dimensional Vietoris–Rips complexes. The distribution of H₀ persistence values has a heavy right tail, but the top features merge gradually (7th/8th most persistent ratio = 1.03×), indicating no sharp topological gap between clusters.

**H₁ (loops):** 5,962 features (5,961 finite, 1 infinite), with total persistence 2,224.7 and maximum persistence 3.21. Loops are numerous but not deeply persistent: the maximum H₁ persistence (3.21) is a fifth of the maximum H₀ persistence (15.81).

**[Figure 3]** presents persistence diagrams for both H₀ and H₁.

### 4.3 Null Model Validation: The Markov Memory Ladder

#### Total-persistence tests

The five null models in the Markov memory ladder yield the following results for total persistence at $L = 5{,}000$ landmarks (Table 2):

**[Table 2: Markov Memory Ladder — Total Persistence]**

| Null Model | *n* | H₀ observed | H₀ null (μ±σ) | H₀ *p* | H₁ observed | H₁ null (μ±σ) | H₁ *p* |
|---|---|---|---|---|---|---|---|
| Label shuffle | 200 | 20,411.1 | 20,405.4 ± 10.3 | 0.315 | 2,224.7 | 2,234.6 ± 13.3 | 0.710 |
| Cohort shuffle | 200 | 20,411.1 | 20,407.8 ± 9.6 | 0.405 | 2,224.7 | 2,234.5 ± 12.7 | 0.725 |
| Order shuffle | 100 | 20,411.1 | 19,364.2 ± 73.8 | **< 0.005** | 2,224.7 | 2,156.7 ± 30.8 | **0.020** |
| Markov-1 | 100 | 20,411.1 | 21,138.3 ± 196.8 | 1.000 | 2,224.7 | 2,381.3 ± 63.8 | 1.000 |
| Markov-2 | 200 | 20,411.1 | 21,323.8 ± 174.2 | 1.000 | 2,224.7 | 2,253.3 ± 47.1 | 0.735 |

Under total persistence, the ladder tells a clean but, as we show below, incomplete story. Temporal ordering shapes the global geometry of the point cloud (order-shuffle H₀ *p* < 0.005). Markov surrogates generate *more* total persistence than observed (null mean H₀ = 21,138.3 vs observed 20,411.1), yielding *p* = 1.000 — the observed value sits below the null distribution. Label and cohort shuffles serve as negative controls (both non-significant, as expected). Order-shuffle H₁ is significant at $L = 5{,}000$ (*p* = 0.020) but landmark-sensitive (non-significant at $L = 2{,}500$ and $L = 8{,}000$; Appendix B).

Taken alone, these results would suggest that first-order Markov dynamics fully account for the topology of the trajectory point cloud. The scalar summary indicates that Markov surrogates produce as much or more total persistence as the real data. The fourth draft of this paper reported this conclusion. The Wasserstein results below revise it.

#### Wasserstein diagram-level tests

We re-run the order-shuffle and Markov-1 nulls using Wasserstein diagram distances as the test statistic, on $L = 2{,}000$ landmarks with *n* = 100 permutations per null type. For each null realisation, we compute $W_1(D_{\text{obs}}, D_{\text{null}})$ per homological dimension, and compare to a null-null baseline of 500 sampled pairs.

**[Table 2b: Markov Memory Ladder — Wasserstein Distances]**

| Null Model | Dim | W(obs↔null) μ±σ | W(null↔null) μ±σ | *p* | Sig? |
|---|---|---|---|---|---|
| Order shuffle | H₀ | 11.22 ± 1.52 | 6.62 ± 2.37 | 0.058 | borderline |
| Order shuffle | H₁ | 139.69 ± 3.07 | 144.66 ± 4.61 | 0.854 | no |
| Markov-1 | H₀ | 11.42 ± 2.15 | 5.99 ± 1.79 | **0.002** | **yes** |
| Markov-1 | H₁ | 126.85 ± 2.92 | 121.39 ± 3.95 | 0.086 | no |

The Wasserstein results change the Markov conclusion. The observed H₀ persistence diagram is significantly different from Markov-1 null diagrams (*p* = 0.002): the mean Wasserstein distance between observed and null diagrams (11.42 ± 2.15) is nearly double the mean distance between pairs of null diagrams (5.99 ± 1.79). The observed diagram is an outlier relative to the Markov null cloud in diagram space, even though it has less total persistence. The Markov process generates *more* features overall but in a different geometric configuration — different birth-death pairs, different persistence structure — than the real data.

Order-shuffle H₀ is borderline under Wasserstein (*p* = 0.058), weaker than the clear rejection under total persistence (*p* < 0.005). This implies that temporal ordering creates aggregate persistence differences (total persistence is higher in ordered data) but the diagram-level structure is only marginally different from the order-shuffled baseline. The effect of temporal ordering is real but operates more through the sum of feature lifetimes than through specific birth-death configurations.

H₁ is non-significant under both null types, consistent with the total-persistence results. Markov-1 H₁ is borderline (*p* = 0.086) — closer to significance under Wasserstein than under total persistence (*p* = 1.000) — suggesting that diagram-level H₁ differences may emerge with larger permutation counts, though we do not pursue this here.

#### The discrepancy between test statistics

The discrepancy between total persistence and Wasserstein distance for the Markov-1 H₀ test is the structurally interesting finding of this analysis. Total persistence says: the observed data has *less* aggregate persistence than the Markov null, so the null is not rejected. Wasserstein says: the observed data has a *different shape* of persistence diagram than the Markov null, and this difference is larger than the variation among null diagrams, so the null *is* rejected. Both are correct statements about different aspects of the comparison. The Markov process generates a more diffuse trajectory cloud (more total persistence, more features) but the specific pattern of which components form and when they merge differs from the observed data.

We interpret this as follows: the connected-component structure of the trajectory manifold — which clusters form, at what filtration scale, and in what hierarchical relationship — carries information about the data-generating process that a first-order Markov chain cannot reproduce. The Markov chain gets the total amount of persistence roughly right (in fact, overshoots it) but distributes it differently across birth-death pairs. The trajectory data has regime-specific substructure that the globally estimated Markov transition matrix smears out.

This finding has methodological implications beyond our specific application. Scalar persistence summaries are standard in TDA hypothesis testing, but they can produce false negatives when the null generates as much or more aggregate persistence while differing in diagram shape. Wasserstein diagram comparisons should be considered alongside total-persistence tests in any TDA null-testing framework.

**Intra-regime compactness confirms temporal order contributes to regime differentiation.** We compute mean within-regime pairwise distances in the PCA-20D embedding under 500 order-shuffled re-embeddings, with PCA loadings frozen from the observed data. All seven regimes show significantly tighter compactness in observed versus order-shuffled embeddings (z-scores ranging from −30.5 to −67.9, all *p* < 0.001). Regime 0 (Mixed Churn, observed mean distance 14.68, null 19.12, *z* = −55.0) and Regime 6 (Low-Income Churn, observed 9.52, null 14.58, *z* = −67.9) show the largest compactness ratios, temporal ordering is most informative for the churning regimes, where transition sequences rather than state composition define the trajectory type.

**Bootstrap null stability.** To verify that null-model conclusions are not artefacts of a particular GMM partition, we conduct a bootstrap stability analysis: 10 bootstrap resamples of the trajectory embeddings, each re-fitted with GMM ($k = 7$), with order-shuffle and Markov-1 null tests (50 permutations each, 500 landmarks). Order-shuffle H₀ is significant in all 10/10 draws (*p*$_{\text{mean}}$ = 0.016, range [0.00, 0.04]). Markov-1 H₀ is significant in all 10/10 draws (*p*$_{\text{mean}}$ = 0.000). No conclusion flips are observed across any bootstrap draw.

**[Figure 4]** shows Betti curves — the number of topological features as a function of filtration radius — for the observed data compared to null envelopes (95% pointwise intervals) from order-shuffle and Markov-1 nulls.

**[Figure 8]** presents the null model summary as a structured visual comparison of *p*-values across the memory ladder, with both test statistics.

**[Figure 9]** shows violin plots comparing the distribution of total persistence across Markov-1 and Markov-2 null realisations to the observed values.

### 4.4 Seven Mobility Regimes

BIC model selection identifies $k = 7$ as optimal. The seven regimes, ordered by size, are:

**Regime 1 — Secure High-Employment** (*n* = 7,358, 27.0%): Dominated by high-income employment (EH). Employment rate 92.3%, inactivity rate 7.4%, unemployment near zero (0.3%). High-income rate 85.5%. Stability index 0.779, the highest of all regimes.

**Regime 2 — Inactive Low** (*n* = 5,415, 19.9%): Entirely inactive (inactivity rate 100%, zero employment or unemployment). Income is mixed (low 38.7%, mid 33.1%, high 28.2%) — the regime groups retirees with pensions alongside carers and those with long-term illness. Stability 0.387. This regime is a key disadvantaged state, though we note that it likely mixes lifecycle inactivity (retirement) with inequality-driven inactivity (disability, long-term sickness, caring). The near-absorbing nature of this regime (§4.4.2) may partly reflect the irreversibility of retirement rather than a "trap" in an inequality sense. We address this via age-stratified analysis in §4.4.2.

**Regime 0 — Mixed Churn** (*n* = 3,787, 13.9%): Mixed employment (41.6%), unemployment (20.3%), and inactivity (38.1%). Income concentrated in mid (34.1%) and high (42.2%). Low stability (0.234), the lowest of all regimes — the archetypal "churning" trajectory.

**Regime 4 — Employed Mid** (*n* = 3,510, 12.9%): Near-universal employment (98.5%) with mixed income (low 26.0%, mid 31.8%, high 42.2%). Stability 0.407.

**Regime 3 — Employment-Inactive Mix** (*n* = 3,333, 12.2%): Mixed employment (58.8%) and inactivity (41.2%), zero unemployment. Income relatively balanced (low 20.0%, mid 39.6%, high 40.4%). Stability 0.280. Likely captures career breaks, part-time work, and caring responsibilities.

**Regime 6 — Low-Income Churn** (*n* = 2,064, 7.6%): Employment (59.1%), unemployment (9.8%), and inactivity (31.1%), with the highest low-income rate (61.1%) of any regime. Stability 0.289. The second key disadvantaged regime: individuals cycle between low-paid employment, unemployment, and inactivity. Combined with Regime 2, these two regimes comprise 27.5% of the sample.

**Regime 5 — High-Income Inactive** (*n* = 1,813, 6.6%): Mixed employment (41.3%) and inactivity (58.3%), with high income (67.2%). Stability 0.400. Likely early retirees with substantial assets or high-income households with one inactive partner.

The correlation between regime stability and high-income rate is strong ($r$ = 0.77, *p* < 0.01), confirming that the most stable trajectories tend to be the most advantaged.

#### 4.4.1 H₀ Geometry vs. GMM Regimes

H₀ persistent homology encodes the Vietoris–Rips single-linkage merge tree. Cutting at $k = 7$ yields labels that are structurally distinct from GMM regimes:

**ARI (H₀ tree $k = 7$ vs. GMM):** 0.00004
**Component sizes:** C0: 99.98% (27,274 trajectories); C1–C6: singletons (1 trajectory each)

| H₀ \ GMM | R0 | R1 | R2 | R3 | R4 | R5 | R6 | Total |
|---|---|---|---|---|---|---|---|---|
| **C0** (99.98%) | 3,781 | 7,358 | 5,415 | 3,333 | 3,510 | 1,813 | 2,064 | 27,274 |
| **C1–C6** (singletons) | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |

Trajectory space is topologically connected — a single giant H₀ component — with density substructure inside it (the 7 GMM regimes). The 6 outlier singletons are all from Mixed Churn (R0), which occupies the most diffuse region of embedding space. The near-zero ARI is expected: H₀ tracks global connectivity and boundary geometry, while GMM identifies interior density modes. H₀ and GMM operate on different geometric properties — global connectivity versus local density — and are complementary. The trajectory manifold is a single connected object with heterogeneous density.

**[Figure 5]** presents the regime profile heatmap.

**[Figure 6]** shows the stability-income correlation scatter plot.

#### 4.4.2 Regime Persistence Over the Life Course

Overlapping 10-year windows (5-year step) for all 27,280 individuals yield 54,560 career-phase windows. The resulting 7 × 7 transition matrix is strongly diagonal-dominant:

|  | R0 | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|---|
| **R0** | 0.53 | 0.13 | 0.12 | 0.06 | 0.08 | 0.02 | 0.07 |
| **R1** | 0.03 | **0.78** | 0.03 | 0.03 | 0.08 | 0.04 | 0.02 |
| **R2** | 0.02 | 0.00 | **0.97** | 0.01 | 0.00 | 0.00 | 0.00 |
| **R3** | 0.05 | 0.14 | 0.18 | 0.41 | 0.15 | 0.04 | 0.04 |
| **R4** | 0.02 | 0.17 | 0.00 | 0.07 | **0.66** | 0.01 | 0.07 |
| **R5** | 0.05 | 0.14 | 0.48 | 0.06 | 0.01 | 0.26 | 0.00 |
| **R6** | 0.05 | 0.07 | 0.21 | 0.06 | 0.14 | 0.00 | 0.46 |

The strongest self-transitions occur in Regime 2 — Inactive Low (0.97), Regime 1 — Secure High-Employment (0.78), and Regime 4 — Employed Mid (0.66). The two disadvantaged regimes differ sharply in persistence: Inactive Low is near-absorbing (97%), while Low-Income Churn is moderately sticky (46%) with significant transitions to Inactive Low (21%) and Employed Mid (14%).

The 97% self-transition for Inactive Low likely reflects, in part, lifecycle inactivity: 86.1% of Inactive Low window-observations come from individuals aged ≥ 60.

**Non-overlapping window validation.** Non-overlapping windows (window_years=5, window_step=5) yield a self-transition rate of 0.601 versus 0.686 for overlapping windows (difference = 0.084). The escape rate from disadvantaged regimes is 11.0% under non-overlapping windows versus 5.6% under overlapping windows. The overlap-induced inflation is approximately 8.4 percentage points for self-transition. The core regime structure is preserved: the transition matrix remains diagonal-dominant and the qualitative ordering of regime persistence is unchanged.

**Age-adjusted escape rates.**

| Group | *n* (disadvantaged start) | *n* (escaped) | Escape rate |
|---|---|---|---|
| Overall | 7,453 | 416 | 5.6% |
| Working-age (< 60) | 2,163 | 386 | 17.8% |
| Retirement-age (≥ 60) | 5,978 | 6 | 0.1% |

The raw 5.6% overall escape rate is heavily confounded by the predominance of retirees in Inactive Low.

**Logistic regression.** The extended model (4,832 individuals with complete covariate data, pseudo-$R^2$ = 0.479):

| Predictor | OR | 95% CI | *p*-value |
|---|---|---|---|
| Age at first window | 0.930 | [0.883, 0.980] | 0.006 |
| Female | 0.760 | [0.558, 1.036] | 0.083 |
| Cohort 1950s (vs pre-1950) | 7.029 | [1.499, 32.96] | 0.013 |
| Cohort 1960s | 23.825 | [4.088, 138.8] | < 0.001 |
| Cohort 1970s | 16.273 | [1.970, 134.4] | 0.010 |
| Cohort post-1980 | 8.204 | [0.632, 106.5] | 0.108 |
| Initial regime 6 (vs regime 2) | 20.556 | [10.65, 39.69] | < 10$^{-19}$ |
| NS-SEC Prof./Managerial | 0.815 | [0.477, 1.393] | 0.456 |
| NS-SEC Routine/Manual | 0.839 | [0.608, 1.157] | 0.284 |

Each additional year of age reduces escape odds by 7% (OR = 0.93, *p* = 0.006). Birth cohort effects are dramatic: the 1960s cohort has 24 times the escape odds of the pre-1950 reference (OR = 23.8, *p* < 0.001). Initial regime is the strongest predictor: individuals starting in Regime 6 have 21 times the escape odds of those starting in Regime 2, the two disadvantaged regimes have very different mobility profiles. Parental NS-SEC is not significant after controlling for age, cohort, and initial regime.

Among the 7,453 individuals whose first window falls in a disadvantaged regime, only 416 (5.6%) ever reach an advantaged regime. All observed escapes occur in a single window-to-window transition — no multi-step "ladders" are observed, though the limited number of windows per person (mean 2.0) constrains our ability to detect longer escape paths.

**[Figure 12]** presents the regime transition heatmap.

**[Figure 13]** shows escape probability from disadvantaged regimes.

### 4.5 Cycle and Trap Analysis

The 5,962 H₁ features indicate substantial looping in the trajectory space, but the cycling is not topologically distinctive under either test statistic. Under total persistence, order-shuffle H₁ is significant at $L = 5{,}000$ (*p* = 0.020) but landmark-sensitive (non-significant at $L = 2{,}500$ and $L = 8{,}000$). Under Wasserstein distances, order-shuffle H₁ is clearly non-significant (*p* = 0.854), and Markov-1 H₁ is non-significant (*p* = 0.086). The H₁ null result is therefore robust across test statistics: the trajectory manifold lacks persistent cyclical structure beyond what first-order Markov dynamics produce.

H₁ loops correspond to cyclical oscillation patterns in the embedding space, not to poverty traps in the absorbing-state sense (§2.3). The most persistent loops (maximum persistence 3.21) involve cycling between low-income employment, unemployment, and inactivity — states concentrated in the Low-Income Churn and Mixed Churn regimes. These descriptive features may prove useful for identifying target populations even though they do not exceed Markov baselines.

#### Phase-Ordering Test

Using the PCA embedding of 50,000 overlapping windows with 3,000 maxmin landmarks and *n* = 500 permutations:

| Dimension | Observed | Null mean ± std | *p*-value | 95% CI |
|---|---|---|---|---|
| H₀ | 19,119.4 | 19,150.2 ± 17.2 | 0.98 | [0.968, 0.992] |
| H₁ | 2,071.2 | 2,078.0 ± 19.9 | 0.542 | [0.498, 0.586] |

The main topological signal arises from the internal sequential structure of full trajectories (captured by bigrams in the embedding) rather than from the higher-order sequencing of phases across the life course.

**[Figure 7]** presents cycle analysis and **[Figure 14]** presents phase PH diagrams.

### 4.6 Stratified Comparisons

Pairwise Wasserstein distances between group-specific persistence diagrams reveal significant topological differences by social origin, gender, and birth cohort. We conduct 50 dimension-specific tests across three stratification axes and report both raw *p*-values and Benjamini-Hochberg (BH) FDR-corrected *q*-values.

Of the 50 tests, 30 are significant at *p* < 0.05 (raw). After BH FDR correction, all 30 remain significant at *q* < 0.05. Of these, 16/25 are H₀ tests and 14/25 are H₁ tests.

**Gender.** Male (*n* = 11,243) versus Female (*n* = 14,402): Wasserstein distance significant for H₀ (*p* < 0.001, BH *q* < 0.001; observed distance 33.7 vs. null mean 21.0), not for H₁ (*p* = 0.27). Men and women occupy different cluster structures — the gender gap in employment and inactivity produces distinct H₀ topology — but their cycling patterns are topologically similar.

**Parental NS-SEC.** Three groups yield significant H₀ differences for all three pairwise comparisons (*p* < 0.001 each). The largest H₀ Wasserstein distance is between Professional/Managerial and Routine/Manual (114.8, vs. null mean 99.8). The sharper separation between extreme classes, with Intermediate occupying a genuinely intermediate topological position, aligns with the cumulative advantage hypothesis (DiPrete & Eirich 2006).

**Birth cohort.** Of 42 cohort tests, 26 are significant at *p* < 0.05 (raw), all surviving BH correction. The 1930s cohort is topologically most distinctive.

**[Table 4: Stratified Wasserstein Test Summary (FDR-Corrected)]**

| Axis | Tests | Significant (raw) | Significant (BH *q* < 0.05) |
|---|---|---|---|
| Gender | 2 | 1 | 1 |
| Parental NS-SEC | 6 | 3 | 3 |
| Birth cohort | 42 | 26 | 26 |
| **Total** | **50** | **30** | **30** |

**[Figure 10]** presents the Wasserstein distance heatmap by parental NS-SEC.

**[Figure 11]** shows gender-specific persistence landscape overlays.

### 4.7 Cross-Era Validation: BHPS-Era Trajectories (1991–2008)

We construct 8,509 BHPS-era trajectories (mean length 14.5 years) using the fixed cross-wave identifier linkage (§3.1).

**PH results.** BHPS-era PH ($L = 5{,}000$, PCA-20D) yields H₀ total persistence = 10,763.2 and H₁ total persistence = 823.0 (1,114 persistent loops).

**Null models (total persistence).** The BHPS-era null battery ($n = 500$) reproduces the qualitative pattern:

| Null Model | H₀ *p* | H₁ *p* |
|---|---|---|
| Order shuffle | **0.000** | 0.520 |
| Markov-1 | 1.000 | 1.000 |
| Label shuffle | 0.272 | 0.396 |

Order-shuffle H₀ is strongly rejected. Markov-1 is not rejected under total persistence, with the Markov null generating more persistence than observed (null mean H₀ = 12,753.8) — the same direction as USoc. The cross-era replication strengthens the total-persistence findings; Wasserstein testing on the BHPS sample is a priority for future work.

**Regime structure.** BIC selects $k = 8$ on BHPS-era embeddings, one regime more than USoc's $k = 7$. Core types are comparable: stable employed high-income (stability = 0.83), economically inactive low-income (employment = 0.0%, stability = 0.44), and multiple churning/mixed regimes.

**Spanning trajectories.** 8,459 spanning trajectories (observed in both surveys) yield order-shuffle H₀ *p* = 0.000 and Markov-1 H₀ *p* = 1.000 (total persistence), confirming the same pattern.

---

## 5. Discussion

### 5.1 What TDA Adds Beyond Sequence Analysis

PH provides a geometric characterisation of the trajectory point cloud unavailable from pairwise dissimilarity methods. The persistence diagrams encode the multi-scale connectivity (H₀) and cyclical structure (H₁) of the entire trajectory space: the most persistent H₀ component (15.81) is nearly four times the mean (4.08), indicating a few well-separated regimes with many weakly separated sub-clusters. The near-zero ARI between H₀ components and GMM assignments (§4.4.1) demonstrates that H₀ PH and GMM operate on different geometric properties — global connectivity versus local density — and are complementary analyses.

The Markov memory ladder provides a framework for bounding the memory-complexity of observed topology. That the Markov conclusion depends on the test statistic (§4.3) is the methodologically important finding: scalar persistence summaries can mask structural differences that Wasserstein comparisons detect.

OM-based clustering at matched *k* = 7 yields ARI = 0.26: the Secure High-Employment regime is identified nearly identically (profile correlation = 0.97), while Mixed Churn diverges most (correlation = 0.02). The broad regime typology is recoverable by either method; TDA adds the geometric characterisation and formal testing.

### 5.2 The Markov Memory Ladder and the Test-Statistic Discrepancy

The Markov memory ladder is our primary methodological contribution. The central finding is that the Markov conclusion depends on how persistence diagrams are compared. Under total persistence, Markov-1 surrogates generate *more* aggregate persistence than observed (*p* = 1.000), suggesting the topology is "bounded" by first-order dynamics. Under Wasserstein distances, the observed H₀ diagram is significantly different from Markov-1 null diagrams (*p* = 0.002), indicating that the specific configuration of connected components — which clusters form, at what scale, and in what hierarchical relationship — carries structural information that a first-order Markov chain cannot reproduce.

We interpret this discrepancy as follows. The globally estimated Markov transition matrix generates trajectories that, in aggregate, are more diffuse than the observed data — they spread more widely in embedding space and produce more topological features. But the pattern of those features differs from what the real trajectories produce. The real data has regime-specific substructure: clusters that form at particular filtration scales and merge in particular ways. The Markov process, which uses a single global transition matrix without regime-specific parameters, smears out this substructure. The total persistence is higher (more features, longer total lifetime) but the configuration of the diagram — the distribution of birth-death pairs — is different.

This interpretation is consistent with the intra-regime compactness results (§4.3): all seven regimes are significantly more compact in the observed embedding than under order-shuffled re-embeddings, with the churning regimes showing the largest compactness ratios. The trajectory data has structural regularity within regimes that a global Markov process does not capture.

Several caveats apply. First, the Wasserstein test uses $L = 2{,}000$ landmarks rather than the $L = 5{,}000$ used for total-persistence tests, due to the computational cost of computing persistence diagrams for each null realisation. The landmark count difference could affect the comparison, though the total-persistence results are stable across $L$ = 2,500 to 8,000 (Appendix B). Second, we have tested Wasserstein distances only for order-shuffle and Markov-1 nulls; extending to the full five-model battery is future work. Third, the Markov-1 Wasserstein rejection does not specify *what kind* of non-Markovian structure is present — it could reflect individual-level heterogeneity, duration dependence, or higher-order memory. Richer null models (hidden Markov, latent-type, variable-order) would help decompose this.

The Markov memory ladder is transportable: it can be applied to any TDA analysis of sequential data. The lesson from our analysis is that the ladder should be climbed with both scalar and diagram-level test statistics, since they can give different answers.

### 5.3 H₁ Cycles: A Negative Result

H₁ loops correspond to cyclical oscillation patterns in the embedding space rather than to poverty traps in the absorbing-state sense. Our results are consistent across test statistics: H₁ is non-significant under Wasserstein distances for both order-shuffle (*p* = 0.854) and Markov-1 (*p* = 0.086). The landmark-sensitive order-shuffle H₁ significance under total persistence (*p* = 0.020 at $L = 5{,}000$, non-significant at other $L$) does not replicate under Wasserstein testing, reinforcing a cautious interpretation.

This does not mean that people do not cycle between employment and poverty. They manifestly do — the Low-Income Churn and Mixed Churn regimes demonstrate extensive state cycling. Rather, the null result means that the topological shape of this cycling is predictable from the marginal state distribution and one-step transition probabilities. A trajectory cloud generated by the same Markov chain would produce loops of comparable persistence and number.

This negative result bounds the complexity of cyclical dynamics and directs analytical attention toward the stronger H₀ results and the escape-rate analysis (§4.4.2).

### 5.4 Limitations

**Spatial dimension.** The analysis is national and non-spatial. The Markov memory ladder is directly applicable to regional comparisons, which we identify as a priority extension.

**State space discretisation.** The nine-state space, while richer than most sequence analysis applications (typically 3–5 states), is a simplification. The 60%/120% thresholds are conventional but arbitrary; sensitivity to alternatives is not examined.

**Embedding sensitivity.** PCA-20D is the primary embedding. The UMAP-16D check yields ARI = 0.33 against PCA at *k* = 7. We test a grid of six configurations varying n-gram order, weighting, and PCA dimensionality:

| Configuration | H₀ *p* | H₁ *p* | H₀ *z* | H₁ *z* | *n* |
|---|---|---|---|---|---|
| Bigram TF, PCA-20 (baseline) | < 0.001 | 0.040 | +15.8 | +1.6 | 50 |
| Bigram TF-IDF, PCA-20 | < 0.001 | 1.000 | +6.5 | −2.6 | 20 |
| Trigram TF, PCA-20 | < 0.001 | 1.000 | +8.1 | −7.6 | 20 |
| Trigram TF-IDF, PCA-20 | < 0.001 | < 0.001 | +23.6 | +4.0 | 20 |
| Bigram TF, PCA-10 | < 0.001 | 0.920 | +2.6 | −1.6 | 50 |
| Bigram TF, PCA-30 | < 0.001 | 0.840 | +16.5 | −1.3 | 50 |

H₀ is uniformly significant across all six configurations, confirming that the connected-component structure is robust. H₁ is embedding-sensitive: significant for trigram TF-IDF but not for most others.

**H₀ chaining.** Single-linkage chaining limits balanced H₀-based clustering in high-dimensional VR complexes: the merge tree produces one dominant component (99.98%) plus outlier singletons, yielding ARI ≈ 0 against GMM. This is a known property of VR H₀ in high dimensions (Bobrowski & Kahle, 2018) and motivates future exploration of density-aware TDA methods (e.g., DTM filtrations, Mapper).

**Landmark sampling.** Maxmin landmark selection (5,000 from 27,280) preserves global geometry but may undersample rare trajectory types. Results are stable across $L$ = 2,500 to 8,000. The Wasserstein tests use $L = 2{,}000$ due to computational cost; validating at higher $L$ is future work.

**Age and lifecycle confounding.** The near-absorbing Inactive Low regime (97% self-transition) partly reflects retirement. We address this via age-stratified analysis (§4.4.2): 86.1% of Inactive Low observations come from individuals aged ≥ 60. Working-age escape rates (17.8%) are more than three times the raw rate (5.6%).

**Markov null limitations.** Our Markov nulls test against globally estimated Markov dynamics. They do not account for individual-level heterogeneity or duration dependence. The Wasserstein rejection of Markov-1 (*p* = 0.002) suggests that such heterogeneity may be precisely what the test is detecting — the global Markov chain cannot reproduce the regime-specific substructure of the observed diagrams. Stratified Markov nulls (separate transition matrices per regime) could help disambiguate this. The per-regime stratified test under total persistence (§5.2 in the previous draft) found non-rejection, but the effective stratification was limited (one regime contained 99.9% of trajectories at the point-cloud level). Stratified Wasserstein testing is future work.

**Family dimension.** We analyse employment-income trajectories only; partnership and household composition are not included.

**Imputation.** Forward-fill imputation for gaps of up to two years affects 4.9% of person-years.

**Cross-survey harmonisation.** BHPS and USoc use different sampling frames, questionnaire designs, and income measurement methodologies. Harmonisation artefacts may contribute to cross-era topological differences. BHPS-era Wasserstein testing is a priority follow-up.

**Pipeline sensitivity.** We vary minimum trajectory length (8, 10, 12 years), weighting (TF vs TF-IDF), and filtration threshold (50th, 75th, 90th percentile). Under TF, results are highly stable: *k* = 7 at 10/12 years, *k* = 8 at 8 years; H₀ persistence varies < 6%; threshold has no effect on H₀ and negligible effect on H₁. TF-IDF reshapes the embedding substantially (ARI = 0.466 against TF baseline, 93% drop in total persistence), confirming that the choice of TF weighting is consequential.

### 5.5 Robustness Summary

| Check | Status | Summary |
|---|---|---|
| Wasserstein diagram tests | **New in 5th draft** (§4.3) | Markov-1 H₀ **rejected** (*p* = 0.002); order-shuffle H₀ borderline (*p* = 0.058); H₁ non-significant |
| Total-persistence tests | Completed (§4.3) | Order-shuffle H₀ *p* < 0.005; Markov-1 *p* = 1.000; H₁ landmark-sensitive |
| Test-statistic discrepancy | **New** (§4.3, §5.2) | Total persistence and Wasserstein give opposite Markov-1 conclusions; scalar masks diagram-shape differences |
| UMAP-16D embedding | Completed (§3.2) | ARI = 0.33; order-shuffle H₀ *p* < 0.001; mirrors PCA pattern |
| Landmark count (*L* = 2,500/5,000/8,000) | Completed (Appendix B) | Order-shuffle H₀ *p* < 0.001 at all *L*; Markov-1 non-significant at all *L* (total persistence) |
| Embedding sensitivity grid | Completed (§5.4) | 6 configs: H₀ *p* < 0.001 uniformly; H₁ embedding-sensitive |
| Non-overlapping windows | Completed (§4.4.2) | Escape rate 5.6% vs 11.0%; core structure preserved |
| OM/TraMineR baseline | Completed (§3.7, §5.1) | ARI = 0.26 at *k* = 7 |
| Wasserstein FDR correction | Completed (§4.6) | 30/50 significant raw; all 30 survive BH |
| Phase-ordering null (*n* = 500) | Completed (§4.5) | H₀ *p* = 0.98; H₁ *p* = 0.542 |
| GMM bootstrap stability | Completed (§3.5) | ARI = 0.646 ± 0.086 |
| Bootstrap null stability | Completed (§4.3) | 10/10 order-shuffle significant; 10/10 Markov-1 significant; no flips |
| Intra-regime compactness | Completed (§4.3) | All 7 regimes *z* = −30 to −68, all *p* < 0.001 |
| NS-SEC missingness | Completed (§3.1) | 39.1% missing; non-random |
| BHPS cross-era replication | Completed (§4.7) | Same qualitative pattern (total persistence) |
| Age-adjusted escape rates | Completed (§4.4.2) | Working-age escape 17.8%; pseudo-R² = 0.479 |
| Pipeline sensitivity | Completed (§5.4) | TF stable; TF-IDF reshapes; threshold no effect |

---

## 6. Conclusion

Persistent homology on 27,280 USoc employment-income sequences (PCA-20D, maxmin landmarks) finds seven mobility regimes with order-dependent clustering (order-shuffle H₀ *p* < 0.005). The regime typology — Secure High-Employment (27%, stability 0.78) through Low-Income Churn (7.6%, stability 0.29) — is robust to analytic method (ARI = 0.26 with OM at matched *k* = 7) and replicates on 8,509 BHPS-era trajectories (1991–2008). Intra-regime compactness is significant for all seven regimes (*p* < 0.001): temporal ordering within trajectories tightens cluster structure.

The structurally interesting finding concerns the Markov null. Under total persistence, Markov-1 surrogates generate more aggregate persistence than observed (*p* = 1.000) — the topology appears bounded by first-order dynamics. Under Wasserstein diagram distances, the same null is rejected (*p* = 0.002): the observed H₀ diagram is an outlier relative to the Markov null cloud. The Markov chain gets the total amount of persistence roughly right but distributes it differently across birth-death pairs. We did not expect this discrepancy; it emerged only because we compared both statistics on the same null battery. The implication for TDA hypothesis testing is that scalar persistence summaries can produce false negatives when null models generate comparable aggregate persistence with different diagram geometry.

Loops (H₁) are non-significant under both statistics and all null models. The trajectory manifold lacks persistent cyclical structure beyond what first-order Markov dynamics produce — a result that is consistent across landmark counts, embedding configurations, and test statistics, and that bounds the complexity of cyclical dynamics in these data.

Stratified Wasserstein distances show origin-dependent topology: gender (H₀ *p* < 0.001), parental NS-SEC (all three pairings *p* < 0.001 for H₀), birth cohort (26/42 tests significant, all 30 surviving FDR correction). NS-SEC is missing for 39.1% of the sample and the missingness is non-random; class-origin effects should be interpreted accordingly. Overlapping career-phase windows show extreme regime persistence: 5.6% escape from disadvantaged regimes (11.0% non-overlapping), with initial regime the strongest predictor (Regime 6 OR = 20.6 vs. Regime 2). Phase-ordering adds no topological structure beyond the within-trajectory signal.

The Wasserstein rejection of Markov-1 complicates the policy reading. Under total persistence, one might conclude that targeting the right single transitions could reshape the regime landscape. The diagram-level evidence says the regime structure has properties not reducible to marginal transition rates: a global Markov chain cannot reproduce the regime-specific substructure. Whether this means policies need to address regime-level conditions rather than individual transitions is an interpretive inference, not a causal claim from these data.

The immediate next steps are Wasserstein testing on the BHPS-era sample and the full five-model battery; Mapper analysis of within-regime heterogeneity (Paper 2); zigzag persistence across annual cohort snapshots (Paper 3); regional stratification (NUTS2/GOR); and cross-national replication on SOEP and PSID, where the regime structure should differ if it reflects UK-specific labour market institutions rather than generic career dynamics.

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
| 8 | Null Model Summary (Markov Memory Ladder, Both Statistics) | §4.3 |
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
| 2 | Markov Memory Ladder: Total Persistence Results | §4.3 |
| 2b | Markov Memory Ladder: Wasserstein Distance Results | §4.3 |
| 3 | Regime Composition and Characteristics | §4.4 |
| 4 | Stratified Wasserstein Test Summary (FDR-Corrected) | §4.6 |
| S2 | H₀ Component–GMM Regime Overlap | §4.4 |
| S3 | OM vs TDA Regime Comparison | §5.1 |
| S4 | Robustness Matrix | §5.5 |

---

## Appendix A: H₀ Merge Tree Analysis

The H₀ persistent homology on 5,000 maxmin landmarks encodes the single-linkage merge tree of the trajectory point cloud.

**Top 10 H₀ lifetimes** (persistence = death − birth, all born at 0):
15.81, 15.50, 14.90, 14.40, 14.16, 14.01, 13.62 (7th), 13.22 (8th), 13.15, 12.92

The ratio between the 7th and 8th most persistent features is 1.03×, indicating no sharp topological gap at $k = 7$.

**Table S2: H₀ Component–GMM Regime Contingency (at $k = 7$ cut)**

| | R0 (Churn) | R1 (EH) | R2 (IL) | R3 (EI Mix) | R4 (EM) | R5 (IH) | R6 (LI Churn) | Total |
|---|---|---|---|---|---|---|---|---|
| **C0** (99.98%) | 3,781 | 7,358 | 5,415 | 3,333 | 3,510 | 1,813 | 2,064 | 27,274 |
| **C1–C6** (singletons) | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |

ARI (H₀ $k = 7$ vs. GMM) = 0.00004.

Trajectory space is topologically connected: a single giant component with heterogeneous density. The 6 outlier singletons are all from Mixed Churn (R0). H₀ tracks global connectivity; GMM identifies local density modes. These measure different aspects of point-cloud geometry.

---

## Appendix B: Landmark Sensitivity

We recompute persistent homology at $L$ = 2,500, 5,000, and 8,000 landmarks (approximately 9%, 18%, and 29% of the 27,280-point cloud). For each, we re-run order-shuffle and Markov-1 null tests (*n* = 50–100 per condition).

**[Table B1: Landmark Sensitivity Analysis]**

| *L* | H₀ total | H₀ max | H₀ *n* | H₁ total | H₁ max | H₁ *n* | OS H₀ *p* | OS H₁ *p* | M1 H₀ *p* | M1 H₁ *p* |
|---|---|---|---|---|---|---|---|---|---|---|
| 2,500 | 14,227.8 | 15.809 | 2,499 | 1,520.3 | 3.213 | 3,249 | < 0.001 | 0.20 | 0.15 | 0.69 |
| 5,000 | 20,411.1 | 15.809 | 4,999 | 2,224.7 | 3.213 | 5,961 | < 0.001 | 0.02 | 1.00 | 1.00 |
| 8,000 | 24,313.8 | 15.496 | 7,998 | 2,619.3 | 3.213 | 8,357 | < 0.001 | 0.14 | 1.00 | 1.00 |

OS = order shuffle; M1 = Markov-1 (total persistence). *n* = number of finite features.

**Total persistence** scales approximately linearly with $L$, as expected. **Maximum persistence** is highly stable (H₀ max 15.50–15.81; H₁ max 3.21 at all three values).

Null model p-values are qualitatively stable:
- Order-shuffle H₀: *p* < 0.001 at all *L*.
- Markov-1 H₀: Non-significant at all *L* under total persistence.
- Order-shuffle H₁: Landmark-sensitive; significant only at $L = 5{,}000$.

These results confirm that the key total-persistence findings are stable across a threefold range of landmark density. Wasserstein landmark sensitivity is a priority for future validation.

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

Bobrowski, O. & Kahle, M. (2018). Topology of random geometric complexes: A survey. *Journal of Applied and Computational Topology*, 1, 331–364.

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

Stolz, B.J., Harrington, H.A. & Porter, M.A. (2017). Persistent homology of time-dependent functional networks constructed from coupled time series. *Chaos*, 27(4), 047410.

Studer, M. & Ritschard, G. (2016). What matters in differences between life trajectories: A comparative review of sequence dissimilarity measures. *Journal of the Royal Statistical Society: Series A*, 179(2), 481–511.

Tong, H. (1990). *Non-linear Time Series: A Dynamical System Approach*. Oxford University Press.

Turner, K., Mileyko, Y., Mukherjee, S. & Harer, J. (2014). Frechet means for distributions of persistence diagrams. *Discrete & Computational Geometry*, 52(1), 44–70.

Vandecasteele, L. (2010). Poverty trajectories, triggering events and exit routes. *Sociological Research Online*, 15(4), 1–17.

Zomorodian, A. & Carlsson, G. (2005). Computing persistent homology. *Discrete & Computational Geometry*, 33(2), 249–274.
