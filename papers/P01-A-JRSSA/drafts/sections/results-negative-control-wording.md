<!--
Target location in v2: §4.3, the sub-paragraph that in v1 begins "This
discrepancy is not an artefact. Label shuffle serves as a negative control…"
(v1-2026-04.md line 126). The Wasserstein-specific negative-control summary
replaces v1's scalar-statistic claim "p > 0.31 under both statistics".

Evidence sources verified during drafting:
  • `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_20260502.json`
    — USoc, L = 5000 landmarks, B = 100 permutations, 500 null-null pairs.
  • `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_L5000_20260502.json`
    — BHPS, L = 5000 landmarks, B = 100 permutations, 500 null-null pairs.
  • `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json`
    — USoc, L = 2000 landmarks (legacy; referenced in Supplement §S0 only).
  • `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json`
    — BHPS, L = 2000 landmarks (legacy; referenced in Supplement §S0 only).

DEVIATION FROM TASK PROMPT (surfaced in Task Log, important_findings: true):
the Task quoted L = 2000 vault values (March 2026) showing BHPS
label-shuffle p ≈ 0.036 and cohort-shuffle p ≈ 0.034, and concluded that
BHPS is *not* a clean negative control. The current canonical L = 5000
post-audit (May 2026) shows label-shuffle p ≈ 0.51 (H₀) and 0.56 (H₁) in
BHPS — a clean negative control consistent with USoc. The text below reports
L = 5000; the L = 2000 deviation is restated as a landmark-budget sensitivity
observation in Supplement §S0 / §S4 (landmark robustness). The Manager
should review whether to invert this framing back to the L = 2000 era
reading or to retain the L = 5000 reading as canonical.

Forbidden content: no characterisation of which dimensions reject which
Markov-memory nulls — that framing is gated. The sub-paragraph stands alone
as a negative-control statement and cross-references §4.3 results elsewhere
in the section.
-->

## §4.3 negative-control sub-paragraph — replacement text

Replace the v1 sentence:

> "label shuffle produces p > 0.31 under both statistics ... confirming that
> 'specific identity of states does not drive diagram geometry when structure
> is otherwise intact'"

with:

> Under the canonical Wasserstein-$W_2$ battery at $L = 5{,}000$ landmarks
> and $B = 100$ permutations (Supplement §S0), label shuffle and cohort
> shuffle satisfy the negative-control criterion in both surveys: USoc
> returns $\hat p_{H_0} = 0.53$ and $\hat p_{H_1} = 0.62$ under label shuffle
> and $\hat p_{H_0} = 0.58$ and $\hat p_{H_1} = 0.57$ under cohort shuffle;
> BHPS returns $\hat p_{H_0} = 0.51$ and $\hat p_{H_1} = 0.56$ under label
> shuffle and $\hat p_{H_0} = 0.55$ and $\hat p_{H_1} = 0.63$ under cohort
> shuffle. All eight tests sit close to the $\hat p \approx 0.5$ value
> expected when the observed diagram is exchangeable with the null
> ensemble, confirming that the specific identity of states and the cohort
> bin assignment do not drive diagram geometry when the within-trajectory
> structure is otherwise intact. The corresponding total-persistence
> label-shuffle $p$-values (USoc $p > 0.31$ under both dimensions) are
> reported in the supplement; the scalar-statistic and $W_2$ summaries
> agree on the direction of the negative-control assessment, though they
> differ in calibration as expected.

## Landmark-budget sensitivity note for Supplement §S0 / §S4

> A legacy run at $L = 2{,}000$ landmarks (March 2026) returned BHPS
> label-shuffle $\hat p_{H_0} = 0.036$ and cohort-shuffle $\hat p_{H_0} =
> 0.034$, outside the negative-control range. The discrepancy is resolved at
> $L = 5{,}000$ landmarks (May 2026) and is consistent with the established
> low-landmark sensitivity of permutation $p$-values on $W_2$ diagram
> distances (Robinson & Turner, 2017, §4) and with the landmark-robustness
> grid reported in Supplement §S4. The canonical reading used throughout the
> main text is the $L = 5{,}000$ post-audit; the $L = 2{,}000$ run is
> retained as the landmark-sensitivity reference only.
