# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Stage 1 BHPS length-matched W2 + landscape L2 battery — tests whether
#   the BHPS topological signal persists when trajectory length is matched to
#   USoc's observation horizon (mean ~12.9 waves). One strategy per launch,
#   selected by --strategy {truncate, first13}. Methodologically parity-matched
#   to run_bhps_headline.py (same B, L, seed, n_null_pairs, vectorisation, and
#   W2 + landscape L2 pair); the only differences are the length-control step
#   and the re-embedding step before the maxmin landmarks.
"""Stage 1 BHPS length-matched phase script.

Sub-phases T1.2f (``--strategy truncate``) and T1.2g (``--strategy first13``)
of the resumed batch on ``run/stage1-headline-batch``.

Both strategies are length-matched against ``--target-years`` (default 13,
matching USoc mean length of ~12.9 waves):

- ``truncate``: every BHPS trajectory is truncated to the first
  ``target_years`` waves; trajectories shorter than ``target_years`` are kept
  at their original length (no padding).
- ``first13``: only BHPS trajectories of length >= ``target_years`` are kept,
  each truncated to exactly ``target_years`` waves.

The sub-sampled / truncated sequences are then re-embedded via
``ngram_embed`` with the same ``embed_kwargs`` as the BHPS headline checkpoint
and fed into ``core.run_headline_from_embeddings`` for the full W2 + landscape
L2 battery. Output JSON is committed at the worktree path; the null-diagram
cache is written to PROJ_ROOT (gitignored, two-path rule).
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path

from typing import Any

import numpy as np

from trajectory_tda.embedding.ngram_embed import ngram_embed
from trajectory_tda.scripts.stage1 import _battery_core as core

logger = logging.getLogger(__name__)

# --- Strategy implementation ------------------------------------------------

# Maps the canonical CLI strategy name to the internal label written into the
# output JSON / phase tag / filename. ``truncate`` is the canonical name in
# the resumed batch task prompt; we keep the JSON/filename label consistent
# so the T1.2h assembler can locate both files by their strategy suffix.
STRATEGIES = {"truncate", "first13"}


def apply_length_strategy(
    sequences: list[list[str]],
    strategy: str,
    target_years: int,
) -> list[list[str]]:
    """Apply a length-control strategy and return the sub-sampled sequences.

    Args:
        sequences: Raw BHPS state sequences (variable length).
        strategy: Either ``"truncate"`` (truncate everything to <= target_years)
            or ``"first13"`` (drop shorter sequences; truncate the rest to
            exactly target_years).
        target_years: Truncation length in waves/states.

    Returns:
        Sub-sampled sequences ready for re-embedding.
    """
    if strategy == "first13":
        return [seq[:target_years] for seq in sequences if len(seq) >= target_years]
    if strategy == "truncate":
        return [seq[:target_years] for seq in sequences]
    raise ValueError(f"Unknown strategy: {strategy!r}. Use 'truncate' or 'first13'.")


# --- Checkpoint loading -----------------------------------------------------


def load_bhps_sequences(checkpoint_dir: Path) -> tuple[list[list[str]], dict[str, Any]]:
    """Load raw BHPS sequences and embed_kwargs from the checkpoint dir.

    Mirrors ``run_wasserstein_battery.load_checkpoint`` minus the
    ``embeddings.npy`` load (since we re-embed after applying the strategy).

    Args:
        checkpoint_dir: BHPS checkpoint directory (default
            ``<PROJ_ROOT>/results/trajectory_tda_bhps``).

    Returns:
        Tuple of (raw sequences, embed_kwargs dict matching ``ngram_embed``).
    """
    seq_path = checkpoint_dir / "01_trajectories_sequences.json"
    info_path = checkpoint_dir / "02_embedding.json"

    if not seq_path.exists():
        raise FileNotFoundError(f"Sequences not found: {seq_path}")

    with open(seq_path) as f:
        sequences = json.load(f)

    embed_kwargs: dict[str, Any] = {
        "pca_dim": 20,
        "include_bigrams": True,
        "tfidf": False,
    }
    if info_path.exists():
        with open(info_path) as f:
            info = json.load(f)
        ei = info.get("info", {})
        embed_kwargs["pca_dim"] = ei.get("final_dims", 20)
        embed_kwargs["tfidf"] = ei.get("tfidf", False)
        if ei.get("n_bigram_dims", 0) > 0:
            embed_kwargs["include_bigrams"] = True

    return sequences, embed_kwargs


# --- Main -------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1 BHPS length-matched phase")
    parser.add_argument(
        "--bhps-dir",
        type=str,
        default=str(core.proj_root() / "results/trajectory_tda_bhps"),
        help=(
            "Upstream BHPS trajectory checkpoint directory. Defaults to the "
            "canonical PROJ_ROOT path so worktree execution works without an "
            "override (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--strategy",
        type=str,
        required=True,
        choices=sorted(STRATEGIES),
        help="Length-control strategy. 'truncate' truncates all sequences; "
        "'first13' keeps only sequences of length >= target_years.",
    )
    parser.add_argument(
        "--target-years",
        type=int,
        default=13,
        help=("Truncation target in waves/states (default 13, matching USoc mean of ~12.9 waves)."),
    )
    parser.add_argument("--L", type=int, default=core.DEFAULT_L, help="Landmarks (default 5000)")
    parser.add_argument("--B", type=int, default=core.DEFAULT_B, help="Permutations (default 1000)")
    parser.add_argument("--seed", type=int, default=core.DEFAULT_SEED)
    parser.add_argument("--k-max", type=int, default=core.DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=core.DEFAULT_N_POINTS)
    parser.add_argument(
        "--n-null-pairs",
        type=int,
        default=core.DEFAULT_N_NULL_PAIRS,
        help="Cap on null-null pairs (default 500)",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=4,
        help="Permutation parallelism (locked to 4 at L>=2000 per OOM finding)",
    )
    parser.add_argument(
        "--frozen-loadings",
        action="store_true",
        help="Reuse the length-matched observed embedding scaler/PCA basis for Markov-null embeddings.",
    )
    parser.add_argument("--smoke", action="store_true", help="Smoke-test mode.")
    parser.add_argument(
        "--probe-symmetric-dedup",
        action="store_true",
        help=(
            "Pre-reg #5 redo amendment robustness probe: force nulls to use "
            "n_perm = obs_n_dedup (eliminating the observed-vs-null vertex-count "
            "asymmetry). Requires --frozen-loadings."
        ),
    )
    parser.add_argument(
        "--probe-pinned-thresh",
        action="store_true",
        help=(
            "Pre-reg #5 redo amendment robustness probe: pin the ripser thresh "
            "to the enclosing radius of observed post-dedup landmarks for both "
            "observed and null PD computations (eliminating compute_rips_ph "
            "auto-thresh subsample drift). Requires --frozen-loadings."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    phase_tag = f"bhps_length_matched_{args.strategy}"
    core.write_launch_marker(
        phase_tag,
        {
            "strategy": args.strategy,
            "target_years": args.target_years,
            "L": args.L,
            "B": args.B,
            "seed": args.seed,
            "smoke": args.smoke,
            "frozen_loadings": args.frozen_loadings,
        },
    )

    sequences, embed_kwargs = load_bhps_sequences(Path(args.bhps_dir))
    logger.info(
        "BHPS checkpoint: n=%d sequences, mean_len=%.2f, target=%d",
        len(sequences),
        float(np.mean([len(s) for s in sequences])),
        args.target_years,
    )

    sub_seqs = apply_length_strategy(sequences, args.strategy, args.target_years)
    lengths = [len(s) for s in sub_seqs]
    length_dist = dict(sorted(Counter(lengths).items()))
    logger.info(
        "Strategy '%s': n=%d, mean_len=%.2f, length_dist=%s",
        args.strategy,
        len(sub_seqs),
        float(np.mean(lengths)) if lengths else 0.0,
        length_dist,
    )

    logger.info(
        "Re-embedding %d sequences (pca_dim=%s, include_bigrams=%s, tfidf=%s)...",
        len(sub_seqs),
        embed_kwargs.get("pca_dim"),
        embed_kwargs.get("include_bigrams"),
        embed_kwargs.get("tfidf"),
    )
    embeddings, embedding_info = ngram_embed(sub_seqs, **embed_kwargs)
    frozen_models = embedding_info["fitted_models"] if args.frozen_loadings else None
    logger.info("Re-embedded shape: %s", embeddings.shape)

    label = f"BHPS LM-{args.strategy}"
    out, null_results, ph_obs = core.run_headline_from_embeddings(
        embeddings=embeddings,
        trajectories=sub_seqs,
        embed_kwargs=embed_kwargs,
        n_permutations=args.B,
        n_landmarks=args.L,
        k_max=args.k_max,
        n_points=args.n_points,
        seed=args.seed,
        label=label,
        phase_tag=phase_tag,
        n_jobs=args.n_jobs,
        n_null_pairs_cap=args.n_null_pairs,
        frozen_models=frozen_models,
        dedup_length_matched=True,
        probe_symmetric_dedup=args.probe_symmetric_dedup,
        probe_pinned_thresh=args.probe_pinned_thresh,
    )
    # Pop the dedup provenance off the result so the JSON's `result` block
    # stays a clean aggregate-output payload; the dedup fields live on
    # run_params per the length-matched-run-params schema contract.
    dedup_info = out.pop("_dedup_info", None)

    today = date.today().isoformat()
    smoke_tag = "_smoke" if args.smoke else ""
    frozen_tag = "_frozen" if args.frozen_loadings else ""
    # Probe-mode tags keep probe result files distinct from the production
    # frozen-dedup result already on the branch. The two probes are
    # mutually exclusive at the CLI; combining them produces a stacked tag.
    probe_tags: list[str] = []
    if args.probe_symmetric_dedup:
        probe_tags.append("symmetric-dedup")
    if args.probe_pinned_thresh:
        probe_tags.append("pinned-thresh")
    probe_tag = f"_probe-{'-'.join(probe_tags)}" if probe_tags else ""

    cache_dir = core.proj_root() / "results/trajectory_tda_integration/stage1/cache"
    cache_name = (
        f"null_diagrams_bhps_length_matched_{args.strategy}{frozen_tag}{probe_tag}_B{args.B}_L{args.L}_seed{args.seed}"
        f"{smoke_tag}_{today}.npz"
    )
    cache_path = core.write_null_diagram_cache(
        cache_dir / cache_name,
        null_results,
        ph_obs,
        {
            "B": args.B,
            "L": args.L,
            "seed": args.seed,
            "dataset": "bhps",
            "phase": phase_tag,
            "strategy": args.strategy,
            "target_years": args.target_years,
            "n_trajectories": len(sub_seqs),
            "timestamp": today,
            "smoke": args.smoke,
            "frozen_loadings": args.frozen_loadings,
        },
    )

    out_dir = core.worktree_root() / "results/trajectory_tda_bhps/stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (
        f"bhps_length_matched_{args.strategy}{frozen_tag}{probe_tag}{smoke_tag}_{today}.json"
    )
    run_params: dict[str, Any] = {
        "L": args.L,
        "B": args.B,
        "null_model": f"markov-{core.DEFAULT_MARKOV_ORDER}",
        "seed": args.seed,
        "landscape_k_max": args.k_max,
        "landscape_n_points": args.n_points,
        "n_null_pairs_cap": args.n_null_pairs,
        "pvalue_formula": "(r+1)/(B+1)",
        "frozen_loadings": args.frozen_loadings,
        "null_diagram_cache": str(cache_path),
        "strategy": args.strategy,
        "target_years": args.target_years,
        "n_trajectories_after_strategy": len(sub_seqs),
        "mean_length_after_strategy": (float(np.mean(lengths)) if lengths else 0.0),
        "length_distribution_after_strategy": length_dist,
    }
    if dedup_info is not None:
        run_params["n_perm_used_observed"] = dedup_info["observed"]["n_perm_used"]
        run_params["covering_radius_at_n_perm_observed"] = dedup_info["observed"][
            "covering_radius_at_n_perm"
        ]
        run_params["n_perm_used_null_summary"] = dedup_info["null_summary"]["n_perm_used"]
        run_params["covering_radius_at_n_perm_null_summary"] = dedup_info[
            "null_summary"
        ]["covering_radius_at_n_perm"]
        run_params["dedup_tolerance"] = dedup_info["tolerance"]
        run_params["dedup_strategy"] = dedup_info["strategy"]
        # Probe-mode provenance — present on probe runs, identifies which
        # robustness probe (if any) was active. Production runs land both
        # at False.
        run_params["probe_symmetric_dedup"] = dedup_info.get(
            "probe_symmetric_dedup", False
        )
        run_params["probe_pinned_thresh"] = dedup_info.get(
            "probe_pinned_thresh", False
        )
        run_params["pinned_thresh_value"] = dedup_info.get("pinned_thresh_value")
    payload = {
        "phase": phase_tag,
        "run_params": run_params,
        "dataset": "bhps",
        "result": out,
    }
    with open(out_path, "w") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
    print(f"BHPS length-matched ({args.strategy}) JSON: {out_path}")
    print(f"Null-diagram cache: {cache_path}")


if __name__ == "__main__":
    main()
