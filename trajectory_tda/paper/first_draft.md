# Topological Dynamics of UK Life-Course Trajectories

**Authors:** [Author Names]
**Target Journal:** *Journal of Economic Geography*
**Date:** February 2026

---

## Abstract

Longitudinal panel data captures the temporal structure of life-course dynamics, yet conventional sequence analysis methods treat trajectories as character strings and discard their geometric structure in high-dimensional space. No existing framework detects regime formation or cyclical traps in trajectory point clouds with formal significance testing. Here we apply persistent homology — the core tool of topological data analysis (TDA) — to 27,280 employment-income trajectories drawn from the British Household Panel Study and Understanding Society (1991–2023). Each trajectory is a sequence of nine states combining employment status (employed, unemployed, inactive) with income tercile (low, mid, high), embedded into 20-dimensional PCA space via n-gram frequency vectors and analysed using Vietoris–Rips persistent homology with 5,000 maxmin landmarks. We introduce a novel "Markov memory ladder" — a battery of five null models of escalating structural complexity — that systematically characterises the generating process underlying the observed topology.

We discover seven distinct mobility regimes via Gaussian mixture models optimised by BIC. Order-shuffle H₀ is strongly significant (*p* < 0.001, *n* = 500), confirming that temporal ordering creates real topological structure beyond random relabelling. However, regime topology is consistent with first-order Markov dynamics (Markov-1 H₀ *p* = 0.148), and H₁ cycles are compatible with state frequencies and transition structure (*p* > 0.25 across all nulls). Stratified Wasserstein distances reveal significant topological differences by gender (2/8 dimensions), parental NS-SEC (6/24), and birth cohort (42/168). Overlapping 10-year career-phase windows confirm extreme regime stickiness: among 7,453 individuals starting in disadvantaged regimes, only 416 (5.6%) escape to advantaged regimes, and phase-ordering adds no additional topological signal (*p*(H₀) = 0.95, *p*(H₁) = 0.75).

TDA thus reveals structural features of the mobility landscape invisible to sequence distance methods, while the memory ladder pins down the complexity of the generating process. Policy implications centre on the sufficiency of targeting single transitions — rather than multi-step pathways — to reshape the regime landscape.

**Keywords:** persistent homology, topological data analysis, social mobility, life-course trajectories, Markov models, regime switching

**JEL Codes:** C14, C38, J62, D63

---

## 1. Introduction

### 1.1 Motivation: UK Social Mobility and Life-Course Dynamics

Intergenerational social mobility in the United Kingdom has been the subject of sustained scholarly and policy attention. Evidence accumulated over two decades indicates that mobility rates have stagnated or declined since the 1970s, with recent cohorts showing lower rates of upward movement relative to their parents' generation (Blanden et al. 2004, 2013; Goldthorpe & Mills 2008). This decline is not merely a statistical artefact of measurement: it reflects deeper life-course dynamics in which persistent unemployment, income churning, and structural inactivity create multiple equilibria in employment-income states. Cross-sectional snapshots — comparing parents' and children's occupational class or income at a single point in time — inevitably miss these dynamics. What matters is not merely where individuals start and end, but the *shape* of the path between.

The British Household Panel Study (BHPS, 1991–2008) and its successor Understanding Society (USoc, 2009–2023) together provide one of the longest continuous household panels in the social sciences: 32 years of annual observations on over 118,000 respondents. From this population, we reconstruct 27,280 individual trajectories with at least 10 consecutive years of data. Each trajectory is a time-ordered sequence through a nine-state space combining employment status — employed (E), unemployed (U), or inactive (I) — with income tercile — low (L), mid (M), or high (H) — derived from equivalised household income relative to 60% of the contemporary median.

The resulting trajectories reveal a labour market in which employment dominates (58% of person-years) but inactivity is pervasive (32%), and low income affects over a third (36%) of observed person-years. These are not transient states: the modal trajectory length in our sample is 13 years, sufficient to observe structural persistence, cycling, and — for some — escape from disadvantaged states. The trajectories thus encode not merely labour market status but the temporal dynamics of socioeconomic position over the life course.

From a policy perspective, the question of whether disadvantaged trajectories represent absorbing states or transient spells is central to the design of welfare-to-work programmes, skills interventions, and the UK Government's "Levelling Up" agenda (HM Government 2022). If low-income churning creates topological traps — persistent cycles from which exit is rare — then marginal interventions targeting single transitions may prove inadequate. If, conversely, the landscape of trajectories is well described by low-order Markov dynamics, then targeting the right transitions could be sufficient. Distinguishing between these scenarios requires methods that go beyond measuring distances between sequences.

### 1.2 Research Gap

Sequence analysis methods — optimal matching (OM) and its many variants — have dominated life-course research since Abbott's (1995) influential importation of biological sequence techniques into sociology. OM and related methods treat trajectories as strings and compute pairwise distances under substitution and indel (insertion-deletion) cost matrices, enabling cluster analysis to identify "types" of life course. This approach has been productive, generating typologies of employment careers, family formation, and housing trajectories across many national contexts (Abbott & Tsay 2000; Lesnard 2010; Gauthier et al. 2010).

However, sequence analysis has fundamental limitations for the questions we pose. First, OM distances depend critically on the substitution cost matrix, which is typically set a priori or estimated from transition rates — introducing subjectivity at a foundational level. Second, OM and its variants treat trajectories as one-dimensional objects: they measure pairwise distances but have no concept of the global *geometry* or *topology* of the trajectory space. They cannot detect persistent clusters (connected components), loops (cyclical traps), or higher-dimensional voids in the point cloud of embedded trajectories. Third, there is no standard framework for formal significance testing — for asking whether the observed structure exceeds what would be expected under explicit generative null models.

Markov chain models, the other workhorse of life-course analysis, capture local transition probabilities but are not designed to detect global shape. A Markov model can tell us the probability of moving from unemployment to employment, but it cannot detect whether the cloud of all trajectories in embedding space has a hole — a topological signature of cyclical trapping — or whether the number and separation of trajectory clusters exceeds what memoryless transitions would produce.

