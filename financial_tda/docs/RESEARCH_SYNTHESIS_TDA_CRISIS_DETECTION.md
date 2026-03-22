# TDA Financial Crisis Detection: Research Synthesis

**Date:** 2025-12-18  
**Purpose:** Synthesize recent TDA literature to identify novel research directions

---

## 1. Papers Reviewed

### 1.1 Gidea & Katz (2018) — The Foundation
- **Title:** Topological data analysis of financial time series: Landscapes of crashes
- **Key Method:** 4-index point cloud, 500-day rolling windows, Kendall-τ trend detection
- **Metrics:** L¹/L² norms of persistence landscapes (variance, spectral density, ACF)
- **Findings:** Strong τ values (0.89-1.00) for 2000 Dotcom and 2008 GFC
- **Limitation:** Focuses on pre-crash trend detection; doesn't distinguish crisis types

### 1.2 Gidea et al. (2024) — Theoretical Justification
- **Title:** Why Topological Data Analysis Detects Financial Bubbles?
- **Key Insight:** Links TDA to **Log-Periodic Power Law Singularity (LPPLS)** model
- **LPPLS Signature:**
  - Super-exponential price growth/decay
  - Oscillations **increasing in frequency, decreasing in amplitude** near critical time
- **Why TDA Works:** Time-delay embedding creates 1D loops; changing oscillation patterns cause norm spikes
- **Critical Finding:** TDA detects **endogenous** bubbles (speculative feedback loops), NOT **exogenous** crashes
- **Application:** Bitcoin bubbles 2021-2022 (hourly data, 48-72 window sizes)

### 1.3 Yao et al. (2025) — Change Point Detection
- **Title:** Change Points Detection in Financial Market Using Topological Data Analysis
- **Key Innovation:** 
  - **Short windows** (60 days) vs G&K's 500-day windows
  - **29 indicators** (indices + 10 sector ETFs) vs G&K's 4 indices
  - **PELT algorithm** for structural break detection vs Kendall-τ trends
- **Events Detected:** 2011 EU Debt, 2016 Brexit, 2020 COVID, 2022 Energy Crisis
- **Finding:** L² more sensitive than L¹ for crashes
- **GitHub:** https://github.com/Janeyaoo/Detecting-Change-Points-in-Multivariate-Stock-prices-Using-Topology-data-analysis

### 1.4 Nie (2025) — Nonlinear Serial Dependence via ATCC
- **Title:** Unveiling complex nonlinear dynamics in stock markets through topological data analysis
- **Journal:** Physica A 680 (2025) 131025
- **Key Innovation:** 
  - **Auto Topological Correlation Coefficient (ATCC)** — uses kNN filtration instead of persistent homology
  - **Small-sample capable** — works with 50-100 observations (vs 500+ for G&K)
  - **High-resolution dynamics** — rolling 30-min windows for minute-level data
- **Key Findings:**
  - ATCC captures **nonlinear dependence** that standard ACF misses
  - Russia-Ukraine conflict (Feb 24, 2022) caused significant ATCC spikes in Chinese market
  - Trump tariffs (2025) altered dependence patterns in both SSE and S&P 500
  - Most stocks show linear dependence; **minority exhibit nonlinear serial dependence**
- **Relevance to Recovery Analysis:** ATCC's small-sample capability enables analysis of **post-crisis windows** (days to weeks) that G&K methodology cannot address

---

## 2. Key Theoretical Insight: Endogenous vs Exogenous

The Bitcoin paper provides a crucial distinction:

| Type | Cause | TDA Signal | LPPLS Fit | Example |
|------|-------|------------|-----------|---------|
| **Endogenous** | Speculative bubbles, herding | Strong, rising trend | Good | 2000 Dotcom, 2008 GFC |
| **Exogenous** | External shocks | Weak or divergent | Poor | COVID, 9/11, Brexit |

> "It is important to distinguish between crashes of an endogenous origin, essentially caused by speculative, unsustainable, accelerating bubbles, and crashes of an exogenous origin, caused by external factors (e.g., natural cataclysms, pandemics, fraud, political changes). Exogenous crashes are less likely to yield early warning signals."
> — Gidea et al. (2024), Section 1

**This explains our Phase 10 findings:**
- **GFC (5/6 consensus):** Endogenous bubble → strong TDA signal
- **COVID (2/6 consensus):** Exogenous shock → divergent, weak signal
- **2000 Dotcom (2/6 consensus):** Sector-specific endogenous → mixed signal

---

## 3. Methodological Comparison

