# /new-analysis — Start a New TDA Analysis

Scaffold and run a new computational analysis for a paper in the research programme.

## Usage

```
/new-analysis PXX [analysis-name]
```

Example: `/new-analysis P02 mapper-parameter-sweep`

---

## Pre-flight

1. Read `papers/PXX/_project.md` — which computations are needed?
2. Check `results/` for existing outputs that can be reused.
3. Read the relevant domain README (e.g., `trajectory_tda/README.md`).

## Branching

Computation runs on a dedicated branch: `run/pXX-[analysis-name]`

```bash
git checkout -b run/pXX-[analysis-name]
```

Results go to `results/trajectory_tda_integration/` (or domain-specific results dir).
Code goes in `trajectory_tda/experiments/` or `trajectory_tda/scripts/`.

## Output format

Every analysis script should produce:
- A JSON results file in `results/` with all numeric outputs
- A brief log of runtime, landmark count, and parameter choices
- Inline comments explaining parameter decisions (these are the computational log)

## After computation

1. Commit results and code to the `run/pXX-` branch.
2. Open a PR to main: title format `results(PXX): [what was computed]`
3. Update `papers/PXX/_project.md` open items.
4. Reference the results file in the paper draft.

## Computational Log

Record benchmarks in `papers/PXX/notes/` or inline in the results JSON:
- Hardware used
- Runtime
- RAM peak
- Parameter choices and rationale

This is the institutional memory that prevents re-running expensive computations for forgotten reasons.
