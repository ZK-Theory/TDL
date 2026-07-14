# §4.2 Markov Ladder Results: Matched-Landmark $W_2$, Stratified Rung, Landscape $L^2$

This working file rewrites §4.2 around the matched-landmark ($L=5{,}000$) $W_2$/landscape
recompute, the stratified Markov-1 rung (Level 4b), and effect sizes/BCa CIs, and reconciles
the abstract's ISSUE C2 claim with the locked headline number. Every number below is cited to
its source JSON. §4.2.1's reproducibility disclosure is already superseded by the
Manager-accepted `results-reproducibility-statement.md` and is not repeated here.

## §4.2.1 Total persistence (Table 1) -- unchanged from v1

Table 1 (scalar total-persistence statistic, $L=5{,}000$, USoc) is unchanged from v1; no
matched-landmark scalar recompute was produced for this rewrite, and the scalar statistic
was already reported at $L=5{,}000$ in v1. See v1 §4.2.2 for the table; it is not
reproduced here as no numbers changed.

## §4.2.2 Matched-landmark ($L=5{,}000$) diagram-level results

**Table 2. Markov ladder, $W_2$ and landscape $L^2$, matched landmarks where available**
*(provisional label; USoc and BHPS, $H_0$/$H_1$; $T$ = mean-vs-mean ratio, §3.3; BCa =
95% bias-corrected-and-accelerated bootstrap interval; $d_{\mathrm{perm}}$ = standardised
permutation effect size)*

| Null level | $L$ | $B$ | Dim | $T$ (BCa 95%) | $d_{\mathrm{perm}}$ | $W_2$ $p$ | Landscape $L^2$ $p$ |
|---|---:|---:|---|---|---:|---|---|
| **USoc** | | | | | | | |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.452 | -- |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | 0.538 | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.458 | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | 0.604 | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | **<0.001** | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | 0.906 | -- |
| Markov-1 (matched) | 5,000 | 1,000 | H0 | 14.91 [14.54, 15.25] | 51.07 | **<0.001** | **<0.001** |
| Markov-1 (matched) | 5,000 | 1,000 | H1 | 1.332 [1.330, 1.334] | 22.09 | **<0.001** | **<0.001** |
| Markov-2, $\alpha=1$ (matched) | 5,000 | 1,000 | H0 | 20.33 | 69.24 | **<0.001** | n/a$^{\ddagger}$ |
| Markov-2, $\alpha=1$ (matched) | 5,000 | 1,000 | H1 | 1.489 | 31.09 | **<0.001** | n/a$^{\ddagger}$ |
| **BHPS** | | | | | | | |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.036 | -- |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | 0.330 | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.034 | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | 0.266 | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | **<0.001** | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | 0.070 | -- |
| Markov-1 (matched) | 5,000 | 1,000 | H0 | 9.251 [9.001, 9.504] | 26.53 | **<0.001** | **<0.001** |
| Markov-1 (matched) | 5,000 | 1,000 | H1 | 1.037 [1.035, 1.039] | 2.06 | **0.019** | **<0.001** |
| Markov-2, $\alpha=1$ (matched) | 5,000 | 1,000 | H0 | 16.95 | 56.76 | **<0.001** | n/a$^{\ddagger}$ |
| Markov-2, $\alpha=1$ (matched) | 5,000 | 1,000 | H1 | 0.956 | -2.78 | 0.997 | n/a$^{\ddagger}$ |

$^{\dagger}$ Label/cohort/order-shuffle are **not yet recomputed at matched $L=5{,}000$**; these
rows carry the legacy $L=2{,}000$, $B=100$ values from v1's post-audit battery unchanged. No
matched-landmark file exists for these three levels at the time of this rewrite (this file's
Task Prompt supplied no such input); flagged as an open item below rather than silently
presented as matched.

