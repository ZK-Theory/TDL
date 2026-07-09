# ARS P0 Python Compatibility Baseline Note

**Date:** 2026-07-01
**Status:** `deferred_environment_compatibility_work`
**P0 effect:** ARS-targeted implementation and tests may proceed; repository-wide collection is not a clean baseline

## Observed baseline

The accepted ARS P0 worktree uses the repository's Python `3.13.5` pin. Before any ARS implementation files existed, the repository-wide unit-surface command

```powershell
uv run pytest tests -q --no-cov -m "not slow and not integration and not validation"
```

stopped during collection with 13 import errors. The failures were confined to existing financial/shared test modules importing `gtda` or `topologytoolkit`; no `research_system`, `tools/ars`, or `tests/research_system` path existed at that point.

`pyproject.toml` already records that `giotto-tda` has no configured Python 3.13 dependency because the required wheel is unavailable for the pinned interpreter. The current environment also lacks the `topologytoolkit` Python binding. These libraries may require a different Python version or separately managed environment from the ARS Python 3.13 foundation.

## P0 baseline decision

- WP1-WP4 use the exact ARS-targeted pytest and ruff commands in the accepted child plans.
- The 13 pre-existing collection errors are not treated as ARS passes and are not suppressed inside ARS tests.
- P0 does not loosen the repository Python pin, add ad hoc dependency versions, or alter existing financial/shared imports.
- Any ARS test importing either unavailable library is a new blocker and must not be waived under this note.

## Deferred compatibility work

Before repository-wide collection is claimed clean:

1. inventory supported Python versions and binary availability for `gtda`/giotto-tda and `topologytoolkit`;
2. decide whether one compatible interpreter can satisfy the repository or whether optional legacy/topology environments are required alongside Python 3.13;
3. lock each chosen environment and add import-smoke coverage for its owned modules;
4. document which test groups run in each environment and ensure aggregate CI reports missing groups rather than silently deselecting them; and
5. rerun repository-wide collection and record the exact remaining failures.

This compatibility work is environment maintenance, not authority to modify accepted ARS semantics or active research results.
