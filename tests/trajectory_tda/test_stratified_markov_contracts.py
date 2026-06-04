# Research context: contracts/topology-invariants + contracts/stage1-output-schemas
# Purpose: Binding tests for the T1.37 frozen stratified Markov-1 runner and output schema.
"""Contract bindings for frozen stratified Markov-1 outputs."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

import trajectory_tda.scripts.run_stage1_battery as stage1_battery
import trajectory_tda.scripts.run_stratified_battery as stratified_battery
import trajectory_tda.scripts.run_wasserstein_battery as wasserstein_battery
import trajectory_tda.topology.permutation_nulls as permutation_nulls
from trajectory_tda.embedding import ngram_embed as embed_module
from trajectory_tda.scripts.stage1 import assemble_stratified_markov_partials


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STRATIFIED_ROOT_KEYS = (
    "pre_registration",
    "params",
    "outcome",
    "outcome_rule",
    "per_dataset",
    "fdr_tests",
    "usoc",
    "bhps",
    "date",
)


class InlineParallel:
    """Small joblib.Parallel stand-in that executes delayed tasks inline."""

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, tasks):
        out = []
        for task in tasks:
            func, args, kwargs = task
            out.append(func(*args, **kwargs))
        return out


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _aggregate_cell(pvalue: float = 0.01) -> dict:
    return {
        "w2_pvalue": pvalue,
        "pvalue_null_draws": 1000,
        "effect_null_pairs": 500,
        "landscape_l2_pvalue": pvalue,
        "t_ratio": 1.2,
        "bca_ci_lower": None,
        "bca_ci_upper": None,
        "d_perm": 0.4,
        "mean_obs_null": 2.0,
        "mean_null_null": 1.5,
        "landscape_t_ratio": 1.1,
        "landscape_bca_ci_lower": None,
        "landscape_bca_ci_upper": None,
        "landscape_d_perm": 0.3,
        "lower_tail_pvalue": 0.99,
    }


def _representative_regime(skipped: bool = False) -> dict:
    if skipped:
        return {"skipped": True, "n": 4}
    return {
        "n": 24,
        "n_landmarks_used": 24,
        "h0": _aggregate_cell(0.01),
        "h1": {k: v for k, v in _aggregate_cell(0.02).items() if k != "lower_tail_pvalue"},
    }


def _representative_output() -> dict:
    usoc = {"R0": _representative_regime(), "R1": _representative_regime(skipped=True)}
    bhps = {"R0": _representative_regime()}
    return stratified_battery._assemble_output(
        usoc_results=usoc,
        bhps_results=bhps,
        n_permutations=1000,
        n_landmarks=5000,
        seed=42,
        frozen_loadings=True,
        today="2026-05-28",
    )


def _assert_aggregate_cell(cell: dict, dim: str) -> None:
    contract = _load_contract("stage1-output-schemas/stage1-aggregate-output-cell.yaml")
    required = [entry["name"] for entry in contract["schema_def"]["required_keys"]]
    missing = [key for key in required if key not in cell]
    assert not missing, f"{dim} aggregate cell missing required keys: {missing}"
    if dim == "h0":
        assert "lower_tail_pvalue" in cell


def _assert_stratified_output_contract(data: dict) -> None:
    """Assert a stratified-Markov battery output payload meets the contract."""
    contract = _load_contract("stage1-output-schemas/stratified-markov1-output.yaml")
    required = [entry["name"] for entry in contract["schema_def"]["required_keys"]]
    assert required == list(STRATIFIED_ROOT_KEYS)
    missing = [key for key in required if key not in data]
    assert not missing, f"stratified output missing required keys: {missing}"
    assert isinstance(data["pre_registration"], str)
    assert isinstance(data["params"], dict)
    assert data["params"]["frozen_loadings"] is True
    assert data["outcome"] in {"A", "B", "C"}
    assert isinstance(data["outcome_rule"], str)
    assert set(data["per_dataset"]) == {"usoc", "bhps"}
    assert isinstance(data["fdr_tests"], dict)
    assert isinstance(data["usoc"], dict)
    assert isinstance(data["bhps"], dict)
    assert isinstance(data["date"], str)

    for summary in data["per_dataset"].values():
        for key in ("n_regimes_tested", "n_significant", "significant_regimes", "frac_significant"):
            assert key in summary

    assert data["fdr_tests"]
    for row in data["fdr_tests"].values():
        assert {"raw_pvalue", "rejected"} <= set(row)

    for dataset in ("usoc", "bhps"):
        assert data[dataset]
        for regime in data[dataset].values():
            if regime.get("skipped"):
                continue
            assert {"h0", "h1"} <= set(regime)
            _assert_aggregate_cell(regime["h0"], "h0")
            _assert_aggregate_cell(regime["h1"], "h1")


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


def test_stratified_markov_runner_threads_frozen_loadings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Frozen stratified runs pass per-regime fitted models into Markov nulls."""
    import joblib
    import poverty_tda.topology.multidim_ph as multidim_ph

    monkeypatch.setattr(joblib, "Parallel", InlineParallel)
    trajectories = [[STATES[(i + j) % len(STATES)] for j in range(10)] for i in range(12)]
    embeddings = np.zeros((12, 2))
    model_bundle = {"scaler": object(), "reducer": object()}
    seen: list[dict | None] = []

    monkeypatch.setattr(
        wasserstein_battery,
        "load_checkpoint",
        lambda checkpoint_dir: (embeddings, trajectories, {"pca_dim": 2, "include_bigrams": True}),
    )
    monkeypatch.setattr(wasserstein_battery, "load_regime_labels", lambda path: np.zeros(12, dtype=int))
    monkeypatch.setattr(
        embed_module,
        "ngram_embed",
        lambda trajs, **kwargs: (np.ones((len(trajs), 2)), {"fitted_models": model_bundle}),
    )
    monkeypatch.setattr(
        multidim_ph,
        "compute_rips_ph",
        lambda landmarks, max_dim: SimpleNamespace(dgms={0: np.empty((0, 2)), 1: np.empty((0, 2))}),
    )

    def fake_single_permutation(*args, frozen_models=None, **kwargs):
        seen.append(frozen_models)
        return {"H0": 1.0, "H1": 1.0, "H0_dgm": [], "H1_dgm": []}

    monkeypatch.setattr(permutation_nulls, "_single_permutation", fake_single_permutation)
    monkeypatch.setattr(stage1_battery, "_aggregate_combined", lambda *args, **kwargs: {"h0": _aggregate_cell()})

    result = stratified_battery._run_regime_battery(
        checkpoint_dir=tmp_path,
        analysis_json_path=tmp_path / "05_analysis.json",
        n_permutations=2,
        n_landmarks=20,
        seed=42,
        label="contract",
        frozen_loadings=True,
    )
    payload = stratified_battery._assemble_output(
        usoc_results=result,
        bhps_results=result,
        n_permutations=2,
        n_landmarks=20,
        seed=42,
        frozen_loadings=True,
        today="2026-05-28",
    )

    assert seen and all(models is model_bundle for models in seen)
    assert payload["params"]["frozen_loadings"] is True


