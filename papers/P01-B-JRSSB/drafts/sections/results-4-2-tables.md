# §4.2 Markov Ladder Results: Matched-Landmark $W_2$, Stratified Rung, Landscape $L^2$

## §4.2.1 Total persistence (Table 1)

Table 1 (scalar total-persistence statistic, $L = 5{,}000$, USoc and BHPS) is incorporated at this location in the assembled manuscript; it is unchanged from the prior draft and is not reproduced in this section file.

## §4.2.2 Matched-landmark ($L=5{,}000$) diagram-level results

**Table 2. Markov ladder, $W_2$ and landscape $L^2$, matched landmarks where available**
*(USoc and BHPS, $H_0$/$H_1$; $T$ = mean-vs-mean ratio, §3.3; BCa = 95% bias-corrected-and-accelerated bootstrap interval; $d_{\mathrm{perm}}$ = standardised permutation effect size)*

| Null level | $L$ | $B$ | Dim | $T$ (BCa 95%) | $d_{\mathrm{perm}}$ | $W_2$ $p$ | Landscape $L^2$ $p$ |
|---|---:|---:|---|---|---:|---|---|
| **USoc** | | | | | | | |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.452 | -- |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | unciteable$^{\dagger}$ | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.458 | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | unciteable$^{\dagger}$ | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | **<0.001** | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | unciteable$^{\dagger}$ | -- |
| Markov-1 (matched) | 5,000 | 1,000 | H0 | 14.91 [14.54, 15.25] | 51.07 | **<0.001** | **<0.001** |
| Markov-1 (matched) | 5,000 | 1,000 | H1 | 3.479 [3.454, 3.503] | 31.16 | **<0.001** | **<0.001** |
| Markov-2, $\alpha=1$ (matched)$^{\P}$ | 5,000 | 1,000 | H0 | 20.33 | 69.24 | **<0.001** | n/a$^{\ddagger}$ |
| Markov-2, $\alpha=1$ (matched)$^{\P}$ | 5,000 | 1,000 | H1 | 1.489 | 31.09 | **<0.001** | n/a$^{\ddagger}$ |
| **BHPS** | | | | | | | |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.036 | -- |
| Label shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | unciteable$^{\dagger}$ | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | 0.034 | -- |
| Cohort shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | unciteable$^{\dagger}$ | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H0 | -- | -- | **<0.001** | -- |
| Order shuffle$^{\dagger}$ | 2,000 | 100 | H1 | -- | -- | unciteable$^{\dagger}$ | -- |
| Markov-1 (matched) | 5,000 | 1,000 | H0 | 9.251 [9.001, 9.504] | 26.53 | **<0.001** | **<0.001** |
| Markov-1 (matched) | 5,000 | 1,000 | H1 | 2.175 [--]$^{\S}$ | 19.26 | **<0.001** | **<0.001** |
| Markov-2, $\alpha=1$ (matched)$^{\P}$ | 5,000 | 1,000 | H0 | 16.95 | 56.76 | **<0.001** | n/a$^{\ddagger}$ |
| Markov-2, $\alpha=1$ (matched)$^{\P}$ | 5,000 | 1,000 | H1 | 0.956 | -2.78 | 0.997 | n/a$^{\ddagger}$ |

$^{\dagger}$ Label/cohort/order-shuffle are **not yet recomputed at matched $L=5{,}000$**; these rows carry the legacy $L=2{,}000$, $B=100$ values from a prior battery unchanged. These rows carry a **second, independent caveat**: their source predates both the exact-solver era (boundary 2026-05-29/30) and the earliest stored null-diagram cache (2026-05-24), so their $W_2$ values were computed under the superseded persistence-rank convention and **no cached diagrams survive against which to gate or correct them** (classification: SUSPECT-UNVERIFIABLE). Their $H_0$ cells are unaffected -- with all births at zero, rank-matching *is* optimal one-dimensional transport, so the $H_0$ values are already exact -- and stand. Their **$H_1$ cells may not be cited without a production re-run** and are marked `unciteable` accordingly. Critically, these $H_1$ cells must **not** be read as negative controls that passed: the superseded convention inflates the observed-to-null and null-to-null distances *together*, driving $T$ toward unity, so under it a negative control **cannot fail**. The absence of rejection in those cells is the direction the convention pushes, not evidence for the null -- they were never actually tested.

