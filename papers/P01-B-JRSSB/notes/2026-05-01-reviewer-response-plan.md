# P01-B v1 Reviewer-Response Plan

**Drafted:** 2026-05-01
**Target draft to revise:** [v1-2026-04.md](../drafts/v1-2026-04.md)
**Reviewer:** External TDA methodological reviewer (round 0, pre-submission)
**Status:** Planning only — no code changes or revisions executed.
**Companion plan:** [P01-A reviewer-response plan](../../P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md). The two papers must be revised in lockstep — many computations serve both.

---

## 0. Document Purpose

The reviewer raised twelve numbered issues in §Summary plus several embedded concerns. Severity ratings used by the reviewer: **Critical** (×2), **High** (×4), **Medium** (×4), **Low–Medium** (×1), **Low** (×1).

This document plans a comprehensive response to every issue — without exception — before producing v2. For each issue we record: (i) what the reviewer said, (ii) the current state in the v1 draft and the codebase / results store, (iii) whether the gap is **prose-only**, **needs new computation**, or **both**, (iv) the concrete strategy to close it, (v) the artefacts and locations expected, and (vi) a verification check.

Two reviewer findings are *worse* than the reviewer realised, after we audited the code:
- The Markov-2 null in `permutation_nulls.py` (lines 168–234) does **no Laplace smoothing**. It uses uniform-distribution fallback only for unseen bigrams. The paper's §3.2 prose ("Laplace smoothing for the $|\mathcal{S}|^2 = 81$ two-step conditioning cells") does not match the implementation. This is more than a "smoothing parameter not stated" — it is a methods-vs-code inconsistency.
- The canonical scale $\varepsilon^* = 0.70$ used in §4.3.2 does **not** match `results/trajectory_tda_zigzag/sensitivity_2d/knee_analysis.json`, which reports median knee = 0.54, mean knee = 0.51, with 5 of 32 years giving degenerate knees ($\varepsilon = 0.05$). The 0.70 value approximates the post-2010 USoc-era median; this is justifiable but currently undocumented.

A consolidated work list with sequencing, blocking dependencies, and resource estimates is in §13. Acceptance criteria for v2 are in §14.

This plan is deliberately exhaustive. Every reviewer claim is itemised below so that nothing is silently dropped.

**Coordination with P01-A.** P01-A and P01-B share the same checkpoint, embedding, null battery, and Wasserstein audit. Tasks marked **[P01-A SHARED]** appear in both response plans and need only be executed once. The substantive division of labour follows the CONVENTIONS BHPS-split rule: applied findings stay in P01-A, methodological framework stays in P01-B; a few items (notably the stratified Markov-1 result and the H₂ check) appear in both papers but with different framing.

---

## 1. ISSUE C1 — Landmark count inconsistency (5,000 vs 2,000 across compared statistics)

### 1.1 Reviewer claim

> "**Critical.** The core finding of the paper — the scalar/diagram discrepancy at Markov-1 — is demonstrated with different landmark counts for the two statistics being compared. […] At minimum, a confirmatory result at matched landmark counts is required before this discrepancy can be presented as a methodological finding rather than a computational artefact."

The reviewer correctly notes that §5.2 advises practitioners to "verify changed Markov conclusions at higher landmark counts" — but the paper itself does not perform this verification.

### 1.2 Current state

- **§4.2.2 — total persistence:** $L = 5{,}000$ landmarks.
- **§4.2.3 — $W_2$ diagrams:** $L = 2{,}000$ landmarks. The reason given (vault Computational-Log 2026-03-24): "Wasserstein tests use fewer landmarks due to computational cost."
- **Existing robustness data:** `results/trajectory_tda_robustness/landmark_sensitivity/` contains total-persistence runs at $L \in \{2500, 5000, 8000\}$ and order-shuffle/Markov-1/Markov-2 nulls at the same $L$ values. None of these are $W_2$ runs — they are total-persistence statistics only. Confirmed by inspection of `landmark_sensitivity_summary.json`.
- **The paper's own §5.2 acknowledges the gap** but defers the matched-$L$ verification to the practitioner.

### 1.3 Classification

**Both** — needs new computation (W₂ at matched $L$) AND substantial prose changes in §3.3, §4.2.3, §5.2.

### 1.4 Strategy [P01-A SHARED]

This is identical in scope to P01-A §1. Strategy:

1. **Settle on a single canonical $L$ for both statistics in the headline result.** Choose $L = 5{,}000$, matching the existing total-persistence battery and falling within the empirical stability range for total persistence.
2. **Recompute the $W_2$ null battery at $L = 5{,}000$** for all five rungs (label, cohort, order, Markov-1, Markov-2) on the USoc and BHPS checkpoints. Use the existing `run_wasserstein_battery.py` with `--landmarks 5000`. Estimated wall-clock: ≈ 5–8 h (USoc) + 2–3 h (BHPS) at the n_perms = 100, n_nullnull = 500 settings of the post-audit.
3. **Cross-landmark sensitivity table** in supplement §S1 (new): paired total-persistence and $W_2$ p-values at $L \in \{2500, 5000, 8000\}$ for all five nulls, both H₀ and H₁. Lets reviewers see the L-dependence of *both* statistics, not just total persistence.
4. **Outcome decisions.**
   - If matched-$L$ $W_2$ Markov-1 H₀ p remains $< 0.05$ on either USoc or BHPS, the headline "scalar–diagram discrepancy" survives; report the matched-$L$ number as headline and demote the legacy $L = 2{,}000$ to supplement.
   - If matched-$L$ $W_2$ Markov-1 p ≥ 0.10 on USoc but BHPS still rejects, the discrepancy claim is preserved but reframed as era-specific (BHPS-only). The abstract and §6 conclusion change accordingly.
   - If matched-$L$ $W_2$ Markov-1 p ≥ 0.10 on both, the central methodological claim collapses and the paper must be substantially restructured. This is the scenario in which the reviewer's concern fully materialises and requires the contingent revision described in §2 below (the $p = 0.002$ vs $p = 0.070$ question).
5. **Prose updates in §3.3 and §4.2.3:** state explicitly that $L$ is matched across statistics, justify the chosen $L$ value by reference to the supplement table, and remove the §5.2 sentence that punts the verification to practitioners.

### 1.5 Artefacts to produce

- `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_<date>.json`
- `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_L5000_<date>.json`
- New supplement table S1.1 — total persistence and $W_2$ p-values at $L \in \{2500, 5000, 8000\}$ for all five nulls, both H₀ and H₁.
- Vault entry: `[RESULT]` log entry to `04-Methods/Computational-Log.md`.

### 1.6 Verification

- §3.3 of v2 names a single $L$ used for both statistics in the headline result.
- Tables 1 and 2 of §4.2 are at matched $L$.
- The reviewer's specific concern ("not directly comparable") is addressed verbatim in the methods text.
- §5.2 practitioner guidance no longer offloads matched-$L$ verification to the reader.

---

## 2. ISSUE C2 — Abstract states $p = 0.002$ but Table 2 shows $p = 0.070$

### 2.1 Reviewer claim

> "**Critical.** The abstract states the core discrepancy result ($p = 0.002$), but Table 2 shows USoc Markov-1 H₀ $p = 0.070$. The $p = 0.002$ is described as a 'legacy USoc result' in §4.2.4, while the current post-audit result is $p = 0.070$. If the main finding is $p = 0.070$, the abstract's central claim is not supported by the current computation."

### 2.2 Current state

- **Abstract:** "the scalar test reports that first-order Markov dynamics (Markov order $k = 1$) account for the topology ($p = 1.000$), while $W_2$ rejects the same first-order null ($p = 0.002$)."
- **§4.2.3 Table 2 (post-audit, $L = 2{,}000$, $B = 100$, seed = 42):** USoc Markov-1 H₀ $p = 0.070$.
- **§4.2.4 prose:** "Total persistence reports $p = 1.000$ (non-rejection); $W_2$ reports $p = 0.002$ in the legacy USoc result and a decisively rejected BHPS result."
- The paper carries both numbers without resolving which one is the headline. The abstract sides with the legacy result; the body sides with the post-audit. Reviewers will read this as numerical inconsistency, and they would be right.
- **Vault Computational-Log 2026-04-07 — Post-audit W₂ entry:** confirms the post-audit USoc Markov-1 $W_2$ H₀ $p = 0.070$ and notes the BHPS rejection $p = 0.000$. The legacy $p = 0.002$ comes from `04_nulls_wasserstein.json` (pre-audit).

### 2.3 Classification

**Prose-only first**, but the substantive resolution depends on the matched-$L$ rerun in §1 above. The two issues are conjoined.

### 2.4 Strategy

1. **Decide which number is the authoritative headline.** Two options:
   - **(a) Use the post-audit $p = 0.070$.** This is methodologically honest. The implication: the central claim of the paper is no longer "scalar says non-rejection, $W_2$ rejects" but rather "scalar says non-rejection ($p = 1.000$), $W_2$ shifts the conclusion toward rejection but does not cross conventional significance ($p = 0.070$) on USoc; on BHPS, $W_2$ decisively rejects ($p < 0.001$)." This is still a *methodologically interesting* finding (scalar gives $p = 1.000$ overshooting the null; $W_2$ gives $p = 0.070$, an order-of-magnitude shift) but it is not the same finding as $p = 0.002$.
   - **(b) Re-run the $W_2$ Markov-1 test under matched $L = 5{,}000$ and use that as the headline.** This is what §1 of this plan recommends. The matched-$L$ outcome will determine whether the abstract's $p = 0.002$ claim is recoverable, partially recoverable (BHPS only), or not recoverable.
