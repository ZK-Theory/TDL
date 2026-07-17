## §3.3 — Effect-size definitions

For each null type the post-audit pipeline stores the array
$\{W_2(D_{\text{obs}}, D^{(j)}_{\text{null}})\}_{j = 1}^{B}$ of obs-null
distances and the summary statistics
$(\bar W_{\text{null,null}},\, \mathrm{sd}(W_{\text{null,null}}),\, N_{\text{pairs}})$
of the null-null reference distribution. From these we report two effect-size
summaries alongside the permutation $p$-value.

The *permutation effect size*

$$
d_{\text{perm}} \;=\; \frac{\bar W_{\text{obs,null}} - \bar W_{\text{null,null}}}
                                    {\mathrm{sd}(W_{\text{null,null}})}
$$

expresses how many null-null standard deviations separate the observed-vs-null
mean distance from its null reference. Values above $\approx 2$ correspond to
diagram configurations that sit outside the bulk of the null ensemble, in
analogy with conventional $z$-style cut-offs.

The *Wasserstein ratio*

$$
\hat\rho \;=\; \frac{\bar W_{\text{obs,null}}}{\bar W_{\text{null,null}}}
$$

is a scale-free version of the same comparison: $\hat\rho = 1$ is the value
expected under exchangeability of $D_{\text{obs}}$ with the null ensemble,
and $\hat\rho > 1$ indicates an observed diagram more dissimilar from null
diagrams than null diagrams are from each other. A delta-method 95%
confidence interval for $\hat\rho$ is obtained from the stored arrays via

$$
\mathrm{Var}(\hat\rho) \;\approx\;
\frac{\mathrm{Var}(\bar W_{\text{obs,null}})}{\bar W_{\text{null,null}}^{\,2}}
\;+\;
\frac{\bar W_{\text{obs,null}}^{\,2} \, \mathrm{Var}(\bar W_{\text{null,null}})}
     {\bar W_{\text{null,null}}^{\,4}},
$$

with $\mathrm{Var}(\bar W_{\text{obs,null}}) = \mathrm{sd}(W_{\text{obs,null}})^2 / B$
and $\mathrm{Var}(\bar W_{\text{null,null}}) = \mathrm{sd}(W_{\text{null,null}})^2 / N_{\text{pairs}}$.
A CI that excludes $\hat\rho = 1$ provides finite-sample evidence that the
observed diagram sits outside the null ensemble at the chosen confidence
level; for the post-audit runs reported in §4.3 we report this CI alongside
$d_{\text{perm}}$ and the empirical $p$-value because the $p$-value resolution
is limited to multiples of $1/N_{\text{pairs}} = 0.002$ and ties out at $0.000$
for several rungs.

The BCa-bootstrap CI on $\hat\rho$ is reported as a sensitivity check in
Supplement §S1.

*Effect-size statistics vs. $p$-value formula.* The $d_{\text{perm}}$
and $\hat\rho$ columns are derived from the stored obs-null and null-null
$W_2$ *distance arrays* and are therefore unaffected by the choice of
$p$-value formula (Edgington vs. empirical fraction; cf. §S0.8). The
$p$-values reported alongside them use the empirical-fraction form. Above
the $1 / (1 + N_{\text{pairs}}) \approx 0.002$ resolution floor the two
formulas agree to three decimals; only the floor itself changes.

## §4.3 Table 1

Table 1 reports the Markov-memory ladder under the columns *Null model*,
*Test statistic*, *Dim*, $\bar W_{\text{obs,null}}$,
$\bar W_{\text{null,null}}$, $\hat\rho$, *95% delta-method CI*,
$d_{\text{perm}}$, and *p*. No binary "rejected" column is reported: the CI
and $d_{\text{perm}}$ make the substantive verdict explicit without
dichotomising it.

The USoc rows (L = 5{,}000 landmarks, B = 100 permutations,
$N_{\text{pairs}} = 500$; post-audit canonical) read:

| Null model | Test stat | Dim | $\bar W_{\text{obs,null}}$ | $\bar W_{\text{null,null}}$ | $\hat\rho$ | 95% delta CI | $d_{\text{perm}}$ | $p$ |
|---|---|---|---|---|---|---|---|---|
| Label shuffle (control) | $W_2$ | $H_0$ | $0.470$ | $0.490$ | $0.96$ | $[0.92,\, 1.00]$ | $-0.17$ | $0.526$ |
| Label shuffle (control) | $W_2$ | $H_1$ | $263.581$ | $263.713$ | $1.00$ | $[1.00,\, 1.00]$ | $-0.01$ | $0.620$ |
| Cohort shuffle | $W_2$ | $H_0$ | $0.466$ | $0.495$ | $0.94$ | $[0.91,\, 0.98]$ | $-0.29$ | $0.580$ |
| Cohort shuffle | $W_2$ | $H_1$ | $263.622$ | $263.531$ | $1.00$ | $[1.00,\, 1.00]$ | $0.01$ | $0.574$ |
| Order shuffle | $W_2$ | $H_0$ | $15.458$ | $5.816$ | $2.66$ | $[2.59,\, 2.73]$ | $6.35$ | $0.000$ |
| Order shuffle | $W_2$ | $H_1$ | $265.621$ | $267.638$ | $0.99$ | $[0.99,\, 1.00]$ | $-0.49$ | $0.722$ |
| Markov-1 | $W_2$ | $H_0$ | $28.122$ | $6.882$ | $4.09$ | $[3.96,\, 4.22]$ | $10.30$ | $0.000$ |
| Markov-1 | $W_2$ | $H_1$ | $247.582$ | $229.768$ | $1.08$ | $[1.07,\, 1.08]$ | $3.37$ | $0.000$ |
| Stratified Markov-1 | $W_2$ | $H_0$ | $37.402$ | $7.966$ | $4.69$ | $[4.56,\, 4.83]$ | $12.58$ | $0.000$ |
| Stratified Markov-1 | $W_2$ | $H_1$ | $285.024$ | $306.659$ | $0.93$ | $[0.93,\, 0.93]$ | $-2.99$ | $1.000$ |
| Markov-2 | $W_2$ | $H_0$ | $10.914$ | $7.401$ | $1.48$ | $[1.40,\, 1.55]$ | $1.53$ | $0.080$ |
| Markov-2 | $W_2$ | $H_1$ | $254.344$ | $242.945$ | $1.05$ | $[1.04,\, 1.05]$ | $1.96$ | $0.030$ |

