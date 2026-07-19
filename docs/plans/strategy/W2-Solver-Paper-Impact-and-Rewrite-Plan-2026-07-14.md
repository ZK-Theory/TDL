# W₂-solver correction — paper impact and rewrite plan (2026-07-14)

**Author:** Manager 13. **Audience:** Stephen (User/Manager) + the next writing-agent dispatch.
**Status:** two items need a User ruling (§2); the rest is dispatch-ready scope (§4–§5).

Anchors already on file — do not re-litigate:
- Ruling: Computational-Log **2026-07-14 `[DECISION]`** — vintage **(a)** immaterial; solver **(i) adopt-exact**; SUSPECT files **per-use**; dedup hold (item 4) closed.
- Audit: `results/trajectory_tda_integration/stage1/w2_fallback_audit_2026-07-14.json` (WT-6, PR #94, merged `5e4ef76`).
- Manifest: `results/trajectory_tda_integration/stage1/SUPERSEDED.md` (axes: PCA-refit / **solver** / vintage).
- Memos: `w2-fallback-audit-memo-2026-07-14`, `headline-vintage-materiality-memo-corrected-2026-07-14`.

---

## 1. One-paragraph statement of the defect (for prose reuse)

`vectorisation.wasserstein_distance` wrapped its gudhi/POT import in `try/except` and
silently fell through to **greedy persistence-rank matching** — not optimal transport —
whenever POT was absent from the venv (**era ≤ 2026-05-29**; boundary established
empirically, not from the 2026-06-16 pyproject pin). For **H₀** the fallback is
harmless (all births = 0 ⇒ rank-matching *is* optimal 1-D transport; max observed
error 1.1%, no decision affected). For **H₁** it inflates distances ~18–30× and, because
it inflates observed-to-null and null-to-null **together**, it **compresses the ratio
toward 1** — i.e. it *dilutes real signal and manufactures non-rejections*. Landscape L²
is immune (separate pure-numpy path). Fixed in PR #94: the solver now raises when POT is
unavailable; greedy is reachable only via an explicit flag with a loud warning.

**The single most important consequence for the manuscripts: every greedy-era H₁ "no
separation / ratio ≈ 1 / non-rejection" result is uninformative — it is the direction the
bug pushes. Greedy-era H₁ non-rejections are not evidence of a null.**

---

## 2. OPEN — needs a User ruling before the dependent prose is drafted

### 2.1 The dedup amendment's justification (gates §S6 + §6.2 rewrite)

The 2×2 factorial (Computational-Log 2026-07-14 `[RESULT]`) shows the H₁ W₂ "flip" that
justifies external de-duplication is **the solver, not the dedup**: dedup moves the
statistic +0.4% on either solver row; greedy→exact moves it ÷30.7 on either dedup column.
The committed mechanism ("~139 phantom H₁ features at near-zero scale") is **false**: the
05-29 observed H₁ diagram has **zero** features with persistence < 1e-6; dedup removed 139
near-duplicate *landmarks* (5000→4861) but changed the H₁ *diagram* by **+2 features**
(3144→3146), exact W₂ = 0.545 — which cannot move p from 0.35 to the floor under a metric.

- **Outcome A is UNCHANGED and safe** — it rests on the two dedup arms (truncate 05-30,
  first13 05-30), both exact-era, both rejecting H₁ W₂. The 2026-05-31 `[DECISION]` stands.
- **What dissolves** is the *evidence offered for the dedup step*, and with it the §S6 /
  §6.2 narrative. Under exact W₂ the no-dedup and dedup arms are statistically
  indistinguishable (t_ratio 1.860 vs 1.866) — **the no-dedup arm rejects too**.

**Decision required — pick one:**

| | Option | Consequence |
|---|---|---|
| **(A) ✅ recommended** | **Keep external dedup; re-justify on data-property grounds.** Near-duplicate landmarks are a true property of the embedding (committed `dedup_provenance` `asymmetry_note`); the Markov-1 surrogates do not reproduce them, so the observed/null vertex-count asymmetry is real and worth correcting. Drop every H₁-W₂-flip claim. | §S6/§6.2 rewritten as a *provenance/representation* argument, not an inferential one. Outcome A unaffected. Honest and defensible. |
| (B) | **Retire the dedup step** and report the no-dedup arm (which rejects under exact W₂). | Simpler, but discards a real data-property correction and forces re-running the length-matched family on the no-dedup arm. No inferential gain. |
| (C) | **Present both arms** as a sensitivity pair (they agree under exact W₂). | Most transparent; costs a paragraph. Compatible with (A). |

**Recommendation: (A), optionally with (C) as a one-sentence sensitivity note.** The
methodological irony should be stated once in the disclosure, not buried: *the amendment
was designed to fix a symptom the solver bug created.* Reviewers reward that candour;
discovering it themselves is fatal.

### 2.2 P01-A Table 1 — every H₁ row is greedy-era and unverifiable

**This file is NOT in the WT-6 audit table and is not named in the ruling. It is the
largest remaining exposure.**

`papers/P01-A-JRSSA/drafts/sections/table1_effects_2026-05-22.{md,json}` (+ generator
`compute_table1_effects.py`, section `table1-effects-d_perm-rho-CI.md`) draws every row
from **greedy-era** sources: `L5000_postaudit_2026-05-02`, `L2000_legacy_2026-04-07`
(`04_nulls_wasserstein_w2_20260407.json`), `L5000_markov2_postaudit_2026-05-02`,
`stratified_markov1_L5000_2026-05-02`.

Evidence it is artifact-bearing, from the committed numbers alone:
- **Every H₁ `rho_hat` is ≈1** (0.999, 1.000, 0.992, 1.078, 1.047, 1.001, 0.964, 1.030,
  1.053, **0.929**, 1.003, 1.014, 0.992, **0.955**, 1.011, 1.033) — the greedy compression
  signature. H₀ rows in the same table separate normally (2.16–5.04).
- **H₁ means are 130–306** on diagrams whose exact-W₂ diagonal bound is ~20 → **impossible
  as exact W₂**, the same screen that convicted the frozen headline.
- **Two rows invert under the exact solver:** BHPS `markov` H₁ → committed
  `rho 0.955, d_perm −2.00, p = 0.978` (a *non-rejection*), where the corrected exact BHPS
  H₁ headline is `t_ratio 2.175, d_perm +19.26, p = 0.000999`. And
  `stratified_markov1` H₁ → `rho 0.929, d_perm −2.99, p = 1.0000`.
- **Sources predate every null cache** (earliest 2026-05-24) ⇒ **SUSPECT-UNVERIFIABLE**;
  by the 2026-07-14 ruling item 3, these H₁ numbers **may not be cited without a
  production re-run**. They are also pre-frozen (PCA-refit era) — doubly superseded.

**Decision required — pick one:**
- **(A) ✅ recommended — commission a Table 1 H₁ re-run** under the fail-loud exact solver
  at the frozen-loadings representation. B=100 per cell → ~200 exact EMD pairs/cell at
  ~5 s/pair ≈ 17 min/cell; ~10 H₁ cells ≈ 3 h with process parallelism. Cheap relative to
  publishing an inverted negative-control table.
- (B) Drop the H₁ column from Table 1 and report H₀ only, disclosing why.
- (C) Rebuild Table 1 from the **frozen exact-era** files instead of the 2026-05-02
  post-audit set (fixes both supersession axes at once) — **preferred if the re-run
  happens anyway**; the frozen battery is the citable representation.

**Recommendation: (A)+(C) as one task — rebuild Table 1 from the frozen/corrected
exact-era sources.** Note the design flaw this exposes: under greedy, a negative control
*cannot fail* (the bug forces ratio→1), so Table 1's H₁ negative controls were never
actually tested. That is a reviewer-visible hole and the reason (B) is weak.

---

## 3. Two audit coverage gaps (record them regardless of §2)

Neither is in `w2_fallback_audit_2026-07-14.json`, the ruling, or `SUPERSEDED.md`:

1. **`04_nulls_wasserstein_w2_20260407.json`** (2026-04-07, deep greedy era) — feeds P01-A
   Table 1 (§2.2) and P01-B §4.2 Table 2's legacy label/cohort/order-shuffle rows. No
   cache exists ⇒ **SUSPECT-UNVERIFIABLE**. Add to `SUPERSEDED.md` axis 2.
2. **`markov2_alpha_sweep_summary_2026-06-16.json`** — dated *after* the 2026-05-29/30
   boundary ⇒ **exact-era, presumed IMMUNE**, but never explicitly gated. It feeds P01-B
   §4.2 Table 2's Markov-2 rows. Cheap to confirm; do not cite as verified until gated.
3. (Already known, restated) **`bhps_nonoverlap_reanalysis_2026-06-09`** H₁ — greedy era by
   7 days, cache present, gate deferred, **re-derivable**. It feeds **merged §6.2's
   non-overlap claim** ("non-overlap 0/20; landscape L² still rejects"). Under greedy that
   0/20 W₂ non-rejection is exactly what the bug produces — **re-derive before the §6.2
   rewrite lands.**

---

## 4. Rewrite scope — per section

Legend: **READY** = corrected numbers exist, dispatch now · **GATED** = needs §2 ruling ·
**BLOCKED** = needs compute first.

| Section | State | What changes |
|---|---|---|
| **P01-B §4.2 Table 2** (drafted, unmerged, T2.16) | **READY** | USoc Markov-1 H₁: `T 1.332 → 3.479`, `d_perm 22.09 → 31.16`, obs-null `233.68 → 12.68`. BHPS Markov-1 H₁: `T 1.037 → 2.175`, `d_perm 2.06 → 19.26`, **`p 0.019 → <0.001` (floor)**. H₀ rows unchanged. Cite the corrected files, not the frozen ones, for H₁ W₂. |
| **P01-B §4.2 "BHPS dual-metric divergence at Markov-1 H₁" paragraph** | **READY — DELETE** | The paragraph exists only because greedy compressed BHPS H₁ W₂ to a marginal `p=0.019` against a decisive landscape L². Under exact W₂ both metrics reject at the floor — **the divergence does not exist.** Remove entirely; do not soften. |
| **P01-B §4.2.4 abstract/C2 reconciliation** | **READY** | Conclusion **holds and strengthens** (H₀ and H₁ both reject decisively at matched L). Update the effect sizes only. |
| **P01-B §4.2 legacy label/cohort/order-shuffle rows** | **BLOCKED** (§3.1) | Greedy-era, unverifiable. Already flagged as unmatched-L. Either re-run or drop with disclosure — do not present the H₁ p-values as findings. |
| **P01-B §4.2 Markov-2 rows** | **BLOCKED-lite** (§3.2) | Presumed exact-era; confirm by gate, then they stand. |
| **P01-A §6.2** `results-bhps-robustness.md` (**MERGED**), lines 46–57 | **GATED** on §2.1 | The "≈139 phantom H₁ features … ratio 1.006 → 1.87" paragraph is factually wrong. Rewrite per the §2.1 ruling. Also re-check the non-overlap claim against §3.3. |
| **P01-A §S6** `supplement-S6-length-matched-dedup.md` (**MERGED**), lines 60–88 | **GATED** on §2.1 | The whole "**The H₁ W₂ flip is mechanistic, not a tuning choice**" argument + the 202.84/201.58/1.006 → 6.63/3.55/1.867 numbers. Rewrite per §2.1; **keep** Outcome A (unchanged). |
| **P01-A `_project.md`** line ~150 | **GATED** on §2.1 | The "1.006→1.867" reference. |
| **P01-A Table 1** (`table1_effects_*`, `table1-effects-d_perm-rho-CI.md`, `compute_table1_effects.py`) | **GATED** on §2.2 | Every H₁ row. See §2.2. |
| **P01-A §6.1 / P01-B §4.2.3 stratified rung** | **NO CHANGE ✅** | T1.28 (2026-07-09) is **exact-era, IMMUNE**. Tables 6.1a/b and Table 3 stand. |
| **All landscape L², all H₀** | **NO CHANGE ✅** | Immune. |
| **Vintage note** | **READY — ADD** | One line, once per paper, per ruling (1). |

---

## 5. Dispatch packaging (next writing-agent dispatch)

**Tranche 1 — dispatch now (READY, no gate):** P01-B §4.2 Table 2 H₁ rows + delete the
divergence paragraph + §4.2.4 effect sizes + the vintage note. Lands on the existing
worktree `.apm/worktrees/paper-p01b-methods-results` (branch `paper/p01b-methods-results`),
which already holds the T2.12–2.16 batch awaiting review — fold this in as a follow-up
Task so the User reviews one coherent §4.2.

**Tranche 2 — after the §2.1 ruling:** P01-A §S6 + §6.2 + `_project.md` dedup rewrite.
**This is outcome-contingent prose** — per APM_RULES the ruling must be a filed
`[DECISION]` before dispatch. Needs a `paper/p01a-dedup-rewrite` branch (both files are
merged on `main`) → PR → CodeRabbit → merge.

**Tranche 3 — after compute:** Table 1 rebuild (§2.2), the `04_nulls` / `markov2` /
`nonoverlap` gates (§3). Compute task first (`run/w2-gap-closure`), prose after.

**Cross-cutting mandates for every tranche:**
1. Cite **corrected** H₁ W₂ files; the frozen 2026-05-28 files remain canonical for **H₀
   and landscape L² only**.
2. **Never present a greedy-era H₁ non-rejection as evidence of a null.**
3. H₀ and landscape L² conclusions are unchanged — do not re-open them.
4. Outcome A is unchanged — do not re-litigate it.
5. Per-section `/notation-check`; per-section User review; Worker does not merge.

---

## 6. Recommended order

1. Rule on **§2.1** (dedup justification) and **§2.2** (Table 1) — both one-liners.
2. Dispatch **Tranche 1** (unblocked, uses already-corrected numbers).
3. Dispatch the **gap-closure compute** (§3) in parallel — it is independent of prose.
4. Tranche 2 once §2.1 is a filed `[DECISION]`; Tranche 3 once compute lands.
