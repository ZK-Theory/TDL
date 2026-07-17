## §5.1 — The Mapper graph is a cover-nerve construction, not a homological invariant

The Mapper construction (Singh, Mémoli & Carlsson, 2007) is a cover-nerve
graph whose node and edge structure depends on the cover, the clustering
algorithm applied within each cover element, and the lens function used to
generate the cover; it is *not* a homological invariant of the underlying
point cloud and does not coincide with the persistence diagrams analysed in
§4. The sub-regime node counts, bridge-node counts, coverage rates, and
NMI-against-GMM statistics reported in §5.2–§5.6 are therefore properties of
the specific Mapper graph produced under the configuration documented in
§3.4, not topological invariants of the trajectory manifold. The
24-configuration sensitivity grid in §5.6 and Supplement §S3 reports the
range over which these graph-level summaries vary across cover and
clustering choices, and supports the qualitative claims while making the
configuration-dependence explicit. Throughout §5 we use "Mapper graph
property", "Mapper geometry", or "graph-based summary" in place of
"topological" or "topology" when the referent is a Mapper-derived
quantity.

## Mapper sub-regime threshold sensitivity

The sub-regime node count reported in §5 depends on the |z| flagging threshold, and
this dependence is now reported explicitly. The threshold sweep (B = 1,000
permutations, seed 42, within-regime PC1-shuffle null on the fixed Mapper graph,
Benjamini–Hochberg correction) shows that the count of flagged sub-regime nodes on the
PC1 lens falls steeply as the threshold tightens — 358 nodes at |z| = 1.0, 134 at
|z| = 1.5, and 40 at |z| = 2.0 — while at every threshold all flagged nodes survive
per-node BH correction (358/358, 134/134, 40/40). The 40 nodes that persist at
|z| = 2.0 form a high-confidence core. The multi-threshold lens comparison repeats the
sweep across both Mapper lenses and adds the |z| = 0.5 level:

**Table — Mapper sub-regime node counts by flagging threshold and lens**

| z-threshold | PC1-lens nodes | L2-norm-lens nodes |
|---:|---:|---:|
| 0.5 | 703 | 638 |
| 1.0 | 358 | 297 |
| 1.5 | 134 | 130 |
| 2.0 | 40 | 74 |

(The "L2-norm lens" is the Mapper lens function — the ℓ²-norm eccentricity filter — and
is distinct from the persistence-landscape $L^2$ distance used in §4/§6.)

The qualitative claim that sub-regime structure exists on both lenses is robust to the
threshold choice; the *number* of sub-regime nodes is not, and should not be reported as
a fixed quantity. A local Benjamini–Hochberg correction applied at the regime level (per
lens) further tempers the individual-node reading: after correction, only the
Mixed-Churn (R0) and Secure-High-Employment (R1) regimes on the L2-norm lens remain
significant at the 0.05 level (BH-adjusted p = 6.8×10⁻⁴ and 8.7×10⁻⁵ respectively); the
PC1-lens regime aggregates and the remaining L2-lens regimes do not survive correction.
The §5 interpretation is therefore stated at the level the evidence supports:
sub-regime heterogeneity is a real, threshold-robust qualitative feature of the Mapper
graph, with regime-level statistical confidence concentrated in R0 and R1 under the
L2-norm lens, rather than a precise count of "significant" sub-regime nodes.
