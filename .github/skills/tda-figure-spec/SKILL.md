---
name: tda-figure-spec
version: 1.0.0
description: |
  Generate publication-quality TDA figures following the codebase style
  conventions (Journal of Economic Geography / JRSS standards). Produces
  correctly sized matplotlib code for persistence diagrams, barcodes,
  Mapper graphs, persistence landscapes, null comparison histograms, and
  trajectory heatmaps. Uses the established PUBLICATION_RC, DPI, FIGSIZE_*,
  STATE_COLORS, and _save_figure conventions from trajectory_tda/viz/.
  Use during the production pass when creating or regenerating paper figures.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - AskUserQuestion
---

# TDA Figure Spec: Generate Publication-Ready TDA Figures

You are generating paper figures for a TDA research paper. All figures must follow
the conventions established in `trajectory_tda/viz/constants.py` and the existing
`paper_figures.py` module.

## Step 1 — Read the style constants

Before generating any code, read:
- `trajectory_tda/viz/constants.py` — PUBLICATION_RC, DPI, FIGSIZE_*, STATE_COLORS, STATES
- `trajectory_tda/viz/paper_figures.py` — the `_save_figure` helper and existing figure functions

This ensures the new figure code is consistent with existing figures.

## Step 2 — Identify the figure

Ask the user:
1. **Figure type:** persistence diagram, barcode, landscape comparison, Mapper graph,
   null histogram, trajectory heatmap, Wasserstein heatmap, embedding scatter, or other
2. **Paper and figure number:** e.g., P01-A Fig 3 or P01-B Fig 2
3. **Data source:** which results file or numpy array contains the data?
4. **Stratification:** single panel, or by regime/era/cohort?
5. **Output path:** `papers/PXX/figures/` (for paper) or `figures/trajectory_tda/` (working)
6. **Format needed:** PDF+PNG (publication) or PNG only (working)

---

## Step 3 — Apply the standard conventions

### Always apply these

```python
from trajectory_tda.viz.constants import (
    DPI, FIGSIZE_FULL, FIGSIZE_WIDE, FIGSIZE_HALF, FIGSIZE_SQUARE,
    PUBLICATION_RC, STATE_COLORS, STATES, STATE_LABELS, REGIME_LABELS,
)
import matplotlib.pyplot as plt

plt.rcParams.update(PUBLICATION_RC)
```

### Figure size selection

| When to use | Constant | Dimensions |
|---|---|---|
| Single full-width plot | `FIGSIZE_FULL` | 190mm × 120mm (~7.48" × 4.72") |
| Wide 2-panel | `FIGSIZE_WIDE` | 190mm × 104mm (~7.48" × 4.11") |
| Half-width single panel | `FIGSIZE_HALF` | 90mm × 120mm (~3.54" × 4.72") |
| Square (e.g. heatmap) | `FIGSIZE_SQUARE` | 90mm × 90mm (~3.54" × 3.54") |

Do not invent custom sizes. Choose the closest standard size.

### Save function

Always use:
```python
def _save_figure(fig, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{name}.pdf", format="pdf")
    fig.savefig(output_dir / f"{name}.png", format="png", dpi=DPI)
```

For working figures only (no PDF needed):
```python
fig.savefig(output_dir / f"{name}.png", format="png", dpi=DPI, bbox_inches="tight")
```

### Colormaps

- State space: use `STATE_COLORS` dict (never `tab10`, `Set1`, or default cycle)
- Regimes: use `plt.cm.tab10` with explicit regime order from `REGIME_LABELS`
- Diverging / sequential: perceptually uniform only — `viridis`, `plasma`, `RdBu_r`; **never `jet`**
- Two-group comparison: `#2d6a2e` (green, observed) vs `#1a237e` (blue, null)

### Typography

All text sizes are controlled by `PUBLICATION_RC` — do not override with manual `fontsize=`.
Exception: annotation text (arrowhead labels, inset annotations) may use `fontsize=8`.

---

## Step 4 — Figure-type templates

### Persistence diagram

```python
def plot_persistence_diagram(
    diagram: np.ndarray,  # shape (n_features, 2): columns [birth, death]
    dim: int,
    ax: plt.Axes,
    threshold: float | None = None,
    title: str | None = None,
) -> None:
    """Plot a persistence diagram on the given axes.

    Args:
        diagram: Birth-death pairs (n_features, 2). Infinite deaths clipped to plot range.
        dim: Homology dimension (0 or 1).
        ax: Matplotlib axes to draw on.
        threshold: If set, draw dashed horizontal/vertical lines at this scale.
        title: Axes title (None for no title).
    """
    finite = diagram[np.isfinite(diagram[:, 1])]
    inf_mask = ~np.isfinite(diagram[:, 1])

    # Determine axis range
    if len(finite) > 0:
        max_val = max(finite.max(), 0.01)
    else:
        max_val = 1.0

    # Diagonal
    ax.plot([0, max_val * 1.05], [0, max_val * 1.05], "k-", linewidth=0.5, alpha=0.5)

    # Finite features
    color = "#2d6a2e" if dim == 0 else "#1a237e"
    ax.scatter(finite[:, 0], finite[:, 1], s=8, c=color, alpha=0.7, linewidths=0)

    # Infinite features (H_0 only — the essential component)
    if inf_mask.any():
        inf_births = diagram[inf_mask, 0]
        ax.scatter(inf_births, [max_val * 1.02] * len(inf_births),
                   s=16, c=color, marker="^", alpha=0.9)

    # Persistence threshold line
    if threshold is not None:
        ax.axhline(threshold, color="gray", linewidth=0.8, linestyle=":")
        ax.annotate(f"ε={threshold:.2f}", xy=(0.02, threshold),
                    xycoords=("axes fraction", "data"), fontsize=8, color="gray")

    ax.set_xlabel("Birth")
    ax.set_ylabel("Death")
    if title:
        ax.set_title(title)
    ax.set_aspect("equal")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
```

