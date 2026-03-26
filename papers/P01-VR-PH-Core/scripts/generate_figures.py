"""
Master figure generation pipeline for P01-VR-PH-Core.

Orchestrates:
  1. paper_figures.py  — Figs 1–11 from integration checkpoint
  2. phase6_figures.py — Figs 12–14 from Phase 6 checkpoint
  3. Copies all figures to papers/P01-VR-PH-Core/figures/ (PDF + PNG)
  4. Writes figures/manifest.json mapping fig-number → filename

Usage (from repo root):
    uv run python papers/P01-VR-PH-Core/scripts/generate_figures.py

Re-run at any time to refresh figures after data changes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for scripts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent.parent  # c:/Projects/TDL
INTEGRATION_DIR = REPO_ROOT / "results" / "trajectory_tda_integration"
PHASE6_DIR = REPO_ROOT / "results" / "trajectory_tda_phase6"
OUTPUT_DIR = Path(__file__).parent.parent / "figures"


def _ensure_phase6(phase6_dir: Path) -> bool:
    """Check whether Phase 6 results exist; print guidance if not."""
    required = [
        "03_regime_transitions.json",
        "05_phase_ph_diagrams.json",
        "06_phase_nulls.json",
    ]
    missing = [f for f in required if not (phase6_dir / f).exists()]
    if missing:
        logger.warning(
            "Phase 6 results missing: %s\n"
            "Run first:  uv run python -m trajectory_tda.scripts.run_phase6 "
            "--checkpoint-dir results/trajectory_tda_integration "
            "--phase6-dir results/trajectory_tda_phase6",
            missing,
        )
        return False
    return True


def generate_paper_figures(integration_dir: Path, output_dir: Path) -> list[dict]:
    """Generate Figs 1–11 via paper_figures.generate_all_figures."""
    from trajectory_tda.viz.paper_figures import generate_all_figures

    logger.info("=== Figs 1–11: paper_figures ===")
    generate_all_figures(integration_dir, output_dir)

    # Enumerate what was produced
    mapping = [
        {
            "fig": 1,
            "stem": "fig1_trajectory_heatmap",
            "caption": "Exemplar trajectories from each of the seven mobility regimes. "
            "Each row represents one individual; colours encode employment-income state.",
        },
        {
            "fig": 2,
            "stem": "fig2_embedding_cloud",
            "caption": "Trajectory embedding space (bigram PCA-20D reduced to UMAP-2D). "
            "Points are individual career trajectories, coloured by GMM regime.",
        },
        {
            "fig": 3,
            "stem": "fig3_persistence_diagrams",
            "caption": "Persistence diagrams for $H_0$ (connected components, left) and $H_1$ "
            "(loops, right). Points far from the diagonal represent long-lived topological features.",
        },
        {
            "fig": 4,
            "stem": "fig4_betti_null_comparison",
            "caption": "Observed total persistence versus order-shuffle null (left: $H_0$; right: $H_1$). "
            "Red line = observed; histogram = null distribution.",
        },
        {
            "fig": 5,
            "stem": "fig5_regime_profiles",
            "caption": "Regime profile heatmap. Rows are the seven mobility regimes; "
            "columns are labour-market metrics. Values are rates (0--1).",
        },
        {
            "fig": 6,
            "stem": "fig6_stability_income",
            "caption": "Stability versus high-income rate for each regime. "
            "Bubble size is proportional to regime membership.",
        },
        {
            "fig": 7,
            "stem": "fig7_cycle_analysis",
            "caption": "Cycle (\\textit{H}\\textsubscript{1}) analysis. Left: $H_1$ persistence diagram "
            "with top 20 features highlighted. Right: cycle-length distribution.",
        },
        {
            "fig": 8,
            "stem": "fig8_null_table",
            "caption": "Null model validation summary across the Markov memory ladder. "
            "Significant results (\\textit{p} < 0.05) are shaded green.",
        },
        {
            "fig": 9,
            "stem": "fig9_markov_memory_depth",
            "caption": "Total persistence distributions for order-shuffle, Markov order-1, "
            "and Markov order-2 null models. Red line = observed value.",
        },
        {
            "fig": 10,
            "stem": "fig10_wasserstein_heatmap",
            "caption": "Pairwise Wasserstein distances between persistence diagrams by parental NS-SEC. "
            "Stars mark statistically significant differences.",
        },
        {
            "fig": 11,
            "stem": "fig11_landscape_comparison",
            "caption": "Persistence landscape comparison (\\textit{L}\\textsubscript{1}) for male versus "
            "female trajectories. Shaded region shows the difference.",
        },
    ]
    return mapping


def generate_phase6_figures(phase6_dir: Path, output_dir: Path) -> list[dict]:
    """Generate Figs 12–14 via phase6_figures and copy to output_dir."""
    import json

    import numpy as np

    from trajectory_tda.viz.phase6_figures import (
        plot_escape_probabilities,
        plot_phase_ph_with_nulls,
        plot_transition_heatmap,
    )

    logger.info("=== Figs 12–14: phase6_figures ===")
    output_dir.mkdir(parents=True, exist_ok=True)

    mapping = []

    # Fig 12: Transition heatmap
    trans_path = phase6_dir / "03_regime_transitions.json"
    if trans_path.exists():
        with open(trans_path) as f:
            trans_data = json.load(f)
        tm = np.array(trans_data["transition_matrix"])
        out_path = output_dir / "fig12_transition_heatmap.pdf"
        plot_transition_heatmap(tm, out_path)
        # Also save PNG (re-render at 300 dpi)
        import matplotlib.pyplot as plt

        from trajectory_tda.viz.constants import DPI, REGIME_LABELS

        n = tm.shape[0]
        labels = [REGIME_LABELS.get(i, f"R{i}") for i in range(n)]
        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(tm, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel("To regime")
        ax.set_ylabel("From regime")
        ax.set_title("Regime Transition Probabilities")
        for i in range(n):
            for j in range(n):
                val = tm[i, j]
                color = "white" if val > 0.5 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=6, color=color)
        fig.colorbar(im, ax=ax, shrink=0.8, label="P(transition)")
        fig.tight_layout()
        fig.savefig(output_dir / "fig12_transition_heatmap.png", dpi=DPI)
        plt.close(fig)
        logger.info("Saved fig12_transition_heatmap.pdf + .png")
        mapping.append(
            {
                "fig": 12,
                "stem": "fig12_transition_heatmap",
                "caption": "Regime transition probability matrix. Cell $(i, j)$ shows $P(\\text{regime}_{t+1} = j "
                "\\mid \\text{regime}_t = i)$ estimated from overlapping career-phase windows.",
            }
        )

        # Fig 13: Escape probabilities
        esc = trans_data.get("escape_probabilities", {})
        if esc:
            out_path = output_dir / "fig13_escape_probabilities.pdf"
            plot_escape_probabilities(esc, out_path)
            # Re-render PNG
            import matplotlib.pyplot as plt

            horizons = esc.get("escape_by_horizon", {})
            x = sorted(int(k) for k in horizons.keys())
            y_vals = [horizons.get(str(h), horizons.get(h, 0)) for h in x]
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.bar(x, y_vals, color="#42a5f5", edgecolor="black", linewidth=0.5)
            ax.set_xlabel("Horizon (windows)")
            ax.set_ylabel("Cumulative escape fraction")
            ax.set_title("Escape Probability from Disadvantaged Regimes")
            n_start = esc.get("n_starting_disadvantaged", "?")
            ever_rate = esc.get("ever_escape_rate", 0)
            ax.text(
                0.95,
                0.95,
                f"N={n_start}, ever={ever_rate:.1%}",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=8,
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "wheat", "alpha": 0.8},
            )
            fig.tight_layout()
            fig.savefig(output_dir / "fig13_escape_probabilities.png", dpi=300)
            plt.close(fig)
            logger.info("Saved fig13_escape_probabilities.pdf + .png")
            mapping.append(
                {
                    "fig": 13,
                    "stem": "fig13_escape_probabilities",
                    "caption": "Cumulative escape probability from disadvantaged regimes "
                    "(Regimes 2 \\& 6) by horizon window. "
                    "Among $N = 7{,}453$ individuals starting in a disadvantaged regime, "
                    "5.6\\% ever reach an advantaged regime.",
                }
            )

    # Fig 14: Phase PH + nulls
    dgm_path = phase6_dir / "05_phase_ph_diagrams.json"
    null_path = phase6_dir / "06_phase_nulls.json"
    if dgm_path.exists() and null_path.exists():
        with open(dgm_path) as f:
            diagrams = json.load(f)
        with open(null_path) as f:
            null_data = json.load(f)
        out_path = output_dir / "fig14_phase_ph_nulls.pdf"
        plot_phase_ph_with_nulls(
            diagrams,
            null_data["null_distributions"],
            null_data["observed"],
            null_data["p_values"],
            out_path,
        )
        # Re-render PNG at 300 dpi from the same data
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        colors = {0: "#1a237e", 1: "#b71c1c"}
        ax = axes[0]
        for dim_str, dgm in diagrams.items():
            dim = int(dim_str)
            arr = np.array(dgm)
            if len(arr) == 0:
                continue
            ax.scatter(
                arr[:, 0],
                arr[:, 1],
                s=8,
                alpha=0.5,
                color=colors.get(dim, "gray"),
                label=f"H{dim} ({len(arr)} features)",
            )
        lims = ax.get_xlim()
        ax.plot(lims, lims, "k--", linewidth=0.5, alpha=0.3)
        ax.set_xlabel("Birth")
        ax.set_ylabel("Death")
        ax.set_title("Phase PH Diagram")
        ax.legend(fontsize=7)
        ax = axes[1]
        nd = null_data["null_distributions"]
        dim_keys = sorted(nd.keys())
        ax.violinplot([nd[k] for k in dim_keys], positions=list(range(len(dim_keys))), showmeans=True, showmedians=True)
        for i, k in enumerate(dim_keys):
            obs_val = null_data["observed"].get(k, 0)
            ax.scatter([i], [obs_val], color="red", zorder=5, s=60, marker="D", label="Observed" if i == 0 else None)
            pval = null_data["p_values"].get(k, 1.0)
            ax.annotate(f"p={pval:.3f}", (i, obs_val), textcoords="offset points", xytext=(10, 5), fontsize=7)
        ax.set_xticks(list(range(len(dim_keys))))
        ax.set_xticklabels(dim_keys)
        ax.set_ylabel("Total persistence")
        ax.set_title("Phase-Order Shuffle Null Test")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(output_dir / "fig14_phase_ph_nulls.png", dpi=300)
        plt.close(fig)
        logger.info("Saved fig14_phase_ph_nulls.pdf + .png")
        mapping.append(
            {
                "fig": 14,
                "stem": "fig14_phase_ph_nulls",
                "caption": "Phase-level persistent homology. Left: persistence diagram for "
                "career-phase embeddings. Right: phase-order shuffle null test "
                "($n = 100$ permutations). The observed total persistence is "
                "not an outlier relative to the null ($H_0$: $p = 0.73$, "
                "$H_1$: $p = 0.28$).",
            }
        )

    return mapping


def write_manifest(mapping: list[dict], output_dir: Path) -> None:
    """Write figures/manifest.json for use by integrate_figures.py."""
    manifest = {str(m["fig"]): {"stem": m["stem"], "caption": m["caption"]} for m in mapping}
    dest = output_dir / "manifest.json"
    with open(dest, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Wrote manifest: %s", dest)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mapping = []

    # Figs 1–11
    mapping.extend(generate_paper_figures(INTEGRATION_DIR, OUTPUT_DIR))

    # Figs 12–14
    if _ensure_phase6(PHASE6_DIR):
        mapping.extend(generate_phase6_figures(PHASE6_DIR, OUTPUT_DIR))
    else:
        logger.warning("Skipping Figs 12–14 (Phase 6 data missing)")

    # Manifest
    write_manifest(mapping, OUTPUT_DIR)

    # Summary
    logger.info("=== Figure generation complete ===")
    for m in sorted(mapping, key=lambda x: x["fig"]):
        pdf = OUTPUT_DIR / f"{m['stem']}.pdf"
        status = "✓" if pdf.exists() else "✗"
        logger.info("  Fig %2d %s %s", m["fig"], status, m["stem"])


if __name__ == "__main__":
    main()
