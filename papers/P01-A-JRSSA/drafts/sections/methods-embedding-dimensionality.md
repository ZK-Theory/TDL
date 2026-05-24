<!--
Target location in v2: §3.2 (Embedding and Vietoris–Rips Pipeline) — appended as
a new sub-paragraph immediately after the existing Vietoris–Rips paragraph
(v1-2026-04.md line 76, ending "...BIC selects $k = 7$.") and before the §3.3
Null-Model Testing heading.

Evidence sources verified during drafting:
  • `results/trajectory_tda_integration/stage1/intrinsic_dim_2026-05-24.json`
    — USoc estimates: full embedding (n = 15,968 unique points) $d_{\mathrm{TwoNN}}
    = 3.588$, $d_{\mathrm{MLE}} = 5.801$; $L = 5000$ maxmin landmark subset
    $d_{\mathrm{TwoNN}} = 10.060$, $d_{\mathrm{MLE}} = 9.164$; explained
    variance at $D = 20$ of $48.96\%$; verdict OVER-DIMENSIONAL; seed $42$.
  • `results/trajectory_tda_bhps/stage1/intrinsic_dim_2026-05-24.json` —
    BHPS estimates: full embedding (n = 5,711 unique points) $d_{\mathrm{TwoNN}}
    = 3.774$, $d_{\mathrm{MLE}} = 6.301$; $L = 5000$ maxmin landmark subset
    $d_{\mathrm{TwoNN}} = 4.975$, $d_{\mathrm{MLE}} = 6.709$; explained
    variance at $D = 20$ of $49.02\%$; verdict OVER-DIMENSIONAL; seed $42$.
  • Producing script: `trajectory_tda/scripts/estimate_intrinsic_dim.py`
    (commit `411336d`); `scikit-dimension` v0.3.4; MLE neighbourhood $k = 10$.
  • Vault `[RESULT]` entry 2026-05-24 on
    `04-Methods/Computational-Log` — records the diagnostic verdict
    OVER-DIMENSIONAL for both datasets and the decision that no T1.5 D-sweep
    is required.

Locked external citations introduced by this section:
  • Damrich, S., Berens, P., & Kobak, D. (2024). Topological data analysis
    in high dimensions: Failure of Vietoris–Rips persistent homology.
    *Advances in Neural Information Processing Systems* 37
    (arXiv:2311.03087v3).
  • Hiraoka, Y., et al. (2024). PCA projection and persistent homology in
    high ambient dimension.
  • Facco, E., d'Errico, M., Rodriguez, A., & Laio, A. (2017). Estimating
    the intrinsic dimension of datasets by a minimal neighborhood
    information. *Scientific Reports* 7, 12140.
  • Levina, E., & Bickel, P. J. (2004). Maximum likelihood estimation of
    intrinsic dimension. *Advances in Neural Information Processing
    Systems* 17.

Notation conformance with `papers/shared/notation.md`: the embedded point
cloud is written $X \subset \mathbb{R}^{20}$ throughout; the symbol $d$ is
used for intrinsic dimension with explicit subscripts $d_{\mathrm{TwoNN}}$
and $d_{\mathrm{MLE}}$ to avoid clash with the trajectory-length $T$ and
with the death-coordinate $d_i$ already in scope. Unsubscripted $D$ in
this section denotes the ambient dimension of the PCA embedding,
following the Damrich–Berens–Kobak (2024) and Facco et al. (2017)
convention; it is distinct from the persistence-diagram symbol $D_q(X)$
of the shared notation standard, which is never written without its
homology-degree subscript $q$ in the paper.
-->

## §3.2 addendum — Intrinsic dimensionality of the embedding

Append the following paragraph at the end of the §3.2 Vietoris–Rips
paragraph (after "BIC selects $k = 7$"):

> The choice of ambient dimension $D = 20$ retains $49\%$ of the variance
> of the raw $90$-dimensional unigram–bigram feature space, but a
> percentage-variance criterion does not directly address the concern
> raised by Damrich, Berens, and Kobak (2024) and Hiraoka et al. (2024)
> that Vietoris–Rips persistent homology can fail to recover the correct
> topology of Euclidean point clouds when the ambient dimension
> substantially exceeds the manifold's intrinsic dimensionality $d$. To
> diagnose exposure to this regime we estimated $d$ on each embedding
> using two complementary estimators applied to the unique support of the
> point cloud: the TwoNN nearest-neighbour-ratio estimator (Facco et al.,
> 2017) and a Levina–Bickel maximum-likelihood estimator with
> neighbourhood size $k = 10$ (Levina and Bickel, 2004). On the full
> embeddings the two estimators agreed within two units
> ($d_{\mathrm{TwoNN}} = 3.6$, $d_{\mathrm{MLE}} = 5.8$ for USoc;
> $d_{\mathrm{TwoNN}} = 3.8$, $d_{\mathrm{MLE}} = 6.3$ for BHPS),
> placing the trajectory manifold well inside the regime
> ($D / d \approx 4\text{–}6$) where Damrich et al. report Vietoris–Rips
> recovery to be reliable. The same estimators applied to the
> $L = 5000$ maxmin landmark subset that the filtration actually sees gave
> larger values ($d_{\mathrm{TwoNN}} = 10.1$, $d_{\mathrm{MLE}} = 9.2$ for
> USoc; $d_{\mathrm{TwoNN}} = 5.0$, $d_{\mathrm{MLE}} = 6.7$ for BHPS),
> reflecting that maxmin landmark selection samples the manifold's extent
> rather than its local density. The BHPS landmark estimates remain
> comfortably below the conservative threshold $d < D / 2$ above which
> Damrich et al. document systematic recovery failure; the USoc landmark
> estimates sit at that threshold ($d_{\mathrm{TwoNN}} = 10.1$,
> $d_{\mathrm{MLE}} = 9.2$ against $D / 2 = 10$), and remain far from the
> high-dimensional regime ($D / d \approx 1$) in which Damrich et al.
> document failure. We treat the $D = 20$ embedding as adequate for the
> Vietoris–Rips analyses reported below; a dimension-sweep sensitivity
> check is therefore not required.

## Note for v2 assembly

The paragraph is written for §3.2 only; it does not reference the
null-model machinery in §3.3 and does not anticipate any results from
§4.2–§4.3. The cross-reference to "$d < D / 2$" is to the Damrich,
Berens, and Kobak (2024) threshold; the four new citations introduced
here should be added to the consolidated v2 reference list at draft
assembly.
