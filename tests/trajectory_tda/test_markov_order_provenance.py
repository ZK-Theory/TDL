"""Binding tests for permutation-null stochastic provenance."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trajectory_tda.scripts.stage1._battery_core import markov_null_provenance

ROOT = Path(__file__).resolve().parents[2]


def test_battery_result_exposes_null_provenance() -> None:
    """The producer emits exact, typed Markov-null provenance and fails closed."""
    provenance = markov_null_provenance(
        markov_order_k=1,
        n_permutations=1000,
        seed=42,
    )

    assert provenance == {
        "markov_order_k": 1,
        "n_permutations": 1000,
        "seed": 42,
        "null_model": "markov-1",
    }
    assert type(provenance["markov_order_k"]) is int
    assert type(provenance["n_permutations"]) is int
    assert type(provenance["seed"]) is int
    assert type(provenance["null_model"]) is str

    invalid_cases = (
        {"markov_order_k": None, "n_permutations": 1000, "seed": 42},
        {"markov_order_k": True, "n_permutations": 1000, "seed": 42},
        {"markov_order_k": 1, "n_permutations": 0, "seed": 42},
        {"markov_order_k": 1, "n_permutations": True, "seed": 42},
        {"markov_order_k": 1, "n_permutations": 1000, "seed": False},
    )
    for invalid in invalid_cases:
        with pytest.raises((TypeError, ValueError)):
            markov_null_provenance(**invalid)


def test_markov_order_provenance_output_validation_dispatch() -> None:
    """Persisted combined batteries dispatch their run_params block to the schema."""
    contract_path = ROOT / "contracts" / "stochastic-tests" / "markov-order-provenance-json-validation.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert contract["kind"] == "output_validation"
    assert contract["output_validation"] == {
        "applies_to_glob": ("results/trajectory_tda_integration/stage1/matched_w2_battery_*.json"),
        "wrapper_key": "run_params",
        "schema_contracts": ["markov-order-provenance"],
    }
