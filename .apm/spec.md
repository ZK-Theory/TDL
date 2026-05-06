---
title: P01-A and P01-B Reviewer-Response Revision to v2
modified: "Locked Python environment" and "Stratified Markov-1" sections updated after T0.1 (sklearn 1.8.0 confirmed; giotto-tda removed; no GMM checkpoint in repo). jbstat section updated after T0.9 (verified, locked recoding). Income section updated after T0.10 (variable name corrected to fihhmngrs_dv; BHPS cohort wave b; calibration results added; tercile-boundary decision PENDING User confirmation). FOO clustering section updated after T0.11 (99.94% coverage confirmed). Modified by the Manager.
---

# APM Spec

## Overview

This project produces v2 drafts of two companion academic papers — **P01-A** (JRSS-A applied) and **P01-B** (JRSS-B methods) — that close every numbered reviewer issue from three independent reviewers per paper, then extracts standalone reproducibility repositories and prepares simultaneous JRSS submission with same-day arXiv posting (`stat.AP` and `stat.ME`). The two papers are revised in lockstep because they share the same checkpoint, embedding, null battery, and Wasserstein audit; many computations marked [P01-A SHARED] in the response plans execute once and feed both papers. Single author Stephen Dorman (The Open University, UK); no deadline; patient cadence over the coming months. Success is defined by the per-paper acceptance-criteria checklists in the response plans (P01-A §12; P01-B §15) plus per-issue verification, with `/humanizer` and human reviewer passes as final gates. A separate post-v2 block performs the full sample re-extraction (P01-A R2 Option A) on the gap-tolerant 10-of-14 sample.

## Workspace

**Repository.** Single git repository at `c:\Users\steph\TDL`, on branch `main`, clean working tree at session start. PowerShell is the default shell; `pdftotext` is available for PDF extraction; `pdftoppm` is not.

**Working targets.**
- `papers/P01-A-JRSSA/` and `papers/P01-B-JRSSB/` — paper-side drafts, figures, notes, `_project.md`, `_outline.md`, `submissions/`
- `papers/shared/` — shared notation file (`notation.md`); cross-paper diagnostic notes
- `papers/style_guides/JRSS/` — JRSS LaTeX class (`statsoc.cls`), `natbib.sty`, `rss.bst`, `statsoc.pdf`, `amssym.{def,tex}`, `stylefile16.zip`
- `trajectory_tda/{data, embedding, mapper, scripts, topology, utils, validation}/` — existing pipeline (reused, updated, developed)
- `shared/`, `shared/deep_learning/` — cross-domain utilities
- `results/...` — numerical artefacts under date-suffixed JSON, never overwritten
- `data/UKDA-6614-tab/` — UKDA Study 6614 (Understanding Society main + Harmonised BHPS), with UKHLS waves a–o and harmonised BHPS waves ba–br

**Reference-only.**
- `.apm-archive/` — previous APM v0.5.3 state (Implementation_Plan.md, Phase_00–Phase_10, Memory/, Delegation/, Manager/Implementation handovers). Historical context only, not a working target.

**Authoritative documents (read locations).**
- Reviewer-response plans, reviewer-issue decompositions, and supporting notes under `papers/P01-A-JRSSA/notes/` and `papers/P01-B-JRSSB/notes/` per the source-documents table in §11
- Project standards: workspace-root `CLAUDE.md` (methodological mandates, code conventions, commit prefixes, after-session sync) and `.claude/CLAUDE.md` (vexp policy, vault-engine MCP server)
- Per-paper status: `papers/P01-{A,B}*/[_project.md, _outline.md]`
- Locked notation: `papers/shared/notation.md`
- Data documentation: `data/UKDA-6614-tab/mrdoc/pdf/` (40+ user guides; the family-matrix guide and harmonised-BHPS user guide are particularly load-bearing)

**Vault access.** Obsidian research vault at `C:\Users\steph\Documents\TDA-Research`, accessed only through the `vault-engine` MCP server (`vault_get`, `vault_query`, `vault_observe`, `vault_skeleton`, `vault_status`, `vault_graph`, `cross_vault`). Authoritative for `CONVENTIONS.md`, `04-Methods/Computational-Log.md`, `04-Methods/Pipeline-Overview.md`, `02-Notes/Permanent/`, `03-Papers/PXX/_project.md`. Not accessible by direct filesystem read.

