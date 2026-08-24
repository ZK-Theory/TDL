"""Contract controls for the public Gate 6 store-binding continuation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import research_system.cli as cli
import research_system.store.ledger as ledger


ROOT = Path(__file__).resolve().parents[3]
BINDING_SCHEMA_ROOT = ROOT / ".research-system" / "schemas" / "wp6-6" / "gate6-binding-repair"
V1_1_SCHEMA = BINDING_SCHEMA_ROOT / "store-binding-advance-object.schema.json"
V1_2_SCHEMA = BINDING_SCHEMA_ROOT / "store-binding-advance-object.v1-2.schema.json"


def _schema(path: Path) -> dict[str, object]:
    assert path.is_file(), f"missing append-only schema: {path.relative_to(ROOT)}"
    return json.loads(path.read_bytes())


@pytest.mark.parametrize("command", ("repair-binding", "advance-binding"))
def test_store_binding_cli_commands_require_intent(
    command: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Remediation-red: both public store commands expose required intent input."""

    intent = tmp_path / "intent.json"
    parser = cli._parser()

    parsed = parser.parse_args(["store", command, "--intent", str(intent)])
    assert parsed.group == "store"
    assert parsed.store_command == command
    assert parsed.intent == intent

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["store", command])
    assert exc_info.value.code == 2
    assert "--intent" in capsys.readouterr().err


def test_ledger_does_not_export_validated_service_session_minter() -> None:
    """Remediation-red: standalone services cannot mint ledger sessions."""

    assert not hasattr(ledger, "_issue_validated_service_session")


def test_store_binding_advance_v1_2_requires_governed_divergence_authority() -> None:
    """Remediation-red: v1.2 binds the exact governed divergent successor."""

    schema = _schema(V1_2_SCHEMA)
    properties = schema["properties"]
    required = set(schema["required"])
    assert schema["$id"] == "ars://wp6-6/gate6/binding-repair/object/StoreBindingAdvance"
    assert properties["schema_version"]["const"] == "1.2.0"
    assert set(properties["owner_action"]["enum"]) == {
        "advance-reviewed-divergence-store-binding",
        "advance-clean-descendant-store-binding",
    }

    required_v1_2_fields = {
        "governed_code_manifest_sha256",
        "governed_code_manifest_path",
        "predecessor_binding_sha256",
    }
    assert required_v1_2_fields <= required
    assert "reviewed_divergence_authority" not in required
    assert required_v1_2_fields | {"reviewed_divergence_authority"} <= set(properties)
    assert properties["governed_code_manifest_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert properties["governed_code_manifest_path"]["type"] == "string"

    authority = properties["reviewed_divergence_authority"]
    authority_fields = {
        "predecessor_binding_sha256",
        "predecessor_git_head",
        "candidate_git_head",
        "integration_ref",
        "protected_route_sha256",
        "protected_sources_sha256",
        "governed_code_manifest_sha256",
    }
    assert authority["type"] == "object"
    assert authority["additionalProperties"] is False
    assert set(authority["required"]) == authority_fields
    assert set(authority["properties"]) == authority_fields
    assert authority["properties"]["integration_ref"]["const"] == "refs/heads/main"

    governed_manifest_sha256 = "a" * 64
    base = {
        "schema_id": "ars://internal/store-binding-recovery",
        "schema_version": "1.2.0",
        "project_id": "prj_01978abc-0001-7000-8000-000000000001",
        "store_identity": "b" * 64,
        "control_root": "C:/control",
        "code_roots": ["C:/candidate"],
        "schema_root": "C:/candidate/.research-system/schemas",
        "origin_witness_sha256": "c" * 64,
        "git_head": "d" * 40,
        "git_tree": "e" * 40,
        "git_clean": True,
        "schema_catalogue_sha256": "f" * 64,
        "route": {
            "ref": ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json",
            "sha256": "1" * 64,
        },
        "sources": [
            {
                "ref": ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
                "sha256": "2" * 64,
                "size_bytes": 1,
            },
            {
                "ref": ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
                "sha256": "3" * 64,
                "size_bytes": 1,
            },
        ],
        "stale_evidence": {"refs": [], "missing_paths": []},
        "command_payload_hash": "4" * 64,
        "owner_actor_id": "act_01978abc-0002-7000-8000-000000000002",
        "idempotency_key": "binding-v1-2-contract",
        "prior_restore_transaction_id": "txb_01978abc-0003-7000-8000-000000000003",
        "prior_restore_intended_manifest_sha256": "5" * 64,
        "binding_config_path": "manifests/binding-repair-control-binding.json",
        "binding_config_sha256": "6" * 64,
        "predecessor_binding_sha256": "b" * 64,
        "governed_code_manifest_sha256": governed_manifest_sha256,
        "governed_code_manifest_path": (f"objects/governed-code/sha256-{governed_manifest_sha256}.json"),
        "reviewed_git_head": "d" * 40,
        "integrated_main_git_head": "d" * 40,
        "integration_ref": "refs/heads/main",
    }
    reviewed_authority = {
        "predecessor_binding_sha256": "b" * 64,
        "predecessor_git_head": "c" * 40,
        "candidate_git_head": "d" * 40,
        "integration_ref": "refs/heads/main",
        "protected_route_sha256": "e" * 64,
        "protected_sources_sha256": "f" * 64,
        "governed_code_manifest_sha256": governed_manifest_sha256,
    }
    reviewed = {
        **base,
        "owner_action": "advance-reviewed-divergence-store-binding",
        "reviewed_divergence_authority": reviewed_authority,
    }
    clean_descendant = {
        **base,
        "owner_action": "advance-clean-descendant-store-binding",
    }
    validator = Draft202012Validator(schema)

    assert validator.is_valid(reviewed)
    reviewed_without_authority = {
        key: value for key, value in reviewed.items() if key != "reviewed_divergence_authority"
    }
    assert not validator.is_valid(reviewed_without_authority)
    assert validator.is_valid(clean_descendant)
    assert not validator.is_valid({**clean_descendant, "reviewed_divergence_authority": reviewed_authority})


def test_store_binding_advance_v1_1_remains_the_legacy_schema() -> None:
    """Preservation-green: the append-only successor does not rewrite v1.1."""

    schema = _schema(V1_1_SCHEMA)
    properties = schema["properties"]
    assert properties["schema_version"]["const"] == "1.1.0"
    assert {
        "governed_code_manifest_sha256",
        "governed_code_manifest_path",
        "reviewed_divergence_authority",
    }.isdisjoint(properties)
