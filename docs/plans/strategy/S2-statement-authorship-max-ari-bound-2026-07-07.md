# S2 — Statement Authorship & Referent Check: Fixed-Margin Max-ARI Concentration Bound

**Date:** 2026-07-07
**Status:** Statements authored; awaiting independent statement review, then Leanstral proof orchestration (Sonnet task per scout plan §7)
**Statement author:** Claude (Fable 5) — per the statement/prover authorship split (scout plan §3.1): Leanstral must not alter these statements; it supplies proof terms only. Any statement change (including "equivalent" re-encodings) stales this document and requires re-review.
**Independent statement reviewer:** Stephen, or a fresh Fable/Opus session (scout plan §8 item 5) — NOT this session's continuation.

---

## 1. Referent — what claim this assures, in plain English

The T1.23d result `results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-24.json` (P01-A, closes reviewer B9) reports a **bracket** on the maximum-achievable ARI for the OM k=7 vs GMM k=7 comparison at fixed cluster-size margins:

- **Achievable lower bound** — ARI 0.8396675957148108, pair overlap 59,684,973, witnessed by the concrete `achieving_table` in the JSON. *Runtime-checkable; not the assurance gap.*
- **Rigorous upper bound** — ARI 0.8606691921483836, pair overlap 60,862,048, justified only by the concentration-relaxation argument in the docstring of `trajectory_tda/analysis/panel/fixed_margin_max_ari.py::concentration_upper_bound_sumsq`. **This is the assurance gap:** if that argument is wrong, the bracket and the published `normalised_ari_bracket` [0.30346, 0.31105] are wrong, and no runtime check can detect it. Its predecessor construction *was* wrong (trivial 1.0, superseded 2026-06-24).

**The claim to certify:**

> For every 7×7 table of non-negative integers with row sums (3438, 2086, 2949, 2489, 9003, 1775, 5540) — the OM k=7 cluster sizes — and column sums (3787, 7358, 5415, 3333, 3510, 1813, 2064) — the GMM k=7 regime sizes — the within-cell co-clustered pair count Σᵢⱼ C(nᵢⱼ, 2) is at most 60,862,048. Consequently the fixed-margin maximum-achievable ARI is at most the exact rational whose float image is 0.8606691921483836, and `normalised_lower_bound = observed/ari_upper` is a true lower bound on the normalised ARI.

Margin totals: both sum to n = 27,280 (verified against `label_counts` in the JSON).

