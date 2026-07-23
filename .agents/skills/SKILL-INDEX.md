# TDL Skill Index — Invocation Routing

> Authoring-tree documentation. This file lives only in the `.agents` authoring
> tree (it is not a skill directory, so the sync tool neither mirrors nor lints
> it). Claude Code discovers skills by their frontmatter descriptions; Codex
> and human readers route by this table.

## Tiers

- **Tier 1 — core research discipline** (always in play):
  `research-assurance-triage` and the lane audits
  (`statistical-design-audit`, `null-operation-invariance-audit`,
  `panel-estimand-audit`, `representation-freeze-audit`,
  `result-provenance-review`, `topology-benchmark-review`,
  `sensitivity-comparison-review`, `reproducibility-package-review`,
  `paper-claim-trace`, `schema-contract-design`, `pre-reg-to-dispatch`),
  plus the TDL-adapted core ten:
  `tda-diagnosing-computational-defects`, `contract-first-tdd`,
  `tda-resource-preflight`, `tda-domain-modeling`, `tda-codebase-design`,
  `tda-statistical-analysis-review`, `tda-peer-review-panel`,
  `tda-literature-verification`, `tda-task-brief-from-plan`, `tda-handoff`.
- **Tier 2 — specialist support** (carry the TDL integration rule; route
  lane-touching output through research-assurance triage).
- **Tier 3 — optional workflow layer** (carry the Tier 3 constraint; may not
  create claims, result artifacts, or contract-bearing implementations
  directly), including `tda-large-workflow-supervision` for standalone
  multi-stage campaigns.

## Routing Table

| Task smells like | Skill |
|---|---|
| Statistical model, baseline fit, robustness, power, survival | `tda-statistical-modeling-toolkit` |
| Trajectory classifier, time-series clustering, anomaly comparator | `tda-trajectory-baselines` |
| Embedding, scaler/PCA, UMAP, SHAP, representation drift | `tda-representation-diagnostics` |
| Mapper graph, transition graph, household network, GNN | `tda-graph-network-analysis` |
| Slow job, GPU/cloud proposal, vectorisation, backend swap | `tda-acceleration-benchmarking` |
| FRED, World Bank, Eurostat, ONS, finance/macro context | `tda-external-data-lookup` |
| Paper figure, diagnostic plot, Mermaid pipeline diagram | `tda-visualisation-and-diagramming` |
| PDF/DOCX/XLSX/codebook ingestion | `tda-document-ingestion` |
| Disposable prototype, UX/CLI sketch | `tda-prototype-sandbox` |
| Speculative hypothesis, future-paper branching | `tda-research-ideation-lab` |
| Multi-branch decision needing risk analysis | `tda-scenario-stress-test` |
| Creating/reviewing/refactoring a skill | `tda-skill-authoring-workbench` |
| Large standalone campaign, context rotation, exact-state packet | `tda-large-workflow-supervision` |
| Git safety, hook coverage, agent write boundaries | `tda-agent-safety-guardrails` |
| Study material, exercises, Lean/Manim drills | `tda-learning-scaffold` |
| Web page, talk, poster from a stable result | `tda-paper-dissemination-pack` |
| Low-risk chore sorting (no lane contact) | `tda-light-task-triage` |

## Tier-1 Dispatch Cross-Links

`tda-task-brief-from-plan` → may dispatch any tier-2 skill ·
`tda-resource-preflight` → `tda-acceleration-benchmarking` ·
`tda-statistical-analysis-review` → `tda-statistical-modeling-toolkit` ·
`tda-domain-modeling` → `tda-representation-diagnostics` ·
`tda-peer-review-panel` → `tda-visualisation-and-diagramming` ·
`tda-literature-verification` → `tda-document-ingestion`

## Hard Rules That Cut Across All Tiers

- Lane-touching work (Topology, Stochastic/Null, Statistical/Panel,
  Representation, Output/Provenance, Paper Claim) passes through
  `research-assurance-triage`; software tests alone are never sufficient.
- Contracts are authored upstream of the implementer, always.
- `results/` holds real, provenance-tracked compute only.
- Skills are authored in this tree, registered in `SYNC_SKILLS`
  (`tools/sync_agent_skills.py`), and mirrored by the sync tool — never
  edit the mirror tree directly (`tda-skill-authoring-workbench`).
