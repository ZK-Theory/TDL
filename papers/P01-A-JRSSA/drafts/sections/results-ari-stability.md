# §4.6 Cluster-Agreement and Uncertainty Additions

This working file covers the §4.6 normalised-ARI rewrite (reviewer issue B9) and the
uncertainty additions to Table 2 (B10, regime-stability SEs) and Table 3 (B11, Wilson
CIs for escape rates). Two of the three deliverables hit provenance limits in the
committed result files; these are flagged inline and summarised at the foot of the file.

## §4.6 Normalised Cluster Agreement

The seven GMM regimes are density modes in the embedding, while $H_0$ persistent
homology partitions the same point cloud by connectivity. A descriptive agreement
statistic quantifies how far the two partitions coincide. Computed against the
canonical embedding and GMM labels (n = 27,280), the $H_0$ connected-component
partition of the radius-neighbours graph at $\varepsilon^\ast = 0.54$ contains 11,315
components — 10,183 of them singletons and 1,132 non-singleton — against the seven GMM
regimes. The raw adjusted Rand index between the two partitions is 0.2425.

That raw value is structurally bounded and must be normalised before it is interpreted.
Because the two partitions have radically different granularity (11,315 versus seven
groups), the fixed-margin maximum achievable ARI is itself only 0.2425 (exact
fixed-margin packing: all 1,132 non-singleton components map whole into the seven GMM
column margins, none split). The observed value therefore attains essentially the entire
achievable ceiling, giving a normalised ARI of 0.99999. Against a label-permutation null
(B = 5,000, GMM labels permuted relative to fixed $H_0$ labels), the null ARI is centred
at zero (mean $3.79\times10^{-6}$, SE $3.48\times10^{-4}$) with no permutation reaching
the observed value (bias-corrected upper-tail p = 0.0001999600). An individual-level
bootstrap (B = 1,000) places a 95% interval of [0.2370, 0.2485] around the raw statistic
(bootstrap mean 0.2428, SE 0.0030).

The interpretation is deliberately narrow. This is a descriptive agreement statistic:
within the structural ceiling imposed by the granularity mismatch, the non-singleton
$H_0$ components align with the GMM regimes about as closely as the fixed margins allow,
and the agreement is far above chance. It carries no causal claim and no claim that the
topology uniquely identifies the regimes; the near-unity normalised value is partly a
mechanical consequence of the singleton-dominated $H_0$ partition, in which singletons
can be absorbed into any margin. It is reported to replace the un-normalised raw ARI that
a reviewer flagged, not to upgrade the substantive claim.

> **[DRAFTING NOTE — comparison-target mismatch, needs Manager/User resolution.]** The
> v1 §4.6 ("Sequence Analysis Comparison") and reviewer issue B9 concern the ARI of
> **0.26 between optimal-matching (sequence-analysis) k = 7 clusters and the GMM k = 7
> regimes** — a *different* comparison from the one the only committed normalised-ARI file
> (`results/panel_methodology/ari/ari_normalised_2026-06-06.json`) computes, which is
> **$H_0$ connected-components vs GMM**. The committed file does not normalise the
> optimal-matching-vs-GMM ARI (the response plan anticipated a null SE of ~0.009 for that
> k7-vs-k7 comparison; the committed $H_0$-vs-GMM null SE is 0.000348, confirming a
> different object). **Decision needed:** either (a) §4.6 is reframed to report the
> $H_0$-vs-GMM normalised agreement above (B9 closed via this file), with the
> optimal-matching comparison retained descriptively or dropped; or (b) a normalised-ARI
> computation for optimal-matching k7 vs GMM k7 is still required to close B9 as written.
> No optimal-matching-vs-GMM normalised-ARI result is committed under `results/`.

## Table 2 — Regime stability with uncertainty (reviewer issue B10)