Topological data analysis (TDA), via persistent homology (PH), directly addresses these limitations. PH identifies topological features — connected components (H₀), loops (H₁), and higher-dimensional voids — that persist across a range of spatial scales, providing a multi-scale signature of the shape of a point cloud that is robust to noise and dimensionality (Carlsson 2009; Edelsbrunner & Harer 2010). TDA has been applied to financial time series (Gidea & Katz 2018), brain networks (Saggar et al. 2018), gene expression (Rizvi et al. 2017), and materials science (Hiraoka et al. 2016), but no study has applied persistent homology to longitudinal socioeconomic trajectories.

Critical gaps remain: How does the topology of trajectory space relate to socioeconomic mobility regimes? Can we systematically test whether observed topological structure exceeds Markov baselines of varying complexity? And does the ordering of career phases over the life course create additional topological structure beyond what the composition of individual trajectories already provides?

### 1.3 Contribution and Roadmap

This paper makes three contributions. First, we present the first application of persistent homology to longitudinal life-course data, demonstrating that TDA reveals structural features of the mobility landscape — including the number and separation of trajectory regimes — that are invisible to sequence distance methods. Second, we introduce a **Markov memory ladder**: a systematic battery of five null models of increasing complexity (label shuffle, cohort shuffle, order shuffle, Markov order-1, Markov order-2) that decomposes the topological signal into contributions from state frequencies, temporal ordering, and memory length. This provides a precise, testable characterisation of the complexity of the generating process — a methodological contribution applicable far beyond the present empirical setting. Third, we extend the analysis beyond full trajectories to overlapping career-phase windows, quantifying regime stickiness and testing whether higher-order phase sequencing adds topological structure.

We discover seven robust mobility regimes and show that H₀ topological structure (cluster separation) is genuinely order-dependent (order-shuffle *p* < 0.001) but requires at most first-order memory to generate (Markov-1 *p* = 0.148). H₁ cycles — potential topological signatures of churning traps — are consistent with state frequencies and Markov transitions (*p* > 0.25 across all nulls), an important negative result that we report honestly rather than over-interpreting. Stratified analysis reveals origin-dependent topology, with parental NS-SEC and birth cohort creating the strongest topological differentiation. Overlapping 10-year windows confirm extreme regime stickiness (5.6% escape rate from disadvantaged regimes), while phase-order shuffle tests show that the temporal sequencing of career phases adds no detectable topological structure.

We are committed to honest reporting of both positive and negative results. The strong H₀ signal validates the regime structure; the null H₁ result bounds the complexity of trajectory cycling; and the phase-ordering null constrains the role of life-course sequencing. Together, these results provide a more precise characterisation of UK mobility dynamics than either sequence analysis or Markov modelling alone.

The remainder of the paper is organised as follows. Section 2 reviews sequence analysis, TDA foundations, poverty trap theory, and statistical null models. Section 3 describes the data and methodology. Section 4 presents results. Section 5 discusses implications, limitations, and future directions.

---

## 2. Literature Review

### 2.1 Sequence Analysis in Social Science

The application of sequence analysis to life-course data originated with Abbott's (1995) proposal to adapt biological sequence techniques for sociological use. Optimal matching (OM) computes distances between state sequences using substitution and indel operations, analogous to edit distances in string matching. The resulting distance matrix is then used for cluster analysis (typically Ward's hierarchical clustering or partitioning around medoids) to identify trajectory "types".

OM and its variants have produced influential typologies in many domains: employment careers (Halpin & Chan 1998), family formation (Elzinga & Liefbroer 2007), and housing trajectories (Coulter et al. 2016). Lesnard (2010) proposed dynamic Hamming distances that weight substitution costs by temporal proximity, addressing the criticism that OM treats all time points equally. Gauthier et al. (2010) extended the framework to multichannel sequences, enabling joint analysis of employment and family states. Studer & Ritschard (2016) provided a comprehensive software implementation in R's TraMineR package.

Despite this productivity, sequence analysis has well-documented limitations. The dependence on substitution cost matrices introduces subjectivity: different cost specifications can yield different typologies from the same data (Robette & Thibault 2008). The resulting distance measures are fundamentally one-dimensional — they compare sequences pairwise but do not characterise the global geometry of the trajectory space. There is no natural notion of "closeness in trajectory space" that preserves topological invariants such as connected components, loops, or higher-dimensional voids. Finally, significance testing is typically absent: cluster solutions are evaluated by silhouette scores or Calinski-Harabasz indices, but there is no formal test of whether the observed clustering exceeds what specific null models would produce.

### 2.2 Topological Data Analysis Foundations

Persistent homology (PH) provides a rigorous mathematical framework for detecting and quantifying topological features in data. Given a point cloud $X \subset \mathbb{R}^d$, PH constructs a filtration — a nested sequence of simplicial complexes $K_0 \subseteq K_1 \subseteq \cdots \subseteq K_m$ — by connecting points within distance $\epsilon$ and tracking which topological features appear (are "born") and disappear ("die") as $\epsilon$ increases (Edelsbrunner et al. 2002; Zomorodian & Carlsson 2005).

The Vietoris–Rips (VR) complex, the most common choice for point cloud data, includes a $k$-simplex whenever all $\binom{k+1}{2}$ pairwise distances are below $\epsilon$. For $n$ points, the VR complex can have up to $2^n$ simplices, making direct computation infeasible for large datasets. Maxmin landmark selection (de Silva & Carlsson 2004) addresses this by greedily selecting a subset of $L \ll n$ points that are maximally dispersed, constructing the VR complex on landmarks only. Ripser (Bauer 2021) provides state-of-the-art computational efficiency, exploiting the apparent pairs optimisation to compute VR persistence through H₁ (and optionally H₂) on thousands of landmarks in minutes.

