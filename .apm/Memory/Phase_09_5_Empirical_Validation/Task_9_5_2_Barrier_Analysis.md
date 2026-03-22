# Task 9.5.2 - Barrier-Gradient Correlation Analysis

**Task ID**: Task_9_5_2_Boundary_Analysis  
**Agent**: Agent_Poverty_Topology (via Antigravity)  
**Status**: ✅ COMPLETE  
**Phase**: 9.5 - Empirical Validation  
**Date Completed**: December 16, 2025

---

## Task Objective

Test whether Morse-Smale barrier heights predict real outcome discontinuities across basin boundaries. This tests TDA's unique value proposition: do topological barriers correspond to real outcome gradients?

## Results Summary

### Multi-Outcome Correlation Results (WM 150x150, n=632 pairs)

| Outcome | r | p | Significant |
|---------|---|---|-------------|
| IMD Score (LSOA) | -0.100 | 0.012 | ✓ (weak) |
| Life Expectancy (LAD) | -0.085 | 0.033 | ✓ (weak) |
| IMD Rank (LSOA) | 0.009 | 0.820 | ✗ |
| Net Migration (LAD) | -0.031 | 0.436 | ✗ |

### Key Finding: WEAK/NO CORRELATION

**TDA barriers do NOT strongly predict outcome gradients** (r < 0.3 for all).

This is an important **null result**: while MS basins explain 73-83% of outcome variance, the barrier *heights* between basins are not strong predictors of outcome *gradients*.

---

## Technical Implementation

### Morse-Smale Complex (WM 150x150)

| Metric | Value |
|--------|-------|
| Critical points | 1,575 |
| Minima (poverty traps) | 383 |
| Saddles (barriers) | 787 |
| Maxima (opportunity peaks) | 405 |
| Separatrices | 3,094 |
| Adjacent basin pairs | 1,080 |
| Pairs with outcome data | 632 |

### Basin Assignment

- 1,638 WM LSOAs assigned to 245 basins
- Assignment via descending manifold grid lookup
- Grid coordinates reprojected from WGS84 to BNG (EPSG:27700)

### Barrier Height Computation

For each adjacent basin pair:
1. Find all boundary cells between the two basins
2. Compute max mobility value at boundary cells
3. Barrier height = max boundary mobility - avg minimum value

---

## Interpretation

### Why Weak Correlation?

1. **Resolution mismatch**: Outcomes at LAD level (7 values) vs grid (150×150) with 245 basins
2. **Static vs dynamic**: Barriers may affect escape *difficulty* not current outcome levels
3. **Metric choice**: Max boundary mobility may not capture true topological barrier

### Implications

- **Basins**: Capture static outcome structure (η² = 73-83%)
- **Barriers**: May capture dynamic escape difficulty (not cross-sectional gradients)
- **Future work**: Test with longitudinal data to see if barriers predict outcome *changes*

---

## Files Created

**New Files**:
- `poverty_tda/validation/run_barrier_analysis.py` - Single outcome analysis
- `poverty_tda/validation/run_barrier_correlation.py` - Full analysis with LE
- `poverty_tda/validation/run_multi_outcome_barrier.py` - Multi-outcome analysis

**Modified Files**:
- `poverty_tda/validation/results/COMPARISON_PROTOCOL_SUMMARY.md` - Added barrier results

---

## Success Criteria

| Criterion | Target | Achieved | Status |
|-----------|--------|----------|--------|
| r > 0.5 (strong correlation) | Goal | **r = -0.1** | ✗ FAILED |
| Statistical significance | p < 0.05 | **p = 0.01-0.03 for 2/4** | ⚠ PARTIAL |
| Multiple outcomes tested | ≥2 | **4 outcomes tested** | ✅ EXCEEDED |

**Important**: This is a meaningful null result - barriers ≠ current gradients.

---

## Conclusion

Task 9.5.2 tested TDA's barrier-gradient hypothesis and found weak/no correlation. While this doesn't meet the success criterion (r > 0.5), it provides important insight: MS basins predict outcomes well, but barrier heights are not strong predictors of cross-sectional gradients. This suggests barriers may affect escape dynamics rather than current state.

**Status: ✅ TASK COMPLETE - NULL RESULT DOCUMENTED**
