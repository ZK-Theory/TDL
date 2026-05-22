<!--
Target location in v2: Supplement §S0 (precedes the existing S1–S5 outline in
v1-2026-04.md lines 395–405).

Evidence sources verified during drafting:
  • `trajectory_tda/topology/permutation_nulls.py`
      `_label_shuffle` lines 53–64,
      `_cohort_shuffle` lines 67–92,
      `_order_shuffle` lines 95–113,
      `_markov_shuffle` (orders 1 and 2) lines 116–241,
      `_stratified_markov_shuffle` lines 249–383,
      `permutation_test_trajectories` lines 571–752.
  • `trajectory_tda/scripts/run_wasserstein_battery.py` `run_battery` lines
    298–434 — drives the post-audit JSON outputs.
  • `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_20260502.json`
    and the BHPS counterpart at the same date — provide the empirical
    `n_permutations` and `n_null_null_pairs` for the post-audit summary.
  • `papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md`
    Reviewer 1 issue R1-M1 — explicit null-model specification required.

Forbidden content (verified absent below): no reporting of $p$-values, no
claim about which nulls reject which dimensions. §S0 specifies the
machinery; the empirical results live in §4.3, §6.2, and the gated tables.

DEVIATION FROM TASK PROMPT: the Task description states that the stratified
Markov-1 null uses "α = 1 Laplace smoothing"; the canonical implementation
in `_stratified_markov_shuffle` uses raw maximum-likelihood per-regime
transition matrices with zero-row safety (no Laplace term). Laplace
smoothing with α = 1 is applied only to the Markov-2 conditional bigram
probabilities in `_markov_shuffle(markov_order = 2)`. The text below
matches the code.
-->

# Supplement §S0 — Null-Model Specification

The five Markov-memory rungs and the stratified Markov-1 rung referenced in
§3.3 and §4.3 are specified below at algorithm-pseudocode level. Each rung
acts on the same input pair: (i) the embedded point cloud $X \subset
\mathbb{R}^{20}$ used to compute the observed persistence diagram, and (ii)
the underlying state-sequence trajectories from which $X$ was derived. The
re-embedding step for the trajectory-level rungs uses the PCA loadings
fitted on the observed data, held fixed across all permutations; this is a
deliberate choice and is restated below.

## §S0.1 Label shuffle

Algorithm — `_label_shuffle` in `trajectory_tda/topology/permutation_nulls.py`:

```
permutation ← rng.permutation(N)            # N = number of point-cloud rows
X_null      ← X[permutation]                # row-permuted embedding
return X_null
```

The embedding rows are permuted in place. No re-embedding step.
Trajectory-row to embedding-row assignment is destroyed; everything else is
preserved.

## §S0.2 Cohort shuffle

Algorithm — `_cohort_shuffle`:

```
for each cohort bin c in unique(cohort_labels):
    indices_c ← {i : cohort[i] = c}
    permutation_c ← rng.permutation(|indices_c|)
    X_null[indices_c] ← X[indices_c[permutation_c]]
return X_null
```

Permutes rows of the embedding within each cohort bin only. Cohort labels
are normalised through `_normalise_cohort_label` before bin assignment to
collapse BHPS and USoc representations of the same birth-decade label.
Within-cohort structure preserved; between-cohort assignment destroyed.
Falls back to label shuffle if the `cohort` field is absent from the
metadata.

## §S0.3 Order shuffle

Algorithm — `_order_shuffle`:

```
for each trajectory traj_i (length T_i):
    permutation_i ← rng.permutation(T_i)
    traj_i_null  ← traj_i[permutation_i]
X_null, _ ← ngram_embed(trajectories_null, **embed_kwargs)
return X_null
```

Permutes the time-order of states *within* each trajectory and re-embeds the
resulting state-sequence list through the same `ngram_embed` pipeline (PCA
loadings reused; see §S0.7). Unigram (state-frequency) structure is
preserved; bigram and higher-order temporal structure are destroyed.

## §S0.4 Markov-1

Algorithm — `_markov_shuffle(markov_order = 1)`:

```
TM        ← (n_states × n_states) zero matrix
init_cnts ← n_states zeros
for each trajectory traj_i:
    init_cnts[traj_i[0]] += 1
    for t in 0 .. T_i - 2:
        TM[traj_i[t], traj_i[t+1]] += 1
TM        ← row-normalise(TM)                 # raw MLE, no smoothing
init_p    ← init_cnts / sum(init_cnts)        # empirical first-state
                                              # distribution
synthetic ← []
for each trajectory traj_i:
    current ← rng.choice(n_states, p = init_p)
    seq     ← [current]
    for t in 1 .. T_i - 1:
        current ← rng.choice(n_states, p = TM[current])
        seq.append(current)
    synthetic.append(seq)
X_null, _ ← ngram_embed(synthetic, **embed_kwargs)
return X_null
```

Single globally fitted first-order transition matrix; per-trajectory length
preserved one-to-one ($T_i$ on input ↦ $T_i$ on output); initial-state
distribution is the empirical first-state frequency vector across all
trajectories. Row-zero safety (`row_sums[row_sums = 0] ← 1`) prevents
division errors and has no effect on rows with observations; no
Laplace smoothing is applied at this order.

## §S0.5 Stratified Markov-1

Algorithm — `_stratified_markov_shuffle`:

