# P02 Reviewer Log

## Round 0 (Internal pre-submission review, April 2026)

**Draft reviewed:** v3-2026-03.md  
**Reviewer:** Self / supervisor feedback session  
**Status:** All items resolved in v4-2026-04.md

---

### R1 — Circular Reasoning Concern

**Comment:** The PC1 outcome variable is derived from the same n-gram state sequences as the PCA-20D embedding. Using PC1 as evidence of within-regime heterogeneity may be circular.

**Response (v4 §3.4, §4.8):** Added explicit correlation matrix (Table 9). PC1 correlates r=−0.921 with employment rate and r=+0.85 with inactivity rate — highly redundant as expected. However, churning rate (r=+0.12) and final income band (r=−0.22) are nearly orthogonal to PC1 and provide independent information. The within-R6 bifurcation on *final income band* (§4.4.1) and churning structure (Figure 9) are therefore genuinely independent evidence. Text now explicitly frames the correlation issue and distinguishes redundant from independent outcome variables.

---

### R2 — "Causal Geography" Terminology

**Comment:** The phrase "causal geography" is misleading — the Mapper graph identifies spatial variation in outcomes but cannot establish causation.

**Response (v4 throughout):** Replaced all instances of "causal geography" with "outcome geography". Added explicit clarification in §5.3: "The phrase 'outcome geography' we use throughout is intended to convey spatial structure in outcome distributions, not a claim about mechanisms."

---

### R3 — Permutation Null Tests Missing

**Comment:** The sub-regime node count (358) lacks a formal significance test. Is this large relative to chance?

**Response (v4 §4.3):** Added two permutation tests (100 permutations each):
- *Regime-shuffle null*: permute GMM labels, recount. Observed 358 vs. null mean=86.3 (sd=12.5), p<0.01 (0/100 perms ≥ 358).
- *Within-node-shuffle null*: fix graph, shuffle outcome values within regimes. Observed 358 vs. null mean=9.4 (sd=5.2), p<0.01.  
Both tests confirm the sub-regime structure is not distributional artefact. Multi-threshold Table 4a added.

---

### R4 — Novelty Framing

**Comment:** The paper does not position itself clearly as the first application of Mapper to longitudinal life-course trajectory data in sociology.

**Response (v4 §1.3):** Added explicit novelty statement: "This is, to our knowledge, the first application of Mapper to longitudinal life-course trajectory data in sociology. Previous work established that regime heterogeneity *exists* (Halpin 2010; silhouette 0.215); Mapper makes the *geometric structure* of that heterogeneity navigable."

---

### R5 — R3/R5 Churning Regime Distinction

**Comment:** The discussion of R3 (Emp-Inactive Mix) and R5 (High-Income Inactive) does not explain what distinguishes them structurally; both are "mixed regimes" with similar employment rates.

**Response (v4 §4.4.2):** Added transition-type decomposition for R3 and R5 (Table 7a). Key finding: E↔I transition rates are nearly identical (36.4% vs. 35.5%), but R3 churns *within employment income bands* (within-E = 38.6%) while R5 churns *within inactivity income bands* (within-I = 54.4%). The latter is consistent with R5 being a retirement/high-income-household inactivity regime, where non-employment income (pension, partner) fluctuates without affecting employment status.

---

### R6 — Algorithm Rationale

**Comment:** The paper evaluates DBSCAN and agglomerative clustering but does not explain *why* a researcher would choose one over the other.

**Response (v4 §3.3):** Added explicit rationale: DBSCAN as "conservative lower bound on sub-regime structure — only geometrically dense sub-regions enter the graph, so detected structure is unlikely to reflect noise"; agglomerative as "complete-coverage upper bound — captures boundary-spanning trajectories that DBSCAN treats as noise." Recommends using both: DBSCAN for exploratory visual inspection; agglomerative for coverage statistics and boundary analysis.

---

### R7 — UMAP Robustness

**Comment:** All results use PCA-20D embeddings. Are the within-regime findings specific to this embedding method?

**Response (v4 §4.7):** Added UMAP-16D robustness section (Table 8). Key findings: (1) Sub-regime structure persists (576–828 sub-regime nodes vs. 358 under PCA-20D; higher count reflects 100% UMAP coverage). (2) Regime purity remains high (0.954–0.967). (3) Bridge nodes appear (81–164) which were absent under PCA-20D DBSCAN — consistent with the agglomerative findings. NMI slightly lower (0.400–0.422 vs. 0.434) which is expected since GMM was fitted on PCA-20D.

---

### R8 — Sample Representativeness

**Comment:** No mention of attrition bias or panel survey limitations.

**Response (v4 §3.1):** Added: "Known panel survey limitations apply. Low-income workers face higher attrition in household panels (Watson & Wooden 2012), so the sample slightly overrepresents stable employment trajectories. USoc's annual refreshment samples partially mitigate attrition bias but do not eliminate it."

---

### R9 — Formal Outcome Definitions

**Comment:** Employment rate, churning rate etc. are used throughout without formal definitions.

**Response (v4 §3.4):** Added formal definitions using summation notation for all six time-averaged outcome variables, with explicit statements that employment+unemployment+inactivity = 1 and high+mid+low income = 1.

---

### R10 — OM Comparison

**Comment:** The OM comparison section describes what OM does but doesn't include a comparative visualisation.

**Response (v4 §5.5):** Added OM dendrogram comparison (Figure 11: Ward dendrogram truncated to 50 leaves, coloured by cluster-mean employment rate at k=7). Added computational cost comparison. Explains why Mapper's spatial layout makes within-regime bifurcations visible where the OM dendrogram cannot.

