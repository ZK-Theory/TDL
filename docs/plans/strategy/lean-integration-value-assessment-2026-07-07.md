# Lean Integration — Value Assessment for the Work Ahead

**Date:** 2026-07-07
**Status:** Assessment for Stephen's decision; gates the shape (not the existence) of S2 and the W5 addendum
**Author:** Claude (Fable 5)
**Inputs:** S0 smoke test (PASS), S1 gap survey + framing memo (`S1-framing-decision-memo-2026-07-07.md`), scout plan (`lean-prover-integration-scout-plan-2026-07-04.md`), S3a/S3b pre-registration skeleton, W5 v0.2 spec, T1.23d certificate code (`trajectory_tda/analysis/panel/fixed_margin_max_ari.py`) and result (`ari_om_gmm_normalised_2026-06-24.json`), grep of `trajectory_tda/` for reduction/landmark usage

## 1. The question

Given that mathlib has essentially no TDA (no persistence, no discrete Morse theory, no Vietoris–Rips), is Lean integration worth doing, and — concretely — how does it help the work ahead rather than becoming a formalisation hobby?

## 2. The honest picture: three value channels on three time horizons

The S1 survey's "mathlib gap" finding does not have one implication; it has three, because Lean would enter the programme through three different doors with very different distances to payoff.

### Channel 1 — Assurance lane for finite exact-mathematics lemmas. **Immediate. This is where Lean earns its keep now.**

The mathlib gap is irrelevant to this channel. The mathematical claims TDL's *certificates and normalisations* rest on are finite combinatorics and exact algebra — `Finset` sums, integer/rational inequalities, counting identities — precisely mathlib's most mature territory.

The exemplar already exists in the repo and was **actually wrong once**. The T1.23d fixed-margin max-ARI certificate has two halves:

- The **achievable lower bound** is runtime-checkable: the achieving table is emitted in the result JSON; anyone can re-verify its margins and pair count. No proof needed.
- The **rigorous upper bound** (pair-overlap ≤ 60,862,048, hence max ARI ≤ 0.8607) rests entirely on a *paper argument* in a docstring — the concentration-relaxation claim in `concentration_upper_bound_sumsq`. If that argument is wrong, the bracket is wrong, the normalised ARI bracket in a reviewer-facing P01-A result is wrong, and **no runtime check can catch it**. Its predecessor (the whole-cluster-packing fallback) *was* wrong, returning a vacuous 1.0 that survived until T1.23d.

That is the exact profile of claim where a Lean proof adds assurance nothing else in the W5 machinery provides: machine-checkable in principle, not checkable by execution, historically fallible in this project. The class is not small — future instances include any certified bound accompanying a result JSON, contingency/counting identities behind normalisations, p-value formula properties, monotonicity claims used in decision rules.

**Cost:** near zero. S0 confirmed the loop (Leanstral iterates locally, kernel verifies, Claude only authors statements). The S2 statements are Fintype/Finset/ℚ material — no missing mathlib theory.

### Channel 2 — Framing B, verified exact reduction. **Medium term — but with a referent gap the memo glossed over.**

The S1 memo and the S3a/S3b skeleton justify B as certifying "one concrete collapse/reduction **actually usable in the TDL pipeline**." I checked: **the pipeline does not perform exact reductions.** Its scaling mechanism is maxmin *landmark subsampling* (`trajectory_tda/topology/trajectory_ph.py::maxmin_landmarks`, used throughout `permutation_nulls.py` and the stage-1 scripts). Landmarking is an *approximation* — the maths that would bless it is interleaving/stability, i.e. framing A, the one correctly deferred as 6+ layers away. An elementary-collapse theorem certifies an *exact* preprocessing step that currently exists nowhere in `trajectory_tda/`.

So B's honest value proposition is one of these, and we should pick explicitly:

- **B-as-pipeline-lever (conditional):** the theorem pays off only if the pipeline *adopts* an exact-reduction step and that step *materially shrinks* panel-trajectory complexes. Both are checkable cheaply before S3b matters: gudhi ships an edge-collapse implementation (Boissonnat–Pradhan; `collapse_edges` on `SimplexTree` — verify availability in the pinned gudhi version per the no-speculative-paths rule) with published proofs that it preserves persistence. A half-day empirical spike — run edge collapse on one real panel-trajectory complex at working landmark count, measure simplex-count reduction and verify diagram equality — tells us whether verified reduction licenses anything we'd actually run.
- **B-as-research-strand (unconditional but different):** the chain bridge + collapse theorem is a genuine mathlib contribution and a publishable formalisation lane regardless of pipeline adoption. Legitimate — but then its budget competes with papers, not with assurance, and it should be justified as such, not as pipeline assurance.

Recommendation: add an **adoption gate** to the S3 sequence (call it S3-pre, runnable in parallel with S3a): the empirical edge-collapse benchmark above. If reduction shrinks real complexes by a useful factor, B is a pipeline lever and S3b's referent clause is real. If not, B continues (or not) as a pure-maths strand with eyes open. This is a one-line amendment to the S3 pre-registration skeleton, decided by you.

### Channel 3 — Formalised persistence (framing A, barcode-flavoured C). **Years away. Correctly deferred; keep it deferred.**

Nothing in this assessment changes the memo's ranking. The one nuance worth recording: because the pipeline's actual scaling mechanism (landmarking) is an approximation, the maths that would certify *what the pipeline really does* is framing A. That is a reason A stays strategically attractive long-term — and no reason at all to start it now.

