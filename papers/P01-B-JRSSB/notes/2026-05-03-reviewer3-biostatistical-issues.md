# R3 Biostatistical Review — Issue Decomposition

**Source:** Biostatistical reviewer feedback on P01-B-JRSSB v1
**Created:** 2026-05-03
**Status:** Decomposed into B1–B13; pending integration into master response plan

## Overview

R3 assesses the paper as a **methods contribution** — the permutation tests, multiple comparisons, effect sizes, and uncertainty quantification are held to the standard of a reusable methodology. Three critical issues would block acceptance; the remainder are high/medium fixes that strengthen but do not fundamentally restructure the paper.

**Cross-references with existing plan:**
- B1 (W₂ anti-conservatism) = existing ISSUE H1 (§3) — same problem, R3 amplifies the stakes because §3.3 publishes the procedure
- B3 (BHPS negative control) = existing ISSUE M5 (§11) — R3 adds the requirement to *resolve* it, not just explain it
- B5 (missing effect sizes) overlaps with R1 effect-size requests already in the plan
- B6 (ε* sensitivity) overlaps with D1 filtration-scale work from R2

---

## B1 — W₂ test construction anti-conservative; published as methodology [CRITICAL]

### B1.1 The problem

§3.3 specifies the W₂ permutation test as: compare $\bar{W}_{\text{obs-null}}$ (a mean over $B$ draws) against individual null-null distances. This compares a low-variance mean against a high-variance reference distribution, inflating rejection rates. The paper publishes this as a **methodological recommendation** — any researcher following §3.3 will inherit the anti-conservatism.

**Same as ISSUE H1 (§3) in the existing plan**, but R3 elevates the severity: in the companion paper this is a results problem; here it is a *methodology propagation* problem.

### B1.2 Current state in v1

- §3.3: "The permutation p-value is the proportion of null-null distances that equal or exceed $\bar{W}$."
- p-value floor of $1/501 \approx 0.002$ from 500 null-null pairs.

### B1.3 Classification

**Code + prose + methodology** — must fix the test construction in §3.3 and re-run all tests. [P01-A SHARED]

### B1.4 Strategy

Already specified in the existing plan under ISSUE H1. The fix is the self-consistent $T_{\text{ratio}}$ statistic comparing mean obs-null to mean null-null:

$$T_{\text{ratio}} = \frac{\bar{W}_{\text{obs-null}}}{\bar{W}_{\text{null-null}}}$$

with BCa bootstrap CI. §3.3 must be rewritten to specify this construction as the recommended procedure. The existing anti-conservative construction should be acknowledged as incorrect in the revision cover letter.

### B1.5 Verification

- §3.3 specifies the corrected test construction ($T_{\text{ratio}}$ or equivalent mean-vs-mean comparison).
- All p-values in Tables 1–2 are recomputed under the corrected construction.
- The delta-method CI for $T_{\text{ratio}}$ is reported alongside every p-value.
- The cover letter explicitly acknowledges the v1 anti-conservatism.

---

## B2 — No type I/II error simulation study [CRITICAL]

### B2.1 The problem

The paper proposes a testing framework but never reports:
- **Type I error rate** (empirical rejection rate under the null at $\alpha = 0.05$) for any procedure
- **Type II error rate** (non-rejection rate under known alternatives) for any procedure
- **Power curves** showing what sample sizes ($N$, $T$) are required for 80% power

For a JRSS-B methods paper, simulation studies establishing calibration are essentially mandatory.

### B2.2 Current state in v1

No simulation study appears anywhere in the paper or supplement.

### B2.3 Classification

**New analysis** — requires designing and executing a simulation study. This is substantial new work.

### B2.4 Strategy — Minimal simulation study design

#### Three data-generating processes

**DGP-0 (Markov-1 null true).** Trajectories from first-order Markov chain with estimated USoc $\hat{P}$, same $N$ and $T_i$ distribution, same starting state distribution. Used for type I error calibration of Markov-1 test.

**DGP-1 (Markov-2 alternative).** Trajectories from second-order Markov chain with estimated $\hat{P}^{(2)}$. Markov-1 null is false; Markov-2 null is true. Used for power of Markov-1 test and type I error of Markov-2 test.

