"""Wasserstein distance matrix between annual persistence diagrams.

Paper 3 analysis: Computes pairwise Wasserstein distances between the
32 annual VR persistence diagrams (1991–2022). Produces a 32×32 symmetric
distance matrix for both H₀ and H₁, suitable for MDS embedding and
correlation with macroeconomic indicators.

Uses gudhi.wasserstein.wasserstein_distance (exact, L₂ ground metric).

Run::

    python -m trajectory_tda.analysis.annual_wasserstein \
        --diagrams-path results/trajectory_tda_zigzag/02_annual_diagrams.json \
        --output-dir results/trajectory_tda_zigzag
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _load_annual_diagrams(
    diagrams_path: Path,
) -> tuple[list[int], dict[int, NDArray[np.float64]], dict[int, NDArray[np.float64]]]:
    """Load annual persistence diagrams from JSON checkpoint.

    Args:
        diagrams_path: Path to ``02_annual_diagrams.json``.

    Returns:
        Tuple of (years, h0_diagrams, h1_diagrams) where each dict maps
        year → (n_bars, 2) array with columns [birth, death].
    """
    with open(diagrams_path) as f:
        data = json.load(f)

    diagrams = data["diagrams"]
    years = sorted(int(y) for y in diagrams.keys())

    h0_by_year: dict[int, NDArray[np.float64]] = {}
    h1_by_year: dict[int, NDArray[np.float64]] = {}

    for year in years:
        d = diagrams[str(year)]
        h0_raw = np.array(d["diagram_h0"], dtype=np.float64)
        h1_raw = np.array(d["diagram_h1"], dtype=np.float64)

        # Keep only finite bars for Wasserstein computation
        if len(h0_raw) > 0:
            finite_mask = np.isfinite(h0_raw[:, 1])
            h0_by_year[year] = h0_raw[finite_mask]
        else:
            h0_by_year[year] = np.zeros((0, 2), dtype=np.float64)

        if len(h1_raw) > 0:
            finite_mask = np.isfinite(h1_raw[:, 1])
            h1_by_year[year] = h1_raw[finite_mask]
        else:
            h1_by_year[year] = np.zeros((0, 2), dtype=np.float64)

    return years, h0_by_year, h1_by_year


def compute_wasserstein_matrix(
    diagrams_by_year: dict[int, NDArray[np.float64]],
    years: list[int],
    order: float = 2.0,
) -> NDArray[np.float64]:
    """Compute pairwise Wasserstein distance matrix between annual diagrams.

    Args:
        diagrams_by_year: Dict mapping year → (n_bars, 2) persistence diagram.
        years: Ordered list of years.
        order: Wasserstein exponent (default 2.0 for W₂).

    Returns:
        Symmetric distance matrix of shape (n_years, n_years).
    """
    from gudhi.wasserstein import wasserstein_distance

    n = len(years)
    dist_matrix = np.zeros((n, n), dtype=np.float64)

    total_pairs = n * (n - 1) // 2
    computed = 0

    for i in range(n):
        for j in range(i + 1, n):
            d = wasserstein_distance(
                diagrams_by_year[years[i]],
                diagrams_by_year[years[j]],
                order=order,
            )
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d
            computed += 1
            if computed % 50 == 0:
                logger.info("  %d / %d pairs computed", computed, total_pairs)

    return dist_matrix


def main() -> None:
    """Compute and save Wasserstein distance matrices."""
    parser = argparse.ArgumentParser(
        description="Wasserstein distance matrix between annual PDs.",
    )
    parser.add_argument(
        "--diagrams-path",
        default="results/trajectory_tda_zigzag/02_annual_diagrams.json",
        help="Path to annual diagrams JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="results/trajectory_tda_zigzag",
        help="Output directory.",
    )
    parser.add_argument(
        "--order",
        type=float,
        default=2.0,
        help="Wasserstein exponent (default: 2.0 for W₂).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    diagrams_path = Path(args.diagrams_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading annual diagrams from %s", diagrams_path)
    years, h0_by_year, h1_by_year = _load_annual_diagrams(diagrams_path)
    logger.info("Loaded %d years (%d–%d)", len(years), years[0], years[-1])

    # H₀ Wasserstein matrix
    logger.info("Computing H₀ Wasserstein matrix (%d × %d)...", len(years), len(years))
    w_h0 = compute_wasserstein_matrix(h0_by_year, years, order=args.order)
    h0_path = output_dir / "annual_wasserstein_h0.npy"
    np.save(h0_path, w_h0)
    logger.info("Saved H₀ matrix: %s", h0_path)

    # H₁ Wasserstein matrix
    logger.info("Computing H₁ Wasserstein matrix (%d × %d)...", len(years), len(years))
    w_h1 = compute_wasserstein_matrix(h1_by_year, years, order=args.order)
    h1_path = output_dir / "annual_wasserstein_h1.npy"
    np.save(h1_path, w_h1)
    logger.info("Saved H₁ matrix: %s", h1_path)

    # Save years index for reference
    meta = {
        "years": years,
        "order": args.order,
        "n_years": len(years),
        "h0_mean_distance": float(w_h0[np.triu_indices_from(w_h0, k=1)].mean()),
        "h1_mean_distance": float(w_h1[np.triu_indices_from(w_h1, k=1)].mean()),
    }
    meta_path = output_dir / "annual_wasserstein_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved metadata: %s", meta_path)

    # Print summary
    logger.info(
        "H₀ W₂ mean=%.4f, std=%.4f",
        meta["h0_mean_distance"],
        float(w_h0[np.triu_indices_from(w_h0, k=1)].std()),
    )
    logger.info(
        "H₁ W₂ mean=%.4f, std=%.4f",
        meta["h1_mean_distance"],
        float(w_h1[np.triu_indices_from(w_h1, k=1)].std()),
    )


if __name__ == "__main__":
    main()
