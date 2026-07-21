# S2 — Statement Authorship & Referent Check: Fixed-Margin Max-ARI Concentration Bound

**Date:** 2026-07-07 · **Review integrated:** 2026-07-20
**Status:** Statements authored and revised under adversarial review; awaiting (i) Stephen's countersignature + claim-grade decision (F7) and (ii) the two owner decisions below, then Leanstral proof orchestration (Sonnet task per scout plan §7)
**Statement author:** Claude (Fable 5) — per the statement/prover authorship split (scout plan §3.1): Leanstral must not alter these statements; it supplies proof terms and auxiliary *private lemmas* only. Auxiliary **definitions, notation, macros, and instances are statement-side objects** and follow the proposal-return loop, not prover authorship (05a M1). Any statement change (including "equivalent" re-encodings) stales this document and requires re-review.
**Independent statement reviewer:** Stephen, or a fresh Fable/Opus session (scout plan §8 item 5) — NOT this session's continuation. **Epistemic grade (Stephen, 2026-07-21):** the S2 max-ARI *certification* is **R2** (a correction/verification affecting evidence validity, W5 §9), so a fresh independent session may perform the referent-adequacy review. The *downstream* step — promoting the normalised bracket into P01-A reviewer-facing prose — is separately **R3 claim promotion** and requires Stephen regardless (out of scope for this spike). **Remaining gate for the proof spike: Stephen's countersignature of the S2 adversarial review + the R2 referent-adequacy review, both before proof search begins (05a §3 item 9).**
**Hammer-proof rule (F6, resolved 2026-07-21):** the governing S3a/S3b prereg §8.4 restriction controls — no opaque hammer-only proofs unless short and auditable (stricter than 05a §3.4; 05a §8.2 precedence). See §5 item 3.

> **Review integration note (2026-07-20).** Adversarial review `adversarial-S2-max-ari-statement-review-2026-07-20.md` returned `accept_with_required_changes` and independently re-derived every constant (all match bit-for-bit). This revision applies the three Majors and the minors: **F1** adds the ARI/normalised glue statements (T5/T6) that §1's certified scope actually requires; **F2** adds the bidirectional anchoring obligation **G** (an inequality proof alone can never catch an *inflated* recorded constant); **F3** replaces the broken transpose fallback with the pre-authored **T4-coarse**. Owner decisions remain open: **F6** (which hammer-proof rule governs — route via the 05a review) and **F7** (claim grade + countersignature). Editing this file moves its git blob hash; `statement_source` must be re-pinned to the revised blob before the diff base is used (F-review consistency matrix).

---

## 1. Referent — what claim this assures, in plain English

The T1.23d result `results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-24.json` (P01-A, closes reviewer B9) reports a **bracket** on the maximum-achievable ARI for the OM k=7 vs GMM k=7 comparison at fixed cluster-size margins:

- **Achievable lower bound** — ARI 0.8396675957148108, pair overlap 59,684,973, witnessed by the concrete `achieving_table` in the JSON. *Runtime-checkable; not the assurance gap.*
- **Rigorous upper bound** — ARI 0.8606691921483836, pair overlap 60,862,048, justified only by the concentration-relaxation argument in the docstring of `trajectory_tda/analysis/panel/fixed_margin_max_ari.py::concentration_upper_bound_sumsq`. **This is the assurance gap:** if that argument is wrong, the bracket and the published `normalised_ari_bracket` [0.30346, 0.31105] are wrong, and no runtime check can detect it. Its predecessor construction *was* wrong (trivial 1.0, superseded 2026-06-24).

**The claim to certify (scope now matched to the authored statements per F1):**

> For every 7×7 table of non-negative integers with row sums (3438, 2086, 2949, 2489, 9003, 1775, 5540) — the OM k=7 cluster sizes — and column sums (3787, 7358, 5415, 3333, 3510, 1813, 2064) — the GMM k=7 regime sizes — the within-cell co-clustered pair count Σᵢⱼ C(nᵢⱼ, 2) is at most 60,862,048 (**T4**, kernel-pinned exactly by **G**). Consequently, via the fixed-margin ARI monotonicity (**T3** instantiated as **T5**), the maximum-achievable ARI is at most the exact rational whose float image is 0.8606691921483836; and via **T6** the normalised observed ARI `observed / ari_upper` is a true lower bound on the normalised ARI. The lower end of the published bracket (pair overlap 59,684,973) is certified by the concrete witness **W**.

Margin totals: both sum to n = 27,280 (verified against `label_counts` in the JSON).