**DGP-2 (Observed data subsamples).** Subsamples of actual USoc embedding. Validates that the test detects real structure; checks label-shuffle negative control under controlled conditions.

#### Simulation grid

| $N$ | $T$ | Interpretation |
|---|---|---|
| 500 | 10 | Small panel, short trajectories |
| 2,000 | 10 | Medium panel, short trajectories |
| 8,509 | 14 | BHPS-scale |
| 27,280 | 13 | USoc-scale (primary target) |

4 $(N, T)$ combinations × 3 DGPs = 12 conditions. $S = 500$ independent replicates per condition. Each replicate: full simulated dataset → frozen PCA embedding → VR persistence at $L = 500$ landmarks.

#### What to compute per replicate

Run the W₂ test **twice** — v1 (anti-conservative) and v2 (corrected):

- **v1 (current):** $\bar{W}_{\text{obs-null}}$ vs individual null-null distances, $B = 100$ null draws.
- **v2 (corrected):** $T_{\text{ratio}} = \bar{W}_{\text{obs-null}} / \bar{W}_{\text{null-null}}$ vs $R = 500$ fresh null realisations of the same ratio.

Record: p-value (both), $\bar{W}_{\text{obs-null}}$, $\bar{W}_{\text{null-null}}$, $T_{\text{ratio}}$, runtime.

Rejection rates across $S = 500$ replicates at $\alpha \in \{0.01, 0.05, 0.10\}$ = empirical type I error (DGP-0) or power (DGP-1).

#### Four key outputs

**Output 1 — Type I error table (DGP-0, Markov-1 null true).**

| $N$ | $T$ | Rejection rate (v1) | Rejection rate (v2) |
|---|---|---|---|
| 500 | 10 | — | — |
| 2,000 | 10 | — | — |
| 8,509 | 14 | — | — |
| 27,280 | 13 | — | — |

Expected: v2 ≈ 0.05 across all rows; v1 > 0.05, inflation increasing with $N$ (larger samples → more stable $\bar{W}_{\text{obs-null}}$ → wider variance gap).

**Output 2 — Power curve (DGP-1, Markov-1 null false).** Rejection rate under v2 as function of $(N, T)$. USoc-scale should show high power; $N = 500$ may show low power. Establishes minimum sample size for reliable detection → direct input to §5.2 practitioner guidance.

**Output 3 — Ladder consistency check (DGP-0, all five levels, USoc-scale).**

| Null level | Expected rejection under DGP-0 |
|---|---|
| Label shuffle | Non-rejection (DGP-0 has no structure beyond Markov-1) |
| Cohort shuffle | Non-rejection |
| Order shuffle | **Rejection** (Markov-1 sequences have sequential order) |
| Markov-1 | Non-rejection (DGP-0 is Markov-1 by construction) |
| Markov-2 | Non-rejection |

Any departure from expected pattern reveals miscalibration at that level.

**Output 4 — BHPS label-shuffle diagnosis (DGP-0, $N = 8{,}509$, $T = 14$).** Run label-shuffle on DGP-0 data at BHPS scale. If rejection rate ≈ 0.05: BHPS failure is genuine data feature (marginal heterogeneity beyond Markov-1), not test miscalibration. If rejection rate >> 0.05: failure is anti-conservatism worsening with trajectory length. **This single output resolves the B3 ambiguity.**

#### Computational feasibility

$S = 500$ replicates × 12 conditions × ($B = 100$ + $R = 500$) = 3,600,000 VR computations at $L = 500$ landmarks. Ripser at $L = 500$ on 20D point cloud ≈ 0.1–0.5s → total ≈ 100–500 CPU-hours. On 16-core machine: 6–31 hours. On 100-core cluster: 1–4 hours.

**Minimal version:** restrict to BHPS-scale + USoc-scale + one smaller condition = 6 conditions → 50–250 CPU-hours (3–15 hours on 16 cores).

#### What the study does NOT need to cover

- Landscape $L^2$ calibration (doubles computation for marginal gain; defer to supplement)
- H₁ calibration (non-significant in most results; note "confirmed in pilot runs")
- Landmark sensitivity within simulation (run at $L = 500$; note same pattern as main analysis)
- SOEP/PSID transportability (not required for JRSS-B acceptance)

#### Reporting in the paper

