# Research context: contracts/stage1-output-schemas
# Purpose: Binding tests for T1.37 denominator-cleanup and comparison JSON artifacts.
"""Contract bindings for Stage-1 cleanup and comparison outputs."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _required_root_keys(schema_rel_path: str) -> list[str]:
    contract = _load_contract(schema_rel_path)
    return [entry["name"] for entry in contract["schema_def"]["required_keys"]]


def _matched_jsons(glob_pattern: str) -> list[Path]:
    matched: list[Path] = []
    for path in REPO_ROOT.rglob("*.json"):
        rel = path.relative_to(REPO_ROOT)
        if rel.full_match(glob_pattern):
            matched.append(path)
    return matched


def _dispatch_filter(file_dispatch: list[dict] | None, json_path: Path) -> bool:
    if not file_dispatch:
        return True
    return any(Path(json_path.name).match(entry["filename_pattern"]) for entry in file_dispatch)


def _assert_has_keys(scope: dict, keys: list[str], label: str) -> None:
    missing = [key for key in keys if key not in scope]
    assert not missing, f"{label} missing required keys: {missing}"


def _cleanup_row() -> dict:
    return {
        "cell_id": "usoc_headline_h0_w2",
        "analysis_id": "usoc_headline",
        "dataset": "usoc",
        "homology_dim": "h0",
        "metric": "w2",
        "old_reported_pvalue": 0.001996007984031936,
        "corrected_pvalue": 0.000999000999000999,
        "old_denominator": 501,
        "corrected_denominator": 1001,
        "old_pvalue_floor": 0.001996007984031936,
        "corrected_pvalue_floor": 0.000999000999000999,
        "rank_count": 0,
        "B": 1000,
        "source_cache_path": "results/trajectory_tda_integration/stage1/cache/null_diagrams_usoc.npz",
        "source_result_path": "results/trajectory_tda_integration/stage1/usoc_headline_2026-05-24.json",
    }


def _representative_cleanup() -> dict:
    return {
        "schema_version": "stage1-pvalue-denominator-cleanup/v1",
        "generated_at": "2026-05-28T00:00:00",
        "formula": "(r + 1) / (B + 1)",
        "source_caches": {
            "usoc_headline": {
                "path": "results/trajectory_tda_integration/stage1/cache/null_diagrams_usoc.npz",
                "size": 1,
                "mtime": "2026-05-24T02:19:06",
            }
        },
        "source_results": {
            "usoc_headline": "results/trajectory_tda_integration/stage1/usoc_headline_2026-05-24.json"
        },
        "cells": [_cleanup_row()],
        "unrecoverable_cells": [{"cell_id": "lm_L2500_h0_w2", "reason": "final JSON lacks aggregate fields"}],
        "summary": {
            "n_recomputed": 1,
            "n_unrecoverable": 1,
            "rejection_direction_changes": 0,
        },
    }


def _assert_cleanup_contract(data: dict) -> None:
    _assert_has_keys(
        data,
        _required_root_keys("stage1-output-schemas/stage1-pvalue-denominator-cleanup.yaml"),
        "denominator cleanup root",
    )
    row_keys = [
        "cell_id",
        "analysis_id",
        "dataset",
        "homology_dim",
        "metric",
        "old_reported_pvalue",
        "corrected_pvalue",
        "old_denominator",
        "corrected_denominator",
        "old_pvalue_floor",
        "corrected_pvalue_floor",
        "rank_count",
        "B",
        "source_cache_path",
        "source_result_path",
    ]
    for idx, row in enumerate(data["cells"]):
        _assert_has_keys(row, row_keys, f"denominator cleanup cells[{idx}]")
    for idx, row in enumerate(data["unrecoverable_cells"]):
        _assert_has_keys(row, ["cell_id", "reason"], f"denominator cleanup unrecoverable_cells[{idx}]")


def _comparison_row() -> dict:
    return {
        "cell_id": "usoc_headline_h0_w2",
        "analysis_id": "usoc_headline",
        "dataset": "usoc",
        "homology_dim": "h0",
        "metric": "w2",
        "provisional_pvalue": 0.001996007984031936,
        "cache_denominator_corrected_pvalue": 0.000999000999000999,
        "frozen_post_fix_pvalue": 0.000999000999000999,
        "provisional_to_cache_delta_pvalue": -0.000997006985030937,
        "cache_to_frozen_delta_pvalue": 0.0,
        "provisional_reject": True,
        "cache_corrected_reject": True,
        "frozen_post_fix_reject": True,
        "rejection_direction_preserved": True,
        "provisional_result_path": "results/trajectory_tda_integration/stage1/usoc_headline_2026-05-24.json",
        "denominator_cleanup_source_path": "results/trajectory_tda_integration/stage1/pvalue_denominator_cleanup_2026-05-28.json",
        "frozen_post_fix_result_path": "results/trajectory_tda_integration/stage1/usoc_headline_frozen_2026-05-28.json",
    }


def _representative_comparison() -> dict:
    return {
        "schema_version": "frozen-vs-provisional-comparison/v1",
        "generated_at": "2026-05-28T00:00:00",
        "task": "T1.37 frozen-loadings rerun and denominator cleanup",
        "inputs": {
            "provisional_results": [],
            "denominator_cleanup": "results/trajectory_tda_integration/stage1/pvalue_denominator_cleanup_2026-05-28.json",
            "frozen_results": [],
        },
        "denominator_cleanup": {
            "formula": "(r + 1) / (B + 1)",
            "cells_recomputed": 1,
            "unrecoverable_cells": 0,
        },
        "cells": [_comparison_row()],
        "decision_summary": {
            "t1_2h_prose_direction": "survives",
            "t1_3_outcome_a": "survives",
        },
        "methodological_disclosure_draft": "The denominator cleanup and frozen-loadings rerun preserve the headline decision direction.",
    }


def _assert_comparison_contract(data: dict) -> None:
    _assert_has_keys(
        data,
        _required_root_keys("stage1-output-schemas/frozen-vs-provisional-comparison-table.yaml"),
        "comparison root",
    )
    row_keys = [
        "cell_id",
        "analysis_id",
        "dataset",
        "homology_dim",
        "metric",
        "provisional_pvalue",
        "cache_denominator_corrected_pvalue",
        "frozen_post_fix_pvalue",
        "provisional_to_cache_delta_pvalue",
        "cache_to_frozen_delta_pvalue",
        "provisional_reject",
        "cache_corrected_reject",
        "frozen_post_fix_reject",
        "rejection_direction_preserved",
        "provisional_result_path",
        "denominator_cleanup_source_path",
        "frozen_post_fix_result_path",
    ]
    for idx, row in enumerate(data["cells"]):
        _assert_has_keys(row, row_keys, f"comparison cells[{idx}]")
    assert "denominator_cleanup" in data
    assert "t1_2h_prose_direction" in data["decision_summary"]
    assert "t1_3_outcome_a" in data["decision_summary"]


def test_stage1_pvalue_denominator_cleanup_schema_contract() -> None:
    """Representative denominator-cleanup output satisfies the schema contract."""
    _assert_cleanup_contract(_representative_cleanup())


def test_stage1_pvalue_denominator_cleanup_json_validation_contract() -> None:
    """Validate every on-disk denominator-cleanup JSON, if any exist."""
    output_validation = _load_contract("stage1-output-schemas/stage1-pvalue-denominator-cleanup-json-validation.yaml")
    ov = output_validation["output_validation"]
    jsons = _matched_jsons(ov["applies_to_glob"])
    jsons = [path for path in jsons if _dispatch_filter(ov.get("file_dispatch"), path)]
    for json_path in jsons:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_cleanup_contract(data)


def test_frozen_vs_provisional_comparison_schema_contract() -> None:
    """Representative frozen-vs-provisional comparison output satisfies the schema contract."""
    _assert_comparison_contract(_representative_comparison())


def test_frozen_vs_provisional_comparison_json_validation_contract() -> None:
    """Validate every on-disk frozen-vs-provisional comparison JSON, if any exist."""
    output_validation = _load_contract("stage1-output-schemas/frozen-vs-provisional-comparison-json-validation.yaml")
    ov = output_validation["output_validation"]
    jsons = _matched_jsons(ov["applies_to_glob"])
    jsons = [path for path in jsons if _dispatch_filter(ov.get("file_dispatch"), path)]
    for json_path in jsons:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_comparison_contract(data)
