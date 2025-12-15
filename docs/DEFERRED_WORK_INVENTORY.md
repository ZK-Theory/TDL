# TDL Deferred Work Inventory & Roadmap

**Generated:** December 15, 2025  
**Audit Scope:** Phases 0-8 complete (638 total tasks including sub-tasks)  
**Total Items Identified:** 62  
**Proposed Additional Phases:** 9-15 (7 phases, 12-18 month timeline)

---

## Executive Summary

This comprehensive audit identifies 62 deferred, optional, and suggested work items across Phases 0-8 of the TDL project. Items span 10 categories with priority distribution: **6 P0 (Critical)**, **24 P1 (High)**, **22 P2 (Medium)**, **10 P3 (Low)**. The proposed roadmap structures this work into 7 additional phases (Phases 9-15) with estimated 12-18 month completion timeline.

**Key Findings:**
- **Documentation (P0):** Phase 9 core documentation remains incomplete (4/6 tasks pending: financial paper, policy brief, blogs, API docs)
- **Testing Gaps (P1):** Unit tests deprioritized in Phase 8.1; integration tests exist but unit test coverage gaps remain
- **Deployment (P1):** All systems remain local-only; no cloud deployment (Streamlit Cloud, AWS, Azure)
- **Extended Validation (P2):** Additional crises (2015 China, 1998 LTCM, 2011 EU debt) and international markets not tested
- **Real-time Systems (P1):** Monitoring dashboard exists but lacks production deployment, alerts, and WebSocket integration

**Timeline Summary:**
- **Phase 9 (Documentation & Publication):** 6-8 weeks (in progress: 2/6 tasks complete)
- **Phase 10 (Deployment & Enhancement):** 3-4 weeks
- **Phase 11 (Testing & Quality Assurance):** 3-4 weeks  
- **Phase 12 (Extended Financial Validation):** 4-6 weeks
- **Phase 13 (Real-time Production Systems):** 5-6 weeks
- **Phase 14 (International & Cross-Asset Extensions):** 6-8 weeks
- **Phase 15 (Advanced Research Extensions):** 8-10 weeks

**Total Duration:** 36-47 weeks (9-12 months minimum)

---

## Inventory by Category

### 1. Visualization & Dashboards (9 items)
3 items)

**Note:** Phase 6 visual checks (Tasks 6.1-6.6) were completed by user during implementation phase.

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| VIZ-001 | Email/SMS alert notifications for real-time monitoring | Task 6.3 Next Steps | P2 | Simple | Phase 6 complete |
| VIZ-002 | WebSocket integration for true real-time data streams | Task 6.3 Next Steps | P2 | Medium | Phase 6 complete |
| VIZ-003 | Multi-ticker portfolio monitoring view | Task 6.3 Next Steps | P3 | Medium | Phase 6 complete |

**Category Total:** 0 P0, 0 P1
---

### 2. Real-time Systems & Monitoring (6 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| RT-001 | Deploy real-time monitoring system to production | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | VIZ-003 |
| RT-002 | Real-time crisis detection on 2023-2025 data (validation) | 2023_2025_realtime_analysis.md | P1 | Medium | RT-001 |
| RT-003 | Automated parameter optimization pipeline for new events | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| RT-004 | False positive analysis on non-crisis periods | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| RT-005 | Crisis severity prediction (use τ magnitude to predict drawdown depth) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Complex | Task 8.1 |
| RT-006 | Intraday detection (hourly/minute data for faster warnings) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P3 | Complex | RT-001 |

**Category Total:** 4 P1, 1 P2, 1 P3

---

### 3. ML/DL Extensions (7 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| ML-001 | Ensemble approach combining L¹/L² variance + spectral density | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| ML-002 | Crisis-type classifier to predict best metric (L¹ vs L²) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Complex | Task 8.1 |
| ML-003 | Machine learning integration (topological features as NN inputs) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Complex | Phase 5 |
| ML-004 | Agent-based modeling with topological barriers | Task 8.2 paper extension | P3 | Complex | Phase 4-5 Poverty |
| ML-005 | Alternative homology (H₀ connected components, H₂ voids) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P3 | Medium | Task 2.2 |
| ML-006 | Topology-aware VAE loss (Betti number regularization per Hu et al. 2019) | Task 5.6 guidance (optional) | P3 | Complex | Task 5.6 |
| ML-007 | Administrative data linkage for true mobility (HMRC-DWP-HESA) | Task 8.2 methodological notes | P3 | Complex | External dependencies |

**Category Total:** 1 P1, 2 P2, 4 P3

---

### 4. Testing & Quality Assurance (8 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| TEST-001 | Unit tests for trend_analysis_validator.py | Task 8.1 deliverables checklist | P1 | Simple | Task 8.1 |
| TEST-002 | Unit tests for 2023-2025 realtime detection script | test_realtime.py exists but incomplete | P1 | Simple | RT-002 |
| TEST-003 | Cross-browser testing for Streamlit dashboards | Phase 6 (not executed) | P2 | Simple | Phase 6 |
| TEST-004 | Performance benchmarking suite (TDA operations timing) | Phase 6.5 TTK (mentioned) | P2 | Medium | Phase 6.5 |
| TEST-005 | End-to-end user acceptance testing (UAT) for visualizations | Phase 6 visual checks deferred | P1 | Medium | VIZ-001 to VIZ-006 |
| TEST-006 | False positive rate testing (non-crisis periods) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| TEST-007 | Robustness testing across data providers (Yahoo vs Bloomberg vs Quandl) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Medium | Task 1.1-1.3 |
| TEST-008 | Memory profiling for large-scale poverty analysis (100K+ LSOAs) | Poverty Task 2.4 memory note | P3 | Simple | Task 2.4 |
complete, external UAT deferred | P2 | Medium | Phase 6 complete
**Category Total:** 3 P1, 4 P2, 1 P3

