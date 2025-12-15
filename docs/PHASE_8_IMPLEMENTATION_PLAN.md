# Phase 8: TDA Methodology Realignment

**Status**: PLANNED  
**Prerequisites**: Phase 7 Complete  
**Duration**: 2-4 weeks  
**Priority**: HIGH

---

## Overview

Phase 7 validation identified that TDA implementation is **mathematically correct** but was evaluated against the **wrong task**. Phase 8 realigns the detection system with literature methodology.

**Key Finding from Phase 7**: G&K replication achieved τ=0.814 (validates TDA works), while bottleneck distance achieved F1=0.216 (wrong task).

---

## Objectives

1. **Align with Literature**: Implement trend detection using L^p norms (Gidea & Katz 2018)
2. **Validate Success**: Achieve Kendall-tau ≥ 0.70 on 250-day pre-crisis windows
3. **Document Methodology**: Explain task difference (trend detection vs classification)
4. **Optional**: Extend to event detection with tolerance windows (F1 ≥ 0.60)

---

## Implementation Options

### ⭐ Option 1: Literature-Aligned Trend Detection (RECOMMENDED)

**Goal**: Achieve τ ≥ 0.70 on 250-day pre-crisis trend detection

**What Changes**:
- **Before**: Bottleneck distance → per-day classification → F1 score
- **After**: L^p norms → trend detection → Kendall-tau correlation

**Code to Create**:
```python
# FILE: financial_tda/validation/trend_analysis_validator.py (NEW)

def compute_trend_indicator(l1_norms, l2_norms, window_size=250):
    """Compute Kendall-tau trend correlation (G&K methodology)."""
    from scipy.stats import kendalltau
    
    time_indices = np.arange(window_size)
    tau_l1, p_l1 = kendalltau(time_indices, l1_norms[-window_size:])
    tau_l2, p_l2 = kendalltau(time_indices, l2_norms[-window_size:])
    
    return {
        'kendall_tau_L1': tau_l1,
        'kendall_tau_L2': tau_l2,
        'p_value_L1': p_l1,
        'p_value_L2': p_l2,
        'status': 'PASS' if tau_l1 > 0.70 else 'FAIL'
    }
```

**Validation Events**:
- 2008 GFC: Target τ ≥ 0.70 (already achieved 0.814 ✓)
- 2000 dotcom: Target τ ≥ 0.70
- 2020 COVID: Target τ ≥ 0.70

**Timeline**: 1-2 weeks

**Success Criteria**:
- ✓ Kendall-tau ≥ 0.70 on all 3 events
- ✓ Documentation updated with methodology explanation
- ✓ Phase 7 validation reports revised

---

### Option 2: Event Detection with Tolerance Windows (OPTIONAL)

**Goal**: Achieve F1 ≥ 0.60 on event detection (±14 days tolerance)

**What Changes**:
- **Before**: Exact day matching required
- **After**: Event detected within ±14 day window counts as success

**Code to Create**:
```python
# FILE: financial_tda/models/change_point_detector.py (MODIFY)

def detect_events_with_tolerance(self, l1_norms, dates, 
                                  threshold_percentile=98.0,
                                  tolerance_days=14):
    """Detect crisis events with tolerance windows (MDPI 2025)."""
    threshold = np.percentile(l1_norms, threshold_percentile)
    spike_indices = np.where(l1_norms > threshold)[0]
    
    # Merge nearby spikes into events
    events = merge_nearby_events(spike_indices, tolerance_days)
    return pd.DataFrame(events)
```

**Timeline**: 1-2 weeks

**Success Criteria**:
- ✓ F1 ≥ 0.60 for tolerance_days=14
- ✓ Benchmark against MDPI 2025 (F1=0.70 at ±14 days)

---

### Option 3: Hybrid TDA + ML Features (OPTIONAL)

**Goal**: Use L^p norms as ML features (F1 ≥ 0.60)

**What Changes**:
- **Before**: Single metric (bottleneck distance)
- **After**: Feature vector {L1, L2, variance, spectral_density, trend}

