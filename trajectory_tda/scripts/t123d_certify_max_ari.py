# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: T1.23d -- certify the maximum-achievable ARI for the reviewer-B9
#          OM-vs-GMM normalisation and recompute the normalised ARI. Reads the
#          accepted T1.23c result (ari_om_gmm_normalised_2026-06-23.json), reuses
#          its observed ARI, permutation null, and bootstrap CI VERBATIM, and
#          replaces only the defective max_achievable_ari block (the trivial 1.0)
#          with a certified fixed-margin maximum (achievable bracket).
"""Recompute the B9 OM-vs-GMM normalised ARI with a certified maximum.

The T1.23c result left ``max_achievable_ari`` at the trivial ``1.0`` because the
greedy whole-cluster-packing fallback returned an all-zero table once the largest
OM cluster (9,003) exceeded every GMM column capacity, making the normalised ARI
vacuous. This script computes the real maximum of ``Sum C(n_ij, 2)`` over the
fixed OM/GMM k=7 margins via :mod:`fixed_margin_max_ari` and writes a new
date-suffixed result that carries the observed/null/bootstrap blocks over unchanged.

Run from the task worktree root::

    uv run --env-file .env python -m trajectory_tda.scripts.t123d_certify_max_ari
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from trajectory_tda.analysis.panel.fixed_margin_max_ari import certify_max_ari
from trajectory_tda.analysis.panel.t123b_ari_om_gmm import (
    CANARY_OBSERVED_ARI,
    CANARY_TOL,
    EXPECTED_N,
    GMM_K,
    OM_K,
    build_max_achievable_block,
    git_head_sha,
    validate_ari_om_gmm_output,
    write_json_no_overwrite,
)

WORKTREE = Path.cwd()

DEFAULT_ARI_DIR = WORKTREE / "results/panel_methodology/ari"
DEFAULT_SOURCE = DEFAULT_ARI_DIR / "ari_om_gmm_normalised_2026-06-23.json"
DEFAULT_DATE = "2026-06-24"


def _counts_from_mapping(mapping: dict[str, int], k: int) -> np.ndarray:
    """Return a length-k int array from a ``{"0": n0, ...}`` size mapping."""

    counts = np.array([int(mapping[str(i)]) for i in range(k)], dtype=np.int64)
    if int(counts.sum()) != EXPECTED_N:
        raise ValueError(f"cluster sizes sum to {int(counts.sum())} != {EXPECTED_N}")
    return counts


def build_certified_payload(source: dict[str, Any], created_at: str) -> dict[str, Any]:
    """Build the T1.23d payload from the accepted T1.23c result.

    Observed ARI, the permutation null, and the bootstrap CI are carried over
    verbatim; only ``max_achievable_ari`` and the derived normalisation change.
    """

    observed = float(source["observed_ari"])
    if abs(observed - CANARY_OBSERVED_ARI) > CANARY_TOL:
        raise ValueError(f"source observed_ari {observed} does not reproduce {CANARY_OBSERVED_ARI}")

    row_counts = _counts_from_mapping(source["label_counts"]["om_cluster_counts"], OM_K)
    col_counts = _counts_from_mapping(source["label_counts"]["gmm_regime_counts"], GMM_K)

    started = time.perf_counter()
    cert = certify_max_ari(row_counts, col_counts, observed)
    certify_seconds = time.perf_counter() - started
    boot_ci_95 = source["bootstrap_ci"]["percentile_95"]
    max_block = build_max_achievable_block(cert, boot_ci_95)

    interpretation = dict(source["interpretation"])
    interpretation["normalisation_basis"] = cert.status

    payload: dict[str, Any] = {
        "schema_version": source["schema_version"],
        "created_at": created_at,
        "git_head": git_head_sha(),
        "referent": source["referent"],
        "input_paths": source["input_paths"],
        "representation": source["representation"],
        "parameters": source["parameters"],
        "label_counts": source["label_counts"],
        "observed_ari": observed,
        "null_distribution": source["null_distribution"],
        "max_achievable_ari": max_block,
        "bootstrap_ci": source["bootstrap_ci"],
        "interpretation": interpretation,
        "supersedes": {
            "file": "results/panel_methodology/ari/ari_om_gmm_normalised_2026-06-23.json",
            "block": "max_achievable_ari and the derived normalisation only",
            "reason": (
                "The 2026-06-23 max_achievable_ari was the trivial 1.0: the greedy "
                "whole-cluster-packing construction fell back to an all-zero table "
                "when the largest OM cluster (9,003) exceeded every GMM column "
                "capacity (max 7,358), so the normalised ARI equalled the observed "
                "ARI and was vacuous. T1.23d certifies the real fixed-margin maximum."
            ),
            "carried_over_verbatim": [
                "observed_ari",
                "null_distribution",
                "bootstrap_ci",
            ],
        },
        "runtime": {
            "wall_seconds": float(certify_seconds),
            "note": (
                "Certification compute only; the observed ARI, permutation null, and "
                "bootstrap CI were inherited from the 2026-06-23 result, not recomputed."
            ),
        },
    }
    validate_ari_om_gmm_output(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_ARI_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.source.open("r", encoding="utf-8") as handle:
        source = json.load(handle)
    out_path = args.out_dir / f"ari_om_gmm_normalised_{args.date}.json"
    print("=== T1.23d: certify maximum-achievable ARI (OM k=7 vs GMM k=7) ===")
    print(f"Source: {args.source}")
    print(f"Output: {out_path}")
    payload = build_certified_payload(source, created_at=args.date)
    write_json_no_overwrite(out_path, payload)
    block = payload["max_achievable_ari"]
    print(
        json.dumps(
            {
                "observed_ari": payload["observed_ari"],
                "status": block["status"],
                "ari_max_achievable": block["value"],
                "ari_max_upper_bound": block["rigorous_upper_bound"]["ari"],
                "normalised_observed_ari": block["normalised_observed_ari"],
                "normalised_ari_bracket": block["normalised_ari_bracket"],
                "normalised_ci_percentile_95": block["normalised_ci_percentile_95"],
            },
            indent=2,
        )
    )
    print("=== complete ===")


if __name__ == "__main__":
    main()
