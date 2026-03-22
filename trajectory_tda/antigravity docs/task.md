# State-Space TDA Pipeline — Task Breakdown

## Phase 1: Planning
- [x] Explore existing codebase for reusable infrastructure
- [x] Write implementation plan
- [x] User review & approval (with enhancements integrated)

## Phase 2: Project Scaffolding
- [x] Create `trajectory_tda/` package structure with `__init__.py` files
- [x] Update `pyproject.toml` (packages, deps, ruff, pytest)
- [x] Create `tests/trajectory/conftest.py` with synthetic generators

## Phase 3: Data Layer
- [x] `trajectory_tda/data/employment_status.py`
- [x] `trajectory_tda/data/income_band.py`
- [x] `trajectory_tda/data/trajectory_builder.py`
- [x] Unit tests for data layer

## Phase 4: Embedding
- [x] `trajectory_tda/embedding/ngram_embed.py`
- [x] `tests/trajectory/test_ngram_embed.py`

## Phase 5: PH Pipeline
- [x] `trajectory_tda/topology/trajectory_ph.py`
- [x] `trajectory_tda/topology/permutation_nulls.py`
- [x] `trajectory_tda/topology/vectorisation.py`
- [x] Tests for PH pipeline

## Phase 6: Analysis
- [x] `trajectory_tda/analysis/regime_discovery.py`
- [x] `trajectory_tda/analysis/cycle_detection.py`
- [x] `trajectory_tda/analysis/group_comparison.py`
- [x] Tests for analysis modules

## Phase 7: Integration & CLI
- [x] `trajectory_tda/scripts/run_pipeline.py`
- [x] Lint + format check
- [x] Full test suite passes

## Phase 8: Integration Testing (Real UKDS Data)
- [x] Run full pipeline on UKDS data to identify runtime issues
- [x] Document findings and resolve bottlenecks (Fixed data extraction paths/variables, bypassed memory explosion in Witness Complex by defaulting to `maxmin_vr`).
