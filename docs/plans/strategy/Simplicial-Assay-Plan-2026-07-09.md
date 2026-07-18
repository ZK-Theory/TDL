# TDL AMENDMENTS AND SPIKE SCOPE (2026-07-10 session review) — NORMATIVE

These amendments override any conflicting statement in the original text below and
fix the scope of the first worktree. The executing agent reads this section first.

## B1. Scope of this worktree (locked)

This worktree runs **Gate 0 + Phase A profiling + Spike S-Rips-1 + Spike
Witness-1 only**, on the branch `run/sparse-witness-assay-spike`. Phases B–D of
the staged design (full ε/m grids at B=1000, adaptive permutation budgets) are a
LATER APM dispatch shaped by these spike results — do not start them. The
promotion gates G1–G7 (§6 below) plus G8 (B5) are the pre-registration skeleton
for that later dispatch, not acceptance criteria for this spike.

## B2. Gate 0 (new, before any ε > 0): PH backend equivalence

The reference pipeline computes persistence with dense **ripser**; sparse Rips is
a **gudhi** feature (`RipsComplex(sparse=ε)`). Backend and sparsification effects
must not be confounded. Before any sparse run: compute H0/H1 on one USoc L=5000
reference landmark cloud with (a) the pipeline's ripser call and (b) gudhi dense
VR at the same max_edge_length and coefficient field; require matched finite
pairs (bottleneck distance ≤ 1e-9 per dimension, identical cardinalities after
applying the pipeline's infinite-feature convention). Document any convention
difference (ripser `thresh`, gudhi infinite-bar handling) in the result note.
Gate 0 failure → STOP, record `BLOCKED`, escalate; every downstream comparison
would be uninterpretable.

## B3. Cost model correction: split PH cost from W₂ cost

An H0 diagram on L landmarks has ~L−1 points regardless of how the complex is
sparsified. Exact W₂ on ~5000-point H0 diagrams is ~5–10 s/pair,
memory-bandwidth-bound, and does not parallelise on this machine (T1.6, measured;
`memory/reference_gudhi_w2_threading_gil.md`). Therefore **sparse Rips reduces
PH construction cost only; it cannot reduce the W₂ aggregation bill. Witness
complexes at m < L are the only complex-side lever on W₂ cost** (smaller vertex
set → smaller H0 diagrams). Phase A must report, per cell, separately:
complex-construction wall, PH wall, per-pair W₂ wall × pair count, peak RSS,
and diagram cardinality by dimension. The §7 prior ("sparse Rips is the best
first candidate") holds for approximation theory, not necessarily for total
cost — let the measured split decide the recommendation.

## B4. Reuse the reference; common random numbers

The reference side of every comparison already exists on disk: frozen null
diagram banks `*_frozen_B1000_L5000_seed42_2026-05-28.npz` plus committed result
JSONs (T1.2a USoc headline et al.). Do NOT recompute reference VR persistence.
Verification step (mandatory, no speculative foundations): from the T1.2a
producing script, identify (i) the USoc frozen embedding + landmark-selection
path, (ii) the null-generation entry point and its seed policy, (iii) the cache
file paths and their draw-indexing; confirm a regenerated null point cloud for
draw b reproduces the cached diagram for draw b (one-draw check per null rung)
BEFORE trusting cache reuse. Candidate complexes are then computed on the SAME
regenerated null clouds (common random numbers), so method differences are not
Monte-Carlo noise.

## B5. Gate G8 (new): dispersion-artefact check

From the T1.5 H2 investigation: a method that changes cloud/diagram dispersion
re-expresses H0 signal as apparent higher-dimensional or shifted structure.
For each candidate configuration, compare the normalized birth/death location
distributions (median-pdist normalization) of candidate vs reference diagrams;
a location shift exceeding the reference null-null variation flags the
configuration `DISPERSION_SUSPECT` even if W₂/effect-size fidelity passes.

## B6. Additional calibration cells from the Task-1 record

- **Small-n stratum cell:** BHPS `nssec/Professional-Managerial` (n=335; ~100%
  landmark fraction — the regime where approximations degrade first and where
  Task 1's power problem lives). Run reference-vs-candidate at B=100 for the
  Markov-1 rung. Cheap; high information. (Stretch: cohort/1980s n=223.)
- **Non-W₂ decision statistic (stretch goal):** the T1.9b windowed normalized
  β₀-AUC (spanning vs newcomers). If time permits, compute it on candidate
  complexes for the matched clouds and check the `newcomers_robust` direction is
  preserved. This tests decision fidelity outside the W₂ machinery entirely.
- **Known fragility precedents as regression expectations:** L=2000 BHPS
  negative-control failure; L=2500 landscape failure (T1.2c); dedup phantom-H1
  (T1.2f). Candidates must not reintroduce these at matched effective budget.
- **BHPS Markov-1 caveat:** T1.6 verdict SUSPECT (anti-conservative). USoc is the
  calibration dataset (as §9 already specifies); any BHPS Markov-1 agreement is
  secondary evidence and carries the caveat.

## B7. Compute-profile instrumentation (Phase A deliverable)

Implement the per-cell profile as a small standalone module
(`trajectory_tda/topology/compute_profile.py` + unit test): a dataclass/dict
`compute_profile` block (n_points, L, max_edge_length, simplex counts by dim,
PH wall, W₂ pair count × per-pair wall, peak RSS, diagram cardinalities by dim,
backend + version). Use it in this spike's runs; additionally write a short
adoption proposal (result-note section, not a pipeline edit) for attaching the
block to future battery result JSONs. Do NOT modify existing battery modules in
this worktree.

## B8. Repo-convention layer

Identical to amendment A5 of the GPT-Prepared spike plan (worktree/.env,
concurrency, `[EXPLORE]` commits, research-context headers + typed public APIs +
deterministic tests for new modules, scratch outputs under
`scratch/discovery_spikes/<slug>/`, nothing in `results/`, pre-registration
skeleton in the result note before compute, 2 h benchmark / 12 h escalation
guardrails). Benchmark discipline: sweep workers on >worker-count units before
projecting any grid cost; expect the W₂ stage to be serial-bound.

---

# Original plan text (context; §9 defines the two spikes)

Yes. The right framing is that your current Vietoris-Rips + Markov-null battery is not merely an expensive first attempt; it is a **reference assay**. You have a rigorously specified null ladder, stored obs-null and null-null Wasserstein arrays, effect-size summaries, and negative controls. That gives you exactly the measuring rod needed to design cheaper complexes without turning the cheaper method into an unvalidated convenience choice.

The strategic move is:

> Use the current VR/Markov-null pipeline as the calibrated reference experiment, then evaluate sparse Rips and witness-family complexes by their ability to reproduce the **inferential conclusions** of that reference, not merely by their ability to produce visually similar diagrams.

That distinction matters. Sparse Rips can be argued as an approximation to Vietoris-Rips. Witness complexes are better treated, initially, as **empirical surrogates** whose validity must be calibrated against the reference.

## 1. Freeze the current pipeline as the reference assay

Your current pipeline already has the structure needed for a benchmark.

The paper sections specify $W_2$ between persistence diagrams, using GUDHI's Wasserstein implementation with `order = 2` and `internal_p = 2`, and the inference machinery stores obs-null distances plus a null-null reference distribution. The $p$-value compares the mean observed-to-null distance against null-null distances using the Edgington form, with $N_{\text{pairs}} = 500$ giving a floor near $0.002$. 

The null ladder is also well specified: label shuffle, cohort shuffle, order shuffle, Markov-1, stratified Markov-1, and Markov-2, with trajectory lengths preserved, PCA loadings held fixed, and seed policies specified. The Markov-1 rung is raw MLE with no smoothing; Markov-2 uses Laplace smoothing at $\alpha = 1$. 

That is already stronger than many approximation studies. You are not just comparing diagrams. You are comparing diagrams inside a controlled inferential design.

So I would explicitly define the current pipeline as:

```text
Reference assay R:
  data embedding: 20D PCA unigram-bigram trajectory embedding
  complex: maxmin-landmark Vietoris-Rips, L = 5000
  dimensions: H0, H1
  nulls: label, cohort, order, Markov-1, stratified Markov-1, Markov-2
  inference: W2 obs-null vs null-null, d_perm, rho_hat, rho_hat CI, p-value
  budget: B = 1000 for headline relaunch; N_pairs = 500
```

Then every cheaper method is not “an alternative TDA analysis” at first. It is a candidate approximation to `R`.

## 2. Optimise for inferential fidelity, not diagram identity

A cheaper complex does not need to reproduce every point in every diagram. It needs to preserve the conclusions that matter.

I would use four fidelity layers.

First, **diagram-level fidelity**:

```text
W2(D_obs^cheap, D_obs^VR)
bottleneck(D_obs^cheap, D_obs^VR)
landscape L2 distance
Betti-curve correlation
top-k persistent feature overlap
```

This is useful, but not enough.

Second, **null-distribution fidelity**:

```text
mean W2(obs, null)
mean W2(null, null)
sd W2(null, null)
d_perm
rho_hat and CI
```

Your own draft already defines $d_{\text{perm}}$ and $\hat\rho$ as effect-size summaries derived from the obs-null and null-null $W_2$ arrays, independent of the precise $p$-value formula.  Those are exactly the right calibration quantities.

Third, **decision-level fidelity**:

```text
Does label shuffle remain a negative control?
Does cohort shuffle remain a negative/control or weak-control rung?
Does order shuffle reproduce the expected H0 behaviour?
Does Markov-1 reproduce the large H0 separation?
Does Markov-2 reduce the effect in the same way?
Does the H1 verdict remain directionally consistent?
```

This is where your reference assay is most valuable. The current negative-control section already says that at $L = 5000$, label and cohort shuffle sit close to exchangeability in both USoc and BHPS, while the older $L = 2000$ run gave a misleading BHPS control failure.  That is direct evidence that low-budget approximations can distort inference even when the code “works”.

Fourth, **substantive conclusion fidelity**:

```text
Does the cheaper method preserve the paper-level claim?
Does it preserve the difference between H0 connectivity structure and H1 temporal-loop structure?
Does it preserve the BHPS/USoc comparison?
Does it preserve the length-matched robustness conclusion?
```

This layer matters because your $H_1$ interpretation is already cautious: the draft notes that low-persistence $H_1$ features in 20D maxmin-landmark VR complexes may arise from landmark sampling fluctuations and PCA projection, so the substantive $H_1$ analysis is the null comparison rather than a raw loop count.  A cheaper method that reproduces raw $H_1$ counts but breaks the null comparison should fail.

## 3. Treat sparse Rips and witness complexes differently

Sparse Rips should be your first candidate because it is closest to the current estimator.

GUDHI defines the Vietoris-Rips complex as the clique complex of a proximity graph, with simplices inserted according to diameter thresholds, and notes that the full Rips complex has exponentially many simplices in the number of vertices. ([GUDHI library][1]) That is exactly the computational wall you are hitting. GUDHI also supports sparse Rips through a `sparse` parameter, where the parameter is the approximation epsilon. ([GUDHI library][2]) The GUDHI documentation describes sparse Rips as a smaller filtered complex with interleaving guarantees, with theoretical guarantees only for $\varepsilon < 1$. ([GUDHI library][1]) Sheehy's original sparse Rips work gives the conceptual basis: a linear-size filtered complex approximating the Vietoris-Rips filtration, with constants depending on doubling dimension and approximation tightness. ([arXiv][3])

So sparse Rips can be framed as:

```text
Approximation candidate:
  "How large can epsilon be before the inferential conclusions of R break?"
```

Witness complexes are different. GUDHI defines witness complexes using landmarks as vertices and witnesses to decide which landmark simplices are inserted; landmarks are often a subset of witnesses, but not required to be. ([GUDHI library][4]) GUDHI's implementation builds nearest-landmark tables and then constructs the witness complex from those tables. ([GUDHI library][5]) That means the method changes the geometry more aggressively than sparse Rips. It is not just pruning the VR filtration; it changes the simplicial representation.

So witness/lazy witness should be framed as:

```text
Surrogate candidate:
  "Can a landmark-witness construction reproduce the inferential signature of R at much lower cost?"
```

Do not initially claim witness complexes are an approximation to your VR inference unless the calibration shows it.

## 4. Use the current results as a calibration target

The first calibration target should be a vector, not a single statistic.

For each dataset, dimension, and null rung, define the reference vector:

```text
V_R(dataset, dim, null) =
  (
    mean_obs_null,
    mean_null_null,
    sd_null_null,
    d_perm,
    rho_hat,
    rho_hat_CI,
    p_band
  )
```

Then for each cheaper method $M$, compute:

```text
V_M(dataset, dim, null)
```

and compare.

I would not use raw $p$-value agreement as the main target because the $p$-value has a resolution floor and can saturate. Your own methods section recognises that the Edgington formula floor is near $0.002$ for $N_{\text{pairs}} = 500$, and that legacy and Edgington formulas only differ practically at the floor.  Use $d_{\text{perm}}$ and $\hat\rho$ as the main calibration quantities, with $p$ as a decision-level check.

A practical scoring function could be:

```text
score(M) =
  0.35 * effect-size error
+ 0.25 * rho error
+ 0.20 * null-ladder decision error
+ 0.10 * diagram-level W2 error
+ 0.10 * seed instability penalty
```

where computational cost is reported separately as a constraint:

```text
accept M only if:
  wall-time reduction >= 5x
  peak RAM reduction >= 3x
  no negative-control failure
  no reversal of headline H0/H1 conclusions
```

## 5. Build a staged experimental design

I would run this in four phases.

### Phase A: profiling the current reference

Before changing complexes, instrument the current VR pipeline.

Record, per cell:

```text
n points / landmarks
max_edge_length
number of edges
number of triangles
number of simplices by dimension
PH wall time
W2 aggregation wall time
peak RAM
diagram cardinality by dimension
number of finite H0/H1 features
```

This will tell you whether the bottleneck is:

```text
complex construction
boundary reduction / persistent cohomology
diagram comparison
null generation / embedding
W2 aggregation
I/O and serialisation
```

Your prompt identifies two bottlenecks: large complexes at sample cohorts 1000-5000 and the $B = 1000$ permutation/aggregation burden. Those should be separated because they require different remedies. Sparse Rips and witness complexes attack the first. Adaptive null budgeting and caching attack the second.

### Phase B: sparse Rips calibration

Use sparse Rips first.

Grid:

```text
epsilon ∈ {0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50}
homology dims: H0, H1
same max_edge_length as reference
same coefficient field as reference
same point-cloud input as reference
same null draws as reference where possible
```

Run initially at reduced permutation budget:

```text
B = 100 or 200
N_pairs = min(500, B(B-1)/2)
```

Then promote only promising epsilon values to:

```text
B = 1000
N_pairs = 500
```

Acceptance criteria should be stricter for controls than for signal rungs:

```text
Negative controls:
  label/cohort shuffle must remain near exchangeability
  |d_perm| preferably < 0.5, certainly < 1
  rho_hat near 1; CI should not indicate large separation

Signal rungs:
  same sign of d_perm
  same broad magnitude class
  same ranking of Markov-memory ladder
  no H0/H1 inversion
```

I would expect sparse Rips to be the most publishable efficiency result because it has the cleanest theoretical relationship to VR.

### Phase C: witness / lazy witness calibration

Only after sparse Rips has been benchmarked, run witness complexes.

Grid:

```text
landmark count m ∈ {250, 500, 1000, 2000}
landmark policy ∈ {maxmin, epsilon-net, stratified maxmin by regime}
witness set ∈ {full point cloud, non-landmark complement}
relaxation alpha grid: method-dependent
complex type ∈ {weak witness, lazy witness if available}
```

Important: because your current VR already uses maxmin landmarks at $L = 5000$, the witness experiment should not silently compare “m landmarks” against “all data”. It should compare against the reference assay:

```text
Reference: VR on L = 5000 maxmin landmarks
Witness candidate: m landmark vertices, full or sampled witnesses
```

For trajectory data, I would add a stratified landmark policy:

```text
choose landmarks by maxmin within GMM regime,
with m_k proportional to sqrt(n_k) or capped proportional n_k,
then union across regimes.
```

Reason: pure maxmin tends to sample geometric extent rather than density. Your dimensionality note already observes that maxmin landmark selection samples the manifold's extent rather than local density, inflating the intrinsic-dimension estimates for the landmark subset relative to the full embedding.  Since witness complexes are even more landmark-sensitive, this is not a minor implementation detail.

### Phase D: permutation-budget reduction

This is separate from the complex problem.

Once you have a cheaper complex candidate, attack the $B = 1000$ burden with sequential testing.

For each cell, run in batches:

```text
B = 50 -> 100 -> 250 -> 500 -> 1000
```

Stop early if the cell is clearly classified:

```text
negative control stable:
  rho near 1, |d_perm| small, p not near threshold

strong rejection stable:
  rho far from 1, |d_perm| large, p at/near floor

uncertain:
  continue to next batch
```

The main point is to stop spending permutations on cells whose effect-size verdict is already stable. Do not make this a pure p-value stopping rule. Use $\hat\rho$, $d_{\text{perm}}$, and the null-ladder role of the cell.

Also use **common random numbers**: the same null-sequence seeds should be used across VR, sparse Rips, and witness candidates wherever possible. That reduces Monte Carlo noise in method comparisons because differences are then caused by the complex construction, not by different null draws.

## 6. Define concrete promotion gates

I would pre-register the cheaper-complex benchmark as follows.

A candidate method is promoted from “experimental approximation” to “economical replacement” only if it passes all of these:

```text
G1. Negative-control preservation:
    label/cohort controls remain exchangeable-like in both H0 and H1.

G2. Null-ladder preservation:
    order, Markov-1, stratified Markov-1, Markov-2 preserve the
    same qualitative ordering as the reference assay.

G3. Effect-size preservation:
    d_perm error <= 0.5 absolute where |d_perm_R| < 2,
    and <= 20% relative where |d_perm_R| >= 2.
    rho_hat relative error <= 10-15% for large-effect cells.

G4. Diagram stability:
    approximation-induced W2 distance is small relative to the
    reference null-null standard deviation.

G5. Seed stability:
    landmark/approximation seeds do not change the substantive verdict.

G6. Computational gain:
    at least 5x wall-time reduction or 3x peak-memory reduction
    at B = 1000-equivalent workload.

G7. No artefact regression:
    deduplication, near-zero H1 features, infinite features, and PCA
    projection conventions remain identical to the reference pipeline.
```

The “no artefact regression” gate is important. Your length-matched supplement shows that numerical near-duplicates can create phantom near-zero $H_1$ features and flip a $W_2$ verdict until corrected.  Any cheaper method must be tested against that failure mode.

## 7. What I would expect to happen

My prior would be:

1. **Sparse Rips with small epsilon** will preserve the null-ladder conclusions and give a useful speed/memory reduction. This is the best first candidate.
2. **Sparse Rips with large epsilon** will preserve large $H_0$ effects but may distort marginal H1 conclusions or negative controls.
3. **Witness/lazy witness** will be much cheaper but more sensitive to landmark policy. It may work for robust H0 structure but will need careful validation for H1.
4. **Permutation reduction** will give a large additional saving because many cells are not genuinely borderline. Strong effects and clean negative controls do not need 1000 nulls to identify their broad class; only marginal Markov-2/H1-type cells need the full budget.
5. The best final method may be hybrid:

```text
Sparse Rips for the headline economical replication.
Witness/lazy witness as an exploratory low-budget screen.
Adaptive B for null computation.
Full VR retained as the reference assay on a reduced set of validation cells.
```

## 8. How to frame this in the paper or a follow-on methods paper

I would not frame this as “we used a cheaper complex because VR is too expensive.”

Frame it as:

> The full Vietoris-Rips/Markov-null battery is a high-cost reference assay. We use it to calibrate economical filtrations and reduced null budgets, requiring candidate methods to reproduce the reference assay's inferential signature across negative controls, Markov-memory rungs, homology dimensions, and survey replications.

That is a much stronger methodological claim.

A possible section title:

```text
Calibrating economical filtrations against a Vietoris-Rips reference assay
```

A possible abstract-level sentence:

```text
Rather than replacing Vietoris-Rips persistence by an unvalidated cheaper complex, we treat the full Markov-null Vietoris-Rips battery as a reference assay and ask which sparse or landmark-witness filtrations preserve its inferential signature at lower computational cost.
```

## 9. Recommended immediate next step

Run a **small calibration spike** before designing the full study.

### Spike: S-Rips-1

```text
Data:
  USoc only, L = 5000 reference point cloud
  H0/H1
  nulls: label, order, Markov-1, Markov-2
  B = 100 using locked seeds

Methods:
  baseline VR
  sparse Rips epsilon = 0.05, 0.10, 0.20, 0.30

Metrics:
  wall time
  peak RAM
  simplex counts
  diagram cardinalities
  W2(D_sparse, D_VR)
  d_perm
  rho_hat
  p-band

Promotion:
  choose the largest epsilon that preserves:
    label control,
    Markov-1 H0 large effect,
    Markov-2 marginal structure,
    no H1 direction reversal.
```

Then run a second spike:

### Spike: Witness-1

```text
Data:
  same as S-Rips-1

Methods:
  lazy/weak witness
  m = 250, 500, 1000, 2000
  landmark policy = maxmin and stratified maxmin

Promotion:
  retain only candidates that preserve negative controls
  and do not introduce H1 artefacts.
```

This gives you an empirical Pareto frontier:

```text
method, parameter, runtime, RAM, fidelity
```

At that point you can decide whether the publishable object is:

1. a paper supplement justifying an economical rerun;
2. a standalone methodological paper on calibrated economical TDA for Markov-null sequence analysis;
3. a software/pipeline contribution;
4. a Lean-backed formal strand proving one reduction/approximation claim while the empirical study calibrates the rest.

My recommendation: start with sparse Rips as the formal approximation candidate, witness as the empirical surrogate candidate, and adaptive permutation budgets as the separate computational-statistics candidate. Do not bundle all three into one uncontrolled optimisation.

[1]: https://gudhi.inria.fr/doc/2.3.0/group__rips__complex.html "GUDHI: Rips complex"
[2]: https://gudhi.inria.fr/python/latest/rips_complex_ref.html "Rips complex reference manual — gudhi v3.13.0 documentation"
[3]: https://arxiv.org/abs/1203.6786 "[1203.6786] Linear-Size Approximations to the Vietoris-Rips Filtration"
[4]: https://gudhi.inria.fr/python/2.0.0/witness_complex_user.html?utm_source=chatgpt.com "Witness complex user manual"
[5]: https://gudhi.inria.fr/python/3.8.0/witness_complex_user.html?utm_source=chatgpt.com "Witness complex user manual"