2. **Pre-commit to a publication rule.** Whatever the matched-$L$ result is, the abstract, §4.2.3, §4.2.4, and §6 must all use the same number. No "legacy" numbers anywhere in the headline narrative. Legacy values should only appear in §5.3 / supplement as historical context.
3. **Reconcile the legacy $p = 0.002$ vs post-audit $p = 0.070$.** Both come from $L = 2{,}000$, $B = 100$, seed = 42 nominally. The vault Computational-Log explicitly attributes the discrepancy to "code/environment provenance drift" — the same drift that produces the 11.5% replay drift on the obs-null mean (ISSUE H4 / §5 below). Document the discrepancy explicitly in §5.3 limitations: "Two $W_2$ Markov-1 H₀ runs on USoc, both with the stated parameters, produced $p = 0.002$ (pre-2026-04-07) and $p = 0.070$ (post-audit). The drift is consistent with the unresolved replay-drift issue documented in §4.2.1." The post-audit run is the authoritative one because it was performed under the audited code path.
4. **Re-write the abstract** to reflect the headline number from the matched-$L$ rerun. Three contingency drafts for the abstract sentence:
   - **If matched-$L$ USoc $p < 0.005$:** "the scalar test reports first-order Markov dynamics account for the topology ($p = 1.000$), while $W_2$ at matched landmark count rejects the same null ($p < 0.005$)." — closest to the legacy story.
   - **If matched-$L$ USoc $0.005 \leq p < 0.05$:** rewrite to "$W_2$ at matched landmark count rejects the same null at conventional significance ($p = X.XXX$) on the USoc sample, with stronger rejection on the longer BHPS panel ($p < 0.001$)."
   - **If matched-$L$ USoc $p \geq 0.05$:** rewrite to "$W_2$ shifts the conclusion sharply ($p_{\text{scalar}} = 1.000$ vs $p_{W_2} = X.XX$, an order-of-magnitude reduction), and the diagram-level test rejects the same first-order null on the longer BHPS panel ($p < 0.001$). The contrast between scalar non-rejection and diagram-level evidence — even when both are non-significant on the shorter panel — is itself the methodological lesson."
5. **Either way, the abstract must change.** The current $p = 0.002$ wording is unsalvageable.

### 2.5 Artefacts to produce

- Reconciliation note in §5.3 (or a new §4.2.5 "Reconciliation of pre- and post-audit $W_2$ values").
- Three contingent abstract drafts (held in this plan as §2.4 above) — one is selected after the §1 rerun.
- Updated §4.2.4 prose using a single authoritative $p$-value.

### 2.6 Verification

- The abstract, every results table caption, and §6 conclusion all cite the same $W_2$ $p$-value for USoc Markov-1 H₀.
- No instance of "legacy USoc result" appears outside §4.2.5 (or §5.3).
- A reader cannot find two numerical claims for the same test in the v2 manuscript.

---

## 3. ISSUE H1 — $W_2$ ground metric inconsistency: definition $\|\cdot\|_\infty$ vs implementation $\|\cdot\|_2$

### 3.1 Reviewer claim

> "The formal definition of $W_p$ in §3.1 contains a subtle but significant error: the ground metric in the infimum is stated as $\|\cdot\|_\infty$. However, the implementation description states `gudhi.wasserstein` with `order=2` and `internal_p=2`, meaning the ground metric is $\|\cdot\|_2$ (Euclidean). The standard definition in Cohen-Steiner et al. (2007) uses $\|\cdot\|_\infty$ ground metric for the bottleneck and $p$-Wasserstein distances, and this is what `internal_p=inf` would produce. The paper's formal definition and its computational implementation are inconsistent. This is not merely a notational issue: the $L^\infty$ and $L^2$ ground metrics yield different numerical distances and different stability constants."

### 3.2 Current state

