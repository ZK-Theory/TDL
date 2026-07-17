<!--
Target location in v2: §5.1 (Two Complementary Analytical Lenses) — added
methodological caveat paragraph; §5.2–§5.6 — vocabulary patches where the
audit identified a problematic usage.

Evidence sources verified during drafting:
  • v1-2026-04.md §5.1 (lines 188–190), §5.2 (192–214), §5.3 (216–220),
    §5.4 (222–234), §5.5 (236–240), §5.6 (242–244).
  • `papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md`
    Reviewer 1 issue R1-10.3 — Mapper is a cover-nerve construction whose
    sub-regime node counts, bridge counts, and graph metrics are not
    homological invariants and should not be described as "topological"
    findings.
  • Singh, Mémoli & Carlsson (2007) — Mapper as a cover-nerve construction;
    cover and clustering choices determine the resulting graph.

Forbidden content: no claim that Mapper *cannot* support sociological
inference — substantive Mapper findings stand. The audit changes
vocabulary only.
-->

## §5.1 methodological caveat — added as a new paragraph immediately after the two-lenses sentence

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

## Vocabulary audit of v1 §5 — table of changes

The audit pass on `v1-2026-04.md` lines 187–244 finds no occurrences of
"topology" or "topological" used as descriptors of Mapper-derived
quantities; all instances of those words in v1 §5 are either absent (the
section uses "geometry", "geographic", "boundary", "node", "bridge" rather
than "topological"), or appear in legitimate methodological context such as
cross-references to §4 persistence-homology results. The following patches
are required only at the framing-level and are entered as one-to-one
replacements when the v2 draft is assembled:

| v1 line | v1 wording (excerpt) | v2 replacement |
|---|---|---|
| 192 | "characterise the global landscape of UK career trajectories" | unchanged |
| 218 | "no natural 'gap' in the boundary structure" | "no natural 'gap' in the Mapper boundary structure" |
| 220 | "Bridge node counts scale monotonically with the distance threshold" | unchanged — the claim is a Mapper-graph property already |
| 226 | "a multi-layered geography that regime-level statistics conceal" | unchanged — "geography" is acceptable Mapper-graph language |
| 244 | "every configuration detects sub-regime structure on both PC1 and L2 norm" | "every configuration detects sub-regime *graph* structure on both PC1 and L2 norm" |

No additional substantive rewrites are required in §5.2–§5.6. The §5.1
methodological caveat above is the principal change.

## Cross-section vocabulary check

The §2.3 phrase "the topological approach adds: a principled metric-space
embedding…" should be split when §2.3 is revisited: "the persistent-homology
approach adds" for items concerning $D_q(X)$; "the Mapper approach adds" for
items concerning the cover-nerve graph. That edit belongs to a §2.3
rewrite, which is gated on the v2 abstract / framing pass and is not
authored here.

## §5.x Mapper sub-regime threshold sensitivity (reviewer issue B12)

The sub-regime node count reported in §5 depends on the |z| flagging threshold, and
this dependence is now reported explicitly. Two committed analyses support the addition.
The threshold sweep (T1.10; `sub_regime_thresh_sweep_2026-06-07.json`; B = 1,000
permutations, seed 42, within-regime PC1-shuffle null on the fixed Mapper graph,
Benjamini–Hochberg correction) shows that the count of flagged sub-regime nodes on the
PC1 lens falls steeply as the threshold tightens — 358 nodes at |z| = 1.0, 134 at
|z| = 1.5, and 40 at |z| = 2.0 — while at every threshold all flagged nodes survive
per-node BH correction (358/358, 134/134, 40/40). The 40 nodes that persist at
|z| = 2.0 form a high-confidence core. The multi-threshold lens comparison
(`03_multi_threshold.json`) repeats the sweep across both Mapper lenses and adds the
|z| = 0.5 level:

**Table — Mapper sub-regime node counts by flagging threshold and lens** *(provisional label; final table number set at v2 assembly)*

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
lens, in `03_multi_threshold.json`) further tempers the individual-node reading: after
correction, only the Mixed-Churn (R0) and Secure-High-Employment (R1) regimes on the
L2-norm lens remain significant at the 0.05 level (BH-adjusted p = 6.8×10⁻⁴ and
8.7×10⁻⁵ respectively); the PC1-lens regime aggregates and the remaining L2-lens regimes
do not survive correction. The §5 interpretation is therefore stated at the level the
evidence supports: sub-regime heterogeneity is a real, threshold-robust qualitative
feature of the Mapper graph, with regime-level statistical confidence concentrated in R0
and R1 under the L2-norm lens, rather than a precise count of "significant" sub-regime
nodes.
