---
agent_type: Manager
agent_id: Manager_1
handover_number: 1
current_phase: "Phase 2: Core Topology Implementation"
active_agents: []
---

# Manager Agent Handover File - TDL (Topological Data Analysis Lab)

## Active Memory Context

**User Directives:**
- Dual portfolio TDA projects with full technical ambition (deep learning integration is core, not optional)
- Mathematical rigor required with validation checkpoints
- 6 critical checkpoints requiring user validation: Tasks 2.3, 2.6, 5.1, 5.2, 5.6, 7.2/7.4
- Heavy review required for academic papers and policy briefs (Phase 8)
- Human visual checks required for all visualization tasks (Phase 6)

**Decisions:**
- Python version constrained to 3.11 (not 3.13) due to giotto-tda wheel availability - this is intentional and must be maintained
- NumPy constrained to <2.0 for giotto-tda/scikit-learn compatibility
- POLAR4 education data skipped (174MB postcode-level); IMD Education domain used as practical alternative for mobility proxy
- Geospatial module renamed from `preprocessors.py` to `geospatial.py` due to existing `preprocessors/` directory conflict
- Exponential backoff retry pattern established across all API fetchers (Yahoo 60s, FRED 60s, CoinGecko 30s base delays)

## Coordination Status

**Producer-Consumer Dependencies (Phase 2):**
- Task 2.1 (Takens Embedding) → No dependencies, ready to assign to Agent_Financial_Topology
- Task 2.2 (Persistence Diagram - Financial) → Depends on Task 2.1 output
- Task 2.3 (Gidea & Katz Replication) → **CHECKPOINT** - Depends on Tasks 2.1, 2.2 - requires user mathematical validation
- Task 2.4 (Mobility Surface) → Depends on Phase 1 Poverty tasks (1.5-1.8) - **CROSS-AGENT** from Agent_Poverty_Data
- Task 2.5 (Morse-Smale TTK) → Depends on Task 2.4
- Task 2.6 (Critical Point Extraction) → **CHECKPOINT** - Depends on Task 2.5 - requires user validation

**Coordination Insights:**
- Agent_Financial_Data completed all 4 tasks efficiently with consistent exponential backoff patterns
- Agent_Poverty_Data completed all 4 tasks with practical adaptations for data availability constraints
- Both agents followed documentation standards (CONTRIBUTING.md) consistently
- Agents correctly used `important_findings: true` flag for significant adaptations

## Next Actions

**Ready Assignments:**
- Task 2.1 (Takens Embedding) → Agent_Financial_Topology - First task of Phase 2, no dependencies
- Task 2.4 (Mobility Surface) → Agent_Poverty_Topology - Can start in parallel, uses Phase 1 outputs

**Blocked Items:**
- None currently - clean phase boundary

**Phase Transition:**
- Phase 1 complete, summary written to Memory Root
- Phase 2 folder and empty Memory Logs need to be created before first assignment
- Phase 2 has 7 tasks across 2 agents (Agent_Financial_Topology, Agent_Poverty_Topology)

## Working Notes

**File Patterns:**
- Financial project: `financial_tda/` with `data/`, `topology/`, `models/`, `viz/`, `analysis/`
- Poverty project: `poverty_tda/` with `data/`, `topology/`, `models/`, `viz/`, `analysis/`
- Shared utilities: `shared/` with interface stubs (persistence.py, visualization.py, validation.py)
- Tests mirror project structure: `tests/financial/`, `tests/poverty/`, `tests/shared/`

**Coordination Strategies:**
- Same-agent dependencies: Simple contextual reference
- Cross-agent dependencies: Comprehensive integration context with explicit file reading steps
- Ad-hoc delegation: Reference `.github/prompts/apm-7-delegate-research.prompt.md` or `apm-8-delegate-debug.prompt.md`

**User Preferences:**
- Prefers concise task reports with clear status indicators
- Expects Memory Log review before proceeding to next task
- Appreciates phase-end summaries before proceeding
- Requested pause after Phase 1 completion for instructions

**Reference Documentation Locations:**
- TTK docs: `C:\Projects\ttk-1.3.0\ttk-1.3.0\doc`
- giotto-tda docs: `C:\Projects\giotto-tda`
- TopoModelX docs: `C:\Projects\TopoModelX\docs`

**Key Technical Notes:**
- giotto-tda import: `from gtda import homology` (not giotto_tda)
- VTK export for TTK: Use pyvista (added in Task 1.8)
- Kriging optional: Falls back to IDW when pykrige not installed
- IMD 2019 uses 2011 LSOA codes; may need mapping for 2021 boundaries in some cases
