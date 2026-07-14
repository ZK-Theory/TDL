# §3.1 Persistent Homology Setup: Filtration, Ground Metric, and Homological Restriction

This working file rewrites §3.1 (VR/witness filtration construction, ground-metric formula,
and the restriction to $H_0/H_1$). It corrects the ground-metric error in v1 (ISSUE H1),
adds the missing filtration-truncation justification (ISSUE M2), and reframes the
$H_0/H_1$ restriction as a disclosed limitation rather than a one-sentence dismissal
(ISSUE L1, per the 2026-06-19 terminal lock — see below). It supersedes v1 §3.1 in full.

## Setup and notation

We follow the notation of `papers/shared/notation.md`. Let $X \subset \mathbb{R}^d$ denote
the embedded trajectory point cloud: sequences of employment/income states are mapped to
$v_i \in \mathbb{R}^d$ via n-gram frequency vectors projected onto PCA axes fitted once on
the full pooled sample and applied without re-fitting to any sub-selection (frozen
loadings), giving a common coordinate system across all temporal slices, null-model
surrogates, and subgroups. In this application $\mathcal{S}$ has nine states (employment
status $\times$ income band), the retained embedding dimension is $d = 20$, and
$T_i \in [10, 18]$ (BHPS) or $T_i \in [10, 14]$ (USoc). For a cohort- or time-indexed
sub-population, $X_t \subset X$ denotes the corresponding sub-cloud.

## Persistent homology construction: landmark-witness complex, maxmin-VR cross-check

Persistent homology is computed not on the raw point cloud $X$ but on a landmark
subsample, selected once per cloud by the greedy maxmin procedure: starting from a
seeded point, each successive landmark is the point farthest (Euclidean) from the current
landmark set, until $n_\ell = \min(L, |X|)$ landmarks are chosen ($L = 5{,}000$ throughout
the matched-landmark headline analyses; seed 42).

Two complementary complexes are built on this landmark set (`trajectory_tda/topology/trajectory_ph.py`):

- **Landmark witness complex (primary).** Following `gudhi.EuclideanStrongWitnessComplex`,
  the landmarks define the simplex vertices and the full point cloud furnishes witnesses
  that certify simplex membership: a simplex is admitted once some witness's squared
  distance to every one of its landmark vertices falls within the filtration parameter
  $\alpha$. Persistence is computed in homological degrees $q \in \{0, 1\}$
  (`limit_dimension = max_dim + 1`, `max_dim = 1`).
- **Maxmin Vietoris-Rips (cross-check).** The same landmark set is used to build the
  Vietoris-Rips complex $K_\varepsilon(Y) = \{[y_0,\ldots,y_k] : \|y_i - y_j\| \le
  \varepsilon\ \forall i,j\}$ directly via `ripser`, with $\varepsilon$ unbounded (full
  filtration to the sample diameter). This is used to validate the witness-complex $H_0$
  and $H_1$ diagrams, not as the reported construction.

### Truncation of the filtration

The witness complex is not built to the full filtration range: the filtration parameter
$\alpha$ (`max_alpha_square`) is capped at
$$
\alpha_{\max} = \min\!\left(10.0,\; Q_{0.95}\!\left(\{\min_{\ell \in \mathrm{L}} \|w - \ell\|^2 : w \in X\}\right)\right),
$$
the 95th percentile of the squared distance from each witness to its nearest landmark,
computed per point cloud. This truncation is necessary for tractability at $L = 5{,}000$
landmarks and is not currently swept as a sensitivity parameter in the committed pipeline;
no threshold-sensitivity result file exists at the time of this rewrite, so we do not claim
a validated stability range and flag this as an open robustness item (see Issues below)
rather than asserting one.

The truncation is justified qualitatively by the embedding's dimensionality. Intrinsic
dimension was estimated on both frozen embeddings (`intrinsic_dim_2026-05-24.json`,
seed 42, TwoNN per Facco et al. 2017 and MLE per Levina & Bickel 2004): on the full
embedding, USoc gives TwoNN $\hat{d} = 3.59$ / MLE $\hat{d} = 5.80$, and BHPS gives TwoNN
$\hat{d} = 3.77$ / MLE $\hat{d} = 6.30$, against an ambient dimension of $d = 20$; both
datasets are flagged **over-dimensional** (`diagnostic_verdict = "OVER-DIMENSIONAL"`,
following Damrich, Berens & Kobak 2024 on VR-persistent-homology failure modes at high
ambient dimension relative to intrinsic dimension). A large gap between ambient and
intrinsic dimension is the standard rationale for restricting the filtration to a bounded
neighbourhood scale rather than the full pairwise-distance range: at $d_{\mathrm{ambient}}
= 20$ against an intrinsic dimension of order 4–6, the volume of the ambient space at large
$\varepsilon$ is dominated by noise directions the data does not occupy, so a percentile-based
cap on witness-to-landmark distance concentrates the filtration budget on the scales at which
the intrinsic structure lives.

## Ground metric and Wasserstein distance (corrects ISSUE H1)

For a point cloud $Y$, persistent homology of the filtration above produces, in degree $q$,
a persistence diagram $D_q(Y)$: a multiset of birth-death pairs $(b_i, d_i) \in
\mathbb{R}^2_{b<d}$. We write $D_q^{\mathrm{obs}}$ for the diagram computed on observed data
and $D_q^{\mathrm{null}}$ for a diagram computed on a null-model surrogate (§3.2).