**Existing `CLAUDE.md` content** to preserve and reference rather than duplicate: project purpose and 10-paper programme overview; Obsidian vault integration workflow; key TDA concepts and library list; code conventions (Python 3.13, 88-char lines, Ruff E/F/I/W, type hints with `numpy.typing.NDArray`, Google docstrings, research-context comment header on new scripts, random seed logging); commit prefixes ([RESULT]/[DECISION]/[NEGATIVE]/[PIPELINE]/[DATA]/[EXPLORE] with vault-action mapping); after-session vault sync; common workflows (test, lint, run pipeline, paper-start sequence); APM workflow placeholder; methodological mandates (W₂ + landscape L²; Markov-order-k; never raw-trajectory PH; never assume BHPS/USoc share variable coding); vexp/jcodemunch code-exploration policy; `vault-engine` MCP usage. The APM_RULES block layered into `CLAUDE.md` during the Rules step adds APM-specific execution patterns without duplicating these.

---

> **Notes:**
> - **Per-section approval pattern.** The User reads each section as drafted; coordination expects User-mediated approvals at section boundaries during the implementation phase, not only at v2-complete checkpoints.
> - **Token-budget-aware Task sizing.** The User has expressed a preference for work units sized for completion within a single agent's budget without interruption. Affects Task granularity decisions.
> - **Concurrent multi-terminal compute is acceptable.** 2–3 parallel VR PH runs at L=5000 are feasible on the local i7 / 32 GB / RTX 3080 per the response-plan budget; dispatch may exploit this.
> - **Second machine available** for the P01-B H3 two-machine bit-for-bit determinism check; provisioning may need a step at the appropriate time.
> - **JRSS formatting questions are embedded in Task descriptions.** When an individual work unit hits a journal-formatting question that has not yet been resolved by the User, the Task surfaces it as an explicit User-facing prompt rather than blocking the work. The Manager should expect these in-Task questions during dispatch.
> - **UKDA T&Cs prohibit redistribution** of `data/UKDA-6614-tab/` contents — extracted repos use pointers and extraction scripts, not embedded data.
> - **Vault access is MCP-only.** Workers and the Manager use `vault-engine` MCP tools (`vault_get`, `vault_query`, `vault_observe`); direct filesystem reads of the vault path will not be available.
> - **Reference-only `.apm-archive/`.** The previous v0.5.3 APM state is preserved as historical record. Workers should not modify or extract from it.
> - **Patient cadence.** No deadline; the User has indicated work proceeds slowly over the coming months. Wall-clock estimates from the response plans inform sequencing but no calendar dates are requested.

## Companion-Paper Structure

The two papers are revised together because they share computational and methodological infrastructure. The substantive division follows the CONVENTIONS BHPS-split rule.

| | P01-A (JRSS-A) | P01-B (JRSS-B) |
|---|---|---|
| Type | Applied | Methods |
| Title | The Geometry of UK Career Inequality: Topology, Regimes, and Mobility Boundaries | Structured Hypothesis Testing for Persistent Homology of Longitudinal Social Data |
| arXiv category | `stat.AP` | `stat.ME` |
| LaTeX class | `statsoc.cls` (JRSS-A track) | `statsoc.cls` (JRSS-B track) |
| Reviewer set | R1 (TDA), R2 (social scientist), R3 (biostatistician) | R1 (TDA), R2 (data/empirical), R3 (shared with P01-A) |
| Source v1 draft | `papers/P01-A-JRSSA/drafts/v1-2026-04.md` (~9,800 words) | `papers/P01-B-JRSSB/drafts/v1-2026-04.md` (~9,100 words) |
| Source content | P01-VR-PH-Core (regimes, BHPS replication) + P02-Mapper (interior structure) | P01-VR-PH-Core (null hierarchy, diagram-level testing) + P03-Zigzag (survey-design diagnostics) |

**Shared computations** (single execution feeds both papers): matched-L W₂ Markov-1 (USoc + BHPS), stratified Markov-1 W₂, landscape L² battery, threshold sensitivity sweep, intrinsic-dimension estimate, H₂ check at L=2000 (Markov-1 null), KDE sub-level-set H₀ (optional), positive-control simulation, ℓ∞ ground-metric sensitivity check, locked-environment two-machine reproducibility check, BHPS H4 negative-control diagnostics (geometry / variance / calibration), per-α Markov-2 sensitivity (α ∈ {0, 0.5, 1, 5}), full BIC curve over k ∈ {3,...,15}.

**Substantive division — items that appear in both papers with different framing:** stratified Markov-1 (P01-A reports outcome A/B/C; P01-B reports as a defined sixth ladder rung), H₂ result (one sentence in P01-B §3.1; descriptive paragraph in P01-A §4.2), H₀ orthogonality (P01-A leads with the framing; P01-B has a light prose audit for consistency).

