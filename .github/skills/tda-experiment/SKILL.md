---
description: Scaffold a new TDA experiment module in the correct domain package
allowed_tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Skill: tda-experiment

Scaffold a new TDA experiment for this research project.

## Your task

1. Ask the user for:
   - Which domain: `financial_tda`, `poverty_tda`, or `trajectory_tda`
   - A short experiment name (snake_case, e.g. `sector_crisis_2024`)
   - What topological method to use (Rips, Alpha, Mapper, Morse-Smale, etc.)
   - What the hypothesis or research question is

2. Determine the correct target directory:
   - `financial_tda/experiments/<name>.py` for financial experiments
   - `trajectory_tda/scripts/<name>.py` for trajectory scripts
   - `poverty_tda/analysis/<name>.py` for poverty analysis

3. Read one or two existing experiment files in that domain to understand the established patterns, imports, and structure.

4. Create the new experiment file following this template structure:
   - Module docstring with: research question, method, expected output, references
   - Typed configuration dataclass or constants section
   - `load_data()` function calling domain `data/` modules
   - `compute_topology()` function calling domain `topology/` modules
   - `analyse()` function implementing the specific analysis
   - `main()` function orchestrating the pipeline with logging
   - `if __name__ == "__main__":` block

5. Create a corresponding test stub in `tests/<domain>/test_<name>.py` with:
   - At least one smoke test
   - Appropriate markers (`@pytest.mark.slow` if needed, `@pytest.mark.integration` if data-dependent)

6. Report back: the files created, the research question captured in the docstring, and what to run next.

## Key conventions to follow

- All public functions need Google-style docstrings and type hints
- Use `pathlib.Path` for all file paths
- Use `logging` not `print()`
- Save results to `results/<domain>/` or `outputs/<domain>/`
- Expose all tunable parameters (thresholds, window sizes, n_permutations) as function arguments with defaults
- Permutation nulls: default `n_permutations=1000`
- Bootstrap CI: default `n_bootstrap=1000`
