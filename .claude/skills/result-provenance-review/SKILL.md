---
name: result-provenance-review
description: Use when reviewing or producing TDL computational result files — caches, seeds, output paths, date suffixes, no-overwrite behavior, gitignored intermediates, or vault traceability — to confirm a result is reproducible and correctly recorded.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - output-provenance
  roles:
    - verifier
  runtime: agnostic
---

# Result Provenance Review

Use this for the Output / Provenance assurance lane. A numerically correct result
is still unusable if it cannot be regenerated, was silently overwritten, or its
parameters and seeds are not recorded. This skill is the judgment layer over the
`results-vault-reminder` hook, the no-overwrite enforcement hook, and the
`output_validation` contracts — run it when those mechanical checks are not enough
to know whether a result is trustworthy and traceable.

## Checklist

Work through each item against the result under review:

1. **Date-suffixed filename.** Numerical results use `<basename>_<YYYY-MM-DD>.json`.
   A new run gets a new date suffix; the prior file is preserved as historical
   record.
2. **No silent overwrite.** Confirm no existing results file was overwritten in
   place. If a value changed, the old file should still exist under its own date.
3. **Two-path rule.** The producing script defines `PROJ_ROOT` and `WORKTREE`
   roots and writes deliverables to the `PROJ_ROOT` path, not the worktree path.
4. **Seeds recorded.** Every stochastic step (permutation, bootstrap, Markov
   simulation, UMAP) has its seed set in the script and recorded in the vault
   `[RESULT]` entry.
5. **Cache provenance matches.** Any reused cache matches the current seed, B
   (permutations), L (landscape levels), null model, Markov order *k*, and date.
   A cache built under different parameters is not a valid input.
6. **Deliverable JSON committed.** Every result JSON in the Task Output section is
   `git add`ed and committed on the Task branch.
7. **CSV/PKL are gitignored and regenerable.** `*.csv` and `*.pkl` are globally
   gitignored (UKDA T&C + size); their producing script is committed so they can
   be regenerated. Do not attempt to commit them.
8. **Vault entry filed.** A `[RESULT]` entry (or `[NEGATIVE]`/`[DECISION]` as
   appropriate) was written to the canonical vault page, at the top, in
   reverse-chronological order.
9. **Downstream intermediates present.** Any gitignored intermediate a downstream
   task consumes exists at its expected `PROJ_ROOT` path; the regeneration command
   is recorded. Gitignored ≠ missing — verify on disk at the absolute path.
10. **No superseded artifact in an active glob.** When a result was corrected
    within the branch, the superseded file is `git rm`ed — not left matching an
    `output_validation` dispatch glob where it fails the active schema and forces
    special-case handling. Correspondingly, confirm the enforcement test
    *exercises* the files it guards: a test that skips the exact stale/non-
    corrected files it is meant to catch (e.g. a `"corrected_" not in name`
    skip) is not enforcing anything.
11. **Referent identity (revision / issue-closing tasks).** When a result closes a
    reviewer issue or supplies a number already in a draft, confirm it computed the
    *exact object the issue/claim names* — which two clusterings, which estimand,
    which metric and denominator — not a topic-adjacent statistic. For an inherited
    number, re-resolve it to the **canonical-latest** date-suffixed file for that
    basename and confirm that file's model/comparison still matches the claim; the
    newest file under a basename can be a *different* analysis. Flag — do not
    silently swap — when the canonical file's object ≠ the claim.