| Aspect | G&K (2018) | Bitcoin Paper (2024) | Yao et al. (2025) | Our Implementation |
|--------|------------|---------------------|-------------------|-------------------|
| **Window Size** | 500 days | 48-72 hours | 60 days | 500 days |
| **Data Frequency** | Daily | Hourly | Daily | Daily |
| **Indices** | 4 (S&P, Dow, NASDAQ, Russell) | 1 (Bitcoin) | 29 (indices + ETFs) | 4 (S&P, Dow, NASDAQ, Russell) |
| **Homology** | H₁ | H₁ | H₀ and H₁ | H₁ |
| **Norms** | L¹, L² | L¹ | L¹, L² | L¹, L² |
| **Detection** | Kendall-τ trend | Visual peak | PELT changepoint | Kendall-τ trend |
| **Metrics** | 6 (var, spec, acf) | 1 (landscape norm) | 2 (L¹, L²) | 6 (var, spec, acf) |

---

## 4. Potential Novel Contributions

### 4.1 Endogenous/Exogenous Classification via Consensus ⭐⭐⭐
**Hypothesis:** High consensus (5-6/6 metrics agreeing) indicates endogenous bubbles; low consensus indicates exogenous shocks.

**Evidence from our data:**
| Event | Consensus | Classification | Var/Spec | ACF |
|-------|-----------|----------------|----------|-----|
| 2008 GFC | 5/6 | Endogenous | +0.80 | +0.52 |
| 2022 Rate Shock | 6/6 | Policy-driven | -0.91 | -0.90 |
| 2000 Dotcom | 2/6 | Sector bubble | +0.55 | -0.19 |
| 2020 COVID | 2/6 | Exogenous | +0.23 | -0.49 |
| 9/11 | 2/6 | Exogenous | +0.14 | -0.58 |

**Gap in literature:** No systematic study of multi-metric consensus as crisis classifier.

### 4.2 ACF as Independent "Memory" Indicator ⭐⭐
**Finding:** ACF metrics show near-zero VIX correlation (r < 0.1), unlike Var/Spec (r ≈ 0.3).

**Potential:** ACF captures topological "memory" — persistence of market structure — that VIX doesn't measure.

### 4.3 Window Size Sensitivity Study ⭐⭐
**Question:** Does 60-day windows (Yao) detect rapid-onset events (COVID, Brexit) better than 500-day (G&K)?

**Experiment:** Run both window sizes on same events, compare signal strength.

### 4.4 Sector Contagion Networks ⭐⭐⭐
**Extension from Yao:** Their 29-indicator approach with sector ETFs could enable:
- Tracking how TDA signals propagate across sectors
- Identifying "epicenter" sectors for each crisis
- Comparing with traditional contagion network methods

---

## 5. Limitations of Current Approaches

### From G&K (2018):
- Requires long data history (500+ days)
- Doesn't distinguish crisis types
- Cherry-picking risk (only 2 events validated originally)

### From Bitcoin Paper (2024):
- LPPLS fitting is sensitive to noise
- Parameter selection (window, delay, embedding dim) is empirical
- Hourly data not always available

### From Yao et al. (2025):
- PELT requires stationarity assumptions
- Short windows may miss slow-building crises
- R implementation (not Python)

### From Our Work:
- Struggles with exogenous shocks (COVID, 9/11)
- Reference value discrepancies (data source dependency)
- No theoretical framework beyond G&K

---

## 6. Suggested Research Directions

### Priority 1: Comprehensive Crisis Characterization Paper ⭐⭐⭐
**Title Idea:** "Topological Fingerprints of Financial Crises: A Multi-Metric Analysis of Endogenous vs Exogenous Shocks"

**Combines three research threads:**

1. **Crisis Classification via Consensus Patterns**
   - Use 6 G&K metrics + consensus patterns to classify 10+ historical crises
   - Hypothesis: High consensus (5-6/6) = endogenous; low consensus (1-2/6) = exogenous
   - Validate against economic literature on crisis origins

2. **ACF as Independent "Memory" Indicator**
   - Demonstrate ACF's VIX-independence (r < 0.1 vs Var/Spec r ≈ 0.3)
   - Argue ACF captures topological "memory" — persistence of market structure
   - Show ACF divergence patterns as early warning signatures

3. **Window Size Sensitivity Analysis**
   - Compare 60/100/250/500 day windows on same 10-event set
   - Identify optimal window for different crisis types (slow-build vs rapid-onset)
   - Bridge G&K (500-day) and Yao (60-day) methodologies

**Data Available:** continuous_tau_all_metrics.csv (7,371 days × 6 metrics)

