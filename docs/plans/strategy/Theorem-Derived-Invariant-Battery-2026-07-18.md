# Theorem-Derived Invariant Battery ("Mathematical Canaries") — Specification

**Date:** 2026-07-18
**Status:** specification + reference implementation delivered together
(`shared/math_invariants.py`, `tests/shared/test_math_invariants.py`). The wiring of
these checks into result-file ingestion schemas, gate-4 contracts, and the ARS
admission predicates is follow-up work for the ARS/Gate-7 lanes; this document is the
authority for *what* each check asserts and *why the assertion is decisive*.
**Companion:** `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md`
(the invariants I1a–I11a referenced throughout).
**Provenance note:** authored 2026-07-18 as a capability-transition deliverable — the
theorem selection and derivations below are the hard part; maintenance and integration
are deliberately routine.

---

## 1. Why this document exists

The failure inventory converts this project's history into machine-checkable
invariants, but several of the highest-severity invariants are *process-shaped*: they
demand a "solver identity block" (I1a), an "impossibility screen" (I1b), a
"demonstrated ability to fire" (I2b), a "machine-checkable invariance audit" (I2d) —
without specifying the mathematics that makes such a check decisive. The W₂
greedy-fallback defect (Class 1) passed every software-shaped check the project had:
hooks, lint, unit tests, review. It was mathematically impossible the whole time — the
frozen USoc H₁ headline 233.68 exceeded a bound computable in O(n) from the diagrams
alone (~35.8). Nothing evaluated that bound.

This battery is the mathematical content for those invariants: a set of checks each
derived from a theorem or an exact identity, such that **a violation implies an
implementation error with certainty** — never a statistical fluctuation, never a
tolerance judgement call beyond floating-point slack. That property is what makes them
suitable as hard gates rather than warnings.

Design principles (each check satisfies all five):

1. **Theorem-derived.** The asserted inequality/identity is a mathematical fact about
   the estimand, independent of any implementation.
2. **Independent code path.** The check never calls the solver under test to compute
   its own reference side (the Class-2e lesson: a reference copied from the artifact
   under validation is vacuous). Reference sides are closed forms, scipy's Hungarian
   algorithm, or gudhi's C++ bottleneck code — none of which share code with the
   POT/EMD W₂ path or the landscape pipeline.
3. **Cheap.** O(n) or O(n³) on small inputs; every check is affordable at commit time
   or ingestion time.
4. **Decisive.** Violation ⇒ bug. The tolerance is floating-point/discretisation
   slack with a stated bound, not a statistical band (the one exception, P2, is
   explicitly a statistical check and says so).
5. **Ships with a negative control (I2b).** Every check's test suite contains a
   known-bad input the check rejects — including a reimplementation of the greedy
   rank-matching defect itself, so the battery provably catches the historical
   failure.

Convention discipline: the project's production W₂ is gudhi's exact POT/EMD solver at
`order=2, internal_p=2` (L² ground metric on the plane) —
`trajectory_tda/topology/vectorisation.py::wasserstein_distance`. Every function in
the battery is parameterised by `(order, internal_p)` with those defaults, and
mixing conventions between a value and its check is itself the I1a failure class.
Under ground metric L^p, the distance from a point (b, d) to the diagonal is
`(d − b)/2 · 2^(1/p)` (perpendicular foot at the midpoint): `pers/√2` for p = 2,
`pers/2` for p = ∞.

---

## 2. The battery

### W — Wasserstein / optimal-transport identity checks

**W1. Closed-form empty-diagram oracle.**
`W_q(D, ∅) = ( Σᵢ (persᵢ/2 · 2^(1/p))^q )^(1/q)` — exact, O(n), no solver involved
(every point must go to the diagonal; the transport problem is trivial). Any W_q
implementation must reproduce this to machine precision on `(D, ∅)` inputs.
*Detection scope (stated honestly):* the greedy rank-matcher **passes** W1 — against
an empty diagram, rank matching also sends everything to the diagonal. W1 catches
convention drift (wrong `internal_p`, wrong exponent, un-halved persistence), not
matching errors. The matching-error catchers are W3–W5.
→ enforces I1a (convention verification); component of I1b.

