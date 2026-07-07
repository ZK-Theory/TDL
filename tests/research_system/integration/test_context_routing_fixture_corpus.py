import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

from research_system.evals.fixture_package import validate_fixture_package


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"
SCHEMAS = ROOT / ".research-system" / "schemas"
EXPECTED_CASES = {
    "F-021": ("governing_amendment_recall", "P1", "R2"),
    "F-022": ("reviewer_independence_evidence", "P0", "R3"),
    "F-025": ("mandatory_scope_closure", "P0", "R3"),
    "F-026": ("implementer_scientific_closure", "P0", "R2"),
    "F-027": ("optional_index_deletion_equivalence", "P0", "R1"),
    "F-028": ("context_budget_fail_closed", "P0", "R2"),
    "F-031": ("deterministic_eligibility_routing", "P0", "R3"),
    "F-033": ("predispatch_verifier_feasibility", "P0", "R3"),
    "F-035": ("two_key_assurance_non_compensation", "P0", "R3"),
}


def _load_json(root: Path, relative: str) -> dict[str, object]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def test_context_routing_corpus_has_exact_validated_staged_closure():
    missing = {fixture_id for fixture_id in EXPECTED_CASES if not (FIXTURES / fixture_id).is_dir()}
    assert not missing

    for fixture_id, (_, priority, risk_tier) in EXPECTED_CASES.items():
        root = FIXTURES / fixture_id
        validated = validate_fixture_package(root, schema_root=SCHEMAS)
        definition = yaml.safe_load((root / "fixture.yaml").read_text("utf-8"))

        assert validated.fixture_id == fixture_id
        assert validated.activation_status == "staged"
        assert definition["status"] == "authored"
        assert definition["priority"] == priority
        assert definition["risk_tier"] == risk_tier
        assert definition["gate_stage"] == "p0_materialization"
        assert definition["calibration_record_id"] is None


def test_each_package_encodes_its_named_contract_from_input_bytes():
    stimulus_hashes = set()
    post_control_hashes = set()

    for fixture_id, (contract, _, _) in EXPECTED_CASES.items():
        root = FIXTURES / fixture_id
        validated = validate_fixture_package(root, schema_root=SCHEMAS)
        stimulus = _load_json(root, "input/stimulus.json")
        pre_control = _load_json(root, "expected/pre-control.json")
        post_control = _load_json(root, "expected/post-control.json")

        assert stimulus["payload"]["contract"] == contract
        assert pre_control["assertions"][0]["property"] == contract
        assert pre_control["assertions"][0]["satisfied"] is False
        assert post_control["assertions"][0]["property"] == contract
        assert post_control["assertions"][0]["satisfied"] is True
        serialized = json.dumps({"stimulus": stimulus, "pre": pre_control, "post": post_control})
        assert "control_satisfied" not in serialized
        assert '"path": "status"' not in serialized
        stimulus_hashes.add(validated.content_hashes["input/stimulus.json"])
        post_control_hashes.add(validated.content_hashes["expected/post-control.json"])

    assert len(stimulus_hashes) == len(EXPECTED_CASES)
    assert len(post_control_hashes) == len(EXPECTED_CASES)


def test_model_graders_are_cross_family_and_f035_keeps_both_keys():
    for fixture_id in EXPECTED_CASES:
        graders = _load_json(FIXTURES / fixture_id, "graders/required.json")
        for grader in graders["required_graders"]:
            if grader["grader_class"] == "M":
                assert grader["independence_requirement"] == "cross_family_context_independent"

    f035 = _load_json(FIXTURES / "F-035", "expected/post-control.json")
    evidence = f035["assertions"][0]["expected_evidence"]
    assert evidence["key_a_passed"] is True
    assert evidence["key_b_passed"] is False
    assert evidence["non_compensable"] is True
    assert evidence["step_up_required"] is True


def test_shard_generators_check_only_their_owned_fixture_directories(tmp_path):
    scripts = (
        ROOT / "tools" / "ars" / "materialize_control_store_fixtures.py",
        ROOT / "tools" / "ars" / "materialize_context_routing_fixtures.py",
    )
    for script in scripts:
        result = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=tmp_path,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        assert result.returncode == 0, result.stderr