12. **Self-description matches payload.** If a file declares which of several
    candidate objects it computed (`use_stability`, `comparison`, `estimand`,
    `metric`), confirm the declared object equals the one actually computed. A
    value-level schema check passes while a declared-vs-computed contradiction lies
    silently; where feasible make it a relational assertion (e.g. recompute the SE
    at the *declared* metric's `p`).
13. **Input vintage + fail-closed canary (baseline reproductions).** "Regenerate
    from the committed script" guarantees code, not data. Treat an input
    mtime/vintage mismatch as a *trigger to run a fail-closed content canary*
    (recompute must reproduce the stored baseline within tol), never as a verdict on
    its own — re-extracted or relocated data routinely carries a new mtime with
    identical bytes. Record a canary PASS as positive coherence evidence, not merely
    "no mismatch found." See
    `[[Regenerated-gitignored-intermediates-can-silently-break-baseline-reproducibility]]`.
14. **Reusable reference caches self-declare their generative inputs.** A cache
    or artifact intended for downstream reuse as a reference (frozen null
    diagrams, calibration banks) must record the sha256 (or key-inventory hash)
    of every generative input in its own metadata — not just
    `{B, L, seed, dataset, timestamp}`. Without it, a consumer cannot cheaply
    verify vintage before an expensive reconstruction; retrofit cache writers to
    stamp source-sequence / embedding hashes in-band. When a brief says "reuse
    the frozen cache, do not recompute," resolve the cache's declared
    source-input hash against the current on-disk input FIRST — a mismatch
    predicts and names a correspondence failure before the reconstruction is run.
15. **File provenance rulings under the object they rule on.** A statement that
    result/cache/bank X is (or is not) affected by a vintage or supersession
    event belongs in X's own authoritative manifest (e.g. `SUPERSEDED.md`) or a
    note it wikilinks — not only inside a differently-titled entry that mentions
    X in passing. State the evidence class explicitly: bit-for-bit reproduction
    settles a vintage claim; mtime or architecture reasoning alone is
    provisional until reproduced, and must be labelled as such.
16. **Exact solver identity and live re-derivation.** When a solver has an
    approximate or greedy fallback, record the backend identity, version, and
    exactness evidence in-band and abort if the exact backend required by the
    claim is absent. A reproduction gate must recompute through the fresh code
    path; comparing a value copied from an artifact back to that artifact is
    self-reference, not validation. Use theorem-derived impossibility bounds
    where available to reject plausible-looking fallback values cheaply.
17. **Date facts from artifacts, guarantees from locks.** A dependency lockfile
    dates when an environment became guaranteed, not when a dependency first
    became present. Establish result eras from surviving outputs, independent
    reproduction under candidate conventions, and natural experiments across
    the suspected boundary. If no artifact survives, report the era
    unverifiable; record any present-to-guaranteed interval as a fragile window.
18. **Checkout-independent identity.** For committed text or binary inputs, bind
    identity to the Git blob (`git rev-parse HEAD:<path>` / `git hash-object`),
    not `sha256` of working-tree bytes that `core.autocrlf` may rewrite.
    Gitignored intermediates have no blob and retain byte SHA-256/vintage rules.
    Diagnose a clean-file hash mismatch with `git ls-files --eol` before
    inferring drift.

## Output Format

Report **PASS / GAP** per checklist item. For each GAP: the item, the specific
file or path, and the corrective action (regenerate, re-date, record the seed,
file the vault entry). Conclude with whether the result is trustworthy as a
downstream input or paper-facing source.

## Escalate Or Stop When

- A results file was overwritten and the prior value cannot be recovered.
- A cache was reused whose parameters do not match the current run.
- A committed JSON consumed downstream is missing or malformed — surface it, do
  not fabricate a substitute.

## Pressure Scenarios From This Repo

- T1.36 produced invalid p-values from preserved caches whose denominator
  parameters no longer matched the corrected formula.
- T1.37 distinguished frozen vs provisional output paths; mixing them silently
  treats a provisional embedding as the frozen reference.
- Superseded smoke-run outputs were left in place and risked being read as live
  results.
- PR #31 left stale pre-correction JSONs (`power_analysis_2026-06-03.json` etc.)
  matching the active dispatch glob while the validation test skipped exactly
  those non-`corrected_` files — so the enforcement never exercised the files it
  was meant to catch. Fix: `git rm` the superseded artifacts and remove the skip.
  See `[[Enforcement-must-assert-value-not-key-presence]]`.
- The frozen USoc null-diagram cache
  (`null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz`) was built on a
  since-superseded May-2 orphan sequences build; its metadata recorded
  `{B, L, seed, dataset, timestamp}` but not the generative input's sha256, so
  the mismatch surfaced only after a full reconstruction-and-compare. A B9
  vintage ruling made in passing inside a `§4-clustering`-titled decision entry
  was never surfaced to `SUPERSEDED.md`, so a later spike could not find it —
  and the ruling itself was mtime-reasoned, not reproduction-verified, and
  turned out to be false.

## Related Skills & Contracts

- Use `vault-sync` to file the `[RESULT]` entry and `commit-log` to draft it.
- Use `reproducibility-package-review` for end-to-end regenerability of a result set.
- Enforcing contracts: `stage1-output-json-validation`, the
  `*-output-json-validation` dispatch contracts, and `markov-order-provenance`.
## Staged-execution provenance

When a final result is assembled from deferred partials, require and verify from disk: the approved plan path and digest, approval state, every batch path and digest, expected and observed unit counts, completion states, deferred-inference declaration, and producer commit. Classify provenance as PASS only when the terminal result binds the complete authorised execution chain.