### Priority 2: Multi-Sector Contagion Networks ⭐⭐⭐
**Extension from Yao et al.:** Their 29-indicator approach with sector ETFs could enable:
- Tracking how TDA signals propagate across sectors over time
- Identifying "epicenter" sectors for each crisis type
- Comparing with traditional contagion network methods (Granger causality, spillover indices)
- Potential for dynamic network visualization

### Priority 3: Extended Kendall-τ Analysis ⭐⭐
**Incremental but publishable:**
- Systematic comparison of all 6 G&K metrics across extended event set
- Contribution: No cherry-picking; all metrics reported transparently
- Limitation: Offers no new technique, primarily replication/extension

### Priority 4: LPPLS + TDA Joint Model ⭐⭐⭐
**Highly novel but requires significant new development:**
- Fit LPPLS model to historical crises (requires implementing LPPLS fitting in Python)
- Compare LPPLS "goodness of fit" with TDA consensus scores
- Test if TDA provides early warning even when LPPLS fitting is poor (as Bitcoin paper suggests)
- Potential to provide theoretical grounding for our empirical findings

### Priority 5: Post-Crisis Recovery Pattern Analysis ⭐⭐⭐⭐
**Novel Research Question:** "If you can't predict a disaster, can you identify optimal routes out of one?"

**Paradigm Shift:** Move from pre-crisis **prediction** to post-crisis **recovery identification**

**Hypothesis:** Different crisis types (endogenous vs exogenous) exhibit distinct topological recovery signatures:
- **Endogenous (bubble bursts):** Gradual normalization, extended high-dependence period
- **Exogenous (external shocks):** Sharp reversion, brief high-dependence spike

**Why This is Novel:**
1. Most TDA financial literature focuses on **pre-crisis early warning signals**
2. Post-crisis recovery patterns are **under-studied topologically**
3. **Actionable for practitioners:** Portfolio rebalancing, re-entry timing decisions
4. **Exogenous events can't be predicted** — but recovery patterns might be systematic

**Methodological Approach:**
1. Use Nie's ATCC for **high-resolution post-crisis windows** (short-sample capability)
2. Compare G&K τ trajectories **after** crisis dates (e.g., 60/120/250 days post-peak)
3. Classify recovery patterns by crisis type and validate across 10 events
4. Potential integration with regime-switching models (HMM)

**Key Questions:**
- Do endogenous crises show longer topological "memory" during recovery?
- Does ACF metric behavior differ from Var/Spec during recovery phase?
- Can recovery pattern type predict subsequent market performance?

**Data Available:** continuous_tau_all_metrics.csv already covers post-crisis periods for all 10 events

### Priority 6: Bond Market / Yield Curve TDA ⭐⭐⭐⭐
**Blue Ocean Research Area:** TDA application to fixed income is **largely unexplored**

**Why Bond Markets Matter:**
- Government debt sustainability is a **critical policy concern**
- Yield curve shape changes (normal → inverted → flat) are **leading economic indicators**
- Bond markets are **less noisy** than equities — potentially cleaner topological signals
- **Sovereign debt crises** (Greece 2010, UK Gilts 2022) have systemic implications

**Potential TDA Applications:**

1. **Yield Curve Shape Dynamics**
   - The yield curve is inherently about **shape** — level, slope, curvature
   - Traditional: Nelson-Siegel / Svensson parametric models
   - TDA approach: Track topological evolution of the curve's embedding
   - H₁ loops could capture **yield curve inversions**

2. **Cross-Country Sovereign Bond Correlation Networks**
   - Build point clouds from multi-country yield spreads
   - Detect contagion patterns (e.g., European debt crisis spreading)
   - Compare with equity TDA during same periods

3. **Credit Spread Topology**
   - Corporate bond spreads vs Treasury spreads
   - Could H₁ generators detect brewing credit stress?
   - Relevant for central bank financial stability monitoring

4. **Flight-to-Quality Detection**
   - During crises, correlation structures change (stocks down, bonds up)
   - TDA could capture this regime shift topologically

**Data Sources:**
- FRED: Treasury yields (1M → 30Y), multiple countries available
- ECB: Euro area government bond yields
- BIS: Global sovereign bond data

**Gap in Literature:** Search confirms **no substantial TDA research on yield curves yet** — this could be a **first-mover** contribution.

---

## 7. Novel Mathematical Contributions: Next-Gen Frameworks

The following proposals go beyond applying existing TDA methods, suggesting novel mathematical syntheses for financial time series.

### 7.1 Framework A: Topological Signature of Visibility (TSV) ⭐⭐⭐⭐⭐
**Synthesis:** Graph Theory + TDA + Rough Path Theory