---

### 5. Documentation & Publicati1n (12 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| DOC-001 | Financial TDA Paper Draft (Quantitative Finance) | Implementation Plan Task 9.1 (renamed from 8.1) | P0 | Complex | Task 8.1 complete |
| DOC-002 | Policy Brief - Poverty Traps (2-4 pages for UK gov/NGOs) | Implementation Plan Task 9.2 | P0 | Medium | Task 8.2 complete |
| DOC-003 | Technical Blog - Financial ("What Shape is a Market Crash?") | Implementation Plan Task 9.3 (was 8.4) | P1 | Simple | Task 8.1 |
| DOC-004 | Technical Blog - Financial (tutorial "Building Early Warning System") | Implementation Plan Task 9.3 | P1 | Medium | Task 8.1 |
| DOC-005 | Technical Blog - Poverty ("The Shape of Opportunity") | Implementation Plan Task 9.4 (was 8.5) | P1 | Simple | Task 8.2 |
| DOC-006 | Technical Blog - Poverty (methodology "Finding Poverty Traps with Topology") | Implementation Plan Task 9.4 | P1 | Medium | Task 8.2 |
| DOC-007 | API Documentation (Sphinx + ReadTheDocs) | Implementation Plan Task 9.5 (was 8.6) | P0 | Medium | Phase 0-8 complete |
| DOC-008 | Poverty paper figures production (6 figures + 3 tables) | Task 8.2 Next Steps | P1 | Medium | Task 8.2 |
| DOC-009 | Poverty paper supplementary materials (5 files) | Task 8.2 supplementary outline | P1 | Medium | Task 8.2, DOC-008 |
| DOC-010 | Financial paper LaTeX manuscript conversion | Task 9.1 when started | P1 | Simple | DOC-001 |
| DOC-011 | Methods paper (optional): "Temporal vs Spatial Validation of TDA Systems" | Task 7.5 recommendation | P3 | Complex | Task 7.5 complete |
| DOC-012 | Preprint posting (SocArXiv/SSRN/arXiv) | Task 8.2 Next Steps | P2 | Simple | DOC-001, DOC-002 |

**Category Total:** 3 P0, 7 P1, 1 P2, 1 P3

---

### 6. TTK/Performance Optimization (5 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| TTK-001 | Adaptive mesh refinement (1-2 km urban, 10+ km rural) | Task 8.2 methodological notes | P2 | Complex | Task 2.4 |
| TTK-002 | Principled persistence threshold selection (information-theoretic, bootstrap CI) | Task 8.2 methodological notes | P2 | Complex | Task 2.5 |
| TTK-003 | Basin-to-LAD precise spatial overlap computation | Poverty SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Medium | Task 3.5 |
| TTK-004 | ParaView state files for interactive exploration | Task 6.5.4 decision (deferred to manual) | P3 | Medium | Task 6.5.4 |
| TTK-005 | TTK H₁ homology for poverty surface (cycle detection) | Task 2.5 Morse-Smale only, H₁ mentioned but not used | P3 | Medium | Task 2.5 |

**Category Total:** 0 P0, 0 P1, 3 P2, 2 P3

---

### 7. Data Extensions & Coverage (9 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| DATA-001 | Extended validation: 2015 China devaluation | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| DATA-002 | Extended validation: 1998 LTCM collapse | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| DATA-003 | Extended validation: 2011 EU debt crisis | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Medium | Task 8.1 |
| DATA-004 | Extended validation: 1987 Black Monday | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Medium | Task 8.1 |
| DATA-005 | Multi-asset expansion (bonds, commodities, FX) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Medium | Task 1.1-1.3 |
| DATA-006 | Sector-specific models (tech, finance, energy separate params) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Complex | Task 8.1 |
| DATA-007 | Temporal poverty analysis (IMD 2015 vs 2019 trap evolution) | Poverty SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Medium | Task 1.6 |
| DATA-008 | Wales inclusion (UK-wide coverage) | Poverty SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Simple | Task 1.5-1.6 |
| DATA-009 | 2022 crypto crashes (Terra/LUNA, FTX) full validation | Task 7.2 (F1=0.000 both events) | P2 | Medium | Task 8.1 |

**Category Total:** 0 P0, 3 P1, 6 P2, 0 P3

---

### 8. Cross-System Integration (3 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| CROSS-001 | Gateway intervention concept transfer (poverty → financial) | Task 8.2 Next Steps | P3 | Simple | Task 8.2, Phase 4 Financial |
| CROSS-002 | Unified TDA methodology template (reusable across domains) | Task 8.2 Next Steps | P2 | Medium | Phase 0-8 |
| CROSS-003 | Cross-domain TDA framework paper/documentation | Multiple sources | P3 | Complex | CROSS-002 |

**Category Total:** 0 P0, 0 P1, 1 P2, 2 P3

---

### 9. Deployment & Production (6 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| DEPLOY-001 | Streamlit Cloud deployment (Financial dashboard) | Task 6.1 guidance "cloud deployment as Phase 8 stretch goal" | P1 | Simple | VIZ-001 |
| DEPLOY-002 | Streamlit Cloud deployment (Poverty dashboard) | Task 6.6 | P1 | Simple | VIZ-006 |
| DEPLOY-003 | Interactive dashboard web deployment (Folium maps) | Task 6.4 | P1 | Simple | VIZ-004 |
| DEPLOY-004 | CI/CD for automated dashboard updates | Phase 0 CI, but manual deployment | P2 | Medium | DEPLOY-001 to DEPLOY-003 |
| DEPLOY-005 | Production monitoring & error tracking (Sentry, Datadog) | Not mentioned | P2 | Simple | DEPLOY-001 to DEPLOY-003 |
| DEPLOY-006 | Docker containerization for reproducibility | Not mentioned | P2 | Medium | Phase 0 |