The v1 Table 2 stability column reports the **window-pair regime-stickiness** metric
(`stability_stored`): R1 0.779, R5 0.400, R4 0.408, R2 0.387, R6 0.289, R3 0.280,
R0 0.234. The committed uncertainty file `stability_se_2026-05-16.json` confirms these
point estimates but provides per-regime standard errors **only for a different metric** —
the within-trajectory state-stickiness measure (`stability_from_seqs`), which the file
itself designates "diagnostic comparison only — not for headline reporting." The
window-pair stored metric used in Table 2 has no committed SE (its window-pair transition
denominator is not in the file). The augmented table below therefore reports the canonical
stored point estimate alongside the available diagnostic `stability_from_seqs` ± SE, with
the headline-metric SE marked pending regeneration.

**Table 2 (augmented) — Seven Mobility Regimes, stability with uncertainty** *(provisional label; final table number set at v2 assembly)*

| Regime | Name | *n* | Stability (stored, headline) | Headline SE | Within-trajectory stickiness ± SE [95% CI] (diagnostic) |
|---|---|---:|---:|---|---|
| R1 | Secure High-Employment | 7,358 | 0.7795 | pending¹ | 0.8437 ± 0.0012 [0.8413, 0.8461] |
| R2 | Inactive Low | 5,415 | 0.3865 | pending¹ | 0.7498 ± 0.0017 [0.7464, 0.7532] |
| R0 | Mixed Churn | 3,787 | 0.2341 | pending¹ | 0.5148 ± 0.0024 [0.5101, 0.5194] |
| R4 | Employed Mid | 3,510 | 0.4075 | pending¹ | 0.6317 ± 0.0023 [0.6271, 0.6363] |
| R3 | Employment–Inactive Mix | 3,333 | 0.2797 | pending¹ | 0.5532 ± 0.0025 [0.5483, 0.5581] |
| R6 | Low-Income Churn | 2,064 | 0.2891 | pending¹ | 0.6497 ± 0.0030 [0.6438, 0.6557] |
| R5 | High-Income Inactive | 1,813 | 0.4003 | pending¹ | 0.6828 ± 0.0031 [0.6766, 0.6889] |

¹ SE for the headline window-pair stored-stability metric is not in the committed
`stability_se_2026-05-16.json` (which reports SEs for the within-trajectory metric only).
Closing B10 as written ("Table 2 has stability ± SE" for the headline metric) requires a
regeneration pass that computes $\sqrt{p(1-p)/n_\text{window-pairs}}$ for the stored
metric — flagged for the Manager.

## Table 3 — Escape rates with Wilson 95% CIs (reviewer issue B11)

Cleanly supported by `escape_wilson_ci_2026-05-16.json`. Every escape rate now carries a
Wilson 95% interval; the retirement-age rate in particular spans a wide relative range, as
the reviewer noted.

**Table 3 (augmented) — Escape Rates from Disadvantaged Regimes** *(provisional label; final table number set at v2 assembly)*

| Group | *n* (disadvantaged start) | Escaped | Escape rate | Wilson 95% CI |
|---|---:|---:|---:|---|
| Overall | 7,453 | 416 | 5.58% | [5.08%, 6.13%] |
| Working-age (< 60) | 2,163 | 386 | 17.85% | [16.29%, 19.52%] |
| Retirement-age (≥ 60) | 5,978 | 6 | 0.10% | [0.05%, 0.22%] |

---

### Open provenance items (surfaced for review)

1. **§4.6 (B9):** the committed normalised-ARI file is $H_0$-vs-GMM, not the
   optimal-matching-vs-GMM ARI (0.26) the section/issue concerns. Reframe §4.6 to the
   $H_0$-vs-GMM result, or commission the optimal-matching normalisation. **Blocks a clean
   B9 closure.**
2. **Table 2 (B10):** committed SEs are for the diagnostic within-trajectory metric, not
   the headline window-pair stored metric. A stored-metric SE regeneration is needed to
   close B10 as written.
3. **Table 3 (B11):** complete and clean.