The output of PH is a persistence diagram (PD): a multiset of birth-death pairs $(b_i, d_i)$ where feature $i$ is born at filtration value $b_i$ and dies at $d_i$. Features with large persistence $\ell_i = d_i - b_i$ are interpreted as genuine topological structure, while short-lived features near the diagonal are attributed to noise. In dimension 0 (H₀), features correspond to connected components: each merger of two components kills one H₀ feature. In dimension 1 (H₁), features correspond to loops or cycles: a loop forms at birth and is filled in at death. Summary statistics include total persistence $\sum_i \ell_i$, maximum persistence $\max_i \ell_i$, and persistence entropy $-\sum_i \hat{\ell}_i \log \hat{\ell}_i$ where $\hat{\ell}_i = \ell_i / \sum_j \ell_j$ (Atienza et al. 2019).

A fundamental property of PH is stability: small perturbations in the input point cloud produce small changes in the persistence diagram, measured by the bottleneck or Wasserstein distance (Cohen-Steiner et al. 2007). This guarantees that topological summaries are robust to noise, sampling variation, and minor measurement errors — a critical property for survey data with imputation and harmonisation challenges.

For comparing persistence diagrams across groups, the Wasserstein distance $W_p(D_1, D_2)$ measures the cost of the optimal transport between two diagrams, providing a principled metric for testing whether subpopulations have different topological structure (Turner et al. 2014).

### 2.3 Poverty Traps and Mobility Regimes

The economics of poverty traps posits that disadvantaged states can be self-reinforcing through multiple equilibria (Azariadis & Stachurski 2005). When returns to human capital investment are nonlinear — or when credit constraints, neighbourhood effects, or discrimination create threshold dynamics — individuals may become trapped in low-productivity equilibria from which escape requires large, discrete shocks rather than marginal improvements (Barrett & Carter 2013).

Life-course researchers have identified analogous patterns in longitudinal data. Vandecasteele (2010) distinguished between stable, mobile, and churning poverty trajectories using Belgian panel data. Jenkins (2011) documented extensive income churning in the UK, where many individuals cycle between poverty and near-poverty without achieving durable exits. Savage et al. (2013) used the Great British Class Survey to identify seven social classes, some characterised by cultural and social capital deficits that reinforce economic disadvantage.

The connection to topology is natural. If mobility regimes exist as distinct clusters in trajectory space, they will appear as persistent H₀ components. If churning creates cyclical traps — where individuals cycle between states without permanently escaping — these will appear as persistent H₁ loops. The distance between components (measured by the gap between large H₀ births and deaths) characterises the "height" of regime barriers. A topological analysis can thus provide a geometric characterisation of the mobility landscape that complements both sequence typologies and Markov transition models.

### 2.4 Statistical Null Models for TDA

The statistical significance of topological features requires comparison to appropriate null distributions. Robinson & Turner (2017) proposed permutation tests for PH, comparing observed total persistence or Betti numbers to distributions generated by permuting group labels. Stolz et al. (2017) applied PH to time-dependent functional networks, using surrogate data methods as nulls.

