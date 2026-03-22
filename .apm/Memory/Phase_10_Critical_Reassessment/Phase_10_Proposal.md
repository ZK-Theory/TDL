# Phase 10: Financial TDA Critical Reassessment

## Background

Phase 8.1 reported "100% validation success" (τ=0.7931 avg) for Financial TDA trend detection. However, subsequent experiments in Projects A (Sector TDA) and B (Multi-Asset TDA) have revealed serious concerns about reproducibility and potential p-hacking.

## Evidence of Methodology Problems

### Sector Basket Experiments (Project A)

| Event | Configuration | τ | Status |
|-------|---------------|---|--------|
| 2008 GFC | US_4 baseline | +0.88 | ✅ Validated |
| 2008 GFC | Inter-sector (9 ETFs) | +0.49 | ⚠️ Degraded |
| 2020 COVID | US_4 baseline | -0.80 | ❌ FAILURE |
| 2020 COVID | Inter-sector (9 ETFs) | -0.87 | ❌ FAILURE |
| 2022 Rate Shock | Inter-sector (9 ETFs) | -0.95 | ❌ FAILURE |

### Crisis Classification Experiments (Pivot)

| Event | Expected Type | Expected Sign | Actual τ | Correct? |
|-------|---------------|---------------|----------|----------|
| 2008 GFC | Endogenous | Positive | +0.88 | ✅ YES |
| 2010 Flash Crash | Exogenous | Negative | +0.15 | ❌ NO |
| 2011 Debt Crisis | Exogenous | Negative | -0.84 | ✅ YES |
| 2015 China Crash | Exogenous | Negative | +0.07 | ❌ NO |

**Classification Accuracy: 50%** — Below the 80% threshold.

### Key Findings

1. **2008 GFC works robustly** across configurations
2. **2020 COVID fails consistently** except with specific parameter tuning (suspected p-hacking)
3. **Exogenous shocks show variable behavior** — some strongly negative (2011), others near-zero (Flash Crash)
4. **τ magnitude may be more meaningful than sign**

## Critical Assessment of Phase 8.1 Claims

| Phase 8.1 Claim | Evidence | Revised Status |
|-----------------|----------|----------------|
| "100% validation success" | COVID only works with tuned params | ❌ Overstated |
| "τ=0.7123 for COVID" | With standard params: τ = -0.80 | ❌ P-hacked |
| "Parameter optimization essential" | Actually post-hoc fitting | ⚠️ Reframe required |

## Proposed Phase 10 Research Direction

Instead of validating G&K claims, we propose a **fundamental reassessment**:

### Task 10.1: Continuous Signal Analysis
- Compute daily rolling τ for entire 2000-2025 period
- Correlate with VIX, realized volatility, credit spreads
- **Question:** Is τ just a lagged volatility proxy?

### Task 10.2: τ Information Content Assessment
- Regress forward returns on τ + VIX
- Test incremental explanatory power
- **Question:** Does TDA add anything beyond standard volatility measures?

### Task 10.3: Time-Stability Analysis
- Split data into 3 periods (2000-2008, 2008-2016, 2016-2024)
- Test consistency of τ-market relationships
- **Question:** Did G&K cherry-pick a favorable period?

### Task 10.4: Honest Documentation
- Update Memory_Root.md to reflect realistic assessment
- Revise any paper claims dependent on COVID "success"
- Document failures as valid scientific findings

## Success Criteria

- If τ correlates r > 0.8 with VIX: G&K adds nothing new
- If τ provides incremental R² > 0.05 beyond VIX: Worth pursuing
- If relationships unstable across periods: G&K cherry-picked

## Files Created During This Investigation

| File | Location | Purpose |
|------|----------|---------|
| `methodology_reality_check.md` | brain artifacts | Evidence synthesis |
| `pivot_proposal.md` | brain artifacts | Initial pivot framing |
| `implementation_plan_pivot.md` | brain artifacts | Pre-registered experiments |
| `pre_registration.md` | brain artifacts | Locked hypotheses |
| `fundamental_assessment.md` | brain artifacts | New research direction |
| `METHODOLOGY_REFERENCE.md` | financial_tda/docs | Canonical pipeline spec |

## Impact on Phase 8-9 Conclusions

Phase 8.1's claims need revision:
- Remove "100% validation success" language
- Acknowledge COVID as a failure with standard methodology
- Reframe parameter optimization as limitation, not feature

Phase 9 paper drafts may need:
- Revised results section
- Additional limitations discussion
- Potentially new framing entirely
