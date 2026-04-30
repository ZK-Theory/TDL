# /tda-figure-spec — Generate Publication-Ready TDA Figures

Scaffold matplotlib figure code following the established `trajectory_tda/viz/` conventions.
Uses `PUBLICATION_RC`, `DPI`, `FIGSIZE_*`, `STATE_COLORS`, and `_save_figure` from the
codebase — never ad-hoc sizes or colours.

## Usage

```
/tda-figure-spec [figure-type] [paper-number]
```

Example: `/tda-figure-spec persistence-diagram P01-B`
Example: `/tda-figure-spec null-histogram P01-A`
Example: `/tda-figure-spec` (interactive)

---

## Style constants (always import from trajectory_tda/viz/constants.py)

```python
from trajectory_tda.viz.constants import (
    DPI, FIGSIZE_FULL, FIGSIZE_WIDE, FIGSIZE_HALF, FIGSIZE_SQUARE,
    PUBLICATION_RC, STATE_COLORS, STATES, STATE_LABELS, REGIME_LABELS,
)
import matplotlib.pyplot as plt
plt.rcParams.update(PUBLICATION_RC)
```

## Figure size guide

| Use case | Constant | Size |
|---|---|---|
| Single full-width plot | `FIGSIZE_FULL` | 190mm × 120mm |
| Wide two-panel | `FIGSIZE_WIDE` | 190mm × 104mm |
| Half-width single panel | `FIGSIZE_HALF` | 90mm × 120mm |
| Square heatmap | `FIGSIZE_SQUARE` | 90mm × 90mm |

## Save function (always use this pattern)

```python
def _save_figure(fig, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{name}.pdf", format="pdf")
    fig.savefig(output_dir / f"{name}.png", format="png", dpi=DPI)
```

---

## Colour rules

- **State space:** always `STATE_COLORS` dict — never `tab10` or default cycle
- **Observations:** `#2d6a2e` (green); **Null:** `steelblue`; **Dim 0:** green; **Dim 1:** `#1a237e`
- **Regimes:** `plt.cm.tab10` with `REGIME_LABELS` order
- **Sequential/diverging:** `viridis`, `plasma`, `RdBu_r` — **never `jet`**

## Annotation standards

- p-values: write `p=0.003`, not `p<0.01`
- Axes: remove top and right spines; keep bottom and left
- Legends: `frameon=False`
- Subplot labels: `ax.text(0.02, 0.97, "(a)", transform=ax.transAxes, ...)`

## Figure templates available

| Template | When to use |
|---|---|
| `plot_persistence_diagram(diagram, dim, ax)` | Scatter birth-death pairs |
| `plot_barcode(diagram, dim, ax)` | Feature lifetimes sorted by persistence |
| `plot_null_histogram(observed, null_dist, p_value, dim, ax)` | Permutation test result |
| `plot_landscape_comparison(obs, null, grid, ax)` | L² landscape distance (mandatory) |

---

## Output paths

| Context | Path | Naming |
|---|---|---|
| Production paper figure | `papers/PXX/figures/` | `fig{N}_{desc}.{pdf\|png}` |
| Supplement | `papers/PXX/figures/` | `figS{N}_{desc}.{pdf\|png}` |
| Working / exploratory | `figures/{domain}/` | `YYYYMMDD_{desc}.png` |

Working figures must not be saved to `papers/PXX/figures/` — that is for production only.