**Placement:** §3.5 or new §4.0 before the application section. ~600 words + 2 tables.

**Simulation Table 1:** Type I error rates at $\alpha = 0.05$ for v1 and v2 constructions, all conditions, Markov-1 level.

**Simulation Table 2:** Power (v2, Markov-1 level under DGP-1) across $(N, T)$ + ladder consistency rates (all five levels, DGP-0, USoc-scale).

### B2.5 Verification

- §3.5 (or supplement) reports type I error rates for Markov-1 null under corrected construction across all $(N, T)$ conditions.
- Empirical rejection rates are within $0.05 \pm 0.019$ (binomial SE for $S = 500$).
- The v1 anti-conservatism inflation factor is quantified: rejection rate (v1) vs rejection rate (v2) at each $(N, T)$.
- Power curve for Markov-2 alternative (DGP-1) is reported.
- Ladder consistency check for all five levels at USoc-scale is reported.
- BHPS label-shuffle diagnosis (Output 4) resolves the B3 ambiguity.
- Total computation is documented (CPU-hours, machine spec).

---

## B3 — BHPS label-shuffle negative control fails ($p = 0.036$) [CRITICAL]

### B3.1 The problem

The label-shuffle is defined in §3.2 as a **negative control** ("rejection would indicate a computational artefact"). The BHPS $W_2$ label-shuffle gives $p = 0.036$ — a rejection at $\alpha = 0.05$. The paper explains this as "BHPS is inherently more topologically sensitive" but does not test this explanation or acknowledge that the negative control has failed. R3 requires either:
1. Show the rejection is a power artefact (e.g., randomly shortened BHPS trajectories give non-significant results), OR
2. Acknowledge the negative control fails for BHPS and interpret the BHPS ladder results with caution.

**Same as ISSUE M5 (§11)** but R3 demands resolution, not just explanation.

### B3.2 Current state in v1

- §4.2.3: "the BHPS-era trajectory manifold has more structure per trajectory than the shorter USoc sample"
- Presented as explanation, not as a problem requiring resolution.

### B3.3 Classification

**Analysis + prose** — requires a diagnostic experiment plus reframing.

### B3.4 Strategy

#### Why the global label shuffle fails: two competing explanations

**Explanation 1 — Anti-conservative test construction (B1).** The v1 mean-vs-individual comparison inflates rejection rates. The BHPS rejection may simply be a type I error inflated by the anti-conservative construction. Resolution: re-run under the v2 corrected construction.

**Explanation 2 — Between-individual heterogeneity destruction.** The global shuffle pools all person-years and permutes across individuals. This destroys between-individual heterogeneity in state frequencies (e.g., an individual who spent 14 years in EH gets states from individuals who spent time in IL). The re-embedded point cloud is more homogeneous than the observed data. The $W_2$ test rejects because the observed cloud has structural variation that the global shuffle cannot reproduce — even though this variation is not sequential structure.

**Key insight:** These explanations are empirically distinguishable via a **within-individual shuffle** that permutes each person's states independently, preserving per-person frequency distributions while destroying temporal order.

#### Five-step resolution

1. **Run within-individual shuffle.** For each individual, permute their own state sequence. Re-embed via frozen PCA. Compute $W_2$. If within-individual shuffle gives $p > 0.05$ while global shuffle gives $p = 0.036$, Explanation 2 is confirmed.

2. **PC1 variance diagnostic.** Compare $\text{Var}_{\text{PC1}}$ across three conditions:
   - Observed embedding
   - Global shuffle (mean over $B = 100$ surrogates)
   - Within-individual shuffle (mean over $B = 100$ surrogates)

   If $\text{Var}_{\text{PC1}}(\text{global}) \ll \text{Var}_{\text{PC1}}(\text{within}) \approx \text{Var}_{\text{PC1}}(\text{observed})$: global shuffle destroys between-individual heterogeneity → Explanation 2 confirmed.
   If $\text{Var}_{\text{PC1}}(\text{global}) \approx \text{Var}_{\text{PC1}}(\text{within})$: heterogeneity destruction is not the mechanism → Explanation 1 more likely.

   This diagnostic takes ~10 minutes on existing pipeline (embedding projection only, no TDA computation).

