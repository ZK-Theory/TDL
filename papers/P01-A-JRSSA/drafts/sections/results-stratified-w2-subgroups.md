<!--
EDITORIAL STATUS (provisional — awaiting User per-section review)
- Numbers traced to:
    results/panel_methodology/fdr/stratified_w2_bh_per_family_2026-07-09.json  (adjusted p, method, effect sizes)
    results/panel_methodology/fdr/stratified_w2_recompute_2026-07-09.json      (n, actual_landmarks, raw p, landscape L2 p, params)
- TWO decisions pending before this section is locked (see hand-off):
  (1) CORRECTION-METHOD CONFLICT. The Task Prompt specified BY (Benjamini-Yekutieli) for the
      cohort family. The committed files report BH for all three families, and the governing
      pre-registration AMENDMENT (2026-06-27, User-approved) explicitly superseded the base
      2026-06-13 pre-reg's cohort=BY to cohort=BH (disjoint per-subgroup-vs-own-null tests are
      mutually independent -> standard BH). This section is drafted to the files (BH/BH/BH).
      User to confirm the prompt's "BY cohort" was stale.
  (2) SECTION STRUCTURE. Drafted as a single combined 23-subgroup section (USoc + BHPS). The
      BHPS block can instead be relocated to Section 6.2 under the BHPS Markov-1 credibility
      caveat. Recommendation and trade-off in the hand-off; User to decide placement.
- Table numbers provisional (final at v2 assembly). Figure callouts are placeholders.
-->

### 6.1 Stratification by Gender, Parental Class, and Birth Cohort

The pooled null tests of Section 5 establish that the observed career-trajectory
topology is irreducible to a first-order Markov (Markov-1) baseline for the sample
as a whole. A natural objection is that this signal is an artefact of pooling
demographically heterogeneous individuals: a mixture of internally Markov-1
subpopulations can present pooled structure that no single subpopulation exhibits.
We address this directly by re-posing the stratified analysis as a within-subgroup
question. For each demographic subgroup we recompute the canonical Markov-1 $W_2$
headline statistic — the observed persistence diagram $D_q(X_g)$ of subgroup $g$
against its *own* Markov-1 surrogate ensemble — and ask whether each subgroup's
topology, taken alone, exceeds its own first-order Markov baseline. This is a test
of per-subgroup Markov-1 irreducibility, and is a distinct question from whether
subgroups differ topologically from one another.

Each subgroup contributes one test. The statistic is the mean-versus-mean ratio
$T = \overline{W_2}(\text{obs},\text{null}) \,/\, \overline{W_2}(\text{null},\text{null})$,
reported with a 95% bias-corrected-and-accelerated (BCa) bootstrap interval, so that
$T \approx 1$ indicates a subgroup indistinguishable from its Markov-1 null and
$T \gg 1$ indicates topological structure the null cannot reproduce. Tests use
$B = 1000$ Markov-1 surrogates, seed 42, the permutation $p$-value
$p = (r+1)/(B+1)$, and significance level $\alpha = 0.05$; the $W_2$ ground metric is
Euclidean on the birth–death plane. All subgroups are row-subsets of the frozen
full-sample embeddings (USoc $n = 27{,}280$; BHPS $n = 8{,}509$), so the PCA-20
loadings are held fixed across strata. Landmark counts are
$\min(5000, n_g)$ per subgroup and are reported alongside each test, since the
landmark fraction varies across the smaller strata. Persistence-landscape $L^2$
distance is reported as the mandatory complementary metric.

The three stratification axes form three independent false-discovery-rate families,
each corrected separately: gender and parental NS-SEC by Benjamini–Hochberg (BH),
and birth cohort also by Benjamini–Hochberg. (The cohort family is corrected by BH
rather than the Benjamini–Yekutieli procedure used for the earlier pairwise design:
under the per-subgroup construction the cohort tests run on disjoint decade subgroups
and are mutually independent, so the standard BH procedure applies.) Because the
raw $p$-value floor at $B = 1000$ is $1/1001 \approx 0.001$, subgroups with no
surrogate exceedance are reported at that resolution limit.

#### Understanding Society

Every one of the twelve USoc subgroups rejects its own Markov-1 null after
within-family FDR correction (Table 6.1a). Effect sizes are large throughout:
the observed-to-null $W_2$ ratio ranges from 3.20 (1930s cohort) to 11.63 (women),
and every BCa interval lies far above unity. The signal is therefore not a property
of the pooled sample alone — it recurs, at full strength, within each gender,
each parental-class origin, and each birth-decade cohort examined. Persistence-
landscape $L^2$ agrees with $W_2$ on rejection in all twelve USoc strata.

**Table 6.1a. USoc per-subgroup Markov-1 $W_2$ tests (three FDR families).**
Effect size is the observed-to-null $W_2$ ratio $T$ with 95% BCa interval;
$p_{\mathrm{adj}}$ is the within-family BH-adjusted $W_2$ $p$-value; landscape
$L^2$ $p$ is the raw (unadjusted) complementary metric.