### Barcode (persistence barcode)

```python
def plot_barcode(
    diagram: np.ndarray,
    dim: int,
    ax: plt.Axes,
    max_death: float | None = None,
    title: str | None = None,
) -> None:
    """Plot a persistence barcode on the given axes.

    Bars sorted by birth, longest bars at top.
    Infinite bars extend to max_death * 1.05.
    """
    finite = diagram[np.isfinite(diagram[:, 1])]
    sort_idx = np.argsort(finite[:, 1] - finite[:, 0])[::-1]
    finite = finite[sort_idx]

    if max_death is None:
        max_death = finite[:, 1].max() if len(finite) > 0 else 1.0

    color = "#2d6a2e" if dim == 0 else "#1a237e"
    for i, (b, d) in enumerate(finite):
        ax.plot([b, d], [i, i], c=color, linewidth=1.2, solid_capstyle="butt")

    ax.set_xlabel("Filtration scale ε")
    ax.set_yticks([])
    ax.set_ylabel("Features (sorted by persistence)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    if title:
        ax.set_title(title)
```

### Null comparison histogram

```python
def plot_null_histogram(
    observed: float,
    null_distribution: np.ndarray,
    p_value: float,
    dim: int,
    ax: plt.Axes,
    statistic_label: str = "Total persistence",
    null_label: str = "Markov-1 null",
) -> None:
    """Plot observed statistic against null distribution.

    Args:
        observed: Observed statistic value.
        null_distribution: (n_perms,) null distribution.
        p_value: One-sided p-value (proportion of nulls >= observed).
        dim: Homology dimension (for colour).
        ax: Axes to draw on.
        statistic_label: x-axis label.
        null_label: Label for null histogram.
    """
    color = "#2d6a2e" if dim == 0 else "#1a237e"
    ax.hist(null_distribution, bins=30, color="steelblue", alpha=0.6,
            edgecolor="none", label=null_label)
    ax.axvline(observed, color=color, linewidth=1.8, linestyle="-",
               label=f"Observed (p={p_value:.3f})")
    null_mean = null_distribution.mean()
    ax.axvline(null_mean, color="steelblue", linewidth=1.0, linestyle="--", alpha=0.7)

    ax.set_xlabel(statistic_label)
    ax.set_ylabel("Frequency")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
```

### Persistence landscape comparison

```python
def plot_landscape_comparison(
    landscapes_obs: np.ndarray,   # (n_layers, grid_size)
    landscapes_null: np.ndarray,  # (n_layers, grid_size) — mean null
    grid: np.ndarray,             # (grid_size,) filtration values
    ax: plt.Axes,
    n_layers: int = 3,
    title: str | None = None,
) -> None:
    """Plot observed vs mean-null persistence landscapes (first n_layers).

    The L² distance between observed and mean-null landscapes is a mandatory
    complementary metric to W₂ — plot this alongside Wasserstein comparisons.
    """
    for k in range(min(n_layers, landscapes_obs.shape[0])):
        alpha = 1.0 - k * 0.25
        ax.plot(grid, landscapes_obs[k], color="#2d6a2e", alpha=alpha,
                linewidth=1.2 - k * 0.2, label=f"Observed λ_{k+1}" if k == 0 else None)
        ax.plot(grid, landscapes_null[k], color="steelblue", alpha=alpha,
                linewidth=1.2 - k * 0.2, linestyle="--",
                label="Mean null" if k == 0 else None)

    ax.set_xlabel("Filtration scale ε")
    ax.set_ylabel("Landscape value")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if title:
        ax.set_title(title)
```

---

## Step 5 — Figure annotation standards

- **p-value annotation:** always show as `p=0.003`, not `p<0.01` or `p=3e-3`
- **Sample size:** include in subtitle or caption, not on the axes
- **Persistence threshold:** annotate with `ε=` if visible on plot
- **Axis spines:** remove top and right; keep bottom and left
- **Legend:** `frameon=False`; place outside plot only if ≥5 items
- **Subplot labels:** `(a)`, `(b)` etc. as `ax.text(0.02, 0.97, "(a)", transform=ax.transAxes, ...)`

---

## Step 6 — Output path and naming

| Context | Path | Naming convention |
|---|---|---|
| Paper figure (numbered) | `papers/PXX/figures/` | `fig{N}_{descriptor}.{pdf|png}` |
| Supplement figure | `papers/PXX/figures/` | `figS{N}_{descriptor}.{pdf|png}` |
| Working/exploratory | `figures/{domain}/` | `{YYYYMMDD}_{descriptor}.png` |

Never save working figures into `papers/PXX/figures/` — that directory is for
production-pass figures only.
