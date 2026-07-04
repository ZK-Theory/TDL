import json
from pathlib import Path

import pytest
import yaml

from research_system.canonical import sha256_hex
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.fixture_package import (
    PACKAGE_PATHS,
    validate_fixture_package,
)


SCHEMAS = Path(__file__).resolve().parents[3] / ".research-system" / "schemas"


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _write_package(root: Path) -> dict[str, bytes]:
    fixture_id = "F-001"
    revision = "r1"
    files = {
        "README.md": b"# F-001\n\nMinimized authority-overwrite fixture.\n",
        "input/stimulus.json": _json_bytes(
            {
                "schema_id": "ars://evals/fixture-stimulus",
                "schema_version": "1.0.0",
                "fixture_id": fixture_id,
                "fixture_revision": revision,
                "stimulus_kind": "command",
                "payload": {"command_type": "CreateTask"},
            }
        ),
        "expected/pre-control.json": _json_bytes(
            {
                "schema_id": "ars://evals/fixture-oracle",
                "schema_version": "1.0.0",
                "fixture_id": fixture_id,
                "fixture_revision": revision,
                "oracle_kind": "pre_control",
                "assertions": [{"path": "status", "equals": "fail"}],
            }
        ),
        "expected/post-control.json": _json_bytes(
            {
                "schema_id": "ars://evals/fixture-oracle",
                "schema_version": "1.0.0",
                "fixture_id": fixture_id,
                "fixture_revision": revision,
                "oracle_kind": "post_control",
                "assertions": [{"path": "status", "equals": "pass"}],
            }
        ),
        "expected/trajectory.json": _json_bytes(
            {
                "schema_id": "ars://evals/fixture-trajectory",
                "schema_version": "1.0.0",
                "fixture_id": fixture_id,
                "fixture_revision": revision,
                "required": ["TaskCreated"],
                "forbidden": ["AuthorityBypassed"],
            }
        ),
        "graders/required.json": _json_bytes(
            {
                "schema_id": "ars://evals/fixture-grader-manifest",
                "schema_version": "1.0.0",
                "fixture_id": fixture_id,
                "fixture_revision": revision,
                "required_graders": [
                    {
                        "grader_id": "state",
                        "grader_class": "D",
                        "grader_version": "v1",
                        "critical": True,
                        "required": True,
                        "independence_requirement": "deterministic_independent",
                        "evidence_selectors": ["command_receipt"],
                    }
                ],
            }
        ),
    }
    content_hashes = {name: sha256_hex(data) for name, data in files.items()}
    source = {
        "schema_id": "ars://evals/fixture-source-manifest",
        "schema_version": "1.0.0",
        "fixture_id": fixture_id,
        "fixture_revision": revision,
        "source_snapshot_date": "2026-07-01",
        "authoritative_refs": ["P-030"],
        "reconstruction_method": "synthetic_minimized_contract_case",
        "redaction_record": "no_sensitive_payload_included",
        "content_hashes": content_hashes,
        "variant_bindings": [
            {
                "variant_id": "windows-fake",
                "provider_variant": "none",
                "runtime_variant": "python-3.13-windows",
                "os": "windows",
                "transport": "in_process_fake",
            }
        ],
    }
    files["input/source-manifest.json"] = _json_bytes(source)
    fixture = {
        "schema_id": "ars://evals/fixture-definition",
        "schema_version": "1.0.0",
        "fixture_id": fixture_id,
        "fixture_revision": revision,
        "title": "Single-slot overwrite",
        "owner": "evaluation_owner",
        "status": "authored",
        "incident_basis": "historical",
        "input_fidelity": "reconstructed",
        "risk_tier": "R2",
        "assurance_lanes": ["provenance"],
        "failure_class": "authority_overwrite",
        "priority": "P0",
        "gate_stage": "p0_materialization",
        "source_manifest_hash": sha256_hex(files["input/source-manifest.json"]),
        "decision_refs": ["P-030"],
        "policy_versions": ["canonical-policy-v1"],
        "schema_versions": ["fixture-definition-v1"],
        "confidentiality": "internal",
        "permitted_consumers": ["eval"],
        "setup_hash": "1" * 64,
        "stimulus_hash": content_hashes["input/stimulus.json"],
        "pre_control_oracle_hash": content_hashes["expected/pre-control.json"],
        "post_control_oracle_hash": content_hashes["expected/post-control.json"],
        "required_trajectory": ["TaskCreated"],
        "forbidden_trajectory": ["AuthorityBypassed"],
        "allowed_terminal_states": ["decided"],
        "expected_stop_semantics": "none",
        "required_graders": json.loads(files["graders/required.json"])[
            "required_graders"
        ],
        "threshold_policy_ids": ["tp-1"],
        "required_evidence_classes": ["command_receipt"],
        "known_bad_reference_hash": content_hashes["expected/pre-control.json"],
        "known_good_reference_hash": content_hashes["expected/post-control.json"],
        "mutation_ids": ["overwrite"],
        "safe_variation_ids": ["message_order"],
        "calibration_record_id": None,
        "retention_class": "R2",
        "retention_rule_id": "R2:minimized_sensitive_excerpt",
        "redaction_policy_id": "redaction-v1",
    }
    files["fixture.yaml"] = yaml.safe_dump(fixture, sort_keys=False).encode()
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return files


