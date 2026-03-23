This is a rich, well-grounded research programme. The paper has established a genuine methodological base — the Markov memory ladder, the over-constraint finding, and the cross-era replication — that can support a coherent sequence of increasingly ambitious projects over a PhD/postdoc-scale horizon. What follows is a stage-by-stage progression from the current state to the geometric and topological deep learning endpoints, with publication targets and computational guidance at each step.

***

## Strategic Overview

The programme has a natural three-stage architecture. The first stage consolidates and extends the current paper's TDA infrastructure (months 0–12), producing 2–3 publishable outputs without requiring new data or new computational methods. The second stage (months 12–24) opens the spatial and comparative dimensions: multi-parameter persistence, cross-national topology, and intergenerational structure. The third stage (months 24–48) moves to geometric and topological deep learning, where the TDA results become *training signal* rather than *analytic endpoint*. The trajectory runs from pure methodology toward policy-relevant prediction tools — which is the correct direction for a programme that has already done the hard work of establishing the geometry of the space.

The single most important action before anything else is to close the most significant open validity issue.

***

## Stage 0: Consolidate and Submit Paper 1 (Months 0–3)

**What to do first:** Upgrade the test statistic from total persistence to diagram-level comparisons. The review identifies this correctly — total persistence is a scalar that can mask substantive differences in the shape of persistence diagrams. The fix is well-scoped: compute the Wasserstein distance between the observed persistence diagram and each null diagram, rather than comparing scalar totals. The `hera` C++ library (with Python bindings via `gudhi`) computes exact Wasserstein and bottleneck distances in seconds for diagrams of the size produced by 5,000-landmark Ripser runs. This does not require any new data processing — it replaces the final test statistic only, leaving the entire pipeline unchanged. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_e5b4e1ce-663f-44e2-8c54-bb89cee3cf96/0a200064-0519-4f33-92fb-0349dc09d29e/A-roadmap-for-the-computation_of-persistent-homology.pdf)

The paired upgrade to **stratified Wasserstein testing** (§4.6) is similar: replace the current bootstrap-p approach with exact Wasserstein distances between subgroup persistence diagrams, using the permutation framework from Robinson-Turner (already cited). This turns the exploratory §4.6 into a rigorous comparative test and directly addresses the underpowered-test critique while adding minimal code.

**Computational requirements:** Both changes are CPU-only and complete in minutes on the current i7/32GB setup. No GPU, no cloud.

**Output: Paper 1.** Submit to *Sociological Methodology* (primary target). The cross-era replication and the diagram-level null tests together give this paper a strong methodological identity that distinguishes it from existing TDA applications, which rarely have out-of-sample validation.

***

## Stage 1: Near Extensions — Mapper and Zigzag Persistence (Months 3–12)

These two projects are independent and can be pursued in parallel. Both use the existing n-gram PCA embedding and the BHPS/USoc data.

### Paper 2: Mapper for Interior Trajectory Structure

**The step:** Where VR persistent homology tells you about global connectivity, Mapper (Singh, Mémoli, & Carlsson, 2007) produces a simplicial graph summarising the *interior density structure* — precisely the region the paper acknowledges it does not fully exploit. Applied to the existing PCA-20D embedding, Mapper would yield a navigable "map" of trajectory space where each node represents a group of similar trajectories and edges represent geometric overlap.

**The methodological contribution:** Colouring Mapper nodes by substantive outcome variables — escape probability from disadvantaged regimes, income at endpoint, NS-SEC of origin — creates a *causal geography* of the trajectory space. You can read directly off the Mapper graph which regions of trajectory space are associated with which outcomes. This addresses the critique that the paper "asserts connections [between manifold structure and intervention design] but does not establish them." The Mapper graph establishes them visually and statistically.

**How to build it from the current base:** The embedding already exists (PCA-20D, 27,280 points). The KeplerMapper Python library (`kmapper`) applies directly to this point cloud with a cover defined by a projection function (e.g., PCA components 1 and 2, or an income-density kernel) and DBSCAN or single-linkage clustering within each cover element. The result requires parameter tuning (overlap fraction, clustering resolution) — this is standard practice and well-documented in the KeplerMapper documentation. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_e5b4e1ce-663f-44e2-8c54-bb89cee3cf96/41914ee3-c9c8-454c-846b-65370dd1dcc4/A_Review_of_Topological_Data_Analysis_for_Cybersec.pdf)

