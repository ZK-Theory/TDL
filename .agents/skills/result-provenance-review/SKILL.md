---
name: result-provenance-review
description: Use when reviewing or producing TDL computational result files — caches, seeds, output paths, date suffixes, no-overwrite behavior, gitignored intermediates, or vault traceability — to confirm a result is reproducible and correctly recorded.
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

## Related Skills & Contracts

- Use `vault-sync` to file the `[RESULT]` entry and `commit-log` to draft it.
- Use `reproducibility-package-review` for end-to-end regenerability of a result set.
- Enforcing contracts: `stage1-output-json-validation`, the
  `*-output-json-validation` dispatch contracts, and `markov-order-provenance`.
