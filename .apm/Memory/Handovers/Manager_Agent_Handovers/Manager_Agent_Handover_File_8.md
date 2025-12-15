---
agent_type: Manager
agent_id: Manager_7
handover_number: 8
current_phase: Phase 7 Ready (Validation & Backtesting)
active_agents: []
---

# Manager Agent Handover File - TDL (Topological Data Analysis Library)

## Active Memory Context

**User Directives:**
- User prefers parallel agent execution when tasks are independent
- User runs multiple agent sessions simultaneously (Financial + Poverty tracks)
- User provides structured task completion reports in YAML format
- User expects Manager to validate test counts and Memory Log completeness before marking tasks done
- Phase 6.5 (TTK Integration) being coordinated separately - do not duplicate those assignments

**Decisions:**
- Phase 6 completed with 6/6 tasks (all visualization dashboards working)
- Phase 6.5 TTK Integration (4 tasks) being handled by separate coordinator
- All pre-commit hooks (ruff, ruff-format) must pass before commits
- Project uses Python 3.11 venv at `.venv/` (system Python 3.13 lacks gtda)
- PyTorch DLL fix template required for all Streamlit dashboards on Windows

## Coordination Status

**Phase 6 COMPLETE ✅ (6/6 tasks):**

| Task | Track | Key Deliverable |
|------|-------|-----------------|
| 6.1 | Financial | streamlit_app.py (1,595 lines), PyTorch DLL fix |
| 6.2 | Financial | regime_compare.py + animation GIF |
| 6.3 | Financial | Real-time monitoring (+1,111 lines, total 2,848) |
| 6.4 | Poverty | maps.py (741 lines), 35K LSOA boundaries |
| 6.5 | Poverty | terrain_3d.py + 13 PNG renders |
| 6.6 | Poverty | dashboard.py (1,100+ lines) |

**Phase 6.5 Status (Handled Separately):**
- Task 6.5.1 ✅ Complete - TTK 1.3.0 installed via conda subprocess
- Tasks 6.5.2, 6.5.3 ⏳ In progress - being coordinated elsewhere
- Task 6.5.4 ⏳ Blocked on 6.5.2/6.5.3

**Producer-Consumer Dependencies for Phase 7:**
- Phase 4 ML models (RegimeClassifier, ChangePointDetector) → Available for 7.1, 7.2 validation
- Phase 5 DL models (RipsGNN, Autoencoder, SpatialGNN, VAE) → Available for integration testing
- Phase 6 dashboards → Available for visual validation during 7.2, 7.4 checkpoints
- Task 4.3 BacktestEngine → Key component for 7.2 crisis validation

## Next Actions

**Phase 7 Ready Assignments:**

| Task | Agent | Objective |
|------|-------|-----------|
| 7.1 | Agent_Financial_ML | Financial System Integration Test |
| 7.2 | Agent_Financial_ML | Crisis Detection Validation **[CHECKPOINT]** |
| 7.3 | Agent_Poverty_ML | Poverty System Integration Test |
| 7.4 | Agent_Poverty_ML | UK Mobility Validation **[CHECKPOINT]** |
| 7.5 | Agent_Docs | Cross-System Comparison & Metrics |

**Parallel Execution Strategy:**
- Tasks 7.1 + 7.3 can run in parallel (different tracks, no dependencies)
- Task 7.2 depends on 7.1, Task 7.4 depends on 7.3
- Task 7.5 depends on both 7.2 and 7.4 (cross-agent dependency)

**Critical Checkpoints:**
- Task 7.2 is a **CRITICAL CHECKPOINT** - user must validate crisis detection results
- Task 7.4 is a **CRITICAL CHECKPOINT** - user must validate UK mobility findings

## Working Notes

**File Patterns:**
- Implementation Plan: `.apm/Implementation_Plan.md`
- Memory Logs: `.apm/Memory/Phase_07_Validation/` (create folder)
- Task prompts follow template in `.github/prompts/apm-3-initiate-implementation.prompt.md`
- Codacy instructions at `.github/instructions/codacy.instructions.md`

**Key Integration Points for Phase 7:**
- `financial_tda/models/regime_classifier.py` - RegimeClassifier for 7.1/7.2
- `financial_tda/models/change_point_detector.py` - ChangePointDetector for 7.2
- `financial_tda/analysis/backtest.py` - BacktestEngine with crisis periods
- `poverty_tda/topology/morse_smale.py` - Morse-Smale complex for 7.3/7.4
- `poverty_tda/analysis/trap_identification.py` - TrapScorer for 7.4

**Crisis Validation Targets (Task 7.2):**
- 2008 GFC: Lehman collapse (2008-09-15)
- 2020 COVID: Market crash (2020-02-20 to 2020-03-23)
- 2022 Rate Hikes: Sell-off (2022-01-03)
- Success metric: Detect regime change ≥5 trading days before peak drawdown

**UK Mobility Validation Targets (Task 7.4):**
- Compare with Social Mobility Commission reports
- Validate against known deprived areas (post-industrial North, coastal towns)
- Cross-reference with "levelling up" target areas

**User Preferences:**
- Prefers concise status tables over prose
- Wants parallel execution for independent tasks
- Expects pre-commit linting to pass before commits
- Values test coverage metrics in completion reports
- CHECKPOINT tasks require explicit user approval before proceeding

**Technical Notes:**
- TTK available via conda subprocess (see `shared/ttk_utils.py`)
- Codacy CLI not installed locally - use ruff for linting
- Some tests skip due to missing external data (acceptable)
- Branch: `feature/phase-5-deep-learning` (consider merge before Phase 7)
