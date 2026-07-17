<!--
EDITORIAL STATUS (provisional — awaiting User per-section review)
- Numbers traced to:
    results/trajectory_tda_integration/stage1/dedup_amendment_comparison_2026-05-31.json  (H1 length-matched; Outcome A)
    results/trajectory_tda_bhps/diagnostics/markov1_calibration_2026-06-21.json            (calibrated flag, ks_p, mean_pvalue, verdict)
    results/trajectory_tda_bhps/diagnostics/markov1_nullnull_variance_2026-06-21.json      (bhps/usoc null-null CV, variance_flag)
    results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_2026-06-09.json   (non-overlap / matched-landmark-fraction sensitivity)
    papers/shared/income_concept_audit.md                                                  (spanning-individual count)
- The BHPS-era headline magnitudes carried from v1 (order-shuffle / Markov-1 H0 obs-null vs
  null-null W2, k=8 BIC, regime stabilities) live in bhps_headline_frozen_2026-05-28.json,
  which is NOT one of this task's named files; they are referenced qualitatively here and
  flagged for exact reconciliation at v2 assembly rather than re-quoted.
- "Replication" language removed throughout per Spec S10 (robustness / consistency check).
- Table/figure callouts provisional; final numbers at v2 assembly. Awaiting User review.
-->

### 6.2 BHPS-Era Cross-Era Robustness Analysis (1991–2008)

The 8,509 BHPS-era trajectories provide a cross-era robustness check: they test whether
the regime structure and topological findings established on Understanding Society hold in
a different labour-market epoch. This is a consistency analysis across eras, not a
validation of the testing methodology — that is developed in the companion paper P01-B —
and it is not a replication study in the confirmatory sense. The BHPS-era regime typology
is broadly comparable to the USoc typology (with one additional BIC-selected regime), and
the BHPS-era order-shuffle and Markov-1 $H_0$ null tests reject in the same direction as
USoc; these headline figures are carried from the cross-era headline battery and
reconciled at final assembly. This section reports three targeted robustness results — the
length-matched $H_1$ analysis, the BHPS Markov-1 null-credibility diagnostic, and the
non-overlap sensitivity analysis — that qualify and sharpen the cross-era reading.

#### The $H_1$ cross-era asymmetry is not an observation-window artefact

The BHPS-era trajectories reject the Markov-1 $H_1$ null under $W_2$ testing, whereas the
same test is borderline in the shorter USoc panel. Because BHPS trajectories are observed
over a longer mean horizon than USoc, an obvious concern is that this $H_1$ asymmetry
merely reflects the longer observation window rather than a genuine difference in cycling
structure. We tested this directly by length-matching the BHPS sample to the USoc horizon
(approximately thirteen waves) under two strategies — truncation to the first thirteen
waves, and restriction to individuals observed for at least thirteen waves — both under
frozen loadings and external-indexing landmark de-duplication. Both strategies reject the
$H_1$ $W_2$ null at $\alpha = 0.05$ ($p = 0.001$ each, the resolution floor at $B = 1000$),
and both reject $H_0$ ($p = 0.001$). The $H_1$ cross-era asymmetry therefore survives
length-matching to the USoc horizon: it is not an artefact of the longer BHPS observation
window.

This conclusion depends on a de-duplication step whose effect is mechanistic rather than a
tuning choice. Without de-duplication, the truncated $H_1$ $W_2$ test does not reject
($p = 0.350$): approximately 139 near-zero-scale phantom $H_1$ features, produced by
numerical near-duplicate landmarks in the embedding, inflate the observed-to-null and
null-to-null $W_2$ distances by the same large factor, so the observed diagram looks
statistically indistinguishable from its null (mean observed-to-null over mean
null-to-null $= 1.006$). External de-duplication of the observed landmark sample — which
the Markov-1 surrogates do not require, because they do not reproduce the near-duplicate
structure — strips the phantoms and exposes the underlying signal (ratio $= 1.87$;
$p = 0.001$). Two robustness probes (forcing symmetric de-duplication of the nulls, and
pinning the filtration threshold) preserve the rejection in every cell. The observation-window
confound is therefore resolved rather than left as an open question.

#### The BHPS Markov-1 null is anti-conservative (credibility diagnostic)

The cross-era Markov-1 rejections must be read against a diagnostic of whether the BHPS
Markov-1 null is itself well-calibrated. Two diagnostics were run. First, a calibration
double-null test asks whether $p$-values computed from one Markov-1 surrogate against a
bank of others are uniformly distributed, as a valid null requires. They are not: the
distribution is strongly non-uniform (Kolmogorov–Smirnov $p = 1.3 \times 10^{-14}$;
calibration flag negative), and the mean double-null $p$-value is $0.40$, below the $0.50$
expected under a calibrated test — the signature of a null that rejects too readily, i.e.
is anti-conservative. Second, a null-null variance diagnostic comparing the BHPS and USoc
null-to-null coefficients of variation does not flag a problem (BHPS CV $= 0.309$, USoc
CV $= 0.265$; the flag rule requires the BHPS CV to fall below half the USoc CV, which it
does not). The combined verdict is *suspect*: the BHPS Markov-1 null is insufficiently
stringent for BHPS $H_0$, driven by the calibration failure rather than by variance
collapse.

The consequence is reported honestly rather than asserted away. Every BHPS Markov-1
rejection in this section — including the length-matched $H_1$ result above — carries this
anti-conservative-null caveat: the diagnostic outcome (a non-uniform calibration
double-null) is the evidence, and we do not claim the BHPS Markov-1 discrimination is fully
credible on the strength of the rejection alone. The USoc results, whose null is not
flagged by this diagnostic, are not affected. Formal, better-calibrated cross-era testing
is the province of the companion methods paper.

#### Non-overlap sensitivity: the $H_1$ signal is landmark-fraction-sensitive

A distinct concern is that the cross-era comparison is contaminated by individuals who span
both surveys, and that the $H_1$ result depends on the landmark fraction (the ratio of
retained landmarks to sample size). The harmonised data contain 10,992 individuals spanning
the BHPS and USoc eras (10,544 with valid income in both waves). We re-ran the cross-era
comparison excluding these spanning individuals and, separately, holding the landmark
fraction fixed at the matched value ($0.588$) across twenty independently drawn subsamples
($n = 3{,}202$ each).

The two homology degrees behave differently under this sensitivity, and the two metrics
diverge. The $H_0$ $W_2$ signal is robust: it rejects in the spanning-excluded sample
($p = 0.001$) and in all twenty landmark-fraction-matched subsamples. The $H_1$ $W_2$
rejection is not robust: it disappears once spanning individuals are excluded
($p = 0.221$) and rejects in none of the twenty matched subsamples, while the persistence-
landscape $L^2$ complement continues to reject $H_1$ throughout (spanning-excluded
$p = 0.020$; twenty of twenty matched subsamples). The BHPS-era $H_1$ $W_2$ rejection is
therefore sensitive to sample size and landmark fraction — the size/landmark-fraction
artefact — and is reported as metric-dependent under this sensitivity, whereas the $H_0$
cross-era finding is stable. Taken together with the length-matched result and the
credibility diagnostic, the cross-era $H_1$ claim is stated with these three qualifications
attached rather than as an unconditional finding; the robust cross-era result is the $H_0$
regime-structure consistency.

[Figure 14: Cross-era robustness — length-matched $H_1$, credibility diagnostic, and non-overlap sensitivity]