$^{\ddagger}$ The Markov-2 $\alpha$-sweep computes $W_2$ only; no landscape $L^2$ companion was computed for this cell. This is a genuine gap against the dual-metric mandate, disclosed rather than filled with an unverified number.

$^{\S}$ BCa interval not re-derived in the exact-$W_2$ correction: the corrected BHPS file reports $T$, $d_{\mathrm{perm}}$, the $W_2$ $p$-value and the per-pair distance arrays, but no bootstrap interval. The interval is **pending** rather than absent in principle -- the retained per-pair arrays make it derivable -- and the superseded interval is deliberately not carried over, since it was computed under a different metric convention and does not describe this statistic.

$^{\P}$ The Markov-2 rows postdate the 2026-05-29/30 solver-convention boundary and are therefore exact-era and presumed unaffected, but they were **not explicitly gated** by the convention audit. They are reported unchanged, pending that confirmation, rather than restated as verified.

**Sequence-vintage note.** Re-derivation of the exact-$W_2$ statistics on the canonical sequence file moves $d_{\mathrm{perm}}$ by at most 0.11 ($H_1$) and 0.23 ($H_0$) and flips no conclusion.

**Metric agreement at Markov-1.** The two metrics agree at every Markov-1 cell in Table 2: both reject decisively in both homology degrees for both datasets. The mandated pairing of $W_2$ with landscape $L^2$ earned its keep in reaching that position -- landscape $L^2$ is computed on a solver-independent path and was therefore unaffected by the superseded $W_2$ convention, so the apparent BHPS $H_1$ disagreement reported in earlier versions of this table was itself the diagnostic that the $W_2$ convention, not the topology, was at fault.

The Markov-2 numbers above are computed under the Laplace-smoothed ($\alpha=1$) code path described in §3.2. The $\alpha$-sensitivity sweep (§3.2) confirms the reject/non-reject pattern reported here -- USoc rejects both dimensions, BHPS rejects H0 but not H1 -- is stable across $\alpha \in \{0, 0.5, 1, 5\}$ and is therefore not an artefact of the smoothing-strength choice.

## §4.2.3 Stratified Markov-1 rung (Level 4b; Table 3)

**Table 3. Per-subgroup Markov-1 irreducibility, three BH families**
*(all subgroups tested against their own Markov-1 null, $B=1{,}000$, seed 42, frozen loadings; $L=\min(5{,}000, n_g)$; BH-adjusted within family)*

