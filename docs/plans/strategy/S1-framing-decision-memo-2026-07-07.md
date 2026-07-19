# S1 Framing Decision Memo: Lean/mathlib Route for the TDA Research Strand

## Decision

Pre-register **Framing B: verified exact reduction**, narrowed to **elementary collapse / finite-complex reduction with machine-checked homology preservation**.

Do **not** pre-register A as the first Lean/TDA strand. Approximation bounds remain mathematically attractive, but they require too much missing persistence infrastructure before Lean contributes concrete value. Do **not** pre-register C as the first main strand unless it is deliberately restricted to Euler-characteristic-type or local finite-complex invariants. Barcode-dependent C collapses back into A.

The recommended direction is therefore:

> **Formalise the finite simplicial-chain bridge for `AbstractSimplicialComplex`, then prove that a specified elementary reduction used by the empirical TDA pipeline preserves homology or Euler characteristic under explicitly stated hypotheses. Use this as the first Lean-certified justification for aggressive preprocessing on large panel-trajectory complexes.**

This directly matches the original plan's research-strand role for Lean: formal assurance attached to large-complex TDA, not theorem proving detached from the empirical pipeline. The attached plan explicitly framed Lean as both an ARS assurance lane and a research-strand agent, with the research bottleneck being TDA on large complexes from large social-science panels.

## Evidence base

The S1 survey result is directionally sound. mathlib currently has usable starting points in abstract simplicial complexes, geometric simplicial complexes, homological algebra, singular homology, metric-space theory, and Euler characteristic machinery. It does not appear to have the TDA-specific stack needed for persistence-first work.

The key positive fact is that mathlib has `AbstractSimplicialComplex ι` as a downward-closed family of nonempty finite sets containing singletons, with order/lattice structure already present. The documentation also shows `PreAbstractSimplicialComplex`, `AbstractSimplicialComplex`, set-like membership for faces, and complete-lattice instances. Geometric simplicial complexes are also present as `Geometry.SimplicialComplex`, built over convex hulls in modules.

The second positive fact is that the homological-algebra side is not the missing part. The mathlib index includes a substantial `Mathlib.Algebra.Homology.*` hierarchy, including `HomologicalComplex`, exact sequences, homotopy, quasi-isomorphisms, homology sequences, short complexes, and spectral-sequence infrastructure. Singular homology is also present: mathlib defines the singular chain complex functor and `singularHomologyFunctor`.

The decisive negative fact is that persistence is absent from the public mathlib surface I checked. The mathlib index search returned no match for “Persistent” and no match for “Vietoris”; the only “Morse” match in the index is `Mathlib.RingTheory.Polynomial.Morse`, which is unrelated to discrete Morse theory. This supports the survey's claim that persistent homology, persistence modules, barcodes, interleavings, bottleneck distance, and the stability theorem should be treated as absent for planning purposes.

There is one important nuance. mathlib has serious metric-space infrastructure, including Gromov-Hausdorff distance on compact metric spaces, and the overview lists Hausdorff distance and Gromov-Hausdorff space. That helps if later work needs metric approximation statements. It does not materially shorten the route to persistent homology stability, because the missing layer is not “metric spaces” but the TDA-specific functorial pipeline from data to filtered complexes to persistence modules to diagrams and distances.

## Ranking

| Rank | Framing                         | Decision                     | Reason                                                                                                                                                                                                 |
| ---: | ------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
|    1 | **B: verified exact reduction** | **Pre-register now**         | Shortest route to a useful theorem tied to the pipeline. The missing bridge is finite simplicial chains from `AbstractSimplicialComplex`; after that, homological machinery can be used.               |
|    2 | **C: new invariants**           | **Retain as auxiliary only** | Medium if restricted to Euler characteristic, face-count summaries, local homology proxies, or finite-chain invariants. Far if it depends on barcodes or stability in the persistence sense.           |
|    3 | **A: approximation bounds**     | **Defer**                    | Most strategically attractive long-term, but it requires the largest formal foundation: VR construction, filtrations, persistence modules, interleavings, barcode/bottleneck machinery, and stability. |