**Anchoring guard (skill-obs #19, W5 §13.2):** the constants 60,862,048 and 59,684,973 above are *recorded values to be independently derived inside Lean by computation* (`decide`-class evaluation of the greedy), never asserted by `sorry`-adjacent shortcuts or copied as axioms. If the Lean-side computation yields a different constant, that is a **finding to report**, not a mismatch to force.

## 2. Mathematical content (informal, for the reviewer)

Fix column sums c₁,…,C. In any feasible table, every entry satisfies nᵢⱼ ≤ cⱼ (column j sums to cⱼ over non-negative entries). Relax the column-sum *equalities* to these per-cell *capacity bounds*: each row i then independently maximises Σⱼ xⱼ² subject to Σⱼ xⱼ = rᵢ, 0 ≤ xⱼ ≤ cⱼ. Because x ↦ Σx² is convex (Schur-convex), the maximum over this box-and-simplex is attained by **greedy concentration**: fill the largest capacities first. Summing the greedy values over rows bounds Σᵢⱼ nᵢⱼ²; the symmetric column relaxation gives a second bound; the code takes the min. Finally, Σᵢⱼ C(nᵢⱼ,2) = (Σ nᵢⱼ² − n)/2, and ARI at fixed margins is an increasing affine function of the pair count, so the pair-count bound transfers to ARI.

Suggested proof routes for the core lemma (T1): direct exchange induction on the sorted capacity list, or majorization + Schur convexity if mathlib support suffices. Prover's choice; the *statement* is fixed.

## 3. Formal statements (authored)

Encoding freedom: the prover/orchestrator may adjust to current mathlib idiom (`List.mergeSort` argument form, `getElem` vs `get`, `Finset.sum` notation) **provided the mathematical content is unchanged and the final signatures come back through statement re-review.** No hypothesis may be added or weakened without re-review.

### Definition — greedy concentration value

```lean
/-- Greedy fill of `t` units into capacities `caps` (intended: sorted descending),
    returning the sum of squares of the placed amounts. Mirrors
    `_maxsq_line` in fixed_margin_max_ari.py. -/
def greedyFill : ℕ → List ℕ → ℕ
  | _, [] => 0
  | t, cap :: caps => min t cap ^ 2 + greedyFill (t - min t cap) caps
```

### T1 — single-line concentration bound (the core lemma)

```lean
/-- Any capacity-respecting allocation is dominated in sum-of-squares by the
    greedy fill of the same total into the descending-sorted capacities. -/
theorem sumSq_le_greedyFill (caps x : List ℕ)
    (hlen : x.length = caps.length)
    (hcap : ∀ i (hi : i < x.length), x[i] ≤ caps[i]'(hlen ▸ hi)) :
    (x.map (· ^ 2)).sum ≤ greedyFill x.sum (caps.mergeSort (· ≥ ·))
```

### T2 — matrix concentration bound (row relaxation)

```lean
/-- Relaxing column-sum equalities to per-cell caps: the total sum of squares of
    any table is bounded by the row-wise greedy fills into the sorted column
    capacities. Only the column-sum hypothesis is needed. -/
theorem matrix_sumSq_le_rowConcentration {R C : ℕ}
    (M : Fin R → Fin C → ℕ) (c : Fin C → ℕ)
    (hcol : ∀ j, ∑ i, M i j = c j) :
    ∑ i, ∑ j, (M i j) ^ 2
      ≤ ∑ i, greedyFill (∑ j, M i j) ((List.ofFn c).mergeSort (· ≥ ·))
```

The symmetric column relaxation is T2 applied to the transpose — no separate theorem. The code's `min` of the two bounds needs no lemma: the corollary (T4) may be proved through whichever side reaches the recorded constant.

### T3 — ARI is monotone in the pair count at fixed margins

```lean
/-- At fixed margins the ARI is an increasing function of the within-cell pair
    count whenever max_index > expected_index. Stated over ℚ. -/
theorem ari_mono (rp cp tp : ℚ) (htp : 0 < tp)
    (hden : 0 < (rp + cp) / 2 - rp * cp / tp)
    {s₁ s₂ : ℚ} (h : s₁ ≤ s₂) :
    (s₁ - rp * cp / tp) / ((rp + cp) / 2 - rp * cp / tp)
      ≤ (s₂ - rp * cp / tp) / ((rp + cp) / 2 - rp * cp / tp)
```

### T4 — the B9 corollary (concrete margins, concrete constant)

```lean
def omCounts  : List ℕ := [3438, 2086, 2949, 2489, 9003, 1775, 5540]
def gmmCounts : List ℕ := [3787, 7358, 5415, 3333, 3510, 1813, 2064]

/-- The certified upper bound for the B9 OM-vs-GMM normalisation:
    no table with the T1.23d margins exceeds 60,862,048 co-clustered pairs. -/
theorem b9_pair_overlap_le
    (M : Fin 7 → Fin 7 → ℕ)
    (hrow : ∀ i, ∑ j, M i j = omCounts[i.val]!)
    (hcol : ∀ j, ∑ i, M i j = gmmCounts[j.val]!) :
    ∑ i, ∑ j, Nat.choose (M i j) 2 ≤ 60862048
```

Proof shape: T2 (direct or transposed) + in-kernel evaluation of the greedy value + the identity Σ C(n,2) = (Σ n² − n)/2 with Σ n = 27,280 from `hrow`. Parity note: the pair-count bound is ⌊(ub_sumsq − n)/2⌋; the floor direction is safe and must be taken explicitly, not assumed even.

### W — non-vacuity witness (mandatory; doubles as the lower-bound certificate)

```lean
def b9Table : Fin 7 → Fin 7 → ℕ :=
  ![![   0,    0,    0,    0, 3438,    0,    0],
    ![   0,    0,    0,   22,    0,    0, 2064],
    ![   0,    0,    0, 2949,    0,    0,    0],
    ![2489,    0,    0,    0,    0,    0,    0],
    ![1298, 7358,    0,  347,    0,    0,    0],
    ![   0,    0,    0,    0,    0, 1775,    0],
    ![   0,    0, 5415,   15,   72,   38,    0]]

example : ∀ i, ∑ j, b9Table i j = omCounts[i.val]!  := by decide
example : ∀ j, ∑ i, b9Table i j = gmmCounts[j.val]! := by decide
example : ∑ i, ∑ j, Nat.choose (b9Table i j) 2 = 59684973 := by decide
```

This proves T4's hypotheses are satisfiable (the theorem is not vacuously true) and kernel-certifies the achievable lower bound, closing *both* ends of the published bracket.

### M — mutation obligation (mandatory; guards the encoding)

```lean
/-- The bound is tight enough to be falsifiable: one below the witness value
    must be refutable. If this cannot be proved, the encoding of T4 is broken. -/
example : ¬ (∀ M : Fin 7 → Fin 7 → ℕ,
    (∀ i, ∑ j, M i j = omCounts[i.val]!) →
    (∀ j, ∑ i, M i j = gmmCounts[j.val]!) →
    ∑ i, ∑ j, Nat.choose (M i j) 2 ≤ 59684972) := by
  intro h
  exact absurd (h b9Table (by decide) (by decide)) (by decide)
```

## 4. What this artefact does and does NOT certify

| Certified (on kernel acceptance) | NOT certified — remains on existing assurance |
|---|---|
| Pair-overlap upper bound 60,862,048 for the exact B9 margins (T2+T4) | That `fixed_margin_max_ari.py` correctly *implements* the greedy — irrelevant once the bound itself is proved |
| Pair-overlap lower bound 59,684,973 via the concrete witness (W) | The observed ARI 0.2611807, the permutation null, the bootstrap CI (carried verbatim from T1.23c; separate provenance) |
| ARI monotone transfer at fixed margins (T3), hence the ARI bracket over ℚ | The float values in the JSON: `ari` fields are float images of the certified rationals — rounding enters only in the final divisions (documented, ≤1 ulp scale, no claim depends on it) |
| Non-vacuity of the corollary's hypotheses (W) | That the margins in the JSON match the underlying clusterings — that is T1.23b/c provenance, already contract-checked |
| | The NW+2-opt search *quality* (heuristic; its output is certified only via W) |

## 5. Acceptance contract instantiation (per prereg §8 + W5 addendum draft)

1. `lake build` exits 0 on a pinned toolchain; record `lean-toolchain` and mathlib commit in `build.log`.
2. No `sorry` / `admit` (grep + `#print axioms` on T1–T4, W, M).
3. Axiom audit: only `propext`, `Classical.choice`, `Quot.sound`. Any use of `native_decide` (which extends trust to the compiler) is **prohibited unless separately approved**; plain `decide` / `norm_num` preferred. Document kernel-reduction cost if `decide` on the 7×7 sums is slow.
4. Constants 60,862,048 / 59,684,973 / 27,280 derived in-proof, never introduced by axiom or unchecked `have`.
5. Statement-referent check: final `.lean` signatures diffed against §3 by the independent reviewer; any drift → re-review before promotion.
6. Scratch/promoted separation per prereg §9; suggested layout `lean-tda-spikes/S2/MaxAriBound.lean` + `README.md` + `build.log` + `axiom-audit.md` + `result.md`.
7. Promoted artefact recorded with a vault `[RESULT]` entry referencing this statement document and the T1.23d result JSON; the result entry carries the referent line verbatim from §1.

## 6. Handoff

Next step (Sonnet, low–medium reasoning, per scout plan §7): orchestrate Leanstral against §3 in a fresh `lean-tda-spikes/S2/` module, T1 first (it is the only lemma with real proof-search content), then T2 (row-wise application), T3 (one-line `div_le_div_of_le_left`-family algebra), then T4/W/M (computation-heavy, proof-search-light). Timebox: 1 day per the scout plan. Stop rule: if T1 resists after the timebox, deliver T4 restricted to the transposed relaxation with a documented obstruction report — a weaker but still referent-relevant certificate is a Partial, not a failure.
