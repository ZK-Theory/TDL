# R2 Referent-Adequacy Review — S2 Max-ARI Statement Set (Key B(a))

**Date:** 2026-07-21
**Review class:** Key B(a) referent adequacy, 05a §3 item 9 — *does the authored statement set say what the P01-A B9 claim needs?* Pre-proof-search gate; this review is the Key B(a) evidence for the eventual `lean_proof` acceptance record.
**Verdict:** **`adequate_with_conditions`** — one condition (C1, a two-line addition to obligation G; pre-approved verbatim text below), three non-blocking recommendations. Every other checklist item is adequate. Per the dispatch's acceptance rule this routes to the **statement author** for the C1 revision, not to Leanstral; no proof effort has been spent.

---

## 0. Independence evidence (05a §3 item 9 / §16.2)

Self-attestation without identity is not evidence; the identity is:

- **Actor:** Claude Fable 5 (model id `claude-fable-5`), Claude Code session `341fdbd9-8f88-4042-9cda-4c6ac9e8c722`, 2026-07-21, Windows host, repo `C:\Users\steph\TDL`.
- **Fresh session:** this session was initiated by the R2 review dispatch and contains no context from the S2 authoring lineage (the 2026-07-07 authoring / 2026-07-20 revision sessions). It is **session-level independent of the statement author** (Claude Fable 5, different session) — the R2 bar per 05a §3 item 9 and §9 decision 3 (Stephen, 2026-07-21), and per the S2 header ("Stephen, or a fresh Fable/Opus session").
- **Independent of the prover:** the prover is Leanstral (Mistral, external API). This reviewer is a different actor and provider; moreover no Leanstral output exists yet (proof search has not started), so prover contamination is impossible in principle.
- **Disclosure:** the reviewer is the *same model family* as the statement author. That satisfies the session-level R2 bar this review is graded at; it would **not** satisfy the R3 bar (I2 + Stephen). The downstream P01-A prose promotion is separately graded R3 and requires Stephen regardless (S2 header; out of scope here).

## 1. Exact bindings (what was reviewed)

All three files clean in the working tree at review time; review bound to these bytes:

| File | Git blob (at HEAD `a98e97d1bc5114ff9f9d9f65874a74a777362246`, branch `pipe/lean-review-integration`) |
|---|---|
| `docs/plans/strategy/S2-statement-authorship-max-ari-bound-2026-07-07.md` (REVISED, countersigned; contains T5/T6, G, T4-coarse) | `e93092e420f540fc4427ff7e5b29aa6e90b8fe24` |
| `docs/plans/agentic-research-system/design/05a-lean-proof-evidence-class-addendum-2026-07-07.md` (ACCEPTED v0.2), §1–§5 | `4cf4f95fb07d817239bfe2ddf1620a1ffa585cfb` |
| `results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-24.json` (T1.23d artefact) | `cee026c63a8e7a4f3e3da2d92576859c987f529c` |

If C1 is applied, the S2 blob moves and `statement_source` must be re-pinned to the new blob (S2 review-integration note); this review then applies to the revised document under the delta rule of §6 below.

**Evidence-fidelity checks in passing:** the §1-cited docstring anchor exists (`trajectory_tda/analysis/panel/fixed_margin_max_ari.py:138`, `concentration_upper_bound_sumsq`); the cited 2026-07-20 adversarial review file exists at `reviews/adversarial-S2-max-ari-statement-review-2026-07-20.md`; the JSON `supersedes.carried_over_verbatim` list (`observed_ari`, `null_distribution`, `bootstrap_ci`) matches §4's "carried verbatim from T1.23c" claim.

