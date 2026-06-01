# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Build the Pre-reg #5 redo amendment comparison JSON closing the
#   length-matched dedup-amendment cycle. Compares the 2026-05-29 frozen
#   no-dedup truncate result against the 2026-05-30 frozen external-indexing
#   dedup truncate result (numerical deltas, rejection-direction preservation),
#   presents the new 2026-05-30 frozen-dedup first13 cell (no prior), and
#   records the Pre-reg #5 redo Outcome A decision summary against the
#   amendment decision rule.
"""Build the Pre-reg #5 redo amendment dedup-comparison JSON.

One-shot builder for the comparison artifact that closes Pre-reg #5 redo.
Reads the four cells (truncate × {2026-05-29 no-dedup, 2026-05-30 dedup}
and first13 × 2026-05-30 dedup), tabulates per-cell deltas, summarises
the Outcome A decision, and writes the comparison JSON to the
trajectory_tda_integration/stage1/ results directory.

Outputs:
  results/trajectory_tda_integration/stage1/
    dedup_amendment_comparison_YYYY-MM-DD.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


ALPHA = 0.05
METRIC_TO_KEY = {
    "w2": "w2_pvalue",
    "landscape_l2": "landscape_l2_pvalue",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _artifact_path(path: Path, worktree_root: Path) -> str:
    """Serialize a path relative to the worktree root for machine-stable JSON.

    Absolute worktree paths leak the local username and make regenerated
    artifacts differ by machine; storing repo-relative paths keeps the
    committed JSON reproducible. Falls back to the absolute string if the
    path is not under worktree_root.
    """
    try:
        return str(path.relative_to(worktree_root))
    except ValueError:
        return str(path)


def _pvalue(scope: dict[str, Any], dim: str, metric: str) -> float:
    return float(scope[dim][METRIC_TO_KEY[metric]])


def _reject(pvalue: float | None) -> bool | None:
    if pvalue is None:
        return None
    return bool(pvalue <= ALPHA)


def _preserved(a: bool | None, b: bool | None) -> bool | None:
    if a is None or b is None:
        return None
    return a == b


def _stage1_cell_h_summary(result: dict[str, Any], dim: str) -> dict[str, float]:
    """Extract the H_dim effect-size summary used in the comparison."""
    cell = result[dim]
    summary: dict[str, float] = {
        "w2_pvalue": float(cell["w2_pvalue"]),
        "landscape_l2_pvalue": float(cell["landscape_l2_pvalue"]),
        "t_ratio": float(cell["t_ratio"]),
        "d_perm": float(cell["d_perm"]),
        "mean_obs_null": float(cell["mean_obs_null"]),
        "mean_null_null": float(cell["mean_null_null"]),
        "landscape_t_ratio": float(cell["landscape_t_ratio"]),
        "landscape_d_perm": float(cell["landscape_d_perm"]),
    }
    return summary


def _cell_compare_row(
    analysis_id: str,
    strategy: str,
    dim: str,
    metric: str,
    worktree_root: Path,
    no_dedup_path: Path | None,
    no_dedup_result: dict[str, Any] | None,
    dedup_path: Path,
    dedup_result: dict[str, Any],
) -> dict[str, Any]:
    dedup_p = _pvalue(dedup_result, dim, metric)
    no_dedup_p = (
        _pvalue(no_dedup_result, dim, metric) if no_dedup_result is not None else None
    )
    return {
        "cell_id": f"{analysis_id}_{dim}_{metric}",
        "analysis_id": analysis_id,
        "strategy": strategy,
        "homology_dim": dim,
        "metric": metric,
        "no_dedup_pvalue": no_dedup_p,
        "no_dedup_path": (
            _artifact_path(no_dedup_path, worktree_root)
            if no_dedup_path is not None
            else None
        ),
        "dedup_pvalue": dedup_p,
        "dedup_path": _artifact_path(dedup_path, worktree_root),
        "delta_pvalue": (
            dedup_p - no_dedup_p if no_dedup_p is not None else None
        ),
        "no_dedup_reject": _reject(no_dedup_p),
        "dedup_reject": _reject(dedup_p),
        "rejection_direction_preserved": _preserved(
            _reject(no_dedup_p), _reject(dedup_p)
        ),
        "no_prior_note": (
            None
            if no_dedup_result is not None
            else "No prior frozen-loadings result for this cell; new under dedup amendment."
        ),
    }


def _dedup_provenance(result_json: dict[str, Any]) -> dict[str, Any]:
    rp = result_json["run_params"]
    return {
        "n_dedup_observed": int(rp["n_perm_used_observed"]),
        "covering_radius_at_n_dedup_observed": float(
            rp["covering_radius_at_n_perm_observed"]
        ),
        "n_dedup_null_summary": rp["n_perm_used_null_summary"],
        "covering_radius_null_summary": rp["covering_radius_at_n_perm_null_summary"],
        "dedup_tolerance": float(rp["dedup_tolerance"]),
        "dedup_strategy": rp["dedup_strategy"],
    }


def _probe_robustness_row(
    probe_id: str,
    analysis_id: str,
    production_result: dict[str, Any],
    probe_result: dict[str, Any],
    worktree_root: Path,
    production_path: Path,
    probe_path: Path,
) -> dict[str, Any]:
    """Compute a per-probe robustness comparison row vs the production result.

    Reports rejection-preservation and signal-to-noise drift, the two
    measurements the probes are designed to expose. Absolute W2 magnitudes
    are not the focus — only the (mean_obs_null / mean_null_null) ratio,
    which is the rejection-driving quantity.
    """
    h0_prod = production_result["h0"]
    h0_probe = probe_result["h0"]
    h1_prod = production_result["h1"]
    h1_probe = probe_result["h1"]

    def _rel_pct(probe_val: float, prod_val: float) -> float:
        if prod_val == 0.0:
            return 0.0
        return 100.0 * (probe_val - prod_val) / prod_val

    def _signal_to_noise(cell: dict[str, Any]) -> float:
        return float(cell["mean_obs_null"]) / float(cell["mean_null_null"])

    return {
        "probe_id": probe_id,
        "analysis_id": analysis_id,
        "production_path": _artifact_path(production_path, worktree_root),
        "probe_path": _artifact_path(probe_path, worktree_root),
        "h0": {
            "w2_pvalue_production": _pvalue(production_result, "h0", "w2"),
            "w2_pvalue_probe": _pvalue(probe_result, "h0", "w2"),
            "landscape_l2_pvalue_production": _pvalue(
                production_result, "h0", "landscape_l2"
            ),
            "landscape_l2_pvalue_probe": _pvalue(
                probe_result, "h0", "landscape_l2"
            ),
            "t_ratio_production": float(h0_prod["t_ratio"]),
            "t_ratio_probe": float(h0_probe["t_ratio"]),
            "t_ratio_relative_change_pct": _rel_pct(
                float(h0_probe["t_ratio"]), float(h0_prod["t_ratio"])
            ),
            "d_perm_production": float(h0_prod["d_perm"]),
            "d_perm_probe": float(h0_probe["d_perm"]),
            "d_perm_relative_change_pct": _rel_pct(
                float(h0_probe["d_perm"]), float(h0_prod["d_perm"])
            ),
            "signal_to_noise_production": _signal_to_noise(h0_prod),
            "signal_to_noise_probe": _signal_to_noise(h0_probe),
            "w2_rejection_preserved": _preserved(
                _reject(_pvalue(production_result, "h0", "w2")),
                _reject(_pvalue(probe_result, "h0", "w2")),
            ),
            "landscape_l2_rejection_preserved": _preserved(
                _reject(_pvalue(production_result, "h0", "landscape_l2")),
                _reject(_pvalue(probe_result, "h0", "landscape_l2")),
            ),
        },
        "h1": {
            "w2_pvalue_production": _pvalue(production_result, "h1", "w2"),
            "w2_pvalue_probe": _pvalue(probe_result, "h1", "w2"),
            "landscape_l2_pvalue_production": _pvalue(
                production_result, "h1", "landscape_l2"
            ),
            "landscape_l2_pvalue_probe": _pvalue(
                probe_result, "h1", "landscape_l2"
            ),
            "t_ratio_production": float(h1_prod["t_ratio"]),
            "t_ratio_probe": float(h1_probe["t_ratio"]),
            "t_ratio_relative_change_pct": _rel_pct(
                float(h1_probe["t_ratio"]), float(h1_prod["t_ratio"])
            ),
            "d_perm_production": float(h1_prod["d_perm"]),
            "d_perm_probe": float(h1_probe["d_perm"]),
            "d_perm_relative_change_pct": _rel_pct(
                float(h1_probe["d_perm"]), float(h1_prod["d_perm"])
            ),
            "signal_to_noise_production": _signal_to_noise(h1_prod),
            "signal_to_noise_probe": _signal_to_noise(h1_probe),
            "w2_rejection_preserved": _preserved(
                _reject(_pvalue(production_result, "h1", "w2")),
                _reject(_pvalue(probe_result, "h1", "w2")),
            ),
            "landscape_l2_rejection_preserved": _preserved(
                _reject(_pvalue(production_result, "h1", "landscape_l2")),
                _reject(_pvalue(probe_result, "h1", "landscape_l2")),
            ),
        },
    }


def build_comparison(
    worktree_root: Path, output: Path | None = None
) -> Path:
    """Build the dedup-amendment comparison JSON and return the output path.

    Args:
        worktree_root: Root of the worktree (used to locate the staged
            2026-05-30 frozen-dedup JSONs, the 2026-05-29 frozen-no-dedup
            JSON, and the two probe JSONs which sit on the branch from
            prior commits).
        output: Optional explicit output path. Defaults to
            ``<worktree>/results/trajectory_tda_integration/stage1/
            dedup_amendment_comparison_<today>.json``.

    Returns:
        Path to the written comparison JSON.
    """
    bhps_stage1 = worktree_root / "results" / "trajectory_tda_bhps" / "stage1"
    truncate_no_dedup_path = bhps_stage1 / "bhps_length_matched_truncate_frozen_2026-05-29.json"
    truncate_dedup_path = bhps_stage1 / "bhps_length_matched_truncate_frozen_2026-05-30.json"
    first13_dedup_path = bhps_stage1 / "bhps_length_matched_first13_frozen_2026-05-30.json"
    truncate_probe_symmetric_dedup_path = (
        bhps_stage1
        / "bhps_length_matched_truncate_frozen_probe-symmetric-dedup_2026-05-30.json"
    )
    truncate_probe_pinned_thresh_path = (
        bhps_stage1
        / "bhps_length_matched_truncate_frozen_probe-pinned-thresh_2026-05-31.json"
    )

    for p in (
        truncate_no_dedup_path,
        truncate_dedup_path,
        first13_dedup_path,
        truncate_probe_symmetric_dedup_path,
        truncate_probe_pinned_thresh_path,
    ):
        if not p.exists():
            raise FileNotFoundError(f"Required input JSON missing: {p}")

    truncate_no_dedup = _load_json(truncate_no_dedup_path)
    truncate_dedup = _load_json(truncate_dedup_path)
    first13_dedup = _load_json(first13_dedup_path)
    truncate_probe_symmetric_dedup = _load_json(
        truncate_probe_symmetric_dedup_path
    )
    truncate_probe_pinned_thresh = _load_json(truncate_probe_pinned_thresh_path)

    truncate_no_dedup_result = truncate_no_dedup["result"]
    truncate_dedup_result = truncate_dedup["result"]
    first13_dedup_result = first13_dedup["result"]
    truncate_probe_symmetric_dedup_result = truncate_probe_symmetric_dedup[
        "result"
    ]
    truncate_probe_pinned_thresh_result = truncate_probe_pinned_thresh["result"]

    cells: list[dict[str, Any]] = []
    for dim in ("h0", "h1"):
        for metric in ("w2", "landscape_l2"):
            cells.append(
                _cell_compare_row(
                    analysis_id="bhps_length_matched_truncate",
                    strategy="truncate",
                    dim=dim,
                    metric=metric,
                    worktree_root=worktree_root,
                    no_dedup_path=truncate_no_dedup_path,
                    no_dedup_result=truncate_no_dedup_result,
                    dedup_path=truncate_dedup_path,
                    dedup_result=truncate_dedup_result,
                )
            )
    for dim in ("h0", "h1"):
        for metric in ("w2", "landscape_l2"):
            cells.append(
                _cell_compare_row(
                    analysis_id="bhps_length_matched_first13",
                    strategy="first13",
                    dim=dim,
                    metric=metric,
                    worktree_root=worktree_root,
                    no_dedup_path=None,
                    no_dedup_result=None,
                    dedup_path=first13_dedup_path,
                    dedup_result=first13_dedup_result,
                )
            )

    h1_w2_cells = {
        row["analysis_id"]: row for row in cells
        if row["homology_dim"] == "h1" and row["metric"] == "w2"
    }
    h0_w2_cells = {
        row["analysis_id"]: row for row in cells
        if row["homology_dim"] == "h0" and row["metric"] == "w2"
    }
    truncate_h1_w2_reject = h1_w2_cells["bhps_length_matched_truncate"]["dedup_reject"]
    first13_h1_w2_reject = h1_w2_cells["bhps_length_matched_first13"]["dedup_reject"]

    if truncate_h1_w2_reject and first13_h1_w2_reject:
        outcome = "A"
        outcome_reasoning = (
            "Both length-matching strategies (truncate and first13) reject H1 W2 "
            "at alpha=0.05 under the dedup amendment methodology. The H1 "
            "topological signature survives length-matching to USoc's mean "
            "horizon (~13 waves) under both truncation and >=13-wave-only "
            "restriction; the BHPS-vs-USoc H1 signal is not a length artefact."
        )
    elif truncate_h1_w2_reject != first13_h1_w2_reject:
        outcome = "B"
        outcome_reasoning = (
            "Length-matching strategies disagree on H1 W2 rejection at "
            "alpha=0.05 under the dedup amendment methodology. Topology is "
            "strategy-dependent; investigate which strategy more faithfully "
            "isolates the length effect."
        )
    else:
        outcome = "C"
        outcome_reasoning = (
            "Neither length-matching strategy rejects H1 W2 at alpha=0.05 "
            "under the dedup amendment methodology. Length-matching kills the "
            "topology; the original BHPS-vs-USoc H1 difference reduces to a "
            "length-of-observation artefact."
        )

    probe_comparison = [
        _probe_robustness_row(
            probe_id="probe_symmetric_dedup",
            analysis_id="bhps_length_matched_truncate",
            production_result=truncate_dedup_result,
            probe_result=truncate_probe_symmetric_dedup_result,
            worktree_root=worktree_root,
            production_path=truncate_dedup_path,
            probe_path=truncate_probe_symmetric_dedup_path,
        ),
        _probe_robustness_row(
            probe_id="probe_pinned_thresh",
            analysis_id="bhps_length_matched_truncate",
            production_result=truncate_dedup_result,
            probe_result=truncate_probe_pinned_thresh_result,
            worktree_root=worktree_root,
            production_path=truncate_dedup_path,
            probe_path=truncate_probe_pinned_thresh_path,
        ),
    ]
    all_probes_preserve_rejection = all(
        row["h1"]["w2_rejection_preserved"] is True
        and row["h1"]["landscape_l2_rejection_preserved"] is True
        and row["h0"]["w2_rejection_preserved"] is True
        and row["h0"]["landscape_l2_rejection_preserved"] is True
        for row in probe_comparison
    )

    decision_summary = {
        "alpha": ALPHA,
        "outcome": outcome,
        "outcome_reasoning": outcome_reasoning,
        "h1_w2_truncate_reject": truncate_h1_w2_reject,
        "h1_w2_first13_reject": first13_h1_w2_reject,
        "h0_w2_truncate_reject": h0_w2_cells["bhps_length_matched_truncate"][
            "dedup_reject"
        ],
        "h0_w2_first13_reject": h0_w2_cells["bhps_length_matched_first13"][
            "dedup_reject"
        ],
        "rejection_direction_changes": sum(
            1 for row in cells
            if row["rejection_direction_preserved"] is False
        ),
        "n_cells_with_prior": sum(
            1 for row in cells if row["no_dedup_pvalue"] is not None
        ),
        "n_cells_no_prior": sum(
            1 for row in cells if row["no_dedup_pvalue"] is None
        ),
        "probes_completed": [row["probe_id"] for row in probe_comparison],
        "all_probes_preserve_rejection": all_probes_preserve_rejection,
    }

    effect_summaries = {
        "truncate_no_dedup": {
            "h0": _stage1_cell_h_summary(truncate_no_dedup_result, "h0"),
            "h1": _stage1_cell_h_summary(truncate_no_dedup_result, "h1"),
        },
        "truncate_dedup": {
            "h0": _stage1_cell_h_summary(truncate_dedup_result, "h0"),
            "h1": _stage1_cell_h_summary(truncate_dedup_result, "h1"),
        },
        "first13_dedup": {
            "h0": _stage1_cell_h_summary(first13_dedup_result, "h0"),
            "h1": _stage1_cell_h_summary(first13_dedup_result, "h1"),
        },
    }

    dedup_provenance = {
        "truncate": _dedup_provenance(truncate_dedup),
        "first13": _dedup_provenance(first13_dedup),
        "asymmetry_note": (
            "Truncate nulls all fell through to no-dedup (n_dedup=L=5000, "
            "max covering radius 0.0): Markov-1 surrogates of BHPS truncate "
            "trajectories do not produce the near-duplicate landmark "
            "clusters that observed BHPS truncate does (~139 near-duplicates "
            "in the observed sample). The obs/null vertex-count asymmetry "
            "(obs=4861 vs nulls=5000) is a TRUE DATA PROPERTY, not an "
            "artefact: it is the same property that makes the dedup "
            "amendment necessary in the first place. First13 nulls did "
            "dedup (n_dedup nulls 3766-3980); the surrogate trajectories "
            "there preserve enough first-13-wave structure to retain some "
            "near-duplicate landmarks under maxmin."
        ),
    }

    _probe_by_id = {row["probe_id"]: row for row in probe_comparison}
    _sym = _probe_by_id["probe_symmetric_dedup"]
    _pin = _probe_by_id["probe_pinned_thresh"]
    _sym_h0_drift = _sym["h0"]["t_ratio_relative_change_pct"]
    _sym_h1_drift = _sym["h1"]["t_ratio_relative_change_pct"]
    _pin_h0_drift = _pin["h0"]["t_ratio_relative_change_pct"]
    _pin_h1_drift = _pin["h1"]["t_ratio_relative_change_pct"]

    methodological_disclosure = (
        "The Pre-reg #5 redo amendment locked external-indexing dedup of "
        "the observed maxmin landmark sample for length-matched cells "
        "(formula contract length-matched-dedup-via-n-perm at vault "
        "[DECISION] 2026-05-30). Compared to the 2026-05-29 frozen-loadings "
        "result for truncate (no dedup), the 2026-05-30 frozen-loadings "
        "dedup result preserves H0 rejection direction and the H1 landscape "
        "L2 rejection direction; the H1 W2 statistic flipped from "
        f"p={cells[2]['no_dedup_pvalue']:.6f} (non-reject) to "
        f"p={cells[2]['dedup_pvalue']:.6f} (reject). The flip is mechanistic, "
        "not a tuning: the 2026-05-29 observed PD contained ~139 phantom "
        "H1 features at near-zero filtration scales contributed by "
        "numerical near-duplicates in the embedding (within the locked "
        "tolerance tau_float = 1e-10); those phantoms inflated the W2 "
        "statistic by a ~30-200x constant on both observed-to-null and "
        "null-to-null pairings, making observed look statistically "
        "indistinguishable from a null (mean_obs_null / mean_null_null = "
        "1.006 in 2026-05-29). External dedup of observed (which Markov-1 "
        "surrogates do not need because they do not reproduce the "
        "near-duplicate structure) strips the phantoms and reveals the "
        "underlying signal (mean_obs_null / mean_null_null = 1.87 in "
        f"2026-05-30). Both length-matching strategies reject H1 W2 at "
        "alpha=0.05, locking Outcome A. Two robustness probes were run "
        "and both preserve the rejection direction in all four cells "
        "(H0/H1 x W2/landscape L2): "
        "(a) probe_symmetric_dedup forces nulls to use n_perm = "
        "obs_n_dedup (eliminating the observed-vs-null vertex-count "
        "asymmetry); the signal-to-noise (mean_obs_null/mean_null_null) "
        f"drift is {_sym_h0_drift:+.1f}% (H0), {_sym_h1_drift:+.1f}% (H1). "
        "(b) probe_pinned_thresh fixes the ripser threshold to "
        "the enclosing radius of the observed post-dedup landmark sample "
        "(eliminating the compute_rips_ph auto-threshold subsample "
        f"drift); the signal-to-noise drift is {_pin_h0_drift:+.1f}% (H0), "
        f"{_pin_h1_drift:+.1f}% (H1). The larger H0 shift reflects "
        "additional features captured under the wider fixed threshold; the "
        "H0 cell nonetheless stays far inside the rejection region (W2 p at "
        "the Monte-Carlo floor) and the contested H1 cell is essentially "
        "unchanged. The Outcome A conclusion rests on the dedup "
        "methodology, not on either of the incidental implementation "
        "choices the probes test."
    )

    payload: dict[str, Any] = {
        "schema_version": "dedup-amendment-comparison/v2",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "task": (
            "Pre-reg #5 redo amendment dedup-path comparison with "
            "robustness probes (length-matched cells)"
        ),
        "inputs": {
            "truncate_no_dedup_frozen": _artifact_path(
                truncate_no_dedup_path, worktree_root
            ),
            "truncate_dedup_frozen": _artifact_path(
                truncate_dedup_path, worktree_root
            ),
            "first13_dedup_frozen": _artifact_path(
                first13_dedup_path, worktree_root
            ),
            "truncate_probe_symmetric_dedup_frozen": _artifact_path(
                truncate_probe_symmetric_dedup_path, worktree_root
            ),
            "truncate_probe_pinned_thresh_frozen": _artifact_path(
                truncate_probe_pinned_thresh_path, worktree_root
            ),
        },
        "cells": cells,
        "effect_summaries": effect_summaries,
        "dedup_provenance": dedup_provenance,
        "probe_comparison": probe_comparison,
        "decision_summary": decision_summary,
        "methodological_disclosure_draft": methodological_disclosure,
    }

    out_root = worktree_root / "results" / "trajectory_tda_integration" / "stage1"
    out_path = output or out_root / (
        f"dedup_amendment_comparison_{date.today().isoformat()}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Pre-reg #5 redo dedup-amendment comparison JSON"
    )
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=Path.cwd(),
        help=(
            "Root of the worktree containing the three input JSONs; "
            "defaults to current working directory."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Explicit output path (default: <worktree>/results/.../dedup_amendment_comparison_<today>.json).",
    )
    args = parser.parse_args()
    out_path = build_comparison(args.worktree_root, output=args.output)
    print(f"Dedup-amendment comparison JSON: {out_path}")


if __name__ == "__main__":
    main()
