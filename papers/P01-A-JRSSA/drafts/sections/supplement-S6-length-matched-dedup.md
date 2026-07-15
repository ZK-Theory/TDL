# Supplement §S6 — External-Indexing Deduplication for the Length-Matched Cells

The length-matched robustness arm (§4.3) compares the BHPS sample against
USoc under two horizon-matching strategies — truncation to USoc's mean
observation window, and restriction to trajectories of at least thirteen
waves — to test whether the BHPS–USoc $H_1$ signal is an artefact of
differing observation lengths rather than a genuine difference in trajectory
geometry. Both strategies apply a preprocessing step that the full-length
headline does not: external-indexing deduplication of the observed maxmin
landmark sample. We document the step here, and report how sensitive the
$H_1$ verdict is to it.

**Why the observed sample is deduplicated and the surrogates are not.**
Horizon-matching clips trajectories before re-embedding, which drives a small
fraction of the observed landmark points to within floating-point tolerance
($\tau_{\text{float}} = 10^{-10}$) of one another: in the truncate cell, 139
of the 5,000 observed maxmin landmarks fall within tolerance of another
retained point, leaving 4,861 numerically distinct landmarks. This
near-duplicate structure is a property of the observed embedding. The
Markov-1 surrogates do not reproduce it, because the synthetic state
sequences are sampled from a transition matrix rather than clipped from real
trajectories. The observed sample and its nulls therefore differ in a respect
that has nothing to do with the trajectory geometry under test, and we
correct that difference on the side where it arises: external indexing is
applied to the observed maxmin sample alone, and the null permutation budget
$n_{\text{perm}}$ is left unchanged. The justification for the step is a
property of the representation; we claim nothing inferential for it.

**The $H_1$ verdict does not depend on the deduplication.** Re-running the
truncate cell without the step — same optimal-transport $W_2$ solver, frozen
loadings, null bank, pair sample, and seed — leaves the test where it stands
with it. Without deduplication the mean observed-to-null distance is $6.61$
against a mean null-to-null distance of $3.55$, a signal-to-noise ratio of
$1.860$; with deduplication the corresponding figures are $6.63$, $3.55$, and
$1.866$. Both arms reject the $H_1$ $W_2$ null at the Monte-Carlo resolution
floor $1/(1 + N_{\text{pairs}})$ with $N_{\text{pairs}} = 1{,}000$. The two
arms are statistically indistinguishable, which is the informative statement
about the step: removing 139 near-duplicate landmarks changes the observed
$H_1$ diagram by two features ($3{,}144 \to 3{,}146$), the $W_2$ distance
between the two observed diagrams is $0.545$, and Outcome A — that the
BHPS–USoc $H_1$ signal is not a length-of-observation artefact — holds whether
or not the step is applied. The deduplication is a defensible treatment of a
known property of the observed sample, not a condition on the conclusion.

**How the step was arrived at.** The deduplication was originally introduced
to remedy an apparent non-separation in the un-deduplicated truncate cell.
That non-separation was subsequently found to be an artefact of the distance
implementation rather than a property of the data: the $W_2$ computation in
use at the time fell back to a greedy persistence-rank matching instead of
solving the optimal transport problem, which inflates observed-to-null and
null-to-null distances alike by a factor of approximately thirty and
compresses the ratio between them to $1.006$. Under the optimal-transport
solver the apparent non-separation does not arise. The step is retained on
the representational grounds set out above, and not on the inferential
grounds that first motivated it.

**Two robustness probes isolate the methodology from incidental
implementation choices.** Each probe re-runs the truncate cell under an
alternative for one implementation detail and checks that the rejection
direction survives across all four cells ($H_0$ and $H_1$, each under $W_2$
and landscape $L^2$). The first, `symmetric_dedup`, addresses the residual
cardinality mismatch that deduplication leaves between the observed sample
and its nulls: it forces the null diagrams to use $n_{\text{perm}}$ equal to
the deduplicated observed point count. The $H_0$ and $H_1$ signal-to-noise
ratios change by $-0.66\%$ and $-0.24\%$ respectively, and every cell
continues to reject. The second, `pinned_thresh`, fixes the Rips threshold to
the enclosing radius of the deduplicated observed landmark sample, removing
the auto-threshold subsampling drift; here the absolute $W_2$ magnitudes
shift because the wider fixed threshold admits more features, and the $H_0$
signal-to-noise ratio rises by $6.7\%$ (T-ratio $7.87 \to 8.40$) while the
$H_1$ ratio moves by under $1\%$. In every probe and every cell the $W_2$ and
landscape $L^2$ rejections are preserved, so the length-matched rejection is
not an artefact of either incidental implementation choice.
