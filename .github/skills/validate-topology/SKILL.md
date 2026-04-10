---
description: Run and summarise topological validation for a domain or specific module
allowed_tools: Read, Glob, Grep, Bash, AskUserQuestion
---

# Skill: validate-topology

Run the topological validation pipeline for this research project and summarise results.

## Your task

1. Ask the user which domain to validate (or "all"):
   - `financial_tda` — validates against Gidea-Katz 2017 and known crisis periods
   - `poverty_tda` — validates ARI agreement, migration patterns, persistence robustness
   - `trajectory_tda` — validates permutation nulls, FDR corrections, bootstrap CIs

2. Locate the relevant validation modules:
   - `financial_tda/validation/`
   - `poverty_tda/validation/`
   - `trajectory_tda/` (look for scripts prefixed `null_` or `validation_`)

3. Run the appropriate validation commands:
   ```bash
   uv run pytest tests/<domain>/ -m validation -v
   ```
   And if domain-specific validation scripts exist, run them and capture output.

4. Parse the results and report:
   - Which validations passed / failed
   - Any persistence thresholds that look suspicious (very low persistence, near-zero)
   - Any statistical tests with p > 0.05 that were expected to be significant
   - FDR corrections: how many hypotheses rejected after correction
   - Comparison with published benchmarks where applicable

5. If failures are found:
   - Read the failing test or validation script
   - Identify whether the issue is in data, topology computation, or statistical test
   - Suggest targeted fixes (do not apply without user confirmation)

## Known validation benchmarks

- **financial_tda**: 2008 GFC should show H1 spike; 2020 COVID should show H0 fragmentation
- **poverty_tda**: ARI between TDA basins and known deprivation deciles should be > 0.3
- **trajectory_tda**: Permutation null p-values for real data should be < 0.05 for primary hypotheses