**Independent re-derivation (fresh path, not copy-compare):** all constants were re-derived from scratch — greedy fill re-implemented independently of `fixed_margin_max_ari.py`, margins typed in fresh from the JSON — **33/33 checks pass**: margins = `label_counts` (both orders, key order 0–6); both margin sums = 27,280 = `label_counts.n`; greedy value 121,751,376; pair bound 60,862,048 (even numerator, division exact); transpose relaxation 128,779,812 → 64,376,266 (confirming it is not a route to T4's constant); rp 72,965,958 / cp 64,376,266 / tp 372,085,560; hden exactly 1737854436932491/31007130 > 0; float image of the ARI upper rational exactly 0.8606691921483836; witness W margins and pair count 59,684,973 with float image exactly 0.8396675957148108; normalised bracket floats exactly [0.30346238425045263, 0.31105252415739076]; coarse Σ r·min(r, 7358) = 131,149,261 (odd numerator, floor strict) → 65,560,990 → ARI 0.9445086… (≈ 0.94451), normalised ≈ 0.2765; witness valid under the coarse bound; M's refuted constant 59,684,972 sits strictly below the witness value. This independently re-confirms the 2026-07-20 review's bit-for-bit constant match rather than relying on it.

## 2. Per-item dispositions

### Item 1 — Scope closure (the F1 fix): **ADEQUATE**

The §1 claim-to-certify decomposes into exactly four certifiable elements, each with an authored statement, and nothing else:

| §1 claim element | Authored statement |
|---|---|
| Pair-overlap upper bound 60,862,048 on every table with the B9 margins | T4 (constant kernel-derived via G) |
| Max-achievable ARI ≤ the exact rational (float image 0.8606691921483836) | T5 (T3 instantiated at the pinned rp/cp/tp; per-table bound; the feasible set is finite and non-empty by W, so the per-table bound is a bound on the maximum) |
| Normalised observed ARI `observed/ari_upper` is a true lower bound on the normalised ARI | T6 (generic ℚ transfer; instantiated at runtime because `obs` is deliberately uncertified — see item 3) |
| Achievable lower end, pair overlap 59,684,973 | W (kernel-certifies margins + pair count of the concrete table, byte-identical to the JSON `achieving_table`) |

No residual ARI/normalised assertion in §1 lacks an authored statement. Conversely, nothing certifies more than §1 claims: T1/T2/T3 are generic supporting lemmas (no artefact content); G pins constants; M is a falsifiability obligation; T4-coarse is explicitly fallback-scoped. A subtle completeness point checked and satisfied: the *upper* end of the published normalised bracket (obs/0.8397) needs the reverse-direction transfer `obs/maxAri ≤ obs/lbAri` — T6's generic form covers this by re-instantiation (ub := maxAri, maxAri := lbAri, with 0 < lbAri from W and lbAri ≤ maxAri from W + T3), so no second transfer lemma is missing.

### Item 2 — Hypothesis tightness: **ADEQUATE**

- `hrow`/`hcol` are margin **equalities** on the literal lists, and the lists equal the JSON `label_counts` exactly (fresh comparison, key order 0–6: omCounts = om_cluster_counts, gmmCounts = gmm_regime_counts). **Confirmed.**
- The hypotheses are not stronger than what the artefact family satisfies: non-negativity comes from the ℕ codomain (no added positivity/ordering/support hypotheses); fixing *both* margins is exactly the fixed-margin referent family the artefact brackets — dropping `hcol` would certify a strictly larger family (T4's route needs only `hcol` via T2 plus the total from `hrow`), but the authored form matches the referent precisely, which is the correct choice for "authored == needed".
- T3/T5's `hden > 0` is discharged on the pinned rationals; the quoted value 1737854436932491/31007130 re-derives exactly and is positive.
- T6's hypotheses (`0 ≤ obs`, `0 < maxAri`) are satisfiable on the referent data: obs = 0.2611807… > 0; maxAri ≥ ARI(W) ≈ 0.8397 > 0. Neither silently narrows the certificate.
- Indexing (`[i.val]!` on length-7 lists under `Fin 7`) cannot hit the default branch.

### Item 3 — Referent-note honesty (§4 table + §1): **ADEQUATE** (one non-blocking recommendation)

The certified-vs-NOT-certified split is correct: floats are declared runtime-checked, not kernel-certified (§1 bullet 1, §4 rows 2, T5 comment); observed ARI, permutation null, and bootstrap CI are excluded as separate T1.23c provenance — confirmed against the JSON's own `supersedes.carried_over_verbatim`; margins-vs-underlying-clusterings is correctly assigned to T1.23b/c provenance with the §5 item 5 re-review check; the NW+2-opt search quality is certified only via W (§4 last row). The 05a §5.1 lane-enumeration requirement does not bite: B9 is a clustering-agreement obligation, not topology-lane.

**Recommendation R1 (non-blocking):** `normalised_ci_percentile_95` in the JSON is only *implicitly* excluded (via the bootstrap-CI and float exclusions). Add it explicitly to §4's NOT-certified column so the eventual `referent_note` cannot be read as covering it.

### Item 4 — Anchoring adequacy (G): **FINDING F-R2-1 (Minor) → Condition C1**

Pinned by kernel **equality** on a derived quantity, as F2 requires: greedy value 121,751,376 (G, from the margin lists) ✓; pair bound 60,862,048 (G, arithmetic from the pinned greedy) ✓; rp/cp/tp (G, from the lists) ✓; witness value 59,684,973 (W) ✓; coarse constants 131,149,261 / 65,560,990 (coarse anchoring block) ✓.

**Residual: n = 27,280.** §5 item 4 names 27,280 in the list of constants that must be "derived in-proof AND pinned by the G equality obligations", but in G (and the coarse block) 27,280 appears only as a **literal inside arithmetic identities** — no equality pins the derived quantity `omCounts.sum` / `gmmCounts.sum` to it. An arithmetic identity between literals is true regardless of the artefact and cannot detect a wrong n.

- *Failure scenario (inflation direction, the exact F2 class):* had the document recorded n' < 27,280 (e.g. 27,270), G would read `(121751376 − 27270)/2 = 60862053` — true arithmetic, passes — and T4 at the **inflated** constant 60,862,053 would prove successfully (true bound 60,862,048 ≤ 60,862,053). No authored kernel obligation catches the mismatch.
- *Mitigations that exist as specified:* the pair bound and n are both artefact-recorded fields, so a faithful acceptor executing 05a §3 item 5's comparison-against-the-artefact catches both mismatches; and the §5 item 5 re-review checklist compares the margin lists to the JSON. The gap is therefore procedural-depth, not a live error (the actual constants are verified correct above). But those catches fire at **acceptance time, after proof effort is spent**, and rest on acceptor procedure rather than the kernel; the fallback path (§6 stop rule) re-instantiates constants mid-spike under time pressure, which is precisely when a wrong literal slips. F2's own standard — every artefact-bound constant pinned by kernel equality on the derived quantity — is not met for this one constant, and §5 item 4 as written promises it is.

**Condition C1 (pre-approved verbatim text; statement author applies):** append to obligation G:

```lean
example : omCounts.sum = 27280 := by decide
example : gmmCounts.sum = 27280 := by decide
```

(These also serve the coarse anchoring block, whose arithmetic uses the same literal.) Both equalities are true — verified by fresh computation. This is a pure addition: no authored theorem signature, hypothesis, or constant changes.

**Recommendation R2 (non-blocking hardening):** also pin the coarse block's capacity literal: `example : gmmCounts.foldr max 0 = 7358 := by decide`. Unlike n, a wrong value here is fail-safe (an understated max makes T4-coarse unprovable; an overstated max only weakens the bound while the equality example keeps the recorded constant faithful), so this is hygiene, not a condition.

### Item 5 — Fallback relevance (T4-coarse): **ADEQUATE**

The coarse bound's mathematics is valid (each entry ≤ min(rᵢ, max cⱼ), so Σⱼxⱼ² ≤ rᵢ·min(rᵢ, max cⱼ)); it needs no sorting and no exchange argument, so it genuinely does not share T1's failure mode. All constants re-derive: 131,149,261 → floor (odd numerator, floor strict — correctly flagged in the doc) → 65,560,990 → ARI 0.9445086… (doc's ≈ 0.94451 ✓) → normalised lower ≈ 0.2765 (✓). The **same witness W remains valid** (59,684,973 ≤ 65,560,990), and M is unaffected (it refutes 59,684,972, below the witness, independent of which upper constant is delivered). The certificate stays referent-relevant for B9: it still certifies a non-trivial max-ARI ceiling and a non-trivial normalised floor, which is the substance of the B9 normalisation defence against the superseded trivial-1.0 construction.

**Honesty note (already handled by the doc, made explicit here):** under the fallback, the *published* bracket lower end 0.30346 is **not** kernel-certified — the certified normalised floor becomes ≈ 0.2765 and the published figure remains on runtime assurance. §3 (re-instantiation), §5 item 7 (referent "at whichever scope was actually proved"), and §6 (Partial) already require the [RESULT] to state the coarse scope; the [RESULT] wording must not present 0.30346 as certified in that case.

### Item 6 — Grade (R2 vs R3): **ADEQUATE**

R2 is correct for the certification. It adds assurance evidence to an already-accepted, already-published artefact bracket and changes no result value and no paper claim — a correction/verification affecting evidence validity (W5 §9), which is R2's definition. The claim-strength step (promoting the normalised bracket into P01-A reviewer-facing prose) is where interpretation enters, and that is separately graded R3 with Stephen mandatory — the split is clean, and the grading is an owner decision on file (Stephen, 2026-07-21) with no contrary evidence found. The independence bar applied to this review (session-level) matches the R2 grade; nothing here launders the R3 step.

## 3. Consistency matrix (obligation → enforcement → check)

| Invariant / obligation | Enforcement point | Check status |
|---|---|---|
| Margins = artefact `label_counts` | Literal defs + §5 item 5 re-review checklist | Verified fresh here (both lists, both sums) |
| Greedy value / pair bound / rp / cp / tp not inflatable | G equalities + 05a §3.5 acceptor comparison | Adequate; re-derived here |
| n = 27,280 not inflatable | **Gap as authored** → C1 | **F-R2-1; C1 closes at kernel level** |
| Non-vacuity | W (real referent data, = JSON `achieving_table`) | Verified byte-identical, margins + pair count re-derived |
| Falsifiability | M (refutes 59,684,972 via W) | Coherent; witness strictly exceeds refuted bound |
| Statement/prover split | S2 header + 05a §4 + §3 item 8 drift check | In place; not weakened by any §3 statement |
| Float boundary | §1/§4/T5 comment declarations | Honest (R1 recommended for the normalised CI field) |
| Fallback scope honesty | §3 re-instantiation + §5 item 7 + §6 Partial | Adequate (honesty note above) |
| Hammer-proof rule | S2 F6 resolution: prereg §8.4 governs (stricter), 05a §8.2 precedence | Consistent across both documents |

## 4. Decision audit

Owner decisions encountered: S2 F6 (hammer rule — resolved, stricter governs), F7 / grade + countersignature (resolved 2026-07-21), 05a §9 items 1–5 (all resolved 2026-07-21). **Keep all** — no contrary evidence; none is challenged by this review. C1 is an *addition* to the mandatory obligation set G, not a reversal of any decision; since Stephen's countersignature reads "these are the statements I want certified", the C1 delta should be acknowledged by Stephen (a one-line ack suffices) when the revised blob is re-pinned.

## 5. Residual risks (accepted, out of scope for adequacy)

- Proof feasibility of T1, kernel `decide` cost on 7×7 sums, mathlib idiom churn — prover/harness concerns (S2 §5–§6 already carry mitigations and the sanctioned re-review valve).
- The observed ARI, permutation null, bootstrap CI, and margins-vs-clusterings correspondence remain on T1.23b/c/d runtime assurance by design; nothing in the statement set claims otherwise.
- The acceptor-side harness (05a §10) does not yet exist; until it does, 05a §3 item 5's artefact comparison is procedure, not code. C1 reduces the exposure of exactly this window.

## 6. Verdict and gate statement

**`adequate_with_conditions`.** Condition **C1** (two `List.sum` equality examples appended to G, verbatim text in item 4 above) routes to the statement author. Subject to C1 applied **verbatim and alone** — no other change to any signature, definition, constant, or hypothesis — and `statement_source` re-pinned to the revised S2 blob, this review's adequacy findings carry over without a further full R2 cycle (the two added lines are themselves reviewed and pre-approved here; any *other* change stales this review per the S2 header rule).

With C1 so applied: **the authored statement set (T1–T6, G+C1, W, M, T4-coarse) is the correct referent for the P01-A B9 claim as scoped in S2 §1, and proof search may proceed.** This document is the Key B(a) referent-adequacy evidence for the eventual `lean_proof` acceptance record, to be re-confirmed at evidence review per 05a §3 item 9.

**Files edited by this review:** none of the reviewed documents (this report only). Spot-check script retained in session scratchpad; its 33 checks are enumerated in §1.
