# Adversarial Statement Review — S2 Fixed-Margin Max-ARI Concentration Bound

**Date:** 2026-07-20
**Reviewed document:** `docs/plans/strategy/S2-statement-authorship-max-ari-bound-2026-07-07.md` (committed 5cdb3d2, 2026-07-18; unmodified since)
**Reviewer:** Claude (Fable 5), fresh session — not a continuation of the authoring session. This review therefore satisfies the document's independence requirement for the independent statement review (S2 header; scout plan §8 item 5), subject to the reviewer-grade question in F7.
**Method:** adversarial-design-review skill; all constants re-derived by a standalone exact-arithmetic script (`fractions.Fraction` / integer arithmetic, zero imports from the TDL codebase — independent of `fixed_margin_max_ari.py`).

---

## Executive verdict: `accept_with_required_changes`

The authored statement set (greedyFill, T1–T4, W, M) is **mathematically correct, well-formed, and referent-faithful at the pair-count level**. Every constant in the document reproduces exactly under independent re-derivation, including the float images (see Verification Evidence). The witness table is valid; the mutation obligation is a sound falsifiability guard; T4 is provable via T2 applied **directly** (no transpose needed).

Three Majors must be fixed before dispatch:

1. **F1** — the certified scope claimed in §1/§4 (ARI bracket over ℚ, normalised lower bound) exceeds what T1–T4+W+M can deliver; the ARI-level and normalised-level glue is unstated, and under the authorship split nobody downstream may author it.
2. **F2** — the anchoring guard ("constants independently derived inside Lean") is one-directional and unmechanized: a `≤`-statement can never detect an *inflated* recorded constant.
3. **F3** — the §6 stop-rule fallback is broken three ways: the transposed relaxation yields 64,376,266 (> 60,862,048), so it **cannot prove T4's constant**; it still depends on T1, the exact lemma the fallback is meant to route around; and any genuine fallback is a different statement, which the authorship split forbids the Sonnet orchestrator from authoring mid-spike.

All three have cheap fixes (new pre-authored statements / one §4 rescope / one §6 rewrite). No Critical findings. The published bracket in the T1.23d JSON is not endangered by any finding — every failure mode found here degrades *detectability* or the *fallback path*, not the truth of the recorded numbers, which this review confirms.

---

## Verification evidence (independent re-derivation, 2026-07-20)

| Quantity | Document / JSON value | Re-derived | Match |
|---|---|---|---|
| n (both margin sums) | 27,280 | 27,280 | ✓ |
| Witness row sums | omCounts | (3438, 2086, 2949, 2489, 9003, 1775, 5540) | ✓ |
| Witness column sums | gmmCounts | (3787, 7358, 5415, 3333, 3510, 1813, 2064) | ✓ |
| Witness pair count | 59,684,973 | 59,684,973 | ✓ |
| Row-relaxation Σn² (T2 direct) | — | **121,751,376** | — |
| Column-relaxation Σn² (transpose) | — | **128,779,812** | — |
| min side | — | ROW (T2 direct, c = gmmCounts) | — |
| (ub_sumsq − n) parity | "floor is safe" | even (exact division) | ✓ |
| Pair upper bound | 60,862,048 | 60,862,048 | ✓ |
| rp, cp, tp | — | 72,965,958 / 64,376,266 / 372,085,560 | — |
| hden (max_index − expected) | > 0 assumed | exact 1737854436932491/31007130 > 0 | ✓ |
| float(exact ARI at 59,684,973) | 0.8396675957148108 | identical bit-for-bit | ✓ |
| float(exact ARI at 60,862,048) | 0.8606691921483836 | identical bit-for-bit | ✓ |
| normalised bracket | [0.30346238425045263, 0.31105252415739076] | identical bit-for-bit | ✓ |

Cited-source checks: the T1.23d JSON exists at the cited path with matching `label_counts`, `achieving_table` (byte-identical to `b9Table`), bracket fields, and the `supersedes` block confirming the "trivial 1.0 predecessor" claim. `_maxsq_line` / `concentration_upper_bound_sumsq` exist as cited; `greedyFill` mirrors `_maxsq_line` semantics exactly (the Python early-`break` at `rem ≤ 0` equals the Lean `min t cap = 0` continuation). The code floors the pair bound (`(ub_sumsq − n) // 2`, line 302) as the parity note requires. Prereg §8 ("Artefact contract") and §9 ("Repository layout", `lean-tda-spikes/` + `scratch/`) exist in `Pre-registration-Skeleton-S3a-S3b.md` and say what S2 §5 cites them for. The W5 addendum draft exists (`docs/plans/agentic-research-system/design/05a-lean-proof-evidence-class-addendum-2026-07-07.md`, status DRAFT `review_pending`) and its §3 acceptance contract matches S2 §5 items 1–5 (see F6 for the one divergence vs prereg §8.4).

