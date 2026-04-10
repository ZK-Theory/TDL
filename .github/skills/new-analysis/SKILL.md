---
description: Scaffold a new analysis module within a domain package
allowed_tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Skill: new-analysis

Add a new analysis module to an existing domain package.

## Your task

1. Ask the user for:
   - Domain: `financial_tda`, `poverty_tda`, or `trajectory_tda`
   - Analysis type: statistical comparison, regime analysis, group comparison, robustness check, etc.
   - Module name (snake_case)
   - What inputs it consumes (persistence diagrams, vectorised features, raw trajectories, etc.)
   - What outputs it produces (statistics, plots, CSVs)

2. Read 2-3 existing analysis modules in that domain's `analysis/` directory to understand conventions.

3. Read any relevant topology modules the new analysis will consume.

4. Create `<domain>/analysis/<module_name>.py` with:
   - Module docstring explaining purpose and relationship to the research question
   - Main analysis function with full type hints and Google docstring
   - Helper functions as needed (keep private with `_` prefix)
   - Output functions that save results to `results/<domain>/`

5. Wire it into any existing pipeline scripts if appropriate (ask user first).

6. Create `tests/<domain>/test_<module_name>.py` with:
   - Unit tests for pure computation functions using synthetic data
   - Mark integration tests that need real data

7. Report: what was created, how to call the main function, and what outputs to expect.

## Patterns to follow

- Pure functions preferred: `analyse(features: NDArray) -> dict[str, float]`
- Side effects (saving files, logging) isolated in `main()` or explicit `save_*` functions
- Never hardcode paths; accept `output_dir: Path` as parameter
- Significance reporting: always report both the statistic AND p-value AND effect size where applicable
- Robustness: if computing something sensitive to parameters, add a `sensitivity_analysis()` companion function
