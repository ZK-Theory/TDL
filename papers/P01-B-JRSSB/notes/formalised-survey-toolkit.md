# Formalised Survey Toolkit for P01-B

Source: `papers/P03-Zigzag/drafts/v2-2026-03.md` §3.6–3.7 and
`papers/P03-Zigzag/_project.md` "Current Results Summary".

These two sections are written as self-contained, mathematically rigorous
prose ready to slot into §3.4 of the P01-B draft. They formalise the two
diagnostic tools developed and validated in the P03 programme. Both are
technique-agnostic: they apply to any topological analysis of repeated
cross-section or rotating panel data, not only to zigzag persistence.

---

## §A: Pool-Draw Null Model

### A.1 Formal Setup

Let $\mathcal{Y} = \{1, \ldots, T\}$ index the observation periods (e.g., survey years). For each $t \in \mathcal{Y}$, let $S_t$ denote the set of individuals observed in period $t$, with $|S_t| = n_t$. Let $\mathcal{S} = \bigcup_{t=1}^{T} S_t$ denote the pool of all observed individual-period records. Each record is represented by its embedded position $v_i \in \mathbb{R}^d$ in a common metric space, where the embedding is computed with frozen loadings (i.e., using projection coordinates fitted to the full pooled sample, not re-fitted within each period).

Let $\psi: \mathcal{Y} \to \mathbb{R}$ denote some topological summary computed from the sequence $(S_1, \ldots, S_T)$ — for example, a block ratio of Wasserstein distances, a Mantel correlation, or a Betti curve comparison statistic. Define the observed statistic $\psi_{\mathrm{obs}} = \psi(S_1, \ldots, S_T)$.

### A.2 Null Hypothesis

The pool-draw null model tests:

$$H_0: \text{the temporal labelling of annual cohorts has no effect on the topological summary } \psi.$$

Equivalently, under $H_0$, any partition of $\mathcal{S}$ into $T$ subsets of sizes $(n_1, \ldots, n_T)$ is equally likely to have produced the observed data. The null asserts that the assignment of individual-period records to years is exchangeable: the topological differences between periods are no greater than what would arise from random partition of the full pool.

This is a composite null. It does not assert that all periods have the same marginal distribution of individual characteristics; it asserts that any structure in the topological summary attributable to which individuals appear in which year is due to chance partitioning of the pool, not to period-specific data-generating processes.

### A.3 Permutation Procedure

The pool-draw test is a non-parametric permutation test on the temporal labelling. The procedure is:

1. **Pool.** Form the unified set $\mathcal{S} = \bigcup_{t=1}^{T} S_t$ by collecting all individual-year embedded records, retaining their embeddings $v_i$ but discarding the year label.

2. **Partition.** Draw $T$ disjoint random subsets $\tilde{S}_1, \ldots, \tilde{S}_T$ from $\mathcal{S}$ without replacement, where $|\tilde{S}_t| = n_t$ for all $t$ (matching the observed cohort sizes exactly). This preserves the sample-size structure of the original time series.

