# P01-A / P01-B Claim-Trace Audit — 2026-07-17 (read-only)

**Audited commit:** `main` @ `e8890fb71331ffa3b9bdba57a55f56ffb30ed65b`
(post-PR #116 CodeRabbit remediation; post-PR #117 restore of the #105 content —
`w2_gap_closure_table1_h1_2026-07-16.json` and its contracts are ON `main` at this
commit; the PR #106 dedup-rewrite prose is NOT — it was reverted by #112 and is
parked for the ARS lane, so §6.2/§S6 are audited in their pre-ruling form).
**Scope:** every file under `papers/P01-A-JRSSA/drafts/sections/` and
`papers/P01-B-JRSSB/drafts/sections/`. No fixes applied; no prose authored. This
table is the rewrite input for the ARS prose lane.
**Authority map:** `results/trajectory_tda_integration/stage1/SUPERSEDED.md`
(both axes: PCA-refit and solver-era, plus its "Not covered" section, as updated by
PR #117); canonical H1 headlines
`headline_vintage_materiality_corrected_2026-07-14.json` (USoc) and
`results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json`
(BHPS); Table-1 H1 = the eight rebuilt rows in
`w2_gap_closure_table1_h1_2026-07-16.json`; notation authority
`papers/shared/notation.md`; governing rulings: 2026-07-14 `[DECISION]` (adopt-exact;
dedup re-justified, flip evidence retired), 2026-07-16 `[NEGATIVE]`/`[DECISION]`
(label/cohort INVALID-BY-CONSTRUCTION; double-null calibration replacement, T1.41),
2026-07-16 `[DECISION]` (non-overlap H1 claim falsified; §6.2 HOLD).

**Verdicts.**
- **VERIFIED** — value/procedure matched against the canonical artifact (or, for
  frozen-record numbers, bit-checked against the canonical JSON during this audit).
- **VERIFIED\*** — the named canonical artifact exists on `main` and the claim is
  consistent with the vault record, but the individual value was not re-matched
  field-by-field in this audit.
- **UNSUPPORTED** — no artifact backs the claim (includes citations of superseded,
  invalidated, or absent files).
- **MISDESCRIBED** — an artifact exists but the prose describes it wrongly.
- **WRONG-REGISTER** — content belonging to a different document class inside a
  manuscript section.
- **NOT-AUDITED** — explicitly out of this pass (v1-legacy descriptives, code-level
  construction details, literature attributions). Listed so silence ≠ verification.

---

## Part 1 — P01-B (JRSS-B) `drafts/sections/`

### methods-3-1-vr-filtration.md

| # | Claim (file:line) | Asserted source | Canonical artifact / implementation | Verdict |
|---|---|---|---|---|
| B1 | Embedding setup: frozen PCA loadings, d=20, 9 states, T ranges (:5) | pipeline | frozen embeddings; CONVENTIONS locks | VERIFIED |
| B2 | L=5,000 landmarks, seed 42, maxmin (:9) | — | CONVENTIONS L=5,000 lock (2026-05-05) | VERIFIED |
| B3 | Witness-complex primary + maxmin-VR cross-check construction; α_max truncation formula (:11–24) | code | construction described; code not re-read this pass | NOT-AUDITED (code-level) |
| B4 | Intrinsic-dim values: USoc TwoNN 3.59/MLE 5.80; BHPS 3.77/6.30; OVER-DIMENSIONAL (:24) | — | `results/*/stage1/intrinsic_dim_2026-05-24.json` (both present; values match) | VERIFIED |
| B5 | W₂ definition; `gudhi.wasserstein…(order=2, internal_p=2)`; ℓ² ground metric; Skraba–Turner stability (:26–36) | code | matches notation.md + post-#94 fail-loud path | VERIFIED |
| B6 | H₂ characterization: L∈{200,300}, dispersion artefact, residual collapses under max-pdist; L=1,000 attempted, confounded + budget-infeasible (:40–44) | H₂ battery | `results/trajectory_tda_integration/h2_check/` intermediates; L=1,000 disclosure added by PR #116 | VERIFIED\* |

### methods-3-2-ladder-markov.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| B7 | Ladder levels 3/4/4b/5 specification; stratified construction, n≥30 floor, smallest cells 223/335 (:5–45) | — | matches T1.28 record + §S0 algorithms | VERIFIED |
| B8 | BH separately per metric within each family (:43) | pre-reg amendment 2026-06-27 | `stratified_w2_bh_per_family_2026-07-09.json` | VERIFIED |
| B9 | **α-sweep sentence** (:53): "rejection direction stable across α ∈ {0,0.5,1,5}… USoc rejects at every α for both H₀/H₁ (p<0.001); BHPS rejects H₀ every α but fails to reject H₁ at every α (p=0.98…0.86); no smoothing strength changes which combinations reject" | α-sweep | `results/trajectory_tda_integration/post_audit/markov2_alpha_sweep_summary_2026-06-16.json` — accurately transcribed, BUT the source's W₂ numbers are solver-uncertifiable (no solver stamp; BHPS H₁ W₂ means ≈277–290 vs a ~20 exact diagonal bound — the greedy signature; classified UNVERIFIABLE by T1.38 Phase 1), and the exact-W₂ rebuild **rejects** BHPS Markov-2 H₁ (p 0.0099, d_perm +27.17, `w2_gap_closure_table1_h1_2026-07-16.json`). The direction-stability claim is contradicted for BHPS H₁. Certified recompute pre-registered 2026-07-17. | **MISDESCRIBED** (major) |
| B10 | Internal consistency: §4.2 holds Markov-2 cells as "unaudited; non-inferential" while §3.2 quotes the same source's p-values as empirical motivation | — | same-paper contradiction | MISDESCRIBED (consistency) |
| B11 | Label/cohort retained "only as a historical audit… not formal nulls" (:59–61) | 2026-07-16 [NEGATIVE] | matches | VERIFIED |

### methods-3-3-w2-test.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| B12 | TP scalar statistic; p=(r+1)/(B+1) (:5) | — | battery convention | VERIFIED |
| B13 | Mean-vs-mean T ratio; d_perm definition (:7–33) | `_battery_core` | matches canonical result files | VERIFIED |
| B14 | BCa disclosure: retained run resampled arrays independently; not clustered intervals (:20) | implementation | PR #116 remediation of the bootstrap-unit misdescription; matches implementation | VERIFIED |
| B15 | Permutation p per-draw ratio construction, p=(r+1)/(B+1) (:22–26) | — | matches `pvalue_null_draws: 1000` in canonical files | VERIFIED |
| B16 | "…type-I-error behavior **is assessed** through the double-null calibration analysis" (:26) | T1.41 | **T1.41 has not run** (approved as the final APM compute Task, pre-reg to be filed at dispatch). At the audited commit no calibration artifact exists; the only double-null artifact is the BHPS Markov-1 diagnostic (which found *mis*-calibration). Present-tense assertion of a pending analysis. | **UNSUPPORTED** (pending T1.41) |
| B17 | Landscape L² construction, k_max=5, 200 grid points, 1-Lipschitz (:35–37) | Bubenik 2015; run_params | matches frozen run_params | VERIFIED |
| B18 | Exchangeability + scalar/diagram discrepancy interpretation (:39–45) | — | interpretive methods prose | NOT-AUDITED (interpretive) |

### methods-3-4-knee-spanning.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| B19 | Knee algorithm; ε\*=0.54 = median of 28 eligible knees; Q25 0.46/Q75 0.63; 4 degenerate years; grid 0.05–2.00 (:9–29) | `detect_eps_star_knee` | CONVENTIONS ε\* lock (commit `4c73a1a`); values match | VERIFIED |
| B20 | Robustness set {0.54, 0.65, 0.70, 0.80}; 0.70 = unjustified v1 constant (:33, :48) | — | CONVENTIONS lock | VERIFIED |
| B21 | Three statistics incl. matched W₂ "constant across the four ε\* by construction" (:44) | — | PR #116 fix; consistent with §4.3 table | VERIFIED |
| B22 | Identification-check design (SMD diagnostic + two adjustment designs) (:52) | — | `balance_2026-05-14.json`, `matched_subset_2026-05-14.json` | VERIFIED\* |

### results-4-2-tables.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| B23 | USoc Markov-1 H₀ row: T 14.91 [14.54, 15.25], d_perm 51.07, both p<0.001 (:15) | corrected headline | `headline_vintage_materiality_corrected_2026-07-14.json` (orphan rows; vintage note carried at :33) | VERIFIED |
| B24 | USoc Markov-1 H₁ row: T 3.479 [3.454, 3.503], d_perm 31.16, both p<0.001 (:16) | corrected headline | same file, exact H₁ | VERIFIED |
| B25 | BHPS Markov-1 H₀ row: T 9.251 [9.001, 9.504], d_perm 26.53, both p<0.001 (:20) | frozen headline | `bhps_headline_frozen_2026-05-28.json` H₀ — bit-checked this audit (t_ratio 9.2505, BCa [9.0007, 9.5037], d_perm 26.525, W₂ p 0.000999, landscape p 0.000999) | VERIFIED |
| B26 | BHPS Markov-1 H₁ row: T 2.175, d_perm 19.26, both p<0.001 (:21) | corrected file | `bhps_headline_frozen_corrected_2026-07-14.json` (t 2.1754, d_perm 19.256, p 0.000999); landscape from frozen (0.000999) | VERIFIED |
| B27 | Footnote §: BHPS H₁ BCa "not re-derived… **pending** rather than absent" (:29) | — | **Stale at the audited commit:** `w2_gap_closure_phase1_2026-07-16.json` (restored via PR #117) carries the BHPS Markov-1 H₁ t-ratio BCa **[2.1646, 2.1832]** (2,000 resamples, seed 42, exact arrays). The interval exists on `main`. | **MISDESCRIBED** (stale, minor) |
| B28 | Markov-2 rows dashed: "unaudited; non-inferential… must not be used until the audit is complete" (:17–18, :22–23, :31, :37) | SUPERSEDED.md | accurate hold; certified recompute pre-registered 2026-07-17 | VERIFIED |
| B29 | Footnote ‡: "The Markov-2 α-sweep computes W₂ only; no landscape L² companion was computed" (:27) | α-sweep JSON | confirmed against the artifact (no landscape keys). **But** the 2026-07-17 pre-registration states certified Markov-2 landscape L² values are "already in hand" (USoc H₀ 0.258; USoc H₁ 0.003; BHPS H₀ <0.001; BHPS H₁ <0.001) — whose source artifact could not be located on `main` in this audit. One of the two statements is wrong, or an uncommitted artifact exists. Flagged as an open conflict (snapshot §3, hole H6). | VERIFIED (footnote) + open conflict |
| B30 | Legacy label/cohort/order-shuffle rows removed; rationale (:25) | 2026-07-16 [NEGATIVE] | matches | VERIFIED |
| B31 | Sequence-vintage note: d_perm moves ≤0.11 (H₁)/0.23 (H₀), no conclusion flips (:33) | WT-1c | corrected memo/JSON; ruling (a) | VERIFIED |
| B32 | Metric-agreement narrative incl. earlier BHPS H₁ divergence as the solver diagnostic (:35) | record | matches WT-6 record | VERIFIED |
| B33 | Table 3 stratified rows (23 subgroups) + incomplete markers (:44–78) | T1.28 recompute | `stratified_w2_recompute_2026-07-09.json` + `…bh_per_family…` (exact-era, audit-IMMUNE by git ancestry) | VERIFIED\* |

### results-spanning-identification.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| B34 | Table 4: three statistics × four ε\* (windowed AUC 1.127–1.129 p=0.001 throughout; single-ε 1.60 p=0.025 at 0.54 only; matched W₂ 2.536 p=0.001) (:13–18) | spanning re-analysis | `results/trajectory_tda_spanning/knee_robustness/spanning_betti_inference_2026-06-20.json`, `spanning_AUC_W2_2026-06-09.json`, per-ε files + pre-reg 2026-06-09 (the well-documented spanning outcome lock, commit `acb7f8a3`) | VERIFIED\* |
| B35 | Matched W₂ described as ε-invariant corroboration, not robustness evidence (:20, :22) | — | PR #116 fix confirmed in current text | VERIFIED |
| B36 | Matched W₂ solver status | — | H₀-degree statistic (births at 0 ⇒ greedy≡exact), but dated 2026-06-09 inside the fragile POT window and never explicitly gated — same date as the non-overlap file the convention gate proved greedy. Recorded as presumed-immune-ungated (snapshot hole H7). | VERIFIED\* (flag) |
| B37 | Balance table: n 5,895/21,385; SMDs −0.617/0.002/0.300/0.193; matched n=5,627; age-stratum ns (:26–39) | balance diagnostic | `results/panel_methodology/spanning_identification/balance_2026-05-14.json`, `matched_subset_2026-05-14.json` | VERIFIED\* |
| B38 | "86.1% of Inactive-Low window observations are aged 60+" (:37) | age-stratified analysis | not individually traced this pass | NOT-AUDITED |
| B39 | Matched/age-stratified topological comparison "pending… awaited before the identification finding can be considered fully corroborated" (:41, :45) | — | honest limitation, in the paper's voice; artifact genuinely absent | VERIFIED (as limitation) |

### results-reproducibility-statement.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| B40 | "the persistent-homology and optimal-transport dependencies (`gudhi`, `ripser`, `scikit-learn`) — pinned in `uv.lock`" (:5) | uv.lock | **POT (`ot`) is the optimal-transport dependency** (promoted to core at `ec291c0` after the greedy-fallback incident) and is not named; `scikit-learn` is neither a PH nor an OT dependency. The load-bearing pin for the paper's central statistic is omitted from the sentence that exists to assert it. | **MISDESCRIBED** (minor but pointed) |
| B41 | Master-seed propagation; `canary_rng.py` runs pipeline twice, bit-identical (:7) | script | `trajectory_tda/scripts/canary_rng.py` exists on `main` | VERIFIED\* |
| B42 | Two-machine confirmation "is in progress; not claimed as completed" (:9) | — | process-status narration in manuscript text (borderline for a repro statement) | WRONG-REGISTER (minor) |
| B43 | Legacy replay note: stored 12.6766 vs replay 11.2172; order-1 control ≈498.64 (:13) | notation.md audit | matches notation.md W₂ audit record and `table1_effects` L2000 order-shuffle H₀ mean 12.677 | VERIFIED |

**P01-B counts (43 rows, B1–B43; each row counted once by its primary verdict):**
VERIFIED 27 (B1–B2, B4–B5, B7–B8, B11–B15, B17, B19–B21, B23–B26, B28–B32, B35,
B39, B43 — B29's footnote verdict counts here, its open conflict is tracked as
snapshot hole H6; B39 is a verified limitation) ·
VERIFIED\* 7 (B6, B22, B33, B34, B36, B37, B41) ·
MISDESCRIBED 4 (B9 major, B10, B27, B40) ·
UNSUPPORTED 1 (B16) · WRONG-REGISTER 1 (B42) · NOT-AUDITED 3 (B3, B18, B38).
The seven P01-B files carry no HTML scaffolding (de-scaffolded by T2.23 / PR #109).

---

## Part 2 — P01-A (JRSS-A) `drafts/sections/`

### results-negative-control-wording.md — **entire file invalid**

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A1 | Replacement §4.3 paragraph: eight label/cohort-shuffle p-values (USoc 0.53/0.62/0.58/0.57; BHPS 0.51/0.56/0.55/0.63) "satisfy the negative-control criterion… confirming that state identity and cohort assignment do not drive diagram geometry" (:44–59) | `04_nulls_wasserstein_w2_L5000_20260502.json` (both surveys) | **INVALID-BY-CONSTRUCTION** (2026-07-16 `[NEGATIVE]`): the operations permute rows of the embedded cloud; VR persistence is set-valued; the p-values measure landmark-subsampling variance only. "None of them was ever evidence." Rows permanently removed from Table 1 (2026-07-16 `[DECISION]`); replacement = T1.41 double-null calibration panel + one-sentence inapplicability disclosure. No re-run can rescue the design. Sources additionally greedy-era/pre-frozen. | **UNSUPPORTED** (worst class) |
| A2 | Landmark-sensitivity note: L=2000 BHPS p≈0.036/0.034 "resolved at L=5,000… consistent with established low-landmark sensitivity" (:63–71) | Robinson & Turner 2017 | The L=2000-vs-L=5000 framing question is **dissolved** — both readings cited landmark noise from a vacuous null (2026-07-16 [NEGATIVE]). Attributing the discrepancy to landmark sensitivity misattributes noise as a resolved effect. | **UNSUPPORTED / MISDESCRIBED** |
| A3 | HTML header incl. "The Manager should review whether to invert this framing…" (:1–32) | — | — | WRONG-REGISTER |

### table1-effects-d_perm-rho-CI.md — **all cells unciteable**

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A4 | §4.3 Table 1 (12 USoc rows) + caption; Supplement §S1 (10 BHPS rows): every ρ̂/d_perm/p cell (:113–181) | `table1_effects_2026-05-22.json` ← `L5000_postaudit_2026-05-02`, `L2000_legacy_2026-04-07`, `L5000_markov2_postaudit_2026-05-02`, `stratified_markov1_L5000_2026-05-02` | SUPERSEDED.md: every source is greedy-era AND pre-frozen (both supersession axes); every H₁ ρ̂ ≈ 1 is the greedy compression signature; H₁ means 130–306 vs ~20 exact bound; two cells invert under exact W₂ (BHPS markov H₁ p 0.978 → 0.000999; stratified H₁ p 1.0000 → 0.0198 rejecting). The do-not-cite lift applies **only** to the eight fresh rows in `w2_gap_closure_table1_h1_2026-07-16.json`, which this file does not use. Label/cohort rows additionally invalid-by-construction and removed by the 2026-07-16 [DECISION]. H₀ rows are pre-frozen (PCA-refit axis) — also superseded. | **UNSUPPORTED** (entire table set) |
| A5 | Markov-2 caption sentence: "H₀ d_perm 1.53, ρ̂ 1.48 at p=0.080, against an H₁ effect size of 1.96 at p=0.030" (:148–151) | same | same sources; additionally contradicted by the exact rebuild's USoc markov2 H₁ (p 0.0099, d_perm +42.69) | UNSUPPORTED |
| A6 | "p-value resolution is limited to multiples of 1/N_pairs = 0.002 and ties out at 0.000" (:82–84, table p=0.000 cells) | legacy JSONs | Contradicts the 2026-05-27 `monte-carlo-permutation-p-value` contract (denominator = null draws, floor 1/(B+1); p=0.000 impossible under the locked Edgington form) | **MISDESCRIBED** |
| A7 | HTML header; "will be re-reported… once the headline B=1,000 relaunch (T1.2, in progress) lands"; "Note for v2 assembly"; repo paths in body (:1–34, :90–99, :183–190) | — | — | WRONG-REGISTER |

### table1_effects_2026-05-22.md / .json / compute_table1_effects.py

| # | Claim | Verdict |
|---|---|---|
| A8 | The full generated table (40 rows) — same sources as A4 | **UNSUPPORTED** for citation (retain as historical record only) |
| A9 | Result artifacts + producing script located inside `papers/…/sections/` (contra "results go in `results/`, never `papers/`") — exempt from results-tree gates by location | WRONG-REGISTER (tree-placement) |

### methods-w2-formal-definition.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A10 | Formal W₂ definition; diagonal projection cost; p=2 per notation standard (:34–49) | notation.md | matches | VERIFIED |
| A11 | **Edgington p-value with denominator 1+N_pairs, N_pairs=min(500, B(B−1)/2), floor ≈0.002, described as "the formula locked by the T1.1 pre-registration"** (:60–87) | `run_stage1_battery.py:466` | Contradicts the locked convention (denominator = null draws; `p=(r+1)/(B+1)`, floor 1/1001 at B=1000 — CONVENTIONS 2026-05-27, corrective commit `9c81311`) and every canonical headline (`pvalue_null_draws: 1000`, `pvalue_formula: (r+1)/(B+1)`). Also diverges from P01-B §3.3 (correct form) on a shared locked object — the exact class `papers/shared/notation.md` exists to prevent. | **MISDESCRIBED** (major) |
| A12 | Empty-diagram/infinite-feature handling (:56–58) | code | not re-read this pass | NOT-AUDITED (code-level) |
| A13 | Repo path + line numbers in body text; T1.1/T0.12/branch names in HTML + body (:1–30, :78–87) | — | — | WRONG-REGISTER |

### supplement-S0-null-specification.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A14 | §S0.1/§S0.2 present label/cohort shuffle as rungs of the null machinery ("assignment is destroyed; everything else preserved") with no invalidation note (:45–76) | `permutation_nulls.py:53–92` | The 2026-07-16 `[NEGATIVE]` (independently source-confirmed) establishes both operations are invariant to the set-valued statistic — nothing the statistic consumes is destroyed. P01-B §3.2 carries the invalidation; §S0 does not. | **MISDESCRIBED** (major) |
| A15 | §S0.3–§S0.6 order/Markov-1/stratified/Markov-2 algorithms; raw-MLE stratified (no Laplace); Markov-2 α=1 (:79–197) | code | consistent with the [NEGATIVE]'s valid-null characterization and CONVENTIONS α=1 lock | VERIFIED\* |
| A16 | §S0.7 frozen loadings + seed schedule (s_j = seed+j+1; RandomState(seed) pair draws) (:199–228) | driver | matches the corrected headline's recorded method | VERIFIED |
| A17 | §S0.8 Edgington form with 1+N_pairs denominator; "resolution floor 1/(1+N_pairs) ≈ 0.002" (:230–274) | pre-reg T1.1 | same defect as A11 | **MISDESCRIBED** |
| A18 | Task IDs (T1.1/T0.12/T1.2) and repo line refs in body text; "will be re-reported… once the headline relaunch lands" (:230–274) | — | — | WRONG-REGISTER |

### results-bhps-robustness.md (§6.2)

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A19 | "BHPS-era trajectories reject the Markov-1 H₁ null under W₂, whereas the same test is **borderline in the shorter USoc panel**" (:33–35) | headline battery | Inverted vs the canonical record in both eras: the borderline value was BHPS (greedy p 0.019 → exact floor); USoc H₁ was at the floor throughout (exact d_perm +31.16). Neither headline is borderline. | **MISDESCRIBED** |
| A20 | Length-matched: both strategies reject H₁ and H₀ at p=0.001 (Outcome A) (:36–44) | dedup arms | `bhps_length_matched_{truncate,first13}_frozen_2026-05-30.json` — exact-era, both reject; Outcome A stands (2026-05-31 + 2026-07-14 rulings) | VERIFIED |
| A21 | Dedup mechanism: "~139 near-zero-scale phantom H₁ features… inflate… ratio 1.006 → 1.87… strips the phantoms and exposes the underlying signal" (:46–57) | dedup comparison | **Struck by the 2026-07-14 ruling:** the 05-29 observed H₁ diagram has zero sub-1e-6 features; dedup changed the diagram by +2 features (exact W₂ 0.545); the 1.006→1.87 flip is greedy→exact, not no-dedup→dedup; exact arms are statistically indistinguishable (t 1.860 vs 1.866, both reject). Dedup is kept on data-property grounds; the flip is retired as evidence. (`dedup_amendment_comparison_corrected_2026-07-14.json`) | **MISDESCRIBED** (major) |
| A22 | Markov-1 credibility diagnostic: KS p=1.3×10⁻¹⁴, mean double-null p 0.40, CVs 0.309/0.265, verdict suspect, honest caveat propagation (:59–81) | diagnostics | `results/trajectory_tda_bhps/diagnostics/markov1_calibration_2026-06-21.json`, `markov1_nullnull_variance_2026-06-21.json` | VERIFIED\* |
| A23 | Spanning counts: 10,992 spanning individuals, 10,544 with valid income (:87–88) | income audit | `papers/shared/income_concept_audit.md` — both values present | VERIFIED |
| A24 | Non-overlap: "H₁ W₂ rejection… disappears once spanning individuals are excluded (p=0.221) and rejects in none of the twenty matched subsamples," H₁ reported as metric-dependent; robust result is H₀ (:93–105) | `bhps_nonoverlap_reanalysis_2026-06-09.json` | **FALSIFIED for the retained remainder object** (2026-07-16 [DECISION]; SUPERSEDED.md): the committed value reproduces bit-for-bit under greedy; exact W₂ gives d_perm **+7.48**, p 0.000999 — the rejection does NOT disappear, and both metrics agree. The twenty-subsample and L=1882 arms have no retained caches (greedy-era; production re-run required before re-assertion). §6.2 prose direction is on HOLD per the User ruling; rewrite is ARS-lane. | **UNSUPPORTED** (falsified core + unverifiable arms) |
| A25 | EDITORIAL STATUS HTML block with result paths and v2-assembly notes (:1–15) | — | — | WRONG-REGISTER |

### supplement-S6-length-matched-dedup.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A26 | Section core: phantom-feature mechanism; "without it the W₂ statistic is corrupted in a way that exactly masks the signal"; 202.84/201.58 (ratio 1.006, p 0.350) → 6.63/3.55 (ratio 1.867, p 0.000999) attributed to dedup (:41–88) | `dedup_amendment_comparison_2026-06-01.json` | Same defect as A21: the numeric contrast straddles the solver boundary (greedy 05-29 arm vs exact 05-30 arm); under exact W₂ both arms reject and are indistinguishable. The ruling requires §S6 rewritten from an inferential to a provenance/representation argument (PR #106 did so; reverted by #112; parked for ARS). | **MISDESCRIBED** (major) |
| A27 | Probe results: symmetric_dedup −0.66%/−0.24%; pinned_thresh H₀ +6.7% (T 7.87→8.40), H₁ <1%; every cell still rejects (:90–107) | probe files | `…probe-symmetric-dedup_2026-05-30.json`, `…probe-pinned-thresh_2026-05-31.json` (exact-era; the +6.7% figure is the PR #28-corrected value) | VERIFIED\* |
| A28 | "the Monte-Carlo resolution floor 1/(1+N_pairs) at N_pairs = 1,000" (:81–82) | — | mislabels null draws as pairs; floor is 1/(B+1) per the locked contract | MISDESCRIBED (minor) |
| A29 | 39-line HTML header (commits, PR numbers, CodeRabbit, vault pointers) (:1–39) | — | — | WRONG-REGISTER |

### results-stratified-w2-subgroups.md (§6.1)

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A30 | Tables 6.1a/6.1b: 23 subgroup rows (T, BCa, p_adj, landscape p) (:72–115) | T1.28 recompute | `stratified_w2_recompute_2026-07-09.json` + `stratified_w2_bh_per_family_2026-07-09.json` (exact-era, audit-IMMUNE); values consistent with P01-B Table 3 where they overlap | VERIFIED\* |
| A31 | BH for all three families incl. cohort (BY superseded by the 2026-06-27 amendment) (:48–55) | amendment | matches | VERIFIED |
| A32 | "nine of eleven BHPS subgroups reject" — counting the 1940s cohort (W₂ p_adj 0.016; landscape p 0.148, non-reject) as a rejection (:93–98, :111) | — | P01-B Table 3 treats landscape-incomplete/divergent rows as non-headline under the dual-metric mandate; §6.1 counts 1940s as a reject while its own text notes the landscape divergence. Cross-paper inconsistency in rejection-counting policy for the same cells. | MISDESCRIBED (consistency, minor) |
| A33 | Power caveat on the two smallest cells (pre-registered underpowered) (:117–131) | pre-reg | matches record | VERIFIED |
| A34 | EDITORIAL STATUS HTML block ("TWO decisions pending… User to confirm/decide") (:1–17) | — | — | WRONG-REGISTER |

### results-ari-stability.md (§4.6 + Tables 2/3 additions)

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A35 | Raw OM-vs-GMM ARI 0.2611; achievable-max bracket [0.8397, 0.8607]; normalised 0.31 (bracket [0.3035, 0.3111]; rescaled CI [0.3030, 0.3195]); perm null SE 5.80×10⁻⁴, p 2.0×10⁻⁴; bootstrap CI [0.2544, 0.2683] (:8–47) | `ari_om_gmm_normalised_2026-06-24.json` | file present; matches the T1.23d certification record (incl. the counterexample-driven ~0.31-not-0.40 correction) | VERIFIED\* |
| A36 | Table 2 stability SEs/Wilson CIs on the stored metric, member-count denominator (:49–71) | `stability_se_stored_2026-06-22.json` | present at `results/panel_methodology/uncertainty_addons/` — the corrected stored-metric file (supersedes the internally inconsistent `stability_se_2026-05-16.json`) | VERIFIED\* |
| A37 | Table 3 escape Wilson CIs (5.58% [5.08, 6.13]; 17.85%; 0.10%) (:73–85) | `escape_wilson_ci_2026-05-16.json` | present at `…/uncertainty_addons/` | VERIFIED\* |
| A38 | "This working file covers… (reviewer issue B9)… (B10…)… (B11…)"; "(The reviewer's response plan anticipated a null standard error near 0.009…)"; closing "Provenance status" section with JSON filenames (:3–6, :38–40, :87–99) | — | — | WRONG-REGISTER (multiple banned tokens) |

### results-escape-regression-foo.md (§4.5)

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A39 | Descriptive rates: 7,453 starters / 416 escapes / 5.58%; working-age 386/2,163 / 17.85% (:3) | escape files | consistent with `escape_wilson_ci_2026-05-16.json` (A37) | VERIFIED |
| A40 | IPW build: AUC 0.7137, ESS 57,035, weight max 535.89→42.78, CV 1.3623→0.9942, cohort coef −6.196; T1.29 eligibility 93.01%; Manski bounds 0.44%/1.34% (:5) | weights/selection/manski files | artifacts present under `results/panel_methodology/{weights,selection_sensitivity,manski_bounds}/` | VERIFIED\* |
| A41 | Tier build-up + headline: Firth OR 18.5954 (n 6,173); GLMM OR 21.29, ICC 0.0595; svyglm headline log OR 3.5516 / OR 34.8691 (n 7,097, 20 imputations); diagnostic companion ICC 0.0622; full coefficient table (:9–45) | regression files | `tier1_clustered_firth_2026-05-16.json`, `tier2_glmm_*`, `tier2_svyglm_headline_2026-06-03.json`, `tier2_ipw_mice_svyglm_2026-06-03.json` — present; consistent with the sample-provenance record | VERIFIED\* |
| A42 | Weighted-RE non-estimability (glmmTMB σ_u 35.6, ICC 0.9974; WeMix NSD; 4,001-s smoke; 6,037 households) (:49) | diagnostics | consistent with the T1.21-era record | VERIFIED\* |
| A43 | Cross-tab χ²=0.5747 df=2 p=0.7503; upstream-selection reading; "formal mediation deferred; the earlier formal-mediation analyses (T1.21/T1.22) were superseded and are not reported" (:47) | — | supersession statement matches the record; but the Task IDs belong to the report channel | VERIFIED (content) / register flagged in A45 |
| A44 | §4.5.1 FOO topology: p 0.00019996; within-pair distance 0.1132; ratio 0.8243; ICCs 0.5810/0.5096/0.4728; comparator arms same floor; SUPPORT + SIGNAL_NOT_TOPOLOGY_SPECIFIC (:51–55) | foo_topology files | `results/trajectory_tda_integration/foo_topology/…2026-06-02.json` (3 files present); locked interpretation matches | VERIFIED\* |
| A45 | Task IDs in body ("(T1.29)", "(T1.15)", "(T1.21/T1.22)"); "*provisional label; final table number set at v2 assembly*" captions (:5, :9, :20, :47) | — | — | WRONG-REGISTER |

### methods-embedding-dimensionality.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A46 | Quoted paragraph: 49% variance at D=20; full-embedding d 3.6/5.8 (USoc), 3.8/6.3 (BHPS); landmark-subset d 10.1/9.2, 5.0/6.7; USoc landmark estimate at the D/2 threshold (:51–86) | intrinsic-dim JSONs | `intrinsic_dim_2026-05-24.json` ×2 — values match | VERIFIED |
| A47 | Damrich et al. reliable-regime/threshold attributions (:59–86) | literature | attribution accuracy not checked | NOT-AUDITED (literature) |
| A48 | HTML evidence header + "Note for v2 assembly" (:1–49, :88–95) | — | — | WRONG-REGISTER |

### methods-h0-orthogonality.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A49 | "ARI of 0.00004 between the GMM partition and the H₀ tree-cut at k=7" — used twice as the load-bearing quantitative anchor of the §4.2 rewrite and §4.4 sharpening (:47–66) | v1 §4.4 | **No artifact located on `main`** backs 0.00004. The nearest canonical H₀-vs-GMM object (`ari_normalised_2026-06-06.json`) reports observed ARI 0.2425 for its recorded comparison; the §4.6 working file states the H₀-vs-GMM material was removed as "a different object". Value appears to be a v1-era unverified number. Requires re-derivation (with referent recorded) before any rewrite uses it. | **UNSUPPORTED** |
| A50 | Dominant H₀ component: persistence 15.81, mean 4.08, 99.98%, six singleton outliers (:42) | v1 §4.2 | v1-era descriptive; embedding vintage unestablished (pre-frozen suspect) | NOT-AUDITED (v1 vintage) |
| A51 | VR-H₀-vs-density-modes framing (Chazal & Michel) (:23–53) | literature | interpretive/literature | NOT-AUDITED |
| A52 | HTML header + "Note for v2 assembly" (:1–21, :68–72) | — | — | WRONG-REGISTER |

### methods-h1-artefact-caveat.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A53 | Quote block: low-persistence H₁ features can be sampling/projection artefacts; substantive H₁ analysis is the null comparison (:22–29) | — | methodological caveat; consistent with record | VERIFIED (interpretive) |
| A54 | "(cf. Bauer 2021; **Reviewer 1, Issue 9**)" inside the manuscript quote block (:27) | — | banned tracker token in referee-visible text | WRONG-REGISTER |
| A55 | v1 figures (5,962 H₁ features; max persistence 3.21 vs H₀ 15.81) referenced in the framing (:5–9) | v1 | v1 vintage | NOT-AUDITED (v1 vintage) |

### results-mapper-vocabulary-audit.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A56 | §5.1 caveat: Mapper is a cover-nerve construction, not a homological invariant; vocabulary policy (:24–39) | Singh et al. 2007 | methodological; sound | VERIFIED (interpretive) |
| A57 | Threshold sweep: 358/134/40 flagged nodes (all surviving per-node BH); multi-threshold table (703/638; 358/297; 134/130; 40/74); regime-level BH: only R0/R1 on the L2 lens survive (6.8×10⁻⁴, 8.7×10⁻⁵) (:73–109) | `sub_regime_thresh_sweep_2026-06-07.json`, `03_multi_threshold.json` | present (`results/trajectory_tda_integration/mapper_threshold/…`, `results/trajectory_tda_mapper/reviewer_response/…`) | VERIFIED\* |
| A58 | File is structured as an edit-plan (v1 line-number patch table, "entered as one-to-one replacements when the v2 draft is assembled", §2.3 gating note, "reviewer issue B12" heading) (:41–71, :72) | — | working-document register throughout | WRONG-REGISTER (structural) |

### supplement-S8-foo-transparency.md

| # | Claim | Asserted source | Canonical artifact | Verdict |
|---|---|---|---|---|
| A59 | Fitted-stage counts 6,995 / 6,284 singletons / 711 multi-members / 342 clusters; earlier 7,098/6,363/735/353 identified as pre-complete-case (:3) | sample-provenance record | matches the 2026-06-03b CONVENTIONS lock exactly (the T1.35 divergence, corrected) | VERIFIED |
| A60 | Singleton decomposition (4,350 true / 1,934 filtered; 1,932 by starter restriction) (:5) | `singleton_decomposition_corrected_2026-06-03.json` | present | VERIFIED\* |
| A61 | Concordance: 396 pairs; table (2,14,25,355); κ 0.0445 [−0.0552, 0.1952]; McNemar 0.1093; OR 2.0286 [0.6390, 8.2653] (:7) | foo_transparency files | present | VERIFIED\* |
| A62 | Power sim type-I 0.951 ⇒ "engine not calibrated"; σ_foo 6.2319 treated as artifact; full-sample σ_foo 0.1702 [0.0001, 36.9459] as fragile disclosure (:9–11) | foo_transparency files | honest artifact-consistent reporting | VERIFIED\* |

(§S8 carries no scaffolding — the only P01-A file fully clean of register violations.)

**P01-A counts (62 rows, A1–A62; each row counted once by its primary verdict):**
VERIFIED 12 (A10, A16, A20, A23, A31, A33, A39, A43, A46, A53, A56, A59 —
A43/A53/A56 are content-verified with their register issues carried by separate
rows) ·
VERIFIED\* 15 (A15, A22, A27, A30, A35–A37, A40–A42, A44, A57, A60–A62) ·
MISDESCRIBED 9 (A6, A11, A14, A17, A19, A21, A26, A28, A32) ·
UNSUPPORTED 7 (A1, A2, A4, A5, A8, A24, A49 — A2 is double-tagged
UNSUPPORTED/MISDESCRIBED and counted here by its primary tag) ·
WRONG-REGISTER 14 (A3, A7, A9, A13, A18, A25, A29, A34, A38, A45, A48, A52,
A54, A58 — one flag in each of 14 of the 15 audited P01-A documents) ·
NOT-AUDITED 5 (A12, A47, A50, A51, A55).
Net: **every P01-A document except `supplement-S8` carries at least one
WRONG-REGISTER flag** (14 of 15), and the four Table-1/negative-control/§6.2/§S6
files carry the major UNSUPPORTED/MISDESCRIBED findings.

### Five worst findings (both papers)

1. **A1** — `results-negative-control-wording.md` asserts eight
   invalid-by-construction p-values as the paper's negative-control evidence
   (no re-run can rescue the design; replacement panel T1.41 not yet run).
2. **A24** — §6.2's non-overlap H₁-disappearance claim is falsified for the
   retained remainder object (exact p 0.000999, d_perm +7.48) and its
   twenty-subsample arm is unverifiable without a production re-run.
3. **A4/A8** — the entire Table-1 effects family (52 table cells across two
   documents) cites greedy-era pre-frozen sources; the rebuilt eight-row exact
   artifact on `main` is consumed by no prose file.
4. **A21/A26** — §6.2/§S6 defend the dedup amendment by the retired
   phantom-feature/flip mechanism; the flip was the solver (ruling: rewrite from
   inferential to provenance/representation grounds; the reviewed rewrite was
   reverted with #112 and is parked for ARS).
5. **A11/A17 (with B-side echo in §S6/A28)** — P01-A's methods define the
   permutation p-value with the wrong denominator (1+N_pairs, floor 0.002) and
   call it the locked formula, contradicting the 2026-05-27 contract, every
   canonical result file, and P01-B §3.3 — a live cross-paper divergence on a
   contract-locked object. (P01-B's worst: **B9**, the α-sweep sentence whose
   BHPS-H₁ direction claim the exact rebuild contradicts.)

---

## Part 3 — Canonical-State Snapshot (at `e8890fb`)

### 3.1 SUPERSEDED.md canonical-file table vs `main` — all "cite this" files verified present

| Canonical file (SUPERSEDED.md "cite this") | On `main` @ e8890fb | Canonical for |
|---|---|---|
| `results/trajectory_tda_integration/stage1/usoc_headline_frozen_2026-05-28.json` | ✅ | USoc Markov-1 headline **H₀ W₂ + landscape L² only** |
| `results/trajectory_tda_bhps/stage1/bhps_headline_frozen_2026-05-28.json` | ✅ | BHPS Markov-1 headline **H₀ W₂ + landscape L² only** |
| `results/trajectory_tda_integration/stage1/headline_vintage_materiality_corrected_2026-07-14.json` | ✅ | USoc Markov-1 **H₁ W₂** (exact; both vintages; vintage note mandatory) |
| `results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_2026-07-14.json` | ✅ | BHPS Markov-1 **H₁ W₂** (exact) |
| `results/trajectory_tda_integration/stage1/lm_sensitivity_L2500_frozen_2026-05-28.json` / `…L8000…` | ✅ | design-choice role (L=5,000 selection) ONLY — H₁ W₂ numbers unciteable |
| `results/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_frozen_2026-05-30.json` | ✅ | length-matched truncate cell (Outcome A) |
| `results/trajectory_tda_bhps/stage1/bhps_length_matched_first13_frozen_2026-05-30.json` | ✅ | length-matched first13 cell |
| `…/stratified_markov/stratified_markov1_W2_L5000_frozen_2026-05-29.json` | ✅ | frozen stratified Markov-1 battery (superseding the 2026-05-13 file) |
| `results/trajectory_tda_integration/stage1/dedup_amendment_comparison_corrected_2026-07-14.json` | ✅ | dedup comparison **H₁ W₂ cell + decision_summary counts** |
| `results/trajectory_tda_integration/stage1/dedup_amendment_comparison_2026-06-01.json` | ✅ | dedup comparison landscape-L², `dedup_provenance`, probes |
| `results/trajectory_tda_integration/stage1/w2_gap_closure_table1_h1_2026-07-16.json` | ✅ (restored by PR #117, merged 2026-07-17 18:44Z) | the ONLY citable Table-1 H₁ rows (8 cells: order-shuffle/M-1/M-2/stratified × USoc/BHPS, B=100, exact) |
| `results/trajectory_tda_integration/stage1/w2_gap_closure_phase1_2026-07-16.json` | ✅ (PR #117) | exact non-overlap remainder H₁ re-derivation; BHPS M-1 H₁ BCa [2.1646, 2.1832] |
| Path note | ⚠️ | `markov2_alpha_sweep_summary_2026-06-16.json` lives at `results/trajectory_tda_integration/post_audit/` — SUPERSEDED.md and several log entries cite it without a path (one implies stage1). Not a missing file; a pointer imprecision. |

SUPERSEDED.md's do-not-cite lists, the Table-1 lift language, the
INVALID-BY-CONSTRUCTION label/cohort statement, and the §6.2 falsification note are
all present and current at the audited commit (updated by PR #117). BHPS-side
`SUPERSEDED.md` pointer file present and consistent.

### 3.2 Definitive citable-artifact list for the two papers

**Headline inference (Markov-1, L=5,000, B=1,000):** the four files in §3.1 rows
1–4 under their stated H₀/H₁/landscape split, with the sequence-vintage note.

**Table-1-class H₁ effects:** `w2_gap_closure_table1_h1_2026-07-16.json` only
(B=100; the greedy-era `table1_effects_2026-05-22.*` family and both `04_nulls_*`
post-audit sets are unciteable; L=2,000 legacy rows unciteable; label/cohort rows
non-existent by design).

**Length-matched / dedup (P01-A §S6, §6.2; P01-B cross-ref):** the two 05-30 dedup
arms (Outcome A); `dedup_amendment_comparison_corrected_2026-07-14.json` +
`…_2026-06-01.json` per the split above; probes
`…probe-symmetric-dedup_2026-05-30.json`, `…probe-pinned-thresh_2026-05-31.json`.

**Non-overlap (§6.2):** exact remainder cell inside
`w2_gap_closure_phase1_2026-07-16.json`. The committed
`bhps_nonoverlap_reanalysis_2026-06-09.json` greedy H₁ is do-not-cite; its
landscape values stand; L=1882 arm + 20 subsamples pending production re-run.

**Stratified rung (P01-A §6.1; P01-B §4.2.3):**
`results/panel_methodology/fdr/stratified_w2_recompute_2026-07-09.json` +
`stratified_w2_bh_per_family_2026-07-09.json`.

**BHPS credibility diagnostics (§6.2):**
`results/trajectory_tda_bhps/diagnostics/markov1_calibration_2026-06-21.json`,
`markov1_nullnull_variance_2026-06-21.json`.

**Spanning/knee (P01-B §3.4/§4.3):**
`results/trajectory_tda_spanning/knee_robustness/spanning_betti_inference_2026-06-20.json`,
`spanning_AUC_W2_2026-06-09.json`, per-ε\* betti files, pre-reg 2026-06-09;
balance/matched files under `results/panel_methodology/spanning_identification/`.

**Panel/regression (P01-A §4.5/§4.6/§S8):**
`ari_om_gmm_normalised_2026-06-24.json`;
`uncertainty_addons/stability_se_stored_2026-06-22.json` (NOT the 05-16 file);
`uncertainty_addons/escape_wilson_ci_2026-05-16.json`;
`regression/tier1_clustered_firth_2026-05-16.json` (NOT 05-13/05-14),
`tier2_svyglm_headline_2026-06-03.json`, `tier2_ipw_mice_svyglm_2026-06-03.json`;
`weights/`, `selection_sensitivity/`, `manski_bounds/`, `foo_transparency/`,
`foo_topology/*2026-06-02.json` sets.

**Intrinsic dimension / H₂ / Mapper:** `intrinsic_dim_2026-05-24.json` ×2;
`h2_check/` characterization set (pre-reg 2026-06-19);
`mapper_threshold/sub_regime_thresh_sweep_2026-06-07.json`,
`trajectory_tda_mapper/reviewer_response/03_multi_threshold.json`.

### 3.3 Open holes — needs with no canonical artifact at `e8890fb`

| # | Hole | Blocks | Status |
|---|---|---|---|
| H1 | **T1.41 double-null calibration panel** — the negative-control replacement | P01-A Table 1 calibration row/panel + §4.3 rewrite; P01-B §3.3's calibration sentence (B16) | Approved as the final APM compute Task; pre-reg filed at dispatch; consumes T1.38 Phase-2 checkpoints (`scratch/w2_fallback_audit/phase2_checkpoints/2026-07-16/`, gitignored — regenerate from committed runner if absent) |
| H2 | **Markov-2 α=1 certified W₂ cells** (USoc/BHPS × H₀/H₁) | P01-B Table 2 Markov-2 rows; §3.2's α-sweep sentence (B9) | Pre-registered 2026-07-17 (hardened runner, POT-core, `backend_versions`, per-pair arrays); enforcement contract `paper-table-source-reconciliation` staged on the pre-reg branch |
| H3 | **Non-overlap L=1882 matched-fraction arm + 20 same-size subsamples** under exact W₂ (caches not retained) | §6.2's landmark-fraction sensitivity claims (A24 residue) | Deferred into the post-Phase-2 decision; production re-run required |
| H4 | **§6.2 / §4.3 / §S6 rewritten prose** (rulings on file; reviewed #106 rewrite reverted) | P01-A assembly | ARS prose lane (freeze: no APM authoring) |
| H5 | **Prose/table consuming the eight rebuilt Table-1 H₁ rows** | P01-A Table 1 | No draft file cites `w2_gap_closure_table1_h1_2026-07-16.json` yet; the greedy `table1_effects` family is still what the sections carry |
| H6 | **Source of the "certified Markov-2 landscape L²" values** quoted in the 2026-07-17 pre-registration (0.258/0.003/<0.001/<0.001) | Footnote ‡ vs pre-reg conflict (B29) | Not locatable on `main` this audit; either an uncommitted artifact exists or the pre-reg misattributes — resolve before the recompute lands |
| H7 | **Ungated presumed-immune W₂ files in the fragile window** — `markov2_alpha_sweep` (post_audit) is classified UNVERIFIABLE; spanning matched W₂ (2026-06-09, H₀ so births-at-zero immune in principle) has no explicit gate on file | B29/B36 | Convention-gate them or annotate immunity rationale in-band before citation-grade use |
| H8 | **P01-A p-value-formula prose** (A11/A17) — no artifact hole, but the methods text contradicts the locked contract and must be rewritten against `pvalue_null_draws` | P01-A §3.3/§S0 | ARS prose lane |
| H9 | **ARI 0.00004 (H₀-tree-cut vs GMM)** — no artifact | methods-h0-orthogonality (A49) | Re-derive with referent recorded, or drop the numeric anchor |

### 3.4 Audit completeness statement

All 22 markdown files under the two `drafts/sections/` directories were read in
full and every substantive numeric or procedural claim was classified; nothing
was triaged out. The count is 15 P01-A markdown documents — the 14 prose section
files **plus the generated companion table `table1_effects_2026-05-22.md`, which
is included in the audit** (rows A8–A9) — and 7 P01-B section files. The two
non-markdown artifacts in the P01-A sections directory
(`table1_effects_2026-05-22.json`, `compute_table1_effects.py`) were classified
through rows A8/A9 (unciteable sources; tree-placement violation) but not
line-audited as prose. NOT-AUDITED rows (8) are enumerated per file above — they
cover v1-legacy descriptives whose embedding vintage predates the frozen era
(A50, A55), code-level construction details (B3, A12), literature attributions
(A47, A51), one uncrossed reference (B38), and one interpretive passage (B18);
none is load-bearing for a headline claim. (A53/A56 are interpretive but
content-verified, and are counted under VERIFIED.) Value-level bit-checks were performed for the
four Markov-1 headline cells, the BHPS H₁ BCa, the α-sweep BHPS H₁ cell, and the
intrinsic-dimension figures; VERIFIED\* rows rest on artifact presence plus
consistency with the (independently verified) vault record.
