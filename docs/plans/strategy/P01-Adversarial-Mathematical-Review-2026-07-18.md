# Adversarial Mathematical Review of the P01-A / P01-B Methodology

**Date:** 2026-07-18
**Status:** Gate-7 intake. This is a referee-stance review of the *mathematical and
statistical soundness* of the methodology as written and as implemented. It
complements — and deliberately does not repeat — the claim-trace audit
(`P01-Claim-Trace-Audit-2026-07-17.md`, provenance and traceability) and the failure
inventory (`APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md`, process
invariants). Everything here concerns whether the methods are *right*, not whether
the numbers are *traceable*.
**Grounding.** Reviewed sources: P01-B `methods-3-1-vr-filtration.md`,
`methods-3-2-ladder-markov.md`, `methods-3-3-w2-test.md`, `methods-3-4-knee-spanning.md`;
P01-A `supplement-S0-null-specification.md`, `methods-h1-artefact-caveat.md`; and the
live implementation verified 2026-07-18 on `origin/main` (`02ebcaf` era):
`trajectory_tda/topology/permutation_nulls.py`,
`trajectory_tda/scripts/stage1/_battery_core.py`,
`trajectory_tda/scripts/run_t128_stratified_w2.py`. Findings that depend on code are
cited to lines and were read in the working tree, not inferred from documentation.
**Severity classes.** **A** — threatens the validity of a headline claim; must be
fixed or the claim re-scoped before the Gate-7 rewrite promotes it. **B** — a
referee at the target journal will raise it; needs a prepared defence, a computed
sensitivity, or a disclosed limitation. **C** — interpretive or framing exposure.
§6 records what the review found *sound*, because a fair adversarial review
certifies as well as attacks.

---

## 1. Class A — validity-threatening findings

### A1. The Markov surrogate generator contradicts the declared conditioning, and the deviation is anti-conservative (code-verified)

**The contradiction.** P01-B §3.2 declares: Level 4 surrogates are drawn
"conditional on each trajectory's observed starting state and length"; Level 5
"conditional on each trajectory's observed first two states". The implementation
(`permutation_nulls.py`) does neither:

- Markov-1 (line 303): every synthetic trajectory's first state is drawn i.i.d.
  from the **pooled empirical initial distribution** `initial_probs` — not set to
  that trajectory's observed start.
- Markov-2 (lines 347–350): the first token is drawn from `initial_probs` and the
  **second token is drawn uniformly over the nine states** (`uniform_fallback`) —
  not the observed first two states, and not even a fitted marginal.

P01-A §S0.4/§S0.6 document the code faithfully (S0 was drafted from these exact
lines and says so), so the two papers currently assert *different null models for
the same rung* — a Class-10 divergence on the central methodological object — and
P01-B's methods sentences fail invariant I3d (methods description vs implementing
function). The battery pipeline routes through this code
(`_battery_core.py` → `_single_permutation("markov", ...)`), so **every headline
Markov-1/Markov-2 result, pooled and stratified, was produced by the S0 generator,
not the §3.2 one.**

**Why it matters mathematically, not just editorially.** The order-1 deviation is
mild: the pooled empirical start marginal reproduces the observed marginal, so the
cost is variance (lost per-trajectory coupling of start state to length/cohort),
second-order. The order-2 deviation is material: a uniform second token perturbs
the bigrams at positions (0,1) and (1,2) — roughly 2/(T−1) ≈ 12–17% of each
trajectory's bigram mass at T ∈ [10, 18] — toward uniform, in a state space where
real transitions are strongly persistent. Every surrogate is perturbed in the
*same direction*, so the entire null ensemble is coherently displaced in n-gram
space relative to a faithful Markov-2 ensemble. A coherent displacement inflates
observed-to-null distances while leaving null-to-null distances (the test's
reference; see A2) largely unchanged — the null-null reference cannot see a shift
shared by all its members. The direction is therefore **anti-conservative for the
Markov-2 rung specifically**: part of any Markov-2 rejection may be the generator's
infidelity, not trajectory memory. USoc's Markov-2 rejections (p < 0.001, both
degrees) carry this confound; BHPS's H₁ non-rejection is, if anything, strengthened
by it. The exact-W₂ rebuild values in the audit record inherit the same generator.