**Computational requirements:** KeplerMapper on 27,280 points takes seconds to low minutes on a standard CPU. The main cost is parameter search, not computation. Fully tractable on the current setup.

**Key publication contribution:** The paper should demonstrate that Mapper nodes coloured by escape probability reproduce the regime structure (validating that the new graph is not an artifact) while revealing *within-regime heterogeneity* — sub-regions of the "Low-Income Churn" node with higher versus lower escape likelihood — that the 7-GMM typology compresses away. This sub-regime structure is the genuinely new finding.

**Output: Paper 2.** Target *Sociological Methods & Research* or *Journal of the Royal Statistical Society Series A (Statistics in Society)*. The framing: "From Global Topology to Navigable Trajectory Space: Mapper Analysis of UK Employment Trajectories."

### Paper 3: Zigzag Persistence for Business Cycle Topology

**The step:** Standard PH is computed on a static point cloud. Zigzag persistence (Carlsson & de Silva, 2010) tracks which topological features persist across a *sequence* of point clouds — specifically, when features appear and disappear as the data is partitioned by calendar year. Applied to the BHPS/USoc combined panel (1991–2023), this produces a topological time series that tracks how the UK trajectory space evolves across economic cycles. [youtube](https://www.youtube.com/watch?v=3g_dffm0U5o)

**The specific question:** Does the number of distinct trajectory clusters (H₀ persistence) increase during recessions, indicating fragmentation? Do loops (H₁) appear during recovery periods? The 1991–2023 window captures the 1993 UK recession, the post-1997 expansion, the 2008 financial crisis, the post-2010 austerity contraction, and the post-2020 pandemic period — a rich enough sequence to identify topological signatures of at least three regime transitions.

**How to build it from the current base:** Partition the combined panel into annual cohort snapshots (persons whose trajectories include each calendar year). Embed each annual snapshot using the *frozen* PCA loadings from the full-sample embedding (critical: the same coordinate system must be used across all years). Compute VR PH on each annual snapshot with a consistent landmark count. Feed the sequence of annual persistence diagrams into Gudhi's zigzag implementation. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_e5b4e1ce-663f-44e2-8c54-bb89cee3cf96/0a200064-0519-4f33-92fb-0349dc09d29e/A-roadmap-for-the-computation_of-persistent-homology.pdf)

**Computational requirements:** Zigzag is computationally more expensive than standard PH because towers of complexes must be tracked rather than single filtrations. The key constraint is RAM: annual snapshots of ~1,000–5,000 individuals with 500–2,000 landmarks each should fit comfortably in 32GB. Expect hours of compute, not minutes. Use the streaming algorithm of Kerber & Schreiber (2017), already in your reference library, which achieves space complexity independent of tower length. No GPU needed; no cloud needed. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_e5b4e1ce-663f-44e2-8c54-bb89cee3cf96/15e39063-2d49-47de-83a4-d3baf4bd1ed8/Barcodes-of-Towers-and-a-Streaming-Algorithm-for-Persistent-Homology.pdf)

**Output: Paper 3.** Target *Sociological Methods & Research* or *Journal of Computational Social Science*. The framing: "Topological Business Cycles: Zigzag Persistence and Labour Market Fragmentation in the UK, 1991–2023."

***

## Stage 2: Medium Extensions (Months 12–24)

These three projects open the substantive rather than purely methodological dimensions of the programme. Each requires either new data access or a significant methodological investment, but none requires the deep learning infrastructure of Stage 3.

### Paper 4: Multi-Parameter Persistent Homology for Poverty Trap Detection

**The step:** Single-parameter PH filters by distance only. Bi-filtration allows two simultaneous parameters — here, pairwise distance *and* an income-level threshold — enabling persistence that is geometrically significant *within* a specific income stratum rather than globally. This directly tests whether near-absorbing states cluster distinctively at the low-income threshold in a way that global PH cannot detect.