def test_stratified_markov1_output_schema_contract() -> None:
    """Representative frozen stratified output satisfies the schema contract."""
    _assert_stratified_output_contract(_representative_output())


def test_stratified_markov_partial_outputs_assemble_to_full_contract(tmp_path: Path) -> None:
    """Split USoc/BHPS job outputs can be assembled into the final stratified schema."""
    usoc_path = tmp_path / "usoc_partial.json"
    bhps_path = tmp_path / "bhps_partial.json"
    output_path = tmp_path / "stratified_markov1_W2_L5000_frozen_2026-05-28.json"
    usoc_payload = stratified_battery._assemble_partial_output(
        dataset="usoc",
        results={"R0": _representative_regime()},
        n_permutations=1000,
        n_landmarks=5000,
        seed=42,
        frozen_loadings=True,
        today="2026-05-28",
    )
    bhps_payload = stratified_battery._assemble_partial_output(
        dataset="bhps",
        results={"R0": _representative_regime()},
        n_permutations=1000,
        n_landmarks=5000,
        seed=42,
        frozen_loadings=True,
        today="2026-05-28",
    )
    usoc_path.write_text(json.dumps(usoc_payload), encoding="utf-8")
    bhps_path.write_text(json.dumps(bhps_payload), encoding="utf-8")

    assembled_path = assemble_stratified_markov_partials.combine_partials(
        usoc_path,
        bhps_path,
        output=output_path,
    )
    data = json.loads(assembled_path.read_text(encoding="utf-8"))
    _assert_stratified_output_contract(data)


def test_stratified_markov1_output_json_validation_contract() -> None:
    """Validate every on-disk frozen stratified Markov-1 JSON, if any exist."""
    output_validation = _load_contract("stage1-output-schemas/stratified-markov1-output-json-validation.yaml")
    ov = output_validation["output_validation"]
    jsons = _matched_jsons(ov["applies_to_glob"])
    jsons = [path for path in jsons if _dispatch_filter(ov.get("file_dispatch"), path)]
    for json_path in jsons:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_stratified_output_contract(data)