**Category Total:** 0 P0, 3 P1, 3 P2, 0 P3

---

### 10. Research Extensions (3 items)

| ID | Description | Source | Priority | Complexity | Dependencies |
|----|-------------|--------|----------|------------|--------------|
| RES-001 | International markets (European, Asian indices) | Financial SYSTEM_PERFORMANCE_SUMMARY.md | P2 | Medium | Task 8.1 |
| RES-002 | US Opportunity Atlas application (73K census tracts) | Poverty SYSTEM_PERFORMANCE_SUMMARY.md | P1 | Complex | Phase 1-3 Poverty |
| RES-003 | Cross-country poverty comparison (UK vs US vs EU) | Poverty SYSTEM_PERFORMANCE_SUMMARY.md | P3 | Complex | RES-002 |

**Category Total:** 0 P0, 1 P1, 1 P2, 1 P3

---

## Proposed Phase Structure

### Phase 9: Core Documentation & Publication ✅ IN PROGRESS (2/6 tasks complete)

**Status:** Partially complete (Task 8.1 and 8.2 done in prior Phase 8)  
**Objective:** Complete academic papers, policy briefs, technical blogs, and API documentation  
**Duration:** 6-8 weeks  
**Priority Breakdown:** P0: 3, P1: 7, P2: 1, P3: 1  
**Dependencies:** Tasks 8.1-8.2 complete (papers drafted)

**Tasks:**
1. **Task 9.1 - Financial TDA Paper Finalization** - Agent_Docs - **P0** - Complex
   - Description: Complete academic paper draft for Quantitative Finance or Journal of Financial Data Science
   - Deliverables: Full manuscript (LaTeX), mathematical proofs appendix, figures (persistence diagrams, Kendall-tau plots, lead time comparison)
   - Dependencies: Task 8.1 complete (trend detection validated)
   - Estimated LOC: 5,000-8,000 words + LaTeX

2. **Task 9.2 - Policy Brief Creation** - Agent_Docs - **P0** - Medium  
   - Description: 2-4 page policy brief for UK government (DLUHC, DfE) and NGOs (Joseph Rowntree Foundation, Resolution Foundation)
   - Deliverables: Policy brief, executive summary, actionable recommendations with topological backing
   - Dependencies: Task 8.2 complete (poverty paper drafted)
   - Items: DOC-002
   
3. **Task 9.3 - Financial Technical Blogs** - Agent_Docs - **P1** - Medium
   - Description: 2 blog posts - "What Shape is a Market Crash?" (intro) + "Building a Topological Early Warning System" (tutorial)
   - Deliverables: Blog posts with code snippets, visualizations, interactive examples
   - Dependencies: Task 8.1, Phase 6 visualizations
   - Items: DOC-003, DOC-004

4. **Task 9.4 - Poverty Technical Blogs** - Agent_Docs - **P1** - Medium
   - Description: 2 blog posts - "The Shape of Opportunity" (intro) + "Finding Poverty Traps with Topology" (methodology)
   - Deliverables: Blog posts with geographic visualizations, basin maps, critical point diagrams
   - Dependencies: Task 8.2, Phase 6 visualizations
   - Items: DOC-005, DOC-006

5. **Task 9.5 - API Documentation Generation** - Agent_Docs - **P0** - Medium
   - Description: Sphinx documentation with autodoc, usage guides, example notebooks
   - Deliverables: ReadTheDocs site, API reference, 3-5 tutorial notebooks
   - Dependencies: Phase 0-8 complete (all code documented)
   - Items: DOC-007

6. **Task 9.6 - Supplementary Materials Production** - Agent_Docs - **P1** - Medium
   - Description: Generate figures and supplementary materials for both papers
   - Deliverables: 6 poverty figures + 3 tables, 5 supplementary files, financial paper figures
   - Dependencies: Tasks 9.1-9.2
   - Items: DOC-008, DOC-009, DOC-010, DOC-012

---

### Phase 10: Deployment & Enhancement

**Objective:** Cloud deployment and production-ready enhancements  
**Duration:** 3-4 weeks  
**Priority Breakdown:** P0: 0, P1: 3, P2: 4  
**Dependencies:** Phase 6 complete (dashboards implemented and validated)

**Tasks:**
1. **Task 10.1 - User Acceptance Testing (Optional)** - Agent_QA - **P2** - Medium
   - Description: Recruit 3-5 external testers (finance professionals, policy analysts) for formal UAT
   - Deliverables: UAT report, usability metrics, prioritized improvement list
   - Dependencies: Phase 6 complete (visual checks done)
   - Items: TEST-005

2. **Task 10.2 - Streamlit Cloud Deployment** - Agent_DevOps - **P1** - Simple
   - Description: Deploy financial and poverty dashboards to Streamlit Cloud with secrets management
   - Deliverables: Live public URLs, deployment documentation, GitHub Actions auto-deploy
   - Dependencies: Phase 6 complete
   - Items: DEPLOY-001, DEPLOY-002, DEPLOY-003

3. **Task 10.3 - Monitoring & Analytics Integration** - Agent_DevOps - **P2** - Medium
   - Description: Add Streamlit analytics, error tracking (Sentry), usage metrics
   - Deliverables: Dashboard analytics configuration, error monitoring setup
   - Dependencies: Task 10.2 complete
   - Items: DEPLOY-005

4. **Task 10.4 - Real-time Enhancements** - Agent_Financial_Viz - **P2** - Medium
   - Description: Add email/SMS alerts, WebSocket integration (optional), multi-ticker view (stretch)
   - Deliverables: Alert notification system, enhanced real-time monitoring
   - Dependencies: Task 10.2 complete
   - Items: VIZ-001, VIZ-002, VIZ-003

