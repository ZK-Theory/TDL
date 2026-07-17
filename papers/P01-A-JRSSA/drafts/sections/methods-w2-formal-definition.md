<!--
Target location in v2: §3.3 (Null-Model Testing) — replaces the brief mention of
"Wasserstein $W_2$ diagram distances" with a formal definition block plus the
permutation p-value formula.

Evidence sources verified during drafting:
  • `trajectory_tda/topology/vectorisation.py` lines 180–232 — function
    `compute_wasserstein(ph1, ph2, dim, p=2, ...)` calls
    `gudhi.wasserstein.wasserstein_distance(dgm1, dgm2, order=p, internal_p=2)`
    with default `p = 2`.
  • `trajectory_tda/scripts/run_stage1_battery.py` line 466 — canonical
    headline $W_2$ p-value `w2_pvalue = (_r_w2 + 1) / (_n_w2 + 1)` (Edgington
    form, locked by the T1.1 pre-registration 2026-05-13).
  • `trajectory_tda/scripts/run_stage1_battery.py` line 486 — companion
    landscape $L^2$ p-value `land_pvalue = (_r_land + 1) / (_n_land + 1)`
    using the same Edgington form.
  • `papers/shared/notation.md` — $W_p$ ground-metric convention (Euclidean on
    the birth–death plane); `papers/P01-A-JRSSA/drafts/v1-2026-04.md` §3.3 is
    the paragraph this block expands.

Locked external references: Cohen-Steiner, Edelsbrunner & Harer (2007),
*Discrete & Computational Geometry* 37(1) — already cited in v1.

Note on legacy code path: the older `permutation_test_trajectories`
function in `trajectory_tda/topology/permutation_nulls.py` computed the
$p$-value as the raw empirical fraction (no $+ 1$ adjustment). That path
is being retired by T0.12 (Stage-1 phase-split, in progress on branch
`pipe/stage1-phase-split`); a one-sentence footnote in Supplement §S0
flags any table that still consumes legacy post-audit JSON output.
-->

## §3.3 amendment — Formal definition of the Wasserstein diagram distance

For persistence diagrams $D_1$ and $D_2$ in homology degree $q$, the order-$p$
Wasserstein distance is

$$
W_p(D_1, D_2) \;=\; \inf_{\gamma}\Bigg( \sum_{x \in D_1 \cup \Delta}
  \lVert x - \gamma(x) \rVert_2^{\,p} \Bigg)^{1/p},
$$

where $\Delta = \{(t, t) : t \in \mathbb{R}\}$ denotes the diagonal and
$\gamma$ ranges over bijections between $D_1 \cup \Delta$ and $D_2 \cup \Delta$.
Off-diagonal points $(b, d)$ that are matched to the diagonal contribute
distance $(d - b)/\sqrt{2}$, the orthogonal projection cost; this is the unique
diagonal-projection rule that preserves stability of $W_p$ under the $\ell^2$
ground metric on the birth–death plane (Cohen-Steiner, Edelsbrunner & Harer,
2007). We fix $p = 2$ throughout, in accordance with the shared notation
standard (Appendix A, $W_p$ entry).

Computation uses the optimal-transport implementation in
`gudhi.wasserstein.wasserstein_distance` with arguments `order = 2` and
`internal_p = 2` (GUDHI ≥ 3.7; Maria et al., 2014); the wrapping function
`compute_wasserstein` in `trajectory_tda/topology/vectorisation.py` returns the
floating-point distance for two `PHResult` objects at the requested dimension.
Infinite features are excluded before the call; an empty diagram contributes
the diagonal-projection cost of its counterpart, i.e.
$\left(\sum_{i}((d_i - b_i)/\sqrt{2})^{\,p}\right)^{1/p}$.

For permutation inference we compute, for each null draw
$j = 1, \ldots, B$, the diagram $D^{(j)}_{\text{null}}$ on the same landmark
budget as the observed diagram $D_{\text{obs}}$, store
$W_2(D_{\text{obs}}, D^{(j)}_{\text{null}})$, and subsample
$N_{\text{pairs}} = \min(500,\, B(B - 1)/2)$ distinct pairs
$(j, j')$ to form the null-null reference distribution
$\{W_2(D^{(j)}_{\text{null}}, D^{(j')}_{\text{null}})\}$. The one-sided upper-tail
$p$-value uses the Edgington form

$$
\hat p \;=\; \frac{1 + \big| \big\{(j, j') :
W_2\big(D^{(j)}_{\text{null}}, D^{(j')}_{\text{null}}\big)
\;\ge\;
\overline{W_2}\big(D_{\text{obs}}, D^{(j)}_{\text{null}}\big)
\big\}\big|}{1 + N_{\text{pairs}}},
$$

where $\overline{W_2}(D_{\text{obs}}, \{D^{(j)}_{\text{null}}\})$ is the mean
across the $B$ obs-null distances. This is the formula locked by the T1.1
pre-registration (2026-05-13) and implemented at
`trajectory_tda/scripts/run_stage1_battery.py:466` for $W_2$ and at line 486
for the companion persistence-landscape $L^2$ p-value. The $+ 1$ adjustment
puts the resolution floor at $1 / (1 + N_{\text{pairs}}) \approx 0.002$ for
$N_{\text{pairs}} = 500$ and is preferred to the raw empirical fraction
because it gives a proper $p$-value under exchangeability without the
zero-floor pathology. The permutation algorithm, seed schedule, and landmark
protocol are specified in Supplement §S0; numerical values appear in §4.3
and §6.2.
