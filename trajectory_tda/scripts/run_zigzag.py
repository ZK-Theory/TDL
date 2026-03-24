"""Orchestrator for Paper 3 Zigzag Persistence pipeline.

Runs four stages against the checkpoint artefacts produced by
``run_pipeline.py``:

    Stage 1  Annual partition — build embeddings_by_year dict
    Stage 2  Annual snapshots — VR PH per year (independent)
    Stage 3  Topological time series — scalar Betti/persistence summaries
    Stage 4  Full zigzag — cross-year feature tracking via dionysus (WSL bridge)

Run from the command line::

    python -m trajectory_tda.scripts.run_zigzag \\
        --checkpoint-dir results/trajectory_tda_full \\
        --output-dir results/trajectory_tda_zigzag

Resume/skip completed stages::

    python -m trajectory_tda.scripts.run_zigzag \\
        --checkpoint-dir results/trajectory_tda_full \\
        --output-dir results/trajectory_tda_zigzag \\
        --skip-stages 1 2
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ─────────────────────────────────────────────────────────────────────
# Checkpoint helpers
# ─────────────────────────────────────────────────────────────────────


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


def _save(data: dict, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fpath = output_dir / f"{name}.json"
    with open(fpath, "w") as f:
        json.dump(_convert(data), f, indent=2)
    logger.info("Saved: %s", fpath)


def _load(output_dir: Path, name: str) -> dict:
    fpath = output_dir / f"{name}.json"
    if not fpath.exists():
        raise FileNotFoundError(f"Checkpoint not found: {fpath}")
    with open(fpath) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# Pipeline stages
# ─────────────────────────────────────────────────────────────────────


def stage1_annual_partition(
    checkpoint_dir: Path,
    output_dir: Path,
    year_start: int,
    year_end: int,
    min_individuals: int,
) -> dict:
    """Build per-year embedding sub-matrices from frozen PCA embeddings.

    Args:
        checkpoint_dir: Directory containing ``01_trajectories.json``
            and ``embeddings.npy`` from ``run_pipeline.py``.
        output_dir: Directory to write ``01_annual_counts.json``.
        year_start: First calendar year (inclusive).
        year_end: Last calendar year (inclusive).
        min_individuals: Warn (but do not skip) years below this count.

    Returns:
        Dict mapping int year → embedding NDArray.
    """
    from trajectory_tda.data.annual_partition import (
        annual_counts,
        build_embeddings_by_year,
    )

    logger.info("=" * 60)
    logger.info("Stage 1: Annual partition (%d–%d)", year_start, year_end)
    logger.info("=" * 60)

    trajectories_json = checkpoint_dir / "01_trajectories.json"
    embeddings_npy = checkpoint_dir / "embeddings.npy"

    embeddings_by_year = build_embeddings_by_year(
        trajectories_json_path=trajectories_json,
        embeddings_npy_path=embeddings_npy,
        year_start=year_start,
        year_end=year_end,
        min_individuals=min_individuals,
    )

    counts = annual_counts(embeddings_by_year)
    _save(
        {"year_counts": counts, "year_start": year_start, "year_end": year_end},
        output_dir,
        "01_annual_counts",
    )
    logger.info("Stage 1 complete: %d years partitioned", len(embeddings_by_year))
    return embeddings_by_year


def stage2_annual_snapshots(
    embeddings_by_year: dict,
    output_dir: Path,
    n_landmarks: int,
    max_filtration: float,
) -> list:
    """Compute independent VR persistence diagrams for each annual snapshot.

    Args:
        embeddings_by_year: Dict from :func:`stage1_annual_partition`.
        output_dir: Directory to write ``02_annual_diagrams.json``.
        n_landmarks: Max landmarks per year for Ripser (default 500).
        max_filtration: Max edge length for VR filtration.

    Returns:
        List of :class:`~trajectory_tda.topology.zigzag.AnnualSnapshot`.
    """
    from trajectory_tda.topology.zigzag import create_annual_snapshots

    logger.info("=" * 60)
    logger.info("Stage 2: Annual VR persistence (%d years)", len(embeddings_by_year))
    logger.info("=" * 60)

    snapshots = create_annual_snapshots(
        embeddings_by_year=embeddings_by_year,
        max_filtration=max_filtration,
        n_landmarks=n_landmarks,
    )

    diagrams_out = {}
    for snap in snapshots:
        diagrams_out[str(snap.year)] = {
            "n_individuals": snap.n_individuals,
            "n_landmarks": snap.n_landmarks,
            "economic_event": snap.economic_event,
            "diagram_h0": snap.diagram_h0.tolist(),
            "diagram_h1": snap.diagram_h1.tolist(),
        }

    _save(
        {
            "n_years": len(snapshots),
            "n_landmarks": n_landmarks,
            "diagrams": diagrams_out,
        },
        output_dir,
        "02_annual_diagrams",
    )
    logger.info("Stage 2 complete: %d annual diagrams", len(snapshots))
    return snapshots


def stage3_time_series(snapshots: list, output_dir: Path) -> dict:
    """Assemble topological time series from independent annual snapshots.

    Produces per-year β₀, β₁, and total-persistence series suitable for
    comparison against economic cycle indicators without the cost of full
    zigzag.

    Args:
        snapshots: List from :func:`stage2_annual_snapshots`.
        output_dir: Directory to write ``03_time_series.json``.

    Returns:
        Dict with time series arrays keyed by name.
    """
    from trajectory_tda.topology.zigzag import (
        ZigzagResult,
        compute_topological_time_series,
    )

    logger.info("=" * 60)
    logger.info("Stage 3: Topological time series")
    logger.info("=" * 60)

    result: ZigzagResult = compute_topological_time_series(snapshots)

    ts_data = {
        "years": result.years,
        "betti_0_series": result.betti_0_series.tolist(),
        "total_persistence_h0": result.total_persistence_h0.tolist(),
        "total_persistence_h1": result.total_persistence_h1.tolist(),
        "recession_years_mask": result.recession_years_mask().tolist(),
        "n_individuals": [s.n_individuals for s in snapshots],
        "economic_events": {str(y): e for y, e in [(s.year, s.economic_event) for s in snapshots if s.economic_event]},
    }

    _save(ts_data, output_dir, "03_time_series")

    # Log recession-vs-expansion summary
    mask = result.recession_years_mask()
    if mask.any() and (~mask).any():
        rec_mean = float(result.betti_0_series[mask].mean())
        exp_mean = float(result.betti_0_series[~mask].mean())
        logger.info(
            "Stage 3 complete: mean β₀ recession=%.2f, expansion=%.2f (Δ=%.2f)",
            rec_mean,
            exp_mean,
            rec_mean - exp_mean,
        )
    else:
        logger.info("Stage 3 complete: %d time points", len(result.years))

    return ts_data


def stage4_zigzag(
    embeddings_by_year: dict,
    output_dir: Path,
    n_landmarks: int,
    max_filtration: float,
    sparse: float,
    checkpoint_dir: Path | None = None,
    max_dim: int = 1,
    wsl_python: str = "/tmp/miniforge3/bin/python",
) -> dict:
    """Run true zigzag persistence on the annual diamond tower.

    Computes a *single* H₀/H₁ barcode over the full multi-year sequence
    P_{y0} ↪ P_{y0}∪P_{y0+1} ↩ P_{y0+1} ↪ … ↩ P_{y_end} via dionysus
    running under WSL.  A bar of length *k* represents a topological
    feature (cluster or loop) that persisted for *k* calendar years.

    Args:
        embeddings_by_year: Dict from :func:`stage1_annual_partition`.
        output_dir: Directory to write ``04_zigzag_diagrams.json``.
        n_landmarks: Max landmarks per year for simplex building.
        max_filtration: Max edge length for Rips filtration.
        sparse: Unused — retained for API compatibility.
        checkpoint_dir: If provided, load trajectory metadata from
            ``01_trajectories.json`` here to enable per-individual identity
            tracking across years.

    Returns:
        Dict with ``h0_bars`` and ``h1_bars`` arrays.
    """
    import json as _json  # noqa: PLC0415 — avoid conflict with top-level json

    import numpy as _np  # noqa: PLC0415
    import pandas as _pd  # noqa: PLC0415

    from trajectory_tda.topology.zigzag import run_gudhi_zigzag  # noqa: PLC0415

    logger.info("=" * 60)
    logger.info("Stage 4: True zigzag persistence (%d years)", len(embeddings_by_year))
    logger.info("=" * 60)

    # Load per-individual metadata so that identity is tracked across years
    metadata: _pd.DataFrame | None = None
    if checkpoint_dir is not None:
        traj_json = checkpoint_dir / "01_trajectories.json"
        if traj_json.exists():
            with open(traj_json) as _f:
                cp = _json.load(_f)
            metadata = _pd.DataFrame(cp["metadata"])
            logger.info(
                "Loaded metadata for %d individuals (start %d–%d)",
                len(metadata),
                int(metadata["start_year"].min()),
                int(metadata["end_year"].max()),
            )
        else:
            logger.warning(
                "01_trajectories.json not found in %s; " "falling back to synthetic metadata (test mode only)",
                checkpoint_dir,
            )

    h0, h1 = run_gudhi_zigzag(
        embeddings_by_year=embeddings_by_year,
        max_filtration=max_filtration,
        n_landmarks=n_landmarks,
        sparse=sparse,
        metadata=metadata,
        max_dim=max_dim,
        wsl_python=wsl_python,
    )

    years = sorted(embeddings_by_year.keys())
    y0 = years[0]

    from trajectory_tda.topology.zigzag import level_to_year  # noqa: PLC0415

    def _bars_with_years(
        diagram: _np.ndarray,
    ) -> list[dict]:
        out = []
        for birth, death in diagram:
            out.append(
                {
                    "birth_level": float(birth),
                    "death_level": float(death) if _np.isfinite(death) else None,
                    "birth_year": float(level_to_year(birth, y0)),
                    "death_year": (float(level_to_year(death, y0)) if _np.isfinite(death) else None),
                    "lifetime_years": (float((death - birth) / 2.0) if _np.isfinite(death) else None),
                }
            )
        return out

    zigzag_data = {
        "n_years": len(embeddings_by_year),
        "year_start": years[0],
        "year_end": years[-1],
        "h0_bars": _bars_with_years(h0),
        "h1_bars": _bars_with_years(h1),
        "n_h0_bars": len(h0),
        "n_h1_bars": len(h1),
        "n_landmarks": n_landmarks,
    }

    _save(zigzag_data, output_dir, "04_zigzag_diagrams")
    logger.info("Stage 4 complete: %d H₀ bars, %d H₁ bars", len(h0), len(h1))
    return zigzag_data


# ─────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for run_zigzag."""
    p = argparse.ArgumentParser(
        description="Paper 3 zigzag persistence pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--checkpoint-dir",
        default="results/trajectory_tda_full",
        help="Directory containing outputs from run_pipeline.py.",
    )
    p.add_argument(
        "--output-dir",
        default="results/trajectory_tda_zigzag",
        help="Directory for zigzag pipeline outputs.",
    )
    p.add_argument("--year-start", type=int, default=1991, help="First calendar year.")
    p.add_argument("--year-end", type=int, default=2023, help="Last calendar year.")
    p.add_argument(
        "--n-landmarks-ph",
        type=int,
        default=500,
        help="Landmarks per year for Stage 2 independent PH.",
    )
    p.add_argument(
        "--n-landmarks-zigzag",
        type=int,
        default=300,
        help="Landmarks per year for Stage 4 zigzag tower.",
    )
    p.add_argument(
        "--max-filtration",
        type=float,
        default=2.0,
        help="Maximum edge length for Vietoris-Rips filtration.",
    )
    p.add_argument(
        "--sparse",
        type=float,
        default=0.5,
        help="SparseRipsComplex sparsity parameter (Stage 4 only).",
    )
    p.add_argument(
        "--min-individuals",
        type=int,
        default=50,
        help="Minimum active individuals before a warning is logged.",
    )
    p.add_argument(
        "--skip-stages",
        type=int,
        nargs="*",
        default=[],
        metavar="N",
        help="Stage numbers to skip (e.g. --skip-stages 1 2 to start from Stage 3).",
    )
    p.add_argument(
        "--max-dim",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="Maximum homology dimension for Stage 4 zigzag (default: 1 → H₀ + H₁ edges only). "
        "Use 2 to add triangles (required for finite H₁ bars, but expensive).",
    )
    p.add_argument(
        "--wsl-python",
        default="/tmp/miniforge3/bin/python",
        help="Path inside WSL to the Python interpreter with dionysus installed.",
    )
    p.add_argument("--skip-zigzag", action="store_true", help="Skip Stage 4 (full zigzag).")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return p


