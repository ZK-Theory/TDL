# TDA-Research Conventions

> **Purpose:** Codified methodological decisions and constraints. Every rule
> has a rationale — this is what steers LLM outputs away from generic
> responses toward project-specific correctness. Updated incrementally as
> decisions are made; never edited lightly.
>
> **For LLM context:** Load this file at the start of any session involving
> TDA paper work, computational decisions, or methodology discussion.

---

## Research Assurance (locked 2026-06-02)

**Rule.** For any task touching the six assurance lanes — Topology, Stochastic/Null
Model, Statistical/Panel, Representation, Output/Provenance, Paper Claim — the
`research-assurance-triage` skill plus the relevant lane skill is the standard
pre-dispatch and review path, and passing software tests is **never** sufficient
on its own. Machine-checkable claims get a deterministic enforcement artifact
(contract / hook / schema / validation command) or an explicit note saying why not.

**Rationale.** The project's largest recurring cost is mathematically wrong results
that pass every software test (e.g. a permutation p-value with the wrong
denominator; a null invariant to the operation it tests). The lane skills supply
the judgment; the contracts/hooks supply the mechanical check.

**Mechanics.** Lane skills live in `.agents/skills/` (Codex authoring source) and
are mirrored to `.claude/skills/` by `tools/sync_agent_skills.py` (pre-commit Gate
0). Runtime-specific skills (`apm-communication`) and the APM guides diverge by
terminology and are presence-checked, not byte-mirrored. Layer-3 enforcement:
`apm_task_prompt_check.py`, `results-no-overwrite.sh`, and the `contracts/`
framework (`contract_binding_check.py`). See the 2026-06-02 `[DECISION]` in
`04-Methods/Computational-Log.md`.

---

## Authorship

All papers in this programme are single-authored:

- **Author:** Stephen Dorman
- **Affiliation:** The Open University, UK
- **Confirmed:** 2026-04-07

This applies to P01-A, P01-B, P04, and all subsequent programme papers unless explicitly noted otherwise. Credit statement, cover letters, and submission accounts are all single-author. No statistician collaborator is being added. This resolves the Phase 0 authorship BLOCKING item.

---

## Programme Structure (as of 2026-04-07)

Three journal-targeted papers replacing the original four technique-first papers:

| ID | Working title | Target | arXiv | Source |
|---|---|---|---|---|
| **P01-A** | The Geometry of UK Career Inequality | JRSS-A | stat.AP | P01 applied + P02 |
| **P01-B** | Structured Hypothesis Testing for PH of Longitudinal Social Data | JRSS-B | stat.ME | P01 methods + P03 toolkit |
| **P04** | Multi-Parameter PH Reveals Income-Stratified Career Topology | AoAS | stat.ME + math.AT | P04 reframed |

**Submission sequence:** P01-A + P01-B to JRSS + arXiv simultaneously. P04 to AoAS after P01-A/B arXiv posting. Do not wait for JRSS acceptance (12–18 months).

**Archived:** P01-Core-VR-PH (→ P01-A + P01-B), P02-Mapper (→ P01-A), P03-Zigzag (→ P01-B).

---

## Always

- **ALWAYS author math-correctness contracts upstream of the implementing
  agent** — Planner during Plan authoring, Manager during pre-dispatch
  coverage check, User at pre-registration time, or a dedicated pre-Worker
  extraction step. Never let the agent that will write the code also author
  the contract that constrains it: the same prose-misreading that produces
  wrong code would produce a wrong contract. The contract is reviewed before
  it lands so the prose-to-YAML translation can be audited. See
  `C:\Users\steph\TDL\contracts\README.md` for the four locked contract
  kinds (formula, schema, invariant, output_validation), the six authorship
  triggers, and the binding convention. Locked 2026-05-27 after T1.36's
  p-value denominator and LM schema-truncation defects (~36+ hours of
  invalidated compute) demonstrated that unit tests + smoke canaries +
  Manager review against those signals are insufficient to catch
  mathematical drift between prose specification and implementation.

