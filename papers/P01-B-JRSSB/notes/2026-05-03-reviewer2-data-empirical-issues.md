# Reviewer 2 (Survey Data & Empirical Claims) — Issue Decomposition

**Date:** 2026-05-03
**Reviewer type:** Survey methodology / empirical data expert
**Source review:** "Survey Data & Empirical Claims Review: Structured Hypothesis Testing for Persistent Homology"
**Severity framework:** Uses reviewer's own Critical / High / Medium ratings
**Key framing:** This reviewer treats data problems as *methodological validation failures* because P01-B positions its UK application as validation of the framework, not mere illustration.

Issues numbered D1–D11 to distinguish from R1 (H1–L1), R2-A (S1–S14), and R3 (B1–B13).

---

## D1 — Annual sub-cloud construction undefined; pool-draw independence violated [CRITICAL]

### D1.1 The problem

The paper never defines which individuals appear in which annual sub-cloud $X_t$. If $X_t$ = "individuals whose trajectory spans year $t$," a single individual with a 14-year trajectory appears in 14 consecutive $X_t$ sub-clouds. The pooled population $\mathcal{X} = \bigcup X_t$ then contains repeated individuals, violating the independence assumption of the pool-draw null. The pool-draw procedure randomly partitions $\mathcal{X}$ preserving sub-cloud sizes — but if the same person appears multiple times, the partition is not over independent observations and the null is invalid.

A trajectory embedded as a single point $v_i \in \mathbb{R}^{20}$ represents a multi-year career sequence. If $X_t$ = "individuals observed in wave $t$", then the pooled $\mathcal{X}$ contains up to 14 copies of the same $v_i$. The pool-draw null treats these as independent draws — but they are the same embedded point. The null distribution becomes the distribution of block ratios under random reshuffling of a multiset with heavy duplication, not exchangeability of independent observations.

### D1.2 Current state in v1

- §3.4.1 defines $X_t$ as "annual embedded sub-clouds" without specifying the membership rule.
- §4.3.1 reports sub-sampling at $n = 8{,}000$ per year from sub-clouds of ~9,600 (BHPS) and ~27,200 (USoc).
- The paper never addresses whether individuals appear in multiple $X_t$ or what this means for pool-draw validity.

### D1.3 Classification

**Both** — needs clarification of the construction AND re-design of the pool-draw null.

### D1.4 Three valid designs

The resolution is not a single fix but a choice among three valid sub-cloud constructions, each suited to a different subset of the paper's analyses. **All three will be needed** (Design 1 for pool-draw/spanning, Design 2 for macro-correlations, Design 3 for zigzag/future work).

#### Design 1 — One trajectory per person, entry-cohort assignment

Each individual contributes **exactly one point** to **exactly one** sub-cloud, assigned by **entry cohort**: $X_t = \{v_i : \text{individual } i \text{ first enters the panel with a qualifying trajectory in year } t\}$.

- Each $v_i$ appears in exactly one $X_t$
- $\mathcal{X} = \bigsqcup_t X_t$ is a proper disjoint partition
- Pool-draw independence holds exactly: points are distinct individuals
- Cost: "annual" indexing tracks cohort vintage, not calendar time. $X_{2009}$ = individuals whose USoc trajectory starts in 2009, not a labour-market snapshot
- **Best for:** pool-draw null (era comparison), spanning-individual decomposition

#### Design 2 — Anchor-year assignment (calendar-time indexing without duplication)

Define the **anchor year** of individual $i$ as:

$$t_i^* = \left\lfloor \frac{t_i^{\text{start}} + t_i^{\text{end}}}{2} \right\rfloor$$

Assign $v_i$ to $X_{t_i^*}$ only. This gives each individual a unique sub-cloud assignment based on where their career sits in calendar time, while using the full trajectory embedding. Result: proper disjoint partition, pool-draw null valid.

- Sub-clouds index calendar time (relevant for macro-correlation in §4.4)
- $|X_t|$ varies by year reflecting cohort size and trajectory-length distribution — pool-draw handles variable sizes by design
- **Best for:** §4.4 macro-correlation analysis (topology-vs-macro time series)

#### Design 3 — Trajectory-window slicing with true per-year independence

Embed **sub-trajectories** using a sliding window of length $w$ (e.g., $w = 5$ years). For each individual $i$ and year $t$, embed the trailing window:

$$v_{i,t} = \text{embed}(s_i^{(t-w+1)}, \ldots, s_i^{(t)})$$

using unigram and bigram frequencies of the $w$-year sub-sequence, projected onto the frozen full-sample PCA axes. The recommended $w = 5$ is derived from a formal analysis of four competing constraints (see §D1.5 below).

$$X_t = \{ v_{i,t} : \text{individual } i \text{ observed in years } t{-}w{+}1 \text{ through } t \}$$

- Points are **not** independent across years for the same individual (share $w-1$ overlapping states), but **are** independent across individuals within a year
- Pool-draw null is valid if it shuffles *individuals* (not sub-trajectory observations) across year labels, preserving within-individual autocorrelation
- **Structurally compatible with zigzag persistence** (see §D1.6 below)

### D1.5 Window length $w$: analysis and recommendation

The choice of $w$ is governed by four competing constraints:

**Constraint A — Bigram estimation variance.** A trailing window of length $w$ contains $w - 1$ consecutive state transitions. For rare discriminating bigrams (e.g., $p_{EL \to UL} \approx 0.08$ in R6), individual-level SE is high at small $w$, but the embedding does not need individual bigram precision — it needs PCA projection stability, which exploits covariation across 90 dimensions. Practical PCA-stability lower bound: $w_{\min} \approx 4\text{–}5$. Pushes toward **larger $w$**.

**Constraint B — Temporal sensitivity.** Year-over-year change in the embedding replaces $1/w$ of the window content. Expected year-over-year $W_2$ distance scales as $\mathbb{E}[W_2(X_t, X_{t+1})] \propto \sigma_{\text{traj}} / w$. At $w = 14$ (full window), this is $\approx 1/14$ of cross-sectional spread — below the noise floor. At $w = 5$, it is $1/5$ — detectable. Upper bound: $w_{\max} \approx 7\text{–}8$. Pushes toward **smaller $w$**.

**Constraint C — State space coverage.** Nine states × 81 possible bigrams. At $w = 3$ (2 transitions), most bigram dimensions are structurally zero; PCA on a vector dominated by zeros is unstable. Pushes toward **larger $w$**.

**Constraint D — Sociological interpretability.** Life-course literature uses 3–7 year "career phase" windows (Bukodi & Goldthorpe 2019 use 5-year phases). The 2008 GFC had deepest effects 2008–2012 (4 years). Pushes toward **moderate $w$ of 4–7**.

#### Recommendation: $w = 5$

- **Bigrams:** 4 transitions per individual-year. Individual SE high for rare bigrams, but population-level n-gram frequencies (aggregated across 27,000+ individuals) estimated with negligible error.
- **Temporal sensitivity:** replaces 20% of content annually — sensitive to 3–5 year structural shifts (welfare reform, GFC recovery, pension age changes).
- **State space:** 4 transitions × 9 states = 36 transition slots. Non-zero bigrams are exactly the signal PCA extracts.
- **Sociological:** matches standard career-phase window in UK life-course research.
- **Survey alignment:** annual in both BHPS and USoc; avoids windows spanning the BHPS-USoc transition for most spanning individuals.