3. **Trajectory-length truncation experiment.** Truncate BHPS trajectories to USoc-equivalent length (14 years). Re-run global label shuffle. If $p > 0.05$: rejection was a power artefact from trajectory length.

4. **Report the v2-corrected p-value.** Under the corrected $T_{\text{ratio}}$ construction, the BHPS label-shuffle p-value may change. If it becomes non-significant, the problem dissolves.

5. **Reframe §3.2.** The label shuffle is not a pure negative control — it tests whether the embedding captures structure beyond what random label assignment produces. For data-rich panels with strong between-individual heterogeneity, rejection is expected and informative:
   - **Global shuffle rejection + within-individual non-rejection** = the embedding captures between-individual heterogeneity (genuine structure, not an artefact).
   - **Both reject** = the embedding captures sequential structure beyond what either shuffle type preserves.
   - **Neither rejects** = the embedding does not capture more than random label assignment.

   The paper should report both shuffle types and interpret the *pattern* rather than treating global shuffle rejection as a failure.

#### Cross-reference with B2

B2 Output 4 (BHPS label-shuffle diagnosis under DGP-0) provides the simulation-based resolution: if the label-shuffle rejection rate ≈ 0.05 under DGP-0 (Markov-1 data at BHPS scale), the BHPS failure is a genuine data feature. The within-individual shuffle diagnostic provides the *mechanistic* explanation for why.

#### Implementation reference

Within-individual shuffle implementation: `rng.permutation(traj)` for each individual's trajectory independently. Global shuffle: pool all person-years via `np.concatenate`, permute, split back to original trajectory lengths. Both re-embed via frozen PCA loadings (no PCA re-fitting). The `compare_shuffle_types` and `diagnose_bhps_label_shuffle` functions provide the complete diagnostic pipeline.

### B3.5 Verification

- §4.2.3 reports both global and within-individual label-shuffle $W_2$ results for BHPS.
- The PC1 variance diagnostic is reported, confirming or ruling out between-individual heterogeneity destruction.
- The corrected p-value under the v2 construction is reported.
- §3.2 reframes the label shuffle to distinguish global vs within-individual variants and interprets the rejection pattern.
- If truncation resolves the global shuffle rejection, this is documented as trajectory-length sensitivity.
- The resolution is cross-referenced with B2 Output 4 (simulation-based calibration).

### B3.6 Implementation architecture

#### Design principle

The Markov memory ladder must support swappable Level 1 strategies without rewriting the runner. The pattern is configuration-driven: the ladder is a list of `(level_name, NullStrategy)` tuples, and only the Level 1 entry changes between surveys.

#### Strategy abstraction

All null models implement a common `NullStrategy` interface with `generate_surrogate(trajectories) -> surrogates`. Five concrete implementations:

| Class | Level | What it destroys | What it preserves |
|---|---|---|---|
| `GlobalLabelShuffle` | 1a (USoc) | Between-individual heterogeneity + temporal order | Population-level state marginals |
| `WithinIndividualLabelShuffle` | 1b (BHPS) | Temporal order only | Per-person state frequencies |
| `CohortShuffle` | 2 | Within-cohort individual assignment | Cohort-level composition |
| `OrderShuffle` | 3 | Temporal order | Per-person state frequencies |
| `MarkovOrder1Surrogate` | 4 | Higher-order memory | First-order transition structure |
| `MarkovOrder2Surrogate` | 5 | Third+ order memory | Second-order transition structure |

**Note:** `WithinIndividualLabelShuffle` and `OrderShuffle` are algorithmically identical (`rng.permutation(traj)` per individual). They differ only in their position in the ladder and their interpretive role: Level 1b tests whether the embedding captures *more than per-person frequencies*; Level 3 tests whether *temporal order* contributes beyond what random reordering produces, after cohort structure has been tested at Level 2.

#### Ladder configuration

```python
# USoc ladder (original):  GlobalLabelShuffle → CohortShuffle → OrderShuffle → Markov1 → Markov2
# BHPS ladder (corrected): WithinIndividualLabelShuffle → CohortShuffle → OrderShuffle → Markov1 → Markov2
```

The `LadderConfig` dataclass selects Level 1 based on `survey` parameter. Levels 2–5 are identical across surveys.

#### Output file naming

