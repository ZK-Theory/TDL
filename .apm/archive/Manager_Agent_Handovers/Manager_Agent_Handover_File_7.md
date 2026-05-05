---
agent_type: Manager
agent_id: Manager_7
handover_number: 7
current_phase: Phase 6 (Visualization) + Phase 6.5 (TTK Integration)
active_agents: [Agent_Financial_Viz (Task 6.3), Agent_Foundation (Task 6.5.1)]
---

# Manager Agent Handover File - TDL (Topological Data Analysis Library)

## Active Memory Context

**User Directives:**
- User prefers parallel agent execution when tasks are independent
- User runs multiple agent sessions simultaneously (Financial + Poverty tracks)
- User provides structured task completion reports in YAML format
- User expects Manager to validate test counts and Memory Log completeness before marking tasks done
- User requested Phase 6.5 (TTK Integration) addition mid-Phase 6

**Decisions:**
- Phase 6 executed with parallel tracks: Financial (6.1, 6.2, 6.3) + Poverty (6.4, 6.5, 6.6)
- Created Phase 6.5 (TTK Integration) with 4 tasks between Phase 6 and Phase 7
- All pre-commit hooks (ruff, ruff-format) must pass before commits
- Project uses Python 3.11 venv at `.venv/` (system Python 3.13 lacks gtda)
- PyTorch DLL fix template documented in Task 6.1 - MUST be applied to all Streamlit dashboards

## Coordination Status

**Phase 6 Completion Status (6/6 tasks complete) ✅:**

| Task | Agent | Status | Key Deliverable |
|------|-------|--------|-----------------|
| 6.1 Streamlit Dashboard | Agent_Financial_Viz | ✅ Complete | streamlit_app.py (1,595 lines) |
| 6.2 ParaView Regime | Agent_Financial_Viz | ✅ Complete | regime_compare.py + animation |
| 6.3 Real-time Monitoring | Agent_Financial_Viz | ✅ Complete | +1,111 lines (total 2,848) |
| 6.4 Interactive Map | Agent_Poverty_Viz | ✅ Complete | maps.py (741 lines) |
| 6.5 ParaView 3D Terrain | Agent_Poverty_Viz | ✅ Complete | terrain_3d.py + 13 PNGs |
| 6.6 Basin Dashboard | Agent_Poverty_Viz | ✅ Complete | dashboard.py (1,100+ lines) |

**Phase 6.5 Status (0/4 tasks complete):**

| Task | Agent | Status | Scope |
|------|-------|--------|-------|
| 6.5.1 TTK Installation | Agent_Foundation | ⏳ Assigned | Install TTK, resolve VTK conflicts |
| 6.5.2 Financial TTK Hybrid | Agent_Financial_Topology | ⏳ Ready | Depends on 6.5.1 |
| 6.5.3 Poverty TTK Direct | Agent_Poverty_Topology | ⏳ Ready | Depends on 6.5.1 |
| 6.5.4 TTK Visualization | Agent_Financial_Viz | ⏳ Ready | Depends on 6.5.2, 6.5.3 |

**Producer-Consumer Dependencies:**
- Task 6.5.1 outputs (TTK installation) → Required for Tasks 6.5.2, 6.5.3, 6.5.4
- Task 6.1 PyTorch DLL fix → Already applied to Task 6.6, document for future dashboards
- Phase 5 ML models → Available for Phase 6 dashboards (already integrated)
- Phase 6 visualization outputs → Will feed into Phase 7 validation reports

**Coordination Insights:**
- Agents work best with step-by-step prompts (4-6 steps per task)
- Agents need explicit venv activation instructions (`source .venv/Scripts/activate`)
- CHECKPOINT steps require pause for user review before proceeding
- Memory Logs occasionally need manual population reminder
- Cross-agent dependency context must include specific file paths and integration steps

## Next Actions

**Active Assignments (Awaiting Completion):**
- Task 6.3 → Agent_Financial_Viz: Real-time monitoring interface (prompt sent)
- Task 6.5.1 → Agent_Foundation: TTK installation & environment (prompt sent)

**Ready Assignments (After 6.5.1 completes):**
- Task 6.5.2 → Agent_Financial_Topology: Financial TTK hybrid implementation
- Task 6.5.3 → Agent_Poverty_Topology: Poverty TTK direct integration

**Phase Transition Notes:**
- Once Task 6.3 completes, Phase 6 is DONE - append summary to Memory_Root.md
- Once Tasks 6.5.1-6.5.4 complete, Phase 6.5 is DONE - append summary to Memory_Root.md
- Branch: `feature/phase-5-deep-learning` (consider creating new branch for Phase 6.5)
- Consider merging to main after Phase 6 + 6.5 complete, before Phase 7

## Working Notes

**File Patterns:**
- Implementation Plan: `.apm/Implementation_Plan.md`
- Memory Logs: `.apm/Memory/Phase_0X_Name/Task_X_Y_Name.md`
- Phase 6.5 Memory: `.apm/Memory/Phase_06_5_TTK_Integration/`
- Task prompts follow template in `.github/prompts/apm-3-initiate-implementation.prompt.md`
- Codacy instructions at `.github/instructions/codacy.instructions.md`

**Coordination Strategies:**
- Create task assignment prompts with comprehensive cross-agent dependency context
- Include specific file paths for agents to read
- Specify test count expectations and coverage targets
- Remind agents to use project venv (Python 3.11)
- For Streamlit tasks: include PyTorch DLL fix template

**User Preferences:**
- Prefers concise status tables over prose
- Wants parallel execution for independent tasks
- Expects pre-commit linting to pass before commits
- Values test coverage metrics in completion reports
- Appreciates structured YAML task reports

**Technical Notes:**
- Codacy CLI not installed locally (404 errors) - use ruff for linting
- torch-geometric requires special installation (--no-build-isolation)
- Some tests skip due to missing external data (acceptable)
- TTK currently not in ParaView 6.0.1 - Task 6.5.1 will resolve
- Current ParaView path: `C:/Program Files/ParaView 6.0.1/`

**Critical Cross-Agent Information:**
- **PyTorch DLL Fix**: Windows Python 3.8+ requires `os.add_dll_directory()` for torch/lib BEFORE importing torch, which must happen BEFORE any project module imports. Template in Task 6.1 Memory Log.
- **TTK Integration Guide**: Existing research in `financial_tda/viz/paraview_scripts/TTK_INTEGRATION.md`
- **VTK Version**: Project uses 9.5.2 via pyvista, TTK may require different version
