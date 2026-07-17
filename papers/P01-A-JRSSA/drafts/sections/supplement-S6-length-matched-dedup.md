<!--
Target location in v2: Supplement, robustness block — follows §S4 (landmark
count robustness) and §S5 (UMAP sensitivity) in the v1-2026-04.md outline
(lines 397-405). Working number §S6; final §-number to be assigned at v2
assembly (note §S8 foo-transparency already exists as a separate section
file). Applies equally to the P01-B headline cells — cross-reference from
P01-B rather than duplicating.

Closes the P01-A _project.md open item "SI methodological-disclosure
paragraph for the dedup amendment" (lines 143-152). Drafted, pending User
per-section review; not yet marked complete.

Evidence sources verified during drafting (all committed on main):
  • results/trajectory_tda_integration/stage1/dedup_amendment_comparison_2026-06-01.json
      — effect_summaries (truncate_no_dedup vs truncate_dedup) and
        probe_comparison (CORRECTED figures); this is the 2026-06-01
        re-build, NOT the 2026-05-31 build whose disclosure-draft field
        carried the stale "<1% in every cell" claim.
  • results/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_frozen_2026-05-30.json
        (production), and the probe-symmetric-dedup / probe-pinned-thresh
        counterparts at 2026-05-30 / 2026-05-31.
  • Vault [DECISION] 2026-05-30 (external-indexing dedup methodology lock,
    formula contract length-matched-dedup-via-n-perm) and 2026-05-31
    (Pre-reg #5 redo Outcome A lock); CONVENTIONS external-indexing-dedup
    always-rule.

CORRECTION CARRIED (do not regress): the dedup-disclosure draft embedded in
the 2026-05-31 comparison JSON stated "<1% S/N drift across all four cells".
CodeRabbit (PR #28) showed this was false for the pinned-thresh H0 cell,
which drifts +6.7% (T-ratio 7.87 -> 8.40); fixed in commit cd7b574, corrected
artefact dedup_amendment_comparison_2026-06-01.json. The text below uses the
corrected figures. The substantive claim — rejection preserved in every cell,
Outcome A unaffected — is independent of the drift magnitude.

Forbidden content (verified absent): no horizon-vs-era attribution (settled
separately by the 2026-05-31 Outcome A lock); this section specifies the
dedup methodology and defends the H1 W2 flip, it does not re-argue the
cross-cohort interpretation.
-->

# Supplement §S6 — External-Indexing Deduplication for the Length-Matched Cells

The length-matched robustness arm (§4.3) compares the BHPS sample against
USoc under two horizon-matching strategies — truncation to USoc's mean
observation window, and restriction to trajectories of at least thirteen
waves — to test whether the BHPS–USoc $H_1$ signal is an artefact of
differing observation lengths rather than a genuine difference in trajectory
geometry. Both strategies require an additional preprocessing step that the
full-length headline does not: external-indexing deduplication of the
observed maxmin landmark sample, locked under the formula contract
`length-matched-dedup-via-n-perm`. We document the step here because it is
load-bearing for the $H_1$ verdict and because, without it, the $W_2$
statistic is corrupted in a way that exactly masks the signal.

**Why the observed sample needs deduplication and the nulls do not.**
Horizon-matching clips trajectories before re-embedding, which drives a small
fraction of the observed landmark points to within floating-point tolerance
($\tau_{\text{float}} = 10^{-10}$) of one another. These numerical
near-duplicates enter the Vietoris–Rips persistence diagram
$D_1^{\mathrm{obs}}$ as phantom loops born and dying at near-zero filtration
scale — approximately 139 spurious $H_1$ features in the truncate cell. The
Markov-1 surrogates that generate $D_1^{\mathrm{null}}$ do not reproduce this
near-duplicate structure, because the synthetic state sequences are sampled
from a transition matrix rather than clipped from real trajectories, so the
correction is applied to the observed diagram alone (external indexing on the
observed maxmin sample; the null permutation budget $n_{\text{perm}}$ is left
unchanged).

**The $H_1$ $W_2$ flip is mechanistic, not a tuning choice.** Under the
no-dedup path the phantom features inflate every pairwise $W_2$ distance —
both the observed-to-null distances $W_2(D_1^{\mathrm{obs}},
D_1^{\mathrm{null}})$ and the null-to-null distances — by a roughly constant
multiplicative factor, so the test statistic cannot separate signal from
noise: the mean observed-to-null distance is $202.84$ against a mean
null-to-null distance of $201.58$ (a signal-to-noise ratio of $1.006$), and
the headline $W_2$ statistic returns $p = 0.350$, a non-rejection. Stripping
the phantoms from the observed diagram removes the shared inflation and
exposes the underlying separation: the mean observed-to-null distance falls
to $6.63$ against a mean null-to-null distance of $3.55$ (signal-to-noise
ratio $1.867$), and the $W_2$ statistic returns $p = 0.000999$, the
Monte-Carlo resolution floor $1 / (1 + N_{\text{pairs}})$ at
$N_{\text{pairs}} = 1{,}000$. The companion landscape $L^2$ statistic rejects
at the floor under both paths, so the metrics agree once the artefact is
removed. The flip is therefore a correction of a known numerical artefact in
the observed diagram, not a parameter chosen to produce a rejection: both
length-matching strategies reject $H_1$ $W_2$ at $\alpha = 0.05$ after
deduplication, which locks Outcome A (the BHPS–USoc $H_1$ signal is not a
length-of-observation artefact).

**Two robustness probes isolate the methodology from incidental
implementation choices.** Each probe re-runs the truncate cell under an
alternative for one implementation detail and checks that the rejection
direction survives across all four cells ($H_0$ and $H_1$, each under $W_2$
and landscape $L^2$). The first, `symmetric_dedup`, forces the null diagrams
to use $n_{\text{perm}}$ equal to the deduplicated observed point count,
eliminating the observed-versus-null vertex-count asymmetry that dedup
introduces; the $H_0$ and $H_1$ signal-to-noise ratios change by $-0.66\%$
and $-0.24\%$ respectively, and every cell continues to reject. The second,
`pinned_thresh`, fixes the Rips threshold to the enclosing radius of the
deduplicated observed landmark sample, eliminating the `compute_rips_ph`
auto-threshold subsampling drift; here the absolute $W_2$ magnitudes shift
because the wider fixed threshold admits more features, and the $H_0$
signal-to-noise ratio rises by $6.7\%$ (T-ratio $7.87 \to 8.40$) while the
$H_1$ ratio moves by under $1\%$. In every probe and every cell the $W_2$ and
landscape $L^2$ rejections are preserved, so Outcome A rests on the
deduplication methodology itself and not on either of the incidental
implementation choices the probes vary.