$^{\ddagger}$ The Markov-2 $\alpha$-sweep (`markov2_alpha_sweep_summary_2026-06-16.json`) computes
$W_2$ only; no landscape $L^2$ companion was computed for this cell. This is a genuine gap
against the dual-metric mandate, disclosed rather than filled with an unverified number (see
Issues).

**Sources.** Markov-1 matched rows: `results/trajectory_tda_integration/stage1/usoc_headline_frozen_2026-05-28.json`,
`results/trajectory_tda_bhps/stage1/bhps_headline_frozen_2026-05-28.json` (both `L=5000, B=1000,
null_model="markov-1", seed=42, pvalue_formula="(r+1)/(B+1)"`). Markov-2 rows:
`results/trajectory_tda_integration/post_audit/markov2_alpha_sweep_summary_2026-06-16.json`,
$\alpha=1$ cell (`L=5000, B=1000, seed=42`). Legacy label/cohort/order-shuffle rows: v1 §4.2.3
Table 2 (unchanged; original source `04_nulls_wasserstein_w2_20260407.json` and BHPS
counterpart per the reproducibility statement).

**M5 prose/code reconciliation note.** The Markov-2 numbers above are computed under the
Laplace-smoothed ($\alpha=1$) code path described in §3.2, which corrects the prose/code
mismatch flagged as ISSUE M5 (v1's Level 5 prose described smoothing the code did not yet
implement). The $\alpha$-sensitivity sweep (§3.2) confirms the reject/non-reject pattern
reported here -- USoc rejects both dimensions, BHPS rejects H0 but not H1 -- is stable
across $\alpha \in \{0, 0.5, 1, 5\}$ and is therefore not an artefact of the smoothing-strength
choice.

**BHPS dual-metric divergence at Markov-1 H1.** $W_2$ only marginally rejects BHPS $H_1$
($p=0.019$, $T=1.037$ -- barely above parity), while landscape $L^2$ rejects decisively
($p<0.001$). Per the dual-metric mandate this divergence is reported, not resolved by
picking one metric: it indicates the two metrics are sensitive to different aspects of the
diagram geometry at this cell, consistent with the divergence pattern documented for BHPS
$H_1$ robustness elsewhere in this paper (P01-A §6.2, non-overlap sensitivity analysis).

## §4.2.3 Stratified Markov-1 rung (Level 4b; Table 3)

**Table 3. Per-subgroup Markov-1 irreducibility, three BH families**
*(provisional label; all subgroups tested against their own Markov-1 null, $B=1{,}000$,
seed 42, frozen loadings; $L=\min(5{,}000, n_g)$; BH-adjusted within family)*