For life-course trajectories, the relevant null models must be carefully chosen to test specific hypotheses. A label shuffle null (permuting state labels globally) tests whether the specific identity of states matters; an order shuffle (permuting each trajectory's state sequence) tests whether temporal ordering matters, preserving marginal state frequencies; and a Markov-$k$ null (simulating from an estimated $k$-th order Markov chain) tests whether topology exceeds what $k$-step memory produces.

Higher-order Markov chains as generative models have a long history in sociology (Singer & Spilerman 1976; Tong 1990). Our contribution is to arrange these null models into a systematic "memory ladder" — a sequence of increasingly structured null hypotheses that progressively preserves more of the observed data's structure. When the observed topology becomes consistent with a Markov-$k$ null, we can conclude that the topological complexity of the trajectory space is well captured by $k$-step memory. This provides a precise, testable decomposition of topological complexity into its sources — a methodological innovation applicable to any setting where TDA is combined with sequential data.

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

As a sensitivity check, we compute UMAP embeddings with 16 dimensions and compare GMM cluster assignments to those from PCA-20D. The adjusted Rand index (ARI) between the two clusterings is 0.31, indicating that while three broad macro-types (secure employment, inactive/marginal, churning/mixed) are stable across embedding methods, finer regime boundaries are embedding-dependent. This is consistent with UMAP and PCA capturing different aspects of local versus global geometry (McInnes et al. 2018), and cautions against over-interpreting differences between neighbouring regimes. We report PCA-20D as the primary embedding and UMAP-16D as a supplementary sensitivity analysis (Figure S1).

### 3.3 Persistent Homology

We compute Vietoris–Rips persistent homology on the PCA-20D point cloud using the following pipeline:

1. **Maxmin landmark selection**: From the 27,280 embedded trajectories, we select 5,000 landmarks using the greedy furthest-point (maxmin) algorithm (de Silva & Carlsson 2004). This selects an initial seed point and iteratively adds the point maximally distant from the current landmark set, producing a well-dispersed subsample that preserves the geometric structure of the full cloud.

2. **VR complex construction and PH computation**: We construct the Vietoris–Rips filtration on the 5,000 landmarks and compute persistence through H₁ using Ripser (Bauer 2021), with the filtration threshold set to the 75th percentile of pairwise distances. Computation completes in approximately 158 seconds on a standard desktop CPU.

3. **Persistence diagrams and summaries**: The output comprises H₀ (connected components) and H₁ (loops) persistence diagrams. For each dimension, we compute total persistence $\sum_i (d_i - b_i)$, maximum persistence, feature count, and persistence entropy.

H₀ features correspond to the merging of trajectory clusters as the filtration radius increases: long-lived H₀ features indicate well-separated regimes. H₁ features correspond to loops in the trajectory space: persistent loops may indicate cyclical trapping where trajectories circulate among a subset of states without converging to a single attractor.

### 3.4 Null Model Battery: The Markov Memory Ladder

We introduce a battery of five null models arranged in order of increasing structural fidelity to the observed data. For each null model, we generate surrogate trajectory datasets, re-embed using the same n-gram + PCA pipeline, recompute PH on maxmin landmarks, and compare total persistence to the observed value via one-sided permutation *p*-values.

**Null 1 — Label shuffle** (*n* = 100): Permute state labels globally across all person-years, destroying all individual-level structure. This trivial null tests whether the specific identities of the nine states matter at all.

**Null 2 — Cohort shuffle** (*n* = 100): Permute trajectories within birth-cohort bins, testing whether cross-cohort differences drive the topological signal while preserving within-cohort structure.

**Null 3 — Order shuffle** (*n* = 500): For each individual, randomly permute the temporal order of their state sequence, preserving per-person state frequencies but destroying all transition and temporal structure. This is the critical test: if topology is significant against order shuffle, temporal ordering genuinely contributes to the shape of the trajectory space.

**Null 4 — Markov order-1** (*n* = 500): Estimate a first-order Markov transition matrix from the observed data and simulate surrogate trajectories of the same lengths, preserving global transition probabilities but not individual-level heterogeneity. If topology is consistent with Markov-1, the observed structure requires at most one-step memory to generate.

**Null 5 — Markov order-2** (*n* = 500): Estimate a second-order Markov transition matrix (conditioning on the previous two states) and simulate surrogates. Tests whether topology exceeds two-step memory.

The test statistic for all comparisons is total persistence (sum of lifetimes of all features) in each homological dimension, separately for H₀ and H₁. The *p*-value is the proportion of null realisations with total persistence as extreme as or more extreme than the observed value.

This "Markov memory ladder" provides a principled decomposition: when observed topology first becomes consistent with a Markov-$k$ null, we can conclude that the trajectory space's topological complexity is captured by $k$-step transition dynamics. This result has direct policy implications: if Markov-1 suffices, single-transition interventions may reshape the regime landscape.

### 3.5 Regime Discovery

We identify mobility regimes by fitting Gaussian mixture models (GMMs) to the PCA-20D embedding, using the Bayesian Information Criterion (BIC) for model selection across $k = 3, 4, \ldots, 15$ components. The BIC-optimal model has $k = 7$ components, each characterised by a multivariate Gaussian distribution in the 20-dimensional embedding space.

Regime profiles are constructed by mapping GMM-assigned labels back to the original state sequences and computing, for each regime: employment rate, unemployment rate, inactivity rate, income distribution (fraction in low/mid/high), and a stability index (fraction of trajectory years spent in the dominant state). These profiles provide substantive interpretability for each topological cluster.

### 3.6 Overlapping Windows and Regime Persistence

To assess regime persistence over the life course, we construct overlapping career-phase windows using a sliding window of 10 years with a 5-year step. For each individual, this produces a sequence of overlapping windows, each embedded and assigned to a regime using the same PCA-GMM model fitted on full trajectories. This yields 54,560 windows from 27,280 individuals (mean 2.0 windows per person).

We construct a 7×7 regime transition matrix from consecutive windows and compute escape probabilities: the fraction of individuals starting in disadvantaged regimes (Low-Income Churn or Inactive Low) who reach an advantaged regime (Secure EH or Employed Mid) within a given number of windows.

We also compute PH on the phase-level embedding cloud and test a phase-order shuffle null that preserves each individual's multiset of windows but randomises their temporal order, testing whether the life-course ordering of career phases adds topological structure beyond the composition of phases.

---

## 4. Results

### 4.1 Descriptive Statistics

Our sample comprises 27,280 individuals with trajectories averaging 12.9 years (range 10–14, median 13). The nine-state distribution reflects a labour market with dominant employment: EH (high-income employment) is the most common dominant state (42.1% of individuals), followed by IL (inactive-low, 13.7%), EM (employed-mid, 12.5%), IM (inactive-mid, 12.1%), and IH (inactive-high, 12.0%). Unemployment is comparatively rare as a dominant state: UL (1.1%), UM (0.5%), and UH (0.4%). The low-income employment state EL dominates 5.7% of trajectories.

Birth cohorts span seven decades, from the 1930s (*n* = 1,642) through the 1990s (*n* = 1,364), with the largest cohorts in the 1960s (*n* = 5,579) and 1950s (*n* = 4,843). The gender split is 56% female, 44% male among those with non-missing sex. Forward-fill imputation affected 4.9% of person-years, distributed proportionally across regimes.

**[Figure 1]** presents trajectory heatmaps showing exemplar sequences from each of the seven regimes discovered in Section 4.4, illustrating the qualitative diversity of life-course patterns.

**[Table 1]** summarises sample characteristics by cohort decade, including mean trajectory length, dominant state distribution, and covariate availability.

### 4.2 Topological Structure of the Trajectory Space

Persistent homology on the PCA-20D embedding with 5,000 maxmin landmarks reveals substantial topological structure in both dimensions.

**H₀ (connected components):** 5,000 features (4,999 finite, 1 infinite — the final connected component), with total persistence 20,411.1 and maximum persistence 15.81. The dominance of a single long-lived component (persistence 15.81, compared to the mean of 4.08) indicates that most trajectory clusters ultimately merge at large filtration values but are well separated at smaller scales. The distribution of H₀ persistence values has a heavy right tail, consistent with multiple distinct clusters separated by varying distances.

**H₁ (loops):** 5,962 features (5,961 finite, 1 infinite), with total persistence 2,224.7 and maximum persistence 3.21. The large number of H₁ features indicates extensive looping structure in the trajectory space, but their relatively modest persistence (compared to H₀) suggests that loops are numerous but not deeply persistent.

**[Figure 3]** presents persistence diagrams for both H₀ and H₁. The H₀ diagram shows a clear separation between the most persistent features (top-right) and the mass of short-lived features near the diagonal, consistent with a small number of well-defined regimes embedded in noise. The H₁ diagram shows a more uniform spread, with no single loop dominating.

### 4.3 Null Model Validation: The Markov Memory Ladder

The five null models in the Markov memory ladder yield the following results for total persistence, summarised in Table 2:

**[Table 2: Markov Memory Ladder Results]**

| Null Model | *n* | H₀ observed | H₀ *p* | H₁ observed | H₁ *p* |
|---|---|---|---|---|---|
| Label shuffle | 100 | 14,227.8 | 0.69 | 1,520.3 | 0.63 |
| Cohort shuffle | 100 | 14,227.8 | 0.66 | 1,520.3 | 0.54 |
| Order shuffle | 500 | 14,227.8 | **<0.001** | 1,520.3 | 0.25 |
| Markov-1 | 500 | 14,227.8 | 0.148 | 1,520.3 | 0.652 |
| Markov-2 | 500 | 14,227.8 | 0.108 | 1,520.3 | 0.434 |

The memory ladder reveals a clear decomposition:

**Order matters for regimes (H₀).** The order-shuffle null, which preserves per-person state frequencies but destroys temporal order, yields *p* < 0.001 for H₀ total persistence. This means the observed cluster structure in the trajectory space cannot be explained by state composition alone — the temporal ordering of states within trajectories genuinely creates topological structure. This is the paper's primary positive result: regimes are not merely compositional artefacts but require temporal ordering to generate.

**Regimes are Markov-1 consistent.** The Markov-1 null yields *p* = 0.148 for H₀ — not significant at conventional levels. The Markov-2 null is also non-significant (*p* = 0.108). This means the observed regime topology is consistent with what a memoryless (one-step) Markov chain would produce given the observed transition probabilities. The topology requires ordering (order shuffle is significant) but does not require long-range memory (Markov-1 is sufficient).

**Cycles are not topologically distinctive (H₁).** All nulls produce H₁ *p*-values well above 0.05: order shuffle *p* = 0.25, Markov-1 *p* = 0.652, Markov-2 *p* = 0.434. This means the observed looping structure in the trajectory space is consistent with what state frequencies and one-step transitions would produce. Importantly, this does *not* mean that people don't cycle between states — it means the topological *shape* of that cycling is predictable from marginal frequencies and transition rates, rather than reflecting non-Markovian trapping dynamics.

**Trivial nulls are non-significant (as expected).** Label shuffle (*p* = 0.69) and cohort shuffle (*p* = 0.66) confirm that the topological signal is not driven by the specific identities of states or by cross-cohort heterogeneity per se.

**[Figure 4]** shows Betti curves — the number of topological features as a function of filtration radius — for the observed data compared to null envelopes (95% pointwise intervals) from order-shuffle and Markov-1 nulls. The observed H₀ curve lies outside the order-shuffle envelope at most scales but within the Markov-1 envelope.

**[Figure 8]** presents the null model summary as a structured visual comparison of *p*-values across the memory ladder.

**[Figure 9]** shows violin plots comparing the distribution of total persistence across Markov-1 and Markov-2 null realisations to the observed values, illustrating the ladder graphically.

### 4.4 Seven Mobility Regimes

BIC model selection identifies $k = 7$ as optimal. The seven regimes, ordered by size, are:

**Regime 1 — Secure High-Employment** (*n* = 7,358, 27.0%): Dominated by high-income employment (EH). Employment rate 92.3%, inactivity rate 7.4%, unemployment near zero (0.3%). High-income rate 85.5%. Stability index 0.779, the highest of all regimes. This is the core of the UK labour market: stably employed, well-paid individuals.

**Regime 2 — Inactive Low** (*n* = 5,415, 19.9%): Entirely inactive (inactivity rate 100%, zero employment or unemployment). Income is mixed (low 38.7%, mid 33.1%, high 28.2%), reflecting heterogeneity within inactivity (retirees with pensions versus carers and those with long-term illness). Stability 0.387. This regime is a key disadvantaged state in our analysis.

**Regime 0 — Mixed Churn** (*n* = 3,787, 13.9%): Mixed employment (41.6%), unemployment (20.3%), and inactivity (38.1%). Income concentrated in mid (34.1%) and high (42.2%). Low stability (0.234), the lowest of all regimes, indicating frequent state changes — the archetypal "churning" trajectory.

**Regime 4 — Employed Mid** (*n* = 3,510, 12.9%): Near-universal employment (98.5%) with mixed income (low 26.0%, mid 31.8%, high 42.2%). Stability 0.407. These are stably employed individuals at moderate income levels — a potential destination for upward mobility from disadvantaged regimes.

**Regime 3 — Employment-Inactive Mix** (*n* = 3,333, 12.2%): Mixed employment (58.8%) and inactivity (41.2%), zero unemployment. Income relatively balanced (low 20.0%, mid 39.6%, high 40.4%). Stability 0.280. These trajectories combine employment spells with periodic inactivity — potentially capturing career breaks, part-time work patterns, and caring responsibilities.

**Regime 6 — Low-Income Churn** (*n* = 2,064, 7.6%): Employment (59.1%), unemployment (9.8%), and inactivity (31.1%), with the highest low-income rate (61.1%) of any regime. Stability 0.289. This is the second key disadvantaged regime: individuals cycle between low-paid employment, unemployment, and inactivity. Combined with Regime 2 (Inactive Low), these two regimes comprise 27.5% of the sample and define the disadvantaged population for escape analysis.

**Regime 5 — High-Income Inactive** (*n* = 1,813, 6.6%): Mixed employment (41.3%) and inactivity (58.3%), with high income (67.2%). Stability 0.400. These are likely early retirees with substantial assets, or individuals in high-income households who are economically inactive by choice.

The correlation between regime stability (fraction of years in the dominant state) and high-income rate is strong ($r$ = 0.77, *p* < 0.01), confirming that the most stable trajectories tend to be the most advantaged — consistent with the "stickiness of privilege" documented in the UK social mobility literature (Goldthorpe 2016).

**[Figure 5]** presents the regime profile heatmap: a 7 × 8 matrix showing employment rate, unemployment rate, inactivity rate, low/mid/high income rates, stability index, and transition rate for each regime.

**[Figure 6]** shows the stability-income correlation scatter plot across regimes.

#### Regime Persistence Over the Life Course

To assess whether individuals remain trapped in their regimes or transition between them, we construct overlapping 10-year windows (5-year step) for all 27,280 individuals, yielding 54,560 career-phase windows. Each window is embedded and assigned to a regime using the same PCA-GMM model.

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

Among the 7,453 individuals whose first window falls in a disadvantaged regime (Inactive Low or Low-Income Churn), only 416 (5.6%) ever reach an advantaged regime (Secure EH or Employed Mid) in the subsequent window. All observed escapes occur in a single window-to-window transition — no multi-step "ladders" are observed in our data.

**[Figure 12]** presents the regime transition heatmap.

**[Figure 13]** shows escape probability from disadvantaged regimes.

### 4.5 Cycle and Trap Analysis

The 5,962 H₁ features indicate extensive looping structure in the trajectory space. However, as shown in Section 4.3, this cycling is not topologically distinctive: it is consistent with state frequencies (order-shuffle H₁ *p* = 0.25) and Markov transition dynamics (Markov-1 H₁ *p* = 0.652, Markov-2 H₁ *p* = 0.434).

This is an important negative result that we report honestly. The H₁ cycles should *not* be interpreted as "topological poverty traps" in a strong causal sense. Rather, the observed looping structure is a predictable consequence of state composition and one-step transition probabilities — the same frequencies and transitions that generate the data also generate comparable loops under simulation.

Nevertheless, the H₁ features provide descriptive value. The most persistent loops (maximum persistence 3.21) involve cycling between low-income employment, unemployment, and inactivity — states concentrated in the Low-Income Churn and Mixed Churn regimes. The characteristic loop scales (persistence values) quantify the "depth" of cycling: how far a trajectory must move in the embedding space to complete a cycle and return to a similar state. These descriptive features may prove useful for policy targeting even if they lack topological distinctiveness relative to Markov baselines.

**[Figure 7]** presents the cycle analysis: top persistent loops and their length distribution.

#### Phase-Ordering Null Test

We also asked whether the ordering of career *phases* — overlapping 10-year windows — adds additional topological structure beyond what the composition of individual trajectories provides. Using the PCA embedding of 50,000 overlapping windows (20,092 from individuals who visit disadvantaged regimes plus 29,908 sampled from others), we compute persistent homology with 3,000 maxmin landmarks.

The phase-level PH yields H₀ total persistence of 19,119.4 (3,000 landmarks, max persistence 18.38) and H₁ total persistence of 2,071.2 (3,482 features, max 3.19). A within-person phase-order shuffle null that preserves each individual's multiset of windows but randomises their temporal order produces *p*(H₀) = 0.95 and *p*(H₁) = 0.75 (*n* = 20 permutations). In contrast to the strongly significant trajectory-level order-shuffle result, phase ordering has no detectable effect on topology: the observed phase-space structure is entirely consistent with the composition of career phases, regardless of their life-course ordering.

This suggests that the main topological signal arises from the shape of full 10-year trajectories — their internal sequential structure — rather than from the higher-order sequencing of overlapping phases across the life course.

**[Figure 14]** presents phase PH persistence diagrams and phase-order null violin plots.

### 4.6 Stratified Comparisons

Pairwise Wasserstein distances between group-specific persistence diagrams reveal significant topological differences by social origin, gender, and birth cohort.

**Gender.** Male (*n* = 11,243) versus Female (*n* = 14,402): Wasserstein distance is significant for H₀ (*p* < 0.001, observed distance 33.7 vs. null mean 21.0), but not for H₁ (*p* = 0.27). This indicates that men and women occupy different cluster structures in the trajectory space — likely reflecting gendered patterns of employment, inactivity, and income — but that their cycling patterns are topologically similar. The regime *landscape* differs by gender, but the *traps* within it do not.

**Parental NS-SEC.** Three groups — Professional/Managerial (*n* = 2,067), Intermediate (*n* = 6,777), Routine/Manual (*n* = 7,779) — yield significant H₀ differences for all three pairwise comparisons (*p* < 0.001 in each case). H₁ differences are non-significant (all *p* > 0.35). The largest H₀ Wasserstein distance is between Professional/Managerial and Routine/Manual (114.8, vs. null mean 99.8), confirming that parental social class creates topologically distinct trajectory clusters. The sharper separation between extreme classes, with Intermediate occupying a genuinely intermediate topological position, aligns with the cumulative advantage hypothesis (DiPrete & Eirich 2006).

**Birth cohort.** Seven cohort decades yield 21 pairwise comparisons. Strikingly, 42 out of 168 dimension-specific tests (21 pairs × 4 dimensions × 2 homological dimensions) are significant at *p* < 0.05. Nearly all significant differences are in H₀ (cluster structure), with a few H₁ differences emerging for the most distant cohort pairs (e.g., 1930s vs. 1960s: H₁ *p* < 0.001). The 1930s cohort is topologically most distinctive, consistent with its passage through fundamentally different labour market conditions (post-war full employment through to early deindustrialisation).

**[Figure 10]** presents a Wasserstein distance heatmap by parental NS-SEC.

**[Figure 11]** shows gender-specific persistence landscape overlays.

---

## 5. Discussion

### 5.1 What TDA Adds Beyond Sequence Analysis

Our results demonstrate that persistent homology reveals structural features of the trajectory space that are invisible to conventional sequence analysis. Three contributions stand out.

First, regime discovery via GMM on topologically informed embeddings produces clusters with formal significance testing. The seven regimes we identify are not merely ad hoc typologies but are validated against a battery of null models: the order-shuffle test confirms that temporal ordering genuinely creates the observed clustering (H₀ *p* < 0.001), something that sequence analysis typologies cannot formally test. The *k* = 7 regime structure qualitatively resembles typologies found by sequence analysis in similar data (e.g., Bukodi & Goldthorpe 2019), but the topological validation provides a level of statistical rigour unavailable to conventional methods.

Second, PH provides a natural language for mobility barriers. The persistence of H₀ features quantifies the "height" of topological barriers between regimes: long-lived connected components correspond to deeply separated trajectory clusters. The near-absorbing nature of Regime 2 (Inactive Low, self-transition probability 0.97) is visible both in the transition matrix and in the topological separation of this regime from others. The barrier is not merely a high transition cost but a geometric feature of the trajectory space — a gap that is robust to the choice of distance metric.

Third, the Markov memory ladder provides a precise, testable decomposition of topological complexity. The statement "regime topology is consistent with first-order Markov dynamics" is a formal claim that can be replicated, extended, and compared across datasets. It goes beyond both the informal typologies of sequence analysis and the purely local transition probabilities of Markov models to characterise the global shape of the trajectory space in terms of the generating process's memory.

### 5.2 The Markov Memory Ladder

The Markov memory ladder is our primary methodological contribution. The result — that H₀ topology requires temporal ordering (order-shuffle *p* < 0.001) but is consistent with one-step memory (Markov-1 *p* = 0.148) — has a precise interpretation: the observed regime landscape can be generated by a process that remembers only the current state, not the full trajectory history. This does *not* mean "there is no interesting topology." The topology is real (it survives the order-shuffle test) and informative (it identifies seven regimes). It means that the topology is *efficiently generated* by one-step transitions — the simplest possible memory model that respects temporal ordering.

This has direct policy implications. If the regime landscape is well captured by first-order dynamics, then interventions targeting *single transitions* — employment entry programmes, in-work benefit tapers, retraining schemes — can, in principle, reshape the landscape. There is no evidence that complex, multi-step pathway interventions are needed to escape disadvantaged regimes; the topology does not encode multi-step traps that a single transition cannot bridge.

The overlapping-window analysis complements and reinforces this conclusion. When we embed 10-year career phases and test a phase-order shuffle null, we find no significant difference in either H₀ or H₁ persistence (*p*(H₀) = 0.95, *p*(H₁) = 0.75). Reordering an individual's career phases does not create or destroy detectable topological structure. Taken together with the Markov memory ladder, this implies that the regime landscape is well captured by first- or second-order transition dynamics within 10-year trajectories, while the sequencing of a small number of overlapping phases adds essentially no additional structure.

The Markov memory ladder is transportable: it can be applied to any TDA analysis of sequential data, from financial time series to genomic sequences, wherever the question "how much memory does the topology require?" is relevant. Future work could extend the ladder to include hidden Markov models (testing whether unobserved states add topological structure) or variable-order Markov models (testing heterogeneous memory across states).

### 5.3 An Honest Assessment of H₁

The H₁ results require frank discussion. Persistent loops in the trajectory space could, in principle, provide topological evidence of poverty traps — cyclical dynamics from which escape is topologically difficult. Our results are clear: H₁ is *not* significant against any null model. Order-shuffle (*p* = 0.25), Markov-1 (*p* = 0.652), and Markov-2 (*p* = 0.434) all fail to reject the null hypothesis that the observed cycling is consistent with state frequencies and transition structure.

This does not mean that people do not cycle between employment and poverty. They manifestly do — the Low-Income Churn and Mixed Churn regimes demonstrate extensive state cycling. Rather, the null result means that the *topological shape* of this cycling is predictable from the marginal state distribution and one-step transition probabilities. The cycling is "generic" — any trajectory cloud with the same composition and transitions would produce similar loops.

We view this as an important negative result that constrains interpretation rather than an analytical failure. It means that claims about "topological poverty traps" would be unsupported by these data: the loops exist, but they are not topologically distinctive. Future directions that might uncover conditional H₁ significance include bifiltration by income threshold (testing whether loops are significant above or below specific income levels), sub-population analysis restricted to the most disadvantaged regimes, or comparison across national panels with different welfare state structures.

The contrast with Markov chain mixing time analysis is instructive. Mixing time measures how quickly a Markov chain converges to its stationary distribution; persistent cycles measure the topological structure of the trajectory cloud. Our null result implies that the two perspectives converge: the cycling visible in the trajectory cloud is that predicted by the mixing properties of the empirical Markov chain.

### 5.4 Limitations

Several limitations warrant discussion.

**State space discretisation.** The nine-state space, while richer than most sequence analysis applications (which typically use 3–5 states), is necessarily a simplification. Within-state variation — for instance, the difference between borderline and deeply low-income — is lost. The 60% median threshold for income terciles is conventional but arbitrary; sensitivity to this threshold is not examined here.

**Embedding sensitivity.** PCA-20D is our primary embedding, but the UMAP-16D sensitivity check yields ARI = 0.31 against PCA regime assignments. While three macro-types (secure employment, inactivity, churning) are robust, finer regime boundaries are embedding-dependent. This cautions against over-interpreting differences between neighbouring regimes (e.g., between Mixed Churn and Low-Income Churn) and motivates future work with autoencoder or other nonlinear embeddings.

**Landmark sampling.** Maxmin landmark selection (5,000 from 27,280) preserves global geometry but may undersample rare trajectory types. Individuals in the smallest regime (High-Income Inactive, *n* = 1,813, 6.6%) may be underrepresented in the landmark subsample. Future work could use weighted or stratified landmark selection.

**Family dimension.** We analyse employment-income trajectories only; partnership and household composition are not included. A 27-state space incorporating partnership status (e.g., single, cohabiting, married) could reveal whether family transitions create additional topological structure. This is deferred to future work.

**Imputation.** Forward-fill imputation for gaps of up to two years affects 4.9% of person-years. While we verify that imputation rates are balanced across regimes, the assumption that states persist during gaps is strong, particularly for transitions between employment and inactivity.

**Cross-survey harmonisation.** BHPS and USoc use different sampling frames, questionnaire designs, and income measurement methodologies. While the BHPS sub-sample in USoc enables longitudinal tracking, harmonisation artefacts may contribute to cohort-specific topological differences. Our data are drawn primarily from the USoc period (start years 2009–2013), limiting historical reach.

**Window resolution and escape paths.** Our overlapping-window design reveals only very short escape paths from disadvantaged regimes. With 10-year windows stepped every five years, most individuals contribute at most two usable windows, and the 416 observed "escapers" from Low-Income Churn or Inactive Low to Employed Mid or Secure EH do so in a single window-to-window transition. This confirms that such escapes are rare (5.6%) and appear as one-step events in our data, but it also means we cannot distinguish between different multi-step topological escape routes. Longer panels or narrower windows would be needed to study escape dynamics in detail and to determine whether distinct escape archetypes exist.

---

## 6. Conclusion

This paper presents the first application of persistent homology to longitudinal life-course trajectories, analysing 27,280 employment-income sequences from the BHPS and Understanding Society (1991–2023) in a 20-dimensional PCA embedding space.

**Positive result.** We discover seven distinct mobility regimes with statistically strong, order-dependent clustering: the order-shuffle null is rejected at *p* < 0.001 for H₀ total persistence, confirming that temporal ordering of states within trajectories creates genuine topological structure that exceeds what state composition alone would produce. The seven regimes range from Secure High-Employment (27%, stability 0.78) to Low-Income Churn (7.6%, stability 0.29), with a strong correlation between regime stability and income (*r* = 0.77).

**Complexity bound.** The Markov memory ladder demonstrates that regime topology requires at most first-order memory to generate: Markov-1 H₀ *p* = 0.148, Markov-2 *p* = 0.108. The topology is real but efficiently described by one-step transitions. This is reinforced by the phase-order null test, which finds no additional topological signal from the temporal ordering of overlapping career phases (*p*(H₀) = 0.95, *p*(H₁) = 0.75).

**Negative result.** H₁ cycles — potential topological signatures of churning traps — are consistent with state frequencies and Markov transition structure across all null models (*p* > 0.25). This important negative result means that the observed cycling, while real and descriptively informative, is not topologically distinctive and should not be over-interpreted as evidence of non-Markovian poverty traps.

**Stratification.** Wasserstein distances reveal origin-dependent topology: gender differences are significant for H₀ (2/8 tests, *p* < 0.001 for cluster structure) but not H₁; parental NS-SEC differences are significant for all three class pairings in H₀ (6/24); and birth cohort produces the most extensive differentiation (42/168 tests significant), concentrated in H₀.

**Regime stickiness.** Overlapping career-phase windows confirm extreme regime persistence: the 7 × 7 transition matrix is diagonal-dominant, and only 5.6% of individuals starting in disadvantaged regimes (Inactive Low or Low-Income Churn) escape to advantaged regimes within a single window transition.

**Policy implications.** The Markov-1 consistency of regime topology implies that interventions targeting single transitions — employment entry, in-work progression, income stabilisation — are potentially sufficient to reshape the regime landscape. The 5.6% escape rate from disadvantaged regimes quantifies the scale of the challenge: current transition probabilities produce escape rates far below what would be needed for meaningful mobility. The near-absorbing nature of Inactive Low (97% self-transition) identifies this regime as the primary policy target.

**Future work.** Extensions include: (i) a 27-state space incorporating family formation; (ii) autoencoder embeddings for richer trajectory representations; (iii) multi-parameter persistent homology using employment and income as separate filtration parameters; (iv) comparative analysis across SOEP (Germany), PSID (US), and other longitudinal panels; and (v) calibration of agent-based models from topological targets, using the persistence diagram as a moment condition for simulation-based estimation.

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

## Tables

| # | Title | Section |
|---|-------|---------|
| 1 | Sample Characteristics by Cohort Decade | §4.1 |
| 2 | Markov Memory Ladder: Null Model Results | §4.3 |
| 3 | Regime Composition and Characteristics | §4.4 |
| 4 | Pairwise Wasserstein Distances by Social Origin | §4.6 |

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

Jenkins, S.P. (2011). *Changing Fortunes: Income Mobility and Poverty Dynamics in Britain*. Oxford University Press.

Lesnard, L. (2010). Setting cost in optimal matching to uncover contemporaneous socio-temporal patterns. *Sociological Methods & Research*, 38(3), 389–419.

McInnes, L., Healy, J. & Melville, J. (2018). UMAP: Uniform manifold approximation and projection for dimension reduction. *arXiv preprint*, arXiv:1802.03426.

Rizvi, A.H., Camara, P.G., Kandror, E.K. et al. (2017). Single-cell topological RNA-seq analysis reveals insights into cellular differentiation and development. *Nature Biotechnology*, 35(6), 551–560.

Robette, N. & Thibault, N. (2008). Comparing qualitative harmonic analysis and optimal matching: An exploratory study of occupational trajectories. *Population-E*, 63(4), 621–646.

Robinson, A. & Turner, K. (2017). Hypothesis testing for topological data analysis. *Journal of Applied and Computational Topology*, 1, 241–261.

Saggar, M., Sporns, O., Gonzalez-Castillo, J. et al. (2018). Towards a new approach to reveal dynamical organization of the brain using topological data analysis. *Nature Communications*, 9, 1399.

Savage, M., Devine, F., Cunningham, N. et al. (2013). A new model of social class? Findings from the BBC's Great British Class Survey experiment. *Sociology*, 47(2), 219–250.

Singer, B. & Spilerman, S. (1976). The representation of social processes by Markov models. *American Journal of Sociology*, 82(1), 1–54.

Stolz, B.J., Harrington, H.A. & Porter, M.A. (2017). Persistent homology of time-dependent functional networks constructed from coupled time series. *Chaos*, 27(4), 047410.

Studer, M. & Ritschard, G. (2016). What matters in differences between life trajectories: A comparative review of sequence dissimilarity measures. *Journal of the Royal Statistical Society: Series A*, 179(2), 481–511.

Tong, H. (1990). *Non-linear Time Series: A Dynamical System Approach*. Oxford University Press.

Turner, K., Mileyko, Y., Mukherjee, S. & Harer, J. (2014). Fréchet means for distributions of persistence diagrams. *Discrete & Computational Geometry*, 52(1), 44–70.

Vandecasteele, L. (2010). Poverty trajectories, triggering events and exit routes. *Sociological Research Online*, 15(4), 1–17.

Zomorodian, A. & Carlsson, G. (2005). Computing persistent homology. *Discrete & Computational Geometry*, 33(2), 249–274.