**W2. Diagonal-transport upper bound — the I1b impossibility screen, generalized.**
Matching *every* point of both diagrams to the diagonal is a feasible transport plan,
so for all q, p:
`W_q(A, B)^q ≤ W_q(A, ∅)^q + W_q(B, ∅)^q`,
i.e. for the production convention
`W₂(A,B) ≤ sqrt(0.5·Σ pers_A² + 0.5·Σ pers_B²)` — exactly the I1b formula, now with
its derivation and its general-(q,p) form. O(n) from the diagrams (or from retained
per-diagram `Σ pers²` fields). A reported value above this bound is not "suspicious";
it is impossible.
*Historical catches:* the frozen USoc H₁ 233.68 vs ~35.8 bound; the α-sweep summary
W₂ means ~277 vs ~20 bound. Both fail W2 instantly.
→ enforces I1b directly.

**W3. Independent exact mini-oracle (the decisive greedy-catcher).**
For diagram pairs up to ~50 points per side, W_q is computed *exactly* by scipy's
Hungarian algorithm (`linear_sum_assignment`) on the canonical augmented bipartite
matrix: rows = A's points plus |B| diagonal slots, columns = B's points plus |A|
diagonal slots, with
- real–real cost `‖a − b‖_p^q`,
- real–diagonal cost `(diagonal distance of the real point)^q` (uniform across
  slots), and
- **diagonal–diagonal cost 0** (both "unused" — this zero block is what makes the
  reduction exact; see the defect note in §4).