3. **Compute.** Evaluate the topological summary $\psi(\tilde{S}_1, \ldots, \tilde{S}_T)$ on the permuted sequence. In practice this means: re-compute VR persistence diagrams on each permuted annual cohort using maxmin landmark selection; compute pairwise Wasserstein distances $W_2(D_q(\tilde{S}_t), D_q(\tilde{S}_{t'}))$ for all pairs; then compute the block ratio or other summary statistic on the resulting distance matrix.

4. **Repeat.** Repeat steps 2–3 for $B$ independent draws (in our application, $B = 50$ for full pool-draw runs; $B = 1000$ for label-permutation on the stored distance matrix). Collect the null distribution $\{\psi_b\}_{b=1}^{B}$.

5. **Test.** The permutation $p$-value is
   $$p = \frac{1 + \#\{b : \psi_b \geq \psi_{\mathrm{obs}}\}}{B + 1}.$$

### A.4 Test Statistic

We focus on the **block ratio statistic** as the primary summary for the pool-draw test. Given a partition of $\mathcal{Y}$ into two eras $\mathcal{E}_1$ and $\mathcal{E}_2$ (e.g., BHPS 1991–2008 and USoc 2009–2022), define:

$$\mathrm{BR} = \frac{\overline{W}_{\times}}{\overline{W}_{\mathrm{within}}},$$

where $\overline{W}_{\times} = \frac{1}{|\mathcal{E}_1||\mathcal{E}_2|}\sum_{t \in \mathcal{E}_1, t' \in \mathcal{E}_2} W_2(D_q(S_t), D_q(S_{t'}))$ is the mean cross-era Wasserstein distance and $\overline{W}_{\mathrm{within}} = \frac{1}{2}\bigl(\overline{W}_{\mathcal{E}_1} + \overline{W}_{\mathcal{E}_2}\bigr)$ is the mean within-era distance.

Under $H_0$, the expected block ratio is approximately 1 (cross-era and within-era distances are drawn from the same distribution). The observed statistic $\mathrm{BR} = 1.581$ in the UK application greatly exceeds the null mean $1.007 \pm 0.095$ ($p < 0.001$, $B = 50$).

The Mantel correlation $r(\mathbf{W}, \mathbf{T})$ — the Pearson correlation between the $T \times T$ Wasserstein distance matrix $\mathbf{W}$ and the temporal distance matrix $T_{tt'} = |t - t'|$ — is a complementary statistic that tests for monotone temporal structure in topology, rather than block structure. Under the label-permutation version of the pool-draw test ($B = 1000$), the full-panel Mantel $r = 0.768$ is rejected with $p < 0.001$.

### A.5 Connection to Bootstrap and Permutation Inference Literature

The pool-draw test is a permutation test on the temporal labelling of observations, in the tradition of Mantel (1967) and the general framework of permutation inference for exchangeable data (Good 2005). It is non-parametric: it makes no distributional assumptions on the embeddings, the persistence diagrams, or the Wasserstein distances. The null distribution is constructed entirely from the observed data.

Under $H_0$, each permutation is equally likely, so the test is exact for finite $B$ in the sense that the Type I error rate does not exceed $\alpha$ for any data distribution. The test is consistent against alternatives where the data-generating process assigns individuals to periods non-exchangeably (e.g., when period membership is determined by systematic selection into survey frames).

The pool-draw test is distinct from the label-permutation test on the stored distance matrix (Part A of the null model battery in §4.4.3 of the P03 draft). Label permutation shuffles year labels on the pre-computed $W_2$ matrix, testing whether the block structure is consistent with random label assignment. Pool-draw goes one step further: it re-draws the period populations from the full pool and recomputes the persistence diagrams from scratch, testing whether fresh population samples drawn without year-specific selection would reproduce the block structure. Pool-draw is the more conservative and computationally intensive test; both converge on the same conclusion here ($p < 0.001$).

### A.6 What the Test Can and Cannot Establish

The pool-draw null, when rejected, establishes that the block structure in the Wasserstein distance matrix is not an artefact of random partitioning of the pooled population. It confirms that the population composition in each period is period-specific, not merely a random draw from a common pool.

The test does not distinguish between substantive (economic) and artefactual (survey-design) sources of period-specificity. Both the GFC of 2008 and the BHPS-to-USoc sampling frame expansion would cause period-specific population composition and hence reject the pool-draw null. Rejection of the pool-draw null is therefore a necessary but not sufficient condition for concluding that topological change is substantive. The spanning-individual decomposition (§B below) is required to adjudicate between these sources.

---

## §B: Spanning-Individual Decomposition

### B.1 Motivation

The pool-draw null establishes that topological differences between periods reflect period-specific population composition. The spanning-individual decomposition identifies whether those differences arise from individuals who are consistently present across periods (and thus exposed to the same labour market conditions in both survey eras) or from individuals who enter the sample exclusively in one era (and thus may reflect survey-frame differences rather than economic change).

### B.2 Definitions

Let $\mathcal{T}_{\mathrm{BHPS}} = [1991, 2008]$ and $\mathcal{T}_{\mathrm{USoc}} = [2009, 2022]$ denote the two survey eras (or more generally, any two contiguous periods of interest). Define:

- **Spanning individuals** $\mathcal{I}^* = \{i : \exists\, t_1 \in \mathcal{T}_{\mathrm{BHPS}},\, t_2 \in \mathcal{T}_{\mathrm{USoc}} \text{ such that } i \in S_{t_1} \cap S_{t_2}\}$: individuals observed in at least one period from each era. In the UK application, $|\mathcal{I}^*| = 8{,}459$.

- **Era-1-only individuals** $\mathcal{I}_1 = \{i : i \in \bigcup_{t \in \mathcal{T}_{\mathrm{BHPS}}} S_t \text{ and } i \notin \bigcup_{t \in \mathcal{T}_{\mathrm{USoc}}} S_t\}$: individuals observed only in the first era.

- **Era-2-only individuals** (newcomers) $\mathcal{I}_2 = \{i : i \in \bigcup_{t \in \mathcal{T}_{\mathrm{USoc}}} S_t \text{ and } i \notin \bigcup_{t \in \mathcal{T}_{\mathrm{BHPS}}} S_t\}$: individuals observed only in the second era. In the UK application, $|\mathcal{I}_2| = 21{,}551$.

These three sets partition the individual-level population: $\mathcal{I}^* \cup \mathcal{I}_1 \cup \mathcal{I}_2 = \mathcal{I}$, with pairwise disjoint intersection.

### B.3 Formal Decomposition of the Embedding

For a year $t \in \mathcal{T}_{\mathrm{USoc}}$, the observed point cloud $S_t \subset \mathbb{R}^d$ decomposes as:

$$S_t = S_t^* \cup S_t^{\mathrm{new}},$$

where $S_t^* = \{v_i : i \in S_t \cap \mathcal{I}^*\}$ is the spanning sub-cloud (individuals from $\mathcal{I}^*$ active in year $t$) and $S_t^{\mathrm{new}} = \{v_i : i \in S_t \cap \mathcal{I}_2\}$ is the newcomer sub-cloud. The corresponding persistence diagrams satisfy, by the stability theorem for Hausdorff perturbations (Cohen-Steiner, Edelsbrunner, and Harer 2007):

$$W_2(D_q(S_t), D_q(S_t^*)) \leq C \cdot d_H(S_t, S_t^*)$$

for some constant $C$ depending on the filtration. A large Hausdorff gap between the spanning and combined point clouds — driven by newcomers occupying positions in $\mathbb{R}^d$ far from the BHPS-era manifold — implies that the persistence diagrams of the combined and spanning-only sub-clouds will differ substantially. Conversely, if newcomers are distributed similarly to spanners, the diagrams will be close.

In the UK application, $d_H(S_t, S_t^*)$ is directly proxied by the fraction of newcomers falling outside the BHPS-era manifold: 11.9% of USoc newcomers fall outside the BHPS-era convex hull (Mann-Whitney $p < 10^{-6}$ for PCs 1–4), compared to 4.6% for spanning individuals (consistent with the 5% baseline rate from the reference distribution). The Hausdorff term is therefore large for the newcomer sub-cloud.

### B.4 Identification Condition and Causal Interpretation

**Claim.** If the post-era-1 topological change is driven by a genuine change in the data-generating process (e.g., economic restructuring following the GFC), then spanning individuals should exhibit the same post-era-1 topological complexity as newcomers, because they face the same post-era-1 labour market. If instead the change is driven by survey-frame expansion (USoc sampling a broader population that BHPS did not reach), spanning individuals should maintain era-1-like topology in the post-era-1 period, while newcomers occupy embedding regions not previously populated.

Formally, let $\beta_q(\varepsilon; S_t^*)$ and $\beta_q(\varepsilon; S_t^{\mathrm{new}})$ denote the Betti-$q$ functions of the spanning and newcomer sub-clouds at filtration scale $\varepsilon$, and let $\beta_q^{\mathrm{ref}}(\varepsilon)$ denote the corresponding reference Betti function computed on the era-1 population. The identification condition is:

$$H_0^{\mathrm{struct}}: \mathbb{E}[\beta_q(\varepsilon; S_t^*)] \approx \beta_q^{\mathrm{ref}}(\varepsilon) \quad \forall\, t \in \mathcal{T}_{\mathrm{USoc}}, \; \varepsilon \in [\varepsilon_{\min}, \varepsilon_{\max}].$$

Rejection of $H_0^{\mathrm{struct}}$ for spanning individuals would indicate that spanning individuals show elevated post-era-1 topological complexity independent of frame expansion — attributing the change to the economic shock rather than the survey transition. Failure to reject $H_0^{\mathrm{struct}}$ for spanning individuals, combined with elevated complexity in the newcomer sub-cloud, implicates survey-frame expansion as the dominant source of cross-era topological change.

### B.5 Formal Test

Compare the Betti-$q$ curve at a fixed canonical scale $\varepsilon^*$ (chosen at the knee of the per-year Betti descent curve, $\varepsilon^* = 0.70$ in the UK application) across three populations in the post-era-1 period $[t_1^{\mathrm{USoc}}, t_2^{\mathrm{USoc}}]$:

| Population | Betti-0 $\beta_0(\varepsilon^*;\cdot)$ 2009–2015 | vs era-1 reference |
|---|---:|---|
| Spanning only ($\mathcal{I}^*$) | $\approx 5.7$ | consistent ($p > 0.05$) |
| USoc newcomers ($\mathcal{I}_2$) | $\approx 9.5$ | elevated ($p < 10^{-6}$) |
| Combined | $\approx 8.1$ | intermediate |
| Era-1 reference ($\beta_0^{\mathrm{ref}}$) | $\approx 6.0$ | — |

The Mann-Whitney test for the newcomer versus spanning Betti comparison, summarised as a block ratio on sub-sampled Betti curves, yields $p < 10^{-6}$. The embedding shift for newcomers (11.9% falling outside the BHPS-era manifold versus 4.6% for spanners) constitutes a directly interpretable geometric measure of the frame expansion.

The block ratio statistic for the spanning-only versus newcomer comparison mirrors the block ratio used in the pool-draw test (§A.4), providing a unified test quantity across both diagnostics.

### B.6 Technique-Agnostic Nature of the Decomposition

The spanning-individual decomposition is technique-agnostic. It does not depend on zigzag persistence, Wasserstein distances, or any particular topological method. It requires only:

1. A common metric space in which individuals are embedded across all periods (here, the PCA-20D embedding with frozen loadings).
2. The ability to separate individual records by era-membership category ($\mathcal{I}^*$, $\mathcal{I}_1$, $\mathcal{I}_2$).
3. Any topological or distributional summary computed separately on the spanning and newcomer sub-clouds.

The decomposition therefore applies equally to:

- **Zigzag persistence** on annual cohort sub-clouds (the P03 application).
- **Standard VR persistent homology** on era-specific samples (as used here for Betti curve comparisons).
- **Wasserstein distance matrices** between annual diagrams (§A of the pool-draw test).
- **Kernel two-sample tests** (e.g., MMD) that compare empirical distributions.
- **Distributional balance tests** on marginal characteristics.

In all cases, the diagnostic logic is the same: spanning individuals provide an internal control group exposed to both survey designs, and their topology is the counterfactual against which newcomers' topology is compared.

For any longitudinal study that links two surveys with different sampling frames, questionnaire designs, or recruitment strategies, the spanning-individual decomposition provides a principled approach to separating design-driven distributional change from substantive change. The broader methodological lesson is that changes in the population of observed individuals — whether from panel attrition, refreshment samples, or survey redesigns — create confounds for any distributional comparison, and the spanning-individual decomposition makes these confounds visible and testable.

### B.7 Relation to Internal Validity in Panel Data

The spanning-individual decomposition is structurally related to difference-in-differences identification in panel econometrics (Angrist and Pischke 2009): spanning individuals serve as the "treated" group that bridges both periods (analogous to the control group observed in both pre- and post-treatment periods), while newcomers are the era-2-only "fresh entrants" (analogous to units that cannot provide a pre-treatment comparison). The parallel-trends analogue here is the assumption that, in the absence of survey-frame expansion, spanning individuals' post-era-1 topology would equal the era-1 baseline — an assumption supported empirically by the near-zero fraction of spanning individuals outside the BHPS manifold ($4.6\%$ vs $5\%$ baseline).

Unlike difference-in-differences, however, the spanning-individual decomposition does not require a clean quasi-experimental event. It is a diagnostic tool that quantifies the *fraction* of cross-era topological change attributable to population composition versus economic change, rather than providing a point estimate of a treatment effect. The decomposition can identify when survey confounds are large (as here) or negligible (which would be indicated by newcomers and spanning individuals showing similar post-era topology).

---

*Prepared 2026-04-30. Source computation: `results/trajectory_tda_zigzag/gfc_deepdive/`. For provenance of W2 results, see `papers/P01-B-JRSSB/notes/2026-04-07-post-audit-w2-repo-note.md`.*