## TDA / Null-Battery Decisions

**W₂ ground metric: ℓ².** The implementation `gudhi.wasserstein.wasserstein_distance(..., order=2, internal_p=2)` in `vectorisation.py:232` is canonical. The P01-B §3.1 formula is corrected to use ‖·‖₂; cite Skraba & Turner (2020) for stability under ℓ². A single empirical safety-net sensitivity check is run at L=2000, n=50 with `internal_p=inf`; if qualitative agreement holds (both reject or both fail to reject the Markov-1 H₀), the choice is recorded as immaterial. `papers/shared/notation.md` records the locked ground metric and constants. Reference: P01-B response plan §3 (H1).

**Canonical landmark count: L = 5,000.** Single value across total-persistence and W₂ headline statistics in both papers. Cross-landmark sensitivity (L ∈ {2500, 5000, 8000}) reported in supplement for both metrics. Reference: P01-A response plan §1 (H1); P01-B §1 (C1).

**Stratified Markov-1 ladder rung.** Inserted between Markov-1 and Markov-2 in the ladder as Level 4b. Diagnoses and fixes the regime-label loading bug. Root-cause candidates: (1) sklearn version mismatch — sklearn 1.3.x has no Python 3.13 cp313 wheels; the locked environment uses sklearn 1.8.0, so T0.5 must determine whether the collapse persists under 1.8.0 or is resolved; (2) checkpoint-field provenance (which field carries regime labels); (3) embedding/GMM misalignment (was GMM fit on the same embedding used by the null run). No GMM checkpoint files exist in the repo; T0.5 must locate the checkpoint before any loadability check. Run at L=5000, n_perms=100, all seven regimes represented, both H₀ and H₁, on USoc and BHPS checkpoints. Outcome-contingent prose direction is **pre-registered** before the run. Reference: P01-A response plan §2 (H2); P01-B §4 (H2).

**Markov-2 null with explicit Laplace smoothing.** Code change to `permutation_nulls.py:168–234` to add α=1 Laplace smoothing matching the prose intent. Sensitivity sweep over α ∈ {0, 0.5, 1, 5} reported in supplement. Reference: P01-B response plan §11 (M5).

**ε\* knee detection.** Algorithm formalised (pseudocode in P01-B §3.4.2). Spanning Betti comparison reported in three forms: single-ε ratio (current), AUC ratio over the full filtration, and W₂(D₀(X_t^new), D₀(X_t^*)) at matched sample sizes. ε* robustness across {0.54, 0.65, 0.70, 0.80}. Reference: P01-B response plan §9 (M3).

**W₂ test construction: mean-vs-mean with BCa CI.** Replaces the anti-conservative mean-vs-individual construction. Test statistic is the ratio T_ratio = mean(W_obs-null) / mean(W_null-null); permutation null distribution generated by replacing the observed diagram with a fresh null draw. Report the ratio with a 95% BCa CI (delta-method CI as a practical fallback when only summary statistics are stored). Reference: P01-A response plan §B2; P01-B inherits via [P01-A SHARED].

**Permutation B ≥ 1,000.** All B=100 results are retired. B=10,000 used where computational budget permits. P-value formula: $p = (r+1)/(B+1)$ stated explicitly in §3.3 of both papers. Reference: P01-A response plan §B1, §B13.

**Effect sizes alongside p-values.** Permutation z-score $d_\text{perm}$ reported in Table 1; W₂ ratio with 95% BCa CI reported alongside W₂ p-values. Reference: P01-A response plan §B5.

**Two-sided directionality reported.** One-sided framing kept where justified, but lower-tail Markov-1 result (data is 3.7σ below the null total persistence) is reported and interpreted, not silently dropped. Reference: P01-A response plan §B4.

**H₀ framing.** VR H₀ as connectivity / single-linkage merge-tree summary, **not** density-mode regime indicator. Methodological caveat box added to P01-A §3.2. The seven GMM regimes are correctly attributed to density modes. Optional KDE sub-level-set H₀ computed as positive complement to give the *correct* topological evidence for density modes; if computed, included as P01-A §4.2.1. Reference: P01-A response plan §3 (H3).

**Persistence landscape L² as parallel column.** Computed for the full null battery at matched L=5000, k_max=5, n_points=200; sensitivity sweep over k_max ∈ {3, 5, 10} and n_points ∈ {100, 200, 500} at the Markov-1 rung. Tables 1 and 2 in P01-B (and Table 1 in P01-A) get parallel landscape L² columns alongside W₂. Reference: P01-A §5 (M2); P01-B §7 (M1). Implements the CONVENTIONS-locked landscape L² mandate.

