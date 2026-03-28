"""Era-specific zigzag persistence.

Paper 3 robustness: runs zigzag separately on BHPS-only (1991–2008)
and USoc-only (2009–2022) to test whether the GFC cluster and other
topological features persist within survey eras (ruling out survey
transition artefacts).

Run::

    python -m trajectory_tda.scripts.run_zigzag_era_specific \
        --checkpoint-dir results/trajectory_tda_full \
        --output-dir results/trajectory_tda_zigzag/era_specific \
        --n-landmarks 150
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ERAS = {
    "bhps": (1991, 2008),
    "usoc": (2009, 2022),
}


def _convert(obj: object) -> object:
    """Recursively convert numpy types to JSON-serialisable equivalents."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    return obj


def run_era_zigzag(
    checkpoint_dir: Path,
    output_dir: Path,
    n_landmarks: int,
    max_filtration: float,
    max_dim: int,
    wsl_python: str,
    sparse: float,
) -> dict:
    """Run zigzag on BHPS-only and USoc-only sub-panels.

    Args:
        checkpoint_dir: Path with ``01_trajectories.json``, ``embeddings.npy``.
        output_dir: Output directory.
        n_landmarks: Landmarks per year for zigzag.
        max_filtration: VR threshold.
        max_dim: Max homology dimension.
        wsl_python: WSL Python path for dionysus bridge.
        sparse: Sparse Rips parameter.

    Returns:
        Dict with per-era zigzag results.
    """
    from trajectory_tda.data.annual_partition import build_embeddings_by_year
    from trajectory_tda.topology.zigzag import level_to_year, run_gudhi_zigzag

    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict = {}

    for era_name, (y_start, y_end) in ERAS.items():
        logger.info("=" * 60)
        logger.info("Era: %s (%d–%d)", era_name.upper(), y_start, y_end)
        logger.info("=" * 60)

        # Build embeddings for this era only
        embeddings_by_year = build_embeddings_by_year(
            trajectories_json_path=checkpoint_dir / "01_trajectories.json",
            embeddings_npy_path=checkpoint_dir / "embeddings.npy",
            year_start=y_start,
            year_end=y_end,
            min_individuals=50,
        )

        years = sorted(embeddings_by_year.keys())
        y0 = years[0]
        n_years = len(years)

        # Load metadata for identity tracking
        with open(checkpoint_dir / "01_trajectories.json") as f:
            cp = json.load(f)
        metadata = pd.DataFrame(cp["metadata"])

        logger.info(
            "%d years, %d–%d, n_landmarks=%d",
            n_years,
            years[0],
            years[-1],
            n_landmarks,
        )

        t0 = time.time()
        try:
            h0, h1 = run_gudhi_zigzag(
                embeddings_by_year=embeddings_by_year,
                max_filtration=max_filtration,
                n_landmarks=n_landmarks,
                sparse=sparse,
                metadata=metadata,
                max_dim=max_dim,
                wsl_python=wsl_python,
            )
        except Exception as exc:
            logger.error("Zigzag failed for %s: %s", era_name, exc)
            results[era_name] = {"error": str(exc)}
            continue

        elapsed = time.time() - t0

        # Convert bars to year coordinates
        h0_bars = []
        for birth, death in h0:
            lt = float((death - birth) / 2.0) if np.isfinite(death) else None
            h0_bars.append(
                {
                    "birth_year": float(level_to_year(birth, y0)),
                    "death_year": float(level_to_year(death, y0)) if np.isfinite(death) else None,
                    "lifetime_years": lt,
                }
            )

        h1_finite = h1[np.isfinite(h1[:, 1])] if len(h1) > 0 else np.zeros((0, 2))
        h1_lifetimes = (h1_finite[:, 1] - h1_finite[:, 0]) / 2.0 if len(h1_finite) > 0 else np.array([])

        era_result = {
            "era": era_name,
            "year_range": [y_start, y_end],
            "n_years": n_years,
            "n_landmarks": n_landmarks,
            "n_h0_bars": len(h0),
            "n_h1_bars": len(h1),
            "elapsed_seconds": elapsed,
            "h0_bars": h0_bars,
            "h1_summary": {
                "n_finite": len(h1_lifetimes),
                "mean_lifetime": float(h1_lifetimes.mean()) if len(h1_lifetimes) > 0 else 0.0,
                "median_lifetime": float(np.median(h1_lifetimes)) if len(h1_lifetimes) > 0 else 0.0,
                "max_lifetime": float(h1_lifetimes.max()) if len(h1_lifetimes) > 0 else 0.0,
            },
        }

        results[era_name] = era_result

        logger.info(
            "%s: %d H₀ bars, %d H₁ bars (%.1f s)",
            era_name.upper(),
            len(h0),
            len(h1),
            elapsed,
        )
        for b in h0_bars:
            logger.info(
                "  H₀ bar: %s–%s, lifetime=%s yr",
                f"{b['birth_year']:.0f}" if b["birth_year"] else "?",
                f"{b['death_year']:.0f}" if b["death_year"] else "∞",
                f"{b['lifetime_years']:.1f}" if b["lifetime_years"] else "∞",
            )

        # Save individual era result
        era_path = output_dir / f"zigzag_{era_name}.json"
        with open(era_path, "w") as f:
            json.dump(_convert(era_result), f, indent=2)
        logger.info("Saved: %s", era_path)

    # Save combined summary
    summary_path = output_dir / "era_summary.json"
    with open(summary_path, "w") as f:
        json.dump(_convert(results), f, indent=2)
    logger.info("Saved era summary: %s", summary_path)

    return results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Era-specific zigzag persistence.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint-dir", default="results/trajectory_tda_full")
    parser.add_argument("--output-dir", default="results/trajectory_tda_zigzag/era_specific")
    parser.add_argument("--n-landmarks", type=int, default=150)
    parser.add_argument("--max-filtration", type=float, default=2.0)
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument("--sparse", type=float, default=0.5)
    parser.add_argument("--wsl-python", default="/tmp/dionysus_env/bin/python")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_era_zigzag(
        checkpoint_dir=Path(args.checkpoint_dir),
        output_dir=Path(args.output_dir),
        n_landmarks=args.n_landmarks,
        max_filtration=args.max_filtration,
        max_dim=args.max_dim,
        wsl_python=args.wsl_python,
        sparse=args.sparse,
    )


if __name__ == "__main__":
    main()