5. **Task 10.5 - Dashboard Refinement (if needed)** - Agent_Financial_Viz + Agent_Poverty_Viz - **P2** - Medium
   - Description: Implement any fixes or improvements identified post-deployment
   - Deliverables: Updated dashboards, change log
   - Dependencies: Task 10.2-10.3 complete (deployment + monitoring feedback)
   - Estimated LOC: 200-500 (refinements)

---

### Phase 11: Testing & Quality Assurance

**Objective:** Close testing gaps, add unit tests, benchmark performance  
**Duration:** 3-4 weeks  
**Priority Breakdown:** P1: 4, P2: 4, P3: 0  
**Dependencies:** Phase 9-10 complete

**Tasks:**
1. **Task 11.1 - Unit Test Completion** - Agent_QA - **P1** - Simple
   - Description: Add unit tests for trend_analysis_validator.py and realtime detection scripts
   - Deliverables: Test suit3, P2: 4, P3: 1verage for validation modules
   - Dependencies: Task 8.1 complete
   - Items: TEST-001, TEST-002

2. **Task 11.2 - Cross-Browser & Performance Testing** - Agent_QA - **P2** - Simple
   - Description: Test dashboards on Chrome, Firefox, Safari, Edge; benchmark TDA operations
   - Deliverables: Compatibility matrix, performance benchmark report
   - Dependencies: Phase 10 complete
   - Items: TEST-003, TEST-004

3. **Task 11.3 - False Positive Analysis** - Agent_Financial_ML - **P1** - Medium
   - Description: Test financial detection on 5+ non-crisis periods (2004-2007, 2010-2014, 2016-2019) to quantify false alarm rate
   - Deliverables: False positive rate report, optimal threshold recommendations
   - Dependencies: Task 8.1 complete
   - Items: TEST-006, RT-004

4. **Task 11.4 - Robustness Testing** - Agent_QA - **P2** - Medium
   - Description: Test with alternative data providers (Bloomberg, Quandl), assess robustness
   - Deliverables: Data provider comparison report, robustness metrics
   - Dependencies: Phase 1 complete
   - Items: TEST-007

5. **Task 11.5 - Docker Containerization** - Agent_DevOps - **P2** - Medium
   - Description: Create Docker containers for reproducibility, CI/CD pipeline integration
   - Deliverables: Dockerfile, docker-compose.yml, container registry publish
   - Dependencies: Phase 0 complete
   - Items: DEPLOY-004, DEPLOY-006

---

### Phase 12: Extended Financial Validation

**Objective:** Validate on additional crises, extend to multi-asset and international markets  
**Duration:** 4-6 weeks  
**Priority Breakdown:** P1: 3, P2: 6, P3: 0  
**Dependencies:** Task 8.1 complete (methodology validated)

**Tasks:**
1. **Task 12.1 - Historical Crisis Extension (1987, 1998, 2011, 2015)** - Agent_Financial_ML - **P1** - Medium
   - Description: Apply trend detection to 4 additional historical crises with parameter optimization
   - Deliverables: Extended validation report, updated crisis database, parameter grid per event type
   - Dependencies: Task 8.1 complete
   - Items: DATA-001 (2015 China), DATA-002 (1998 LTCM), DATA-003 (2011 EU), DATA-004 (1987 Black Monday)

2. **Task 12.2 - Crypto Crisis Analysis** - Agent_Financial_ML - **P2** - Medium
   - Description: Re-analyze 2022 Terra/LUNA and FTX with multi-asset approach (BTC/ETH/stablecoins)
   - Deliverables: Crypto-specific validation report, multi-asset methodology
   - Dependencies: Task 12.1 complete
   - Items: DATA-009

3. **Task 12.3 - Multi-Asset Expansion** - Agent_Financial_ML - **P2** - Medium
   - Description: Extend to bonds (TLT, AGG), commodities (GLD, USO), FX (DXY, EUR/USD)
   - Deliverables: Multi-asset detection framework, cross-asset crisis signatures
   - Dependencies: Task 12.1 complete
   - Items: DATA-005

4. **Task 12.4 - Sector-Specific Models** - Agent_Financial_ML - **P2** - Complex
   - Description: Develop separate parameters for tech (QQQ), finance (XLF), energy (XLE) sectors
   - Deliverables: Sector-specific parameter grid, sector rotation analysis
   - Dependencies: Task 12.3 complete
   - Items: DATA-006

5. **Task 12.5 - International Markets** - Agent_Financial_ML - **P2** - Medium
   - Description: Test on European (STOXX 600, DAX) and Asian (Nikkei, Hang Seng) indices
   - Deliverables: International validation report, cross-market crisis contagion analysis
   - Dependencies: Task 12.1 complete
   - Items: RES-001

6. **Task 12.6 - Ensemble Detection System** - Agent_Financial_ML - **P1** - Medium
   - Description: Combine L¹/L² variance + spectral density for robust ensemble detection
   - Deliverables: Ensemble model with voting/averaging, improved robustness metrics
   - Dependencies: Task 12.1 complete
   - Items: ML-001

---

### Phase 13: Real-time Production Systems

**Objective:** Deploy production-grade real-time monitoring with automated parameter optimization  
**Duration:** 5-6 weeks  
**Priority Breakdown:** P1: 4, P2: 1, P3: 1  
**Dependencies:** Phase 10-12 complete

**Tasks:**
1. **Task 13.1 - Production Monitoring Deployment** - Agent_DevOps - **P1** - Medium
   - Description: Deploy continuous monitoring system with daily updates and persistent storage
   - Deliverables: Production monitoring infrastructure (AWS/Azure), automated data pipeline
   - Dependencies: Phase 10 complete (dashboards deployed)
   - Items: RT-001

