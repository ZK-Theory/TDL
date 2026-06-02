---
name: reproducibility-package-review
description: Use before a result set is relied on for a paper or handed off — to confirm every committed result can be regenerated end-to-end from committed scripts plus recorded seeds and parameters.
---

# Reproducibility Package Review

Use this for the Output / Provenance lane, at the end-to-end level. Individual
results may each pass provenance review while the *set* is not reproducible: a
gitignored intermediate has no committed producer, or a seed was never recorded.
This is the final check that someone could rebuild the results from the repo alone.

## Core Check

1. **Producer committed.** Every result file (including gitignored `*.csv`/`*.pkl`
   intermediates) has its producing script committed on the branch.
2. **Regeneration command recorded.** The command to regenerate each gitignored
   intermediate is in the Task Log / vault entry.
3. **Seeds + parameters recorded.** Every stochastic step's seed and the run
   parameters (B, L, k, null model) are recorded in the script and the vault.
4. **Intermediates present.** Downstream-needed gitignored files exist at their
   `PROJ_ROOT` paths (verify on disk; gitignored != missing).
5. **Chain closes.** Following the recorded commands from raw inputs reproduces the
   committed results.

## Output Format

A regenerability table: result -> producer script -> seed/params recorded (Y/N)
-> intermediate present (Y/N) -> **REPRODUCIBLE / GAP**. List every gap with the
missing artifact.

## Pressure Scenario

A gitignored intermediate consumed downstream had no committed producing script;
the result could not be regenerated from the repo.

## Related Skills & Contracts

- Pairs with `result-provenance-review` (per-file) and `commit-log` / `vault-sync`
  (recording the regeneration command and seeds).
- Enforcing: the two-path rule and downstream-data guarantee in CLAUDE.md APM_RULES.
