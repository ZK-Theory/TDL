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

`torch-geometric` is an **optional dependency** — do not import it at module load. Guard it behind an availability check so a missing install fails with a clear, actionable message instead of an opaque `ImportError`:

```python
import importlib.util


def require_torch_geometric() -> None:
    """Raise a clear error if torch-geometric is not installed."""
    if importlib.util.find_spec("torch_geometric") is None:
        raise ImportError(
            "torch-geometric is required for GNN models; install with: "
            "uv pip install torch-geometric"
        )
```

Centralise this helper in `shared/deep_learning/` and call `require_torch_geometric()` at the top of any function or model `__init__` that needs it (importing `torch_geometric` only after the check passes), rather than importing it directly at module scope.