**Anchoring guard — now bidirectional (F2).** The certified statements are *inequalities*, so a proof of `≤ 60,862,048` succeeds for **any** recorded constant at or above the true greedy value: a *deflated* wrong constant makes T4 unprovable (caught), but an *inflated* wrong constant proves silently (uncaught) — the exact failure the predecessor's trivial-1.0 exemplifies in the other direction. Obligation **G** closes this by pinning the derived greedy value with a kernel **equality** (`= 121751376 := by decide`) and deriving the pair bound from it (`(121751376 − 27280)/2 = 60862048`). The constants below are therefore **derived in-kernel by G, not asserted**; if the Lean-side computation yields a different value, that is a **finding to report against the artefact** (05a §3.5 discrepancy record), never a mismatch to force.

## 2. Mathematical content (informal, for the reviewer)

Fix column sums c₁,…,c_C. In any feasible table, every entry satisfies nᵢⱼ ≤ cⱼ (column j sums to cⱼ over non-negative entries). Relax the column-sum *equalities* to these per-cell *capacity bounds*: each row i then independently maximises Σⱼ xⱼ² subject to Σⱼ xⱼ = rᵢ, 0 ≤ xⱼ ≤ cⱼ. Because x ↦ Σx² is convex (Schur-convex), the maximum over this box-and-simplex is attained by **greedy concentration**: fill the largest capacities first. Summing the greedy values over rows bounds Σᵢⱼ nᵢⱼ²; the symmetric column relaxation gives a second bound. **For these margins the row relaxation (c = gmmCounts) is the winning side** — it yields Σn² ≤ 121,751,376 → pair bound 60,862,048; the column relaxation yields only Σn² ≤ 128,779,812 → pair bound 64,376,266 and is *not* a proof route for T4's constant (F3 correction). Finally, Σᵢⱼ C(nᵢⱼ,2) = (Σ nᵢⱼ² − n)/2, and ARI at fixed margins is an increasing affine function of the pair count, so the pair-count bound transfers to ARI.

Suggested proof routes for the core lemma (T1): direct exchange induction on the sorted capacity list, or majorization + Schur convexity if mathlib support suffices. Prover's choice; the *statement* is fixed.

## 3. Formal statements (authored)

Encoding freedom: the prover/orchestrator may adjust to current mathlib idiom (`List.mergeSort` argument form, `getElem` vs `get`, `Finset.sum` notation) **provided the mathematical content is unchanged and the final signatures come back through statement re-review** (this is the sanctioned valve for mathlib idiom churn; instances must not invent looser ones). No hypothesis may be added or weakened without re-review.

### Definition — greedy concentration value