- **ALWAYS enforce on VALUE and TYPE, not key presence — and make contract
  literals machine-equality-checkable.** A binding test / validator that only
  checks that a key exists (or that a count is "positive", or that a structure
  is well-formed) is not enforcement: malformed or wrong data passes. Assert the
  exact type and value the contract specifies (e.g. a coefficient `level` is
  `str` or `null`, never `{}`; the fitted sample is exactly `n=711`, not just
  `>0`; the calibration gate evaluates a pinned tolerance, not an undefined
  "approximately"). Correspondingly, the PRODUCER must emit contract-pinned
  fields as exact literal tokens (e.g. `family = "quasibinomial"`, the precise
  `ipw_trimming` string), never free-form prose, so the validator can
  equality-check them. A literal that lives only in a contract *description* is
  documentation, not a guard. Locked 2026-06-03c after a CodeRabbit batch on
  PR #31 showed a cluster of defects all slipping past presence-only checks: a
  false `735/353` sample count in contract prose, `level: {}` instead of `null`
  in the headline JSON, prose `params` instead of literal tokens, and an
  "any-positive" sample check instead of the pinned `711/342`. See
  [[Enforcement-must-assert-value-not-key-presence]].

- **ALWAYS keep the contract framework in default-enforce mode with every
  invariant grounded.** Every `formula.invariants[]` item carries exactly one of
  `expression` (a machine-checkable relationship) XOR `enforced_by` (a named
  binding-test assertion, for genuinely procedural claims) — never neither,
  never both. Every `binding.must_assert` lettered clause `(a)…` has a matching
  negative case in the bound test (claim↔assertion coverage), and every schema
  `required_key` type/bound is asserted, not merely present. `contract_binding_check.py`
  runs the hardening gates (1b qualitative-language lint, 1c invariant-enforcement
  completeness, 2b claim↔assertion coverage, gate-4 type/bound) in **enforce mode
  by default** — commits are blocked on staged-file violations. Provenance /
  output-validation contracts grandfather pre-existing immutable result JSONs
  ONLY via explicit `legacy_exempt` entries and NEVER by backfilling inferred
  provenance into historical files; the `--all-jsons` audit of grandfathered
  legacy files stays informational, not commit-blocking. Locked 2026-06-04
  (Stage-0 contract-framework-hardening workstream).