## 3. What Lean will NOT provide — negative scope (bind this into W5)

To prevent the assurance lane from overselling itself, the W5 `lean_proof` addendum must state what a kernel-verified artefact cannot discharge:

1. **No topology-lane coverage for years.** Persistence computations, W2 distances, landscape norms, stability-based claims, landmark approximation error — none of these can be Lean-certified until the missing stack exists. The topology lane's assurance remains permutation nulls, benchmarks (Gidea–Katz), and independent recomputation. A `lean_proof` attached to a topology-lane claim must be scoped to the specific finite lemma it proves, never presented as certifying the persistence result.
2. **No certification of executing code.** A Lean theorem about the concentration bound does not verify that `fixed_margin_max_ari.py` implements it. The bridge is the **certificate pattern** (§4): the theorem certifies the *bound*; runtime checks certify the *witness*; the two together bracket the claim without verifying any implementation.
3. **No float-valued claims.** Theorems are stated over ℕ/ℤ/ℚ. Result JSONs carry floats. Every referent note must state the exact-arithmetic core that is certified (here: integer pair counts) and where float rounding enters (final divisions), or the statement-referent check fails.
4. **No discharge of Key B.** The kernel is Key A evidence — deterministic, independent-by-construction. The statement-referent match ("does this theorem say what the claim needs?") is exactly the scientific-review key, and a prover output can never satisfy it. This maps onto W5 two-key validity with zero architectural change, which is the single strongest reason the integration is cheap.

## 4. The integration architecture that makes this compound: certificates, not verified software

The pattern that generalises across channels 1 and 2:

```
implementation (unverified, fast)  →  emits witness/certificate into the result JSON
Lean theorem (verified once)       →  "any witness satisfying P has property Q"
runtime check (cheap, per-result)  →  witness satisfies P
```

T1.23d already accidentally has this shape: the achieving table is the witness for the lower bound; the concentration theorem (S2) closes the upper bound. A future collapse-based reduction has the same shape: the preprocessing code emits the collapse sequence; the S3b theorem says each free-face collapse preserves homology; a cheap checker validates each step's free-face condition. **We never verify pipeline code; we verify the mathematics its certificates appeal to.** This keeps Lean effort bounded and permanently reusable, and it is the design principle the W5 addendum encodes.

## 5. Cost side (confirmed by S0)

> **Erratum 2026-07-21.** This section (and the scout plan §§1, 2.2–2.3) described Leanstral as a *local* model. Per the S0 vault `[RESULT]` (2026-07-04), Leanstral is an **external Mistral Labs API** (requires `MISTRAL_API_KEY` + Labs enablement) — proof search is a data-boundary crossing to Mistral, not local execution. The zero-metered-cost premise holds **provisionally and for a different reason**: Mistral currently provides Leanstral **free under its experimental Labs programme**, not guaranteed to persist. The relative token argument (proof search off Claude's budget) is unaffected; the data-boundary and durability caveats are new. See 05a §8 and the `prover_data_exposure` field (05a §2).

| Cost | Assessment |
|---|---|
| Claude tokens | Statement authorship + referent review only; proof search is off Claude's budget (external Leanstral, free under Mistral Labs *for now* — see erratum), verification is the free kernel |
| Wall time | S2 statements are standard mathlib territory; days not weeks. S3a/S3b timeboxed with kill criteria already written |
| Toolchain | Windows elan/lake works (S0); mathlib cache in place |
| Real risks | (a) proving the wrong statement — mitigated by authorship split + non-vacuity witnesses + false-variant mutation checks (all in the W5 addendum contract); (b) formalisation time-sink — mitigated by stop rules and, now, the S3-pre adoption gate |

## 6. Verdict

**Integrate, with the value claim narrowed to what the evidence supports:**

> Lean's near-term value to TDL is machine-certifying the small exact-mathematics lemmas that the programme's certificates, normalisations, and decision rules rest on — the class of claim that has actually been wrong once and that no runtime check can catch. It is not, and must not be presented as, an assurance lane for the topology itself.

Concretely:

1. **Proceed with S2 now** (statement authorship delivered alongside this memo: `S2-statement-authorship-max-ari-bound-2026-07-07.md`). It pilots the full assurance loop on a claim with real stakes in P01-A.
2. **Proceed with the W5 `lean_proof` addendum now** (draft delivered: `05a-lean-proof-evidence-class-addendum-2026-07-07.md`), with the negative scope of §3 binding.
3. **Amend the S3 skeleton with the S3-pre adoption gate** before S3b is treated as pipeline assurance (user decision — one paragraph in the skeleton).
4. **Keep A/C2 dead** until the chain bridge exists and someone re-surveys mathlib.

## 7. Decision points for Stephen

| # | Decision | Recommendation |
|---|---|---|
| 1 | Accept the narrowed value framing (§6 quote) as the strand's stated purpose? | Yes — it is what S0/S1 actually support |
| 2 | Add S3-pre (empirical edge-collapse benchmark, ~½ day) to the S3 pre-registration? | Yes — it converts B's referent clause from asserted to verified |
| 3 | If S3-pre shows weak reduction on real complexes: continue B as a pure-maths/mathlib-contribution strand, or park it? | Decide then, with the data — do not pre-commit |