```lean
/-- Greedy fill of `t` units into capacities `caps` (intended: sorted descending),
    returning the sum of squares of the placed amounts. Mirrors
    `_maxsq_line` in fixed_margin_max_ari.py (the Python early-`break` at
    `rem ≤ 0` equals the `min t cap = 0` continuation here). -/
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

The symmetric column relaxation is T2 applied to the transpose — no separate theorem. **T4 is proved by T2 applied directly (c = gmmCounts); the transpose is retained only as the mathematical justification for the code's `min` and is not a proof route for T4's constant** (F3).

### T3 — ARI is monotone in the pair count at fixed margins

```lean
/-- At fixed margins the ARI is an increasing function of the within-cell pair
    count whenever max_index > expected_index. Stated over ℚ.
    (F4: `htp` dropped — over ℚ total division the conclusion follows from
    `hden` alone; `tp` enters only through the caller's definition of `hden`.) -/
theorem ari_mono (rp cp tp : ℚ)
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

Proof shape: T2 (direct, c = gmmCounts) + in-kernel evaluation of the greedy value (obligation **G**) + the identity Σ C(n,2) = (Σ n² − n)/2 with Σ n = 27,280 from `hrow`. Parity note: the pair-count bound is ⌊(ub_sumsq − n)/2⌋; here (121,751,376 − 27,280) is even, so the division is exact — but the floor direction must still be taken explicitly, not assumed. `Nat.choose · 2` evaluation: prefer rewriting via `Nat.choose_two_right` before `decide` if the kernel is slow (§5 item 3).

### T5 — concrete ARI upper bound (F1; instantiates T3 at the B9 margins)

```lean
def rpQ : ℚ := 72965958   -- row_pairs  = Σ C(omCounts_i, 2),   pinned by G
def cpQ : ℚ := 64376266   -- col_pairs  = Σ C(gmmCounts_j, 2),  pinned by G
def tpQ : ℚ := 372085560  -- C(27280, 2),                       pinned by G

/-- Any table on the B9 margins has ARI at most the value at pair count
    60,862,048 — an exact rational; its float image 0.8606691921483836 is a
    runtime-checked, NOT kernel-certified, claim (float rounding is outside
    the certified core). -/
theorem b9_ari_le (M : Fin 7 → Fin 7 → ℕ)
    (hrow : ∀ i, ∑ j, M i j = omCounts[i.val]!)
    (hcol : ∀ j, ∑ i, M i j = gmmCounts[j.val]!) :
    ((∑ i, ∑ j, Nat.choose (M i j) 2 : ℚ) - rpQ * cpQ / tpQ)
        / ((rpQ + cpQ) / 2 - rpQ * cpQ / tpQ)
      ≤ ((60862048 : ℚ) - rpQ * cpQ / tpQ)
        / ((rpQ + cpQ) / 2 - rpQ * cpQ / tpQ)
```

Proof: T4 gives the pair-count bound; T3 (with `hden > 0` discharged by `norm_num` on the pinned rationals — positivity independently verified: `hden = 1737854436932491/31007130 > 0`) transfers it to ARI.

### T6 — normalised transfer (F1)

```lean
/-- A certified upper bound on the max ARI gives a true lower bound on the
    normalised ARI `observed / ari_max`. -/
theorem normalised_lower (obs ub maxAri : ℚ)
    (hobs : 0 ≤ obs) (hmax : 0 < maxAri) (hle : maxAri ≤ ub) :
    obs / ub ≤ obs / maxAri
```

### G — anchoring obligation (F2; mandatory, both directions)

```lean
/-- The greedy value, derived pair bound, and the ARI margins are pinned by
    kernel computation so an INFLATED recorded constant cannot pass silently. -/
example : (∑ i : Fin 7, greedyFill (omCounts[i.val]!)
    (gmmCounts.mergeSort (· ≥ ·))) = 121751376 := by decide
example : (121751376 - 27280) / 2 = 60862048 := by norm_num
-- rpQ/cpQ/tpQ are themselves derived, closing F2 "one level up":
example : (omCounts.map (fun r => Nat.choose r 2)).sum = 72965958 := by decide
example : (gmmCounts.map (fun c => Nat.choose c 2)).sum = 64376266 := by decide
example : Nat.choose 27280 2 = 372085560 := by decide
```

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

This proves T4's hypotheses are satisfiable (the theorem is not vacuously true) and kernel-certifies the achievable lower bound, closing *both* ends of the published bracket. The same witness satisfies T4-coarse's hypotheses (59,684,973 ≤ 65,560,990), so the fallback is also non-vacuous.

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

### T4-coarse — pre-authored fallback bound (F3; used only if T1 resists the timebox)

```lean
/-- Fallback bound needing no concentration lemma and no sorting: for each row,
    every entry satisfies x_j ≤ min(r_i, max c_j), hence Σ_j x_j² ≤ r_i·min(r_i, max c_j).
    Yields Σn² ≤ 131,149,261 → pair bound 65,560,990 (weaker than T4's
    60,862,048 but coherent and referent-relevant). The transpose relaxation is
    NOT a fallback: it reaches only 64,376,266 and still factors through T1. -/
theorem b9_pair_overlap_le_coarse
    (M : Fin 7 → Fin 7 → ℕ)
    (hrow : ∀ i, ∑ j, M i j = omCounts[i.val]!)
    (hcol : ∀ j, ∑ i, M i j = gmmCounts[j.val]!) :
    ∑ i, ∑ j, Nat.choose (M i j) 2 ≤ 65560990
```

Fallback anchoring (parallel to G; note (131,149,261 − 27,280) is odd, so the floor is strict):

```lean
example : (∑ i : Fin 7, omCounts[i.val]! * min (omCounts[i.val]!) 7358) = 131149261 := by decide
example : (131149261 - 27280) / 2 = 65560990 := by norm_num  -- Nat floor division
```

If the fallback is taken, T5/T6 re-instantiate with `65560990` in place of `60862048` (ARI upper ≈ 0.94451, normalised lower ≈ 0.2765), and the §5 item 7 `[RESULT]` referent states the coarse scope.

## 4. What this artefact does and does NOT certify

| Certified (on kernel acceptance) | NOT certified — remains on existing assurance |
|---|---|
| Pair-overlap upper bound 60,862,048 for the exact B9 margins (T2+T4), kernel-pinned exactly by **G** | That `fixed_margin_max_ari.py` correctly *implements* the greedy — irrelevant once the bound itself is proved |
| Pair-overlap lower bound 59,684,973 via the concrete witness (W) | The observed ARI 0.2611807, the permutation null, the bootstrap CI (carried verbatim from T1.23c; separate provenance) |
| **ARI upper bound as an exact rational (T5)** and **normalised-ARI lower bound (T6)** — the ARI/normalised claims §1 makes are now backed by authored statements (F1) | The **float** values in the JSON: `ari` fields are float images of the certified rationals — rounding enters only in the final divisions (documented; no claim depends on it) |
| ARI monotone transfer at fixed margins (T3) over ℚ | That the margins in the JSON match the underlying clusterings — that is T1.23b/c provenance, already contract-checked (added to the §5 re-review checklist) |
| Non-vacuity of the corollaries' hypotheses (W); falsifiability of the encoding (M) | The NW+2-opt search *quality* (heuristic; its output is certified only via W) |

## 5. Acceptance contract instantiation (per prereg §8 + 05a addendum)

1. `lake build` exits 0 on a pinned toolchain; record `lean-toolchain` and mathlib commit in `build.log`. **Per 05a C1, these checks are established by the accepting gate's own re-execution against the hashed artefact bytes, not by producer-supplied logs.**
2. No `sorry` / `admit` (grep + `#print axioms`) on **T1–T6, G, W, M, T4-coarse**.
3. Axiom audit: only `propext`, `Classical.choice`, `Quot.sound`. This mechanically enforces the `native_decide` ban too — `native_decide` introduces `Lean.ofReduceBool`/`Lean.trustCompiler`, which fail the ⊆-check. `native_decide` remains prohibited unless separately approved; plain `decide` / `norm_num` preferred. Document kernel-reduction cost if `decide` on the 7×7 sums is slow (mitigation: `Nat.choose_two_right` rewrite). **Proof style: the governing S3a/S3b prereg §8.4 rule controls (resolved 2026-07-21) — no opaque hammer-only proof unless short and auditable; this is stricter than 05a §3.4 and governs this instance per 05a §8.2.**
4. Constants 60,862,048 / 59,684,973 / 27,280 / 121,751,376 / rp / cp / tp **derived in-proof AND pinned by the G equality obligations** (F2); never introduced by axiom or unchecked `have`. A strict-inequality-only derivation does not satisfy this item.
5. Statement-referent check: final `.lean` signatures diffed against §3 by the independent reviewer; the diff base is the **git blob hash of this revised document** recorded as `statement_source` (05a §2). Any drift → re-review. Re-review checklist additionally confirms the JSON `label_counts` margins equal omCounts/gmmCounts.
6. Scratch/promoted separation per the governing pre-registration's artefact-contract and layout sections; suggested layout `lean-tda-spikes/S2/MaxAriBound.lean` + `README.md` + `build.log` + `axiom-audit.md` + `result.md`. **Repository anchor:** the Lean project lives outside TDL — bind its repo identity + commit in the evidence, not bare file hashes (05a m3).
7. Promoted artefact recorded with a vault `[RESULT]` entry referencing this statement document and the T1.23d result JSON; the result entry carries the referent line verbatim from §1 **at whichever scope was actually proved (full T4/T5/T6, or the T4-coarse fallback)**.

## 6. Handoff and stop rule

Next step (Sonnet, low–medium reasoning, per scout plan §7): orchestrate Leanstral against §3 in a fresh `lean-tda-spikes/S2/` module. Order: **T1** first (the only lemma with real proof-search content), then T2 (row-wise application), T3 (one-line `div_le_div_of_le_left`-family algebra), T4 + G + W + M (computation-heavy, proof-search-light), then T5 (T3∘T4) and T6 (elementary `div` monotonicity). Timebox: 1 day per the scout plan.

**Stop rule (F3, corrected):** if T1 resists after the timebox, deliver the **pre-authored T4-coarse** (§3) instead, with an obstruction report on T1, and re-instantiate T5/T6/G at the coarse constant. T4-coarse needs no sorting and no exchange argument, so it does not share T1's failure mode. The transposed relaxation is **not** a fallback — it reaches only 64,376,266 (> 60,862,048) and still factors through T1. Delivering T4-coarse+W+M+G(coarse) is a **Partial** (weaker but sound certificate), not a failure; the Sonnet orchestrator must not author any new statement mid-spike (authorship split) — only the statements in this document are authorized.
