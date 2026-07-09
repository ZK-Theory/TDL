from pathlib import Path

import pytest

from research_system.errors import ConfigurationError
from research_system.evals.policies import (
    load_threshold_policies,
    require_calibration_policy,
)

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


def test_threshold_policies_define_exact_property_v1():
    policies = load_threshold_policies(EVALS / "threshold-policies.yaml")
    row = policies["exact-property-v1"]
    assert row["comparison"] == "byte_identical_normalized_decision"
    assert set(row["grader_classes"]) == {"D", "T", "R", "O", "P"}
    assert row["model_threshold"] is None and row["human_threshold"] is None


def test_every_p0_fixture_threshold_policy_resolves():
    from research_system.evals.coverage import P0_CASES
    from research_system.evals.fixture_package import load_typed_definition

    policies = load_threshold_policies(EVALS / "threshold-policies.yaml")
    for fixture_id in sorted(P0_CASES):
        definition = load_typed_definition(EVALS / "fixtures" / fixture_id)
        missing = set(definition.threshold_policy_ids) - set(policies)
        assert not missing, f"{fixture_id} references undefined policies {missing}"


def test_calibration_policy_matches_engine():
    payload = require_calibration_policy(EVALS / "p0-calibration-policy.yaml")
    from research_system.evals.calibration import DETERMINISTIC_REPETITIONS

    assert payload["deterministic_repetitions"] == DETERMINISTIC_REPETITIONS


def test_calibration_policy_mismatch_is_configuration_error(tmp_path):
    bad = tmp_path / "p0-calibration-policy.yaml"
    bad.write_text(
        (EVALS / "p0-calibration-policy.yaml")
        .read_text(encoding="utf-8")
        .replace("deterministic_repetitions: 2", "deterministic_repetitions: 1"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError):
        require_calibration_policy(bad)


def test_calibration_policy_engine_constant_mismatch_raises_configuration_error(monkeypatch):
    monkeypatch.setattr("research_system.evals.calibration.DETERMINISTIC_REPETITIONS", 3)
    with pytest.raises(ConfigurationError, match="engine constant is 3"):
        require_calibration_policy(EVALS / "p0-calibration-policy.yaml")


def test_empty_threshold_registry_loads_as_empty(tmp_path):
    bad = tmp_path / "threshold-policies.yaml"
    bad.write_text("schema_version: '1.0.0'\npolicies: []\n", encoding="utf-8")
    policies = load_threshold_policies(bad)
    assert policies == {}
    # The closure check itself lives in run_p0_coverage (Step 6): an empty
    # registry makes every fixture's threshold_policy_ids unresolvable there.