## Why B wins

B is the only framing where Lean can plausibly produce a valuable, checkable artefact before the project is swallowed by foundational library construction.

The survey identifies the critical missing link as:

> `AbstractSimplicialComplex -> ChainComplex`

That is the correct bottleneck. The available simplicial-complex side is combinatorial. The available homological-algebra side is mature. What is missing is the concrete simplicial-chain functor: oriented simplices or ordered vertex lists, free modules over faces of each dimension, the alternating boundary map, proof that `∂ ∘ ∂ = 0`, and then a packaged `ChainComplex` or `HomologicalComplex`.

Once that bridge exists, B becomes formally meaningful. A collapse or reduction can be expressed as a chain map, chain homotopy equivalence, quasi-isomorphism, or Euler-characteristic-preserving transformation. The Lean target can be modest but real:

> Removing a free face together with its unique coface from a finite abstract simplicial complex induces a chain homotopy equivalence, hence preserves homology over a chosen coefficient ring or field.

That is not the whole of discrete Morse theory. It is the atomic move from which useful collapse pipelines are built. This matters: the S1 survey says discrete Morse theory is absent, so trying to formalise “discrete Morse theory” as the first target would be too broad. But an elementary free-face collapse is a much smaller theorem and can be tied directly to preprocessing in the TDA pipeline.

B also has the strongest engineering payoff. Your large-complex problem is not merely “can we compute PH faster?” It is “can we justify reductions aggressively enough to make large social-science panel complexes tractable without destroying the topological signal?” A Lean-checked reduction theorem provides exactly that type of licence. It does not certify the whole implementation, but it certifies the mathematical invariant-preservation claim that the implementation relies on.

## Why A should be deferred

A is the most academically natural TDA theorem direction: approximation with guarantees, interleaving bounds, bottleneck-distance guarantees, and stability. But it is the wrong first Lean target.

To make A meaningful in Lean, you would need at least the following layers:

1. A construction of Vietoris-Rips or related complexes from finite metric data.
2. A notion of filtration indexed by a preorder or ordered parameter.
3. A functorial route from filtered complexes to chain complexes.
4. A definition of persistence modules, probably as functors from a poset category into a module category.
5. Interleaving distance between persistence modules.
6. Barcode or persistence-diagram representation, if the theorem is diagrammatic.
7. Bottleneck distance and the algebraic stability theorem, if the guarantee is expressed in the usual TDA language.

mathlib has some of the ambient category, metric, and module infrastructure, but not the TDA-specific stack. The official docs support the presence of the ambient mathematical worlds, but the index-level absence of “Persistent” and “Vietoris” supports treating the actual persistence stack as absent.

A should therefore remain a **phase-two research programme**, not the S1 pre-registration direction. It may become attractive after B has built the chain bridge and after one or two finite-complex functoriality lemmas exist.

## Why C is not a single option

C splits into two very different tracks.

**C1: Euler/local finite-complex invariants.** This is plausible. mathlib already has Euler-characteristic definitions for homological complexes and finite-support results. A Lean-certified invariant such as “this reduction preserves Euler characteristic” or “this local finite-chain summary is invariant under relabelling / inclusion-preserving isomorphism / elementary collapse” could be formalised earlier than persistence. This could be useful for MCbiF-adjacent work if the invariant is designed around categorical-state panel data rather than geometric point clouds.

**C2: barcode-like new invariants.** This is effectively A in disguise. If the invariant needs filtrations, persistence modules, barcodes, bottleneck/interleaving stability, or VR filtrations, it inherits the same missing layers as A.

Therefore C should not be pre-registered as the first main strand. It should be held as a **bounded auxiliary lane** attached to B: after the simplicial-chain bridge is built, define one cheap invariant and prove it is preserved by the same reduction used in B.

## Recommended pre-registration direction

### Working title

**Lean-certified elementary reductions for large finite simplicial complexes arising from panel-trajectory TDA**

### Core hypothesis

For a finite abstract simplicial complex used in the empirical pipeline, a specified elementary reduction rule can be formalised in Lean and proved to preserve a target invariant, initially Euler characteristic and then homology, under explicit combinatorial hypotheses.

