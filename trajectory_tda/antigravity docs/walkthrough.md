# State-Space TDA Pipeline Implementation

The new `trajectory_tda` package has been successfully implemented and tested. This pipeline provides a comprehensive toolkit for analyzing life-course trajectories (Employment Status × Income Band) using persistent homology.

## 1. Architecture Overview

The pipeline is organized into five core modules, mirroring the `poverty_tda` and `financial_tda` structures:

*   **`trajectory_tda.data`**: Includes `employment_status.py` (handling BHPS/USoc harmonized `jbstat` mappings) and `income_band.py` (HBAI-standard poverty thresholds with continuous mediation). `trajectory_builder.py` unites these into 9-state life courses, filtering out short sequences and interpolating gaps up to 2 years.
*   **`trajectory_tda.embedding`**: `ngram_embed.py` transforms state sequences into high-dimensional vector spaces. Supports 9D unigrams, 90D bigrams, TF-IDF weighting (to highlight rare transitions like poverty escapes/falls), and UMAP/PCA dimensionality reduction.
*   **`trajectory_tda.topology`**: Implements a hybrid persistent homology approach in `trajectory_ph.py`:
    *   **MaxMin VR** (`ripser`) for robust H₀ components (mobility regimes).
    *   **Witness Complex** (`gudhi`) for H₁ loops (poverty/unemployment traps).
    *   `permutation_nulls.py` provides four distinct null models (label, cohort, order, Markov) to test different aspects of topological significance.
*   **`trajectory_tda.analysis`**:
    *   **Regime Discovery:** Combines GMM clustering with PH-detected components to identify dominant mobility classes.
    *   **Cycle Detection:** Isolates persistent H₁ loops and finds defining transition patterns (traps).
    *   **Group Comparison:** Uses Wasserstein distances (implemented in `vectorisation.py`) and topological landscapes to compare stratified subgroups (e.g. by parental class).
*   **`trajectory_tda.scripts`**: Contains `run_pipeline.py`, an end-to-end CLI orchestrator with intermediate state checkpointing for reproducibility.

## 2. Validation & Quality Assurance

A comprehensive testing suite was built in `tests/trajectory/` with **63 automated tests**. All tests pass successfully.

*   **Mock Generation:** We implemented robust synthetic trajectory generators in `conftest.py` that can simulate random uniform sequences, dense isolated regimes, persistent cycles, and Markov-churn behavior.
*   **Module Testing:** Validated gap handling, TF-IDF standardisation interactions, MaxMin landmark spatial coverage, Betti curve extraction, and permutation P-value bounding.
*   **Linting:** The codebase has been fully checked and cleaned with `ruff`, resolving prior unused-variable warnings and adhering to project style guidelines.

## 3. How to Run

To execute the full analytical pipeline against the real UKDS data (`UKDA-5151` and `UKDA-6614`):

```bash
python -m trajectory_tda.scripts.run_pipeline \
    --data-dir data \
    --min-years 10 \
    --n-perms 100 \
    --landmarks 5000 \
    --embed pca20 \
    --nulls all \
    --checkpoint results/trajectory_tda/
```

> [!TIP]
> Use `--verbose` to trace the data harmonisation processing when running real UKDS extracts.

## 4. Empirical Integration Validation

The pipeline successfully completed a full end-to-end integration test against the real UKDS panel data (BHPS waves a-r and USoc waves a-n). 

**Key Execution Metrics:**
- **Data Load**: Processed 805,172 person-year records across 118,153 unique individuals.
- **Trajectory Filtering**: Built 27,280 valid ≥10-year mixed employment/income trajectories.
- **Embedding**: Handled 90D ngram TF-IDF embedding before PCA 20D reduction.
- **Topology (maxmin\_vr)**: Computed persistent homology over 2,500 adaptive landmarks.
- **Discovery**: Uncovered 7 dominant mobility regimes and 1,840 H₁ topological cycle trap patterns.

The pipeline is complete and production-ready for empirical evaluation.