**Remediation fork (User decision required; do not guess).**
- *(a) Fix the generator* to condition on the observed first two states (making
  §3.2 true as written) and recompute the Markov-2 rung. This is the right answer
  for a JRSS-B methods paper — but it invalidates comparability with the certified
  α=1 landscape cells (H6 ruling, PR #129), which were computed under the current
  generator, and it re-widens the parked W₂-only recompute back into a full
  dual-metric recompute under the corrected null. The 2026-07-17 recompute
  pre-registration locks the *existing* generator's parameters and seeds, so an
  amendment is required under either fork.
- *(b) Keep the generator and correct the prose* (§3.2 rewritten to match S0),
  disclosing the second-token deviation as a limitation with a computed magnitude
  diagnostic: compare surrogate vs observed bigram frequencies at positions (0,1)
  and (1,2), and report the displacement's share of the observed-to-null distance.
  Cheaper, honest, but leaves a methods paper defending a null it knows is
  unfaithful at two tokens per trajectory.

Recommendation: (a), costed and scheduled at Gate-7 intake; (b) is acceptable only
as an interim disclosure if compute cannot be scheduled. Either way §3.2 and §S0
must stop asserting different nulls.

### A2. The implemented p-value is not the documented test — and the documented test is not implemented anywhere

**What is implemented.** `_battery_core.py` lines 408–411 (and identically for the
landscape metric, lines 428–431):

```
r  = #{ null-null pair distances  ≥  mean of the B obs-null distances }
p  = (r + 1) / (N_pairs + 1)
```

The observed statistic is a **mean over B distances**; the reference distribution
is the set of **individual null-null pair distances**. P01-A §S0.8 documents this
form. The stratified (T1.28) runner consumes the same cell fields
(`run_t128_stratified_w2.py` lines 406–430), so **all current headline p-values —
pooled rungs, stratified 4b, the Markov-2 α-sweep cells, and the landscape
complement including the H6-certified cells — use this construction.**

**What is documented in P01-B §3.3.** A different and better test: for each null
draw j, form the leave-one-out ratio T⁽ʲ⁾ (draw j against the rest, over the
null-null baseline) and compare the observed ratio T to the B reference ratios.
**No production code path implements this.** The methods paper's central test
description describes an unimplemented procedure — the most consequential
methods-vs-implementation divergence in either paper, strictly larger than the
already-logged denominator-token contradiction.

**Why the implemented form is miscalibrated.** Under H₀ (observed exchangeable
with surrogates), the mean-of-B-distances statistic concentrates: its conditional
expectation given the observed draw has the same mean as an individual pair
distance (E over obs and null of W equals E of a null-null pair) but strictly
smaller dispersion. Comparing a concentrated statistic against the quantiles of a
dispersed reference means null p-values pile up near the mid-tail probability
P(pair ≥ E[mean]) ≈ 0.4–0.6 and essentially never take small values — the test is
severely conservative, its p-values are not uniform under H₀, and its power
behaviour is uncalibrated. (It remains superuniform, hence "valid" in the weak
sense, under a tail-dominance condition that generically holds; it is not a
permutation test in any standard sense.) Note the composition with A1: the
generator's coherent displacement inflates the mean-of-distances numerator without
touching the pair-distance reference — the two defects push in opposite
directions on different axes (A2 deflates size; A1 inflates the statistic), and
nothing currently quantifies the net.

**Remediation.** Adopt exactly one construction as a registry object (I10a):
recommend §3.3's LOO-ratio form, which is the standard surrogate-data test
(observed plays the role of one more draw; its reference distribution is
calibrated by construction, up to A3). Two cost observations that make this
cheaper than it looks: (i) the per-cell JSONs retain the full
`obs_null_distribution` arrays and null-null distances, so the LOO-ratio p-values
for W₂ are **recomputable from stored distances without re-running any persistent
homology** wherever per-pair arrays were retained (the retention mandate exists
precisely for this); (ii) where only summary scalars survive, the cell joins the
recompute queue already scoped at Gate 7. The §3.3 subtlety to fix while adopting
it: the fixed 500-pair null-null subsample is shared across all T⁽ʲ⁾, inducing
dependence between reference ratios — use all pairs or draw independent subsamples
per j, and say which.

### A3. Every "permutation p-value" at the Markov rungs is a parametric-bootstrap p-value, and the calibration analysis the paper cites in its own defence does not exist

Nothing is permuted at Levels 4, 4b, or 5: surrogates are draws from a transition
matrix **fitted on the observed data** (plug-in parametric bootstrap). The
observed trajectories are used twice — to fit P̂ and as the test object — so
exchangeability of the observed draw with surrogate draws fails at the order of
the estimation error even when H₀ is exactly true, with a sign that is not
determined (model misfit inflates observed-to-null distances; shrinkage of P̂
toward the data deflates them). §3.3 concedes this ("its type-I-error behavior is
assessed through the double-null calibration analysis") — but that analysis is
T1.41, which is **parked and has never run**: the paper cites a nonexistent
analysis as its validity warrant. Level 3 (order shuffle) is, by contrast, a
genuine permutation test — exact conditional on within-trajectory state multisets
— and should be labelled as the only exact rung.

**Remediation.** (i) Rename: "surrogate-data p-value" or "Monte-Carlo
parametric-bootstrap p-value" for rungs 4–5 throughout both papers (RSS referees
are precisely the audience that will not forgive "permutation" here; CONVENTIONS'
"permutation nulls are the standard" wording needs the same qualification).
(ii) Run the double-null calibration *before* any rung-4/5 rejection is promoted
by the Gate-7 rewrite: generate data from a *known* Markov-k chain, run the full
pipeline (fit → surrogates → embed → landmark → diagram → test), and check the
p-value distribution — this is exactly the battery's P2 harness
(`shared/math_invariants.py::double_null_calibration`, PR #131) at pipeline scale,
and exactly T1.41's pre-registered design. It also empirically measures A2's
conservatism and A1's displacement in one experiment — one calibration run
answers three findings.

### A4. Per-cloud filtration truncation couples the statistic to dispersion through the filtration window itself

§3.1 caps the witness filtration at
α_max = min(10, Q95 of squared witness-to-nearest-landmark distance), **computed
per point cloud** — the observed cloud and every surrogate get different
truncation thresholds. Diagrams computed under different filtration windows are
then compared by W₂ as if they shared one. Any dispersion difference between
observed and null clouds moves the truncation point, censoring different feature
sets — so part of any observed-to-null distance can be a truncation artifact
rather than topology. The paper's own H₂ investigation identified cloud dispersion
as a rejection driver and, notably, found the residual H₂ signal collapses under
diameter normalization — the per-cloud cap is a mechanism by which dispersion
enters *every* homological degree, including the headline H₀/H₁. §3.1's candour
("we do not claim a validated stability range for this truncation") is not a
defence a JRSS-B referee will accept for the primary construction.

**Remediation.** The pinned-threshold machinery already exists (it was built for
the H₂ diagnostics). Pin one α_max per analysis cell — computed from the observed
cloud, or the pooled observed+surrogate ensemble — for the observed cloud *and*
all B surrogates; recompute one headline cell as a sensitivity triage before
deciding whether the full grid needs it. If pinning changes conclusions, the
change is a finding, not an inconvenience.

---

## 2. Class B — referee-anticipation findings

### B1. Frozen PCA loadings: right choice, wrong framing

S0.7's frozen-loadings policy is defensible — and (see C1) is actually the
paper's best defence on H₁ interpretability — but the hypothesis actually tested
is *conditional on the observed-fit embedding map*, and the observed cloud is
special with respect to that map (the loadings maximize observed variance, not
surrogate variance), so exchangeability is broken by construction even under a
true H₀. The bias direction is not obvious and its magnitude is plausibly small at
pooled-sample size; but "plausibly small" is an assertion. Remediation: state H₀
conditionally everywhere ("the embedded geometry under the fixed observed-fit
embedding is consistent with..."), and quantify once: a split-fit sensitivity
(loadings fitted on half the trajectories, test run on the other half) on one
headline cell bounds the double-use effect empirically.

### B2. What a rejection licenses

A rung-k rejection establishes: *the observed embedded, landmarked,
truncation-censored diagram differs from those of surrogates drawn from the
fitted order-k chain under the frozen embedding.* Substantive claims of the form
"career trajectories carry memory beyond order k" require every link of the chain
(dynamics → n-gram frequencies → PCA-20 → landmark/witness → truncated diagram →
distance) to transmit only dynamical differences — and A1, A4, and B1 are three
documented artifact channels in that chain. P01-B (stat.ME) should state the
operational estimand exactly; P01-A may carry the substantive interpretation with
its existing caveat apparatus. This is a wording discipline, not new computation —
but it is the difference between a defensible methods paper and a referee's
counterexample factory.

### B3. Landscape-lane parameters need pinning and one free diagnostic

k_max = 5 layers on diagrams with thousands of features is a declared truncation;
fine — but (i) the evaluation grid's range must be pinned per analysis cell and
stated (a data-dependent grid re-introduces A4 for the landscape metric);
(ii) the claimed "1-Lipschitz w.r.t. bottleneck" stability transfers to L² only
with a support-measure factor — cite the precise statement for the L² claim or
drop the stability appeal to the informal register; (iii) the battery's exact norm
identity (Σₖ‖λₖ‖² closed form) yields a free, per-cell diagnostic of how much
landscape content the k ≤ 5 truncation discards — report it once; if the top-5
share is small, the metric's sensitivity claims need re-examination.

### B4. Dependence-blind uncertainty summaries

Three instances, all disclosed or partially disclosed, none yet resolved: the BCa
intervals resample dependent distance arrays i.i.d. (§3.3 says "descriptive" —
then the tables must not present them alongside inferential p-values without the
qualifier); the 500-pair null-null subsample shares diagrams across pairs
(underestimates reference dispersion; affects both s_null,null and A2's reference
quantiles); and d_perm's denominator is the sd of *pair distances*, which scales
with diagram size and landmark count — cross-cell d_perm league tables (12/12,
9/11 subgroup counts) implicitly compare incommensurable units. Remediation:
paired/clustered bootstrap (resample surrogate indices, recompute all means
jointly) is a one-day implementation against retained arrays; add a d_perm
comparability caution or size-adjust.

### B5. Multiplicity architecture is per-family, but the headline claims aggregate

BH within family × metric is correctly specified and its positive-dependence
caveat is honestly stated (§3.2). But the paper's headline claims aggregate across
families and metrics ("12/12 subgroups reject") with no stated error rate for the
aggregate; and the dual-metric rule (is a cell a "rejection" when both metrics
reject, or either?) determines the effective level of every such count —
conjunction is size-conservative, disjunction is not, and W₂/landscape statistics
on the same diagrams are strongly dependent so "both reject" is far less than two
independent confirmations. State the cell-level decision rule once, in the
registry, and derive the aggregate claim's error property from it — or demote
aggregate counts to description.

### B6. Knee/ε* and the spanning decomposition (P01-B §3.4.2)

The reviewer-driven redesign (windowed AUC headline, matched-W₂ scale-free
companion, mandatory identification check with balance diagnostics and two
adjustment designs) is the strongest part of either paper. Residual attack
surface: (i) the four degenerate-year exclusions (2003, 2005, 2011, 2019 — one of
which is the BHPS→USoc seam) need a statement that exclusion was blind to
downstream statistics; (ii) ε_lo = 0.1115 is stated to four significant figures
with no derivation — a referee reads unexplained precision as tuning; derive it or
round it and show insensitivity; (iii) `np.gradient`-based discrete curvature is
noise-sensitive — the degeneracy flags mitigate, but a one-line smoothing
sensitivity (window ±1 grid step) closes the question; (iv) keep the
constant-by-construction matched-W₂ out of cross-ε* robustness claims (already
struck once; the rewrite must not resurrect it).

### B7. Survey design: attrition, weights, and the population the topology describes

The pipeline uses no survey weights, and trajectory windows of T ≥ 10 waves select
long-tenure panel members. Attrition in BHPS/UKHLS is non-random and plausibly
mobility-correlated (movers, job-changers, and the precariously employed attrit
more), so the observed cloud under-represents exactly the volatile careers the
topology is meant to characterize — a selection effect on the *shape* of the data,
not just its size. JRSS-A will demand: characterize who survives the window
requirement (a covariate table against the full frame); state the direction-of-
selection argument; and either a weight-aware sensitivity (resample trajectories
by design weight before embedding — crude but responsive) or an explicit scope
statement ("the topology of sustained panel participation"). §3.4.2's
identification machinery covers the era-comparison frame question, not this
population question.

---

## 3. Class C — interpretive exposures

### C1. H₁ under n-gram + PCA: the horseshoe objection, and the defence the paper already owns but has not written

Compositional frequency vectors (n-gram frequencies live on a simplex) projected
by PCA generate curved, arch-like structures from purely gradient-like variation
(the Guttman/horseshoe effect — the reason detrended correspondence analysis
exists). Loops in the embedded cloud therefore need not correspond to any cyclical
career dynamic; an ordination referee will raise this within a page of seeing
"H₁" and "PCA" together. The existing caveat (short-bar features; substantive H₁
analysis is the null comparison) points the right way but understates the
paper's best argument: **because surrogates are re-embedded under the same frozen
loadings, the horseshoe channel is matched between observed and null clouds — the
null comparison differences out the artifact to the extent the artifact depends
on the shared compositional geometry rather than the dynamics.** Write that
argument explicitly. Note the design coupling: B1's refit-per-draw alternative
would *weaken* this defence — a substantive reason (beyond S0.7's variance
argument) to keep frozen loadings and frame H₀ conditionally.

### C2. Vocabulary discipline

"Permutation" for rungs 4–5 (see A3), "null model" vs "surrogate process",
"exchangeable" where the honest term is "approximately exchangeable up to
estimation error" — each term is load-bearing for an RSS audience. One
terminology pass, driven from the registry definitions, after A2/A3 land.

### C3. α-sweep motivation scope

§3.2's α-sensitivity sentence ("rejection direction stable across α ∈ {0, 0.5, 1,
5}") is sourced from the solver-uncertifiable W₂ sweep for its W₂ half (H6 ruling:
those fields are do-not-cite); the sentence survives only on its landscape half
until the W₂-only recompute lands. Re-scope the sentence now or gate it on the
recompute — do not let it ride into the rewrite attached to dead evidence.

---

## 4. Composition: how the A-findings interact

The three statistical A-findings do not simply add. A2 (mean-vs-pairs reference)
makes the test conservative under an ideal null; A1 (generator displacement) and
A3 (plug-in fitting) shift the statistic and reference in ways A2's conservatism
partially masks. A rejection under the current stack therefore reflects an unknown
net of: true signal + generator displacement − reference miscalibration ±
estimation error. The clean resolution is not to reason about the net — it is to
(1) fix the generator (A1a), (2) adopt the calibrated LOO-ratio test (A2), and
(3) certify the assembled pipeline once by double-null calibration (A3/T1.41,
P2 harness). After those three, the battery's screens (PR #131) keep it certified.

## 5. Priority map for Gate-7 intake

| Finding | Blocks | Action | Cost signal |
|---|---|---|---|
| A1 | Markov-2 rung claims (P01-B §4.2, Table 2); recompute pre-reg scope | User fork (a)/(b); §3.2↔S0 reconciliation either way | (a) full Markov-2 recompute; (b) prose + diagnostic |
| A2 | Every headline p-value's documentation; P01-A §S0.8-sourced values | Registry-lock one construction; recompute LOO-ratio p from retained arrays | Low where arrays retained; no PH re-runs needed |
| A3 | The validity warrant of all rung-4/5 p-values | Rename; run T1.41 double-null before promotion | One calibration campaign (answers A1/A2/A3 jointly) |
| A4 | All witness-complex cells | Pin α_max per cell; one-cell sensitivity triage first | Cheap triage; scope decided by its outcome |
| B1–B7 | Referee survival | Per-finding one-shot sensitivities + wording | Mostly days, not weeks |
| C1–C3 | Interpretation | Prose; one terminology pass | Prose only |

## 6. What survives review

Recorded so the rewrite preserves them deliberately: the ladder architecture
(nested nulls of increasing fidelity, with the honest Level-3-is-exact
distinction available); the trajectory as the surrogate unit (§3.3's
exchangeability paragraph identifies the right granularity and correctly rejects
transition-level scrambling); one-to-one length preservation; the dual-metric
mandate (once B5's decision rule is stated); the frozen-loadings choice *as a
conditional design with the C1 artifact-matching defence*; the H₂ dispersion
investigation (a model of self-critique — it found and characterized its own
artifact); the §3.4.2 identification check (balance diagnostics + two adjustment
designs as a mandatory method component is above the field's standard); the
retired-nulls disclosure; the retained per-pair distance arrays (which make A2's
fix cheap); and the seeds/provenance discipline of the post-hardening era. The
skeleton is sound. The findings above are about making the inferential joints
match the skeleton's quality.
