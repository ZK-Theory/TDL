# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: BHPS length-matched W₂ H₁ sub-analysis (ISSUE L3).
#   The v1 draft reports BHPS Markov-1 H₁ p=0.002 vs USoc H₁ p=0.226 and
#   attributes the difference to window length (14.5 vs 12.9 years), but
#   acknowledges this is unverified. This script tests the attribution by
#   truncating BHPS trajectories to match the USoc mean length (default 13
#   years) and re-running the W₂ Markov-1 H₁ test.
#
# Two strategies (both run by default):
#   "first13"    — keep only trajectories with length >= target_years,
#                  truncate to exactly target_years (n=5363 at target=13).
#                  Cleanest length-control: uniform sequence length.
#   "truncation" — truncate all trajectories to at most target_years, keeping
#                  shorter sequences at their natural length (n=8509).
#                  Includes the short-cohort (len=10) trajectories as-is.
#
# Decision rule (pre-registered):
#   Both strategies: H₁ p > 0.05 → rejection is a window-length artefact.
#   Both strategies: H₁ p ≤ 0.05 → rejection survives length control.
#   Strategies disagree → report both, focus on "first13" as primary.

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts.run_wasserstein_battery import _convert_numpy
from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

logger = logging.getLogger(__name__)


def _load_sequences(checkpoint_dir: Path) -> tuple[list[list[str]], dict[str, Any]]:
    """Load raw sequences and embed_kwargs from BHPS checkpoint."""
    seq_path = checkpoint_dir / "01_trajectories_sequences.json"
    info_path = checkpoint_dir / "02_embedding.json"

    if not seq_path.exists():
        raise FileNotFoundError(f"Sequences not found: {seq_path}")

    with open(seq_path) as f:
        sequences = json.load(f)

    embed_kwargs: dict[str, Any] = {"pca_dim": 20, "include_bigrams": True, "tfidf": False}
    if info_path.exists():
        with open(info_path) as f:
            info = json.load(f)
        ei = info.get("info", {})
        embed_kwargs["pca_dim"] = ei.get("final_dims", 20)
        embed_kwargs["tfidf"] = ei.get("tfidf", False)
        if ei.get("n_bigram_dims", 0) > 0:
            embed_kwargs["include_bigrams"] = True

    return sequences, embed_kwargs


def _apply_strategy(
    sequences: list[list[str]],
    strategy: str,
    target_years: int,
) -> list[list[str]]:
    """Apply a length-truncation strategy and return the sub-sampled sequences."""
    if strategy == "first13":
        # Only trajectories long enough; all truncated to exactly target_years.
        return [seq[:target_years] for seq in sequences if len(seq) >= target_years]
    if strategy == "truncation":
        # All trajectories; those exceeding target_years are truncated.
        return [seq[:target_years] for seq in sequences]
    raise ValueError(f"Unknown strategy: {strategy!r}. Use 'first13' or 'truncation'.")


def _run_one_strategy(
    sequences: list[list[str]],
    embed_kwargs: dict[str, Any],
    strategy: str,
    target_years: int,
    n_permutations: int,
    n_landmarks: int,
    seed: int,
) -> dict[str, Any]:
    """Apply strategy, re-embed, run W₂ Markov-1 H₀+H₁ test."""
    sub_seqs = _apply_strategy(sequences, strategy, target_years)
    lengths = [len(s) for s in sub_seqs]
    length_dist = dict(sorted(Counter(lengths).items()))
    logger.info(
        "Strategy '%s': n=%d, mean_len=%.1f, length_dist=%s",
        strategy,
        len(sub_seqs),
        float(np.mean(lengths)),
        length_dist,
    )

    logger.info("Re-embedding %d sequences (pca_dim=%d)...", len(sub_seqs), embed_kwargs["pca_dim"])
    t_embed = time.time()
    embeddings, _ = ngram_embed(sub_seqs, **embed_kwargs)
    logger.info("  Embedded in %.1fs, shape %s", time.time() - t_embed, embeddings.shape)

    logger.info(
        "Running W₂ Markov-1 test: n_perms=%d, L=%d, seed=%d",
        n_permutations,
        n_landmarks,
        seed,
    )
    t_test = time.time()
    result = permutation_test_trajectories(
        embeddings=embeddings,
        trajectories=sub_seqs,
        null_type="markov",
        n_permutations=n_permutations,
        max_dim=1,
        n_landmarks=n_landmarks,
        statistic="wasserstein",
        markov_order=1,
        n_jobs=1,
        seed=seed,
        embed_kwargs=embed_kwargs,
    )
    elapsed = time.time() - t_test
    result["elapsed_seconds"] = elapsed
    result["strategy"] = strategy
    result["target_years"] = target_years
    result["n_trajectories"] = len(sub_seqs)
    result["mean_length"] = float(np.mean(lengths))
    result["length_distribution"] = length_dist

    for key in ("H0", "H1"):
        if key in result:
            r = result[key]
            logger.info(
                "  %s: W(obs,null)=%.3f, W(null,null)=%.3f, p=%.4f (%s)",
                key,
                r["mean_wasserstein_obs_null"],
                r["mean_wasserstein_null_null"],
                r["p_value"],
                "***" if r["p_value"] < 0.001 else ("*" if r["p_value"] < 0.05 else "ns"),
            )

    return result