The $p$-Wasserstein distance between diagrams $D$ and $D'$ is
$$
W_p(D, D') = \left(\inf_{\gamma:\, D \to D'} \sum_i \|x_i - \gamma(x_i)\|_2^p\right)^{1/p},
$$
where the infimum ranges over all bijections $\gamma$ between $D \cup \Delta$ and
$D' \cup \Delta$, $\Delta = \{(t,t) : t \in \mathbb{R}\}$ is the diagonal, and unmatched
points are paired to their orthogonal projection onto $\Delta$,
$(b,d) \mapsto \big(\tfrac{b+d}{2}, \tfrac{b+d}{2}\big)$, at cost
$\|(b,d) - (\tfrac{b+d}{2},\tfrac{b+d}{2})\|_2 = \tfrac{d-b}{\sqrt{2}}$.

**This corrects a formula error in v1**, which stated the ground metric as $\|\cdot\|_\infty$.
The implementation (`trajectory_tda/topology/vectorisation.py`, `wasserstein_distance`)
calls `gudhi.wasserstein.wasserstein_distance(dgm1, dgm2, order=p, internal_p=2)` with
`p = 2` as the function default throughout the pipeline — an unambiguous $\ell^2$
(Euclidean) ground metric on the birth-death plane, not $\ell^\infty$. We use $\|\cdot\|_2$
above and rely on the stability theorem for the $\ell^2$ ground metric (Skraba & Turner,
2020) rather than the $\ell^\infty$ bottleneck-style stability constant. As throughout this
paper, we write $W_p$ with explicit order; the primary metric is $W_2$
(`order=2, internal_p=2`), with persistence-landscape $L^2$ distance
$\|\lambda_q - \lambda_q'\|_{L^2}$ reported as the mandatory complementary metric (§3.3)
wherever a rejection is claimed.

## Restriction to $H_0$/$H_1$, and the $H_2$ finding (corrects ISSUE L1)

The analysis is restricted to homological degrees $q \in \{0, 1\}$: connected components
and independent cycles. This restriction is **not** justified here by a claim that higher
homology is trivially absent or uninformative — an exploratory characterization found a
genuine, if qualified, $H_2$ signal, and the restriction is a disclosed scope decision, not
a dismissal.

**What the $H_2$ characterization showed.** A dedicated diagnostic battery
(`h2_characterization_2026-06-19.json`, $L \in \{200, 300\}$ — the largest landmark counts
at which a scale-comparable pinned-threshold witness complex is tetrahedron-feasible for
$H_2$; $B = 1{,}000$, seed 42, Markov-1 null, dual-metric) found that the raw $H_2$
$W_2$/landscape-$L^2$ rejection of the Markov-1 null is **mostly, but not entirely, a
cloud-dispersion artefact**: real trajectory clouds are more dispersed than a memoryless
Markov-1 surrogate, and this dispersion alone shifts birth/death coordinates enough to
register as a distance-based "rejection" at every homological degree, including $H_0$ and
$H_1$, without implying genuine void structure. Scale-normalizing each cloud by a
per-cloud characteristic distance before recomputing removes most, but not all, of the
effect: under the central-tendency normalizers (median-pdist, mean-pdist) a residual
$H_2$ rejection survives at both $L = 200$ ($W_2$ $p = 0.002$, landscape $L^2$ $p =
0.001$, $T$-ratio 1.75/1.93) and $L = 300$ ($W_2$ $p = 0.001$, landscape $L^2$
$p = 0.003$, $T$-ratio 2.11/1.85), but the same residual **collapses under the
diameter-based (max-pdist) normalizer** at both landmark counts (e.g. $L = 200$: $W_2$
$p = 0.47$, not rejected) — the signature of a distance-distribution-shape effect rather
than a normalizer-invariant one.

**Locked prose direction.** Per the pre-registered decision rule (reject $\Rightarrow$
expand to a dedicated $H_2$ analysis; fail $\Rightarrow$ restriction stands), this
characterization was reviewed and terminally locked as **restriction stands** (User
decision, 2026-06-19; Computational-Log `[DECISION]`/`[NEGATIVE]`, "T1.5 H2 Check —
RESTRICTION STANDS"): the residual is modest in magnitude, present only at small,
tetrahedron-feasibility-limited landmark counts ($L \le 300$; a matched-scale $H_2$ run at
$L = 5{,}000$ is not computationally feasible), not robust to the diameter-normalization
choice, and — because the frozen embedding was re-fit on 2026-05-28 and no serialized
pre-refreeze scaler/PCA checkpoint survives — not independently checkable on a second
frozen representation. No dedicated higher-homology section is added; the restriction to
$H_0/H_1$ stands, and this $H_2$ characterization is disclosed here as a limitation of that
scope decision rather than reported as an additive finding. We do not report an
$L = 2{,}000$ $H_2$ result: a scale-comparable pinned-threshold $H_2$ computation at that
landmark count exceeds the tetrahedron budget and no such result was computed.

## Issues (for Manager/notation review before this section is folded into v2)

- No committed filtration-threshold sensitivity sweep exists (response-plan ISSUE M2
  proposed a $q \in \{0.50, 0.75, 0.90\}$ percentile sweep); the truncation paragraph above
  is justified qualitatively via intrinsic dimension only. If a sweep is run before v2
  assembly, this paragraph should cite it directly.
- `papers/shared/notation.md` does not currently lock the $\ell^2$ ground-metric choice or
  cite Skraba & Turner (2020); per the response plan this should be added to the shared
  notation file so P01-A does not diverge on the same object.