- **ALWAYS fail fast on misalignment, missing lookups, and oversized groups —
  never silently truncate, coerce, or drop.** Silent data loss is a correctness
  defect even when nothing errors: `zip(rows, cols)` truncates to the shorter
  input (add a length check + raise); a `.SD[1:2]` / "first two per group" keeps
  an arbitrary subset and discards the rest (enumerate explicitly or restrict
  and report the exclusion); a missing lookup term returning `NA` propagates
  into an acceptance gate and quietly flips it (guard: stop or set the flag
  `FALSE` explicitly); `NULL`/empty serialized as `{}` corrupts the schema
  (normalise to the contracted form). Corollary — **superseded artifacts must
  not linger in an active dispatch glob, and enforcement tests must exercise
  (not skip) the files they guard.** When a result is corrected within a branch,
  `git rm` the superseded file rather than leaving it to be special-cased, and
  never write a test that skips the exact stale files it is meant to catch.
  Locked 2026-06-03c (same PR #31 CodeRabbit batch). See
  [[Enforcement-must-assert-value-not-key-presence]].

- **ALWAYS parallelize long-running stochastic compute to at least 4 workers,
  with checkpoint/progress reporting and an up-front wall-time estimate.**
  Bootstraps, permutation nulls, MICE-pooled refits, and per-individual / per-
  cluster batteries must be written to run on ≥ 4 parallel workers by default
  (joblib `n_jobs`, R `future` / `parallel` / `foreach`, or an explicit worker
  pool), exposed via a worker-count parameter (default ≥ 4) and a chunked
  checkpoint so a halted job resumes rather than restarts. Workers flag any job
  expected to exceed ~30 min as long-running **before** launch and state the
  expected wall time. The machine handles ≥ 4 concurrent worker jobs. Locked
  2026-06-03 after repeated overnight-scale serial runs (e.g. the T1.34 full-
  sample FOO bootstrap) were cut to a fraction by appropriate parallelization;
  serial-only long stochastic compute is a defect to be flagged in review.

- **ALWAYS persist a sample-provenance ledger and cite sample counts by
  reference, never free-typed.** Every model-fitting Task writes a
  `sample_provenance` block into its result JSON recording n at EACH filter
  stage (eligible → IPW-weighted → complete-case → fitted) plus a row-level
  (PIDP) manifest of the fitted sample, so any downstream Task reconstructs
  from the manifest rather than re-deriving. Pre-registrations and contracts
  MUST cite the fitting-stage count by reference to a produced result JSON's
  `sample_provenance.fitted` field and MUST name the stage — never transcribe
  a number from memory or an upstream stage. Locked 2026-06-03b after the
  T1.35 contract family pinned the pre-complete-case IPW-eligible counts
  (735 / 353 / 6363 / 7098) as if they were the T1.21 fitted sample, which
  actually fit on 6,995 obs / 711 multi-members / 342 clusters / 6,284
  singletons (`tier3_cross_classified_2026-05-25.json`); the divergence went
  undetected for a week because T1.21 never persisted a sample manifest to
  reconcile against. This is a recurring class — "two deterministic scripts on
  the same dataset disagree" is almost always a stage-of-measurement mismatch,
  not non-determinism. Enforcement contract + `result-provenance-review`
  judgment layer tracked in the research-assurance implementation plan.

- **ALWAYS state the Monte Carlo permutation p-value denominator as the
  number of null draws used in the test**, not the diagnostic effect-size
  pair cap. The formula is `p = (r + 1) / (n + 1)` where `n` equals
  `min(B, total_pairs)` (B is the permutation count, `total_pairs = B*(B-1)/2`
  is the number of unique null-null index pairs). For B = 1000 the minimum
  achievable p-value is `1/1001 ≈ 0.000999`, NOT `1/(n_null_pairs_cap + 1)`.
  Output JSONs MUST expose both `pvalue_null_draws` (the p-value denominator
  minus 1) and `effect_null_pairs` (the count actually used for T-ratio and
  d-perm diagnostics) for traceability. Locked 2026-05-27 by the
  `monte-carlo-permutation-p-value` contract; the corrective fix landed at
  commit `9c81311`.

- **ALWAYS use Wasserstein-2 distance for persistence diagram comparisons**
  because it is sensitive to both the position and multiplicity of topological
  features, unlike bottleneck distance which only captures the single worst
  discrepancy. This was established during null model validation for P01.

- **ALWAYS use persistence landscape L² distance as a complementary metric
  alongside Wasserstein** because it captures shape-level differences in
  persistence that single summary statistics miss. Confirmed via the `persim`
  library benchmarks.

- **ALWAYS specify the BHPS wave range explicitly** when discussing cross-era
  validation. The BHPS runs 1991–2008 (waves 1–18); Understanding Society
  begins 2009. Ambiguous wave references cause silent errors in replication.

- **ALWAYS state the Markov order k when describing null models** — "Markov
  null model" alone is ambiguous. The Markov memory ladder framework tests
  k = 1, 2, 3, ... to determine the minimal order at which topological
  structure is explained.

- **ALWAYS follow the verification protocol for Perplexity sources:**
  Perplexity surfaces → human verifies existence → Zotero entry → literature
  note → prose. No shortcuts. Perplexity confabulates quotations and
  occasionally invents plausible-sounding papers.

- **ALWAYS include both the test statistic AND the p-value** when reporting
  computational results in the vault. A p-value without context is
  uninterpretable; a test statistic without significance is incomplete.

- **ALWAYS use `--break-system-packages` when pip installing** in the
  computational environment (Python 3.13 on Windows). This is a known
  requirement of the local setup.

- **ALWAYS cross-reference new literature against the paper pipeline**
  (P01-A, P01-B, P04, FIN-01, P05–P10) when adding to the vault. Every source
  should be tagged with which papers it serves — orphan literature notes
  accumulate without this discipline.

- **ALWAYS use L = 5,000 as the canonical landmark count** for all W₂ and
  persistence landscape L² headline statistics. L = 2,000 is retired — H₁ loop
  topology is landmark-sensitive and requires L ≥ 5,000 for reliable inference
  in USoc data. Locked 2026-05-05 (APM Spec); see Computational-Log entries
  dated 2026-05-02 and 2026-05-05 for the landmark-sensitivity finding.

- **ALWAYS use external-indexing dedup for length-matched cell Rips PH.** For
  length-matched Stage-1 cells (T1.2f truncate, T1.2g first13), the observed PD
  is computed as `ripser.ripser(X[I])` where `I` is the greedy-permutation index
  set returned by `compute_greedy_dedup_count(X, tolerance=1e-10)`. Do NOT use
  the `ripser.ripser(X, n_perm=N)` shortcut — ripser's internal greedy
  permutation can select a different N-subset than the contract specifies,
  producing a non-zero H0 bottleneck deviation (~3e-8 on T1.2f truncate
  landmarks, established by the 2026-05-30 canary). Null PDs follow the same
  dedup rule per-permutation; the obs/null vertex-count asymmetry that emerges
  (observed has near-duplicate landmarks, Markov-1 surrogates do not) is a
  TRUE DATA PROPERTY and is documented in the cell's run_params
  (`dedup_strategy = "greedy-permutation-external-indexing"`,
  `dedup_tolerance = 1e-10`, plus per-PD-class `n_perm_used` and covering
  radius). Locked 2026-05-31 by Pre-reg #5 redo Outcome A; formula contract
  `length-matched-dedup-via-n-perm`. The 2026-05-29 frozen no-dedup truncate
  result is preserved as historical record but superseded for inference. The
  rejection direction is robust to both the obs/null asymmetry and the
  `compute_rips_ph` auto-thresh divergence (probes `symmetric_dedup` and
  `pinned_thresh` both preserve rejection at < 1% S/N drift).

- **ALWAYS load regime labels from `05_analysis.json["gmm_labels"]`**, never
  from a pickle-based GMM file. Cross-version sklearn pickle loads silently
  collapse all 27,280 trajectories to a single regime (regime 0) without raising
  any error. The JSON source is the only safe, version-stable route. Locked
  2026-05-02; see `sklearn-cross-version-silent-GMM-failure` permanent note.

- **ALWAYS follow the BHPS split rule when allocating content across P01-A and
  P01-B.** "How UK careers looked 1991–2008" (regime structure k=8, qualitative
  similarity) → P01-A §6. "How the methodology performs on a second dataset"
  (Wasserstein discrepancy replication, BHPS Markov-1 H₁ rejection) → P01-B §4.
  BHPS Markov-1 H₁ result (p=0.000) is a methodological replication; it belongs
  in P01-B and is only referenced briefly in P01-A as "confirmed in P01-B §4."

---

## Never

- **NEVER bypass the pre-commit contracts hook with `git commit --no-verify`
  except in a documented emergency**, and even then a follow-up
  contract-authoring or corrective commit MUST land within 24 hours. The hook
  enforces meta-schema validation, binding existence + one-to-one
  enforcement, pytest invocation of all live bindings, and JSON schema
  validation of staged output files. Bypassing it silently re-opens the gap
  the contracts framework was authored to close (T1.36 p-value denominator +
  LM schema truncation). If the hook is blocking a legitimate commit on a
  legitimate code change, the right response is to author or update the
  relevant contract, not to bypass. Locked 2026-05-27 alongside the
  framework landing (commit `bb1b0a1`).

- **NEVER author your own math-correctness contract for code you are about
  to implement.** Same blind spot, same wrong contract. Push the contract
  authorship upstream — to the Plan task, the pre-registration, the
  Manager's pre-dispatch coverage check, or a dedicated extraction agent.
  The agent that writes the code receives the contract and binds tests to
  it; it does not propose the contract content. Locked 2026-05-27.

- **NEVER cite Perplexity outputs directly** — they are leads, not sources.
  Even when Perplexity provides a DOI, verify it resolves to the claimed
  paper before adding to Zotero.

- **NEVER use total persistence as the sole topological summary statistic**
  — it cannot distinguish between many small features and few large ones,
  making it insensitive to the kind of structural differences the Markov
  memory ladder is designed to detect. This was a negative result from
  early P01 exploration.

- **NEVER assume Understanding Society and BHPS use the same variable
  coding** — even for variables that appear identical (e.g., employment
  status), the coding schemes changed at the survey transition. Always
  check the variable documentation for the specific wave.

- **NEVER run persistent homology on raw trajectory data without the
  embedding step** — the Vietoris-Rips complex requires a metric space.
  Trajectories must first be embedded (the pipeline handles this, but
  ad-hoc exploration sometimes skips it).

- **NEVER use `Array<T>` syntax in TypeScript code for the website project**
  — the ESLint config enforces `T[]`. This is a Hardening Principle example:
  the lint rule is deterministic and should be respected, not fought.

- **NEVER write $W_1$ for the P01 trajectory null-battery results.** The Phase 0
  W2 audit (2026-04-07, commit `d21da41`) confirmed all code paths
  (`vectorisation.py`, `wasserstein_null_tests.py`) default to `order=2`, and
  W1 replay is orders of magnitude away from stored values (W1 H₀: 498.64 vs
  stored 11.22). The "$W_1$" wording in the P01 v8 LaTeX manuscript is stale
  prose. Correct it to "$W_2$" during P01-B §3.3 assembly. P03 is independently
  aligned on W2. Full audit record in `papers/shared/notation.md`.
  *(BLOCKING item resolved 2026-04-07)*

- **NEVER silently replace archived P01 Wasserstein null-battery values if
  recomputing.** Code/environment drift means exact replay is imperfect (H₀
  drift ~1.5 units; H₁ drift ~0.2 units). New runs must be recorded as new
  Computational-Log entries, not silent corrections to the archived JSON.
  *(Established 2026-04-07)*

- **NEVER treat label-shuffle or cohort-shuffle p-values as negative
  controls** — in either dataset, at any landmark count. The null
  constructions in `_label_shuffle` (`permutation_nulls.py:53-64`) and
  `_cohort_shuffle` (`permutation_nulls.py:67-92`) permute rows of an
  already-computed embedding matrix; persistent homology is row-order
  invariant, so the reported p-values measure landmark-subsampling
  variance only, not a label-shuffle test. This invalidates all
  historical p-values, including the 2026-05-22 entry that previously
  occupied this slot: BHPS L=2000 label H0 p=0.036 (treated as
  asymmetry; was landmark variance), BHPS L=5000 label/cohort p in the
  range 0.5 to 0.7 (treated as clean negative control; was landmark
  variance), USoc L=5000 label/cohort p in the same range (same). A
  correct label-shuffle null must shuffle state labels at the
  person-year level BEFORE embedding (re-build trajectories from
  shuffled labels, then call `ngram_embed`); a correct cohort-shuffle
  null must shuffle birth-cohort metadata BEFORE any cohort-conditioned
  step. Re-implementation pending.
  *(Revised 2026-05-25 from confirmation of code-review findings P0-3
  and P1-5; supersedes the 2026-05-22 entry which itself superseded the
  2026-04-07 L=2000 entry. Full record in
  `04-Methods/Computational-Log.md` entry dated 2026-05-25 and in
  `c:\Users\steph\TDL\.apm\memory\code-review-2026-05-25.md`.)*

- **NEVER treat reported Markov-1, Markov-2, stratified-Markov-1, or
  order-shuffle p-values as final pending the `ngram_embed()`
  frozen-loadings fix.** `_order_shuffle`, `_markov_shuffle`, and
  `_stratified_markov_shuffle` correctly re-permute trajectory state
  sequences but call `ngram_embed(synthetic, **kwargs)` without a
  frozen-loadings option (`ngram_embed.py:115-241` re-fits scaler and
  PCA on every call). Observed and null persistence diagrams therefore
  live in independently-fit PCA coordinate frames; their W2 distance
  jointly tests (a) generative-process difference and (b) PCA-basis
  rotation across draws. Rejection directions are likely robust but
  cannot be isolated until a `frozen_scaler` / `frozen_pca` parameter
  exists on `ngram_embed()` and is threaded through the trajectory-
  level null functions. All affected results carry a PROVISIONAL flag
  until the frozen-loadings fix lands and re-runs complete: T1.2 USoc
  and BHPS headlines (L=5000 and LM sensitivity L in 2500 / 8000),
  T1.3 stratified-Markov Outcome A lock, the T1.2b through T1.2h
  in-flight overnight batch, T1.8 Markov-2 alpha sweep when run, T1.6
  BHPS H4 diagnostics when run. Affected paper sections: P01-A
  section 4.3 (Markov-1 and stratified rejections); P01-A section 6.2
  (BHPS H1); P01-B section 4 (Markov ladder + Wasserstein
  discrepancy).
  *(Established 2026-05-25.)*

- **NEVER write P01-B §4 content that discusses regime profiles, escape rates,
  gender/age/education stratification, poverty trap interpretation, or Mapper
  results.** P01-B §4 demonstrates the hypothesis-testing framework only (Markov
  ladder results, Wasserstein discrepancy, survey-design decomposition,
  practitioner guidance). Applied findings belong exclusively to P01-A and P04.
  *(P01-B §4 strict scope rule — established 2026-04-07)*

- **NEVER submit P04 to AoAS before P01-A/B appear on arXiv.** P04 references
  "Paper 1 in this programme" throughout; arXiv preprints provide stable
  citations before JRSS acceptance (which may take 12–18 months).
  *(Established 2026-04-07)*

---

## Methodological Conventions

- **Null model design:** The preferred null for P01 is a k-th order Markov
  chain fitted to the observed transition probabilities, with synthetic
  trajectories generated via simulation. The key test is whether the
  persistent homology of the observed data exceeds what the null produces
  at each Markov order.

- **ε\* canonical value:** The locked ε\* point estimate is **0.54**, the
  median knee across 32 years (1991–2022) from `detect_eps_star_knee()`
  sensitivity analysis (commit `4c73a1a`). Locked 2026-05-07. The robustness
  set is {0.54, 0.65, 0.70, 0.80}; 4 degenerate years (2003, 2005, 2011,
  2019) are reported alongside. The value 0.70 previously used in P01-A §4.3.2
  is retired — it was a pre-sensitivity-analysis constant, not data-driven.

- **Persistence diagram comparison pipeline:**
  1. Compute VR persistence on observed trajectories
  2. Generate N synthetic trajectory sets from the fitted null
  3. Compute VR persistence on each synthetic set
  4. Compare observed vs null distributions using Wasserstein-2 AND
     persistence landscape L² distance
  5. Report both metrics with permutation-based p-values

- **Paper staging convention:**
  - Stage 0: Literature review + methodology design
  - Stage 1: Implementation + initial results
  - Stage 2: Full draft + submission
  - Stages are tracked in each paper's `_project.md`

- **Code repository convention (post-2026-04-07):** Each paper has its own
  self-contained GitHub repo. Embedding code is duplicated across all three
  repos — standard academic reproducibility approach. Accept the maintenance
  cost; reviewers get a self-contained repo with no cross-repo dependencies.
  Repo names: `stephendor/p01a-career-inequality-topology`,
  `stephendor/p01b-ph-hypothesis-testing`, `stephendor/p04-multiparameter-poverty`.
  All repos require Zenodo DOI v1.0.0. **P01-B repo must be finalised before
  responding to any JRSS-B revision request** (JRSS-B requires archived code
  before acceptance, not just initial submission).

---

## Citation Conventions

- Use `@citekey` format in prose drafts (compatible with Zotero Integration
  plugin export)
- Literature notes use the filename pattern from Zotero Integration:
  `@AuthorYear - Title.md`
- When a source is used in multiple papers, the literature note should tag
  all relevant paper IDs

---

## Computational Environment

- Python 3.13 on Windows (username: `steph`)
- Primary IDE: VSCode with GitHub Copilot
- TDL repository: `C:\Users\steph\TDL\`
- Key libraries: `persim`, `ripser`, `scikit-tda`, `giotto-tda`
- Vault path: `C:\Users\steph\Documents\TDA-Research\`

**Environment variables (commit `72f91c4`):**

| Variable | Purpose | Default |
|---|---|---|
| `TDA_VAULT_PATH` | Vault root for copilot/agent context | `C:\Users\steph\Documents\TDA-Research` |
| `TRAJECTORY_TDA_DATA_DIR` | Raw trajectory data directory for battery scripts | Package data fallback |

Set `TRAJECTORY_TDA_DATA_DIR` when running `run_wasserstein_battery.py` outside the default package layout (e.g., on a different machine or in CI). Without it the script falls back to package-bundled data, which may not include the full USoc/BHPS data files.

---

*Last updated: 2026-05-25*