---

### R11 — Extended Literature on Within-Trajectory Complexity

**Comment:** The literature review on within-regime heterogeneity is thin. More could be said about measuring complexity inside sequence trajectories.

**Response (v4 §2.3):** Expanded with Gabadinho et al. (2011) on TraMineR complexity indices, Ritschard & Studer (2018) on entropy-based complexity measures, and Liao et al. (2022) on sequence network analysis. Positions Mapper as complementary: these methods reduce complexity to scalars; Mapper preserves spatial structure of the trajectory-type distribution.

---

### Code availability

Not previously stated. Added Code Availability statement (v4, end of §6) with GitHub URL and specific module paths.

---

*All R1–R11 items resolved. v4 ready for humanizer pass before final submission review.*

---

## Round 1 (Second internal review of v4, March 2026)

**Draft reviewed:** v4-2026-04.md
**Reviewer:** Internal quality check against original peer review PDF
**Status:** All items resolved in v4-2026-04.md (in-place revision)

---

### R12 — Embedding Robustness Qualifier (Tier 1 Essential)

**Comment:** Abstract and §1.3 use unqualified robustness language ("within-regime heterogeneity persists across all 24 configurations") despite §5.6 acknowledging embedding robustness was only partially tested. Reviewer's fallback: reframe as "robust to Mapper configuration, contingent on PCA-20D embedding."

**Response:** Added qualifying phrases throughout: abstract now says "within the PCA-20D embedding, within-regime heterogeneity persists across all 24 configurations; a UMAP-16D replication confirms qualitative robustness to embedding choice (§4.7)." §1.3 adds "robust to Mapper configuration within the PCA-20D embedding and replicate qualitatively under UMAP-16D." §4.5.1 scoped to "(within PCA-20D)." §5.6 rewritten: claims are "robust to Mapper configuration and qualitatively robust to embedding choice, but contingent on the n-gram frequency representation." §6 conclusion scoped to "under both PCA-20D and UMAP-16D embeddings."

---

### R13 — "Author (2026a)" → Real Name (Tier 3 Essential)

**Comment:** Placeholder "Author (2026a)" throughout would cause desk rejection.

**Response:** All 11 instances replaced with "Dorman (2026a)". Author field updated to "Stephen Dorman". Reference entry updated to "Dorman, S. (2026a). *Sociological Methodology*."

---

### R14 — |z| > 1.0 Statistical Justification (Tier 2)

**Comment:** Threshold arbitrary under non-normal distributions; no FDR acknowledgement for 14 comparisons; no permutation null for sub-regime node counts.

**Response:** §3.7 now explicitly states |z| > 1.0 is an exploratory screening criterion, not a significance test. Points to multi-threshold Table 4a (|z| > 0.5, 1.0, 1.5, 2.0) for robustness. Notes that FDR-corrected binomial tests are reported in §4.3, and permutation nulls provide distribution-free confirmation.

---

### R15 — Bridge Node Scaling Table (Tier 3 Polish)

**Comment:** Reviewer asked for threshold–bridge-count relationship explicitly; only prose existed.

**Response:** Added Table 7b to §4.5.2 showing bridge node counts by distance threshold (1.0, 1.5, 2.0) across all four lens functions. Text explicitly notes the relationship is monotonically increasing with no natural elbow.

---

### R16 — Figure 6 Caption Truncation Note (Tier 3 Polish)

**Comment:** Note about 1,500-node truncation was in §5.6 limitations, not in the figure caption itself.

**Response:** Figure 6 caption updated to: "Right: Agglomerative graph showing the 1,500 largest nodes for visual clarity; full graph contains 37,772 nodes at 100% coverage."

---

### R17 — Sociological Value of Navigability (Tier 2 Partial)

**Comment:** §1.3 does not explicitly tie navigability to a sociological value proposition (efficiency targeting, theoretical understanding of absorbing states).

**Response:** Added sentence to §1.3: "For sociology, this navigability matters: it converts an abstract statistical observation ('clusters are heterogeneous') into a concrete, spatially indexed answer about which sub-populations within a regime face divergent outcomes — enabling both more precise theoretical accounts of absorbing-state boundaries and better-targeted policy interventions."

---

### R18 — OM Dendrogram Comparison Strengthened (Tier 2)

**Comment:** §5.5 comparison "mostly rhetorical" — needed side-by-side with same colour scheme.

**Response:** Figure 11 description now cross-references Figure 8's colour scheme ("using the same colour scheme as the Mapper employment rate graph (Figure 8)"). Added interpretability comparison: "For a sociology audience, the Mapper graph is interpretable as a map ('these individuals are near the boundary with stable employment'), whereas the dendrogram is interpretable as a hierarchy ('these sub-clusters merge at Ward distance 12'). The former is more natural for questions about where within a regime someone sits."

---

### R19 — Code Availability (Tier 2)

**Comment:** No code availability statement.

**Response:** Already present in v4 at end of paper (after §6 Conclusion): GitHub URL, branch, module paths, and archived results. Confirmed present; no change needed.

---

### R20 — Undefined Variables Cleanup

**Comment:** §4.4.1 prose mentioned "employment improvement score" and "escape-to-employment indicator" which were not formally defined in §3.4.

**Response:** §4.4.1 prose updated to reference only the 6 formally defined variables. Table 9 (correlation matrix) trimmed of the two undefined rows.

---

*All R12–R20 items resolved. v4 ready for humanizer pass before final submission review.*
