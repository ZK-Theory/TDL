---
paths:
  - "**/models/**"
  - "shared/deep_learning/**"
---

# Deep Learning Integration

## Current integration points

- GNNs: `torch-geometric`; spatial graphs in `poverty_tda/models/spatial_gnn.py`, persistence graphs in `financial_tda/models/rips_gnn.py`
- VAEs: `poverty_tda/models/opportunity_vae.py`
- Persistence-based DL: Perslay/PersFormer patterns for learning on persistence diagrams (partially implemented)
- TTK/ParaView: acceleration for large-scale topology; see `shared/ttk_utils.py`

## Geometric / topological deep learning (emerging structure)

- Domain-agnostic DL layers → `shared/deep_learning/` (persistence-based layers, simplicial convolutions)
- Domain-specific DL models → `<domain>/models/` (as now)
- Experiment scaffolds → `<domain>/experiments/` or `<domain>/scripts/`

Key frameworks to integrate: `torch-geometric`, `TopoModelX` (simplicial/cellular/hypergraph NNs), `Perslay`.

Do not import `torch-geometric` without checking it is installed — optional dependency.