Results saved as `ladder_{survey}_L{landmarks}_B{B}_{date}.json`. The `survey` field distinguishes variants: `"bhps"` (within-individual Level 1), `"bhps_global_l1"` (global Level 1 for comparison), `"usoc"` (global Level 1). No silent overwriting — existing files get `_v2` suffix.

#### BHPS comparison diagnostic

`compare_level1_variants_bhps` runs both Level 1 variants on the same BHPS data and produces a comparison table with:
- $T_{\text{ratio}}$, 95% CI, corrected p-value for each variant
- $\text{Var}_{\text{PC1}}$ under null surrogates for each variant
- Direct evidence for Explanation 1 vs Explanation 2

**Total cost:** ~2× the compute of a single Level 1 run (~200 VR computations at $L = 2{,}000$). Approximately 30–60 minutes on i7/32 GB.

#### Repository integration

**Immutability constraint:** `results/trajectory_tda_bhps/post_audit/` and `results/trajectory_tda_integration/post_audit/` are **never modified**. All new results go under `level1_revision/` subdirectories.

**Files changed (minimal diff):**

| File | Action | Purpose |
|---|---|---|
| `src/tda_pipeline/null_models/base.py` | NEW | `NullStrategy` ABC |
| `src/tda_pipeline/null_models/shuffle.py` | MODIFIED | Add `WithinIndividualLabelShuffle` |
| `src/tda_pipeline/null_models/ladder.py` | MODIFIED | Survey-aware builder with `LEVEL1_REGISTRY` |
| `src/tda_pipeline/null_models/__init__.py` | MODIFIED | Export new classes |
| `config/bhps_ladder.yaml` | MODIFIED | `level1_type: within_individual` |
| `config/usoc_ladder.yaml` | MODIFIED | `level1_type: global` (unchanged value, explicit key) |
| `scripts/run_bhps_level1_comparison.py` | NEW | One-off diagnostic |
| `src/tda_pipeline/tests/test_shuffle.py` | NEW | Unit tests |
| `src/tda_pipeline/tests/test_ladder_config.py` | NEW | Integration tests |
| `papers/P01-B-JRSSB/notes/2026-05-XX-level1-revision-note.md` | NEW | Audit trail |

**Config-driven design:** The BHPS/USoc distinction lives entirely in YAML (`level1_type` key). A future researcher cannot accidentally use the global shuffle for BHPS — the config enforces the correct choice. Reverting to global is a single YAML key change.

**Unit tests (four key properties):**
1. Global shuffle preserves population-level marginals
2. Within-individual shuffle preserves per-person state counts
3. Within-individual shuffle changes temporal ordering
4. Global shuffle does NOT preserve per-person frequencies (confirms it destroys between-individual heterogeneity)

**Integration tests:** Verify `build_ladder` returns correct Level 1 class for each survey, raises `ValueError` for unknown types, and produces exactly 5 levels.

**Results directory structure:**

```
results/trajectory_tda_bhps/
├── post_audit/                           # IMMUTABLE
│   └── 04_nulls_wasserstein_w2_20260407.json
└── level1_revision/                      # NEW
    ├── ladder_bhps_within_L2000_B100_YYYYMMDD.json
    ├── ladder_bhps_global_L2000_B100_YYYYMMDD.json
    └── level1_comparison_YYYYMMDD.json
```

**Revision note template:** Documents motivation, diagnostic results (PC1 variance comparison), files changed, and relation to paper sections (§3.2, §4.2.3, §5.2). Filled after diagnostic run with actual values and conclusion.

---

## B4 — $\text{BR}^{\text{span}}$ defined as test statistic but no null distribution reported [HIGH]

### B4.1 The problem

$\text{BR}^{\text{span}} = \beta_0(\varepsilon^*; X_t^{\text{new}}) / \beta_0(\varepsilon^*; X_t^*) = 9.5/5.7 \approx 1.67$ is presented as a formal statistic in §3.4.2 but reported without a null distribution, CI, or permutation test. The pool-draw null provides the null for the aggregate block ratio, not for the spanning-vs-newcomer ratio.

### B4.2 Classification

**New analysis** — requires a permutation test for $\text{BR}^{\text{span}}$.

### B4.3 Strategy

