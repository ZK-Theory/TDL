"""Deterministic tests for the deprivation scale-coherence battery driver."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from poverty_tda.scripts.run_deprivation_scale_coherence import (
    PreparedLad,
    _peak_rss_mb,
    enumerate_eligible_lads,
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