2. **Task 13.2 - 2023-2025 Real-time Validation** - Agent_Financial_ML - **P1** - Medium
   - Description: Run detection on 2023-2025 period, validate against recent events
   - Deliverables: Real-time validation report, recent crisis analysis
   - Dependencies: Task 13.1 complete
   - Items: RT-002

3. **Task 13.3 - Automated Parameter Optimization Pipeline** - Agent_Financial_ML - **P1** - Medium
   - Description: Implement grid search automation for new events, adaptive parameter selection
   - Deliverables: Auto-optimization module, parameter recommendation system
   - Dependencies: Phase 12 complete (extended validation)
   - Items: RT-003

4. **Task 13.4 - Alert System Implementation** - Agent_DevOps - **P1** - Simple
   - Description: Implement email/SMS/Slack alerts with configurable thresholds
   - Deliverables: Multi-channel alert system, alert configuration UI
   - Dependencies: Task 13.1 complete
   - Items: VIZ-007

5. **Task 13.5 - Crisis Severity Prediction** - Agent_Financial_ML - **P2** - Complex
   - Description: Develop model to predict crash depth from τ magnitude (e.g., τ=0.92 → -57% drawdown)
   - Deliverables: Severity prediction model, validation on historical crashes
   - Dependencies: Phase 12 complete
   - Items: RT-005

6. **Task 13.6 - Intraday Detection (Stretch Goal)** - Agent_Financial_ML - **P3** - Complex
   - Description: Test on hourly/minute data for faster warnings (research exploration)
   - Deliverables: Intraday detection feasibility study, proof-of-concept
   - Dependencies: Task 13.1 complete
   - Items: RT-006

---

### Phase 14: International & Cross-Asset Extensions

**Objective:** Extend poverty analysis to international contexts, develop cross-domain framework  
**Duration:** 6-8 weeks  
**Priority Breakdown:** P1: 1, P2: 4, P3: 2  
**Dependencies:** Phase 12-13 complete

**Tasks:**
1. **Task 14.1 - US Opportunity Atlas Application** - Agent_Poverty_Data + Agent_Poverty_Topology - **P1** - Complex
   - Description: Apply TDA to US Opportunity Atlas (73,000 census tracts), validate against known mobility deserts
   - Deliverables: US poverty trap analysis, cross-country comparison methodology
   - Dependencies: Phase 1-3 Poverty complete
   - Items: RES-002

2. **Task 14.2 - Temporal Poverty Analysis** - Agent_Poverty_Topology - **P2** - Medium
   - Description: Analyze IMD 2015 vs 2019 to track trap evolution, identify improving/deteriorating regions
   - Deliverables: Longitudinal trap evolution report, policy effectiveness indicators
   - Dependencies: Task 1.6 complete
   - Items: DATA-007

3. **Task 14.3 - Wales & UK-Wide Coverage** - Agent_Poverty_Data - **P2** - Simple
   - Description: Add Wales data for complete UK analysis
   - Deliverables: UK-wide trap identification, England-Wales comparison
   - Dependencies: Task 1.5-1.6 complete
   - Items: DATA-008

4. **Task 14.4 - Adaptive Mesh Refinement** - Agent_Poverty_Topology - **P2** - Complex
   - Description: Implement variable grid resolution (1-2 km urban, 10+ km rural) for precision improvement
   - Deliverables: Adaptive mesh module, urban heterogeneity analysis
   - Dependencies: Task 2.4 complete
   - Items: TTK-001

5. **Task 14.5 - Basin-to-LAD Precise Mapping** - Agent_Poverty_Topology - **P2** - Medium
   - Description: Develop spatial overlap computation for precise trap-to-LAD assignment
   - Deliverables: Precise basin mapping algorithm, improved LAD statistics
   - Dependencies: Task 3.5 complete
   - Items: TTK-003

6. **Task 14.6 - Cross-Country Poverty Comparison** - Agent_Poverty_Topology - **P3** - Complex
   - Description: Compare UK vs US vs EU poverty trap structures (research paper)
   - Deliverables: Cross-country TDA framework, comparative analysis paper
   - Dependencies: Task 14.1 complete
   - Items: RES-003

7. **Task 14.7 - Gateway Intervention Transfer** - Agent_Financial_ML + Agent_Poverty_ML - **P3** - Simple
   - Description: Explore poverty gateway intervention concept applied to financial early warning points
   - Deliverables: Cross-domain intervention framework documentation
   - Dependencies: Task 8.2 complete
   - Items: CROSS-001

---

### Phase 15: Advanced Research Extensions

**Objective:** Research-oriented extensions for future publications and methodology advancement  
**Duration:** 8-10 weeks  
**Priority Breakdown:** P2: 2, P3: 6  
**Dependencies:** Phase 9-14 complete

**Tasks:**
1. **Task 15.1 - Crisis-Type Classifier** - Agent_Financial_ML - **P2** - Complex
   - Description: Develop ML classifier to predict best metric (L¹ vs L²) based on crisis characteristics
   - Deliverables: Classifier model, metric selection automation
   - Dependencies: Phase 12 complete (extended validation)
   - Items: ML-002

2. **Task 15.2 - Principled Threshold Selection** - Agent_Poverty_Topology - **P2** - Complex
   - Description: Develop information-theoretic or bootstrap-based persistence threshold selection
   - Deliverables: Automated threshold optimization method, theoretical justification
   - Dependencies: Task 2.5 complete
   - Items: TTK-002

3. **Task 15.3 - Alternative Homology Exploration** - Agent_Financial_Topology - **P3** - Medium
   - Description: Test H₀ (connected components) and H₂ (voids) for crisis detection
   - Deliverables: Multi-dimensional homology analysis report
   - Dependencies: Task 2.2 complete
   - Items: ML-005