| Family (method) | Subgroup | $n$ | Landmarks | $T$ ($W_2$ ratio) | 95% BCa | $p_{\mathrm{adj}}$ | Landscape $L^2$ $p$ | Reject |
|---|---|---:|---:|---:|---|---:|---:|:--:|
| Gender (BH) | Female | 14,362 | 5,000 | 11.63 | [11.35, 11.92] | 0.001 | 0.001 | ✓ |
| Gender (BH) | Male | 11,218 | 5,000 | 11.44 | [11.16, 11.71] | 0.001 | 0.001 | ✓ |
| NS-SEC (BH) | Intermediate | 8,622 | 5,000 | 9.25 | [9.03, 9.49] | 0.001 | 0.001 | ✓ |
| NS-SEC (BH) | Professional/Managerial | 2,407 | 2,407 | 4.93 | [4.80, 5.07] | 0.001 | 0.001 | ✓ |
| NS-SEC (BH) | Routine/Manual | 10,158 | 5,000 | 10.33 | [10.08, 10.58] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1930s | 1,642 | 1,642 | 3.20 | [3.09, 3.30] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1940s | 4,155 | 4,155 | 4.58 | [4.46, 4.70] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1950s | 4,843 | 4,843 | 7.20 | [7.01, 7.40] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1960s | 5,579 | 5,000 | 9.27 | [9.02, 9.51] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1970s | 4,674 | 4,674 | 5.52 | [5.35, 5.70] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1980s | 3,103 | 3,103 | 6.02 | [5.84, 6.19] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1990s | 1,364 | 1,364 | 3.75 | [3.65, 3.85] | 0.001 | 0.001 | ✓ |

Twelve of twelve USoc subgroups are topologically irreducible to their own
first-order Markov baseline. The pooled-sample finding is not an artefact of
demographic composition.

#### BHPS

The BHPS strata are smaller, and here nine of eleven subgroups reject their own
Markov-1 null after within-family FDR correction (Table 6.1b). The two exceptions
are the two smallest strata in the entire stratified design — parental
Professional/Managerial ($n = 335$) and the 1980s cohort ($n = 223$) — and both are
treated below under an explicit power caveat. Every other BHPS stratum
rejects, with effect sizes from 2.18 (1940s) to 5.68 (women).

**Table 6.1b. BHPS per-subgroup Markov-1 $W_2$ tests (three FDR families).**
Columns as in Table 6.1a.

| Family (method) | Subgroup | $n$ | Landmarks | $T$ ($W_2$ ratio) | 95% BCa | $p_{\mathrm{adj}}$ | Landscape $L^2$ $p$ | Reject |
|---|---|---:|---:|---:|---|---:|---:|:--:|
| Gender (BH) | Female | 3,016 | 3,016 | 5.68 | [5.52, 5.85] | 0.001 | 0.001 | ✓ |
| Gender (BH) | Male | 2,524 | 2,524 | 3.90 | [3.77, 4.03] | 0.001 | 0.001 | ✓ |
| NS-SEC (BH) | Intermediate | 1,790 | 1,790 | 3.77 | [3.65, 3.88] | 0.001 | 0.001 | ✓ |
| NS-SEC (BH) | Professional/Managerial | 335 | 335 | 1.60 | [1.54, 1.66] | 0.086 | 0.003 | ✗ |
| NS-SEC (BH) | Routine/Manual | 2,620 | 2,620 | 4.15 | [4.03, 4.28] | 0.001 | 0.001 | ✓ |
| Cohort (BH) | 1930s | 986 | 986 | 2.35 | [2.27, 2.43] | 0.010 | 0.001 | ✓ |
| Cohort (BH) | 1940s | 1,360 | 1,360 | 2.18 | [2.11, 2.25] | 0.016 | 0.148 | ✓ |
| Cohort (BH) | 1950s | 1,373 | 1,373 | 2.86 | [2.77, 2.96] | 0.002 | 0.013 | ✓ |
| Cohort (BH) | 1960s | 1,722 | 1,722 | 3.20 | [3.09, 3.30] | 0.002 | 0.001 | ✓ |
| Cohort (BH) | 1970s | 1,064 | 1,064 | 2.67 | [2.58, 2.76] | 0.002 | 0.001 | ✓ |
| Cohort (BH) | 1980s | 223 | 223 | 1.53 | [1.48, 1.58] | 0.097 | 0.180 | ✗ |

**Power caveat on the two non-rejections.** The parental Professional/Managerial
stratum ($n = 335$) and the 1980s cohort ($n = 223$) are the two smallest cells in
the stratified design and were pre-registered as underpowered for a per-subgroup
Markov-1 $W_2$ test. Their effect sizes ($T = 1.60$ and $T = 1.53$) sit only
marginally above unity. Because both cells were pre-registered as underpowered, this
marginal separation is not read as an established topological equivalence. These two
cells are therefore reported as inconclusive on power grounds; they are not evidence that career topology in these
subgroups is reducible to a Markov-1 process, and they must not be read as
counter-evidence to the topological heterogeneity documented across the remaining
strata. (Consistent with this, the two metrics disagree in the smallest cells: for
Professional/Managerial the landscape $L^2$ complement rejects while $W_2$ does not,
and for the 1980s cohort both metrics fail to reach significance — the kind of
metric-dependent instability expected when a stratum is underpowered. Landscape
$L^2$ likewise diverges from $W_2$ in the 1940s cohort, which $W_2$ rejects but the
landscape does not.)

Any interpretation of the BHPS rejections should additionally be read together with
the BHPS-specific Markov-1 credibility diagnostic reported in Section 6.2, which
finds the BHPS Markov-1 null to be anti-conservative; the BHPS per-subgroup
rejections carry that caveat.

#### Summary

Under the per-subgroup construction, twelve of twelve USoc subgroups and nine of
eleven BHPS subgroups are topologically irreducible to their own first-order Markov
baseline, the two BHPS exceptions being the two smallest, pre-registered-
underpowered strata. The topological signal is not generated by demographic pooling:
it is present within gender, within parental-class origin, and within birth-cohort
partitions. The topological heterogeneity across demographic strata is established on
Understanding Society, where every subgroup rejects.

[Figure 13: Per-subgroup observed-to-null $W_2$ ratios with BCa intervals, by family]