**Filtration threshold justification.** 75th-percentile threshold defended via intrinsic-dimension estimate (Levina-Bickel + Facco et al.), elbow heuristic in cumulative total persistence, maxmin landmark-set diameter, and a 50/75/90 sensitivity sweep. Reported in both percentile and absolute-distance units. Reference: P01-A §6 (M3); P01-B §8 (M2).

**H₂ check.** Computed once at L=2000 with `maxdim=2`, plus a single Markov-1 null at n_perms=50. Justifies the H₁ ceiling in §3.2 of both papers. Pre-registered: if H₂ rejects under Markov-1, the methods restriction to q ∈ {0,1} is unjustified and the papers expand. If unaffordable at L=2000, fall back to L=1000 with documentation of the limit. Reference: P01-A §7 (M4/L1); P01-B §12 (L1).

**Negative-control wording.** §4.3 negative-control claim cites W₂ label-shuffle p ≈ 0.45, not legacy total-persistence p ≈ 0.31. BHPS asymmetry (label-shuffle p ≈ 0.036 — not negative control) reported as empirical finding consistent with CONVENTIONS. Reference: P01-A response plan §10.1.

**BHPS H4 negative-control hypothesis discrimination.** Three diagnostics — pairwise-distance KS test for label-shuffle (geometry hypothesis), CV of null-null distribution + L=5000 rerun (variance-inflation hypothesis), 100-trial double-null p-value uniformity check (calibration hypothesis). Pre-registered: outcome determines whether the BHPS Markov-1 rejection is fully credible, conditionally credible, or suspect. Reference: P01-B response plan §6 (H4).

**Mapper-vocabulary audit.** §5 of P01-A re-worded so that no Mapper-derived quantity is called "topological"; replaced with "Mapper graph property" / "Mapper geometry" / "graph-based summary". Reference: P01-A response plan §10.3.

**Mapper threshold sensitivity.** Sub-regime node count recomputed at |z| ∈ {1.0, 1.5, 2.0}; B reported; per-node z-scores BH-corrected for individual-node identification. Reference: P01-A response plan §B12.

**FDR family redefinition.** §6.1 stratified W₂ tests split into three BH families (2 gender, 6 NS-SEC, 42 cohort) with BY correction for the cohort family. Reference: P01-A response plan §B8.

**ARI normalisation.** ARI reported with null SE, max-achievable ARI (given cluster-size distributions), normalised ARI, and 95% bootstrap CI. Reference: P01-A response plan §B9.

**Stability score and escape rate uncertainty.** Per-regime stability scores reported with binomial SE (Table 2). Wilson 95% CIs on every escape rate (Table 3). Reference: P01-A response plan §B10–B11.

**BIC curve.** Full BIC over k ∈ {3,...,15} reported as figure or table; ΔBIC between k=7 and nearest competitors interpreted on the Kass-Raftery scale. Reference: P01-A response plan §B6.

**BHPS H1 length-matched analysis.** Both truncation and first-13 windowing strategies on BHPS to 12.9 years. Pre-registered: outcome determines whether §6.2 reports an era-specific H₁ finding or a window-length artefact; "future work" hedge replaced with a tested claim. Reference: P01-A response plan §9 (L3).

## Panel-Data and Regression Decisions

**R as the regression language.** All regression work — Tier 1/2/3 GLMM, Firth penalisation, MICE — is done in R. Thin Python wrappers around R scripts are accepted where they help integration. Output serialised to JSON for downstream prose insertion. Libraries: `lme4`, `glmmTMB`, `logistf`, `mice`, `survey`, `igraph`.

**Final regression specification: Tier 3 cross-classified GLMM.** Random intercepts for current household (`hidp`) and family of origin (constructed from `xhhrel`), Firth-penalised likelihood for separation control, sibling-consistent MICE for parental NS-SEC. Tier 1 (clustered SE on `hidp` + Firth) and Tier 2 (household-RE GLMM + Firth) reported as build-up specifications in the same regression table to make the methodological logic legible. Reference: P01-A response plan §S5, §S7, §S9.

**Family-of-origin clustering uses `xhhrel.tab`.** The Understanding Society family matrix at `data/UKDA-6614-tab/tab/ukhls/xhhrel.tab` provides cross-wave, cross-survey relationship identifiers and an `osm_hh` origin-household identifier. It supplants the multi-source `ppid`/`mpid` reconstruction proposed in plan §S5.9 and gives substantially better coverage for sibling identification, particularly for the spanning BHPS-USoc subsample. The family-matrix user guide is at `data/UKDA-6614-tab/mrdoc/pdf/6614_main_survey_user_guide_family_matrix_xhhrel.pdf`. **T0.11 complete (commit `74e147d`):** FOO clusters built from bcx/bpx/bsbx biological edges; 27,972 connected components (excl. singletons), 99.94% xwavedat coverage; median cluster size 3, max 48. ICC (gross HH income, wave b)=0.899 upper bound (co-residential inflation — true ICC lower but clearly material). FOO cluster IDs at `data/derived/foo_clusters_2026-05-06.csv`.