- **§3.1 line 92:** $W_p(D, D') = \left(\inf_\gamma \sum_i \|x_i - \gamma(x_i)\|_\infty^p\right)^{1/p}$ — uses $\ell^\infty$.
- **§3.3 prose:** "the `gudhi.wasserstein` implementation backed by the POT (Python Optimal Transport) library with `order=2` and `internal_p=2`" — uses $\ell^2$.
- **`vectorisation.py:232`:** `gudhi.wasserstein.wasserstein_distance(dgm1, dgm2, order=p, internal_p=2)` with `p = 2`. Confirmed: implementation is $\ell^2$ ground metric.
- **CONVENTIONS:** P01 uses $W_2$. The notation file `papers/shared/notation.md` is the source of truth — must be checked against this fix.
- **Stability theorem (Cohen-Steiner et al. 2007):** the standard form is bottleneck-stability under $\ell^\infty$ ground metric; the $W_p$ extension under $\ell^\infty$ ground metric is the stable form. The Skraba-Turner (2020) paper extends $W_p$ stability to general $\ell^q$ ground metrics including $\ell^2$, but with different constants. The reviewer is correct that the paper currently mixes the two.

### 3.3 Classification

**Prose-only AND a decision about whether to change the implementation.** Two clean options:

### 3.4 Strategy

1. **Decide between two corrections.**
   - **(A) Keep $\ell^2$ implementation, fix the formula.** This is the lowest-cost option. Replace the §3.1 formula with $\|x_i - \gamma(x_i)\|_2$ and cite Skraba & Turner (2020) for the stability constant under the $\ell^2$ ground metric. This is what the code actually does and what all the existing results reflect. **Recommended.**
   - **(B) Switch implementation to $\ell^\infty$ ground metric.** This requires `internal_p=inf` in `gudhi.wasserstein.wasserstein_distance(...)`, recomputing every $W_2$ in the paper, and re-running the entire null battery. This is a much larger amount of work and changes every reported numerical value. The argument for (B) is canonical compatibility with the Cohen-Steiner et al. (2007) stability theorem. The argument against is the cost-benefit: option (A) is consistent with the existing literature using $\ell^2$ ground metric (e.g. Carrière et al. 2017; Bubenik 2020) and adds a single citation rather than weeks of compute.
2. **Document the decision in the supplement.** Even under option (A), the supplement should explain that $W_2$ with $\ell^2$ ground metric is one of two standard variants and cite the stability result for this variant. State the precise mathematical object computed: "$W_2$ under the $\ell^2$ ground metric on the birth-death plane, with diagonal projection $(b, d) \mapsto ((b+d)/2, (b+d)/2)$, distance to diagonal $(d - b) / \sqrt 2$."
3. **Update the notation document `papers/shared/notation.md`** (CONVENTIONS-locked) to lock the choice and the constants, so future drafts in the programme cannot drift.
4. **Sensitivity check.** As a small safety net, compute a single test (Markov-1 H₀ on USoc) under both ground metrics at $L = 2{,}000$, $B = 50$, and report the two p-values side by side. If they agree qualitatively (both reject or both fail to reject), the choice is empirically immaterial for the headline finding and the paper can confidently default to $\ell^2$. If they disagree, the choice is material and option (B) becomes mandatory.

### 3.5 Artefacts to produce

- Corrected formula in §3.1.
- New supplement subsection "Choice of ground metric for $W_2$" (~ 200 words + one-line stability statement + one-line cost statement).
- `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L2000_internal_pInf_<date>.json` for the sensitivity check above.
- Updated `papers/shared/notation.md` with the locked ground-metric choice and stability constants.

### 3.6 Verification

- §3.1 formula and §3.3 implementation description use the same ground metric.
- The supplement's ground-metric statement matches `vectorisation.py:232`.
- The reviewer's "not merely a notational issue" criticism cannot be re-raised on the same evidence.
- A small numerical comparison (one test, two ground metrics) is on file as the empirical check.

---

## 4. ISSUE H2 — Globally estimated Markov null misspecification

### 4.1 Reviewer claim

> "For a JRSS-B methods paper, a known source of misspecification that may be the *sole* cause of the central finding cannot be relegated to a paragraph in §5.3. The regime-stratified Markov null is described as requiring 'regime labels to be defined independently of the TDA results' — this is a circular dependency that is real but overstated. The GMM regime labels from the companion paper are defined by Gaussian mixture model on the PCA embedding, prior to TDA; they are available and independent of the null test. A regime-stratified surrogate test is feasible and should be reported."

### 4.2 Current state

- **§5.3:** "Stratified Markov nulls — separate transition matrices per regime — would disambiguate this, but require regime labels to be defined independently of the TDA results." — the reviewer correctly identifies this as overstated; GMM labels in P01-A *are* independent of the null tests.
- **Code exists in `permutation_nulls.py:246–362`:** `_stratified_markov_shuffle()` takes `regime_labels` and produces per-regime synthetic trajectories.
- **Existing run is broken** (same as P01-A H2): `results/trajectory_tda_integration/stratified_markov/stratified_markov1_results.json` has `regime_distribution: {0: 27252, 3: 28}` because of an sklearn version mismatch that collapsed labels to 2 effective regimes. The result is functionally a duplicate of the global Markov-1 null.
- **CONVENTIONS rule (Markov-Memory-Ladder.md):** explicitly notes "Markov-1 destroys regime substructure" — known limitation, never previously tested.

### 4.3 Classification

**Both** — needs new computation (the same fix as P01-A H2) AND substantial prose changes in §3.2, §4.2, §5.3, possibly the abstract.

### 4.4 Strategy [P01-A SHARED]

1. **Diagnose the regime-label loading bug.** Same as P01-A: identify why the existing stratified-Markov run collapsed to 2 effective regimes (likely sklearn 1.8.0 → 1.3.2 mismatch; verify and fix).
2. **Run a correctly stratified Markov-1 null** at $L = 5{,}000$ (matching ISSUE C1), $n\_perms = 100$, all seven regimes represented (verify regime distribution matches P01-A Table 2), both H₀ and H₁, on both USoc and BHPS checkpoints.
3. **Decision rule for §3.2 of P01-B (different from P01-A).** P01-A reports the substantive *outcome* (does stratification absorb the rejection?). P01-B reports the *methodological framework*: stratified Markov-1 is added formally as a sixth rung on the ladder, regardless of outcome. The methods presentation:
   - Insert "Level 4b — Stratified Markov order-1" between Levels 4 and 5 in §3.2.
   - State the formal hypothesis: $H_0^{(4b)}$: the topology is consistent with surrogates generated by per-regime first-order Markov chains, with regime labels defined independently of the TDA pipeline (see P01-A §3.4).
   - Pseudocode (~ 8 lines) for the stratified procedure.
   - Discussion of when this null is appropriate (when regimes are pre-defined and substantive).
4. **Update §3.2 procedure** to clarify that regime labels for the stratified rung come from the GMM in P01-A, fitted to the PCA embedding *prior* to any TDA computation, and are therefore independent of the null comparison. This rebuts the "circular dependency" framing in v1 §5.3.
5. **Update Table 2 in §4.2.3** to add a row for stratified Markov-1 (USoc and BHPS, H₀ and H₁).
6. **Outcome decision tree (mirrors P01-A H2):**
   - **Outcome A — stratified Markov-1 still rejected ($W_2$ p < 0.05):** the methodological message strengthens. The discrepancy holds against the better-specified null. Update §4.2.4 to note this explicitly.
   - **Outcome B — stratified Markov-1 not rejected:** the central finding shifts character. The "scalar vs $W_2$ disagree at Markov-1" lesson is preserved (because total persistence with the global Markov-1 null still says $p = 1.000$), but now must be framed as "the apparent non-Markovian structure detected by $W_2$ at the global Markov-1 level disappears under a regime-stratified null, *which is the more accurate test*. The methodological lesson remains: scalar persistence statistics can hide null misspecification that diagram-level statistics expose."
   - **Outcome C — borderline (0.05 ≤ p < 0.20):** report both global and stratified results, discuss the methodological implication, possibly escalate to a stratified Markov-2 rung.
7. **Pre-register the analysis** (in this plan, with timestamp): $L = 5{,}000$, $n\_perms = 100$, both H₀ and H₁, decision rule p < 0.05 → reject, p ≥ 0.20 → fail to reject, 0.05–0.20 → borderline. This makes outcome B a transparent revision rather than HARKing.

### 4.5 Artefacts to produce

- Diagnostic note: `papers/shared/2026-05-XX-stratified-markov-diagnosis.md` (shared with P01-A).
- `results/trajectory_tda_integration/stratified_markov/stratified_markov1_FIXED_W2_L5000_<date>.json`.
- BHPS counterpart: `results/trajectory_tda_bhps/stratified_markov/stratified_markov1_FIXED_W2_L5000_<date>.json`. (The BHPS checkpoint has $k = 8$ regimes per P01-A; verify the regime-label artefact was not also broken for BHPS.)
- Updated §3.2 ladder definition and §4.2.3 Table 2.
- Vault entry: `[RESULT]` log + (depending on outcome) a `[DECISION]` lock.

### 4.6 Verification

- The stratified Markov-1 rung is a defined level in §3.2 of v2.
- Table 2 contains a row for it.
- §5.3 limitations no longer contain the "circular dependency" framing.
- The reviewer's "regime-stratified surrogate test is feasible and should be reported" is satisfied verbatim.

---

## 5. ISSUE H3 — Replay drift: 11.5% non-reproducibility of $W_2$

### 5.1 Reviewer claim

> "Section §4.2.1 explicitly discloses that a deterministic replay of the stored $W_2$ results does not reproduce the archived values (H₀: 12.6766 stored vs 11.2172 replay). […] For JRSS-B, a methods paper with non-reproducible core numerical results is a major problem. The 11.5% difference between stored and replay values for the primary test statistic may or may not change the $p = 0.002$ finding (depending on the shape of the null-null distribution), but this cannot be verified without a full rerun. […] It should not be a limitation at all in a submitted methods paper — the computations should be numerically reproducible from the stated inputs."

### 5.2 Current state

- **§4.2.1:** explicitly documents the drift: H₀ obs-null mean 12.6766 stored vs 11.2172 replay, p = 0.000 stored vs 0.058 replay.
- **Vault Computational-Log 2026-04-07:** the audit conclusion is that "the stored P01 trajectory null-battery Wasserstein values should be treated as W2-era outputs. The remaining mismatch is exact code/environment provenance drift."
- **CONVENTIONS:** "NEVER silently replace archived P01 Wasserstein null-battery values if recomputing." This rule was set to prevent us from overwriting the historical-record JSON, but for a methods paper the recomputed values must become the headline.

### 5.3 Classification

**Computation + prose.** The reproducibility gap can be closed by re-running the entire battery under a **frozen, citable environment** (locked Python version, locked package versions in a `pyproject.toml` snapshot or `uv.lock`) and treating that re-run as the canonical numerical source for v2.

### 5.4 Strategy

1. **Freeze the environment.** Capture the exact `uv.lock` (or equivalent) at the start of the rerun. Pin Python 3.13.X (specific patch version), gudhi version, ripser version, scikit-learn version (resolves the sklearn 1.8.0 / 1.3.2 mismatch that broke the stratified Markov run). Commit the lockfile to the paper repo so the rerun is provably reproducible from the stated inputs.
2. **Re-run the entire null battery from scratch under the frozen environment.** This subsumes the matched-$L$ rerun (§1) and the stratified Markov rerun (§4). One unified rerun, one frozen lockfile, one set of canonical results.
3. **Deterministic seed propagation.** The current `run_wasserstein_battery.py` uses seed = 42 at the top level; verify that every downstream RNG (maxmin landmark selection, surrogate generation, null-null pair sampling) is seeded deterministically from the master seed. Any unseeded RNG is the most likely cause of the drift. Audit `permutation_nulls.py`, `trajectory_ph.py`, and the script wrapper for unseeded `np.random.default_rng()` calls.
4. **Two-machine reproducibility check.** Run the same locked-environment script on two machines (e.g., the local i7 and a clean cloud VM with the same lockfile). If the results match bit-for-bit, declare the pipeline reproducible. If they differ, the cause is platform-specific numerical determinism (e.g., BLAS implementation differences); document and pin BLAS via `MKL_NUM_THREADS=1, OMP_NUM_THREADS=1` or equivalent.
5. **Replace §4.2.1 entirely.** The new §4.2.1 reads: "All $W_2$ results in this section are reproducible from the data and the locked environment specified in `papers/P01-B-JRSSB/repo/uv.lock`. Two independent runs on different machines yielded identical numerical values. The earlier 11.5% drift documented in the project change log was caused by [whatever the audit identifies — likely sklearn version + unseeded landmark RNG], both of which are now pinned."
6. **Move the legacy provenance discussion to the supplement** as a project-history note, not a methods paper limitation. Cite it briefly in §5.3 limitations only as "an earlier version of the pipeline produced numerically different values; we report only the locked-environment results here."

### 5.5 Artefacts to produce

- `papers/P01-B-JRSSB/repo/uv.lock` (or equivalent dependency snapshot).
- Two independent results files from two machines, with a checksum-comparison note: `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_locked_<machine>_<date>.json`.
- Updated §4.2.1 (no longer a "replay drift" disclosure — now a reproducibility statement).
- Vault entry: `[DECISION]` log + `[PIPELINE]` log entry to Pipeline-Overview.md.

### 5.6 Verification

- §4.2.1 contains no instance of "drift", "discrepancy", or "may not exactly reproduce".
- The locked environment is referenced and the lockfile is in the repo.
- A reviewer could in principle reproduce the headline numbers from the stated inputs alone.

---

## 6. ISSUE H4 — BHPS label-shuffle and cohort-shuffle reject ($p \approx 0.03$): negative controls fail

### 6.1 Reviewer claim

> "The label shuffle is designed to be a negative control — it should produce $p \approx 0.5$ under the null. A value of $p = 0.036$ means the test falsely rejects a null that is designed to be true. There are three possible explanations: (a) the BHPS point cloud has a geometry such that even random state relabelling changes Euclidean distances between trajectory embeddings, (b) the $W_2$ computation at $L = 2{,}000$ landmarks has higher variance in the smaller BHPS sample, inflating rejection rates for all tests, or (c) the permutation $p$-value itself is miscalibrated. […] Crucially, if explanation (b) holds, the same variance inflation would affect all BHPS Markov tests, and the BHPS Markov-1 rejection cannot be interpreted cleanly."

### 6.2 Current state

- **Table 2:** BHPS label-shuffle H₀ $p = 0.036$, cohort-shuffle H₀ $p = 0.034$.
- **§4.2.3 paragraph after Table 2:** offers a post-hoc interpretation ("the older, longer panel is more topologically sensitive even under assignment-preserving perturbations") that is not tested.
- **CONVENTIONS rule:** "NEVER treat BHPS label-shuffle and cohort-shuffle as assumed negative controls in P01-B §4." The vault has a permanent note `02-Notes/Permanent/BHPS-H0-sensitive-to-assignment-preserving-shuffles.md` documenting the empirical finding. But the reviewer's question is sharper: **why** does BHPS produce small p-values for the negative control? The vault note records the *finding* but does not adjudicate between the three causal hypotheses the reviewer raises.

### 6.3 Classification

**Both.** Three diagnostic computations are needed to discriminate between (a), (b), and (c); plus prose updates in §4.2.3 and §5.3.

### 6.4 Strategy

1. **Discriminate between (a), (b), (c) with three targeted computations.**

   **(a) Geometry hypothesis — does state relabelling change Euclidean distances between trajectory embeddings?**
   - Compute pairwise embedding-vector $\ell^2$ distances on observed BHPS embedding ($n = 8{,}509$) and on a single label-shuffled surrogate.
   - If the two pairwise-distance distributions are nearly identical (KS test $p > 0.5$), then label shuffling does *not* materially change embedding geometry, and (a) is ruled out.
   - If they differ, the n-gram + PCA embedding is sensitive to label permutation (e.g., because some n-gram bigrams become near-impossible under shuffle and the PCA basis no longer covers the surrogate well), and (a) is confirmed. Likely cause: PCA loadings frozen on observed data; surrogates with a different state-frequency profile project onto a basis that no longer captures their variance.

   **(b) Variance inflation hypothesis — is the BHPS $W_2$ null-null distribution wider than USoc's relative to the obs-null?**
   - Compute the coefficient of variation $\mathrm{CV} = \mathrm{SD}(W_{\mathrm{null,null}}) / \mathrm{Mean}(W_{\mathrm{null,null}})$ for label-shuffle on both USoc and BHPS at the current $L = 2{,}000$.
   - If BHPS CV is much larger (say > 50% larger than USoc CV), variance inflation is a real candidate. Then re-run BHPS label-shuffle at $L = 5{,}000$ (matching ISSUE C1) to test whether the rejection persists at higher landmark count.
   - If the rejection disappears at $L = 5{,}000$, hypothesis (b) is confirmed. Document and report.
   - If it persists at $L = 5{,}000$, (b) is partially ruled out and (a) or (c) become more plausible.

   **(c) p-value miscalibration hypothesis — is the permutation reference distribution well-formed?**
   - Compute a "double-null" diagnostic: pick two random label-shuffled surrogates as the "observed" and run the full label-shuffle test on the resulting comparison. The p-value should be uniformly distributed on (0, 1) across many such double-null draws. Run 100 double-null trials; KS-test the resulting p-value distribution against uniform.
   - If the p-value distribution is uniform, the test is calibrated and (c) is ruled out.
   - If the p-value distribution is biased (e.g., shifted toward small values), the test is mis-calibrated for the BHPS sample and the BHPS Markov-1 rejection is suspect.

2. **Report the diagnostic results in §4.2.3** with a small table showing the three diagnostics and which hypothesis each rules in / out. This replaces the post-hoc "older, longer panel is more topologically sensitive" paragraph with a tested explanation.

3. **Action conditional on the diagnostic outcome:**
   - If (a) is the cause (PCA basis insensitive to surrogate state-distribution), the methodological fix is to refit PCA per surrogate or use a permutation-invariant embedding. This is a substantial methods change. **Recommendation:** if (a) is the cause, document it as a **calibrated nuisance**: the BHPS Markov-1 rejection is genuine (because Markov surrogates also use the frozen PCA basis), but the rejection is conditional on the chosen embedding pipeline. Note in §5.3 that frozen-PCA embeddings can sensitise small-sample diagnostics.
   - If (b) is the cause, the matched-$L$ rerun (§1) closes the issue: report the $L = 5{,}000$ BHPS results in Table 2.
   - If (c) is the cause, the permutation infrastructure needs revisiting — likely candidate is the obs-null vs null-null comparison's reference for small samples. May require a parametric calibration adjustment or a higher $B$.

4. **Update CONVENTIONS** with whichever explanation is supported, and update the vault note `02-Notes/Permanent/BHPS-H0-sensitive-to-assignment-preserving-shuffles.md` accordingly.

### 6.5 Artefacts to produce

- `results/trajectory_tda_bhps/diagnostics/label_shuffle_geometry_check_<date>.json` — KS test of pairwise distance distributions.
- `results/trajectory_tda_bhps/diagnostics/label_shuffle_variance_check_<date>.json` — CV statistics + L = 5000 rerun.
- `results/trajectory_tda_bhps/diagnostics/label_shuffle_pvalue_calibration_<date>.json` — 100 double-null p-values.
- New supplement subsection "Diagnostic of BHPS negative-control sensitivity" (~ 350 words).
- Updated §4.2.3 paragraph after Table 2.

### 6.6 Verification

- §4.2.3 contains a tested explanation for the BHPS small-p negative-control result, not a post-hoc one.
- The reviewer's three hypotheses are explicitly addressed (one ruled in, two ruled out, or whatever the actual data shows).
- §5.3 honestly reports any residual concern about BHPS Markov-1 interpretation following from the diagnostic.

---

## 7. ISSUE M1 — Persistence landscape $L^2$ committed to in §3.3 but absent from results tables

### 7.1 Reviewer claim

> "Section §3.3 now defines the persistence landscape $L^2$ distance […] and correctly states its Lipschitz stability constant of 1. The paper commits to reporting landscape $L^2$ distances 'as a supplementary comparison whenever Wasserstein tests are reported.' However, Tables 1–5 in §4 do not contain a single landscape $L^2$ value. The commitment in §3.3 is not fulfilled in §4."

### 7.2 Current state

- **§3.3:** "We report landscape $L^2$ distances as a supplementary comparison whenever Wasserstein tests are reported." — explicit commitment.
- **Tables 1, 2, 3, 4, 5:** no landscape $L^2$ values anywhere.
- **CONVENTIONS rule:** landscape $L^2$ is **mandatory** as a complementary metric. The current draft technically violates this rule by promising and then omitting.
- **Code:** `vectorisation.py:28` implements `persistence_landscape()`. Never invoked in P01-B's null battery.

### 7.3 Classification

**Both** — landscape $L^2$ needs to be computed for the full null battery AND the prose / tables updated.

### 7.4 Strategy [P01-A SHARED in part]

1. **Compute landscape $L^2$ distances for the same null battery as $W_2$**, on the matched-$L$ rerun (ISSUE C1). For each null and each diagram dimension:
   - Compute landscape representations using `persistence_landscape(ph, dim, k_max=5, n_points=200)`.
   - Compute pairwise $L^2$ distances on the (5 × 200)-dimensional landscape vectors using `np.linalg.norm(L1 - L2)`.
   - Report mean obs-null and null-null landscape $L^2$, plus the permutation p-value via the same null-null pair sampling as $W_2$.
2. **Add columns to Table 1 and Table 2.** Table 1 (total persistence) gets a "landscape $L^2$" column. Table 2 ($W_2$) gets a parallel "landscape $L^2$" column for both H₀ and H₁ on both checkpoints.
3. **Add a sub-paragraph in §4.2.3** discussing the landscape $L^2$ vs $W_2$ comparison: when they agree, conclusions are robust; when they disagree, that itself is informative (landscape representations smooth out sub-resolution discrepancies that $W_2$ detects).
4. **Sensitivity table in supplement** for landscape resolution: $k\_max \in \{3, 5, 10\}$ and $n\_points \in \{100, 200, 500\}$ at the Markov-1 rung only. Confirms the landscape $L^2$ p-value is stable over reasonable resolution choices.
5. **Don't use landscape for the survey-design tests in §4.3.** The pool-draw and spanning-individual tests use a different test statistic (block ratio, Betti at $\varepsilon^*$); the landscape commitment from §3.3 is specifically a *Wasserstein companion*. Be explicit about this in the §3.3 commitment so the reviewer's "absent from all results tables" criticism cannot be reraised about §4.3 / §4.4.

### 7.5 Artefacts to produce

- `results/trajectory_tda_integration/post_audit/04_nulls_landscape_L2_L5000_<date>.json`.
- `results/trajectory_tda_bhps/post_audit/04_nulls_landscape_L2_L5000_<date>.json`.
- Stratified-Markov landscape $L^2$ for the new rung.
- Supplement table for landscape resolution sensitivity.
- Updated Tables 1 and 2 in §4.2.

### 7.6 Verification

- Every $W_2$ value in §4.2 has a paired landscape $L^2$ value.
- The §3.3 commitment is fulfilled in §4.2.
- CONVENTIONS landscape rule is satisfied.

---

## 8. ISSUE M2 — Filtration threshold not stated; inherited from companion but unjustified

### 8.1 Reviewer claim

> "The notation section correctly defines the Vietoris–Rips filtration $\{K_\varepsilon(Y)\}_{\varepsilon \geq 0}$. However, the key computational parameter — the filtration threshold at which computation terminates — is still not explicitly stated in this paper. The JRSS-A companion used the 75th percentile of pairwise distances; this paper inherits the same pipeline without justifying or even restating the threshold choice. For a methods paper targeting JRSS-B, where the computational procedure is the contribution, the filtration truncation criterion requires a principled justification."

### 8.2 Current state

- **§3.1:** defines the VR filtration but does not state the truncation threshold.
- **§4.1:** "VR persistent homology is computed using Ripser (Bauer 2021) with maxmin landmark selection" — no threshold specified.
- **The 75th-percentile choice is inherited from `run_wasserstein_battery.py` /  `trajectory_ph.py`** but never justified anywhere in the codebase.

### 8.3 Classification

**Both** — needs the threshold-sensitivity sweep from P01-A H6 AND a methods-paper justification paragraph specific to JRSS-B framing.

### 8.4 Strategy [P01-A SHARED for the computation; P01-B-specific framing]

1. **Run the threshold sensitivity sweep** at three thresholds (50th, 75th, 90th percentile of pairwise distances), $L = 5{,}000$, $n\_perms = 50$ at the Markov-1 rung. Report total persistence, $W_2$ p-value, and landscape $L^2$ p-value at each threshold.
2. **Estimate intrinsic dimension** of the PCA-20D point cloud (Levina-Bickel MLE + Facco et al. two-NN). Report a single $\hat d$.
3. **Methods paper framing for §3.1:** the JRSS-B framing should be more thorough than P01-A's. Add a sub-paragraph in §3.1 (after the VR filtration definition) titled "Truncation of the filtration":
   - Definition: the practical filtration is $\{K_\varepsilon(Y)\}_{\varepsilon \in [0, \varepsilon_{\max}]}$ with $\varepsilon_{\max}$ chosen at the $q$-th percentile of pairwise distances.
   - Default: $q = 0.75$.
   - Justification: appeal to the elbow heuristic in cumulative total persistence (Carlsson 2009), the intrinsic-dimension estimate, the maxmin landmark-set diameter, and the empirical stability of headline p-values across $q \in \{0.50, 0.75, 0.90\}$.
   - State the $\varepsilon_{\max}$ in absolute units (PCA-20D distance) for reproducibility.
   - Discuss the trade-off: lower $q$ shortens computation but may suppress long-lived features; higher $q$ admits late-merging components at the cost of computation and may embed noise from concentration of distances in high dimension.
4. **Add the threshold sensitivity table to the supplement** as new §S2.
5. **Don't make a different threshold decision than P01-A.** Both papers must use the same $\varepsilon_{\max}$ at the same $q$. CONVENTIONS will be updated accordingly.

### 8.5 Artefacts to produce

- `results/trajectory_tda_robustness/threshold_sensitivity/ph_thresh_{p50,p75,p90}_L5000_<date>.json`.
- `results/trajectory_tda_robustness/intrinsic_dimension/id_estimates_<date>.json`.
- New §3.1 sub-paragraph "Truncation of the filtration".
- Supplement §S2 — threshold sensitivity.
- CONVENTIONS update locking the choice.

### 8.6 Verification

- §3.1 reports the threshold as a percentile *and* an absolute distance, with three justifications (elbow, intrinsic dimension, p-value stability).
- The supplement contains a sensitivity table that a reviewer can verify.
- A reader who disagrees with the choice can see the consequences at 50% and 90%.

---

## 9. ISSUE M3 — Kneepoint detection algorithm for $\varepsilon^*$ unspecified

### 9.1 Reviewer claim

> "The canonical scale $\varepsilon^*$ (chosen at the 'knee of the per-year Betti descent curve') is referenced in the spanning-individual decomposition but the kneepoint detection algorithm is not specified. Knee detection is notoriously sensitive to the scaling of the axes and the algorithm used (Kneedle, curvature-based, etc.); a JRSS-B methods paper should either specify the algorithm or show robustness to its choice."

### 9.2 Current state

- **§3.4.2:** "Compare the Betti-$q$ curve at canonical scale $\varepsilon^*$ (chosen at the knee of the per-year Betti descent curve)."
- **§4.3.2 Table 4:** uses $\varepsilon^* = 0.70$ — value stated, derivation not.
- **`results/trajectory_tda_zigzag/sensitivity_2d/knee_analysis.json`:** reports per-year knees with median = 0.54, mean = 0.51, range 0.05–0.83. Five years (1991, 2003, 2005, 2011, 2019) give degenerate knees ($\varepsilon = 0.05$), which the run_zigzag_era_robustness.py script explicitly excludes (`v > 0.1` filter). This means **the actual algorithm is implicit and undocumented in the paper**: take the per-year knees, exclude degenerate ones, take the median for the relevant era. The 0.70 value approximately matches the post-2010 USoc median (USoc median of non-degenerate knees ≈ 0.65–0.74 depending on year subset).
- **The algorithm itself isn't named** anywhere in the codebase or paper. Inspection of the per-year knee values (0.05 → 0.83) suggests a discrete grid scan over precomputed values rather than a continuous knee-finder like Kneedle.

### 9.3 Classification

**Both** — needs the algorithm specification AND a robustness analysis to alternative knee choices.

### 9.4 Strategy

1. **Audit and name the actual algorithm in use.** Inspect `trajectory_tda/scripts/spanning_pipeline.py` and the knee_analysis.json provenance script (`trajectory_tda/scripts/run_zigzag_sensitivity.py` is the likely source). Determine the operational definition: e.g., "for each year $t$, compute $\beta_0(\varepsilon; X_t)$ on a grid $\varepsilon \in \{0.05, 0.10, \ldots, 1.00\}$; identify the smallest $\varepsilon$ such that $\beta_0(\varepsilon; X_t)$ has decreased by ≥ 95% from its maximum; report this as the knee. Exclude degenerate cases where the decrease is achieved at the smallest grid value." Verify against the 0.05 degenerate values in knee_analysis.json.
2. **Document the algorithm formally in §3.4.2.** Provide pseudocode (~ 5 lines) and define the degeneracy criterion explicitly.
3. **Document the per-era aggregation rule.** The spanning-individual analysis uses a single $\varepsilon^*$ (= 0.70) across all USoc years 2009–2015. Make explicit: this is the median of non-degenerate USoc-era knees rounded to the nearest 0.05 grid point. Verify against the JSON file; if 0.70 cannot be derived from the documented rule, identify the discrepancy and decide what to do.
4. **Robustness analysis.** Re-run the spanning-individual Betti comparison (Table 4) at three alternative $\varepsilon^*$ values:
   - $\varepsilon^* = 0.54$ (the median across all years, including BHPS).
   - $\varepsilon^* = 0.65$ (a slightly lower USoc-era choice).
   - $\varepsilon^* = 0.80$ (a slightly higher choice).
   - Report the spanning-only and newcomer Betti-0 means at each $\varepsilon^*$ in a supplement sensitivity table.
   - If the qualitative conclusion (newcomers higher than spanning) holds at all three, the result is robust. If not, the conclusion is contingent and §4.3.2 must say so.
5. **Replace single-scale Betti ratio with full-curve summary.** The reviewer's separate concern (§3.4.2 sub-bullet 2 in the original review): "A ratio of Betti numbers at a single $\varepsilon$ is sensitive to that choice and discards the persistence information available across the full filtration. A more robust version would compare the full AUC of the Betti-0 curve, or use $W_2(D_0(X_t^{\mathrm{new}}), D_0(X_t^*))$ directly." This is addressed by:
   - Adding an AUC version of the spanning ratio: $\mathrm{BR}^{\mathrm{span,AUC}} = \mathrm{AUC}(\beta_0(\cdot; X_t^{\mathrm{new}})) / \mathrm{AUC}(\beta_0(\cdot; X_t^*))$ over the full filtration $[0, \varepsilon_{\max}]$.
   - Adding a $W_2$ version: $W_2(D_0(X_t^{\mathrm{new}}), D_0(X_t^*))$ at matched sample sizes.
   - Reporting all three (single-$\varepsilon$ ratio, AUC ratio, $W_2$) in Table 4. The conclusion should be robust across all three; if it is, the spanning-individual decomposition is more credible. If not, the paper has to qualify the single-$\varepsilon$ result.

### 9.5 Artefacts to produce

- `results/trajectory_tda_spanning/knee_robustness/spanning_betti_eps_{054,065,070,080}_<date>.json`.
- `results/trajectory_tda_spanning/spanning_full_curve/spanning_AUC_W2_<date>.json`.
- Updated §3.4.2 with formal algorithm specification.
- Updated Table 4 with three test statistics (single-$\varepsilon$, AUC, $W_2$).
- Supplement subsection — "Knee detection algorithm and $\varepsilon^*$ robustness".

### 9.6 Verification

- §3.4.2 names the knee detection algorithm and gives pseudocode.
- The choice of $\varepsilon^* = 0.70$ is justified by an explicit derivation rule.
- The headline "newcomers have elevated Betti-0" claim is shown to hold at three alternative $\varepsilon^*$ values *and* under two alternative summary statistics.

---

## 10. ISSUE M4 — Spanning-individual parallel-trends assumption not tested for demographic confounds

### 10.1 Reviewer claim

> "The spanning-individual test shows that spanning individuals maintain BHPS-like topology, but this is consistent with the parallel-trends assumption only if spanning individuals were exposed to the same post-2008 labour market conditions as newcomers. If spanning individuals are systematically older, more stably employed, and less exposed to post-GFC labour market disruption — which is plausible for a longitudinal panel's continuing sample — the null result for spanning individuals does not rule out that newcomers' topology reflects genuine economic change rather than pure frame expansion."

### 10.2 Current state

- **§3.4.2 / §4.3.2:** the parallel-trends analogy is invoked but the assumption is never tested. Spanning individuals are assumed to face the same post-2008 labour market as newcomers, but no demographic balance check is reported.
- **Vault knowledge:** spanning individuals are by construction those present in *both* eras, which means they were aged 16+ in 1991. By 2009 they are aged 34+; by 2015 (the end of the spanning analysis window in Table 4) they are aged 40+. USoc newcomers can be aged 16+ in 2009. So the demographic profiles **are** systematically different.

### 10.3 Classification

**Both** — needs a demographic balance test AND prose updates / a new sub-section.

### 10.4 Strategy

1. **Demographic balance table.** For the 2009–2015 window used in Table 4, compute:
   - Age distribution: mean ± SD, percent under 30, percent over 50 — for spanning individuals vs USoc newcomers.
   - Sex ratio.
   - Education proxy if available (e.g., highest qualification at first observation).
   - Initial employment status at first USoc observation (employed / unemployed / inactive).
   - Initial income band.
   - Birth cohort distribution.
2. **Report the table as new Table 4a.** Columns: spanning $n$, spanning value, newcomer $n$, newcomer value, standardised mean difference, $t$- or $\chi^2$-test p-value with BH-FDR correction.
3. **If spanning individuals are systematically older / more employed / higher-income**, the parallel-trends assumption needs to be defended. Two options:
   - **(a) Demographic-matched subset.** Construct a propensity-score or coarsened-exact-matched subset of spanning individuals matched to newcomers on age, sex, initial employment, initial income (matched at first USoc observation). Re-run the Table 4 spanning-individual Betti comparison on the matched subset. If the conclusion (spanning ≈ BHPS, newcomer > BHPS) holds on the matched subset, the parallel-trends concern is empirically defused. If the conclusion flips, the original Table 4 result was confounded by demographics and the methodological contribution must be reframed.
   - **(b) Age-stratified comparison.** Restrict both spanning and newcomer subsets to a common age band (e.g., 30–55 in the year of observation). Repeat Betti comparison.
   - **Recommended: do both** — they are mutually corroborating and add only modest computational cost.
4. **Update §3.4.2 to add an "Identification check" sub-section** describing the demographic balance test as a *required* part of the spanning-individual decomposition. This generalises the methods paper claim: it is not just that the decomposition exists, but that it must be paired with a balance check before the parallel-trends conclusion is drawn.
5. **Update §4.3.2 prose** to report the balance result and the matched subset result. If the conclusion changes, update §4.4 and §6 conclusion accordingly.
6. **Update §5.2 practitioner guidance** to add a sixth decision point: "Demographic balance check. Before accepting a spanning-individual null result as evidence of frame expansion, verify that spanning and newcomer subsets are comparable on demographic characteristics relevant to the substantive question. Report a balance table and a matched-subset rerun."

### 10.5 Artefacts to produce

- `results/trajectory_tda_spanning/identification/demographic_balance_<date>.json`.
- `results/trajectory_tda_spanning/identification/matched_subset_betti_<date>.json`.
- `results/trajectory_tda_spanning/identification/age_stratified_betti_<date>.json`.
- New Table 4a in §4.3.2.
- Updated §3.4.2 (identification check) and §5.2 (practitioner guidance).

### 10.6 Verification

- §4.3.2 explicitly tests the parallel-trends assumption rather than asserting it.
- The matched-subset result is reported (whether or not it matches the original).
- §5.2 tells future practitioners to do this balance check as part of the toolkit.

---

## 11. ISSUE M5 — Laplace smoothing parameter for Markov-2 not stated; directional bias not examined

### 11.1 Reviewer claim

> "The smoothing parameter (add-$\alpha$ constant) is not stated. With only $|\mathcal{S}|^2 = 81$ cells and large $N$, this matters less than it would with a coarser data structure, but the choice should be reported explicitly. More importantly, the Laplace-smoothed Markov-2 null potentially adds persistence to the surrogate trajectories by flattening the transition distribution — which would bias the $W_2$ comparison in the same direction as is already observed for Markov-1. The direction of this bias should be examined."

### 11.2 Current state

- **§3.2 prose:** "Simulate surrogate trajectories from a second-order Markov chain […] (with Laplace smoothing for the $|\mathcal{S}|^2 = 81$ two-step conditioning cells)."
- **`permutation_nulls.py:168–234` (the actual Markov-2 implementation):** does **no Laplace smoothing**. The code uses `bigram_probs[key] = np.ones(n_states) / n_states` *only when a bigram is unseen* (`else` branch on line 195–196). For all observed bigrams, it uses raw MLE counts: `bigram_probs[key] = counts / total`. This is a **uniform-fallback** strategy, not Laplace smoothing.
- **The paper and the code are inconsistent.** The reviewer asked for the smoothing parameter; the truthful answer is "no smoothing was used; the prose is wrong."

### 11.3 Classification

**Both — and a more serious code-vs-prose problem than the reviewer realised.**

### 11.4 Strategy

1. **Decide which to fix: code or prose.** Two options:
   - **(A) Add Laplace smoothing to the code.** Replace `bigram_probs[key] = counts / total` with `bigram_probs[key] = (counts + alpha) / (total + alpha * n_states)` for some $\alpha$ (typically $\alpha = 1$). This is a 2-line change. Re-run Markov-2 nulls.
   - **(B) Update the prose to match the code.** Change §3.2 to: "Simulate surrogate trajectories from a second-order Markov chain […] with uniform-distribution fallback for the small fraction of two-step conditioning cells (out of $|\mathcal{S}|^2 = 81$) that are unobserved in the data."
   - **Recommendation: (A) with $\alpha = 1$.** Laplace smoothing is more defensible methodologically (avoids zero-probability transitions that artificially constrain surrogate trajectories) and matches the original prose intent. Cost: 1–2 hours to re-run the Markov-2 null and update Table 1 / Table 2 / supplement.
2. **Examine the directional bias.** The reviewer's secondary concern: Laplace smoothing flattens the transition distribution, which generates more diffuse surrogate trajectories and potentially more total persistence. This is the same direction of bias as the global Markov-1 null already shows. To examine:
   - Run Markov-2 with $\alpha \in \{0, 0.5, 1, 5\}$ (no smoothing, mild, standard, strong). Report total persistence and $W_2$ p-value at each $\alpha$.
   - Plot (or report) the relationship: as $\alpha$ increases, total persistence of surrogate trajectories should increase (more diffuse), and the Markov-2 obs-null $W_2$ may decrease (surrogates become less data-conditional, less able to reproduce regime-specific structure).
   - If the Markov-2 conclusion (no rejection) is stable across $\alpha$, the result is robust. If $\alpha = 0$ rejects but $\alpha = 1$ does not, the non-rejection in v1 was a smoothing artefact.
3. **Update §3.2 to state the smoothing rule explicitly.** "Laplace smoothing with $\alpha = 1$ (add-one) on the conditional probabilities $\hat P^{(2)}(s_t | s_{t-2}, s_{t-1})$, applied to all 81 conditioning cells. The choice of $\alpha = 1$ is empirically motivated by the supplement sensitivity analysis showing the rejection conclusion is stable across $\alpha \in \{0, 0.5, 1, 5\}$."
4. **Update the §S0 supplement (null specification, see ISSUE in P01-A M1)** to include the explicit Markov-2 algorithm with smoothing.

### 11.5 Artefacts to produce

- Code change: 2-line addition to `permutation_nulls.py:194` — `(counts + alpha) / (total + alpha * n_states)`.
- `results/trajectory_tda_integration/post_audit/04_nulls_markov2_smoothing_alpha{0,0.5,1,5}_L5000_<date>.json` — sensitivity sweep.
- `results/trajectory_tda_bhps/post_audit/04_nulls_markov2_smoothing_alpha1_L5000_<date>.json` — final canonical re-run.
- Updated §3.2 prose with explicit $\alpha$.
- Supplement table — Markov-2 $\alpha$ sensitivity.

### 11.6 Verification

- §3.2 states the smoothing rule and the parameter value.
- The code matches the prose.
- The supplement contains a sensitivity table that addresses the directional-bias concern.
- The reviewer's concern about smoothing parameters is addressed verbatim.

---

## 12. ISSUE L1 — H₂ and higher homology computation not justified as unnecessary

### 12.1 Reviewer claim

> "**Low.** H₂ and higher homology computation not justified as unnecessary."

### 12.2 Current state

- **§3.1:** defines the VR filtration and persistence diagram in homology degree $q$ generally, but the analysis is reported only for $q = 0$ and $q = 1$.
- **No H₂ has been computed** anywhere in the codebase.

### 12.3 Classification

**Both** — needs a single H₂ check (subsumes P01-A H4, can be reported in both papers) AND a justification paragraph.

### 12.4 Strategy [P01-A SHARED]

1. **Compute H₂ once** at $L = 2{,}000$ on the USoc embedding under `maxdim=2`. Report observed H₂ feature count, total persistence, max persistence. Run a single Markov-1 null comparison at $n\_perms = 50$ at the same $L$.
2. **Report in §3.1 of P01-B** with a single sentence: "H₂ and higher homology are not analysed here because (i) empirical computation on the trajectory embedding shows H₂ features are sparse and short-lived (max H₂ persistence = X.XX, observed H₂ total persistence = X.XX vs Markov-1 null mean = X.XX, $p_{W_2} = X.XX$, $L = 2{,}000$, $B = 50$); and (ii) higher-dimensional features in 20-dimensional VR complexes are computationally expensive without commensurate methodological return for sequential categorical data with small per-individual sample sizes." Cite Edelsbrunner & Harer (2010) for the general framework.
3. **Outcome contingency.** If H₂ unexpectedly rejects under Markov-1, the methods paper's restriction to $q \in \{0, 1\}$ is unjustified and the paper must be reframed. Pre-register: if H₂ rejects, expand the methods paper to include H₂ analysis.
4. **Don't add H₂ to the headline tables.** The Markov ladder remains a $q \in \{0, 1\}$ analysis in the headline; H₂ is a check, not a contribution.

### 12.5 Artefacts to produce

- `results/trajectory_tda_integration/h2_check/ph_H2_L2000_<date>.json`.
- `results/trajectory_tda_integration/h2_check/nulls_markov1_H2_L2000_<date>.json`.
- One sentence in §3.1 of P01-B.

### 12.6 Verification

- §3.1 contains an H₂ justification, not silent omission.
- The single sentence is supported by a result file.

---

## 13. EMBEDDED CONCERNS — issues raised inside paragraphs but not in the issues table

### 13.1 H₀ orthogonality between density-mode regimes and VR connectivity

The P01-A reviewer raised this; the P01-B reviewer did not, but P01-B inherits the same conceptual gap. Action: ensure §2.3 and §3.1 of P01-B are consistent with the H₀-as-connectivity-not-density framing being added to P01-A. **Light prose audit only**, no new computations needed beyond what P01-A produces.

### 13.2 The MMD connection in §3.3

**§3.3 final paragraph** ("Connection to MMD") is informal and connects $W_2$ to MMD without making a precise claim. The paragraph is fine as orienting context but should be verified once. The kernelised diagram representation it cites (Reininghaus et al. 2015) is the **persistence scale-space kernel**, which is genuinely related to landscape representations but not to $W_2$ directly. **Recommendation:** tighten the paragraph to say "$W_2$ and MMD with a persistence kernel are distinct but conceptually related diagram-level test statistics; we do not claim formal equivalence." This pre-empts a reviewer push.

### 13.3 Mantel test p-value in §4.3.1

Table 3 reports Mantel $r = 0.768$, $p < 10^{-6}$ for the full panel. The Mantel test is asymptotic and known to under-estimate p-values when the distance matrices have block structure — which is exactly the case here. A permutation Mantel test with $B = 10{,}000$ row-column shuffles would be the standard fix. **Action:** re-run the Mantel test with permutation, report the empirical p-value (likely still $< 10^{-3}$), and update Table 3 footnote to say "permutation Mantel test, $B = 10{,}000$." This is small (5-minute) and pre-empts a reviewer concern.

### 13.4 "Dominant post-2008 topological shift is a survey-frame artefact" claim — strength of language

§4.3.2 final paragraph and §6 conclusion both say the survey-frame interpretation is "unambiguous." The reviewer's M4 demographic-balance concern (§10 above) makes "unambiguous" too strong unless the matched-subset rerun (§10.4 step 3) confirms the conclusion. Soften to "well-supported" pending the §10 outcome; restore to "unambiguous" only if the matched-subset rerun confirms.

### 13.5 The §4.4 within-BHPS macroeconomic correlations table

Table 5 reports five very strong correlations ($|r| > 0.76$, $p < 0.001$) on $n = 18$ years. This is a small-sample analysis with high risk of spurious correlation; the BH-FDR correction is applied, but the source table for FDR is unclear (out of how many tests is the $\alpha = 0.05$ correction made?). **Action:** state in the Table 5 caption "$m = 35$ tests in the full panel of which 10 survive BH-FDR; reported correlations are the BH-FDR-significant subset within the BHPS-only re-analysis ($n = 18$ years)." Clarifies the multiple-testing accounting and pre-empts a methodological concern.

### 13.6 Embedding stability practitioner guidance (§5.2 point 1)

§5.2 point 1 advises practitioners to verify embedding stability by comparing pooled vs era-specific PCA axes. We do not currently report this check for our own data. **Action:** run the check for the BHPS+USoc embedding and report the ARI / Procrustes alignment of pooled-PCA vs era-PCA in a supplement table, then we can refer practitioners to this as a worked example.

---

## 14. Sequencing, Dependencies, and Resource Estimates

### 14.1 Dependency graph (combined with P01-A)

```
[ISSUE C1: matched-L W2]                ─┐
[ISSUE C2: abstract reconciliation]    ──┤── must complete before §4.2 / abstract / §6 rewrite
[ISSUE H2: stratified Markov-1]         ─┤
[ISSUE M5: Laplace smoothing]           ─┤
[ISSUE M1: landscape L²]                ─┘

[ISSUE H1: ground metric fix]           ── prose + small sensitivity check
[ISSUE H3: replay drift / lockfile]    ── must complete before any rerun (sets the environment for ALL reruns)
[ISSUE H4: BHPS negative-control diag] ── three small computations + prose
[ISSUE M2: filtration threshold]       ── shared sweep with P01-A
[ISSUE M3: knee algorithm]             ── prose + small robustness check
[ISSUE M4: spanning demographics]      ── prose + matched-subset rerun
[ISSUE L1: H₂ check]                   ── single computation (shared with P01-A)
[ISSUE 13.x embedded]                  ── prose + small reruns (Mantel, embedding stability)
```

### 14.2 Critical path

Two parallel critical paths:
1. **Lockfile & rerun:** ISSUE H3 (lock environment) → ISSUE C1 (matched-L W₂ rerun) + ISSUE H2 (stratified Markov rerun) + ISSUE M5 (Laplace re-implementation) + ISSUE M1 (landscape L² battery). **Estimate: 4–6 working days** (most of which is unattended compute).
2. **Decision rewrite:** ISSUE C1 outcome → ISSUE C2 abstract reconciliation → §4.2 / §6 rewrite. **Estimate: 2 working days** *after* the rerun completes.

### 14.3 Wall-clock estimates (i7 / 32 GB / no GPU per CONVENTIONS)

| Task | Estimate | Shared with P01-A? |
|---|---|---|
| Environment lockfile + two-machine reproducibility check | 1 day human + 1 day compute | yes (single fix) |
| Matched-$L$ W₂ Markov ladder (USoc + BHPS) | 8–12 h compute | yes |
| Stratified Markov-1 (USoc + BHPS) | 8–12 h compute | yes |
| Laplace smoothing $\alpha$ sensitivity sweep (4 values, USoc) | 4–6 h compute | yes |
| Landscape $L^2$ battery (USoc + BHPS) | 8–14 h compute | yes |
| Threshold sensitivity sweep | 6–10 h compute | yes |
| BHPS label-shuffle 3-hypothesis diagnostic | 4–6 h compute | no (P01-B only) |
| Spanning-individual demographic balance + matched subset | 3–5 h compute | no (P01-B only) |
| Knee robustness ($\varepsilon^* \in \{0.54, 0.65, 0.70, 0.80\}$) | 2–3 h compute | no |
| AUC and $W_2$ versions of spanning ratio | 2–3 h compute | no |
| H₂ check at L = 2000 | 10–24 h compute | yes |
| Permutation Mantel test (§13.3) | <1 h compute | no |
| Embedding stability check (§13.6) | 1–2 h compute | no |
| Ground-metric sensitivity (§3 ISSUE H1 step 4) | 1 h compute | no |
| **Total compute (mostly parallelisable)** | **~70–110 h** | |
| **Total human time** | **~10–14 working days** | |

### 14.4 Suggested execution order (combined with P01-A)

1. **Day 1 — environment.** Lock the dependency environment (ISSUE H3). Set up reproducible compute. Audit unseeded RNGs in `permutation_nulls.py` and `trajectory_ph.py`.
2. **Day 2 — bug fixes & smoothing.** Diagnose and fix the stratified-Markov regime-label bug. Implement Laplace smoothing (ISSUE M5). Push code changes; tag the repo at this commit ("v2-prep-environment-frozen").
3. **Days 3–5 — primary reruns in parallel.** Kick off (in 2–3 concurrent terminals): matched-$L$ W₂ ladder (USoc + BHPS), stratified Markov-1 (USoc + BHPS), positive-control (P01-A 10.2). All on the locked environment.
4. **Days 6–7 — secondary reruns in parallel.** Landscape $L^2$ battery, Laplace $\alpha$ sweep, threshold sensitivity, BHPS negative-control diagnostic, spanning-individual demographic balance + matched subset, knee robustness.
5. **Days 8–9 — H₂ + small computations.** H₂ check at $L = 2{,}000$ (longest single job, run unattended). Permutation Mantel, embedding stability, ground-metric sensitivity (small, ~ 4 hours total).
6. **Day 10 — outcome compilation.** Decide ISSUE C2 outcome; compile all numerical results into a single results-summary table for both papers. Make the final decision on the abstract for P01-B and §4.3 for P01-A.
7. **Days 11–13 — rewrite.** P01-A v2 and P01-B v2 in lockstep. Specific P01-B rewrites:
   - §3.1 (ground metric fix; threshold paragraph; H₂ justification).
   - §3.2 (stratified Markov-1 rung; Laplace smoothing parameter).
   - §3.3 (landscape $L^2$ commitment, MMD paragraph tightening).
   - §3.4.2 (knee algorithm; identification check).
   - §4.2.1 (replace replay-drift disclosure with reproducibility statement).
   - §4.2.3 (Tables 1 and 2 with new columns; BHPS negative-control diagnostic paragraph).
   - §4.3.2 (Table 4 with three test statistics; demographic balance Table 4a; soften "unambiguous").
   - §4.4 (clarify multiple-testing accounting).
   - §5.2 (add demographic balance practitioner guidance).
   - §5.3 (move replay-drift to a project-history note; state matched-$L$ result).
   - §6 (rewrite to match the new headline).
   - Abstract.
8. **Day 14 — internal review.** /humanizer pass. Notation cross-check against `papers/shared/notation.md`. CONVENTIONS compliance audit. Prepare v2.

---

## 15. Acceptance Criteria for v2

The v2 draft is ready to circulate (pre-submission) only when **every** item below holds.

### 15.1 Numerical correctness

- [ ] The abstract, every results table, and the conclusion cite a single $W_2$ Markov-1 USoc H₀ p-value (no "legacy" vs "post-audit" duality).
- [ ] All results in §4 are derived from a single locked-environment rerun, reproducible from the stated lockfile and seed.
- [ ] Tables 1 and 2 are at matched $L$ for total persistence and $W_2$.
- [ ] Tables 1 and 2 contain landscape $L^2$ columns matching the §3.3 commitment.
- [ ] Table 2 contains a stratified Markov-1 row.
- [ ] Markov-2 results are computed with explicit Laplace smoothing and the parameter is stated.
- [ ] Mantel test p-value in Table 3 is permutation-based.

### 15.2 Methodological completeness

- [ ] §3.1 $W_p$ formula uses the same ground metric as the implementation (recommended: $\ell^2$).
- [ ] §3.1 contains a filtration-threshold sub-paragraph (75th percentile + justification).
- [ ] §3.1 contains a one-sentence H₂ justification with a supporting result reference.
- [ ] §3.2 includes Stratified Markov-1 (Level 4b) as a defined ladder rung.
- [ ] §3.2 states the Laplace smoothing $\alpha$ explicitly.
- [ ] §3.4.2 names the knee detection algorithm with pseudocode.
- [ ] §3.4.2 includes an "Identification check" sub-section requiring demographic balance.
- [ ] §4.2.1 is a reproducibility statement, not a drift disclosure.

### 15.3 Framing fixes

- [ ] §4.2.3 BHPS negative-control paragraph cites a tested explanation, not a post-hoc one.
- [ ] §4.3.2 includes single-$\varepsilon$, AUC, and $W_2$ versions of the spanning ratio.
- [ ] §4.3.2 reports a demographic balance check and a matched-subset Betti comparison.
- [ ] §4.4 multiple-testing accounting is unambiguous.
- [ ] §6 conclusion uses the matched-$L$ headline number; "unambiguous" language about survey-frame artefact is calibrated to the matched-subset outcome.
- [ ] §5.3 limitations no longer contains the "circular dependency" framing for stratified Markov.

### 15.4 CONVENTIONS compliance

- [ ] $W_2$ used throughout — no bare "Wasserstein" without order.
- [ ] Landscape $L^2$ included as a complementary metric in every table that has $W_2$.
- [ ] Every Markov null is labelled with its order $k$.
- [ ] BHPS wave range stated explicitly wherever BHPS is mentioned.
- [ ] Random seeds reported wherever new computations are described.
- [ ] `papers/shared/notation.md` updated to lock the new ground-metric and threshold conventions.

### 15.5 Reproducibility

- [ ] Repository contains a frozen lockfile (`uv.lock` or equivalent).
- [ ] All new results files exist under `results/` with date-suffixed names.
- [ ] Each new result file is referenced from the manuscript by name (in supplement) and has a corresponding `[RESULT]` entry in the vault Computational-Log.
- [ ] Two-machine reproducibility check is on file.

---

## 16. Open questions to resolve before execution begins

1. **Ground-metric option (A) vs (B) for §3 ISSUE H1.** Recommendation: option (A) ($\ell^2$, fix the formula). Confirm with the author / co-thinker before starting the lockfile rerun, since switching the implementation is the single biggest extra-cost decision in this plan.
2. **Lockfile pinning depth.** Pin Python patch version + all top-level packages, or also pin BLAS / numerical-determinism settings? Recommendation: pin both. The 11.5% replay drift is large enough that BLAS variation is a plausible co-cause; better to over-pin than to debug platform-specific drift later.
3. **P01-A vs P01-B split for stratified Markov-1.** Same question as P01-A §13 question 3. Recommendation: results published in both, with P01-A reporting substantive outcome and P01-B reporting methodological framework.
4. **What to do if the matched-$L$ $W_2$ Markov-1 USoc p-value is borderline (0.05 ≤ p < 0.10)?** Pre-commit: if so, increase $B$ to 200 perms, $n_{\text{nullnull}} = 2000$ pairs, on USoc only, to reduce Monte Carlo noise. If still borderline, report as borderline and frame the methodological lesson conditionally ("scalar test gives $p = 1.000$; $W_2$ shifts the conclusion sharply but does not cross conventional significance — the order-of-magnitude shift is itself the methodological lesson, even when it does not produce a significance-level rejection.").
5. **Does "Laplace smoothing" with $\alpha = 1$ change the v1 Markov-2 conclusion ($p_{W_2} = 0.546$)?** Cannot know in advance. If the conclusion changes (e.g., Markov-2 becomes rejected), the entire "second-order memory accounts for the diagram structure" thesis must be reframed. This is a real outcome risk and the author should be aware before executing.
6. **Knee algorithm — formal vs operational.** Should the v2 paper present the knee algorithm as a formal contribution (with its own pseudocode and citation as a methods choice) or as a pragmatic operational rule? Recommendation: operational rule, with pointer to the supplement's robustness analysis. The methods paper's formal contributions are the Markov ladder and the survey-design diagnostics — adding a fourth contribution dilutes the framing.

---

## 17. References to add to v2 if not already cited

- **Carrière, M., Cuturi, M., & Oudot, S. (2017).** Sliced Wasserstein kernel for persistence diagrams. *ICML.* — backstop for $W_2$ with $\ell^2$ ground metric (§3.1).
- **Skraba, P., & Turner, K. (2020).** Wasserstein stability for persistence diagrams. *arXiv:2006.16824.* — stability constant for $W_p$ under $\ell^q$ ground metrics (§3.1).
- **Bubenik, P. (2020).** The persistence landscape and some of its properties. *Topological Data Analysis*, Springer. — landscape $L^2$ in current notation (§3.3).
- **Beyer, K., Goldstein, J., Ramakrishnan, R., & Shaft, U. (1999).** When is "nearest neighbor" meaningful? *ICDT.* — curse-of-dimensionality justification for filtration threshold (§3.1).
- **Facco, E., d'Errico, M., Rodriguez, A., & Laio, A. (2017).** Estimating the intrinsic dimension of datasets. *Scientific Reports* 7. — intrinsic dimension estimate (§3.1).
- **Levina, E., & Bickel, P. J. (2004).** Maximum likelihood estimation of intrinsic dimension. *NeurIPS* 17. — same as above.
- **Satopaa, V., Albrecht, J., Irwin, D., & Raghavan, B. (2011).** Finding a "kneedle" in a haystack: detecting knee points in system behavior. *ICDCS Workshops.* — knee detection algorithm reference (§3.4.2).
- **King, G., & Nielsen, R. (2019).** Why propensity scores should not be used for matching. *Political Analysis* 27. — informs the choice of coarsened-exact-matching over PSM in §10 step 3 if matching is needed.

---

*End of plan. No code or revisions executed; this document is the input to the next planning conversation, not the output.*