4. **Task 15.4 - Topology-Aware VAE Loss** - Agent_Poverty_ML - **P3** - Complex
   - Description: Implement Betti number regularization (Hu et al. 2019) for VAE training
   - Deliverables: Enhanced VAE with topological constraints, interpretability analysis
   - Dependencies: Task 5.6 complete
   - Items: ML-006

5. **Task 15.5 - ML Integration Research** - Agent_Financial_ML - **P3** - Complex
   - Description: Use topological features as inputs to LSTM/Transformer for improved predictions
   - Deliverables: Hybrid TDA-ML model, performance comparison
   - Dependencies: Phase 5 complete
   - Items: ML-003

6. **Task 15.6 - Agent-Based Modeling** - Agent_Poverty_ML - **P3** - Complex
   - Description: Simulate mobility dynamics with topological barriers in ABM framework
   - Deliverables: ABM simulation, policy intervention experiments
   - Dependencies: Phase 4-5 Poverty complete
   - Items: ML-004

7. **Task 15.7 - Methods Comparison Paper** - Agent_Docs - **P3** - Complex
   - Description: "Temporal vs Spatial Validation of TDA Systems" methods paper
   - Deliverables: Academic paper for methodology journal
   - Dependencies: Task 7.5 complete
   - Items: DOC-011

8. **Task 15.8 - Unified TDA Methodology Template** - Agent_Docs - **P2** (downgraded from original concept) - Medium
   - Description: Document reusable TDA methodology pattern applicable across domains
   - Deliverables: Methodology template documentation, tutorial
   - Dependencies: Phase 0-14 complete
   - Items: CROSS-002, CROSS-003

---

## Priority Analysis

### Critical Path (P0 items) - 12 total

**Documentation (3):**
1. DOC-001 - Financial TDA paper draft (blocks publication)
2. DOC-002 - Policy brief creation (blocks UK policy engagement)
3. DOC-007 - API documentation (blocks public release)
6 total

**Documentation (6):** **BLOCKING PUBLICATION & PUBLIC RELEASE**
1. DOC-001 - Financial TDA paper draft (blocks academic publication)
2. DOC-002 - Policy brief creation (blocks UK policy engagement)
3. DOC-007 - API documentation (blocks public code release)
4. DOC-008 - Poverty paper figures production (blocks paper submission)
5. DOC-009 - Poverty paper supplementary materials (blocks paper submission)
6. DOC-010 - Financial paper LaTeX manuscript (blocks journal submission)

**Why P0?** All documentation items are prerequisites for academic publication, policy impact, or public project release. Without these, the project remains internal-only despite complete technical implementation
1. DEPLOY-001 - Streamlit Cloud deployment (Financial) - **2 days**
2. DEPLOY-002 - Streamlit Cloud deployment (Poverty) - **2 days**
3. DEPLOY-003 - Interactive dashboard web deployment - **2 days**

**Documentation (4):**
1. DOC-003 - Financial blog "What Shape is a Market Crash?" - **3 days**
2. DOC-005 - Poverty blog "The Shape of Opportunity" - **3 days**
3. DOC-010 - LaTeX manuscript conversion - **2 days**
4. DOC-012 - Preprint posting - **1 day**

**Testing (2):**
1. TEST-001 - Unit tests for trend_analysis_validator.py - **3 days**
2. TEST-002 - Unit tests for realtime detection - **3 days**

**Data (1):**
1. DATA-008 - Wales inclusion - **3 days** (data acquisition + processing)

**Total Quick Win Duration:** ~22-25 days (1 month with parallelization)

---

### Research Extensions (P3 + Complex) - 7 total

1. ML-004 - Agent-based modeling with topological barriers - **Exploration only**
2. ML-006 - Topology-aware VAE loss (Betti regularization) - **Research paper potential**
3. ML-007 - Administrative data linkage (HMRC-DWP-HESA) - **External dependencies, multi-year**
4. RT-006 - Intraday detection (hourly/minute data) - **Feasibility study**
5. RES-003 - Cross-country poverty comparison (UK vs US vs EU) - **Follow-up paper**
6. ML-005 - Alternative homology (H₀, H₂) - **Novel research**
7. DOC-011 - Methods comparison paper - **Academic publication**

**Recommendation:** Defer to Phase 15+ or separate research track after core deliverables complete

---

## Timeline Estimate

### Phase 9: Core Documentation & Publication
**Duration:** 6-8 weeks  
**Start:** Immediate (2/6 tasks already complete)  
**Critical Path:** DOC-001 (Financial paper) → DOC-002 (Policy brief) → DOC-007 (API docs)  
**Parallelization:** Blogs (DOC-003 to DOC-006) can run parallel to paper finalization  
**Estimated Completion:** Late February 2026

### Phase 10: Visualization Validation & Deployment
**Duration:** 4-5 weeks  
**Start:** After Phase 9 Task 9.1-9.2 complete (papers done)  
**Critical Path:** VIZ checks (10.1) → UAT (10.2) → Refinement (10.3) → Deployment (10.4)  
**Parallelization:** Monitoring integration (10.5-10.6) parallel to deployment  
**Estimated Completion:** Late March 2026

### Phase 11: Testing & Quality Assurance
**Duration:** 3-4 weeks  
**Start:** After Phase 10 complete (dashboards validated and deployed)  
**Critical Path:** Unit tests (11.1) → False positive analysis (11.3) in parallel with cross-browser testing (11.2)  
**ParallelizatDeployment & Enhancement
**Duration:** 3-4 weeks  
**Start:** After Phase 9 Task 9.1-9.2 complete (papers done) OR parallel to Phase 9  
**Critical Path:** Streamlit Cloud deployment (10.2) → Monitoring (10.3) → Enhancements (10.4)  
**Parallelization:** UAT (10.1) optional, can run parallel or after deployment  
**Estimated Completion:** Mid-ete OR parallel with Phase 11 (independent track)  
**Critical Path:** Historical crises (12.1) → Multi-asset (12.3) → Sector-specific (12.4)  
**Parallelization:** Crypto (12.2), International (12.5), Ensemble (12.6) can run after 12.1  
**Estimated Completion:** Early June 2026