### Primary formalisation target

Build the minimal bridge:

```lean
AbstractSimplicialComplex ι
  -> dimension-indexed oriented faces
  -> free module of n-chains
  -> alternating boundary
  -> proof boundary_boundary = 0
  -> ChainComplex / HomologicalComplex
```

Then prove one reduction theorem.

### First theorem target

Start with the weaker theorem if necessary:

> **Euler preservation:** an elementary free-face collapse changes the face counts in adjacent dimensions by equal and opposite Euler signs, hence preserves Euler characteristic.

Then attempt the stronger theorem:

> **Homology preservation:** an elementary free-face collapse induces a chain homotopy equivalence, hence is a quasi-isomorphism and preserves homology.

The Euler theorem is not enough for the full TDA claim, but it is an excellent first acceptance test because it exercises the same finite-complex representation without requiring all chain-homotopy machinery at once.

### Empirical referent

The theorem should not be stated as an abstract library exercise only. The referent should be:

> This reduction is valid for the finite complexes generated by the panel-trajectory pipeline when the implementation identifies a free face satisfying the theorem's hypotheses.

That referent clause is essential. The existing plan correctly identifies “proving the wrong statement” as the critical Lean risk and requires independent statement/referent checking.

## Concrete spike sequence after S1

### S2 stays as planned

Run the assurance-lane micro-formalisation first. The existing plan proposes the corrected max-achievable-ARI bound as a small theorem with real assurance value because it was previously wrong once. That is still the right S2. It proves the workflow: statement authored independently, Leanstral fills the proof, Lean kernel verifies, and the artefact passes the no-`sorry` / axiom-audit contract.

### S3 should be re-scoped

Original S3 says:

> “formalise homology-preservation for one concrete collapse/reduction actually usable in the TDL pipeline.”

That is correct, but it needs a two-stage gate:

**S3a: Chain bridge spike.**
Goal: define finite chain groups and the boundary map for `AbstractSimplicialComplex`; prove `∂² = 0` for low dimension first, then general dimension if feasible.

**S3b: Reduction theorem spike.**
Goal: formalise one free-face elementary collapse and prove either Euler preservation or chain-homotopy equivalence.

Do not let S3 start with “discrete Morse theory”. That is too broad and invites a foundational detour.

### A-spike deferred

Run an A-spike only after the chain bridge exists. The first A-spike should not attempt full stability. It should ask:

> Can we define a finite filtration of abstract simplicial complexes as a monotone map from a finite ordered index type into `AbstractSimplicialComplex`, and can we induce maps between chain complexes?

That would be the first true step toward persistence, but it should not precede B.

## Go / no-go criteria

### Promote B if

B should be promoted if, within the S3 budget, the agent can produce:

1. A compiling Lean file defining the chain objects for finite abstract simplicial complexes.
2. A proof of boundary compatibility, ideally `∂² = 0`.
3. A theorem statement for elementary collapse whose hypotheses match the implementation-level concept of a free face.
4. At least Euler preservation, with homology preservation as the stretch target.
5. A referent note explaining exactly how the theorem licenses one preprocessing step in the empirical pipeline.

### Park B if

Park B if the chain bridge itself becomes too expensive: for example, if orientation, quotienting by permutations, or free-module infrastructure consumes the entire spike without a working low-dimensional prototype. In that case, pivot temporarily to C1 with face-count/Euler invariants over finite complexes, because that still yields Lean-certified value without full homology.

### Kill A for now if

A should remain deferred unless a later survey finds pre-existing persistence-module or interleaving infrastructure. The current evidence does not support that assumption.

## Final recommendation

The S1 decision is:

> **Pre-register B, but formulate it as “Lean-certified finite-complex reductions” rather than “discrete Morse theory” or “persistent homology”.**

This preserves the strategic advantage of the Lean integration while avoiding the trap of formalising an entire missing TDA library before producing any research value. It also aligns with your broader programme: exact nerve / finite-complex constructions for large panel data, aggressive but justified preprocessing, and formal assurance for mathematical claims that would otherwise remain informal.