1. **Implement a permutation test.** Under the null that spanning and newcomer populations have the same topological complexity: randomly split the combined population into groups of sizes $|\mathcal{I}^*|$ and $|\mathcal{I}_2|$, compute $\text{BR}^{\text{span}}$ for each draw, report p-value.
2. **Report a CI for $\text{BR}^{\text{span}}$.** Bootstrap over landmark selections and sub-samples.
3. **Report the null distribution mean and SD** alongside the observed value, as done for the aggregate block ratio.

### B4.4 Verification

- §4.3.2 reports $\text{BR}^{\text{span}}$ with a permutation p-value, null mean, null SD, and effect size in SD units.
- A CI for the observed $\text{BR}^{\text{span}}$ is reported.

---

## B5 — Table 2 reports only p-values; no $W_2$ effect sizes or null means [HIGH]

### B5.1 The problem

Table 2 ($W_2$ results) reports only p-values. No observed $W_2$ distances, null means, null SDs, or effect sizes. The obs-null mean (23.18) and null-null mean (7.05) for BHPS Markov-1 appear only in the companion paper. A JRSS-B reviewer requires the effect-size analogue for every significant test.

### B5.2 Classification

**Prose + table restructuring** — the data exists; it needs to be reported.

### B5.3 Strategy

1. **Expand Table 2** to match Table 1's format: observed value, null mean, null SD, p-value, effect size $d = (\text{obs} - \mu_{\text{null}}) / \sigma_{\text{null}}$.
2. **Add a $T_{\text{ratio}}$ column** with delta-method CI (per B1 fix).
3. **For every significant test**, report the effect size in the text as well as the table.

### B5.4 Verification

- Table 2 has columns: Observed $\bar{W}_{\text{obs-null}}$, Null mean $\bar{W}_{\text{null-null}}$, Null SD, $T_{\text{ratio}}$, 95% CI, p-value, effect size $d$.
- Every significant result in the text cites the effect size, not just the p-value.

---

## B6 — $\varepsilon^* = 0.70$ sensitivity not examined [HIGH]

### B6.1 The problem

Table 4 results are computed at $\varepsilon^* = 0.70$, chosen at the knee of the Betti descent curve. No sensitivity analysis shows how the results change at nearby scales. The Kneedle algorithm is a heuristic with inherent uncertainty.

### B6.2 Classification

**New analysis** — requires computing Table 4 across a range of $\varepsilon$ values.

### B6.3 Strategy

**Note: partially addressed by D1 filtration-scale work.** Under the revised D1 design, $\varepsilon^*$ is derived from the persistence gap rather than the Betti knee, which removes the heuristic dependency. Additionally:

1. **Report Table 4 results across $\varepsilon \in \{0.50, 0.60, 0.70, 0.80, 0.90, 1.00\}$** as a sensitivity table in the supplement.
2. **Show that the qualitative conclusion** ($\text{BR}^{\text{span}} > 1$, newcomers more topologically complex) holds across the range.
3. **Report the persistence-gap-derived $\varepsilon^*$** and note whether it agrees with the Kneedle estimate of 0.70.

### B6.4 Verification

- Supplement contains Table 4 results across 6 $\varepsilon$ values.
- $\text{BR}^{\text{span}} > 1$ is robust across the range (or the range where it fails is documented).
- $\varepsilon^*$ is derived from the persistence gap, not the Kneedle heuristic.

---

## B7 — Macro correlations: CIs not reported; BH-FDR total test count unstated [HIGH]

### B7.1 The problem

Table 5 reports Pearson $r$ without CIs. With $n = 18$ years, CIs are wide (e.g., $r = 0.823 \Rightarrow 95\%\text{ CI} \approx [0.58, 0.93]$). Total test count for BH-FDR not stated — "10/35 in the full panel" is mentioned but the full family size is unclear. Four specifications (raw, within-era, detrended, first-differenced) × 35 pairs = 140 tests if tested separately.

### B7.2 Classification

**Prose + analysis** — CIs are straightforward (Fisher z-transform); BH accounting requires stating the family.

### B7.3 Strategy

