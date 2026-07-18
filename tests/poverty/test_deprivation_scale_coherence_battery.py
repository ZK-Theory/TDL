"""Deterministic tests for the deprivation scale-coherence battery driver."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from poverty_tda.scripts import run_deprivation_scale_coherence as driver
from poverty_tda.scripts.run_deprivation_scale_coherence import (
    PreparedLad,
    _peak_rss_mb,
    build_staged_launch_plan,
    enumerate_eligible_lads,
    load_staged_batch_rows,
    prepare_staged_batch_artifact,
    run_resource_preflight,
    run_lad_battery,
)


def test_enumerate_eligible_lads_freezes_all_and_only_lads_at_floor() -> None:
    frame = pd.DataFrame(
        {
            "Local Authority District code (2024)": ["E2"] * 151 + ["E1"] * 150 + ["E3"] * 149,
            "Local Authority District name (2024)": ["Two"] * 151 + ["One"] * 150 + ["Three"] * 149,
        }
    )

    family = enumerate_eligible_lads(frame)

    assert family == [
        {"lad_code": "E1", "lad_name": "One", "n_lsoas": 150},
        {"lad_code": "E2", "lad_name": "Two", "n_lsoas": 151},
    ]


def test_run_lad_battery_records_draws_in_seed_order_and_checkpoints(tmp_path) -> None:
    rng = np.random.default_rng(123)
    raw = rng.normal(size=(20, 7))
    closed = [np.array([(index - 1) % 20, index, (index + 1) % 20], dtype=np.intp) for index in range(20)]
    lad = PreparedLad("E1", "One", raw, closed, n_islands=0)

    result = run_lad_battery(lad, n_draws=3, checkpoint_dir=tmp_path, checkpoint_interval=2)

    assert len(result["null_h1_total_area"]) == 3
    assert result["draw_seeds"] == [42, 43, 44]
    assert 0.25 <= result["p_lower"] <= 1.0
    assert result["runtime"]["completed_draws"] == 3
    assert (tmp_path / "deprivation_scale_coherence_E1.npz").exists()


def test_peak_rss_instrumentation_is_available_on_windows() -> None:
    peak_rss_mb = _peak_rss_mb()

    assert peak_rss_mb is not None
    assert peak_rss_mb > 0


def test_resource_stop_persists_preflight_before_raising(tmp_path) -> None:
    partial = tmp_path / "partial"
    benchmark = partial / "benchmark"
    benchmark.mkdir(parents=True)
    (benchmark / "benchmark_record.json").write_text(
        json.dumps(
            {
                "lad_code": "E1",
                "lad_name": "One",
                "n_lsoas": 200,
                "B": 999,
                "wall_seconds": 50_000.0,
                "peak_rss_mb": 200.0,
                "production_entry_point": "run_lad_battery",
            }
        ),
        encoding="utf-8",
    )
    sweep = [
        {"workers": 1, "wall_seconds": 100.0, "lad_count": 1, "draws_per_lad": 25},
        {"workers": 8, "wall_seconds": 100.0, "lad_count": 1, "draws_per_lad": 25},
    ]
    (partial / "worker_sweep.json").write_text(json.dumps({"records": sweep}), encoding="utf-8")
    lad = PreparedLad("E1", "One", np.zeros((1, 7)), [np.array([0])], n_islands=1)
    output = tmp_path / "resource_preflight.json"

    with pytest.raises(RuntimeError, match="projected family launch"):
        run_resource_preflight([lad], workers=8, partial_root=partial, output_path=output)

    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["decision"]["status"] == "STOP"
    assert persisted["decision"]["launch_authorized"] is False


def test_staged_plan_is_deterministic_balanced_and_exact() -> None:
    members = [{"lad_code": f"E{index:02d}", "lad_name": f"LAD {index}", "n_lsoas": 300 - index} for index in range(69)]
    frozen = {"eligible_count": 69, "members": members, "family_sha256": "frozen-sha"}
    preflight = {"estimated_wall_time_hours": 16.5, "decision": {"status": "STOP"}}

    first = build_staged_launch_plan(frozen, preflight, approved_at="2026-07-16T12:00:00+00:00")
    second = build_staged_launch_plan(frozen, preflight, approved_at="2026-07-16T12:00:00+00:00")

    assert first == second
    assert [batch["member_count"] for batch in first["batches"]] == [23, 23, 23]
    assigned = [member["lad_code"] for batch in first["batches"] for member in batch["members"]]
    assert sorted(assigned) == sorted(member["lad_code"] for member in members)
    assert len(set(assigned)) == 69
    assert first["batches"][0]["members"][0]["lad_code"] == "E00"
    costs = [batch["lsoa_count"] for batch in first["batches"]]
    assert max(costs) - min(costs) <= 2
    assert first["inference_deferred_until_all_batches_complete"] is True


def test_staged_batch_artifact_omits_all_family_inference() -> None:
    row = {
        "lad_code": "E1",
        "lad_name": "One",
        "n_lsoas": 150,
        "null_h1_total_area": [1.0] * 999,
        "null_summary": {"mean": 1.5, "standard_deviation": 0.5, "observed_percentile": 50.0},
        "draw_seeds": list(range(42, 1041)),
        "p_lower": 0.5,
        "p_upper": 1.0,
        "p_fdr": 0.5,
        "rejects_lower_fdr": False,
    }
    plan = {
        "family_sha256": "frozen-sha",
        "batch_count": 3,
        "locked_compute_contract": {"B": 999, "workers": 8},
        "batches": [
            {
                "batch_index": 1,
                "members": [{"lad_code": "E1", "lad_name": "One", "n_lsoas": 150}],
            }
        ],
    }

    artifact = prepare_staged_batch_artifact([row], plan=plan, batch_index=1, elapsed_seconds=1.0)

    staged_row = artifact["rows"][0]
    assert artifact["contains_family_inference"] is False
    assert "p_lower" not in staged_row
    assert "p_upper" not in staged_row
    assert "p_fdr" not in staged_row
    assert "rejects_lower_fdr" not in staged_row
    assert "observed_percentile" not in staged_row["null_summary"]


def test_staged_assembly_refuses_an_incomplete_batch_set(tmp_path) -> None:
    plan = {
        "eligible_count": 69,
        "batches": [{"batch_index": index, "members": []} for index in (1, 2, 3)],
    }

    with pytest.raises(FileNotFoundError, match="batch_1.json"):
        load_staged_batch_rows(plan, tmp_path)


def test_assemble_result_reconstructs_deferred_tail_inference(monkeypatch) -> None:
    monkeypatch.setattr(driver, "validate_result_payload", lambda payload: None)
    row = {
        "lad_code": "E1",
        "lad_name": "One",
        "n_lsoas": 150,
        "observed": {"h1_total_area": 1.0},
        "null_h1_total_area": [1.0, 2.0, 3.0],
        "null_summary": {"mean": 2.0, "standard_deviation": 1.0},
        "null_validity": {"valid": True, "reasons": []},
        "redundant": False,
        "runtime": {"peak_rss_mb": 10.0},
    }

    payload = driver.assemble_result(
        [row],
        frozen_family={
            "eligible_count": 1,
            "members": [{"lad_code": "E1", "lad_name": "One", "n_lsoas": 150}],
            "family_sha256": "family-sha",
            "frozen_at": "2026-07-16T00:00:00+00:00",
        },
        input_hashes={"input": "sha"},
        workers=8,
        preflight={"estimated_wall_time_hours": 1.0},
        pilot={"lad_code": "E08000025", "observed": {"h1_total_area": 27.0}, "p_lower": 0.01},
        invariance_audit={"verdict": "VALID NULL"},
        elapsed_seconds=1.0,
    )

    assembled = payload["lad_results"][0]
    assert assembled["p_lower"] == 0.5
    assert assembled["p_upper"] == 1.0
    assert assembled["null_summary"]["observed_percentile"] == pytest.approx(100.0 / 3.0)
    assert assembled["p_fdr"] == 0.5