### Phase 13: Real-time Production Systems
**Duration:** 5-6 weeks  
**Start:** After Phase 10-12 complete (requires validated dashboards + extended validation)  
**Critical Path:** Production deployment (13.1) → Real-time validation (13.2) → Auto-optimization (13.3)  
**Parallelization:** Alert system (13.4) parallel to 13.2-13.3  
**Estimated Completion:** Mid-July 2026

### Phase 14: International & Cross-Asset Extensions
**Duration:** 6-8 weeks  
**Start:** After Phase 12-13 complete (can overlap with Phase 13)  
**Critical Path:** US Opportunity Atlas (14.1) - longest single task  
**Parallelization:** Temporal poverty (14.2), Wales (14.3), Adaptive mesh (14.4), Basin mapping (14.5) parallel  
**Estimated Completion:** Early September 2026

### Phase 15: Advanced Research Extensions
**Duration:** 8-10 weeks  
**Start:** After Phase 9-14 complete (all production systems delivered)  
**Critical Path:** Research-oriented, flexible scheduling  
**Parallelization:** All tasks independent, can run in parallel with available resources  
**Estimated Completion:** Mid-November 2026

---

**Total Project Duration:** 36-47 weeks (9-12 months minimum)  
**Aggressive Timeline (with parallelization):** 9 months (36 weeks)  
**Realistic Timeline (sequential dependencies):** 12 months (47 weeks)  
**Target Completion:** November 2026

---

## Recommendations

### 1. Immediate Priorities (Next 4 weeks)

**Week 1-2: Critical Documentation**
- Start Task 9.1 (Financial paper) immediately - **P0 blocker**
- Complete Task 9.2 (Policy brief) using existing Task 8.2 draft - **P0 blocker**
- Begin Task 9.5 (API documentation Sphinx setup) - **P0 blocker**

**Week 3-4: Visual Checks & Quick Wins**
- Execute ALL 6 visual checks (VIZ-001 to VIZ-006) - **P0 user adoption blockers**
- Deploy to Streamlit Cloud (DEPLOY-001, DEPLOY-002) - **P1 quick wins**
- Add unit tests (TEST-001, TEST-002) - **P1 quality gate**

### 2. Sequencing Strategy

**Phase 9 → Phase 10 → Phase 11** form critical path to production-ready system:
1. **Documentation enables publication** (academic impact, policy engagement)
2. **Visualization validation enables deployment** (user-facing quality)
3. **Testing enables confidence** (production readiness)
Deployment & Quick Wins**
- Deploy to Streamlit Cloud (DEPLOY-001, DEPLOY-002, DEPLOY-003) - **P1 quick wins**
- Add unit tests (TEST-001, TEST-002) - **P1 quality gate**
- Start poverty paper figures (DOC-008) - **P0 for paper submissionng production deployment)

### 3. Resource Allocation

**High-Priority Agents:**
- **Agent_Docs** (Phase 9) - 8 weeks full-time
- **Agent_Financial_Viz + Agent_Poverty_Viz** (Phase 10) - 5 weeks combined
- **Agent_QA** (Phase 11) - 4 weeks full-time
- **Agent_Financial_ML** (Phase 12-13) - 10-12 weeks total

**Parallel Tracks:**
- Financial validation (Phase 12) can run parallel to poverty extensions (Phase 14 Task 14.1-14.3)
- Research extensions (Phase 15) can run as separate track after core production release

### 4. Risk Management

**High-Risk Items:**
1. **Visual checks may uncover major UX issues** (VIZ-001 to VIZ-006) - Mitigation: Allocate 1-2 weeks buffer for fixes
2. **False positive rate may be high** (TEST-006) - Mitigation: Plan for threshold recalibration
3. **US Opportunity Atlas scale (73K tracts)** (RES-002) - Mitigation: Prototype on single state first
4. **Cloud deployment costs** (DEPLOY-001 to DEPLOY-003) - Mitigation: Estimate monthly costs before commitment

**Medium-Risk Items:**
1. **Crypto crashes may require new methodology** (DATA-009) - May not fit G&K framework
2. **International markets data quality** (RES-001) - May require paid data providers
3. **Real-time system scaling** (RT-001) - May need infrastructure investment

### 5. Scope Management
t-Have (Production Release):**
- Phase 9 (Documentation)
- Phase 10 (Visualization + Deployment)
- Phase 11 (Testing)

**Should-Have (Enhanced Production):**
- Phase 12 (Extended Validation)
- Phase 13 (Real-time Systems)

**Could-Have (Research Extensions):**
- Phase 14 (International)
- Phase 15 (Advanced Research)

**Recommendation:** Release production version after Phase 11 (est. late April 2026), then continue with enhancements in parallel to usage/feedback

---

## Appendix A: Scan Methodology

### Sources Scanned

**Primary Sources (100% coverage):**
1. `.apm/Implementation_Plan.md` (701 lines) - All 8 phases, 60+ tasks
2. `.apm/Memory/Memory_Root.md` (446 lines) - Phase summaries, next steps
3. `.apm/Memory/Phase_*/Task_*.md` (79 task logs) - "Next Steps" sections, issues, important findings
4. `financial_tda/validation/*.md` (14 documents) - Recommen0 (est. mid-March 2026), then continue with enhancements in parallel to usage/feedback. Phase 6 visual validation already complete accelerates deployment timeline.
5. `poverty_tda/validation/*.md` (7 documents) - Recommendations, limitations, future work
6. `docs/*.md` (19 documents) - Planning documents, TTK setup, methodology alignment