| Family | Subgroup | $n$ | $L$ | $T$ | 95% BCa | $W_2$ $p_{\mathrm{adj}}$ | Landscape $L^2$ $p$ | Reject |
|---|---|---:|---:|---:|---|---|---|:---:|
| **USoc** | | | | | | | | |
| Gender | Female | 14,362 | 5,000 | 11.63 | [11.35, 11.92] | 0.0010 | 0.0010 | Y |
| Gender | Male | 11,218 | 5,000 | 11.44 | [11.16, 11.71] | 0.0010 | 0.0010 | Y |
| NS-SEC | Intermediate | 8,622 | 5,000 | 9.25 | [9.03, 9.49] | 0.0010 | 0.0010 | Y |
| NS-SEC | Professional/Managerial | 2,407 | 2,407 | 4.93 | [4.80, 5.07] | 0.0010 | 0.0010 | Y |
| NS-SEC | Routine/Manual | 10,158 | 5,000 | 10.33 | [10.08, 10.58] | 0.0010 | 0.0010 | Y |
| Cohort | 1930s | 1,642 | 1,642 | 3.20 | [3.09, 3.30] | 0.0010 | 0.0010 | Y |
| Cohort | 1940s | 4,155 | 4,155 | 4.58 | [4.46, 4.70] | 0.0010 | 0.0010 | Y |
| Cohort | 1950s | 4,843 | 4,843 | 7.20 | [7.01, 7.40] | 0.0010 | 0.0010 | Y |
| Cohort | 1960s | 5,579 | 5,000 | 9.27 | [9.02, 9.51] | 0.0010 | 0.0010 | Y |
| Cohort | 1970s | 4,674 | 4,674 | 5.52 | [5.35, 5.70] | 0.0010 | 0.0010 | Y |
| Cohort | 1980s | 3,103 | 3,103 | 6.02 | [5.84, 6.19] | 0.0010 | 0.0010 | Y |
| Cohort | 1990s | 1,364 | 1,364 | 3.75 | [3.65, 3.85] | 0.0010 | 0.0010 | Y |
| **BHPS** | | | | | | | | |
| Gender | Female | 3,016 | 3,016 | 5.68 | [5.52, 5.85] | 0.0010 | 0.0010 | Y |
| Gender | Male | 2,524 | 2,524 | 3.90 | [3.77, 4.03] | 0.0010 | 0.0010 | Y |
| NS-SEC | Intermediate | 1,790 | 1,790 | 3.77 | [3.65, 3.88] | 0.0015 | 0.0010 | Y |
| NS-SEC | Professional/Managerial | 335 | 335 | 1.60 | [1.54, 1.66] | 0.0859 | 0.0030 | **N** |
| NS-SEC | Routine/Manual | 2,620 | 2,620 | 4.15 | [4.03, 4.28] | 0.0015 | 0.0010 | Y |
| Cohort | 1930s | 986 | 986 | 2.35 | [2.27, 2.43] | 0.0105 | 0.0010 | Y |
| Cohort | 1940s | 1,360 | 1,360 | 2.18 | [2.11, 2.25] | 0.0156 | 0.1479 | Y$^{*}$ |
| Cohort | 1950s | 1,373 | 1,373 | 2.86 | [2.77, 2.96] | 0.0020 | 0.0130 | Y |
| Cohort | 1960s | 1,722 | 1,722 | 3.20 | [3.09, 3.30] | 0.0020 | 0.0010 | Y |
| Cohort | 1970s | 1,064 | 1,064 | 2.67 | [2.58, 2.76] | 0.0020 | 0.0010 | Y |
| Cohort | 1980s | 223 | 223 | 1.53 | [1.48, 1.58] | 0.0969 | 0.1798 | **N** |

$^{*}$ BHPS 1940s cohort: $W_2$ rejects (BH-adjusted $p=0.0156$) but landscape $L^2$ does not
($p=0.1479$) -- a dual-metric divergence in the opposite direction from Professional/Managerial
(where $W_2$ fails to reject but landscape rejects). Both are reported per the dual-metric
mandate rather than resolved by deferring to one metric.

**Sources.** `results/panel_methodology/fdr/stratified_w2_recompute_2026-07-09.json` ($n$,
landmarks, $T$, BCa, landscape $L^2$ $p$) and
`results/panel_methodology/fdr/stratified_w2_bh_per_family_2026-07-09.json` (BH-adjusted
$W_2$ $p$, reject flag, per pre-registration amendment 2026-06-27/-28).

**What this rung tests (restated from §3.2).** Each row asks whether subgroup $g$'s topology
exceeds *its own* first-order Markov baseline, estimated on that subgroup's own transition
data -- a test of per-subgroup Markov-1 irreducibility, not a between-subgroup heterogeneity
test. All three families (gender, NS-SEC, cohort) are BH-corrected for both datasets (not BY;
the per-subgroup construction runs on disjoint subgroups and the tests are mutually
independent, unlike the earlier pairwise adjacent-cohort design).

**USoc: 12/12 subgroups reject.** Every USoc subgroup across all three families rejects its
own Markov-1 null under both metrics ($T$ ranging 3.20-11.63).