| Family | Subgroup | $n$ | $L$ | $T$ | 95% BCa | $W_2$ $p_{\mathrm{adj}}$ | Landscape $L^2$ $p$ | Reject |
|---|---|---:|---:|---:|---|---|---|:---:|
| **USoc** | | | | | | | | |
| Gender | Female | 14,362 | 5,000 | 11.63 | [11.35, 11.92] | 0.001 | 0.001 | Y |
| Gender | Male | 11,218 | 5,000 | 11.44 | [11.16, 11.71] | 0.001 | 0.001 | Y |
| NS-SEC | Intermediate | 8,622 | 5,000 | 9.25 | [9.03, 9.49] | 0.001 | 0.001 | Y |
| NS-SEC | Professional/Managerial | 2,407 | 2,407 | 4.93 | [4.80, 5.07] | 0.001 | 0.001 | Y |
| NS-SEC | Routine/Manual | 10,158 | 5,000 | 10.33 | [10.08, 10.58] | 0.001 | 0.001 | Y |
| Cohort | 1930s | 1,642 | 1,642 | 3.20 | [3.09, 3.30] | 0.001 | 0.001 | Y |
| Cohort | 1940s | 4,155 | 4,155 | 4.58 | [4.46, 4.70] | 0.001 | 0.001 | Y |
| Cohort | 1950s | 4,843 | 4,843 | 7.20 | [7.01, 7.40] | 0.001 | 0.001 | Y |
| Cohort | 1960s | 5,579 | 5,000 | 9.27 | [9.02, 9.51] | 0.001 | 0.001 | Y |
| Cohort | 1970s | 4,674 | 4,674 | 5.52 | [5.35, 5.70] | 0.001 | 0.001 | Y |
| Cohort | 1980s | 3,103 | 3,103 | 6.02 | [5.84, 6.19] | 0.001 | 0.001 | Y |
| Cohort | 1990s | 1,364 | 1,364 | 3.75 | [3.65, 3.85] | 0.001 | 0.001 | Y |
| **BHPS** | | | | | | | | |
| Gender | Female | 3,016 | 3,016 | 5.68 | [5.52, 5.85] | 0.001 | 0.001 | Y |
| Gender | Male | 2,524 | 2,524 | 3.90 | [3.77, 4.03] | 0.001 | 0.001 | Y |
| NS-SEC | Intermediate | 1,790 | 1,790 | 3.77 | [3.65, 3.88] | 0.001 | 0.001 | Y |
| NS-SEC | Professional/Managerial | 335 | 335 | 1.60 | [1.54, 1.66] | 0.086 | 0.003 | **N** |
| NS-SEC | Routine/Manual | 2,620 | 2,620 | 4.15 | [4.03, 4.28] | 0.001 | 0.001 | Y |
| Cohort | 1930s | 986 | 986 | 2.35 | [2.27, 2.43] | 0.010 | 0.001 | Y |
| Cohort | 1940s | 1,360 | 1,360 | 2.18 | [2.11, 2.25] | 0.016 | 0.148 | Y$^{*}$ |
| Cohort | 1950s | 1,373 | 1,373 | 2.86 | [2.77, 2.96] | 0.002 | 0.013 | Y |
| Cohort | 1960s | 1,722 | 1,722 | 3.20 | [3.09, 3.30] | 0.002 | 0.001 | Y |
| Cohort | 1970s | 1,064 | 1,064 | 2.67 | [2.58, 2.76] | 0.002 | 0.001 | Y |
| Cohort | 1980s | 223 | 223 | 1.53 | [1.48, 1.58] | 0.097 | 0.180 | **N** |

$^{*}$ BHPS 1940s cohort: $W_2$ rejects (BH-adjusted $p=0.016$) but landscape $L^2$ does not ($p=0.148$) -- a dual-metric divergence in the opposite direction from Professional/Managerial (where $W_2$ fails to reject but landscape rejects). Both are reported per the dual-metric mandate rather than resolved by deferring to one metric.

**What this rung tests (restated from §3.2).** Each row asks whether subgroup $g$'s topology exceeds *its own* first-order Markov baseline, estimated on that subgroup's own transition data -- a test of per-subgroup Markov-1 irreducibility, not a between-subgroup heterogeneity test. All three families (gender, NS-SEC, cohort) are BH-corrected for both datasets (not BY; the per-subgroup construction runs on disjoint subgroups and the tests are mutually independent, unlike the earlier pairwise adjacent-cohort design).

**USoc: 12/12 subgroups reject.** Every USoc subgroup across all three families rejects its own Markov-1 null under both metrics ($T$ ranging 3.20-11.63).

**BHPS: 9/11 reject under $W_2$, with three distinct dual-metric patterns.** Two subgroups do not reject under $W_2$ after BH adjustment -- Professional/Managerial ($n=335$, $T=1.60$, $p_{\mathrm{adj}}=0.086$) and 1980s cohort ($n=223$, $T=1.53$, $p_{\mathrm{adj}}=0.097$) -- both the two smallest BHPS cells and both **pre-registered as underpowered**, not evidence of equivalence to the Markov-1 null. Three qualitatively different metric patterns appear across the eleven BHPS subgroups: (i) agreement on non-rejection (1980s cohort: neither metric rejects), (ii) $W_2$ rejects but landscape does not (1940s cohort), and (iii) landscape rejects but $W_2$ does not (Professional/Managerial). All three are disclosed in Table 3 rather than summarised as a single "two non-rejections" statement, since the metrics disagree on *which* cells reject. Any interpretation of BHPS stratified rejections should be read together with the BHPS-specific Markov-1 null-credibility caveat reported elsewhere in this paper (the calibration diagnostic finding the BHPS Markov-1 null anti-conservative; P01-A §6.2) -- the BHPS rejections in this table carry that caveat.