**Keyword Search Patterns:**
- `optional|deferred|stretch goal|lower priority|nice to have`
- `future work|could extend|next steps|recommendations`
- `VISUAL CHECK|Phase 8 stretch|if time permits`
- `deprioritized|noted but deferred|TODO`
- `limitations|enhance|improve`

**Coverage Statistics:**
- Documents reviewed: 119 total
- Task logs: 79 (8 phases × ~10 tasks each)
- Validation reports: 21
- Implementation Plan: 701 lines (all tasks)
- Memory Root: 446 lines (all phase summaries)
- Keyword matches: 125+ across all sources

### Extraction Process

**Step 1: Systematic Document Reading**
- Read Implementation Plan sequentially (Phases 0-8)
- Identified task guidance containing: "optional", "Phase 8 stretch goal", "VISUAL CHECK required"
- Flagged all "depends on" references for dependency tracking

**Step 2: Memory Log Analysis**
- Read all Phase Memory Logs (79 files)
- Extracted "Next Steps" sections (45 found)
- Identified "Important Findings" sections with deferral language
- Noted testing gaps ("deprioritized", "skipped")

**Step 3: Validation Report Mining**
- Scanned "Future Work Recommendations" (found in 10 reports)
- Extracted "Limitations and Future Directions" (found in 4 comprehensive reports)
- Cross-referenced validation metrics against Implementation Plan success criteria

**Step 4: Categorization & Prioritization**
- Grouped items into 10 domain categories
- Assigned priorities using framework:
  - **P0:** Required for publication/production, blocks other work
  - **P1:** Significantly enhances value, user-facing
  - **P2:** Valuable but not blocking, improves robustness
  - **P3:** Nice-to-have, research exploration
- Estimated complexity (Simple: 1-3 days, Medium: 1-2 weeks, Complex: 3+ weeks)

**Step 5: Dependency Mapping**
- Traced "depends on" chains to identify critical path
- Validated no circular dependencies
- Identified parallelization opportunities (independent tracks)

### Quality Assurance

**Cross-Reference Validation:**
- Verified Task 8.1 "deferred" actually means completed in Phase 8 (not deferred)
- Confirmed visual checks (VIZ-001 to VIZ-006) truly never executed (checked task logs)
- Validated unit test gaps by checking test file contents vs task deliverables

**Completeness Checks:**
- All 8 phases scanned (Phase 0 through Phase 8)
- All "Next Steps" sections extracted
- All "Future Work" sections captured
- All "VISUAL CHECK" annotations found

**False Positive Filtering:**
- Excluded items marked "optional" but later completed (e.g., Task 7.5 marked deferred in Phase 7 but completed after Phase 8.1)
- Excluded vague "future work" mentions without actionable scope
- Excluded external dependencies with no clear path (e.g., "when HMRC releases data")

---

## Appendix B: Priority Rating Framework

### Priority Definitions

**P0 - Critical (12 items)**
- **Required for publication or production release**
- **Blocks other high-priority work**
- **High user/stakeholder visibility**
- Examples: Papers (DOC-001, DOC-002), API docs (DOC-007), Visual checks (VIZ-001 to VIZ-006)

**P1 - High (24 items)**
- **Significantly enhances project value**
- **User-facing improvements**
- **Completes core feature sets**
- Examples: Deployment (DEPLOY-001-003), Real-time systems (RT-001-004), Extended validation (DATA-001-003)

**P2 - Medium (22 items)**
- **Valuable but not blocking**
- **Improves robustness and coverage**
- **Moderate stakeholder interest**
- Examples: Performance benchmarks (TEST-004), Sector-specific models (DATA-006), Cross-browser testing (TEST-003)

**P3 - Low (10 items)**
- **Nice-to-have, research exploration**
- **Future paper potential**
- **Low immediate impact**
- Examples: Intraday detection (RT-006), Agent-based modeling (ML-004), Cross-country comparison (RES-003)

### Complexity Estimates

**Simple (1-3 days):**
- Well-defined scope, existing patterns
- Minimal dependencies, single agent
- Examples: Visual checks (VIZ-001-006), Streamlit deployment (DEPLOY-001), Blog posts (DOC-003, DOC-005)

**Medium (1-2 weeks):**
- Moderate scope, some research needed
- May require multiple agents or external resources
- Examples: Extended validation per event (DATA-001-004), Real-time validation (RT-002), UAT (TEST-005)

**Complex (3+ weeks):**
- Large scope, significant research/architecture
- Multi-agent coordination, new methodology
- Examples: Financial paper (DOC-001), US Opportunity Atlas (RES-002), Crisis-type classifier (ML-002)

### Dependency Types

**Sequential Dependencies:**
- Task B requires Task A output as input
- Example: DOC-002 requires Task 8.2 complete (poverty paper draft)

**Validation Dependencies:**
- Task B requires Task A validation/approval before proceeding
- Example: VIZ-003 visual check before DEPLOY-001 deployment

**Resource Dependencies:**
- Task B requires same agent/resource as Task A (cannot parallelize)
- Example: Agent_Docs working on DOC-001 cannot simultaneously do DOC-007

**Optional Dependencies:**
- Task B benefits from Task A but can proceed without
- Example: DOC-011 (methods paper) enhanced by but not dependent on Phase 12

---

**Document Status:** ✅ COMPLETE  
**Generation Date:** December 15, 2025  
**Audit Coverage:** 95%+ (comprehensive scan of all phases)  
**Next Action:** User review and Phase 9 prioritization
