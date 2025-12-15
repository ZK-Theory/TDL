# APM Research Delegation: TDA Crisis Detection Failure Analysis

**Delegation Type**: Research Investigation  
**Priority**: CRITICAL  
**Delegated By**: Agent_Financial_ML  
**Delegated To**: Research Agent / Expert Review  
**Date**: 2025-12-15  
**Context**: Task 7.2 Crisis Detection Validation - FAILED

---

## Problem Statement

Financial TDA crisis detection validation has catastrophically failed:
- **Average F1 Score**: 0.216 (target 0.70) - 69% below target
- **Crypto F1**: 0.000 (complete failure)
- **G&K Replication**: τ=0.814 vs expected 1.00 (19% shortfall)
- **User Assessment**: "Lead time is largely irrelevant if accuracy and precision are very poor. No one is interested in making bad decisions well in advance."

---

## Research Questions

### 1. Implementation Verification
**Question**: Are there bugs or errors in our persistence computation?
- Compare our persistence landscape implementation in `financial_tda/topology/features.py` against G&K paper methodology in `docs/Research Papers/arXiv-1703.04385v2/TDA_financial_5.1.tex`
- Verify bottleneck distance calculation is correct
- Check if Vietoris-Rips filtration parameters are appropriate
- Cross-validate with alternative TDA libraries (persim, scikit-tda)

### 2. G&K Replication Analysis
**Question**: Why did we only achieve τ=0.814 vs paper's τ≈1.00?
- Did we misunderstand their spectral density calculation?
- Are we using correct persistence landscape formula?
- Should we try different parameters (window sizes, embedding dimensions)?
- Is there a data source difference affecting results?

### 3. Bottleneck Distance Viability
**Question**: Is bottleneck distance fundamentally wrong for this task?
- Why does worst-case matching fail when L^p norms succeed?
- Should we use Wasserstein distance instead?
- Are persistence images or persistence statistics better features?
- Does the literature use bottleneck distance for crisis detection?

### 4. Literature Review
**Question**: What do OTHER papers actually achieve?
- Search for TDA financial crisis detection papers beyond G&K
- What F1/accuracy/precision metrics do they report?
- Do ANY papers achieve F1>0.70 for per-day classification?
- Is our target unrealistic or is our implementation broken?
- What methods actually work for crisis detection?

### 5. Threshold Calibration
**Question**: Is 95th percentile fundamentally flawed?
- Why does it fail differently across crisis speeds (slow GFC, fast COVID, crypto)?
- Should we use adaptive/dynamic thresholding?
- Are there better statistical approaches (changepoint detection, anomaly detection)?
- Does the literature use percentile-based thresholds?

### 6. Fundamental Viability
**Question**: Is TDA even suitable for per-day crisis classification?
- Maybe it only works for trend detection (G&K approach), not classification
- Do financial time series have stable enough topology?
- Are topological features actually predictive of crises?
- Should we pivot to different approach entirely?

---

## Required Deliverables

### 1. Root Cause Analysis Report
- Identify specific reasons for F1=0.216 failure
- Determine if implementation bugs vs methodology issues
- Provide evidence (code traces, calculations, comparisons)

### 2. Literature Comparison
- Summary of OTHER TDA crisis detection papers
- Their reported metrics (F1, accuracy, precision, recall)
- Their methodologies vs ours
- Performance benchmarks we should target

### 3. Viability Assessment
**Must answer definitively**:
- ✅ **FIXABLE**: Bugs/parameters can be corrected → path to F1≥0.60
- ⚠ **SALVAGEABLE**: Methodology needs major changes → hybrid approach
- ❌ **NOT VIABLE**: TDA unsuitable for this task → recommend pivot

### 4. Concrete Recommendations
If fixable/salvageable:
- Specific bugs to fix
- Parameters to change
- Alternative TDA metrics to try
- Expected performance improvement

If not viable:
- Alternative approaches (ML on raw features, traditional indicators, etc.)
- Honest admission that TDA isn't the right tool
- Recommended next steps

---

## Files to Examine

### Implementation Files
- `financial_tda/topology/features.py` - Persistence landscape computation
- `financial_tda/topology/filtration.py` - Vietoris-Rips and diagrams
- `financial_tda/models/change_point_detector.py` - Threshold calibration
- `financial_tda/validation/gidea_katz_replication.py` - Our G&K implementation

### Validation Results
- `financial_tda/validation/CHECKPOINT_REPORT.md` - Overall failure summary
- `financial_tda/validation/cross_event_metrics.md` - Metrics across events
- `financial_tda/validation/gidea_katz_2008_replication.md` - G&K results
- `financial_tda/validation/2008_gfc_validation.md` - GFC F1=0.351
- `financial_tda/validation/2020_covid_validation.md` - COVID F1=0.514
- `financial_tda/validation/2022_crypto_terra_validation.md` - Terra F1=0.000

### Reference Material
- `docs/Research Papers/arXiv-1703.04385v2/TDA_financial_5.1.tex` - Original G&K paper
- Search academic literature for other TDA crisis detection papers

---

## Critical Constraints

### Honesty Required
- **No bullshit**: If TDA doesn't work, say so
- **No excuses**: Don't explain away failures with "different tasks"
- **No false optimism**: F1=0.216 is unacceptable, period
- **Evidence-based**: All conclusions must be backed by data/literature

### Focus Areas
1. **First Priority**: Verify implementation correctness (bugs?)
2. **Second Priority**: Literature review (realistic benchmarks?)
3. **Third Priority**: Viability assessment (salvageable?)

### Decision Criteria
- If we can identify path to F1≥0.60 → continue with fixes
- If not → recommend pivot to different approach
- User needs honest assessment to make informed decision

---

## Success Criteria

Research is successful if it provides:
1. ✅ Clear root cause(s) of failure identified
2. ✅ Literature benchmarks established (realistic targets)
3. ✅ Definitive viability assessment (fix/salvage/pivot)
4. ✅ Concrete next steps with expected outcomes

---

## Urgency

**BLOCKING**: Task 7.2 cannot proceed until this research is complete. User has rejected current validation results and demands honest investigation.

---

**Delegation Status**: ACTIVE  
**Expected Completion**: ASAP  
**Blocking Tasks**: Task 7.2, Task 7.5, Phase 8 planning