1. **Add Fisher z-transform 95% CIs** to every $r$ in Table 5.
2. **State the full family size.** Specify: $M$ macro indicators × $K$ topological measures × $S$ specifications = total tests. State whether BH is applied within each specification or pooled.
3. **Report the full table** (all tests, including non-significant) in the supplement. The main text can show the significant subset, but the supplement must show the full family.
4. **Address the ecological fallacy** (already in D6 from R2): correlating annual topological summaries with annual macro indicators on $n = 18$ or $n = 32$ time points is ecologically valid but cannot support individual-level causal claims. State this.

### B7.4 Verification

- Table 5 includes 95% CIs for all $r$ values.
- The total test count and BH family definition are stated.
- Supplement contains the full correlation table (all tests, not just significant).

---

## B8 — Mantel test assumes exchangeable annual diagrams; serial dependence not acknowledged [HIGH]

### B8.1 The problem

The Mantel test ($r = 0.768$, $p < 10^{-6}$, $B = 1{,}000$) permutes row/column labels. Valid only if off-diagonal entries are exchangeable under the null. But consecutive years share individuals through the panel structure, creating positive serial correlations along diagonal bands. The permutation test is anti-conservative under serial dependence.

### B8.2 Classification

**Analysis + prose** — requires either the Dutilleul (1993) correction or an alternative test.

### B8.3 Strategy

1. **Apply the Dutilleul (1993) correction** for autocorrelated spatial data. This adjusts the effective degrees of freedom and produces a corrected p-value. Report both the uncorrected and Dutilleul-corrected p-values.
2. **Alternatively, use a block permutation** that preserves the serial structure: permute blocks of consecutive years rather than individual years.
3. **State the serial dependence assumption explicitly** in §4.3.1.
4. **Note:** Under Design 3 (window slicing), consecutive sub-clouds share even more individuals than under the current construction. The serial dependence is structural and must be addressed regardless of design choice.

### B8.4 Verification

- §4.3.1 states the exchangeability assumption and its violation.
- The Dutilleul-corrected p-value (or block-permutation p-value) is reported alongside the standard Mantel p-value.
- The serial dependence issue is acknowledged as a limitation of the Mantel test for panel data.

---

## B9 — Pool-draw null: 10-repetition variance not reported; CI for block ratio not given [MEDIUM]

### B9.1 The problem

The block ratio is averaged over 10 repetitions of the sub-sampling/landmark pipeline. The variance across repetitions is not reported. If it varies substantially (e.g., [1.3, 1.8]), the point estimate 1.581 is imprecise.

### B9.2 Strategy

1. **Report the 10-repetition mean and SD** for the block ratio: $\hat{\text{BR}} = 1.581 \pm \text{SD}$.
2. **Report a CI** using the 10 repetitions as a simple $t$-interval.
3. **If the SD is large**, consider increasing the repetition count.

### B9.3 Verification

- Table 3 reports $\hat{\text{BR}} \pm \text{SD}$ from the 10 repetitions.
- A 95% CI for $\hat{\text{BR}}$ is stated.

---

## B10 — One-sided test direction not specified for $W_2$ or block ratio tests [MEDIUM]

### B10.1 The problem

§3.3 states the TP test direction (one-sided, larger-is-more-extreme) but does not state the direction for the $W_2$ test or the block ratio test. For Markov-1 TP, the observed value falls in the *lower* tail ($p = 1.000$), meaning the implicit directional assumption was violated. A methods paper must specify direction before seeing results, or use two-sided tests.

### B10.2 Strategy

1. **Specify two-sided tests throughout §3.3** unless a strong prior justification exists for one-sided.
2. **For the block ratio:** state one-sided ($\text{BR} > 1$, cross-era exceeds within-era) with justification that the survey transition hypothesis predicts elevation, not reduction.
3. **For the Markov-1 TP result ($p = 1.000$):** report as a two-sided test where the observed value falls in the lower tail. State: "the observed TP is $d = -3.7$ SD below the Markov-1 null mean, indicating that the Markov-1 model generates more total persistence than the data."

### B10.3 Verification

- §3.3 specifies test directionality for every test.
- Two-sided p-values are reported for tests where the direction was not pre-specified.
- The Markov-1 TP result is reported with the correct tail interpretation.

---

## B11 — Replay drift implications for p-values not quantified [MEDIUM]

### B11.1 The problem

The 13% W₂ replay drift (stored 12.68 vs replay 11.22) is disclosed but its effect on the ratio $T_{\text{ratio}}$ is not assessed.