**Currency (Lane 4):** no `lean-tda-spikes/` directory exists anywhere on disk (checked `C:\Users\steph\TDL` and `C:\Users\steph`); no S2 Lean artifacts exist; the document's "awaiting independent statement review" status matches live state. No addendum needed.

---

## Major findings

### F1 (Major) — Certified-scope overhang: the ARI-level and normalised-level claims have no authored statement

- **Claim:** §1's claim-to-certify ("Consequently the fixed-margin maximum-achievable ARI is at most the exact rational … and `normalised_lower_bound = observed/ari_upper` is a true lower bound on the normalised ARI") and §4's certified column ("ARI monotone transfer at fixed margins (T3), **hence the ARI bracket over ℚ**") promise ARI-level and normalised-level certification. The statement set delivers: a pair-count bracket (T4 + W) and a *generic* division-monotonicity lemma (T3) never instantiated at the concrete rp/cp/tp. No statement (a) instantiates T3 with rp = 72,965,958, cp = 64,376,266, tp = 372,085,560, (b) discharges `hden > 0` on those values, (c) states the concrete ARI upper bound as a rational, or (d) states the antitone division step `0 < maxAri ≤ ub → obs/ub ≤ obs/maxAri` needed for the normalised claim.
- **Evidence:** S2 §3 (statements T1–T4, W, M only); §1 claim paragraph; §4 row 3. Composition glue absent by inspection.
- **Failure scenario:** the spike delivers kernel-accepted T1–T4+W+M; acceptance §5 item 5 passes (signatures match §3); §5 item 7 writes a vault `[RESULT]` carrying the §1 referent verbatim — which asserts a certified ARI bracket the artifact does not contain. Under the authorship split, neither the Sonnet orchestrator nor Leanstral may author the missing glue; it either silently stays informal or gets authored by the wrong actor.
- **Impact:** validity of the *certification claim* (not of the numbers): the exact referent trap (skill-obs #13, 05a §2 `referent_note`) this document exists to guard. Also blocks 05a's plan to use S2 as the seed fixture/capability evidence (05a §6.1) at its stated strength.
- **Disposition:** fix now — author the glue statements in this document (statement author = Fable, satisfied by adopting the proposal below through owner sign-off), or rescope.
- **Proposed text:** add to §3 either (preferred) T5 + T6:

  ```lean
  def rpQ : ℚ := 72965958
  def cpQ : ℚ := 64376266
  def tpQ : ℚ := 372085560

  /-- T5 — concrete ARI upper bound: any table on the B9 margins has ARI at most
      the value at pair count 60,862,048 (an exact rational; float image
      0.8606691921483836 is a runtime-checked, not kernel-certified, claim). -/
  theorem b9_ari_le (M : Fin 7 → Fin 7 → ℕ)
      (hrow : ∀ i, ∑ j, M i j = omCounts[i.val]!)
      (hcol : ∀ j, ∑ i, M i j = gmmCounts[j.val]!) :
      ((∑ i, ∑ j, Nat.choose (M i j) 2 : ℚ) - rpQ * cpQ / tpQ)
          / ((rpQ + cpQ) / 2 - rpQ * cpQ / tpQ)
        ≤ ((60862048 : ℚ) - rpQ * cpQ / tpQ)
          / ((rpQ + cpQ) / 2 - rpQ * cpQ / tpQ)

  /-- T6 — normalised transfer: a certified upper bound on the max ARI gives a
      true lower bound on the normalised ARI. -/
  theorem normalised_lower (obs ub maxAri : ℚ)
      (hobs : 0 ≤ obs) (hmax : 0 < maxAri) (hle : maxAri ≤ ub) :
      obs / ub ≤ obs / maxAri
  ```

  (T5 needs `hden > 0` discharged by `norm_num` inside the proof; the positivity was verified exactly above. rpQ/cpQ/tpQ definitions must themselves be derived from omCounts/gmmCounts — see F2's equality-obligation pattern — or F2's critique recurs one level up.) Alternatively (minimal): strike "hence the ARI bracket over ℚ" from §4 row 3, move "ARI bracket" and "normalised lower bound" to the NOT-certified column, and re-word the §1 claim so the certified referent is the pair-count bracket only. The §5 item 7 `[RESULT]` referent line must match whichever scope is chosen.
- **Affected:** §1, §3, §4, §5.7; 05a §6.1; P01-A B9 disclosure text if it ever says "kernel-certified normalised bracket".

### F2 (Major) — Anchoring guard is one-directional and has no enforcement artifact

- **Claim:** §1's anchoring guard promises the constants are "independently derived inside Lean by computation … If the Lean-side computation yields a different constant, that is a finding to report." But T4 is an inequality: it is provable for **any** recorded constant ≥ the true greedy value. If the Python-side constant were inflated (the exact class of silent error the predecessor's trivial-1.0 failure exemplifies, in the other direction), every statement still proves, every §5 check passes, and the guard never fires. Deflation is caught (T4 becomes unprovable); inflation is invisible. §5 item 4 ("constants derived in-proof, never introduced by axiom or unchecked `have`") is satisfied vacuously by a ≤-proof and never forces the equality the guard's prose promises.
- **Evidence:** §1 anchoring-guard paragraph; T4's `≤ 60862048` goal; §5 item 4; absence of any equality obligation in §3.
- **Failure scenario:** a future regeneration of the JSON with a subtly buggy `_maxsq_line` records ub 61,000,000; a re-run of this pipeline proves `≤ 61000000` without complaint; the published bracket silently widens; "kernel-certified" is claimed for a constant no kernel computation ever pinned. (Today's constant is correct — verified above — so this is a control gap, not a present error.)
- **Impact:** the guard the document itself designates as the anti-anchoring defence (skill-obs #19, W5 §13.2) is aspirational prose; tightness of the certified bound is unverifiable in-kernel. Soundness of the *published* claim survives (an inflated upper bound still yields a true normalised lower bound), which is why this is Major, not Critical.
- **Disposition:** fix now — add a mandatory equality obligation **G** to §3:

  ```lean
  /-- G — anchoring: the greedy value and derived pair bound are pinned by
      kernel computation, both directions. -/
  example : (∑ i : Fin 7, greedyFill (omCounts[i.val]!)
      (gmmCounts.mergeSort (· ≥ ·))) = 121751376 := by decide
  example : (121751376 - 27280) / 2 = 60862048 := by norm_num
  ```

  and add G to the §5 item 2/3 audit surface (`#print axioms` list) and to item 4's wording: "…derived in-proof **and pinned by the G equality obligations**".
- **Affected:** §1, §3, §5.4; 05a §3.5 (whose "derived, not asserted" wording has the same one-directional gap — flag to its pending review).

### F3 (Major) — The §6 stop-rule fallback cannot work as written, and violates the authorship split it lives under

- **Claim:** §6: "if T1 resists after the timebox, deliver T4 restricted to the transposed relaxation." Three independent defects: **(a)** the transposed (column-side) relaxation yields Σn² ≤ 128,779,812 → pair bound 64,376,266 > 60,862,048, so it **cannot prove T4's stated constant** — re-derived above, and §3's "the corollary (T4) may be proved through whichever side reaches the recorded constant" is factually misleading, since only the row side reaches it; **(b)** the transposed route is T2 on the transpose, which factors through T1 identically — if T1 resists, both routes are blocked; **(c)** any genuinely weaker fallback certificate is a *different statement* (different constant), and under the header's authorship split the Sonnet orchestrator/Leanstral may not author statements — the fallback path as designed requires mid-spike statement authorship by the wrong actor.
- **Evidence:** §6 stop rule; §3 post-T2 paragraph; column-relaxation value 128,779,812 (re-derived; matches `concentration_upper_bound_sumsq`'s `ub_cols` on these margins).
- **Failure scenario:** T1 resists on day 1; the orchestrator attempts the documented fallback, discovers T4 unprovable via transpose (or worse, burns the remaining timebox trying), and has no authorized weaker statement to fall back to. The Partial the stop rule promises cannot be delivered.
- **Impact:** operational — a timeboxed spike with a dead fallback path; no evidence corruption.
- **Disposition:** fix now — pre-author the fallback in this document so it is covered by the same review. Proposed replacement for the §6 stop rule:

  > Stop rule: if T1 resists after the timebox, deliver the pre-authored fallback **T4-coarse** instead (below), with an obstruction report on T1. T4-coarse needs no sorting and no exchange argument — for each row, every entry satisfies xⱼ ≤ min(rᵢ, max cⱼ), hence Σⱼ xⱼ² ≤ rᵢ · min(rᵢ, max cⱼ) — and yields Σn² ≤ 131,149,261 → pair bound 65,560,990 → ARI upper ≈ 0.94451 → normalised lower ≈ 0.2765: weaker but coherent and referent-relevant. The transposed relaxation is NOT a fallback: it cannot reach 60,862,048 and shares the T1 dependency.

  ```lean
  /-- T4-coarse — pre-authored fallback bound (no concentration lemma needed). -/
  theorem b9_pair_overlap_le_coarse
      (M : Fin 7 → Fin 7 → ℕ)
      (hrow : ∀ i, ∑ j, M i j = omCounts[i.val]!)
      (hcol : ∀ j, ∑ i, M i j = gmmCounts[j.val]!) :
      ∑ i, ∑ j, Nat.choose (M i j) 2 ≤ 65560990
  ```

  And correct the §3 sentence to: "Only the row-side relaxation (T2 applied directly, c = gmmCounts) reaches the recorded constant — the transpose yields 64,376,266 and is not a proof route for T4; it is retained only as the mathematical justification for the code's `min`."
- **Affected:** §3, §6; the Sonnet handoff prompt; the W/M obligations apply unchanged to T4-coarse's margins (same witness works: 59,684,973 ≤ 65,560,990).

---

## Minor findings

### F4 (Minor) — T3's `htp : 0 < tp` is unused

Over ℚ (total division), the conclusion follows from `hden` alone; `htp` adds an instantiation obligation with no strength. Harmless, but an unused hypothesis in a fixed statement invites "may I drop it?" drift questions later. Either delete it now or leave with a comment marking it intentionally redundant. Disposition: fix now (delete), at author's option.

### F5 (Minor) — Re-review is positioned post-proof; drift discovered late wastes work but corrupts nothing

The header ("any statement change stales this document") and §3 ("final signatures come back through statement re-review") are consistent on the *requirement* but place the check after proof search (also §5 item 5). A drifted encoding is caught before promotion but after the timebox is spent. Given the 1-day box this is proportionate. Disposition: accept risk, no change.

### F6 (Minor) — Hammer-proof rule diverges between the two cited authorities

Prereg §8 item 4 forbids "opaque hammer-only proof unless short and auditable"; 05a §3.4 permits any kernel-checked proof term. S2 §5 cites both and silently adopts the permissive stance by omission. Both are defensible (the kernel checks the term either way; the statement is fixed), but the pending 05a review should reconcile them, and S2 §5 should name which governs. Disposition: owner decision (via the 05a review).

### F7 (Minor) — Reviewer independence grade unstated

05a §3.8 scales required reviewer independence with claim risk (≥ I1 for R2; I2 + Stephen for R3). S2 names "Stephen, or a fresh Fable/Opus session" without classifying the B9 claim's grade. If the published P01-A bracket is R3-class under W5, a fresh session alone may not suffice and Stephen's sign-off on this review is required regardless. Disposition: owner decision — state the grade in the header; Stephen countersigns this review either way (cheap, and 05a is still a draft).

### F8 (Editorial) — §2 malformed subscript

"Fix column sums c₁,…,C." should read "c₁,…,c_C". Not fixed in place: the reviewed document's header makes *any* modification a staleness trigger, so even editorial fixes are left to the author. Same for the §3/§6 corrections above.

---

## Statement-by-statement disposition (completeness gate)

| Object | Verdict | Notes |
|---|---|---|
| `greedyFill` | **Sound** | Exact semantic mirror of `_maxsq_line` incl. the `rem ≤ 0` edge |
| T1 | **Sound, provable** | True as stated (pointwise caps against unsorted list; greedy on the sorted multiset dominates). Exchange induction viable; hypothesis set exactly right |
| T2 | **Sound, provable** | `hcol` alone suffices (entries bounded by their column sum); direct application reaches the winning bound |
| T3 | **Sound; htp unused** (F4) | Generic transfer only — concrete instantiation missing (F1) |
| T4 | **Sound, provable via T2 direct** | Constant verified; transpose route impossible (F3); `Nat.choose … 2` evaluation: prefer rewriting via `Nat.choose_two_right` before `decide` if the kernel is slow (§5.3 already anticipates documenting this) |
| W | **Verified** | Margins and pair count all reproduce; byte-identical to the JSON `achieving_table` |
| M | **Sound guard** | Correctly refutes 59,684,972; also (with W) excludes hypothesis-vacuity — a vacuous encoding would make M's inner ∀ true and M unprovable |
| *(missing)* T5/T6, G, T4-coarse | **Required additions** | F1, F2, F3 |

## §5 acceptance-contract disposition

| Item | Disposition |
|---|---|
| 1 `lake build` + pinned toolchain | Keep — mechanical |
| 2 no sorry/admit | Keep — mechanical; extend scope to G/T5/T6/T4-coarse |
| 3 axiom audit | Keep — note it *also* mechanically catches `native_decide` (introduces `Lean.ofReduceBool`/`Lean.trustCompiler`, failing the ⊆-check), so the prohibition is enforced, not just stated |
| 4 constants derived in-proof | **Amend** per F2 (add G; "derived" currently enforceable only in the deflation direction) |
| 5 signature diff by independent reviewer | Keep — record the S2 doc's git blob as `statement_source` hash per 05a §2 so the diff base is pinned |
| 6 scratch/promoted separation | Keep — consistent with prereg §9 layout |
| 7 vault `[RESULT]` with verbatim referent | **Amend** — referent line must match the F1-resolved scope |

## Consistency matrix (invariant → enforcement → status)

| Invariant | Enforcement | Status |
|---|---|---|
| Statements immutable by prover | §5.5 diff vs §3; 05a `statement_hash` | OK (pin blob hash of 5cdb3d2 version — post-F1/F3 edits will move it; re-pin then) |
| No proof holes | grep + `#print axioms` | OK, mechanical |
| Axiom set ⊆ {propext, Choice, Quot.sound} | `#print axioms` | OK; also enforces the native_decide ban |
| Constants derived in Lean | **none (≤ only)** | **Gap — F2 (add G)** |
| Non-vacuity | W (kernel) | OK |
| Encoding falsifiable | M (kernel) | OK |
| ARI/normalised referent certified | **no statement** | **Gap — F1 (add T5/T6 or rescope)** |
| Margins match JSON `label_counts` | authored once; verified by this review | OK now; add to §5.5 reviewer checklist for re-review |
| Fallback deliverable exists | **broken route** | **Gap — F3 (pre-author T4-coarse)** |

## Decision audit

| Decision | Disposition |
|---|---|
| Statement/prover authorship split (owner-approved, scout plan §3.1) | **Keep** — no contrary evidence; this review is downstream of it |
| Encoding freedom with post-hoc re-review | **Keep** (F5 accepted risk) |
| "min needs no lemma; whichever side reaches the constant" | **Amend** (F3: only the row side does) |
| Stop rule / fallback | **Amend** (F3: pre-authored T4-coarse) |
| Acceptance contract per prereg §8 + 05a draft | **Keep with amendments** (F2 item 4, F6 reconciliation, F7 grade) |
| `lean-tda-spikes/S2/` layout | **Keep** — consistent with prereg §9 |
| Statement set T1–T4+W+M | **Amend** — add G mandatory; T5/T6 or §1/§4 rescope; T4-coarse |
| Reviewer identity "Stephen or fresh Fable/Opus" | **Owner decision** (F7) |

## Practicality

Proportionate. The contract is almost entirely mechanical; the only real proof-search content is T1 (as the doc says); T5/T6/G add ~zero proof-search load (`norm_num`/`decide`/one mathlib div lemma); T4-coarse is elementary algebra. The 1-day timebox remains realistic *with* a working fallback; without one (status quo) the timebox has no graceful exit. Kernel-cost risk on the `decide` obligations is real but anticipated (§5.3); the `Nat.choose_two_right` rewrite is the standard mitigation.

## Revision plan

**Immediate (author, before dispatch):** apply F1 (T5/T6 *or* rescope §1/§4 + §5.7), F2 (G + §5.4 wording), F3 (§3 correction + §6 stop-rule rewrite + T4-coarse), F4 (drop or annotate `htp`), F8 (typo). Any edit stales the 5cdb3d2 hash — re-pin `statement_source` after.
**Owner decisions:** F6 (which hammer rule governs — route to the pending 05a review), F7 (claim grade + countersignature of this review).
**Later-work dependencies:** 05a §3.5 one-directionality note (to 05a's own adversarial review); W6 seed-fixture claim strength depends on the F1 resolution.

## Residual risks

- The Lean-side kernel cost of `decide` on Finset sums over the matrix literal is unmeasured; mitigation is documented but untested here.
- mathlib idiom drift (`mergeSort` argument form) is delegated to the orchestrator under encoding freedom; re-review (F5) is the backstop.
- 05a is a draft; if its review changes the acceptance contract, §5 must be re-instantiated.

## Change log

- Created this report. **No edits to the reviewed document or any other file** (the document's own staleness rule makes even editorial fixes author-only — see F8).
- Verification script (exact arithmetic, no TDL imports) retained in session scratchpad; all outputs quoted in the Verification Evidence table.