## §4.3 Table 1 — caption

> Table 1 reports the post-audit Wasserstein-$W_2$ summary for the USoc
> trajectory diagram against each null model at L = 5{,}000 landmarks and
> B = 100 permutations. Label-shuffle and cohort-shuffle controls return
> $\hat\rho$ close to $1$ with $d_{\text{perm}}$ within $\pm 1$ at both
> dimensions, as expected under exchangeability. The order-shuffle and
> Markov-1 nulls return $H_0$ effect sizes of $d_{\text{perm}} = 6.35$ and
> $10.30$ respectively, with delta-method 95% CIs on $\hat\rho$ that
> exclude $\hat\rho = 1$ by an order of magnitude
> ($[2.59,\, 2.73]$ and $[3.96,\, 4.22]$); the stratified Markov-1 null
> tightens this further to $\hat\rho = 4.69$, $[4.56,\, 4.83]$. The
> Markov-2 null pulls the $H_0$ effect size to $d_{\text{perm}} = 1.53$
> with $\hat\rho = 1.48$, $[1.40,\, 1.55]$ at $p = 0.080$, against an
> $H_1$ effect size of $1.96$ at $p = 0.030$. The substantive arbitration
> between these summaries — including the relative weight given to the
> $\hat\rho$ CI vs. the $p$-value at $B = 100$ — is reported in the
> Markov-memory discussion in §4.3.

## Supplement §S1 — BHPS post-audit effect-size table

The BHPS post-audit run at L = 5{,}000 landmarks uses B = 100 permutations
rather than the pre-registered headline budget of B = 1{,}000. It is
therefore reported in Supplement §S1 rather than in the main Table 1, with
the explicit caveat that the obs-null array length matches the post-audit
canonical and not the pre-registered headline.

| Null model | Test stat | Dim | $\bar W_{\text{obs,null}}$ | $\bar W_{\text{null,null}}$ | $\hat\rho$ | 95% delta CI | $d_{\text{perm}}$ | $p$ |
|---|---|---|---|---|---|---|---|---|
| Label shuffle (control) | $W_2$ | $H_0$ | $1.196$ | $1.519$ | $0.79$ | $[0.59,\, 0.99]$ | $-0.22$ | $0.512$ |
| Label shuffle (control) | $W_2$ | $H_1$ | $203.674$ | $203.128$ | $1.00$ | $[1.00,\, 1.01]$ | $0.04$ | $0.558$ |
| Cohort shuffle | $W_2$ | $H_0$ | $1.005$ | $1.514$ | $0.66$ | $[0.49,\, 0.84]$ | $-0.35$ | $0.554$ |
| Cohort shuffle | $W_2$ | $H_1$ | $203.387$ | $200.674$ | $1.01$ | $[1.00,\, 1.03]$ | $0.09$ | $0.634$ |
| Order shuffle | $W_2$ | $H_0$ | $13.701$ | $5.157$ | $2.66$ | $[2.56,\, 2.75]$ | $5.84$ | $0.000$ |
| Order shuffle | $W_2$ | $H_1$ | $209.037$ | $210.667$ | $0.99$ | $[0.99,\, 1.00]$ | $-0.42$ | $0.666$ |
| Markov-1 | $W_2$ | $H_0$ | $34.674$ | $6.882$ | $5.04$ | $[4.87,\, 5.21]$ | $11.44$ | $0.000$ |
| Markov-1 | $W_2$ | $H_1$ | $201.851$ | $211.333$ | $0.96$ | $[0.95,\, 0.96]$ | $-2.00$ | $0.978$ |
| Stratified Markov-1 | $W_2$ | $H_0$ | $15.131$ | $7.384$ | $2.05$ | $[1.95,\, 2.15]$ | $3.14$ | $0.000$ |
| Stratified Markov-1 | $W_2$ | $H_1$ | $224.435$ | $243.576$ | $0.92$ | $[0.92,\, 0.92]$ | $-3.46$ | $0.998$ |

The legacy L = 2{,}000 post-audit values are reported in Supplement §S4 as
the landmark-budget sensitivity benchmark.