**Sibling-consistent MICE for parental NS-SEC.** Imputation done at the family-of-origin level: where ≥1 sibling has observed NS-SEC the value propagates; where all are missing, single cluster-level imputation; for singletons, standard individual-level MICE. Custom imputation code required.

**Standard MICE for income within observed waves.** 20 imputations, Rubin-pooled estimates for regime-membership and escape statistics. Predictors: prior/subsequent wave income, employment status, household composition, region and wave fixed effects.

**Sample correction sequence: Option B for v2; Option A as a separate post-v2 block.** Option B implements Components 2 (two-stage IPW from `lwtresp` × continuity propensity), 3 (MICE for income), 4 (Manski bounds for permanent attritors), and 5 (honest scope statement) with Component 1 (gap-tolerant 10-of-14 rule) as a sensitivity check (GMM only, no full TDA pipeline rerun). Option A then reruns the entire TDA pipeline on the gap-tolerant point cloud as primary analysis, with the original 27,280 sample demoted to robustness. Reference: P01-A response plan §S1.

**Endogeneity / mediation framework.** §4.5 explicitly names the mediation structure: parental NS-SEC operates on escape probability primarily through initial regime placement. Baron-Kenny or causal-mediation decomposition reports total / direct / indirect effects. Reference: P01-A response plan §S8.

**Quasi-separation control.** Firth penalisation is the primary specification for any model touching age × regime × cohort cells with near-zero escape. Profile-likelihood CIs (not Wald) for all ORs. Reference: P01-A response plan §S9.

**Exchangeability of permutation tests.** Label-shuffle permutation operates at the individual-trajectory level (entire trajectories permuted), not the person-year level. Where household clustering matters for an outcome, household-block permutation is used. Reference: P01-A response plan §B3.

**Survey-weight handling for TDA.** PCA / persistent homology / Mapper cannot be directly weighted. Use weighted bootstrap resampling — draw trajectories with probability proportional to combined `lwtresp × continuity` weight — to construct the point cloud, and report sensitivity of diagram-level results. Weighted descriptive statistics and regression use the combined weight directly. Reference: P01-A response plan §S2.

**`jbstat` harmonisation and BHPS/USoc state-space comparability.** Verified (T0.9, commit `ea6f657`). All 33 waves confirmed consistent (BHPS ba–br + UKHLS a–o); all code labels verified from UKDA wave-level RTF data dictionaries (not inferred). **Locked recoding:** `jbstat_E <- c(1, 2, 5, 11, 12, 13, 14, 15)` (employed inc. apprenticeship, furlough, parental/adoption leave); `jbstat_U <- c(3, 9)` (unemployed); `jbstat_I <- c(4, 6, 7, 8, 10, 97)` (inactive inc. unpaid family business). Codes 12–15 are UKHLS-only (furlough from wave k; parental/adoption leave from waves m/n); these are confirmed E-bin. Structural difference from v1 plan: code 11 "On apprenticeship" is UKHLS c–o only (not in BHPS), confirmed E-bin. Reference: P01-A response plan §S4; audit at `papers/shared/jbstat_harmonisation_audit.md`; JSON at `results/panel_methodology/harmonisation/jbstat_coding_2026-05-06.json`.

**BHPS / USoc income concept reconciliation.** Verified (T0.10, commit `de724f6`). **Variable name correction:** `fihhmn` and `fihhmnnet3_dv` do not exist in UKDA-6614. Canonical variable is `{wave}_fihhmngrs_dv` (gross household income, month before interview), present identically in BHPS and UKHLS `hhresp` files. BHPS net (`hhneti`) and UKHLS net (`fihhmnnet1_dv`) use different derivation methods and are not directly cross-era comparable. **BHPS cohort enrollment:** BHPS cohort enrolled into UKHLS from wave b (2010–12), not wave a (2009–11); wave a has 0 BHPS br respondents. Spanning individuals: 10,992 (10,544 with valid income in both waves). **Calibration results (br × b):** Spearman ρ=0.760; exact tercile concordance=68.9% (FLAG — below the 80% quality gate); within-1-bin concordance=96.7%; MALR=0.359; median ratio=1.055×. **Tercile boundary decision: LOCKED — within-era boundaries (User-confirmed).** Income terciles (L/M/H) are defined relative to the wave-specific gross household income distribution, consistent with standard mobility research practice. Cross-era rank preservation confirmed: Spearman ρ=0.760, 96.7% within-1-bin concordance on n=10,544 spanning individuals; the 31.1% who change exact tercile at the BHPS→USoc boundary do so during the 3-year gap spanning the 2008 financial crisis — treated as genuine income mobility. For T1.14: MICE imputes within each survey era independently, then assigns tercile relative to that era's distribution. For T1.19–T1.21 regression: income state at each wave uses within-era tercile, consistent with how the GMM regimes were originally identified. Reference: P01-A response plan §S12; audit at `papers/shared/income_concept_audit.md`.