**BHPS: 9/11 reject under $W_2$, with three distinct dual-metric patterns.** Two subgroups do
not reject under $W_2$ after BH adjustment -- Professional/Managerial ($n=335$, $T=1.60$,
$p_{\mathrm{adj}}=0.0859$) and 1980s cohort ($n=223$, $T=1.53$, $p_{\mathrm{adj}}=0.0969$) --
both the two smallest BHPS cells and both **pre-registered as underpowered**, not evidence of
equivalence to the Markov-1 null. Three qualitatively different metric patterns appear across
the eleven BHPS subgroups: (i) agreement on non-rejection (1980s cohort: neither metric
rejects), (ii) $W_2$ rejects but landscape does not (1940s cohort), and (iii) landscape rejects
but $W_2$ does not (Professional/Managerial). All three are disclosed in Table 3 rather than
summarised as a single "two non-rejections" statement, since the metrics disagree on *which*
cells reject. Any interpretation of BHPS stratified rejections should be read together with
the BHPS-specific Markov-1 null-credibility caveat reported elsewhere in this paper (the
calibration diagnostic finding the BHPS Markov-1 null anti-conservative; P01-A §6.2) -- the
BHPS rejections in this table carry that caveat.

## §4.2.4 Reconciling the abstract's ISSUE C2 claim with the matched-landmark headline

v1's abstract states the Markov-1 discrepancy at the legacy landmark-mismatched figure
($p=0.002$), while v1's Table 2 (mismatched $L=2{,}000$) reports $p=0.070$ for the same cell --
an internal contradiction (ISSUE C1/C2) that the matched-landmark recompute above resolves.
**At matched $L=5{,}000$, USoc Markov-1 $H_0$ rejects decisively under $W_2$
($p<0.001$, $T=14.91$)**, and $H_1$ also rejects decisively ($p<0.001$, $T=1.332$) -- both
stronger than either legacy number. Per the response plan's pre-registered publication rule
(whatever the matched-$L$ result is, the abstract, §4.2, and the discussion must all use the
same number, with no legacy figure surviving anywhere in the headline narrative), the
reconciled statement for both the abstract and this section is:

> The scalar (total-persistence) test reports that first-order Markov dynamics account for
> the topology ($p=1.000$; Table 1), while $W_2$ at the matched landmark count decisively
> rejects the same first-order null ($p<0.001$; Table 2). Second-order Markov dynamics
> (Table 2, $\alpha=1$) reject as well for USoc, localising -- though not eliminating -- the
> discrepancy as a matched-landmark, dual-metric-confirmed finding rather than a
> landmark-count artefact.

This differs from all three of v1's abstract numbers ($p=0.002$ legacy, $p=0.070$
mismatched-$L$ post-audit) and from the original pre-registered contingency's most
conservative branch: the matched-$L$ result is decisive ($p<0.001$), not borderline, so no
major restructuring of the paper's central claim is triggered. The abstract text itself is
out of scope for this Task (§4.2 only); this reconciled sentence is provided so the Manager
can apply it verbatim to the abstract, §4.2, and any discussion-section restatement,
satisfying the "no legacy numbers anywhere" publication rule.

## Issues (for Manager review before v2 assembly)

- **No matched-$L=5{,}000$ recompute exists for label/cohort/order-shuffle.** Table 2's
  three legacy rows remain at $L=2{,}000$; if full landmark-count matching across all five
  rungs is required for JRSS-B submission (per the response plan's original ISSUE C1
  strategy), this recompute is still outstanding and was not an input to this Task.
- **No landscape $L^2$ companion exists for the Markov-2 $\alpha$-sweep.** The dual-metric
  mandate is not yet satisfied for the Markov-2 rows; flagged as `n/a` rather than a
  fabricated number.
- Figure placeholders `[Figure 1]`, `[Figure 2]` from v1 are not re-created here; assign at
  v2 figure-production pass.