**How to build it:** The `multipers` library  is a scikit-style PyTorch-autodiff package that integrates with Gudhi and supports signed barcode decompositions (NeurIPS 2023) — the state of the art for making multi-parameter persistence computationally tractable. The bifiltration is defined on the existing n-gram PCA embedding with a second filtration parameter derived from mean trajectory income (a per-person scalar already available from the data). [github](https://github.com/DavidLapous/multipers)

**Computational requirements:** This is the first computationally non-trivial step in the programme. Multi-parameter persistence does not admit a complete decomposition analogous to the 1D barcode, so approximation methods (Hilbert functions, rank invariants, Euler surfaces) are used instead. Memory is the key constraint — 32GB RAM is sufficient for moderate problem sizes (2,000–5,000 landmarks × bifiltration), but full-scale experiments with 8,000+ landmarks and fine-grained income discretisation may push into cloud territory. The RTX 3080 (10GB VRAM) can accelerate the PyTorch autodiff components of `multipers`. **Recommended cloud targeting:** A single A100 40GB session on Colab Pro+ or AWS SageMaker (~4–8 GPU-hours) for the full-scale bifiltration experiments, with preliminary development done locally at reduced scale. Prepare the full data pipeline locally first; use cloud only for the final high-resolution computation. [theoj](https://www.theoj.org/joss-papers/joss.06773/10.21105.joss.06773.pdf)

**Output: Paper 4.** Target *JASA Applications and Case Studies* or *Annals of Applied Statistics*. The framing connects directly to the poverty trap literature — "does topological persistence in low-income regions of trajectory space exceed what global topology would predict?"

### Paper 5: Cross-National Welfare State Topology

**The step:** The Markov memory ladder's portability is the paper's most reusable methodological innovation. Applying the identical pipeline to SOEP (Germany), PSID (USA), and CNEF-linked panels (France, Canada, Switzerland, Australia) tests the hypothesis that liberal welfare states produce higher topological complexity while social democratic states produce more constrained topology — connecting directly to Esping-Andersen.

**Data access:** SOEP requires a use agreement with DIW Berlin (typically 2–4 weeks). PSID is publicly downloadable. CNEF requires data preparation via Cornell PAC. These access steps should begin at month 12, since they have administrative lead times. Income harmonisation using CNEF standards already provides equivalent definitions.

**How to build it:** The pipeline is identical to the current paper: n-gram PCA embedding (using country-specific PCA or frozen UK PCA for strict comparability — a methodological choice to justify), VR PH, and the Markov memory ladder. The cross-national comparison is of the z-scores from the Markov-1 test — how far below (or above) the Markov null each country's trajectory space sits.

**Computational requirements:** Equivalent to the current paper for each country. Fully tractable on the current setup.

**Output: Paper 5.** This is the highest-impact empirical paper in the programme. Target *American Journal of Sociology* or *European Sociological Review*. The UK z ≈ −3.7 finding gains interpretive power in comparative context.

### Paper 6: Intergenerational Topological Inheritance

**The step:** USoc and BHPS contain household identifiers that enable parent-child linkage. Both parent and child trajectories can be represented as points in the same embedding space, enabling Wasserstein distance between parent-regime-conditional child persistence diagrams as a topological measure of intergenerational mobility.

**How to build it:** The BHPS-USoc spanning trajectories (8,459 individuals tracked across both surveys) enable ~20-year parent trajectories. Cross-referencing with household membership files to identify co-resident children (who also have USoc trajectories) yields the parent-child pairs. The question is whether the topological relationship between parent and child trajectory clouds exceeds what parental NS-SEC alone would predict — a topological mobility measure unavailable from income correlation or rank statistics.

**Computational requirements:** Sample size for parent-child pairs will be smaller (likely 2,000–5,000 linked pairs), making this computationally lighter than the main analysis.

**Output: Paper 6.** Target *British Journal of Sociology* or *Sociology*. This paper delivers on the intergenerational mobility motivation in §1.1 that the current paper explicitly defers.

***

## Stage 3: Geometric and Topological Deep Learning (Months 24–48)

This stage moves from using topology as an *analytical lens* to using it as an *architectural constraint* on predictive models. The three most tractable and publication-ready projects are ordered below by their proximity to the existing base.

### Paper 7: Geometric Trajectory Forecasting

**The step:** Rather than treating the 9-state employment-income space as a flat categorical space, represent it explicitly as a graph where nodes are the nine states and edge weights are observed transition probabilities. A graph transformer or message-passing neural network (Bronstein et al., 2021) learns dynamics that respect this graph structure, generating trajectory forecasts as *paths through the state graph* rather than independent categorical predictions at each time step.

**Why this is the right entry point into deep learning:** The state graph is tiny (9 nodes, ≤81 edges), so the GNN component is computationally trivial. The complexity comes from the trajectory data pipeline, which you already have. The TDA connection is direct: train on the observed trajectories, then simulate counterfactual trajectories under modified transition matrices and compare the PH of the simulated trajectory cloud to the observed — providing the "topological counterfactual" capability that the current paper correctly identifies as unresolved.

**Computational requirements:** Training a graph transformer on 27,280 trajectories with a 9-node state graph is trivially fast on the RTX 3080. The memory-intensive step is maintaining the full trajectory dataset during training — comfortably within 32GB RAM. Total training time: hours, not days.

**Implementation path:** PyTorch Geometric provides message-passing primitives. The model architecture is a small GRU/LSTM over state embeddings with a GNN layer over the transition graph. Pre-train on the full dataset; fine-tune on disadvantaged trajectories for escape-probability forecasting.

**Output: Paper 7.** Target *Journal of Machine Learning Research* or *Advances in Neural Information Processing Systems* (NeurIPS). The framing: "Structure-Respecting Trajectory Forecasting for Labour Market Dynamics."

### Paper 8: GNNs on Household Social Graphs

**The step:** Represent individuals as nodes in a graph where edges encode household membership and geocoded neighbourhood proximity. A GNN propagates information across these edges, testing whether escape from disadvantaged trajectories depends on relational context — which the current paper cannot test because it treats individuals as isolated points in the embedding space.

**The TDA synthesis:** The key novelty is using GNN-learned representations as *input features* to the TDA pipeline rather than n-gram vectors. This produces a *socially-informed topology* that reflects both individual trajectory structure and household/neighbourhood relational context. The Markov memory ladder can then be re-run on the socially-informed embedding to ask: does incorporating relational context change the topological complexity bound? If the z-score shifts from −3.7 toward 0 when household graphs are included, this provides evidence that the over-constraint finding is partly explained by social network structure.

**Computational requirements:** The household graph for 27,280 individuals across 14 USoc waves involves approximately 8,000–12,000 households as edges. A modest GNN (3 layers, 256 hidden dimensions) on this graph trains in hours on the RTX 3080. Neighbourhood graphs (Local Authority areas) would involve ~380 LA nodes — still tractable on the RTX 3080. The binding constraint is VRAM for large neighbourhood-level graphs with many trajectories per node; 10GB VRAM supports message-passing on graphs of ~50,000 nodes with moderate feature dimensions. For full LA-level experiments with feature-rich nodes, consider Colab Pro+ (A100 40GB).

**Output: Paper 8.** Target *Computational Social Science* or *Sociological Methods & Research*. This paper introduces GNNs to the research programme as a methodological tool rather than a paper-length contribution in its own right.

### Paper 9: Combinatorial Complex Neural Networks for Multi-Level Social Data

**The step:** Replace graphs with hierarchical cell complexes — individuals as 0-cells, households as 1-cells, neighbourhoods as 2-cells, local authorities as 3-cells — and train a Combinatorial Complex Neural Network (CCNN, Hajij et al. 2023)  that learns representations respecting the full multi-level structure of social data. [arxiv](https://arxiv.org/abs/2206.00606)

**Why this is the most ambitious but also most natural extension:** The social stratification literature already recognises individual, household, neighbourhood, and regional levels as analytically distinct. CCNNs provide the first neural architecture that can simultaneously model all four levels within a single learned representation, without flattening higher levels into individual-level controls. The mathematical framework (TopoModelX, TopoNetX, the TopoTune framework ) is stabilising — the ICML 2023 Topological Deep Learning Challenge  produced benchmarks and tooling that make this buildable, not just theoretically defined. [arxiv](https://arxiv.org/html/2410.06530v2)

**Implementation path:** Start with the 2-level version (individuals + households) using existing household identifiers. Validate against the GNN from Paper 8 to confirm that the cell-complex message passing adds predictive signal. Extend to 3-level (adding Local Authority data from ONS geocoding) in a second phase. Use the TDA results from Stage 1–2 as supervision signal: the escape probability labels from Paper 1 and the Wasserstein-differentiated subgroup labels from the cross-national comparison.

**Computational requirements:** This is the most computationally intensive step in the programme. The 2-level version (individual + household) is trainable on the RTX 3080 (10GB VRAM). The 3-level version with neighbourhood cells requires careful memory management — sparse cell-complex representations and gradient checkpointing. The 4-level version (adding Local Authority 3-cells) almost certainly requires cloud compute. **Recommended cloud strategy:** Develop and validate the 2-level architecture locally; run ablation studies comparing 2-level vs. 3-level vs. 4-level on a cloud A100 (target: 20–40 GPU-hours on AWS or GCP). The student cloud credits from AWS Educate or Google Cloud for Students (typically $100–$300) are sufficient for 2–3 targeted experimental runs if the experiments are pre-planned and the data pipeline is fully developed locally.

**Output: Paper 9.** Target *NeurIPS* or *ICML* (machine learning venues with social science application) or *Journal of Machine Learning Research*. This is the paper that scales the TDA insights to population-level prediction tools — the "horizon" identified in the source document.

### Paper 10: Topological Fairness Analysis (Policy Fast-Track)

**The step:** Apply Wasserstein distance between persistence diagrams not to subgroup trajectory clouds but to *prediction errors* across demographic groups. A trajectory forecasting model (Paper 7) trained on the full dataset may produce residuals with entirely different topological structures across gender, ethnic, or class groups — a signature of systematic bias invisible to mean-error metrics.

**Why this is policy-urgent:** Universal Credit administration, housing allocation, and school placement in the UK increasingly use algorithmic models. If those models have topologically distinct error structures across demographic groups, traditional fairness metrics (demographic parity, equalized odds) may not detect them. This paper provides a genuinely new lens and is explicitly policy-legible.

**How to build it:** Train the geometric trajectory forecasting model (Paper 7). Compute residuals (predicted vs. observed trajectory endpoints) for each demographic subgroup. Embed residuals in the PCA space (or use the model's learned representation). Compute Wasserstein distances between subgroup residual persistence diagrams. Use the existing permutation testing framework (Markov memory ladder) to assess significance.

**Computational requirements:** Trivial — CPU-only, Hera library, minutes of runtime. The main cost is having trained Paper 7's model first.

**Output: Paper 10.** Target *FAccT* (ACM Conference on Fairness, Accountability, and Transparency) or *Nature Machine Intelligence*. This paper has the highest policy impact of the programme and the fastest route from method to application — it requires only that Paper 7 is complete.

***

## Computational Resource Map

| Stage | Project | Local (i7/32GB/3080) | Cloud needed? | Estimated local time |
|---|---|---|---|---|
| 0 | Wasserstein upgrades to Paper 1 | ✅ Full | No | Minutes |
| 1a | Mapper | ✅ Full | No | Minutes–hours |
| 1b | Zigzag persistence | ✅ Full (streaming algorithm) | No | Hours–day |
| 2a | Multi-parameter PH | ✅ Development; ⚠️ Full scale | Optional A100 (~4–8 GPU-hrs) | Hours locally; cloud for full scale |
| 2b | Cross-national comparison | ✅ Full | No | Per-country: same as current paper |
| 2c | Intergenerational | ✅ Full | No | Hours |
| 3a | Geometric forecasting | ✅ Full | No | Hours |
| 3b | GNNs on household graphs | ✅ 2-level; ⚠️ 3-level | Optional for 3+ levels | Day locally for 2-level |
| 3c | CCNNs / cell complexes | ✅ 2-level only | Required for 3–4 levels | Cloud: 20–40 GPU-hrs (A100) |
| 3d | Topological fairness | ✅ Full | No | Minutes |

**Cloud compute targeting priority:** If credits are limited, concentrate cloud use on (1) the full-scale bifiltration experiments in Paper 4 and (2) the 3–4 level CCNN experiments in Paper 9. These are the two computationally irreducible steps — everything else is tractable on the current hardware with patience.

***

## Publication Sequence and Independent Project Boundaries

Each of Papers 2–10 is independently publishable and does not require the completion of any subsequent paper. The logical dependency structure is:

- Paper 2 (Mapper) and Paper 3 (Zigzag) depend only on Paper 1's existing pipeline
- Papers 4–6 depend on Paper 1's conceptual framework but not on Papers 2–3
- Papers 7 and 8 share a codebase and can be written as a single two-part contribution or two papers depending on scope
- Papers 9 and 10 depend on Paper 7 being complete

The strongest submission sequence for the programme's legibility is: Paper 1 → Papers 2+3 (simultaneous submissions) → Papers 5 (cross-national, highest sociological impact) + 4 (methods, JASA track) → Papers 7+10 (DL+fairness, policy-legible pair) → Papers 8+9 (technical deep learning). This sequence builds a recognisable research identity — the person who brought formal null-testing topology to life-course sociology and then connected it to policy-relevant prediction — which is coherent as a postdoc-to-faculty or independent-researcher narrative.