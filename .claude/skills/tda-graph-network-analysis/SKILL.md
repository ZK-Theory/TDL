---
name: tda-graph-network-analysis
description: Use when constructing or analysing Mapper graphs, employment-state transition graphs, household or social networks, relational trajectory graphs, or future graph-learning (GNN) work in TDL.
---

# TDA Graph & Network Analysis

Graph summaries complement PH; they do not replace it. Use this for Mapper
graphs, transition graphs, household networks, and graph metrics that serve a
named scientific question. Do not use it when a graph summary is being treated
as equivalent to persistent homology — that equivalence claim needs the
topology lane.

## TDL Integration Rule

This skill is a specialist support skill. If the task touches Topology,
Stochastic/Null Model, Statistical/Panel, Representation, Output/Provenance,
or Paper Claim, run the project research-assurance triage path before treating
this skill's output as implementation-ready or claim-ready.

## Tooling Default

**NetworkX is the immediate default.** torch-geometric stays parked for the
later graph-learning papers (P08/P09) unless there is a concrete
graph-learning task — and it is an optional dependency: check it is installed
before importing. Do not pull GNN machinery into P01-era work.

## Procedure

1. Define the graph object and the scientific question it answers.
2. Define node semantics and edge semantics precisely (a Mapper node is a
   cluster of trajectories, not a person; a transition edge is a count or a
   probability — say which).
3. Specify: directed/undirected, weighted, bipartite, temporal, multiplex.
4. State construction thresholds (overlap, edge cutoffs, binning) — these are
   parameters and belong in the output record.
5. Compute only the metrics that match the question; a metric dump is not an
   analysis.
6. Check whether the construction depends on an exploratory embedding — if
   yes, `tda-representation-diagnostics` applies to that embedding first.
7. If visualized, record the layout algorithm and seed (layouts are
   stochastic; an unseeded layout is unreproducible).
8. State how the graph result relates to the PH/Mapper result or paper claim
   it accompanies.

## Required Output Record

```text
graph construction rule · node semantics · edge semantics ·
directed/undirected · edge weights · thresholds · component handling ·
layout seed · metrics computed · relationship to PH result · paper target
```

## Self-Test Prompts

- *A transition-graph modularity score is presented as confirming the PH
  regime structure.* → Expected: flag the equivalence claim; a graph metric
  can corroborate but not substitute for the topological result — route the
  claim through the topology lane.
- *A Mapper graph is built on a UMAP embedding chosen because it "looks
  cleanest".* → Expected: the embedding choice is a representation decision;
  run representation diagnostics and record the construction parameters.

## Escalate Or Stop When

- The graph construction thresholds materially change the conclusion — that
  is a sensitivity analysis (`sensitivity-comparison-review`), not a footnote.
- GNN work is proposed for a current paper — surface as a User scope decision.

## Related Skills

`tda-representation-diagnostics` (embedding dependencies) ·
`tda-visualisation-and-diagramming` (graph figures) ·
`tda-statistical-modeling-toolkit` (graph metrics entering models) ·
`validate-topology` (when a graph claim brushes against a topological one).