def run_length_matched(
    checkpoint_dir: Path,
    strategies: list[str],
    target_years: int = 13,
    n_permutations: int = 100,
    n_landmarks: int = 5000,
    seed: int = 42,
    output_dir: Path | None = None,
    date_suffix: str = "20260502",
) -> dict[str, dict[str, Any]]:
    """Run length-matched W₂ Markov-1 tests for all requested strategies.

    Args:
        checkpoint_dir: BHPS checkpoint directory.
        strategies: List of 'first13' and/or 'truncation'.
        target_years: Truncation target (default 13, matching USoc mean 12.9).
        n_permutations: Permutations per test.
        n_landmarks: Landmark count.
        seed: RNG seed.
        output_dir: Directory for result JSONs (default: checkpoint_dir/length_matched/).
        date_suffix: Appended to output filenames.

    Returns:
        Dict of strategy → result dict.
    """
    sequences, embed_kwargs = _load_sequences(checkpoint_dir)
    logger.info(
        "BHPS checkpoint: n=%d sequences, mean_len=%.1f, target=%d years",
        len(sequences),
        float(np.mean([len(s) for s in sequences])),
        target_years,
    )

    out_dir = output_dir or (checkpoint_dir / "length_matched")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, dict[str, Any]] = {}
    for strategy in strategies:
        logger.info("\n%s\nStrategy: %s\n%s", "=" * 60, strategy, "=" * 60)
        t0 = time.time()

        result = _run_one_strategy(
            sequences,
            embed_kwargs,
            strategy,
            target_years,
            n_permutations,
            n_landmarks,
            seed,
        )
        result["total_elapsed_seconds"] = time.time() - t0
        all_results[strategy] = result

        out_path = out_dir / f"nulls_markov1_W2_{strategy}{target_years}_L{n_landmarks}_{date_suffix}.json"
        with open(out_path, "w") as f:
            json.dump(_convert_numpy(result), f, indent=2)
        logger.info("Saved %s → %s", strategy, out_path)

    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "BHPS length-matched W₂ Markov-1 H₁ test (ISSUE L3). "
            "Tests whether the BHPS H₁ rejection is a window-length artefact."
        )
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        required=True,
        help="BHPS checkpoint directory (results/trajectory_tda_bhps).",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["first13", "truncation"],
        choices=["first13", "truncation"],
        help="Length-control strategies to run (default: both).",
    )
    parser.add_argument(
        "--target-years",
        type=int,
        default=13,
        help="Truncation target in years/states (default: 13, matching USoc mean 12.9).",
    )
    parser.add_argument("--n-perms", type=int, default=100)
    parser.add_argument("--landmarks", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: checkpoint-dir/length_matched/).",
    )
    parser.add_argument("--date-suffix", type=str, default="20260502")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    run_length_matched(
        checkpoint_dir=Path(args.checkpoint_dir),
        strategies=args.strategies,
        target_years=args.target_years,
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
        seed=args.seed,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        date_suffix=args.date_suffix,
    )


if __name__ == "__main__":
    main()