#### Required sensitivity analysis: $w \in \{3, 5, 7, 10\}$

The paper must report block-ratio and consecutive-year $W_2$ across $w \in \{3, 5, 7, 10\}$:

| $w$ | Block ratio (BR) | Consec. $W_2$ | Within-BHPS trend $r$ | Zigzag noise (mean bar length) |
|---|---|---|---|---|
| 3 | — | — | — | — |
| 5 | — | — | — | — |
| 7 | — | — | — | — |
| 10 | — | — | — | — |

Expected pattern: (1) BHPS-to-USoc discontinuity present and significant for all $w \geq 3$. (2) Within-BHPS secular trend detectable for $w \leq 7$, disappears at $w = 10$ (Constraint B binding). (3) Zigzag barcode at $w = 3$ shows more topological noise than $w = 5$ (Constraint A binding).

#### BHPS-USoc boundary correction (three components)

At the 2008–2009 boundary, three problems arise under Design 3 with $w = 5$:

**Problem 1 — Mixed-survey bigrams.** A spanning individual at $t = 2009$ has a trailing window 2005–2009: four BHPS-era states and one USoc state. The bigram $s_i^{(2008)} \to s_i^{(2009)}$ crosses the survey boundary. If income measurement is not perfectly harmonised (per D3), this bigram records a partially spurious transition — a measurement jump, not a labour market move.

**Problem 2 — Short windows for newcomers.** USoc newcomers at $t = 2009$ have at most 1 year of data. They cannot construct a full $w = 5$ trailing window. Either they are excluded (losing the newcomer signal) or a shorter window creates a length confound.

**Problem 3 — Asymmetric contamination.** The spanning/newcomer $W_2$ comparison at $t = 2009$ is partially a measurement comparison rather than a frame-composition comparison.

##### Component 1 — Survey-aware bigram masking

Compute bigrams only from **within-survey** consecutive pairs:

$$b_{ab}^{(i,t)} = \mathbf{1}[s_i^{(t-1)} = a,\; s_i^{(t)} = b,\; \text{survey}(t-1) = \text{survey}(t)]$$