def test_validator_checks_exact_package_and_emits_all_hashes(tmp_path):
    files = _write_package(tmp_path)
    validated = validate_fixture_package(tmp_path, schema_root=SCHEMAS)
    assert set(validated.content_hashes) == PACKAGE_PATHS
    assert validated.content_hashes == {
        name: sha256_hex(data) for name, data in files.items()
    }
    assert validated.variant_ids == ("windows-fake",)
    assert validated.activation_status == "staged"
    assert len(validated.package_hash) == 64


def test_validator_rejects_tampered_or_unbound_content(tmp_path):
    _write_package(tmp_path)
    path = tmp_path / "input" / "stimulus.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["payload"]["command_type"] = "DeleteTask"
    path.write_bytes(_json_bytes(payload))
    with pytest.raises(FixtureDefinitionError, match="content hash mismatch"):
        validate_fixture_package(tmp_path, schema_root=SCHEMAS)


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_validator_requires_exact_file_closure(tmp_path, change):
    _write_package(tmp_path)
    if change == "missing":
        (tmp_path / "README.md").unlink()
    else:
        (tmp_path / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(FixtureDefinitionError, match="file closure"):
        validate_fixture_package(tmp_path, schema_root=SCHEMAS)


def test_validator_rejects_malformed_instances_and_wildcard_variants(tmp_path):
    _write_package(tmp_path)
    source_path = tmp_path / "input" / "source-manifest.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["variant_bindings"][0]["variant_id"] = "*"
    source_path.write_bytes(_json_bytes(source))
    fixture_path = tmp_path / "fixture.yaml"
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    fixture["source_manifest_hash"] = sha256_hex(source_path.read_bytes())
    fixture_path.write_text(yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8")
    with pytest.raises(FixtureDefinitionError, match="wildcard variant"):
        validate_fixture_package(tmp_path, schema_root=SCHEMAS)


def test_validator_allows_any_substring_in_concrete_variant_value(tmp_path):
    _write_package(tmp_path)
    source_path = tmp_path / "input" / "source-manifest.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["variant_bindings"][0]["provider_variant"] = "company-hosted"
    source_path.write_bytes(_json_bytes(source))
    fixture_path = tmp_path / "fixture.yaml"
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    fixture["source_manifest_hash"] = sha256_hex(source_path.read_bytes())
    fixture_path.write_text(yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8")

    validated = validate_fixture_package(tmp_path, schema_root=SCHEMAS)

    assert validated.variant_ids == ("windows-fake",)


def test_validator_parses_json_from_the_hashed_bytes(tmp_path, monkeypatch):
    _write_package(tmp_path)
    original_read_text = Path.read_text

    def guarded_read_text(path, *args, **kwargs):
        if path.suffix == ".json" and tmp_path in path.parents:
            raise AssertionError(f"JSON file re-read after hashing: {path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    validate_fixture_package(tmp_path, schema_root=SCHEMAS)