### B11.2 Strategy

1. **Compute the ratio under both values.** Stored: $12.68/5.99 \approx 2.12$. Replay: $11.22/5.99 \approx 1.87$. State: "neither changes the qualitative conclusion."
2. **Report the replay ratio alongside the stored ratio** in §4.2.1.
3. **Document the source of the drift** (unseeded RNG, library version change, etc.) and the mitigation (lockfile pinning for v2).

### B11.3 Verification

- §4.2.1 reports both stored and replay ratios with explicit statement about qualitative robustness.
- The drift source is diagnosed and documented.

---

## B12 — Table 3 tests five statistics from the same matrix without multiplicity correction [MEDIUM]

### B12.1 The problem

Table 3 reports five statistics (cross-era mean $W_2$, within-BHPS mean, within-USoc mean, consecutive-year mean, Mantel $r$) each with their own p-value. These are not independent — all derived from the same 32×32 matrix.

### B12.2 Strategy

1. **Apply Bonferroni correction over 5 tests.** Threshold: $p < 0.01$. All Table 3 statistics currently survive this (all $p < 0.001$ or $p = 0.34$).
2. **State the correction explicitly.** "Five statistics are derived from the same distance matrix; we apply Bonferroni correction with $m = 5$. All significant results survive the correction."
3. **Alternatively, designate one primary statistic** (the block ratio) and treat the others as descriptive. This avoids multiplicity but requires the designation to be stated before the results.

### B12.3 Verification

- Table 3 reports adjusted p-values or states the multiplicity correction.
- The correction is acknowledged as conservative given the non-independence.

---

## B13 — Practitioner guidance lacks calibrated decision thresholds [MEDIUM]

### B13.1 The problem

§5.2 advises increasing $B$ when $p \approx 0.05\text{–}0.10$ but does not define "near-significant" or specify minimum $B$ for a given decision threshold. Without type I error calibration (B2), these thresholds are ungrounded.

### B13.2 Strategy

1. **Define the inconclusive zone.** Propose $p \in [0.02, 0.10]$ as the zone where $B$ should be increased.
2. **Specify minimum $B$** as a function of the target p-value resolution: $B_{\min} \geq 10 / \alpha$ for resolution at level $\alpha$ (e.g., $B \geq 200$ for $\alpha = 0.05$).
3. **Ground the guidance in the simulation study (B2).** The simulation results provide empirical calibration for the recommended $B$ values.
4. **Add a decision flowchart** to §5.2 (or supplement) showing the recommended procedure.

### B13.3 Verification

- §5.2 specifies calibrated $B$ recommendations grounded in the simulation study.
- The inconclusive zone is defined with numerical boundaries.
- The decision flowchart is included (supplement or main text).

---

## Dependency Map

```
B1 (W₂ fix) ──→ B2 (simulation study uses corrected construction)
             ──→ B3 (corrected p-value may resolve BHPS label-shuffle)
             ──→ B5 (Table 2 restructuring uses corrected statistics)

B2 (simulation) ──→ B13 (practitioner guidance grounded in calibration)

B6 (ε* sensitivity) ←── D1 (persistence-gap ε* from R2)

B7 (macro CIs) ←── D6 (macro-correlation fixes from R2)

B8 (Mantel serial dependence) ←── D1 (Design 3 increases serial dependence)
```

## Summary by Action Type

| Action type | Issues | Estimated effort |
|---|---|---|
| **Fix test construction** (code + §3.3 rewrite) | B1, B10 | 2 days human + re-run compute |
| **New simulation study** | B2 | 3–5 days human + 2–4 days compute |
| **Diagnostic experiment** (BHPS truncation) | B3 | 0.5 days compute |
| **New permutation test** ($\text{BR}^{\text{span}}$) | B4 | 1 day compute |
| **Table restructuring** | B5, B9 | 0.5 days human |
| **Sensitivity analysis** ($\varepsilon$) | B6 | 2–4 h compute |
| **CIs and family accounting** | B7 | 0.5 days human |
| **Dutilleul/block-permutation correction** | B8 | 1 day human + compute |
| **Prose fixes** | B10, B11, B12, B13 | 1 day human |
| **Total** | | **~8–12 days human + 3–5 days compute** |
