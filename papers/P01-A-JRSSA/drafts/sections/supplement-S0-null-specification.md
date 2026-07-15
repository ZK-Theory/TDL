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

Algorithm:

```
permutation ← rng.permutation(N)            # N = number of point-cloud rows
X_null      ← X[permutation]                # row-permuted embedding
return X_null
```

The embedding rows are permuted in place. No re-embedding step.
Trajectory-row to embedding-row assignment is destroyed; everything else is
preserved.

## §S0.2 Cohort shuffle

Algorithm:

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

Algorithm:

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

Algorithm:

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

Algorithm:

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
the integer GMM assignments used in Table 2; the function rejects scalar inputs (cluster count `k`) and
length-mismatched label arrays, with explicit error messages, to prevent
the two most common misuse patterns.

Smoothing: the canonical implementation uses *raw maximum-likelihood*
per-regime transition matrices with zero-row safety only; no Laplace
prior is applied at this order.

## §S0.6 Markov-2

Algorithm:

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

Each null type is run for $B$ permutations and $N_{\text{pairs}}$ null-null
pairs. The pre-registration (2026-05-13) locks $B = 1{,}000$ and
$N_{\text{pairs}} = 500$ for the headline run. The headline
$p$-value uses the Edgington form

$$
\hat p \;=\; \frac{1 + \big|\big\{(j, j') :
W_2\big(D^{(j)}_{\text{null}}, D^{(j')}_{\text{null}}\big)
\;\ge\;
\overline{W_2}\big(D_{\text{obs}}, D^{(j)}_{\text{null}}\big)
\big\}\big|}{1 + N_{\text{pairs}}},
$$

with $\overline{W_2}(\cdot, \cdot)$ the mean across the $B$ stored
obs-null distances. The headline implementation writes the full
`obs_null_distribution` array and the null-null summary statistics to JSON
for downstream effect-size and CI computation (Tables 1 and S1). The
resolution floor of $1 / (1 + N_{\text{pairs}}) \approx 0.002$ at
$N_{\text{pairs}} = 500$ replaces the strict-zero floor that the raw
empirical fraction produces when all null-null distances fall below the
obs-null mean.

> *Note on legacy data.* Some figures and tables consume post-audit output
> computed under a legacy code path that used the empirical-fraction form
> $\hat p_{\text{legacy}} = N_{\text{pairs}}^{-1} \,|\{\ldots\}|$ rather
> than the Edgington form $(1 + |\{\ldots\}|) / (1 + N_{\text{pairs}})$.
> Above the resolution floor the two formulas agree to within
> $1 / (1 + N_{\text{pairs}}) \approx 0.002$; the only practical
> difference is the floor itself ($0$ vs $\approx 0.002$). The headline
> $B = 1{,}000$ results use the Edgington form; legacy values are labelled
> in the supplement where they appear and will be re-reported under the
> Edgington form in the final submission. The post-audit canonical runs
> ($L = 5{,}000$, $B = 100$, $N_{\text{pairs}} = 500$) are the
> legacy-formula values consumed by the Supplement §S1 and Table 1 cells
> that label themselves *post-audit canonical*.
