"""Year-shuffle null model for zigzag persistence.

Paper 3 validation: Permutes the year labels on annual trajectory clouds
and re-runs zigzag persistence to test whether the alignment of
topological features with economic events is non-random.

Under the null hypothesis, the mapping from year labels to point clouds
is arbitrary — any observed alignment between bar birth/death dates and
recession years is coincidental. We test this by:

1. Permuting year labels n_permutations times, keeping point clouds fixed.
2. For each permutation, running zigzag on the re-labelled tower.
3. Computing test statistics:
   - Number of H₀ bars with lifetime > threshold
   - Maximum H₀ bar lifetime
   - Recession-alignment score: count of bars whose birth/death falls
     within ±1 year of a known recession date
4. Computing empirical p-values by comparing observed statistics to the
   null distribution.

Run::

    python -m trajectory_tda.validation.zigzag_null_tests \
        --checkpoint-dir results/trajectory_tda_full \
        --output-dir results/trajectory_tda_zigzag/null_year_shuffle \
        --n-permutations 100 \
        --n-landmarks 150
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Recession years (±1 year alignment window)
RECESSION_YEARS = {1993, 2008, 2009, 2020}


def _recession_alignment_score(
    h0_bars: list[dict],
    recession_years: set[int] = RECESSION_YEARS,
    window: int = 1,
) -> int:
    """Count H₀ bars whose birth or death aligns with recession years.

    Args:
        h0_bars: List of dicts with 'birth_year' and 'death_year' keys.
        recession_years: Set of recession year integers.
        window: Alignment tolerance in years.

    Returns:
        Count of bars with at least one endpoint near a recession year.
    """
    score = 0
    for bar in h0_bars:
        birth = bar.get("birth_year")
        death = bar.get("death_year")
        aligned = False
        for ry in recession_years:
            if birth is not None and abs(birth - ry) <= window:
                aligned = True
            if death is not None and abs(death - ry) <= window:
                aligned = True
        if aligned:
            score += 1
    return score


def _extract_test_stats(
    h0: NDArray[np.float64],
    h1: NDArray[np.float64],
    y0: int,
    lifetime_threshold: float = 5.0,
) -> dict:
    """Extract test statistics from zigzag barcode.

    Args:
        h0: H₀ diagram (n, 2) in zigzag level coords.
        h1: H₁ diagram (n, 2) in zigzag level coords.
        y0: First year (for level → year conversion).
        lifetime_threshold: Min lifetime in years for "long" bars.

    Returns:
        Dict of test statistics.
    """
    from trajectory_tda.topology.zigzag import level_to_year

    # H₀ bar details
    h0_bars = []
    h0_lifetimes = []
    for birth, death in h0:
        lt = float((death - birth) / 2.0) if np.isfinite(death) else None
        h0_bars.append(
            {
                "birth_year": float(level_to_year(birth, y0)),
                "death_year": float(level_to_year(death, y0)) if np.isfinite(death) else None,
                "lifetime_years": lt,
            }
        )
        if lt is not None:
            h0_lifetimes.append(lt)

    h0_lifetimes_arr = np.array(h0_lifetimes) if h0_lifetimes else np.array([0.0])

    return {
        "n_h0_bars": len(h0),
        "n_h1_bars": len(h1),
        "n_h0_long": int((h0_lifetimes_arr > lifetime_threshold).sum()),
        "max_h0_lifetime": float(h0_lifetimes_arr.max()) if len(h0_lifetimes_arr) > 0 else 0.0,
        "mean_h0_lifetime": float(h0_lifetimes_arr.mean()) if len(h0_lifetimes_arr) > 0 else 0.0,
        "recession_alignment": _recession_alignment_score(h0_bars),
        "h0_bars": h0_bars,
    }


def run_null_test(
    checkpoint_dir: Path,
    output_dir: Path,
    n_permutations: int,
    n_landmarks: int,
    year_start: int,
    year_end: int,
    max_filtration: float,
    max_dim: int,
    wsl_python: str,
) -> dict:
    """Run year-shuffle null model.

    Args:
        checkpoint_dir: Path to pipeline checkpoints.
        output_dir: Output directory.
        n_permutations: Number of permutations.
        n_landmarks: Landmarks for zigzag.
        year_start: First year.
        year_end: Last year.
        max_filtration: VR threshold.
        max_dim: Max homology dimension.
        wsl_python: WSL Python path.

    Returns:
        Dict with observed stats, null distribution, and p-values.
    """
    import pandas as pd

    from trajectory_tda.data.annual_partition import build_embeddings_by_year
    from trajectory_tda.topology.zigzag import run_gudhi_zigzag

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info("Loading embeddings and metadata...")
    embeddings_by_year = build_embeddings_by_year(
        trajectories_json_path=checkpoint_dir / "01_trajectories.json",
        embeddings_npy_path=checkpoint_dir / "embeddings.npy",
        year_start=year_start,
        year_end=year_end,
        min_individuals=50,
    )

    with open(checkpoint_dir / "01_trajectories.json") as f:
        cp = json.load(f)
    metadata = pd.DataFrame(cp["metadata"])

    years = sorted(embeddings_by_year.keys())
    y0 = years[0]

    # ── Observed run ──
    logger.info("Computing observed zigzag (n_landmarks=%d)...", n_landmarks)
    h0_obs, h1_obs = run_gudhi_zigzag(
        embeddings_by_year=embeddings_by_year,
        max_filtration=max_filtration,
        n_landmarks=n_landmarks,
        metadata=metadata,
        max_dim=max_dim,
        wsl_python=wsl_python,
    )
    observed = _extract_test_stats(h0_obs, h1_obs, y0)
    logger.info(
        "Observed: %d H₀ bars, %d long, alignment=%d",
        observed["n_h0_bars"],
        observed["n_h0_long"],
        observed["recession_alignment"],
    )

    # ── Null permutations ──
    rng = np.random.default_rng(42)
    null_stats: list[dict] = []
    clouds = [embeddings_by_year[y] for y in years]

    for perm_i in range(n_permutations):
        logger.info("Permutation %d / %d", perm_i + 1, n_permutations)
        t0 = time.time()

        # Shuffle year labels: randomly re-assign point clouds to years
        perm_order = rng.permutation(len(years))
        shuffled_by_year = {years[j]: clouds[perm_order[j]] for j in range(len(years))}

        try:
            h0_null, h1_null = run_gudhi_zigzag(
                embeddings_by_year=shuffled_by_year,
                max_filtration=max_filtration,
                n_landmarks=n_landmarks,
                metadata=None,  # no identity tracking in null
                max_dim=max_dim,
                wsl_python=wsl_python,
            )
            stats = _extract_test_stats(h0_null, h1_null, y0)
            stats["elapsed"] = time.time() - t0
            stats["permutation"] = perm_i
            null_stats.append(stats)

            logger.info(
                "  perm %d: %d H₀ bars, alignment=%d (%.1f s)",
                perm_i + 1,
                stats["n_h0_bars"],
                stats["recession_alignment"],
                stats["elapsed"],
            )

        except Exception as exc:
            logger.error("  perm %d failed: %s", perm_i + 1, exc)
            null_stats.append({"permutation": perm_i, "error": str(exc)})

        # Save intermediate results
        if (perm_i + 1) % 10 == 0:
            _save_intermediate(output_dir, observed, null_stats)

    # ── Compute p-values ──
    valid_nulls = [s for s in null_stats if "error" not in s]
    n_valid = len(valid_nulls)

    p_values = {}
    if n_valid > 0:
        for stat_key in [
            "n_h0_bars",
            "n_h0_long",
            "max_h0_lifetime",
            "recession_alignment",
        ]:
            obs_val = observed[stat_key]
            null_vals = np.array([s[stat_key] for s in valid_nulls])
            p_greater = float(np.sum(null_vals >= obs_val) / n_valid)
            p_values[stat_key] = {
                "observed": obs_val,
                "null_mean": float(null_vals.mean()),
                "null_std": float(null_vals.std()),
                "p_value_greater": p_greater,
                "p_value_less": float(np.sum(null_vals <= obs_val) / n_valid),
            }
            logger.info(
                "%s: observed=%.2f, null_mean=%.2f±%.2f, p=%.4f",
                stat_key,
                obs_val,
                null_vals.mean(),
                null_vals.std(),
                p_greater,
            )

    results = {
        "observed": observed,
        "null_stats": null_stats,
        "p_values": p_values,
        "n_permutations": n_permutations,
        "n_valid": n_valid,
        "n_landmarks": n_landmarks,
    }

    out_path = output_dir / "null_test_results.json"
    with open(out_path, "w") as f:
        json.dump(_convert(results), f, indent=2)
    logger.info("Saved: %s", out_path)

    return results


def _save_intermediate(output_dir: Path, observed: dict, null_stats: list) -> None:
    """Save intermediate results for resumption."""
    intermediate = {
        "observed": observed,
        "null_stats": null_stats,
        "n_completed": len(null_stats),
    }
    path = output_dir / "intermediate_results.json"
    with open(path, "w") as f:
        json.dump(_convert(intermediate), f, indent=2)


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


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Year-shuffle null model for zigzag persistence.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint-dir", default="results/trajectory_tda_full")
    parser.add_argument("--output-dir", default="results/trajectory_tda_zigzag/null_year_shuffle")
    parser.add_argument("--n-permutations", type=int, default=100)
    parser.add_argument("--n-landmarks", type=int, default=150)
    parser.add_argument("--year-start", type=int, default=1991)
    parser.add_argument("--year-end", type=int, default=2022)
    parser.add_argument("--max-filtration", type=float, default=2.0)
    parser.add_argument("--max-dim", type=int, default=1)
    parser.add_argument("--wsl-python", default="/tmp/miniforge3/bin/python")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_null_test(
        checkpoint_dir=Path(args.checkpoint_dir),
        output_dir=Path(args.output_dir),
        n_permutations=args.n_permutations,
        n_landmarks=args.n_landmarks,
        year_start=args.year_start,
        year_end=args.year_end,
        max_filtration=args.max_filtration,
        max_dim=args.max_dim,
        wsl_python=args.wsl_python,
    )


if __name__ == "__main__":
    main()
