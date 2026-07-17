# §4.6 Cluster-Agreement and Uncertainty Additions

This working file covers the §4.6 normalised-ARI rewrite (reviewer issue B9) and the
uncertainty additions to Table 2 (B10, regime-stability SEs) and Table 3 (B11, Wilson
CIs for escape rates). All three are now finalised against committed canonical result
files.

## §4.6 Normalised Cluster Agreement (Sequence Analysis vs GMM)

Optimal-matching sequence analysis (dynamic Hamming distances, Lesnard 2010; Ward
linkage) and the GMM regime model offer two independent partitions of the same 27,280
trajectories. Cutting the optimal-matching dendrogram at $k = 7$ and comparing with the
seven GMM regimes gives a raw adjusted Rand index of 0.2611.

That raw value understates agreement because the two partitions impose different
cluster-size margins (optimal-matching cluster sizes ranging from 1,775 to 9,003; GMM
regimes from 1,813 to 7,358), and an exact match across mismatched margins is impossible.
The maximum ARI achievable under the fixed margins is therefore well below one. Because
that maximum is the solution to an NP-hard assignment problem with no exact solver
available in the locked environment, it is certified as a bracket rather than a point: a
constructive feasible table attains ARI 0.8397 (a rigorous lower bound on the maximum),
and a per-line concentration relaxation gives a rigorous upper bound of 0.8607, so the
achievable maximum lies in $[0.8397, 0.8607]$.

Normalising the observed agreement against this achievable maximum gives a normalised ARI
of 0.31 — the optimal-matching and GMM partitions agree at about 31% of the agreement
attainable given their cluster-size structure. The achievable-maximum bracket propagates
to a normalised-ARI bracket of $[0.3035, 0.3111]$, and the raw-ARI bootstrap interval
rescaled by the achievable maximum gives a normalised 95% CI of $[0.3030, 0.3195]$. The
achievable maximum is a certified bracket, not an exact value, so the normalised figure is
reported with its bracket rather than as a single exact number.

Inferential support is clear. Against a cluster-size-preserving permutation null
($B = 5{,}000$, GMM labels permuted relative to the fixed optimal-matching labels), the
null ARI is centred at zero with standard error $5.80\times10^{-4}$, and no permutation
reaches the observed value (upper-tail $p = 2.0\times10^{-4}$). An individual-level
bootstrap ($B = 1{,}000$) places a 95% interval of $[0.2544, 0.2683]$ around the raw ARI.
(The reviewer's response plan anticipated a null standard error near 0.009; the empirical
permutation null is legitimately tighter, and the tighter $5.80\times10^{-4}$ is reported
rather than the looser hand-estimate.)

The interpretation is deliberately narrow. This is a descriptive clustering-agreement
statistic: it quantifies how far two partitions of the same trajectories coincide,
normalised for the structural ceiling their cluster-size margins impose. It carries no
causal claim and no claim that either method uniquely identifies the regimes. It closes
the reviewer's request for a normalised, null-tested, interval-bearing ARI; it does not
upgrade the substantive claim.

## Table 2 — Regime stability with uncertainty (reviewer issue B10)

The v1 Table 2 stability column reports the window-pair regime-stickiness metric
(`stability_stored`). Per-regime standard errors and Wilson 95% confidence intervals for
that headline metric are now reported. Each SE is $\sqrt{p(1-p)/n_\text{members}}$ on the
stored proportion, paired with a Wilson score interval on the same proportion.

**Table 2 (augmented) — Seven Mobility Regimes, stability with uncertainty** *(provisional label; final table number set at v2 assembly)*

| Regime | Name | *n* | Stability (stored) | SE | Wilson 95% CI |
|---|---|---:|---:|---:|---|
| R1 | Secure High-Employment | 7,358 | 0.7795 | 0.0048 | [0.7699, 0.7888] |
| R2 | Inactive Low | 5,415 | 0.3865 | 0.0066 | [0.3736, 0.3995] |
| R0 | Mixed Churn | 3,787 | 0.2341 | 0.0069 | [0.2209, 0.2479] |
| R4 | Employed Mid | 3,510 | 0.4075 | 0.0083 | [0.3914, 0.4238] |
| R3 | Employment–Inactive Mix | 3,333 | 0.2797 | 0.0078 | [0.2647, 0.2952] |
| R6 | Low-Income Churn | 2,064 | 0.2891 | 0.0100 | [0.2699, 0.3090] |
| R5 | High-Income Inactive | 1,813 | 0.4003 | 0.0115 | [0.3780, 0.4230] |

The headline denominator is $n_\text{members}$ (one observation per individual in the
regime). A tighter window-pair-denominator alternative — using the regime's window-pair
transition count rather than its member count — is available in the result file for
transparency, but the member-count denominator is the headline.

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

### Provenance status

All three uncertainty items are now closed against committed canonical files:

1. **§4.6 (B9):** finalised against the optimal-matching-vs-GMM normalised ARI
   (`ari_om_gmm_normalised_2026-06-24.json`; raw 0.2611, normalised 0.31 with achievable
   maximum certified as the bracket $[0.8397, 0.8607]$). The earlier H₀-vs-GMM material —
   a different object — is removed.
2. **Table 2 (B10):** headline stored-metric SE/Wilson CI populated from
   `stability_se_stored_2026-06-22.json` (denominator $n_\text{members}$).
3. **Table 3 (B11):** Wilson CIs from `escape_wilson_ci_2026-05-16.json`.
