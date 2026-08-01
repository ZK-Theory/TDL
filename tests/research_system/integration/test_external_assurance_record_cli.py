"""Exercise the bounded external assurance-record CLI seam end to end."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.assurance.external_records import ExternalAssuranceRecordStore
from research_system.authority import authority_bootstrap_sha256, initialize_authority_control_store
from research_system.canonical import canonical_bytes, jsonable
from research_system.cli import main
from research_system.config import ControlBinding
from research_system.errors import ConfigurationError
from research_system.store.identity import rebind_restored_store
from tests.research_system.factories import authority_bootstrap


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
RECORD_ID = "act_01978abc-2000-7000-8000-000000002000"


def _record() -> dict[str, str]:
    return {
        "record_type": "canonical_actor",
        "actor_id": RECORD_ID,
        "actor_kind": "agent",
        "canonical_name": "Ada",
        "status": "active",
    }


def _config(tmp_path: Path) -> tuple[Path, Path, str]:
    code_root = tmp_path / "code"
    code_root.mkdir()
    shutil.copytree(SCHEMA_ROOT, code_root / ".research-system" / "schemas")
    shutil.copytree(REPO_ROOT / ".research-system" / "contracts", code_root / ".research-system" / "contracts")
    control_root = tmp_path / "control"
    bootstrap = authority_bootstrap(publication_expires_at="2099-07-13T00:00:00Z")
    identity = initialize_authority_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=code_root / ".research-system" / "schemas",
    )
    schema_root = code_root / ".research-system" / "schemas"
    config = tmp_path / "binding.json"
    config.write_text(
        json.dumps(
            {
                "code_roots": [str(code_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(schema_root.resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )
    return config, control_root, identity


def _restore_cli_case(tmp_path: Path) -> tuple[dict[str, object], list[str]]:
    from tests.research_system.integration.test_gate5_release_tranche import _build_restore_case

    case = _build_restore_case(tmp_path)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(jsonable(asdict(case["receipt"]))))
    registry = case["registry"]
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://evals/evidence-store-registry",
                "schema_version": "1.0.0",
                "store_id": registry.store_id,
                "registry_hash": registry.registry_hash,
                "policy_revision": registry.policy_revision,
                "primary_root": str(registry.primary_root),
                "runtime_root": str(registry.runtime_root),
                "staging_root": str(registry.staging_root),
                "temp_root": str(registry.temp_root),
                "replicas": [str(path) for path in registry.replicas],
                "backup_roots": [str(path) for path in registry.backup_roots],
                "restore_roots": [str(path) for path in registry.restore_roots],
                "permitted_consumers": list(registry.permitted_consumers),
                "retention_policy_ids": list(registry.retention_policy_ids),
                "verifier_authority_bindings": [list(pair) for pair in registry.verifier_authority_bindings],
                "unregistered_replicas_prohibited": registry.unregistered_replicas_prohibited,
            }
        )
    )
    config_output = tmp_path / "restored-binding.json"
    args = [
        "store",
        "restore-bind",
        "--control-root",
        str(case["target"]),
        "--receipt",
        str(receipt_path),
        "--snapshot",
        str(case["snapshot_path"]),
        "--endpoint-ownership",
        str(case["endpoint_path"]),
        "--artefact-manifest",
        str(case["artefact_manifest_path"]),
        "--registry",
        str(registry_path),
        "--actor-id",
        case["actor_id"],
        "--authority-grant-id",
        case["authority_grant_id"],
        "--schema-root",
        str(case["code_root"] / ".research-system" / "schemas"),
        "--config-output",
        str(config_output),
    ]
    return case, args


def test_assurance_record_write_cli_persists_and_resolves(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config, control_root, authority_root = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")

    assert (
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["record_class"] == "canonical_actor"
    assert receipt["record_id"] == RECORD_ID
    assert receipt["revision"] == 1

    resolved = ControlStoreAuthorityResolver(ControlBinding.load(config)).resolve(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=authority_root,
        phase="load",
    )
    assert resolved == _record()


def test_assurance_record_write_cli_requires_json_object(tmp_path: Path) -> None:
    config, _, _ = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must contain an object"):
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )


def test_assurance_record_survives_copy_rebind_and_fresh_binding_restart(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config, source_root, store_identity = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")
    assert (
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )
        == 0
    )
    capsys.readouterr()

    target_root = tmp_path / "restored"
    shutil.copytree(source_root, target_root)
    rebind_restored_store(
        target_root,
        source_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=store_identity,
        expected_code_roots=[tmp_path / "code"],
    )
    fresh_config = tmp_path / "fresh-binding.json"
    fresh_config.write_text(
        json.dumps(
            {
                "code_roots": [str((tmp_path / "code").resolve())],
                "control_root": str(target_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((tmp_path / "code" / ".research-system" / "schemas").resolve()),
                "store_identity": store_identity,
            }
        ),
        encoding="utf-8",
    )
    fresh = ControlBinding.load(fresh_config)
    resolved = ControlStoreAuthorityResolver(fresh).resolve(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=store_identity,
        phase="load",
    )
    assert resolved == _record()


def test_restore_bind_cli_rebinds_only_after_verified_preflight(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tests.research_system.integration.test_gate5_release_tranche import _build_restore_case

    case = _build_restore_case(tmp_path)
    source_config = tmp_path / "source-binding.json"
    source_config.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(case["code_root"].resolve())],
                "control_root": str(case["source"].resolve()),
                "project_id": case["receipt"].project_id,
                "schema_root": str((case["code_root"] / ".research-system" / "schemas").resolve()),
                "store_identity": case["receipt"].store_identity,
            }
        )
    )
    ExternalAssuranceRecordStore(ControlBinding.load(source_config)).write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=_record(),
    )
    shutil.copytree(
        case["source"] / "objects" / "assurance_record",
        case["target"] / "objects" / "assurance_record",
        dirs_exist_ok=True,
    )
    before_events = sorted(
        (path.relative_to(case["target"]).as_posix(), path.read_bytes())
        for path in (case["target"] / "events").rglob("*.jsonl")
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(jsonable(asdict(case["receipt"]))))
    registry = case["registry"]
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://evals/evidence-store-registry",
                "schema_version": "1.0.0",
                "store_id": registry.store_id,
                "registry_hash": registry.registry_hash,
                "policy_revision": registry.policy_revision,
                "primary_root": str(registry.primary_root),
                "runtime_root": str(registry.runtime_root),
                "staging_root": str(registry.staging_root),
                "temp_root": str(registry.temp_root),
                "replicas": [str(path) for path in registry.replicas],
                "backup_roots": [str(path) for path in registry.backup_roots],
                "restore_roots": [str(path) for path in registry.restore_roots],
                "permitted_consumers": list(registry.permitted_consumers),
                "retention_policy_ids": list(registry.retention_policy_ids),
                "verifier_authority_bindings": [list(pair) for pair in registry.verifier_authority_bindings],
                "unregistered_replicas_prohibited": registry.unregistered_replicas_prohibited,
            }
        )
    )
    config_output = tmp_path / "restored-binding.json"
    assert (
        main(
            [
                "store",
                "restore-bind",
                "--control-root",
                str(case["target"]),
                "--receipt",
                str(receipt_path),
                "--snapshot",
                str(case["snapshot_path"]),
                "--endpoint-ownership",
                str(case["endpoint_path"]),
                "--artefact-manifest",
                str(case["artefact_manifest_path"]),
                "--registry",
                str(registry_path),
                "--actor-id",
                case["actor_id"],
                "--authority-grant-id",
                case["authority_grant_id"],
                "--schema-root",
                str(case["code_root"] / ".research-system" / "schemas"),
                "--config-output",
                str(config_output),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "bound"
    fresh = ControlBinding.load(config_output)
    assert fresh.control_root == case["target"].resolve()
    resolved = ControlStoreAuthorityResolver(fresh).resolve(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=case["receipt"].store_identity,
        phase="load",
    )
    assert resolved == _record()
    assert (
        sorted(
            (path.relative_to(case["target"]).as_posix(), path.read_bytes())
            for path in (case["target"] / "events").rglob("*.jsonl")
        )
        == before_events
    )


def test_restore_bind_cli_preflights_fresh_binding_failure_before_rebind(tmp_path: Path, monkeypatch) -> None:
    import research_system.cli as cli_module
    from research_system.store.identity import load_restore_binding_evidence

    case, args = _restore_cli_case(tmp_path)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    before_events = sorted(path.read_bytes() for path in (case["target"] / "events").rglob("*.jsonl"))
    original_load = cli_module.ControlBinding.load

    def fail_shadow_load(path):
        if ".restore-binding-" in str(path):
            raise ConfigurationError("simulated fresh binding failure")
        return original_load(path)

    monkeypatch.setattr(cli_module.ControlBinding, "load", staticmethod(fail_shadow_load))
    with pytest.raises(ConfigurationError, match="simulated fresh binding failure"):
        main(args)
    assert manifest_path.read_bytes() == before_manifest
    assert sorted(path.read_bytes() for path in (case["target"] / "events").rglob("*.jsonl")) == before_events
    assert load_restore_binding_evidence(case["target"]) is None
    assert not (tmp_path / "restored-binding.json").exists()


def test_restore_bind_cli_retry_recovers_after_output_publication_failure(tmp_path: Path, monkeypatch) -> None:
    import research_system.cli as cli_module
    from research_system.store.identity import load_restore_binding_evidence, load_store_manifest

    case, args = _restore_cli_case(tmp_path)
    original_publish = cli_module._publish_reserved_output

    def fail_publication(*_args, **_kwargs):
        raise OSError("simulated output publication failure")

    monkeypatch.setattr(cli_module, "_publish_reserved_output", fail_publication)
    with pytest.raises(OSError, match="simulated output publication failure"):
        main(args)
    assert load_store_manifest(case["target"])["control_root"] == str(case["target"].resolve())
    assert load_restore_binding_evidence(case["target"]) is not None
    assert not (tmp_path / "restored-binding.json").exists()

    monkeypatch.setattr(cli_module, "_publish_reserved_output", original_publish)
    assert main(args) == 0
    assert ControlBinding.load(tmp_path / "restored-binding.json").control_root == case["target"].resolve()