**Code to Create**:
```python
# FILE: financial_tda/models/tda_feature_extractor.py (NEW)

def extract_tda_features(l1_norms, l2_norms, window_size=50):
    """Extract TDA-derived features for ML classifier."""
    features = {
        'L1_current': l1_norms,
        'L2_current': l2_norms,
        'L1_variance_50d': rolling_variance(l1_norms, window_size),
        'L2_variance_50d': rolling_variance(l2_norms, window_size),
        'L1_trend_50d': rolling_trend(l1_norms, window_size),
        'spectral_density_low': compute_spectral_density(l1_norms)
    }
    return pd.DataFrame(features)

# Train Random Forest (best from Task 7.1)
clf = RandomForestClassifier(n_estimators=100, max_depth=10)
clf.fit(features, labels)
```

**Timeline**: 2-3 weeks

**Success Criteria**:
- ✓ F1 ≥ 0.60 using Random Forest + TDA features
- ✓ Compare against Option 2 performance

---

## Recommended Implementation Sequence

### Week 1-2: Option 1 (Trend Detection) - PRIORITY

**Tasks**:
1. Create `trend_analysis_validator.py`
2. Implement Kendall-tau trend detection
3. Validate on 2008, 2000, 2020 crises
4. Update documentation

**Deliverables**:
- `financial_tda/validation/trend_analysis_validator.py`
- Updated `VALIDATION_SUMMARY.md` with revised criteria
- `docs/METHODOLOGY_ALIGNMENT.md` explaining task difference

**Success Metric**: τ ≥ 0.70 on all events

---

### Week 3-4: Documentation & Handoff

**Tasks**:
1. Update all Phase 7 validation reports
2. Create `docs/TASK_7_COMPLETION.md`
3. Document why bottleneck distance failed
4. Prepare Phase 9 proposal (if needed)

**Deliverables**:
- Complete Phase 7 documentation package
- Handoff document for manager review
- Roadmap for optional extensions (Options 2-3)

---

### Optional (Future): Options 2-3

**If per-day or event detection still required**:
- Implement Option 2 OR Option 3
- Target F1 ≥ 0.60 (realistic benchmark)
- Compare performance against literature

---

## Key Changes from Phase 7

### What Works (KEEP)
✅ Persistence landscape computation (features.py)  
✅ L^p norm calculation  
✅ G&K replication script (τ=0.814)  
✅ Early warning lead times (282 days avg)

### What Changes (FIX)
❌ **Remove**: Bottleneck distance as primary metric  
✅ **Replace**: L^p norms as primary metric

❌ **Remove**: Per-day binary classification (F1)  
✅ **Replace**: Trend detection (Kendall-tau)

❌ **Remove**: 95th percentile threshold on bottleneck distance  
✅ **Replace**: Kendall-tau > 0.70 on L^p norm trends

---

## Success Criteria (Revised)

### Phase 8 Complete When:

1. ✓ Trend analysis validator implemented
2. ✓ Kendall-tau ≥ 0.70 achieved on ≥2 events
3. ✓ Documentation explains methodology alignment
4. ✓ Phase 7 reports updated with findings
5. ✓ Manager approval for Phase 8 completion

### Optional Extensions Complete When:

6. ✓ Event detection (Option 2) OR Hybrid TDA+ML (Option 3) achieves F1 ≥ 0.60
7. ✓ Comparative analysis with literature benchmarks

---

## References

**Research Findings**: `.apm/Delegation/Phase_07_Research_Findings_TDA_Analysis.md`  
**Phase 7 Validation**: `financial_tda/validation/CHECKPOINT_REPORT.md`  
**Literature**: Gidea & Katz (2018), MDPI (2025), Guo et al. (2020)

---

## Manager Approval Required

**Questions for Manager**:
1. Approve Option 1 (trend detection) as Phase 8 scope?
2. Defer Options 2-3 to Phase 9, or include in Phase 8?
3. Allocate 2-4 weeks for implementation?
4. Assign Agent_Financial_ML for Phase 8 work?

**Status**: AWAITING MANAGER APPROVAL

---

*Plan Created*: December 15, 2025  
*Dependencies*: Phase 7 Complete (Research Findings Available)  
*Blocking*: None  
*Next Step*: Manager review and approval
