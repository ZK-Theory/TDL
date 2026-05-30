# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.2g first13 / T1.2f truncate greedy-subsampling viability diagnostic.
#   For each strategy, compute the L=5000 maxmin landmark sample, then run a
#   greedy permutation through it recording the covering radius epsilon_N at
#   every step. Time ripser.ripser at n_perm in {500, 1000, 1500, 2000} on the
#   actual landmark sample to measure realised speedup and to confirm top H1
#   features survive the approximation. Output: a single JSON capturing the
#   epsilon_N curve and per-n_perm timing+features for each strategy. Informs
#   Pre-reg #5 redo amendment for length-matched cells (T1.2f, T1.2g).

"""Covering-radius and n_perm timing diagnostic for length-matched Stage-1 cells.

Output JSON shape:
    {
      "task": ...,
      "generated_at": ...,
      "params": {L, seed, target_years, bhps_dir},
      "strategies": {
        "truncate": {
          "n_after_strategy": int,
          "embedding_shape": [N, 20],
          "landmark_shape": [L, 20],
          "covering_radius_curve": [{"N": int, "epsilon": float,
                                     "ratio_to_h1_top": float}, ...],
          "ripser_timing": [{"n_perm_effective": int, "elapsed_sec": float,
                             "h0_n_finite": int, "h1_n_finite": int,
                             "h0_top5_lifetimes": [...],
                             "h1_top5_lifetimes": [...]}, ...]
        },
        "first13": { ... same shape ... }
      }
    }
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import ripser
from scipy.spatial.distance import cdist

from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts.stage1.run_bhps_length_matched import (
    apply_length_strategy,
    load_bhps_sequences,
)
from trajectory_tda.topology.permutation_nulls import maxmin_landmarks


def greedy_permutation_with_cover_radius(
    X: np.ndarray, seed: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    """Greedy (farthest-point) permutation of X with per-step covering radius.

    The covering radius at size k is max over all points x in X of the distance
    from x to the nearest of the first k selected points. This is the
    Cavanna-Jahanseir-Sheehy bound on the bottleneck distance between the
    full-point-cloud persistence diagram and the size-k subsample diagram.

    Args:
        X: Shape (n, d) point cloud.
        seed: Reserved for future tie-breaking; unused here. First point is
            X[0] (deterministic given the input ordering).

    Returns:
        perm: Length-n integer array of selection order.
        cover_radii: Length-n float array; cover_radii[k] is the covering
            radius of the first k+1 selected points.
    """
    n = X.shape[0]
    D = cdist(X, X)
    perm = np.zeros(n, dtype=np.int64)
    cover_radii = np.zeros(n)

    perm[0] = 0
    min_dists = D[0].copy()
    cover_radii[0] = float(min_dists.max())

    for k in range(1, n):
        next_idx = int(np.argmax(min_dists))
        perm[k] = next_idx
        min_dists = np.minimum(min_dists, D[next_idx])
        cover_radii[k] = float(min_dists.max())

    return perm, cover_radii


def time_ripser(X: np.ndarray, n_perm: int | None) -> dict:
    """Time a single ripser.ripser(maxdim=1) call and summarise the diagram."""
    t0 = time.perf_counter()
    result = ripser.ripser(X, maxdim=1, n_perm=n_perm)
    elapsed = time.perf_counter() - t0

    dgm0 = result["dgms"][0]
    dgm1 = result["dgms"][1]
    finite_h0 = dgm0[np.isfinite(dgm0[:, 1])]
    finite_h1 = dgm1[np.isfinite(dgm1[:, 1])]

    h0_lifetimes = sorted(
        (finite_h0[:, 1] - finite_h0[:, 0]).tolist(), reverse=True
    )
    h1_lifetimes = sorted(
        (finite_h1[:, 1] - finite_h1[:, 0]).tolist(), reverse=True
    )

    return {
        "n_perm_effective": int(n_perm) if n_perm is not None else int(X.shape[0]),
        "elapsed_sec": round(elapsed, 3),
        "h0_n_finite": int(finite_h0.shape[0]),
        "h0_n_infinite": int(dgm0.shape[0] - finite_h0.shape[0]),
        "h1_n_finite": int(finite_h1.shape[0]),
        "h1_n_infinite": int(dgm1.shape[0] - finite_h1.shape[0]),
        "h0_top5_lifetimes": [round(float(v), 4) for v in h0_lifetimes[:5]],
        "h1_top5_lifetimes": [round(float(v), 4) for v in h1_lifetimes[:5]],
    }


def run_strategy(
    strategy: str,
    target_years: int,
    L: int,
    seed: int,
    bhps_dir: Path,
    h1_top_reference: float = 2.0,
    n_perm_grid: tuple[int, ...] = (500, 1000, 1500, 2000),
    include_exact_reference: bool = False,
) -> dict:
    print(f"\n========== {strategy.upper()} ==========")
    print(f"Loading BHPS sequences from {bhps_dir} ...")
    sequences, embed_kwargs = load_bhps_sequences(bhps_dir)
    print(f"  total sequences loaded: {len(sequences)}")

    sub_seqs = apply_length_strategy(sequences, strategy, target_years)
    print(f"  n_after_strategy ({strategy}): {len(sub_seqs)}")

    print("Re-embedding via ngram_embed ...")
    t0 = time.perf_counter()
    embeddings, _embed_info = ngram_embed(sub_seqs, **embed_kwargs)
    print(
        f"  embedding shape: {embeddings.shape} (took {time.perf_counter() - t0:.2f}s)"
    )

    print(f"Computing maxmin landmarks (L={L}, seed={seed}) ...")
    t0 = time.perf_counter()
    _, landmarks = maxmin_landmarks(embeddings, L, seed=seed)
    landmarks = np.asarray(landmarks, dtype=np.float64)
    print(
        f"  landmark shape: {landmarks.shape} (took {time.perf_counter() - t0:.2f}s)"
    )

    print(
        f"Computing greedy permutation + covering radius on {L} landmarks ..."
    )
    t0 = time.perf_counter()
    _perm, cover_radii = greedy_permutation_with_cover_radius(landmarks, seed=seed)
    print(f"  greedy permutation took {time.perf_counter() - t0:.2f}s")

    key_Ns = [10, 50, 100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]
    print(
        f"\n  Covering radius curve (h1_top reference for ratio = {h1_top_reference}):"
    )
    print(f"  {'N':>5} | {'epsilon':>10} | {'ratio_to_h1_top':>15}")
    print("  " + "-" * 40)
    cover_radius_summary = []
    for N in key_Ns:
        if N <= L:
            eps_N = float(cover_radii[N - 1])
            ratio = eps_N / h1_top_reference
            print(f"  {N:>5d} | {eps_N:>10.4f} | {ratio:>15.4f}")
            cover_radius_summary.append(
                {
                    "N": int(N),
                    "epsilon": round(eps_N, 4),
                    "ratio_to_h1_top": round(ratio, 4),
                }
            )

    print("\n  Timing ripser.ripser at n_perm grid:")
    print(
        f"  {'n_perm':>7} | {'elapsed_s':>9} | {'H0_fin':>6} | {'H1_fin':>6} | H1 top-5 lifetimes"
    )
    print("  " + "-" * 80)
    timing_results = []
    grid: list[int | None] = list(n_perm_grid)
    if include_exact_reference:
        grid.append(None)
    for n_perm in grid:
        n_perm_label = n_perm if n_perm is not None else L
        print(f"    running n_perm={n_perm_label} ...")
        result = time_ripser(landmarks, n_perm)
        timing_results.append(result)
        print(
            f"  {result['n_perm_effective']:>7d} | {result['elapsed_sec']:>9.3f} | "
            f"{result['h0_n_finite']:>6d} | {result['h1_n_finite']:>6d} | "
            f"{result['h1_top5_lifetimes']}"
        )

    return {
        "strategy": strategy,
        "n_after_strategy": int(len(sub_seqs)),
        "embedding_shape": list(embeddings.shape),
        "landmark_shape": list(landmarks.shape),
        "h1_top_reference_used_for_ratio": h1_top_reference,
        "covering_radius_curve": cover_radius_summary,
        "ripser_timing": timing_results,
    }


def main() -> None:
    out_dir = Path(".apm/diagnostics/t12g-profiling")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "covering_radius_diagnostic.json"

    bhps_dir = Path("results/trajectory_tda_bhps")
    L = 5000
    seed = 42
    target_years = 13

    results: dict = {
        "task": "T1.2g first13 / T1.2f truncate covering-radius + n_perm timing diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "context": (
            "Empirical viability check for ripser.ripser(..., n_perm=N) sparse-Rips "
            "approximation on the L=5000 length-matched cells. epsilon_N is the "
            "Cavanna-Jahanseir-Sheehy bottleneck-distance bound from greedy "
            "subsampling. The decision is whether some defensible n_perm yields "
            "epsilon_N small enough relative to the top H1 feature lifetime to "
            "support a Pre-reg #5 redo amendment for length-matched cells."
        ),
        "params": {
            "L": L,
            "seed": seed,
            "target_years": target_years,
            "bhps_dir": str(bhps_dir),
            "ripser_version": ripser.__version__,
        },
        "strategies": {},
    }

    for strategy in ("truncate", "first13"):
        results["strategies"][strategy] = run_strategy(
            strategy=strategy,
            target_years=target_years,
            L=L,
            seed=seed,
            bhps_dir=bhps_dir,
            h1_top_reference=2.0,
            n_perm_grid=(500, 1000, 1500, 2000),
            include_exact_reference=False,
        )

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDiagnostic JSON written: {out_path}")


if __name__ == "__main__":
    main()