The cross-survey transition at $t = 2009$ is excluded from the bigram count; the denominator for bigram frequencies is reduced by 1. Unigram frequencies use all within-window person-years regardless of survey (unigrams don't depend on consecutive-pair measurement consistency).

For a spanning individual at $t = 2009$, $w = 5$:
- Unigrams: 5 person-years (2005–2009), all valid
- Bigrams: 3 within-BHPS transitions (05→06, 06→07, 07→08), 0 cross-survey — effectively $w_{\text{bigram}} = 3$

Cost: bigram frequencies estimated from 3 transitions rather than 4 at boundary years. Benefit: no measurement-change artefacts injected into the embedding.

##### Component 2 — Short-window handling for newcomers

Embed each newcomer using whatever history is available (minimum 1 year). Apply **length-variance standardisation** to bigram frequencies:

$$\tilde{p}_{ab}^{(i,t)} = \frac{\hat{p}_{ab}^{(i,t)}}{\sqrt{\hat{p}_{ab}(1-\hat{p}_{ab}) / (w_{i,t}^{\text{bigram}})}}$$

where $w_{i,t}^{\text{bigram}} \leq w - 1$ is the effective bigram window length. The PCA projection onto frozen loadings places short-window newcomers in the embedding space with appropriately inflated variance.

Supplementary enrichment: some USoc newcomers have prior BHPS records (entered BHPS as household members, not original sample members). Use `xwavedat` linkage to identify these individuals and construct full $w = 5$ windows with survey-aware masking.

For the pool-draw null: shuffling entire individuals (with their window lengths) means the null distribution inherits the same length-variance structure as the observed data. No additional correction needed.

##### Component 3 — Three-version boundary diagnostic

Compare three versions of $X_{2009}$:

- **Version A — Uncorrected:** trailing window ignores survey membership, includes cross-survey bigrams
- **Version B — Corrected:** survey-aware masking + length-standardised newcomers
- **Version C — Spanning-only, full BHPS window:** $X_{2009}$ restricted to spanning individuals, embedded using 2005–2008 BHPS history only (ignoring 2009 USoc observation)

The $W_2$ distances decompose the boundary discontinuity:

$$W_2(\text{A}, \text{B}) = \text{measurement artefact from cross-survey bigrams}$$
$$W_2(\text{B}, \text{C}) = \text{signal from newcomer population addition}$$
$$W_2(\text{A}, \text{C}) = \text{total boundary discontinuity}$$

If $W_2(\text{A}, \text{B})$ dominates: cross-survey bigram contamination is the primary boundary signal → income harmonisation problem is more serious than frame expansion. If $W_2(\text{B}, \text{C})$ dominates: newcomer population is genuinely geometrically distinct → frame expansion interpretation is supported.

This three-way decomposition converts the boundary correction from data cleaning into an **identification result**: it empirically partitions the 2008–2009 discontinuity into measurement and compositional components. Report as a named diagnostic in §4.3.

##### Implementation summary

Four-step procedure applied once, prior to all downstream analyses:

1. **Survey membership tagging.** For each person-year $(i, t)$, record `survey(i,t) ∈ {BHPS, USoc}` from wave identifier in `xwavedat`.
2. **Survey-aware bigram computation.** Compute bigram counts only over consecutive pairs sharing the same survey tag. Record effective bigram window length $w_{i,t}^{\text{bigram}} \leq w - 1$.
3. **Length-variance standardisation.** Apply to bigram frequencies using $w_{i,t}^{\text{bigram}}$; apply standard normalisation to unigrams using full window length $w_{i,t}^{\text{unigram}} \leq w$.
4. **Three-version boundary diagnostic.** For $t = 2009, \ldots, 2009 + w - 2$ (all years within $w - 1$ years of the boundary), compute Versions A, B, C and report the three-way $W_2$ decomposition.

The corrected $32 \times 32$ $W_2$ distance matrix and block ratio should be reported alongside the uncorrected versions. A substantial $\text{BR}$ reduction after correction would indicate the headline finding was partly a measurement artefact — a more troubling but more honest conclusion.

### D1.6 Zigzag compatibility analysis

Zigzag persistence applied to annual sub-clouds uses the union-intersection sequence:

$$X_1 \hookrightarrow X_1 \cup X_2 \hookleftarrow X_2 \hookrightarrow X_2 \cup X_3 \hookleftarrow X_3 \hookrightarrow \cdots$$

The critical requirement is that consecutive sub-clouds share enough geometric proximity for the union complex $K_\varepsilon(X_t \cup X_{t+1})$ to produce non-trivial cross-simplices. If $X_t$ and $X_{t+1}$ share no individuals and are geometrically distant, the zigzag barcode encodes nothing beyond the fact that the two sub-clouds are distinct populations.

**Design 1 — Zigzag incompatible.** Entry-cohort sub-clouds share **no individuals** across consecutive years. The zigzag barcode over entry cohorts answers the wrong question: a bar spanning 1995–2005 means "a feature is present in every entry cohort from 1995 to 2005," not "individuals observed in those years have persistent connectivity."

**Design 2 — Zigzag incompatible with additional artefact.** Anchor-year sub-clouds also share no individuals, and introduce a bimodal artefact at the BHPS-USoc boundary: BHPS respondents spanning 1991–2008 anchor to ~1999, producing almost no BHPS-origin individuals in the 2009 sub-cloud. The zigzag barcode at 2008–2009 shows a dramatic composition change from the anchor distribution, not from the labour market.

**Design 3 — Zigzag structurally correct.** Window slicing produces sub-clouds where $X_t$ and $X_{t+1}$ share a large fraction of individuals (everyone whose window spans both years). The inclusion maps are genuine inclusions of overlapping point sets. Cross-simplices in $K_\varepsilon(X_t \cup X_{t+1})$ form between exiting individuals ($X_t \setminus X_{t+1}$) and entrants ($X_{t+1} \setminus X_t$) when they occupy the same embedding region — capturing **topological continuity through population replacement**. A bar of length $k$ means a topological feature persisted in the embedded sub-cloud for $k$ consecutive calendar years, which is exactly the temporal persistence statement the paper makes.

At the BHPS-USoc transition: spanning individuals appear in both $X_{2008}$ and $X_{2009}$ as the geometrically stable backbone. USoc newcomers enter $X_{2009}$ as genuinely new points. The zigzag barcode encodes whether new topological complexity in 2009 is connected to the pre-existing manifold (continuity) or disconnected (new population). This is exactly the survey-design diagnostic the paper needs.

#### Cross-simplex formation at the 2008–2009 boundary

The union complex $K_\varepsilon(X_{2008} \cup X_{2009})$ contains three kinds of simplices: intra-$X_{2008}$, intra-$X_{2009}$, and **cross-simplices** between exiting points ($X_{2008} \setminus X_{2009}$) and entering points ($X_{2009} \setminus X_{2008}$). Cross-simplices form when $\|v_{i,2008} - v_{j,2009}\| \leq \varepsilon$ — a departing individual's career trajectory resembles an arriving individual's at filtration scale $\varepsilon$. Without cross-simplices, every feature dies at 2008 and is reborn at 2009.

At most year boundaries this is uneventful: departing workers are replaced by demographically similar entrants in nearby embedding positions. At 2008–2009, two distortions intervene:

**Distortion 1 — Newcomer geometric gap.** If USoc newcomers genuinely occupy new embedding regions (as the spanning-individual analysis suggests), cross-simplices between exiting BHPS-era points and entering newcomers **fail to form** at scales $\varepsilon$ that support cross-simplices in other years. Barcode consequence: BHPS-era cluster features **die** at the 2008 union step; newcomer cluster features **are born** at 2009 — short bars spanning only the boundary union step, a signature of population discontinuity.

**Distortion 2 — Measurement jitter.** Income measurement change displaces spanning individuals' embeddings between $X_{2008}$ and $X_{2009}$. For a spanning individual in a stable regime, $\|v_{i,2008} - v_{i,2009}\| > \|v_{i,2008} - v_{i,2007}\|$ due to income band reassignment at the survey transition (concentrated on income-sensitive PCA dimensions). This makes cross-simplex distances at the boundary larger than at other years — even for features representing purely continuing BHPS populations. Barcode consequence: **apparent decrease in feature persistence** at the boundary for income-sensitive features, a measurement artefact masquerading as topological signal.

#### Four bar types in the boundary barcode

| Bar type | Cause | Interpretation |
|---|---|---|
| Long bar crossing 2008–2009 cleanly | Stable BHPS regime cluster replaced by geometrically proximate newcomers | Genuine topological continuity of a career type across eras |
| Bar dying at 2008, new bar born at 2009 | BHPS cluster not replaced by nearby newcomers | Frame expansion — new population type with no BHPS analogue |
| Bar shortening/dying specifically at 2008–2009 despite stable population | Income measurement displacement of spanning individuals | Measurement artefact — removed by boundary correction |
| Very short bars within the 2009 sub-cloud only | Newcomer sub-clusters too small or sparse to persist | Sparse sampling of new population types in year 1 |

**Critical identification problem:** Bar types 2 and 3 produce **identical barcode signatures** (a death at the boundary) but have completely different meanings. Without the survey-aware bigram masking (D1.5 Component 1), they are indistinguishable.

#### What the boundary correction restores

After survey-aware bigram masking: spanning individuals' $v_{i,2008}$ and $v_{i,2009}$ are computed using only within-survey bigrams, eliminating the measurement displacement. The cross-simplex gap now reflects **only** genuine geometric difference between departing BHPS trajectories and arriving newcomers.

Under the corrected embedding, the barcode interpretation becomes clean:
- **Bar crossing 2008–2009** = a career regime cluster with BHPS-era precedent that newcomers continue or approximate
- **Death at 2008 / birth at 2009** = a career regime with no newcomer counterpart, or a genuinely new cluster with no BHPS-era precedent

This is a precise topological statement about the transition: which regime types have continuity of population, and which are discontinued (BHPS-only) or newly introduced (USoc-newcomer). The corrected barcode is **interpretively richer** than the uncorrected one — each bar boundary carries a specific identification meaning.

#### Recommended zigzag reporting at the boundary

Report the zigzag barcode under three conditions:

1. **Uncorrected** — total boundary effect including both distortions (baseline)
2. **Corrected (survey-aware masking)** — removes distortion 2 (measurement jitter), leaving only genuine geometric gaps
3. **Spanning-individuals-only** — sub-cloud restricted to spanning individuals, showing regime continuity maintained by the continuing population alone

The $W_2$ distance between the corrected and spanning-only barcodes quantifies what the paper claims: how much topological novelty at 2009 is attributable to newcomers bringing genuinely new career types, versus measurement noise. This is the barcode-level version of the three-way $W_2$ decomposition in D1.5 Component 3 — together they constitute a complete identification of the 2008–2009 discontinuity's sources.

#### Choosing the filtration scale $\varepsilon^*$ for the cross-simplex diagnostic

The cross-simplex gap is most visible at the scale $\varepsilon^*$ where within-era regime clusters are connected but the cross-boundary gap has not yet been bridged:

$$\varepsilon_{\text{intra}} < \varepsilon^* < \varepsilon_{\text{cross}}$$

where $\varepsilon_{\text{intra}}$ is the scale at which within-era clusters become connected, and $\varepsilon_{\text{cross}}$ is the scale at which cross-simplices finally bridge the boundary gap.

**Estimation of $\varepsilon_{\text{intra}}$.** Approximate from the DBSCAN `eps = 0.5` parameter (within-regime dense cores connected at this scale) and the 75th percentile of pairwise distances $d_{75}$ (filtration threshold). Roughly $\varepsilon_{\text{intra}} \approx 0.4\text{–}0.6 \times d_{75}$.

**Estimation of $\varepsilon_{\text{cross}}$.** The block-ratio cross-era $W_2 = 0.752$ vs within-era $W_2 \approx 0.476$ (ratio $\approx 1.58$) suggests the newcomer population is shifted by $\Delta_{\text{frame}} \approx 0.58 \times \bar{d}_{\text{intra}}$, so $\varepsilon_{\text{cross}} > \varepsilon_{\text{intra}}$ and the diagnostic window is non-trivial.

**Three approaches to choosing $\varepsilon^*$:**

1. **Betti descent knee.** $\varepsilon^*_{\text{knee}} = \arg\max_\varepsilon |d^2 \beta_0 / d\varepsilon^2|$. This is the lower bound of the diagnostic window — right for Betti-based spanning decomposition but suboptimal for cross-simplex gap detection (the gap hasn't been tested at this scale).

2. **Persistence gap scale (RECOMMENDED).** Compute $H_0$ persistence diagram of $K_\varepsilon(X_{2008} \cup X_{2009})$. Identify the feature corresponding to the cross-boundary component merge: born at $\varepsilon_{\text{intra}}$, dies at $\varepsilon_{\text{cross}}$. Set $\varepsilon^*_{\text{gap}} = (\varepsilon_{\text{intra}} + \varepsilon_{\text{cross}}) / 2$. The persistence $\ell_{\text{gap}} = \varepsilon_{\text{cross}} - \varepsilon_{\text{intra}}$ is itself a test statistic: under the pool-draw null it should be near zero; a significantly large $\ell_{\text{gap}}$ is direct evidence of frame expansion, bypassing the block ratio entirely. The ratio $\ell_{\text{gap}}^{\text{obs}} / \bar{\ell}_{\text{gap}}^{\text{null}}$ is a scale-free measure of geometric distinctness.

3. **Wasserstein sensitivity profile.** Compute $f(\varepsilon) = W_2(D_0(X_{2008}; \varepsilon), D_0(X_{2009}; \varepsilon))$ over a grid, subtract the null mean $f_{\text{null}}(\varepsilon)$. Set $\varepsilon^*_{W_2} = \arg\max_\varepsilon [f(\varepsilon) - f_{\text{null}}(\varepsilon)]$. Most computationally expensive (full null battery at each $\varepsilon$) but directly identifies the scale of maximum significance.

**Practical implementation (Approach 2):**

1. Compute $H_0$ persistence diagram of $K_\varepsilon(X_{2008} \cup X_{2009})$ over $\varepsilon \in [0.1 \times d_{75}, 1.0 \times d_{75}]$ in steps of $0.05 \times d_{75}$.
2. Identify the long-lived $H_0$ feature corresponding to the cross-boundary component (largest persistence among features born after $\varepsilon_{\text{knee}}$).
3. Set $\varepsilon^* = (\varepsilon_{\text{intra}} + \varepsilon_{\text{cross}}) / 2$.
4. Report $\ell_{\text{gap}}$ under observed data and pool-draw null.
5. Use $\varepsilon^*$ for the Betti-ratio $\text{BR}^{\text{span}}$ in the spanning-individual decomposition.

$\varepsilon^*$ is a **derived quantity** — computed from the persistence diagram, not chosen by analyst judgment. This removes the kneepoint-detection ambiguity and makes the diagnostic fully reproducible.

#### Figure design: three-barcode comparison for §4.3

**Layout:** 3 × 2 panel grid (rows = Versions A, B, C; columns = H₀, H₁). Total width 140mm (double-column), height ~160mm. Vertical dashed line at 2008–2009 boundary running through all panels.

**H₀ panel content — three layers, not all bars:**

1. **Layer 1 — Regime skeleton (grey, thin).** The $k = 7$ longest-lived H₀ bars (the seven regimes). Stable reference background; regime labels (R1, R2, …) at right terminus.
2. **Layer 2 — Boundary-spanning bars (black, thick).** Bars born before 2009 and dying after 2009. These are cross-simplex-mediated continuities. Annotated with persistence values $\ell = d - b$. Primary comparison layer: Version A fewest (measurement jitter kills some), Version B more (correction restores them), Version C most (no newcomer disruption).
3. **Layer 3 — Boundary-coincident bars (red/dark grey, dashed).** Bars dying within 1 year of 2008 or born within 1 year of 2009. Count annotated in panel margin. Version A most (false deaths); Version B fewer; Version C fewest.

**H₁ panels:** Show all H₁ features as thin bars. If no H₁ bars span the boundary in any version, collapse to a note: "No H₁ features span the 2008–2009 boundary; max H₁ persistence at boundary = [value]."

**Annotations:**

- **Count inset** (upper-right of each H₀ panel): $n_{\text{span}}$ (boundary-spanning bars), $n_{\text{boundary}}$ (deaths/births), mean persistence of spanning bars.
- **Persistence labels** on each Layer 2 bar.
- **$\varepsilon^*$ marker:** horizontal dotted line across all panels at the persistence-gap midpoint, linking the barcode to the $\text{BR}^{\text{span}}$ table.

**Null comparison:** Fourth panel row (or shaded reference band in Version B panel) showing pool-draw null expectation for boundary-spanning bar count and persistence. Observed count above the band = genuine frame-expansion signal; within the band = consistent with random variation.

**X-axis:** Calendar year (not filtration scale $\varepsilon$). Bars extend horizontally across the years they persist. Filtration scale is a secondary dimension shown by the $\varepsilon^*$ reference line.

**Caption template:**

> Figure X. Zigzag H₀ barcodes at the 2008–2009 BHPS-to-USoc boundary under three embedding treatments. Each row: barcode of boundary-adjacent annual sub-clouds ($t \in \{2005, \ldots, 2013\}$) for one version of the trailing-window embedding ($w = 5$). Version A: uncorrected. Version B: boundary-corrected (survey-aware bigram masking, length-standardised newcomers). Version C: spanning individuals only. Vertical dashed line: 2008–2009 survey transition. Thick black bars: H₀ features persisting across the boundary. Dashed red bars: features dying/born within 1 year of transition. Horizontal dotted line: $\varepsilon^*$, persistence-gap midpoint. Comparing A→B isolates measurement artefact ($\Delta n_{\text{span}} = n_{\text{span}}^B - n_{\text{span}}^A$); B→C isolates newcomer composition effect.

**Failure modes to avoid:**

1. Plotting all H₀ bars (thousands of short-lived features → grey rectangle). Use three-layer selection.
2. Filtration scale on x-axis instead of calendar year. Time is the primary axis for the temporal zigzag.
3. No null comparison. Without the null band, the reader cannot assess whether boundary bar counts are extreme.
4. Disconnecting figure from hypothesis tests. Every visual feature maps to a named statistic: $n_{\text{span}}$, $\ell_{\text{gap}}$, $W_2(\text{A}, \text{B})$. Make mappings explicit in caption.

### D1.7 Spanning-individual decomposition under each design

Under Designs 1 and 2, each individual appears in exactly one sub-cloud. "Spanning" must be redefined: individuals whose **assigned sub-cloud falls in $\mathcal{E}_1$** who also have **qualifying observations in $\mathcal{E}_2$**. The near-100% BHPS/spanning overlap (D2) **dissolves** under these designs.

Under Design 3, spanning individuals appear in multiple sub-clouds by construction — the decomposition works naturally as currently written. The overlap problem persists but is reframed: spanning individuals' presence in both eras is informative, not tautological, because their *sub-trajectory embeddings* can differ across eras (a 5-year window centred on 2006 is a different point from a 5-year window centred on 2012 for the same individual).

### D1.8 Recommended design for this paper — REVISED

**Design 3 (window slicing) is the primary design for all analyses.** It is the only construction simultaneously valid for pool-draw, zigzag, spanning decomposition, and macro-correlations.

| Design | Pool-draw | Zigzag | Spanning decomposition | Macro-correlation |
|---|---|---|---|---|
| Design 1 — Entry cohort | ✓ Valid | ✗ Wrong question | ✓ With redefinition | ✗ Not calendar time |
| Design 2 — Anchor year | ✓ Valid | ✗ Bimodal artefact | ✓ With redefinition | ✓ Calendar time |
| **Design 3 — Window slicing** | **✓ Valid (shuffle individuals)** | **✓ Structurally correct** | **✓ Natural** | **✓ Calendar time** |

**Pool-draw under Design 3:** shuffle entire individual trajectories $\{v_{i,t}\}_{t \in \text{window}}$ across year labels, not individual-year observations. Exchangeability operates at the individual level.

**Designs 1 and 2 as robustness checks:** run pool-draw under Design 1 (entry cohort) and report block-ratio comparison. If the block ratio is robust across all three designs, the result is design-independent. Design 2 is a secondary robustness check for the macro-correlations.

### D1.9 Strategy

1. **Audit the codebase** to determine which definition is currently implemented.
2. **Implement Design 3 as the primary construction.** Embed sub-trajectories with trailing window $w = 5$. Define $X_t$ as all individuals with valid observations in years $t{-}4$ through $t$.
3. **Implement survey-aware bigram masking.** Tag person-years by survey; compute bigrams only from within-survey consecutive pairs; apply length-variance standardisation for short-window newcomers.
4. **Run the $w$-sensitivity analysis.** Compute block-ratio and consecutive-year $W_2$ for $w \in \{3, 5, 7, 10\}$. Report the sensitivity table.
5. **Run the three-version boundary diagnostic.** Compute Versions A, B, C of $X_{2009}$ through $X_{2009+w-2}$. Report the $W_2$ decomposition.
6. **Re-run pool-draw null** under Design 3 with individual-level shuffling (corrected embeddings).
7. **Implement Designs 1 and 2 as robustness checks.** Report block-ratio comparison across all three designs.
8. **Document Design 3 formally in §3.4.1** with zigzag compatibility justification, pool-draw exchangeability argument, $w = 5$ derivation, and boundary correction procedure.
9. **Derive the filtration scale $\varepsilon^*$ from the persistence gap.** Compute $H_0$ persistence diagram of $K_\varepsilon(X_{2008} \cup X_{2009})$; identify the cross-boundary merge feature; set $\varepsilon^* = (\varepsilon_{\text{intra}} + \varepsilon_{\text{cross}}) / 2$. Report the gap persistence $\ell_{\text{gap}}$ under observed data and pool-draw null.

### D1.10 Verification

- §3.4.1 defines $X_t$ membership under Design 3 with exchangeability justification, zigzag compatibility argument, $w = 5$ derivation, and boundary correction.
- The pool-draw null uses Design 3 with individual-level shuffling on corrected embeddings.
- The zigzag analysis uses Design 3 sub-clouds with shared individuals across consecutive years.
- The macro-correlation analysis uses Design 3 (calendar-time indexed).
- Block-ratio robustness across Designs 1, 2, and 3 is reported.
- Window-length sensitivity table for $w \in \{3, 5, 7, 10\}$ is reported.
- Three-version boundary diagnostic ($W_2$ decomposition into measurement and compositional components) is reported for $t = 2009, \ldots, 2009 + w - 2$.
- Zigzag barcode at the 2008–2009 boundary is reported under three conditions (uncorrected, corrected, spanning-only) with $W_2$ distances between corrected and spanning-only barcodes.
- Corrected and uncorrected block ratios are both reported.
- Filtration scale $\varepsilon^*$ is derived from the persistence gap (Approach 2), not chosen by analyst judgment.
- The gap persistence $\ell_{\text{gap}}$ is reported under observed data and pool-draw null as a direct frame-expansion statistic.
- The spanning-individual decomposition uses Design 3 with sub-trajectory-level era comparison.

---

## D2 — 99.4% BHPS/spanning overlap collapses the key decomposition [CRITICAL]

### D2.1 The problem

8,459 of 8,509 BHPS-era individuals (99.4%) are also spanning individuals. The "BHPS-era trajectories" and "spanning individuals" are almost the same set. The spanning-individual decomposition — which compares spanning individuals to newcomers — nearly collapses: the BHPS reference population *is* the spanning population.

The reviewer notes this is a highly selected group: people who were in BHPS from the early 1990s and remained through the BHPS-USoc transition into the 2010s+. Finding that "spanning individuals maintain BHPS-like topology" may be tautological: of course long-term survivors maintain stable trajectories.

### D2.2 Current state in v1

- §4.1 states the numbers (8,509 BHPS, 8,459 spanning) without commenting on the near-total overlap.
- §4.3.2 presents the decomposition as if spanning individuals and BHPS-era individuals are meaningfully distinct groups.

### D2.3 Classification

**Prose + analysis** — needs explicit acknowledgment AND analysis of what the overlap means for the decomposition's informativeness.

### D2.4 Strategy

1. **Acknowledge the overlap explicitly in §4.3.2.** State: "99.4% of BHPS-era trajectories correspond to spanning individuals. The BHPS reference and spanning populations are nearly identical by construction, because the continuity filter selects individuals who persisted through the survey transition."
2. **Reframe the decomposition's contribution.** The decomposition is not testing whether "spanning individuals differ from the BHPS reference" (they can't — they *are* the reference). It is testing whether *newcomers* differ from the reference population. This is still informative: the key finding is that newcomers show topological elevation, not that spanning individuals match the baseline.
3. **Discuss the selection implication.** The near-total overlap means spanning individuals are the most stable, most continuously engaged BHPS respondents. Their topological stability in the USoc era may reflect individual-level stability rather than absence of frame effects. Cross-reference with D4 (demographic comparison).
4. **Consider a robustness check.** If any BHPS-only individuals exist (50 people = 8,509 − 8,459), characterise them. Are they qualitatively different? If so, this is informative about selection.
5. **Under Design 3 (primary), the overlap is reframed rather than dissolved.** Spanning individuals appear in multiple sub-clouds by construction, but their *sub-trajectory embeddings* differ across eras: a 5-year window centred on 2006 is a different embedded point from a 5-year window centred on 2012 for the same individual. Their presence in both eras is therefore informative, not tautological — we can ask whether their era-2 sub-trajectory embeddings are topologically similar to their era-1 embeddings. Under Designs 1/2 (robustness checks), the overlap dissolves by construction.

### D2.5 Verification

- §4.3.2 explicitly acknowledges the 99.4% overlap under the full-trajectory construction.
- The decomposition is reframed around the newcomer elevation, not the spanning-individual stability.
- The tautology concern is addressed.
- Under Design 3, the spanning-individual comparison uses sub-trajectory embeddings that differ across eras.
- Under Designs 1/2 (robustness), the overlap is documented as dissolved by construction.

---

## D3 — Income variable identification error: `fihhmnnet1_dv` is individual, not household [CRITICAL]

### D3.1 The problem — three compounding issues

Three distinct but related income measurement problems compound each other:

**Problem 1 — Variable identity.** §5.3 names `fihhmnnet1_dv` as the USoc income variable. This is individual net labour income (employment earnings net of tax and NICs for one person), not household income. The BHPS variable `fihhmn` is net household income aggregated across all household members. These are incommensurable concepts: one measures personal earnings, the other the resources of the household unit.

**Problem 2 — Measurement timing.** BHPS `fihhmn` is a point-in-time annual recall measure collected at the interview date. USoc income is constructed from monthly financial questions across the wave and annualised. A point-in-time annual income and an annualised monthly average respond differently to within-year income volatility — precisely the kind of volatility that defines the churning regimes the paper studies.

**Problem 3 — Threshold calibration.** Income bands (below 60%, 60–120%, above 120% of the contemporary equivalised median) are relativised annually. If the anchor median is drawn from the survey's own continuity-selected sub-sample rather than the national population (HBAI/FRS), the thresholds float with the sample's income distribution, not the national one. "Low income" in 2009 USoc and "low income" in 1995 BHPS are then defined relative to different reference populations.

### D3.2 Current state in v1

- §5.3 (Limitations): "`fihhmnnet1_dv` in USoc; `fihhmn` equivalised by `eq_moecd` in BHPS" — first time USoc variable is named, and only in the limitations section.
- §4.1 of P01-A says "equivalised household income" without naming the variable.

### D3.3 Classification

**Code audit + re-extraction + prose** — potentially the highest-cost fix in the entire revision if the wrong variable was genuinely used. [P01-A SHARED — same as S3]

### D3.4 The correct target variable

The conceptually correct income variable is **net equivalised household income**, derived consistently across both surveys:

$$y_{it} = \frac{\text{total net household income}_{it}}{\text{modified OECD equivalence scale}_{it}}$$

**In USoc:** The correct variable is `fihhmnnet3_dv` — total net household income, derived, monthly — in the `hhresp` file. Includes employment income (all household members), self-employment, benefits/tax credits, pensions, investments. Equivalisation uses `ieqmoecd_dv` (modified OECD scale). Annualise by ×12.

**In BHPS:** `fihhmn` is total net household income monthly. The equivalisation denominator should be computed from household composition variables using the same modified OECD weights (1.0 first adult, 0.5 additional adults, 0.3 children under 14) applied in USoc's `ieqmoecd_dv`.

### D3.5 Five-step harmonisation protocol

**Step 1 — Align the income concept.** Use `fihhmnnet3_dv` (USoc) and `fihhmn` (BHPS), both total net monthly household income. Exclude imputed rental income from both if present, for consistency. Document the exclusion.

**Step 2 — Apply a common equivalisation formula.** Do not use `eq_moecd` (BHPS) and `ieqmoecd_dv` (USoc) as pre-computed scalars — re-derive from raw household composition variables in both surveys using identical formula:

$$\text{scale}_{it} = 1.0 + 0.5 \times (\text{adults}_{it} - 1) + 0.3 \times \text{children under 14}_{it}$$

This eliminates discrepancies between the surveys' derived-variable OECD scale implementations (which differ in their age-boundary treatment for the child weight in some waves).

**Step 3 — Deflate to a common price base.** Both surveys use nominal terms. The annual relativisation (bands relative to contemporary median) partially addresses this. However, the contemporaneous median should be anchored to an **external reference** — the HBAI (Households Below Average Income) survey annual median — rather than the internal sample median. This:
- Prevents continuity-selection bias from distorting the threshold
- Makes the 60% threshold correspond to the official UK relative poverty line
- Ensures comparability with published UK income poverty literature (Jenkins 2011; DWP HBAI series)

HBAI annual equivalised median is publicly available from DWP for 1994/95 onwards; for 1991–1993 approximate from the IFS Living Standards series.

**Step 4 — Handle measurement timing.** BHPS collects income at annual interview (typically Sept–Apr). USoc uses wave-varying approaches. Least-bad solution:
- BHPS: use `fihhmn` directly as annual interview income
- USoc: use wave-specific annual income derived variable, confirmed against wave-specific documentation
- Apply the same annual banding (relative to HBAI-anchored median) to both

This does not eliminate the timing difference but makes it transparent and consistently handled.

**Step 5 — Verify cross-era comparability with a distributional balance test.** For spanning individuals (8,459 in both BHPS and USoc), compare income band distributions in their final BHPS year vs first USoc year. Under genuine harmonisation, the distribution should be approximately stable across the survey transition for this group (same people one year apart). A large distributional shift at 2008–2009 signals residual measurement inconsistency, not labour market change. Test statistic: chi-squared on 3×2 income-band × survey-era table, or Wasserstein distance between income band distributions at $t = 2008$ and $t = 2009$. This applies spanning-individual logic as a *data quality check* prior to the main TDA analysis.

### D3.6 What changes in the analysis if done correctly

**State space stability.** With proper harmonisation, the nine-state crossing (employment × income band) should show similar marginals for spanning individuals across the survey transition. Strengthens the "frame artefact" claim by ruling out measurement-change as alternative explanation.

**Income band thresholds.** Anchoring to HBAI rather than internal sample median will shift some individuals between bands. The 60% threshold from the continuity-selected sub-sample is likely higher in absolute terms than the HBAI-anchored threshold (sample is income-biased upward). Current analysis probably *understates* the proportion of individuals in low-income states; the "Low-Income Churn" regime (R6, 7.6%) may expand.

**Cross-era regime comparison.** With consistent household income and HBAI-anchored thresholds, comparing 7 BHPS-era to 8 USoc-era regimes becomes more meaningful — no longer confounded with the possibility that the state space means different things across surveys.

### D3.7 Irreducible limitations

One limitation is genuinely irreducible: USoc's monthly-average approach introduces regression-to-the-mean in income relative to BHPS's point-in-time snapshot. USoc income distributions will be slightly more compressed than BHPS equivalents even after the above steps. This compression differentially affects classification near the 60% and 120% thresholds. No post-hoc correction fully resolves this. The paper should acknowledge this residual non-comparability as a named limitation with a directional assessment: compression makes USoc individuals near thresholds more likely to be classified in the middle band, potentially *understating* extreme-state trajectories in the USoc era.

### D3.8 Strategy

1. **Audit `trajectory_tda/data/income_band.py`** for the exact variable and equivalisation procedure. [P01-A SHARED]
2. **If `fihhmnnet1_dv` genuinely used:** implement the full five-step protocol above. Re-extract with `fihhmnnet3_dv`. Re-derive equivalisation. Anchor to HBAI. Re-run the full pipeline.
3. **If it's a typo for `fihhmnnet3_dv`:** still implement Steps 2–5 of the protocol (common equivalisation formula, HBAI anchoring, timing documentation, spanning-individual balance test).
4. **State the variable and protocol in §4.1** (P01-B) and the data construction section (P01-A), not in limitations.
5. **Add the Step 5 balance test** as a pre-TDA data quality diagnostic. Report in §4.3 or supplement.

### D3.9 Verification

- §4.1 names the exact USoc income variable (`fihhmnnet3_dv`) and documents the harmonisation protocol.
- The named variable matches the codebase.
- Equivalisation is re-derived from raw composition variables, not imported from pre-computed derived variables.
- Income thresholds are anchored to HBAI annual medians, not the internal sample median.
- The spanning-individual income-band balance test is reported.
- The measurement-timing limitation is named with a directional effect assessment.

---

## D4 — Spanning individuals not demographically compared to newcomers [HIGH]

### D4.1 The problem

The parallel-trends analogy requires that spanning individuals would have shown the same topology as newcomers absent frame effects. The paper provides trajectory-type differences (newcomers have more EL/IH) but not covariate differences (age, gender, education, region). If spanning individuals are systematically older and more established, the finding that "only newcomers show topological elevation" is mechanically guaranteed by compositional differences, not frame effects.

### D4.2 Current state in v1

- §4.3.2 reports trajectory-type differences but no demographic comparisons.
- Already flagged in R1 as ISSUE M4 with a detailed strategy (demographic balance table, propensity-score matching, age-stratified comparison).

### D4.3 Classification

**Already covered by R1 ISSUE M4.** This is the same concern from a different reviewer angle. The D4 framing adds emphasis on the *validation* consequence: if the parallel-trends assumption fails, the framework's primary validation fails.

### D4.4 Strategy

Same as R1 M4 (§10 of existing response plan). Add one element: state in the response that the reviewer's concern is correct that this is a *methodological validation* issue, not just an applied finding issue. The demographic balance check should be presented as a *required component* of the spanning-individual decomposition methodology (§3.4.2), not just an applied check.

### D4.5 Verification

- Same as R1 M4 verification.

---

## D5 — Sub-sampling algorithm unspecified; may bias against newcomers [HIGH]

### D5.1 The problem

Annual sub-clouds are sub-sampled at $n = 8{,}000$. This removes 17% of BHPS observations (9,600 → 8,000) but 71% of USoc observations (27,200 → 8,000). The sub-sampling algorithm (random? stratified? weighted?) is not described. Random sub-sampling from 27,200 USoc observations discards 19,200 individuals per year, including newcomers whose topological elevation drives the key finding. If not stratified by spanning/newcomer status, the annual diagrams may systematically under-represent newcomers.

### D5.2 Current state in v1

- §4.3.1 states "$n = 8{,}000$ per year" without describing the sub-sampling algorithm.

### D5.3 Classification

**Both** — needs documentation AND possibly a stratified-subsampling sensitivity check.

### D5.4 Strategy

1. **Audit the codebase** to determine the sub-sampling algorithm.
2. **Document in §4.3.1:** state whether sub-sampling is simple random, stratified, or weighted.
3. **If simple random:** run a sensitivity check with stratified sub-sampling (proportional representation of spanning/newcomer within each $X_t$). Compare block ratios.
4. **Report both** in Table 3 or supplement.
5. **Justify the $n = 8{,}000$ choice:** is this the BHPS-era sub-cloud size? If so, state: "sub-sampled to $n = 8{,}000$ per year to match the smaller BHPS annual sub-cloud size, ensuring equal representation across eras."

### D5.5 Verification

- §4.3.1 names the sub-sampling algorithm.
- The $n = 8{,}000$ choice is justified.
- If simple random, a stratified sensitivity check is reported.

---

## D6 — Macro-correlation analysis: ecological fallacy, autocorrelation, spurious trends [HIGH]

### D6.1 The problem (three sub-issues)

**(a) Ecological fallacy.** Table 5 correlations are between aggregate annual macro indicators and aggregate annual topological measures ($n = 18$ years). This is ecological correlation, not individual-level association. The paper presents this as "topology tracks structural change" without discussing the ecological inference limitation.

**(b) Autocorrelation.** With 18 observations, effective df is substantially fewer than 16 after accounting for autocorrelation. No Durbin-Watson test or Newey-West SEs reported. BH-FDR correction does not address autocorrelation. At $n = 18$ with autocorrelated series, correlations of $r = 0.80+$ are achievable with any pair of trending variables.

**(c) First-difference null.** The paper reports first-differenced correlations yield no significant associations and interprets this as "topology tracks slow structural change." But the null result is equally consistent with correlations being spurious due to shared trends — the standard critique of levels correlations with non-stationary series. No stationarity tests reported.

### D6.2 Current state in v1

- §4.4: reports levels correlations with BH-FDR only. First-difference null interpreted favourably.
- Already partially flagged in R1 §13.5 (multiple-testing accounting).

### D6.3 Classification

**Both** — needs autocorrelation correction AND prose revisions.

### D6.4 Strategy

1. **Test for stationarity** of both topological time series and macro indicators (ADF or KPSS test, $n = 18$).
2. **Report Durbin-Watson statistics** for each correlation in Table 5.
3. **Apply Newey-West SEs** (or HAC-robust SEs) to the correlations. Re-assess significance.
4. **Acknowledge the ecological fallacy** in §4.4: "These correlations establish covariation between aggregate time series, not between individual-level labour market exposure and individual trajectory complexity."
5. **Reframe the first-difference null result.** Add: "The null first-difference result is also consistent with the levels correlations being driven by shared trends rather than causal structural association. We cannot distinguish these interpretations with $n = 18$ annual observations."
6. **Soften the interpretive claims.** "Topology tracks structural change" → "Topology covaries with structural employment composition at the aggregate level, though the ecological and small-sample nature of this analysis limits causal interpretation."

### D6.5 Verification

- §4.4 reports autocorrelation diagnostics (DW or equivalent).
- Ecological fallacy is acknowledged.
- First-difference null is interpreted symmetrically (slow change vs spurious trends).
- No stationarity test? Then the correlations are explicitly caveated as potentially spurious.

---

## D7 — Deferred data construction: methods paper not self-contained [HIGH]

### D7.1 The problem

The paper defers all data construction to "the companion paper" with only a two-paragraph summary in §4.1. For JRSS-B, the framework's validity is demonstrated on one dataset, and that dataset's properties are established in an unpublished companion. Every data concern from the P01-A review propagates silently into the methods validation. Reviewers will not have access to the companion.

### D7.2 Current state in v1

- §4.1: two paragraphs summarising the data, with "full data construction and embedding details reported in the companion paper."
- The continuity filter, absence of weights, USoc income variable, `jbstat` harmonisation, and household-income-as-individual-income conflation are all inherited.

### D7.3 Classification

**Prose** — §4.1 needs substantial expansion to make the methods paper self-contained on data.

### D7.4 Strategy

1. **Expand §4.1 to ~1 page.** Include: (a) exact selection criteria with sample-size flow diagram; (b) the income variable name and equivalisation procedure; (c) the `jbstat` harmonisation summary; (d) the embedding procedure (n-gram + PCA) in sufficient detail for reproducibility; (e) the survey weight treatment (or justification for not weighting).
2. **Add a data construction supplement section** (§S1) with the full variable-by-variable specification that P01-A's supplement contains. This can be a condensed version, but must be self-contained.
3. **Cross-reference P01-A for full details** but ensure a reviewer who has not read P01-A can still evaluate the methods validation.

### D7.5 Verification

- §4.1 is self-contained: a reviewer can understand the sample construction, variable definitions, and embedding procedure without reading P01-A.
- The supplement contains a data construction section.

---

## D8 — Transportability claims without second-dataset validation [MEDIUM]

### D8.1 The problem

§5.1 asserts transportability to SOEP, PSID, and CNEF without using any of these datasets. For JRSS-B, transportability requires at minimum a demonstration on a second dataset or rigorous theoretical argument about boundary conditions. The reviewer asks: does the framework work when sample size *decreases* at the transition? When spanning individuals are a *small* fraction of era-1?

### D8.2 Current state in v1

- §5.1: entirely speculative transportability discussion.

### D8.3 Classification

**Prose** — either obtain a second dataset or reframe claims.

### D8.4 Strategy

1. **Option A (ideal): Obtain a second dataset.** SOEP or PSID would be natural candidates. Even a small demonstration (pool-draw null on SOEP's 2012 refreshment sample) would substantiate the claims.
2. **Option B (pragmatic): Reframe as methodological discussion, not validation.** Replace "the framework is transportable" with "the framework is designed for settings where..." and explicitly state the boundary conditions: (a) spanning individuals must constitute a non-trivial fraction of both eras; (b) the pool-draw null requires sub-cloud sizes to be comparable or sub-sampling to be applied; (c) the sample-size increase at the transition is the specific case tested here.
3. **Add a boundary-conditions subsection** listing the assumptions under which the framework applies. The reviewer's specific questions (sample-size decrease, small spanning fraction) should be explicitly addressed.

### D8.5 Verification

- §5.1 either demonstrates on a second dataset or explicitly states boundary conditions.
- No unqualified "transportable to SOEP/PSID" claims.

---

## D9 — Sub-sampling discards 71% of USoc observations [MEDIUM]

### D9.1 The problem

Sub-sampling at $n = 8{,}000$ from 27,200 USoc observations discards 19,200 individuals per year, including newcomers. This is related to D5 (algorithm) but distinct: even if the algorithm is correct, the magnitude of the discard is substantial. The reviewer's concern is that the sub-sampled annual diagrams may not represent the full USoc topology.

### D9.2 Strategy

1. **Run the pool-draw analysis at multiple sub-sample sizes:** $n \in \{5{,}000, 8{,}000, 15{,}000\}$. If the block ratio and significance are stable, the sub-sampling is not distorting the result.
2. **Report in supplement** as a sub-sampling sensitivity table.
3. **Note in §4.3.1** that 10 repetitions are used to reduce sub-sampling variance, and report the across-repetition SD of the block ratio.

### D9.3 Verification

- Supplement reports sub-sampling sensitivity.
- §4.3.1 reports across-repetition variability.

---

## D10 — Continuity-filter selection bias inherited from companion [MEDIUM]

### D10.1 The problem

The 10-consecutive-years continuity filter systematically excludes disadvantaged, churning, unstable individuals. All Markov ladder conclusions are conditional on this selected sample. This is the same issue as P01-A S1, but here it affects the *methodological validation* rather than substantive claims.

### D10.2 Current state

Already addressed in the P01-A response plan (S1) with a five-component revised sample construction. For P01-B, the question is whether the Markov ladder and survey-design diagnostics are sensitive to the selection.

### D10.3 Strategy

1. **If P01-A implements the gap-tolerant sample (S1 Component 1):** re-run the Markov-1 and pool-draw tests on the expanded sample and report stability. This is a sensitivity check, not a primary re-analysis.
2. **If P01-A uses Option B (sensitivity-only):** state in §4.1 of P01-B that the sample is continuity-selected, cite the P01-A attrition analysis, and note that the Markov ladder conclusions are conditional on this population.
3. **Add to §5.3 limitations:** "The Markov ladder is validated on a continuity-selected sample. Whether the framework's conclusions generalise to populations with higher attrition and more intermittent observation remains untested."

### D10.4 Verification

- §4.1 or §5.3 explicitly acknowledges the continuity-filter selection.

---

## D11 — Sample size arithmetic: 8,459/8,509 overlap implication [MEDIUM]

### D11.1 The problem

Related to D2 but distinct: the near-total overlap implies the BHPS sample is almost exclusively composed of long-term panel survivors — the most stable subset. This has implications beyond the decomposition: the Markov ladder is validated on this highly selected population. Markov dynamics estimated from the most stable respondents may not represent population-level transition dynamics.

### D11.2 Strategy

1. **Report the overlap fraction explicitly in §4.1.**
2. **Note the selection implication for Markov estimation:** "The Markov transition matrix is estimated from a continuity-selected sample; the one-step transition probabilities may overstate state persistence relative to the population."
3. **Cross-reference with D10** (continuity filter) and D2 (decomposition collapse).

### D11.3 Verification

- §4.1 reports the 8,459/8,509 overlap.
- The implication for Markov estimation is discussed.

---

## Cross-Reference Matrix: Data Reviewer Issues × R1/R2-A/R3 Issues

| Data issue | Interacts with | Nature |
|---|---|---|
| D1 (sub-cloud construction) | R1 M3 (knee algorithm) | Both affect $X_t$ definition |
| D2 (99.4% overlap) | D4, D11 | All concern spanning-individual selection |
| D3 (income variable) | R2-A S3 (income variable), R2-A S12 (BHPS income) | Same variable identification problem |
| D4 (demographic comparison) | R1 M4 (spanning demographics) | Identical concern; R1 plan covers it |
| D5 (sub-sampling algorithm) | D9 | Algorithm + magnitude |
| D6 (macro-correlation) | R1 §13.5 (multiple testing) | R1 covers accounting; D6 adds autocorrelation + ecological fallacy |
| D7 (deferred data) | R2-A S1–S14 (all data issues) | All P01-A data issues propagate here |
| D8 (transportability) | — | New concern specific to JRSS-B |
| D9 (sub-sampling magnitude) | D5 | Related |
| D10 (continuity filter) | R2-A S1 (continuity filter) | Same issue, different paper |
| D11 (overlap arithmetic) | D2 | Related |

---

## Summary Table

| Issue | Severity | Type | §§ affected |
|---|---|---|---|
| D1: Sub-cloud $X_t$ undefined; pool-draw independence violated | **Critical** | Code audit + possible re-design | §3.4.1, §4.3 |
| D2: 99.4% BHPS/spanning overlap collapses decomposition | **Critical** | Prose + analysis | §4.1, §4.3.2 |
| D3: `fihhmnnet1_dv` — wrong income variable | **Critical** | Code audit + possible re-extraction | §5.3, §4.1 |
| D4: Spanning vs newcomer demographics untested | **High** | Covered by R1 M4 | §3.4.2, §4.3.2 |
| D5: Sub-sampling algorithm unspecified | **High** | Code audit + documentation | §4.3.1 |
| D6: Macro-correlations: ecological + autocorrelation + spurious | **High** | Computation + prose | §4.4 |
| D7: Deferred data construction; paper not self-contained | **High** | Prose expansion | §4.1 |
| D8: Transportability claims without second dataset | **Medium** | Prose reframing | §5.1 |
| D9: 71% USoc discard from sub-sampling | **Medium** | Sensitivity check | §4.3.1 |
| D10: Continuity-filter selection inherited | **Medium** | Prose + optional sensitivity | §4.1, §5.3 |
| D11: Sample overlap arithmetic implication | **Medium** | Prose | §4.1 |

---

*End of issue decomposition. To be integrated into the master response plan.*
