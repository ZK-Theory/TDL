# Agent Orchestration Plan

Reference: `trajectory_tda/plan-fourthDraftMajorRevision.md` (core plan — do not modify)

## Architecture

Five agents, two waves. No worktrees needed — all code agents touch unique files.

```
WAVE 1 (all start simultaneously)
├── Agent 1: BHPS Data Pipeline     → employment_status.py, income_band.py, trajectory_builder.py
├── Agent 2: Null Model Compute     → runs rerun_nulls.py (no code edits, pure compute)
├── Agent 3: New Analyses           → intra_regime_compactness.py, nssec_missingness.py,
│                                      bootstrap_null_stability.py, age_stratified.py
├── Agent 4: Robustness Code        → ngram_embed.py, permutation_nulls.py,
│                                      run_embedding_sensitivity.py, run_nonoverlapping_windows.py
└── Agent 5: Paper (Pass 1)         → fourth_draft.md (copied from third_draft.md; reframing-only sections, no data deps)

WAVE 2 (after ALL Wave 1 agents complete)
└── Agent 5: Paper (Pass 2)         → fourth_draft.md (result-dependent sections)
```

## File Ownership Rules

Each agent has EXCLUSIVE write access to specific files. Violations will cause merge conflicts.

| Agent | EXCLUSIVE WRITE files | READ-ONLY files |
|-------|----------------------|-----------------|
| Agent 1 | `trajectory_tda/data/employment_status.py`, `trajectory_tda/data/income_band.py`, `trajectory_tda/data/trajectory_builder.py` | `xwavedat.tab`, BHPS/USoc raw data |
| Agent 2 | `results/trajectory_tda_integration/04_nulls.json`, `results/trajectory_tda_integration/04_nulls_markov2.json`, new L=5000 result files | `trajectory_tda/scripts/rerun_nulls.py` (run, don't edit) |
| Agent 3 | `trajectory_tda/analysis/intra_regime_compactness.py` (NEW), `trajectory_tda/analysis/nssec_missingness.py` (NEW), `trajectory_tda/analysis/bootstrap_null_stability.py` (NEW), `trajectory_tda/analysis/age_stratified.py` | `trajectory_tda/analysis/regime_discovery.py`, `trajectory_tda/analysis/gmm_bootstrap.py` (read for context) |
| Agent 4 | `trajectory_tda/embedding/ngram_embed.py`, `trajectory_tda/topology/permutation_nulls.py`, `trajectory_tda/scripts/run_embedding_sensitivity.py` (NEW), `trajectory_tda/scripts/run_nonoverlapping_windows.py` (NEW) | `trajectory_tda/data/trajectory_builder.py` (import only — Agent 1 owns edits) |
| Agent 5 | `trajectory_tda/paper/fourth_draft.md` (copied from `third_draft.md` at start) | `trajectory_tda/paper/third_draft.md` (read-only source), all results files, all analysis outputs |

## Dependency Graph

```
Agent 1 ─────────────────────────┐
Agent 2 ─────────────────────────┤
Agent 3 ─────────────────────────┼──→ Agent 5 Pass 2
Agent 4 ─────────────────────────┘
Agent 5 Pass 1 (independent) ────────→ Agent 5 Pass 2 (continues)
```

## Handoff Protocol

When each Wave 1 agent completes, it must produce a **handoff summary** containing:
1. List of files created/modified
2. Key numerical results (if any) that Agent 5 needs for paper sections
3. Any unexpected findings that affect paper framing
4. Test/verification status

Agent 5 Pass 2 consumes all handoff summaries to write result-dependent paper sections.

## Risk: Agent 4 imports from trajectory_builder.py

Agent 4's `run_nonoverlapping_windows.py` imports `build_windows()` from `trajectory_builder.py`, which Agent 1 is editing. Agent 1's edit adds a `survey_era` metadata column — an additive change that doesn't alter the `build_windows()` API signature or return type. No conflict expected, but if Agent 4 starts its script before Agent 1 commits, Agent 4 should import-test the script after Agent 1 completes.

## Resource Contention

Agents 1 and 2 both run compute-heavy pipelines. If running on the same machine:
- Agent 2 (null model re-runs) is the heavier workload (500 permutations × 3 null models at L=5000)
- Agent 1 (BHPS pipeline) is lighter but depends on data loading
- Consider staggering: start Agent 2 first (longest runtime), Agent 1 second
- Agents 3 and 4 are primarily code-writing with lighter compute
