import json
from pathlib import Path

import yaml

from research_system.evals.fixture_package import validate_fixture_package


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"
SCHEMAS = ROOT / ".research-system" / "schemas"

EXPECTED_CONTRACTS = {
    "F-001": "immutable_message_ownership",
    "F-002": "message_kind_separation",
    "F-003": "explicit_root_binding",
    "F-004": "canonical_projection_precedence",
    "F-005": "exact_scope_revision_closure",
    "S-001": "idempotent_receipt_recovery",
    "S-002": "exclusive_claim_serialization",
    "S-006": "compatibility_path_ownership",
    "S-008": "complete_scope_member_closure",
    "S-009": "projection_replay_equivalence",
    "S-010": "unknown_event_version_fail_closed",
    "S-011": "atomic_writer_crash_recovery",
    "S-012": "single_writer_branch_serialization",
}


def _load_json(root: Path, relative: str) -> dict[str, object]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def test_control_store_corpus_has_exact_validated_staged_closure():
    observed = {path.name for path in FIXTURES.iterdir() if path.is_dir()}
    assert observed == set(EXPECTED_CONTRACTS)

    for fixture_id in sorted(EXPECTED_CONTRACTS):
        root = FIXTURES / fixture_id
        validated = validate_fixture_package(root, schema_root=SCHEMAS)
        definition = yaml.safe_load((root / "fixture.yaml").read_text("utf-8"))

        assert validated.fixture_id == fixture_id
        assert validated.activation_status == "staged"
        assert definition["status"] == "authored"
        assert definition["calibration_record_id"] is None


def test_each_package_encodes_its_named_behavior_contract_from_input_bytes():
    stimulus_hashes = set()
    post_control_hashes = set()

    for fixture_id, contract in EXPECTED_CONTRACTS.items():
        root = FIXTURES / fixture_id
        validated = validate_fixture_package(root, schema_root=SCHEMAS)
        stimulus = _load_json(root, "input/stimulus.json")
        pre_control = _load_json(root, "expected/pre-control.json")
        post_control = _load_json(root, "expected/post-control.json")
        graders = _load_json(root, "graders/required.json")

        assert stimulus["payload"]["contract"] == contract
        assert pre_control["assertions"][0]["property"] == contract
        assert pre_control["assertions"][0]["satisfied"] is False
        assert post_control["assertions"][0]["property"] == contract
        assert post_control["assertions"][0]["satisfied"] is True
        assert {
            f"{fixture_id.lower()}-outcome",
            f"{fixture_id.lower()}-trajectory",
        }.issubset({
            grader["grader_id"] for grader in graders["required_graders"]
        })
        assert all(
            contract in grader["evidence_selectors"]
            for grader in graders["required_graders"]
        )

        serialized = json.dumps(
            {"stimulus": stimulus, "pre": pre_control, "post": post_control}
        )
        assert "control_satisfied" not in serialized
        assert '"path": "status"' not in serialized
        stimulus_hashes.add(validated.content_hashes["input/stimulus.json"])
        post_control_hashes.add(validated.content_hashes["expected/post-control.json"])

    assert len(stimulus_hashes) == len(EXPECTED_CONTRACTS)
    assert len(post_control_hashes) == len(EXPECTED_CONTRACTS)


def test_corpus_oracles_bind_required_and_forbidden_trajectories():
    for fixture_id in EXPECTED_CONTRACTS:
        root = FIXTURES / fixture_id
        definition = yaml.safe_load((root / "fixture.yaml").read_text("utf-8"))
        trajectory = _load_json(root, "expected/trajectory.json")

        assert trajectory["required"] == definition["required_trajectory"]
        assert trajectory["forbidden"] == definition["forbidden_trajectory"]
        assert trajectory["required"]
        assert trajectory["forbidden"]
        assert set(trajectory["required"]).isdisjoint(trajectory["forbidden"])
