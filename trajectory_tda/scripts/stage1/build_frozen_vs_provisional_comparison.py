# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Build the T1.37 frozen-vs-provisional comparison bridge after the
#   frozen Stage-1 reruns and stratified Markov-1 rerun have completed.
"""Build the T1.37 frozen-vs-provisional comparison JSON."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJ_ROOT = Path("C:/Users/steph/TDL")
ALPHA = 0.05
METRIC_TO_KEY = {
    "w2": "w2_pvalue",
    "landscape_l2": "landscape_l2_pvalue",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _latest(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No files match {root / pattern}")
    return matches[0]


def _stage1_scope(data: dict[str, Any]) -> dict[str, Any]:
    result = data["result"]
    if {"h0", "h1"} <= set(result):
        return result
    if len(result) == 1:
        nested = next(iter(result.values()))
        if isinstance(nested, dict) and {"h0", "h1"} <= set(nested):
            return nested
    raise ValueError("Stage-1 result does not expose h0/h1 cells")


def _pvalue(scope: dict[str, Any], dim: str, metric: str) -> float:
    return float(scope[dim][METRIC_TO_KEY[metric]])


def _reject(pvalue: float | None) -> bool | None:
    if pvalue is None:
        return None
    return bool(pvalue <= ALPHA)


def _preserved(*decisions: bool | None) -> bool:
    observed = [d for d in decisions if d is not None]
    return len(set(observed)) <= 1


def _cell_id(analysis_id: str, dim: str, metric: str) -> str:
    return f"{analysis_id}_{dim}_{metric}"


def _cleanup_maps(cleanup: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = {row["cell_id"]: row for row in cleanup.get("cells", [])}
    unrecoverable = {row["cell_id"]: row for row in cleanup.get("unrecoverable_cells", [])}
    return rows, unrecoverable


def _stage1_rows(
    analysis_id: str,
    dataset: str,
    provisional_path: Path,
    frozen_path: Path,
    cleanup_path: Path,
    cleanup_rows: dict[str, dict[str, Any]],
    cleanup_unrecoverable: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    provisional = _stage1_scope(_load_json(provisional_path))
    frozen = _stage1_scope(_load_json(frozen_path))
    rows: list[dict[str, Any]] = []
    for dim in ("h0", "h1"):
        for metric in ("w2", "landscape_l2"):
            cid = _cell_id(analysis_id, dim, metric)
            provisional_p = _pvalue(provisional, dim, metric)
            frozen_p = _pvalue(frozen, dim, metric)
            cleanup_row = cleanup_rows.get(cid)
            cache_p = float(cleanup_row["corrected_pvalue"]) if cleanup_row else None
            provisional_reject = _reject(provisional_p)
            cache_reject = _reject(cache_p)
            frozen_reject = _reject(frozen_p)
            rows.append(
                {
                    "cell_id": cid,
                    "analysis_id": analysis_id,
                    "dataset": dataset,
                    "homology_dim": dim,
                    "metric": metric,
                    "provisional_pvalue": provisional_p,
                    "cache_denominator_corrected_pvalue": cache_p,
                    "frozen_post_fix_pvalue": frozen_p,
                    "provisional_to_cache_delta_pvalue": (
                        cache_p - provisional_p if cache_p is not None else None
                    ),
                    "cache_to_frozen_delta_pvalue": frozen_p - cache_p if cache_p is not None else None,
                    "provisional_reject": provisional_reject,
                    "cache_corrected_reject": cache_reject,
                    "frozen_post_fix_reject": frozen_reject,
                    "rejection_direction_preserved": _preserved(
                        provisional_reject,
                        cache_reject,
                        frozen_reject,
                    ),
                    "provisional_result_path": str(provisional_path),
                    "denominator_cleanup_source_path": str(cleanup_path),
                    "frozen_post_fix_result_path": str(frozen_path),
                    "cache_recoverable": cleanup_row is not None,
                    "unrecoverable_reason": cleanup_unrecoverable.get(cid, {}).get("reason"),
                }
            )
    return rows


def _stratified_rows(
    provisional_path: Path,
    frozen_path: Path,
    cleanup_path: Path,
) -> list[dict[str, Any]]:
    provisional = _load_json(provisional_path)
    frozen = _load_json(frozen_path)
    rows: list[dict[str, Any]] = []
    for test_id in sorted(frozen.get("fdr_tests", {})):
        frozen_test = frozen["fdr_tests"][test_id]
        provisional_test = provisional.get("fdr_tests", {}).get(test_id)
        if provisional_test is None:
            continue
        dataset, regime, dim = test_id.split("_", 2)
        provisional_p = float(provisional_test["raw_pvalue"])
        frozen_p = float(frozen_test["raw_pvalue"])
        provisional_reject = bool(provisional_test["rejected"])
        frozen_reject = bool(frozen_test["rejected"])
        rows.append(
            {
                "cell_id": f"stratified_markov1_{test_id}_w2",
                "analysis_id": "stratified_markov1",
                "dataset": dataset,
                "regime": regime,
                "homology_dim": dim,
                "metric": "w2",
                "provisional_pvalue": provisional_p,
                "cache_denominator_corrected_pvalue": None,
                "frozen_post_fix_pvalue": frozen_p,
                "provisional_to_cache_delta_pvalue": None,
                "cache_to_frozen_delta_pvalue": None,
                "provisional_reject": provisional_reject,
                "cache_corrected_reject": None,
                "frozen_post_fix_reject": frozen_reject,
                "rejection_direction_preserved": _preserved(provisional_reject, frozen_reject),
                "provisional_result_path": str(provisional_path),
                "denominator_cleanup_source_path": str(cleanup_path),
                "frozen_post_fix_result_path": str(frozen_path),
                "cache_recoverable": False,
                "unrecoverable_reason": "No preserved stratified null-diagram cache; T1.3 comparison uses provisional vs fresh frozen FDR rows.",
                "rejection_basis": "joint BH-FDR over stratified W2 tests",
            }
        )
    return rows


def _decision_summary(rows: list[dict[str, Any]], frozen_stratified: dict[str, Any]) -> dict[str, Any]:
    stage1_rows = [row for row in rows if row["analysis_id"] != "stratified_markov1"]
    central_rows = [
        row
        for row in stage1_rows
        if row["analysis_id"]
        in {
            "usoc_headline",
            "bhps_headline",
            "lm_sensitivity_L2500",
            "lm_sensitivity_L8000",
            "bhps_length_matched_truncate",
        }
    ]
    frozen_support = all(row["frozen_post_fix_reject"] is True for row in central_rows)
    outcome = frozen_stratified["outcome"]
    return {
        "alpha": ALPHA,
        "t1_2h_prose_direction": "survives" if frozen_support else "needs_revision",
        "t1_2h_basis": (
            "All fresh frozen-loadings Stage-1 headline, LM-sensitivity, and length-matched cells reject at alpha=0.05."
            if frozen_support
            else "At least one fresh frozen-loadings Stage-1 comparison cell does not reject at alpha=0.05."
        ),
        "t1_3_outcome_a": "survives" if outcome == "A" else "needs_revision",
        "t1_3_frozen_outcome": outcome,
        "rejection_direction_changes": sum(1 for row in rows if not row["rejection_direction_preserved"]),
        "n_cells": len(rows),
    }


def build_comparison(worktree_root: Path, output: Path | None = None) -> Path:
    stage1_root = worktree_root / "results/trajectory_tda_integration/stage1"
    bhps_stage1_root = worktree_root / "results/trajectory_tda_bhps/stage1"
    stratified_root = worktree_root / "results/trajectory_tda_integration/stratified_markov"

    cleanup_path = _latest(stage1_root, "pvalue_denominator_cleanup_*.json")
    cleanup = _load_json(cleanup_path)
    cleanup_rows, cleanup_unrecoverable = _cleanup_maps(cleanup)

    analyses = [
        (
            "usoc_headline",
            "usoc",
            PROJ_ROOT / "results/trajectory_tda_integration/stage1/usoc_headline_2026-05-24.json",
            _latest(stage1_root, "usoc_headline_frozen_*.json"),
        ),
        (
            "bhps_headline",
            "bhps",
            PROJ_ROOT / "results/trajectory_tda_integration/stage1/bhps_headline_2026-05-24.json",
            _latest(bhps_stage1_root, "bhps_headline_frozen_*.json"),
        ),
        (
            "lm_sensitivity_L2500",
            "usoc",
            PROJ_ROOT / "results/trajectory_tda_integration/stage1/lm_sensitivity_L2500_2026-05-24.json",
            _latest(stage1_root, "lm_sensitivity_L2500_frozen_*.json"),
        ),
        (
            "lm_sensitivity_L8000",
            "usoc",
            PROJ_ROOT / "results/trajectory_tda_integration/stage1/lm_sensitivity_L8000_2026-05-25.json",
            _latest(stage1_root, "lm_sensitivity_L8000_frozen_*.json"),
        ),
        (
            "bhps_length_matched_truncate",
            "bhps",
            PROJ_ROOT / "results/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_2026-05-25.json",
            _latest(bhps_stage1_root, "bhps_length_matched_truncate_frozen_*.json"),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for analysis_id, dataset, provisional_path, frozen_path in analyses:
        rows.extend(
            _stage1_rows(
                analysis_id,
                dataset,
                provisional_path,
                frozen_path,
                cleanup_path,
                cleanup_rows,
                cleanup_unrecoverable,
            )
        )

    provisional_stratified = PROJ_ROOT / "results/trajectory_tda_integration/stage1/stratified_markov1_battery_2026-05-13.json"
    frozen_stratified_path = _latest(stratified_root, "stratified_markov1_W2_L5000_frozen_*.json")
    frozen_stratified = _load_json(frozen_stratified_path)
    rows.extend(_stratified_rows(provisional_stratified, frozen_stratified_path, cleanup_path))

    decision_summary = _decision_summary(rows, frozen_stratified)
    disclosure = (
        "The audit separated two issues: the p-value denominator in the Stage-1 reporting path and "
        "the PCA/scaler loadings used inside Markov-null embeddings. Preserved pre-fix null-diagram "
        "caches were re-evaluated under (r+1)/(B+1), and the affected analyses were then rerun with "
        "frozen observed loadings for the Markov null. The corrected and frozen rerun layers preserve "
        f"the T1.2h prose direction ({decision_summary['t1_2h_prose_direction']}) and the T1.3 "
        f"Outcome A decision ({decision_summary['t1_3_outcome_a']})."
    )
    payload = {
        "schema_version": "frozen-vs-provisional-comparison/v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "task": "T1.37 frozen-loadings rerun and denominator cleanup",
        "inputs": {
            "provisional_results": [str(item[2]) for item in analyses] + [str(provisional_stratified)],
            "denominator_cleanup": str(cleanup_path),
            "frozen_results": [str(item[3]) for item in analyses] + [str(frozen_stratified_path)],
        },
        "denominator_cleanup": {
            "formula": cleanup["formula"],
            "cells_recomputed": cleanup["summary"]["n_recomputed"],
            "unrecoverable_cells": cleanup["summary"]["n_unrecoverable"],
            "rejection_direction_changes": cleanup["summary"]["rejection_direction_changes"],
            "source_caches": cleanup["source_caches"],
        },
        "cells": rows,
        "unrecoverable_cells": cleanup.get("unrecoverable_cells", []),
        "decision_summary": decision_summary,
        "methodological_disclosure_draft": disclosure,
    }
    out_path = output or stage1_root / f"frozen_vs_provisional_comparison_{date.today().isoformat()}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build T1.37 frozen-vs-provisional comparison JSON")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    out_path = build_comparison(Path.cwd(), output=args.output)
    print(f"Frozen-vs-provisional comparison JSON: {out_path}")


if __name__ == "__main__":
    main()