**BHPS overlap / "replication" reframing.** "Cross-era replication" → "cross-era robustness check" or "cross-era consistency analysis" throughout. Spanning-individual count reported explicitly. Non-overlapping BHPS sensitivity check (exclude spanning individuals) reported in supplement. Reference: P01-A response plan §S10; P01-B response plan §13.1 and D-series.

**Spanning-individual identification check.** Demographic balance table comparing spanning individuals vs USoc newcomers on age, sex, education, initial employment status, initial income, birth cohort. Propensity-score / coarsened-exact-matched subset rerun and age-stratified sub-analysis for the parallel-trends defence. Reference: P01-B response plan §10 (M4).

**Sparse U-states.** Effective dimensionality of the bigram matrix reported. 6-state (E/I × L/M/H) sensitivity rerun if computationally feasible; ARI between 9-state and 6-state regimes reported as evidence that U-states do not drive results. Reference: P01-A response plan §S13.

## Reproducibility Framework

**Locked Python environment.** A `uv.lock` (and `pyproject.toml` snapshot) committed to the repo at commit `214586e` on branch `pipe/lock-python-env`. Confirmed pins: Python 3.13.5, numpy 2.3.2, scipy 1.16.1, scikit-learn 1.8.0, gudhi 3.11.0, ripser 0.6.14, persim 0.3.8 — 103 packages total. Notes: (a) sklearn 1.3.x has no Python 3.13 cp313 wheels; 1.8.0 is the actual locked version; T0.5 diagnoses whether the GMM regime-label collapse is resolved under 1.8.0 or requires refitting. (b) giotto-tda removed — no cp313 wheels exist; TDA pipeline operates on gudhi/ripser/persim directly; any `gtda.*` imports in downstream code will fail and must be removed. (c) scikit-tda meta-package not resolvable for Python 3.13; its components ripser and persim are pinned directly. (d) BLAS thread pins are in `.env` (gitignored) and `.env.example` (committed); loading is manual: `uv run --env-file .env python script.py`. (e) No GMM checkpoint files (`.pkl`, `.joblib`, `.pickle`) exist in the repo; the checkpoint presumably lives outside the repo in a gitignored location; T0.5 must locate it before any loadability check. `MKL_NUM_THREADS=1` and `OMP_NUM_THREADS=1` set for BLAS determinism. Reference: P01-B response plan §5 (H3).

**Two-machine bit-for-bit determinism.** The locked-environment run is executed on two machines; numerical outputs must match exactly. Where they do not, the cause is documented and pinned (BLAS variant, RNG propagation, etc.). The second machine is provisioned at the appropriate time. Reference: P01-B response plan §5 (H3).

**Deterministic seed propagation.** A master seed flows to every downstream RNG (maxmin landmark selection, surrogate generation, null-null pair sampling, GMM initialisation, MICE iterations). `permutation_nulls.py`, `trajectory_ph.py`, and the script wrappers are audited for unseeded `np.random.default_rng()` calls. Random seeds recorded in every output file and in the corresponding vault Computational-Log entry.

**Pre-registration discipline.** Before each outcome-contingent run — H2 stratified-Markov A/B/C, H1 ℓ∞ ground-metric sensitivity, M3 ε* knee robustness, H4 BHPS negative-control a/b/c — a pre-registration entry is written to vault `04-Methods/Computational-Log.md` with timestamp, parameter values, decision rule, and the prose-direction rule for each outcome. The post-run results entry references the pre-registration.

**No-overwrite policy.** New numerical outputs are written under date-suffixed filenames in the existing `results/...` tree (e.g., `04_nulls_wasserstein_w2_L5000_<date>.json`). Archived JSONs are never silently replaced. CONVENTIONS-locked.