```
for each regime k in unique(regime_labels):
    indices_k ← {i : regime_labels[i] = k}
    if |indices_k| < min_regime_n (= 30):
        TM_k     ← global_TM        # fallback
        init_p_k ← global_init_p
    else:
        TM_k, init_p_k ← raw-MLE first-order chain on trajectories[indices_k]
                                    # row-normalised counts;
                                    # init_p from regime-specific first
                                    # states
for each trajectory traj_i with regime label k:
    sample synthetic_i from (TM_k, init_p_k) at length T_i
X_null, _ ← ngram_embed(synthetic, **embed_kwargs)
return X_null
```

Per-regime transition matrices are fitted on regime-specific trajectories
only and applied to generate per-regime synthetic sequences. The
`min_regime_n = 30` fallback transfers a regime to the global transition
matrix when fewer than 30 trajectories support it. The regime labels are
the integer GMM assignments from `05_analysis.json` (the same labels used
in Table 2); the function rejects scalar inputs (cluster count `k`) and
length-mismatched label arrays, with explicit error messages, to prevent
the two most common misuse patterns.

Smoothing: the canonical implementation uses *raw maximum-likelihood*
per-regime transition matrices with zero-row safety only; no Laplace
prior is applied at this order.

## §S0.6 Markov-2

Algorithm — `_markov_shuffle(markov_order = 2, alpha = 1.0)`:

```
init_cnts     ← n_states zeros
bigram_counts ← {(i, j) -> n_states-zeros vector}
for each trajectory traj_i:
    init_cnts[traj_i[0]] += 1
    for t in 0 .. T_i - 3:
        bigram_counts[(traj_i[t], traj_i[t+1])][traj_i[t+2]] += 1
for each (i, j) in observed bigrams:
    bigram_probs[(i, j)] ← (bigram_counts[(i, j)] + alpha) /
                            (sum(bigram_counts[(i, j)]) + alpha · n_states)
init_p          ← init_cnts / sum(init_cnts)
uniform_fallback ← (1 / n_states) repeated n_states times
synthetic ← []
for each trajectory traj_i:
    prev    ← rng.choice(n_states, p = init_p)
    current ← rng.choice(n_states, p = uniform_fallback)
    seq     ← [prev, current]
    for t in 2 .. T_i - 1:
        p_next ← bigram_probs.get((prev, current), uniform_fallback)
        nxt    ← rng.choice(n_states, p = p_next)
        seq.append(nxt); prev ← current; current ← nxt
    synthetic.append(seq)
X_null, _ ← ngram_embed(synthetic, **embed_kwargs)
return X_null
```

Conditional bigram → next-state probabilities are computed with Laplace
add-$\alpha$ smoothing at $\alpha = 1$, so each conditional distribution has
weight $(c + 1)/(c_{\text{tot}} + 9)$ on each of the nine states; unobserved
bigrams default to the uniform distribution. The second-state draw is
deliberately uniform (no bigram context yet exists at $t = 1$), so the
$T_i = 2$ case degenerates to an independence model on the second token.

## §S0.7 Trajectory length, initial state, PCA loadings, and seeds

The four cross-cutting policies that apply to every rung above:

1. *Trajectory lengths* are preserved one-to-one: the synthetic sequence
   produced for trajectory $i$ has length $T_i$ matching the observed
   trajectory $i$. The order of trajectories in the list is preserved.

2. *Initial-state distribution* is the empirical first-state frequency
   across all (or regime-specific) trajectories, normalised to sum to one.
   Trajectories of length zero are skipped during count accumulation but
   do not contribute to the synthetic output (they would produce
   zero-length synthetics by construction).

3. *PCA loadings* — and the full `ngram_embed` configuration — are held
   fixed at the observed fit and reused for every null draw via the
   `embed_kwargs` dictionary stored alongside the observed embedding. This
   is a non-trivial choice: null-side re-embedding under the *same* PCA
   loadings tests whether the embedded trajectory geometry under the
   observed PCA basis is exchangeable with the null, isolating
   trajectory-level structure from PCA-rotation variability. Re-fitting
   PCA on each null draw would conflate the two sources of variability
   and is not done.

4. *Seeds.* The driver `permutation_test_trajectories` accepts a master
   seed (default `seed = 42`) and constructs per-permutation seeds
   $s_j = \text{seed} + j + 1$ for $j = 1, \ldots, B$. The null-null pair
   subsampling uses a separate `np.random.RandomState(seed)` to draw
   `min(500, B (B - 1) / 2)` distinct index pairs from the $B$ stored
   diagrams.

## §S0.8 Permutation budget and $p$-value computation

Each null type is run for $B$ permutations. The post-audit canonical runs
deposited in `results/trajectory_tda_integration/post_audit/` and
`results/trajectory_tda_bhps/post_audit/` use $B = 100$ permutations and
$N_{\text{pairs}} = 500$ null-null pairs (`L = 5{,}000` landmarks, May
2026); the pre-registration locks $B = 1{,}000$ for the headline relaunch
when the resumed phase-split pipeline emits the next round of diagrams.
All $p$-values below the headline relaunch are computed identically by

$$
\hat p \;=\; \frac{1}{N_{\text{pairs}}}\, \Big|\big\{(j, j') :
W_2\big(D^{(j)}_{\text{null}}, D^{(j')}_{\text{null}}\big)
\;\ge\;
\overline{W_2}\big(D_{\text{obs}}, D^{(j)}_{\text{null}}\big)
\big\}\Big|,
$$

with $\overline{W_2}(\cdot, \cdot)$ the mean across the $B$ stored
obs-null distances. The implementation
(`permutation_test_trajectories`, lines 571–752) writes the full
`obs_null_distribution` array and the null-null summary statistics to JSON
for downstream effect-size and CI computation (Tables 1 and S1).