This is the same estimand computed by an algorithm sharing no code with POT/EMD. The
production solver must agree to ~1e-9 relative on randomized small pairs. The greedy
rank-matcher disagrees immediately and grossly (negative control in the test suite:
a pair where greedy exceeds the *optimum* by >100× and violates W2's bound).
→ enforces I1a (solver identity by agreement), I1c (binding test that the default
path computes optimal transport); the "smoke canary with teeth" for Class 1.

**W4. Metric axioms on sampled inputs.**
W_q is a metric on diagrams. Harness over any distance callable: on randomized
diagrams check `W(D, D) = 0`, `W(A, B) = W(B, A)`, and
`W(A, C) ≤ W(A, B) + W(B, C) + tol` on sampled triples. Cheap; requires only the
solver under test plus arithmetic. Approximate matchers typically break the triangle
inequality or oracle agreement even when they preserve symmetry.
→ enforces I1a/I1c; a solver-agnostic screen usable when W3's size limit is exceeded.

**W5. Order-interleaving sandwich against an independent bottleneck.**
`gudhi.bottleneck_distance` is hera-based C++, sharing nothing with the POT path. For
any matching, `(Σ c^q)^(1/q) ≥ max c`, and `‖·‖_p ≥ ‖·‖_∞` pointwise, hence
**lower bound:** `W_q(A, B; internal_p) ≥ bottleneck(A, B)` for every q and every
p ≥ 1. A reported W₂ *below* the independently computed bottleneck is impossible.
**Upper bound:** taking the bottleneck-optimal matching as a feasible plan and
`‖x‖_p ≤ 2^(1/p)·‖x‖_∞` on the plane:
`W_q(A, B) ≤ (n_A + n_B)^(1/q) · 2^(1/p) · bottleneck(A, B)`.
Together the sandwich localizes gross inflation *and* gross deflation at any diagram
size, not just W3's small-pair regime.
→ enforces I1a/I1b at production scale.

### L — Persistence-landscape checks

The landscape lane is the certified side of the dual-metric mandate (no OT solver;
structurally immune to Class 1's instance). These checks keep it that way — silent
failure modes for landscapes are grid/truncation/normalisation errors, which the
following make loud. Notation: the k-th landscape function `λ_k(t)` is the k-th
largest value at t among the "tent" functions
`tent_i(t) = max(0, min(t − bᵢ, dᵢ − t))`, one per diagram point — this
*pointwise descending rearrangement* characterisation is the engine of L2 and L3.

**L1. Structural invariants.** For all t on the evaluation grid:
`λ_1(t) ≥ λ_2(t) ≥ … ≥ 0` (rearrangement order); each λ_k is 1-Lipschitz
(`|λ_k(t₂) − λ_k(t₁)| ≤ |t₂ − t₁|`, checked with grid slack); support of every λ_k
lies in `[min b, max d]`; and `sup_t λ_k(t) ≤ (k-th largest persistence)/2`.
Violations indicate resampling, smoothing, or normalisation applied silently — the
landscape analogue of an undeclared convention change.
→ enforces I1a for the landscape lane.

**L2. Exact norm identity (the landscape closed-form oracle).**
Because `{λ_k(t)}_k` is the descending rearrangement of `{tent_i(t)}_i` at every t,
`Σ_k λ_k(t)^p = Σ_i tent_i(t)^p` **pointwise and exactly**, for every finite p.
Integrating, with `h_i = persᵢ/2` (each tent contributes `∫ tent^p = 2·h^(p+1)/(p+1)`):

`Σ_k ‖λ_k‖_p^p = Σ_i 2·h_i^(p+1)/(p+1)`, in particular
**`Σ_k ∫ λ_k(t)² dt = (2/3) · Σ_i (persᵢ/2)³`.**

An O(n) closed form for the total L² content of the *entire* landscape, computable
from the diagram alone. Any landscape implementation's total squared norm must match
it up to (a) quantified grid error and (b) truncation: computing only K levels drops
the *smallest* rearranged values, so `computed ≤ closed form` always, with equality
(to grid tolerance) when K ≥ the diagram's maximum overlap depth. A computed norm
*above* the closed form, or materially below it at sufficient K, is a bug —
this catches wrong grid weights, dropped levels, silent normalisation, and
unit-of-integration errors in one identity.
*Scope:* holds for the standard unweighted full-support landscape; a pipeline using a
windowed or weighted variant must declare it (I1a identity block), and the check then
applies to the declared variant's own closed form.
→ enforces I1a/I1b for the landscape lane (this *is* the landscape impossibility
screen).

**L3. Stability cross-check between the two pipelines.**
Landscape ∞-stability (Bubenik 2015): `sup_k ‖λ_k(A) − λ_k(B)‖_∞ ≤ bottleneck(A, B)`.
This couples the landscape code to the diagram-metric code through a theorem: compute
the left side with the landscape pipeline and the right side with hera's bottleneck,
and a violation proves one of the two independent implementations wrong. A derived L²
form via `‖f‖₂² ≤ ‖f‖_∞·‖f‖₁`:
`Σ_k ‖λ_k(A) − λ_k(B)‖₂² ≤ bottleneck(A,B) · (Σ_i h_i²(A) + Σ_j h_j²(B))`
(using `Σ_k ‖λ_k‖₁ = Σ_i h_i²` from L2 at p = 1), bounding the *headline landscape L²
distance itself* by independently computable quantities.
→ the dual-metric mandate becomes mutually self-checking rather than merely parallel.

### P — Permutation-test and null-model checks

**P1. p-value grid membership.**
A Monte-Carlo permutation p-value with B null draws is `(b + 1)/(B + 1)` for an
integer b ∈ [0, B] (the add-one form is the contract-locked estimator). Check:
`p·(B + 1) − 1` is within tolerance of an integer in range. O(1) per reported
p-value; screens every result JSON.
*Historical catch:* the Class-10 denominator contradiction (P01-A's
`1 + N_pairs` prose vs the locked `null draws` denominator) is detectable
mechanically — a p-value on the wrong grid fails membership against the artifact's
recorded B.
→ enforces I8c/I10a for the p-value formula as a registry object.

**P2. Double-null calibration (statistical, and says so).**
For data generated *from the test's own null*, a valid permutation test satisfies
`P(p ≤ α) ≤ α` (exact superuniformity of the add-one estimator under
exchangeability). Harness: run the full test M times on null-generated data; reject
if the empirical rejection rate at any α on a small grid exceeds
`α + one-sided binomial/DKW slack`. Anti-conservatism ⇒ the test is invalid (wrong
exchangeability, leaky conditioning, seed reuse). This is the T1.41 double-null
concept generalized from a one-off panel into a standing harness — and it is the only
battery member with a statistical (not certain) verdict, which is why its
significance level is part of its identity block.
→ enforces I2d's "not structurally centered" clause; subsumes the parked T1.41
design.

**P3. Null-sensitivity probe (the vacuous-null detector).**
Before any permutation null is trusted, verify the null operation *perturbs the
statistic's actual input object*: draw probe transforms, recompute the statistic, and
require that it varies (nonzero variance across draws, and at least one draw differing
from observed). O(probes × statistic cost).
*Historical catch:* `_label_shuffle`/`_cohort_shuffle` permuted rows of an
already-embedded point cloud; VR persistence is set-valued, so every "null draw" had
the identical statistic — Table 1's negative controls could neither pass nor fail.
P3 rejects that null in three probe draws.
→ enforces I2d directly.

### D — Diagram well-formedness (preconditions)

**D1.** Every diagram consumed or emitted: shape (n, 2); `birth ≤ death` for every
finite pair; no NaN; infinite-death pairs explicitly filtered or explicitly declared
(never silently mixed into finite-pair arithmetic). Cheap admission predicate ahead of
all other checks.
→ supports I1a, I8c.

---

## 3. Check → invariant → historical instance

| Check | Invariants | Would have caught (documented instance) |
|---|---|---|
| W1 closed-form empty oracle | I1a | convention drift (no historical instance; preventive) |
| W2 diagonal bound | I1b | USoc frozen H₁ 233.68 (bound ~35.8); α-sweep means ~277 (bound ~20) |
| W3 Hungarian mini-oracle | I1a, I1c, I2b | the greedy fallback itself (18–56× H₁ inflation, ρ̂ ≈ 1 signature) |
| W4 metric axioms | I1a, I1c | approximate matchers at any scale |
| W5 bottleneck sandwich | I1a, I1b | gross inflation/deflation at production scale (233.68 also fails W5's upper bound) |
| L1 landscape structure | I1a | silent smoothing/normalisation (preventive) |
| L2 norm identity | I1a, I1b | grid/truncation/normalisation errors in the certified lane (preventive) |
| L3 stability cross-check | dual-metric mandate | divergence between the two pipelines (preventive) |
| P1 p-value grid | I8c, I10a | the `1 + N_pairs` denominator contradiction (Class 10) |
| P2 double-null calibration | I2d | anti-conservative test construction; T1.41's target class |
| P3 null-sensitivity probe | I2d | the invariant label/cohort-shuffle nulls (Class 2) |
| D1 well-formedness | I1a, I8c | malformed-diagram arithmetic (preventive) |

Negative controls shipped in the test suite (I2b compliance): a reimplemented greedy
rank-matcher (fails W2, W3, W4); a no-zero-diagonal augmented matcher reproducing the
§4 defect (fails W3 agreement); scaled/shuffled landscapes (fail L1, L2); off-grid
p-values `b/B` (fail P1); a constant-under-null statistic (fails P3); an
anti-conservative p-value procedure (fails P2).

## 4. Defect noted in passing (not fixed here)

`trajectory_tda/validation/wasserstein_null_tests.py::_scipy` fallback builds the
augmented cost matrix with diagonal–diagonal entries equal to the distance *between
the two diagonal projections* instead of 0. Whenever the optimal plan matches at
least one real–real pair, the perfect matching is forced to pair surplus diagonal
slots at positive cost, so the fallback **over-estimates** W_q — it is an upper-biased
approximation, not the same estimand by a different algorithm (the failure inventory's
Class-1 "benign fallback" contrast overstates it). It is disclosed as an
approximation in its own docstring, so this is a documentation/severity correction
plus a one-line fix (zero the diagonal–diagonal block), flagged as a separate task.
The battery's `wasserstein_exact_small` implements the correct reduction and the test
suite demonstrates the discrepancy on a constructed pair.

## 5. Integration path (follow-up, not this change)

1. **Result-file ingestion (ARS / Gate 7):** W2, P1, D1 run per artifact at admission
   using retained per-diagram/per-pair fields; artifacts without enough retained data
   for W2 are marked non-citable (I1b's own fallback clause). The Markov-2 W₂-only
   recompute (2026-07-17 pre-registration, H6-narrowed scope) should be the first
   producer whose outputs are screened at write time.
2. **Solver certification at dispatch:** W1, W3, W4, W5 as a pre-run certification
   block any battery/pipeline executes against its *resolved* solver before heavy
   compute — turning "solver identity" from a recorded string into a demonstrated
   property (I1a with teeth).
3. **Landscape lane:** L1, L2 as assertions inside the landscape vectorisation path;
   L3 as a per-run cross-check wherever both metrics are computed on the same pairs
   (the dual-metric mandate makes that ubiquitous).
4. **Null admission:** P3 as a hard gate in any new permutation-null spec (I2d);
   P2 as a slow-marked calibration run required once per test design, not per run.
5. **CI:** the delivered `tests/shared/test_math_invariants.py` runs under
   `-m validation` and is itself the battery's liveness proof (every check
   demonstrated firing on its negative control, per I2b).
