<!--
Target locations in v2: §3.2 (Embedding and Vietoris-Rips Pipeline) — added
caveat sentence; §4.2 (Persistence Diagrams) — rewritten H₀ orthogonality
paragraph; §4.4 (Seven Mobility Regimes) — sharpened ARI = 0.00004 sentence.

Evidence sources verified during drafting:
  • `papers/P01-A-JRSSA/drafts/v1-2026-04.md` §3.2 (lines 72–76), §4.2 H₀
    paragraph (line 100), and §4.4 ARI paragraph (line 152).
  • `papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md`
    Reviewer 1 issue R1-H3 — H₀-vs-density orthogonality needs explicit
    pre-empting, not incidental framing.
  • Chazal, F., & Michel, B. (2021). An introduction to topological data
    analysis: Fundamental and practical aspects for data scientists.
    *Frontiers in Artificial Intelligence* 4: 667963. — distinguishes
    Vietoris-Rips H₀ (single-linkage hierarchical-merge structure) from
    DTM-sublevel-set H₀ (density-mode inference).

Forbidden content (verified absent below): no claim that H₀ "encodes regime
separation"; no language reserved for the v2 abstract (gated, not drafted
in this Task).
-->

## §3.2 caveat — added at the end of the Vietoris-Rips paragraph

Vietoris–Rips $H_0$ is reported throughout as a single-linkage
hierarchical-merge summary of the 20-dimensional point cloud — equivalently, a
filtration view of the connectivity graph on $X$ — not as a density-mode
indicator. Mode-detection in TDA proceeds through sublevel-set or
distance-to-measure filtrations on a density estimate (Chazal & Michel, 2021,
§3); we do not invoke that construction here. Regime-level structure is
identified by the Gaussian mixture model described in §3.4, whose latent
clusters target a different topological object than the components tracked by
$D_0(X)$.

## §4.2 rewrite — H₀ orthogonality paragraph

Persistent homology in degree zero on the maxmin-landmark Vietoris–Rips
complex measures the single-linkage merge structure of the connectivity graph
of $X \subset \mathbb{R}^{20}$: at filtration scale $\varepsilon$, two points
belong to the same connected component once a chain of pairwise distances
below $\varepsilon$ links them. The dominant connected component (persistence
$15.81$, mean $4.08$, 99.98% of trajectories) plus six singleton outliers
describes the hierarchical-merge structure of that graph, not the density of
the embedding. The seven Gaussian mixture regimes characterised in §4.4 are
density modes of the same point cloud; the two analyses share an input but
target distinct topological objects, in the sense of Chazal & Michel (2021,
§3, §6). The Adjusted Rand Index of $0.00004$ between the GMM partition and
the $H_0$ tree-cut at $k = 7$ (reported in §4.4) is the value predicted by
that distinction: connectivity-graph merges in 20-dimensional Vietoris–Rips
complexes do not align with density-based partitions of the same point set
except by coincidence, and the trajectory manifold here gives no such
coincidence. Both structures are properties of the data, and they are
complementary rather than competing summaries.

## §4.4 sharpening — replacing v1's "expected and substantively meaningful" sentence

The two analyses target structurally distinct objects on the same point
cloud: $D_0(X)$ records the hierarchical-merge order of the
connectivity graph, while the Gaussian mixture model identifies modes of the
embedding density. ARI between the tree-cut at $k = 7$ and the GMM partition
is $0.00004$ — the value predicted by this structural orthogonality, not an
artefact of small-sample noise or parameter choice (cf. §4.2; Chazal &
Michel, 2021, §6). The two summaries are reported in this paper because they
answer different questions about the same trajectory space, and the regime
geography developed in §4.4–§4.6 and §5 should be read against the GMM
partition rather than against $D_0$.

## Note for v2 assembly

The phrase "$H_0$ encodes regime separation" appears in the v1 abstract and
must be removed when the abstract is rewritten (gated section, not drafted
here). The body text above does not use it.
