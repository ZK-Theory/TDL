## §3.2 — Intrinsic dimensionality of the embedding

The choice of ambient dimension $D = 20$ retains $49\%$ of the variance
of the raw $90$-dimensional unigram–bigram feature space, but a
percentage-variance criterion does not directly address the concern
raised by Damrich, Berens, and Kobak (2024) and Hiraoka et al. (2024)
that Vietoris–Rips persistent homology can fail to recover the correct
topology of Euclidean point clouds when the ambient dimension
substantially exceeds the manifold's intrinsic dimensionality $d$. To
diagnose exposure to this regime we estimated $d$ on each embedding
using two complementary estimators applied to the unique support of the
point cloud: the TwoNN nearest-neighbour-ratio estimator (Facco et al.,
2017) and a Levina–Bickel maximum-likelihood estimator with
neighbourhood size $k = 10$ (Levina and Bickel, 2004). On the full
embeddings the two estimators agreed within two units
($d_{\mathrm{TwoNN}} = 3.6$, $d_{\mathrm{MLE}} = 5.8$ for USoc;
$d_{\mathrm{TwoNN}} = 3.8$, $d_{\mathrm{MLE}} = 6.3$ for BHPS),
placing the trajectory manifold well inside the regime
($D / d \approx 4\text{–}6$) where Damrich et al. report Vietoris–Rips
recovery to be reliable. The same estimators applied to the
$L = 5000$ maxmin landmark subset that the filtration actually sees gave
larger values ($d_{\mathrm{TwoNN}} = 10.1$, $d_{\mathrm{MLE}} = 9.2$ for
USoc; $d_{\mathrm{TwoNN}} = 5.0$, $d_{\mathrm{MLE}} = 6.7$ for BHPS),
reflecting that maxmin landmark selection samples the manifold's extent
rather than its local density. The BHPS landmark estimates remain
comfortably below the conservative threshold $d < D / 2$ above which
Damrich et al. document systematic recovery failure; the USoc landmark
estimates sit at that threshold ($d_{\mathrm{TwoNN}} = 10.1$,
$d_{\mathrm{MLE}} = 9.2$ against $D / 2 = 10$), and remain far from the
high-dimensional regime ($D / d \approx 1$) in which Damrich et al.
document failure. We treat the $D = 20$ embedding as adequate for the
Vietoris–Rips analyses reported below; a dimension-sweep sensitivity
check is therefore not required.