**Headline number provenance.** Every numerical claim in v2 is traceable to a specific locked-environment results file via a per-paper provenance table in the supplement.

## Data Infrastructure

**Source dataset.** UKDA Study 6614 — Understanding Society main survey (UKHLS waves a–o) plus Harmonised BHPS (waves ba–br) — at `data/UKDA-6614-tab/`. The harmonisation is the working assumption for cross-survey comparability of `jbstat`, income, and other state-space-relevant variables; verification gates the corresponding R2 work.

**Per-wave files.** `*_indresp.tab` (individual response, includes `jbstat` and missingness profiles), `*_income.tab` (income breakdown), `*_egoalt.tab` (within-wave relationship pairs), `*_indall.tab` (co-resident kin including parent/spouse identifiers), `*_hhresp.tab` (household-level response).

**Cross-wave files.** `xwavedat.tab` (cross-wave individual-level data including `pidp`, `ppid`, `mpid`), `xhhrel.tab` (the family matrix — cross-wave family relationships with `osm_hh` origin-household identifier; the canonical FOO-clustering source).

**Documentation.** `data/UKDA-6614-tab/mrdoc/pdf/` — 40+ PDF user guides. Particularly load-bearing: `6614_main_survey_user_guide_family_matrix_xhhrel.pdf` (FOO clustering source-of-truth), `6614_bhps_harmonised_user_guide.pdf` (harmonisation rules), `6614_main_survey_user_guide.pdf` (general). UKDA T&Cs prohibit redistribution; standalone repos use pointers and extraction scripts, never embedded data.

**No data caching expected.** Some `results/...` JSON files exist from previous runs and are historical, never headline.

## Validation Framework

**Per-paper acceptance-criteria checklists** at P01-A response plan §12 (12.1 methodological completeness, 12.2 result completeness, 12.3 framing fixes, 12.4 CONVENTIONS compliance, 12.5 reproducibility) and P01-B response plan §15. These are the master verification surface for v2.

**Per-issue verification sub-sections** in the response plans — each numbered issue has a §X.6 Verification block defining what must hold in v2 prose and computation.

**`/humanizer` pass.** Essential before any draft is considered ready. Specifically tuned for academic writing in TDA / computational social science; addresses both general AI tells and academic-specific patterns.

**`/notation-check` pass.** Run at every prose change against `papers/shared/notation.md` to prevent compounding inconsistencies. Not batched; not deferred.

**Per-section human review.** The User reads each section as drafted; section-level approval is a gate, not just v2-completion approval.

**Final human reviewer pass.** Before submission, an end-to-end review by an external human reviewer.

**Pre-registration as evidence.** Outcome-contingent decisions reference the pre-registered vault entry; no post-hoc reframing without the pre-registration on record.

## Outputs and Submission Targets

**Drafts.** `papers/P01-A-JRSSA/drafts/v2-YYYY-MM.md` and `papers/P01-B-JRSSB/drafts/v2-YYYY-MM.md`, each with section-level files in `drafts/sections/` if useful. Versioning rule `vN-YYYY-MM.md`, never overwriting prior drafts. Subsequent revisions (v3, etc.) follow the same convention.

**Supplements.** Per the response plans: P01-A supplement (S0 null specification, S2 attrition analysis, S4 landmark robustness, plus thresholds, intrinsic dimension, Markov-2 α sensitivity, landscape L² resolution sensitivity, BIC curve, demographic balance, knee-detection robustness, double-n W₂ sanity, BHPS H4 diagnostics, full coefficient table, ARI null & max). P01-B supplement (S0 null specification, S1 landmark robustness, S2 threshold sensitivity, ground-metric statement, knee-detection algorithm, Markov-2 α sensitivity, BHPS H4 diagnostics, replay-drift project history).

**Numerical outputs.** All under `results/...` per existing tree, with date-suffixed filenames matching the response-plan artefact lists. No legacy file overwritten.

**Figures.** Targeted at JRSS submission specifications from generation: vector PDF, journal-prescribed dimensions and typography per `statsoc.cls` and `statsoc.pdf`. Figures in `papers/PXX/figures/`. Specific regenerations and additions enumerated in the response plans.

**Standalone reproducibility repositories.** Extracted to `papers/P01-A-JRSSA/repo/` and `papers/P01-B-JRSSB/repo/`. Contents: locked `uv.lock` and `pyproject.toml` snapshot; subset of `trajectory_tda/` and R code that the paper actually exercises; pointer to `data/UKDA-6614-tab/` plus an extraction script (UKDA T&Cs); all headline `results/` JSONs at frozen timestamps; fixed seeds; README with replication procedure; replication script that reproduces every Table and Figure number. Zenodo DOI applied at submission, post-v2 (or v3) draft.