**Concept:** 
1. Transform a time-series window into a **Natural Visibility Graph (NVG)**. Nodes = time points; Edges = visibility between peaks.
2. Construct a **Filtration** on the graph (e.g., using the graph Laplacian eigenvalues or clique complexes).
3. Compute the **Persistence Path** — the sequence of Betti numbers or landscape norms as the filtration evolves.
4. Apply the **Signature Transform** (from Rough Path Theory) to this Persistence Path.

**Novelty:** Standard TDA on Visibility Graphs exists, but using the **Signature** of the resulting topological evolution captures the *non-commutative sequential structure* of how the graph's "shape" breaks down. This would be a first-of-its-kind multi-layered filter.

### 7.2 Framework B: Analytic-Delay Embedding (ADE) ⭐⭐⭐⭐
**Synthesis:** Signal Processing (Analytic Signals) + TDA

**Concept:** 
Instead of standard time-delay embedding $X_t = (x_t, x_{t-\tau}, \dots)$, use the **Hilbert Transform** to create an analytic signal $z_t = x_t + i\tilde{x}_t$.
Map the window into a 4D complex-valued point cloud: 
$$P_t = (x_t, \tilde{x}_t, x_{t-\tau}, \tilde{x}_{t-\tau})$$

**Novelty:** This explicitly embeds **Phase and Amplitude** into the topological space. Traditional delay embedding captures phase implicitly (Takens), but ADE makes it first-class. This could precisely isolate the "Log-Periodic Oscillations" in the LPPLS model as specific H₁ cycle rotations.

### 7.3 Framework C: Topological Matrix Profile (TMP) ⭐⭐⭐⭐
**Synthesis:** Motif Discovery + Optimal Transport + TDA

**Concept:** 
1. Use the **Matrix Profile** approach: Slide a sub-window and find its "Nearest Neighbor" in the rest of the series.
2. **Crucial Twist:** Instead of using Euclidean distance (Z-normalized) to find neighbors, use the **Wasserstein distance ($W_p$)** between the **Persistence Diagrams** of the sub-windows.
3. Construct the "Topological Profile" — a series where each point indicates the distance to its topologically-most-similar motif.

**Novelty:** Standard Matrix Profile finds price-shape motifs. TMP would find **Topological Motifs** — recurring patterns of market *complexity* and *connectivity* that are invariant to scaling or absolute price levels. This could identify "Topological Pre-shocks" that recur exactly the same way before crashes.

---

## 8. References

1. Gidea, M., & Katz, Y. (2018). Topological data analysis of financial time series: Landscapes of crashes. *Physica A: Statistical Mechanics and its Applications*, 491, 820-834. https://doi.org/10.1016/j.physa.2017.09.028

2. Akingbade, S. W., Gidea, M., Manzi, M., & Nateghi, V. (2024). Why Topological Data Analysis Detects Financial Bubbles? [Preprint]. https://arxiv.org/abs/2304.06877

3. Yao, J., Li, J., Wu, J., Yang, M., & Wang, X. (2025). Change Points Detection in Financial Market Using Topological Data Analysis. *SSRN*. https://papers.ssrn.com/abstract=5196633

4. Johansen, A., & Sornette, D. (2000). The Nasdaq crash of April 2000: Yet another example of log-periodicity in a speculative bubble ending in a crash. *The European Physical Journal B*, 17(2), 319-328.

5. Gerlach, J. C., Demos, G., & Sornette, D. (2019). Dissection of Bitcoin's multiscale bubble history from January 2012 to February 2018. *Royal Society Open Science*, 6(7), 180643.

6. Bubenik, P. (2015). Statistical topological data analysis using persistence landscapes. *Journal of Machine Learning Research*, 16(1), 77-102.

7. Perea, J. A., & Harer, J. (2015). Sliding windows and persistence: An application of topological methods to signal analysis. *Foundations of Computational Mathematics*, 15(3), 799-838.

8. Nie, C.-X. (2025). Unveiling complex nonlinear dynamics in stock markets through topological data analysis. *Physica A: Statistical Mechanics and its Applications*, 680, 131025. https://doi.org/10.1016/j.physa.2025.131025

---

## 9. Data Assets

| File | Description |
|------|-------------|
| [continuous_tau_all_metrics.csv](file:///C:/Projects/TDL/outputs/foundation/continuous_tau_all_metrics.csv) | Full daily τ values 1996-2025 |
| [gk_complete_replication.csv](file:///C:/Projects/TDL/outputs/phase_10c_complete/gk_complete_replication.csv) | All 6 metrics for 10 events |
| [yao_tda_changepoints/](file:///C:/Projects/TDL/yao_tda_changepoints/) | Cloned Yao et al. R implementation |

---

*Created as part of Phase 10 Remediation Analysis*