def main(args: argparse.Namespace | None = None) -> None:
    """Run the zigzag pipeline."""
    if args is None:
        args = build_parser().parse_args()

    _setup_logging(args.verbose)

    checkpoint_dir = Path(args.checkpoint_dir)
    output_dir = Path(args.output_dir)
    skip = set(args.skip_stages or [])

    t_start = time.time()
    embeddings_by_year: dict | None = None

    # ── Stage 1 ──────────────────────────────────────────────────────
    if 1 not in skip:
        embeddings_by_year = stage1_annual_partition(
            checkpoint_dir=checkpoint_dir,
            output_dir=output_dir,
            year_start=args.year_start,
            year_end=args.year_end,
            min_individuals=args.min_individuals,
        )
    else:
        logger.info("Stage 1 skipped — loading annual counts from checkpoint")
        counts_cp = _load(output_dir, "01_annual_counts")
        logger.info("Loaded annual counts: %d years", len(counts_cp.get("year_counts", {})))

    # ── Stage 2 ──────────────────────────────────────────────────────
    snapshots: list | None = None
    if 2 not in skip:
        if embeddings_by_year is None:
            # Rebuild from disk if stage 1 was skipped
            from trajectory_tda.data.annual_partition import build_embeddings_by_year

            embeddings_by_year = build_embeddings_by_year(
                trajectories_json_path=checkpoint_dir / "01_trajectories.json",
                embeddings_npy_path=checkpoint_dir / "embeddings.npy",
                year_start=args.year_start,
                year_end=args.year_end,
                min_individuals=args.min_individuals,
            )
        snapshots = stage2_annual_snapshots(
            embeddings_by_year=embeddings_by_year,
            output_dir=output_dir,
            n_landmarks=args.n_landmarks_ph,
            max_filtration=args.max_filtration,
        )
    else:
        logger.info("Stage 2 skipped")

    # ── Stage 3 ──────────────────────────────────────────────────────
    if 3 not in skip:
        if snapshots is None:
            raise RuntimeError(
                "Stage 3 requires Stage 2 snapshots. " "Do not skip Stage 2 without also skipping Stage 3."
            )
        stage3_time_series(snapshots=snapshots, output_dir=output_dir)
    else:
        logger.info("Stage 3 skipped")

    # ── Stage 4 ──────────────────────────────────────────────────────
    if 4 not in skip and not getattr(args, "skip_zigzag", False):
        if embeddings_by_year is None:
            from trajectory_tda.data.annual_partition import build_embeddings_by_year

            embeddings_by_year = build_embeddings_by_year(
                trajectories_json_path=checkpoint_dir / "01_trajectories.json",
                embeddings_npy_path=checkpoint_dir / "embeddings.npy",
                year_start=args.year_start,
                year_end=args.year_end,
                min_individuals=args.min_individuals,
            )
        stage4_zigzag(
            embeddings_by_year=embeddings_by_year,
            output_dir=output_dir,
            n_landmarks=args.n_landmarks_zigzag,
            max_filtration=args.max_filtration,
            sparse=args.sparse,
            checkpoint_dir=checkpoint_dir,
            max_dim=args.max_dim,
            wsl_python=args.wsl_python,
        )
    else:
        logger.info("Stage 4 skipped")

    elapsed = time.time() - t_start
    logger.info("Pipeline complete in %.1f s  (%.1f min)", elapsed, elapsed / 60)


if __name__ == "__main__":
    main()