**Vault entries.**
- `04-Methods/Computational-Log.md`: pre-registrations (timestamped before runs), `[RESULT]` per computation, `[DECISION]` for any locked parameter or method, `[NEGATIVE]` for informative null findings (a permanent note in `02-Notes/Permanent/` for the latter).
- `04-Methods/Pipeline-Overview.md`: `[PIPELINE]` updates for any pipeline change.
- `CONVENTIONS.md`: any newly-locked rule (e.g., the W₂ ground-metric, the L=5000 canonical landmark count, the stratified Markov rung).
- `papers/shared/notation.md`: notational locks across both papers.
- `03-Papers/PXX/_project.md`: status and open-items updates.

Vault entries are written **directly via the `vault-engine` MCP** at the end of every work session, not drafted for User commit.

**Per-paper `_project.md` updates.** Status, open items, draft history kept current as work progresses. Authorship single-author Stephen Dorman, fixed.

**JRSS submission packages and arXiv metadata.** Built from the v2 drafts (or whichever `vN` has cleared all gates). LaTeX class `statsoc.cls` with `natbib.sty` and `rss.bst`; arXiv categories `stat.AP` (P01-A) and `stat.ME` (P01-B); same-day submission.

## Source Documents and Authority

| Source | Location | Authority for |
|---|---|---|
| P01-A reviewer-response plan | [papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md](papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md) | All P01-A R1 (H1–L3) + R2 (S1–S14) + R3 (B1–B13) + embedded 10.x; sequencing §11; acceptance §12 |
| P01-B reviewer-response plan | [papers/P01-B-JRSSB/notes/2026-05-01-reviewer-response-plan.md](papers/P01-B-JRSSB/notes/2026-05-01-reviewer-response-plan.md) | All P01-B R1 (C1–C2, H1–H4, M1–M5, L1) + R2 (D1–D11); acceptance §15; [P01-A SHARED] flagging |
| R2 P01-A decomposition | [papers/P01-A-JRSSA/notes/2026-05-03-reviewer2-social-scientist-issues.md](papers/P01-A-JRSSA/notes/2026-05-03-reviewer2-social-scientist-issues.md) | S1–S14 details: 5-component sample reconstruction, IPW, MICE, Tiers 1–3 GLMM, Firth, mediation, BHPS overlap, income variable, sparse U-states |
| R3 P01-A decomposition | [papers/P01-A-JRSSA/notes/2026-05-03-reviewer3-biostatistician-issues.md](papers/P01-A-JRSSA/notes/2026-05-03-reviewer3-biostatistician-issues.md) | B1–B13 details: p-value floor, W₂ construction + BCa CI implementation specs (B2.8, B2.9), exchangeability, effect sizes, BIC, regression table, BH families, ARI, stability SEs, escape CIs, Mapper threshold |
| R2 P01-B decomposition | [papers/P01-B-JRSSB/notes/2026-05-03-reviewer2-data-empirical-issues.md](papers/P01-B-JRSSB/notes/2026-05-03-reviewer2-data-empirical-issues.md) | D1–D11 details: data infrastructure, sub-cloud independence, BHPS overlap concerns, income identification across eras |
| Per-paper status | `papers/P01-{A,B}*/_project.md`, `_outline.md` | Paper status, open items, draft history |
| Locked notation | [papers/shared/notation.md](papers/shared/notation.md) | Notation across both papers |
| Methodological mandates | `CLAUDE.md`, `.claude/CLAUDE.md` | W₂ + landscape L² mandate, Markov order k, never raw-trajectory PH, never assume BHPS/USoc share variable coding, vexp policy, vault-engine MCP |
| Vault — convention | `CONVENTIONS.md` (via `vault_get`) | Locked methodological rules |
| Vault — log | `04-Methods/Computational-Log.md` (via `vault_get`) | Logged results and decisions |
| Vault — pipeline | `04-Methods/Pipeline-Overview.md` (via `vault_get`) | Pipeline architecture |
| Data documentation | `data/UKDA-6614-tab/mrdoc/pdf/` | Variable definitions, harmonisation, family-matrix coverage |
| JRSS style | `papers/style_guides/JRSS/{statsoc.cls, natbib.sty, rss.bst, statsoc.pdf, amssym.def, amssym.tex, stylefile16.zip}` | Submission formatting |

The reviewer-response plans use issue codes (H1, M5, S1, B1, C1, D3, etc.) as the canonical reference handles. Per-Task content extraction by the Manager refers to issues by these codes plus their location in the plan documents.
