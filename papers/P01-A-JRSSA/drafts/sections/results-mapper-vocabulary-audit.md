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
