"""Exercise the governed KAN-77 CreateBackup public seam."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import research_system.cli as cli
import research_system.operations.backups as backups_module
from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.command.service import CommandService
from research_system.errors import ArsError, ConfigurationError, IntegrityError
from research_system.evals.retention import EvidenceStoreRegistry
from research_system.schema_registry import runtime_schema_registry
from research_system.projection.replay import replay
from research_system.store.identity import load_store_manifest
from research_system.store.ledger import EventLedger
from tests.research_system.integration.test_scoped_authority_grant_activation import (
    ACTIVATE_DECISION_ID,
    ACTOR_ID,
    GRANT_ID,
    PROJECT_ID,
    _activation_command,
    _decision,
    _system,
)


BACKUP_COMMAND_ID = "cmd_01978abc-7702-7000-8000-000000007702"
BACKUP_RECEIPT_ID = "bkr_01978abc-7703-7000-8000-000000007703"
ARTEFACT_ID = "art_01978abc-7704-7000-8000-000000007704"
DUPLICATE_COMMAND_ID = "cmd_01978abc-7705-7000-8000-000000007705"
DUPLICATE_RECEIPT_ID = "bkr_01978abc-7706-7000-8000-000000007706"
VERIFY_COMMAND_ID = "cmd_01978abc-7707-7000-8000-000000007707"
RECOVERY_EVIDENCE_ID = "rcv_01978abc-7708-7000-8000-000000007708"


def _backup_request_for_cli_validation() -> dict[str, Any]:
    request = dict.fromkeys(cli._BACKUP_REQUEST_FIELDS)
    request.update(
        {
            "evidence_refs": ["evidence:external-availability"],
            "schema_versions": ["ars-core@1.0.0"],
            "tool_versions": ["tdl@1.0.0"],
            "external_artefacts": [
                {
                    "artefact_id": ARTEFACT_ID,
                    "source_path": "external-evidence.bin",
                    "content_sha256": "0" * 64,
                    "availability": "available",
                    "availability_evidence_refs": ["evidence:external-availability"],
                    "observed_at": "2026-08-05T08:00:00Z",
                }
            ],
        }
    )
    return request


def _backup_cli_validation_args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        config=tmp_path / "binding.json",
        request=tmp_path / "backup-request.json",
        registry=tmp_path / "registry.yaml",
        destination_root=tmp_path / "backup",
    )


@pytest.mark.integration
def test_store_backup_cli_rejects_unexpected_external_artefact_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _backup_request_for_cli_validation()
    request["external_artefacts"][0]["unexpected"] = "not-in-the-input-contract"
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: object())
    monkeypatch.setattr(cli, "_read_json", lambda _path: request)

    with pytest.raises(ConfigurationError, match=r"external_artefacts\[0\].*unexpected"):
        cli._store_backup(_backup_cli_validation_args(tmp_path))


@pytest.mark.integration
@pytest.mark.parametrize(
    ("field", "nested"),
    [
        ("evidence_refs", False),
        ("schema_versions", False),
        ("tool_versions", False),
        ("availability_evidence_refs", True),
    ],
)
def test_store_backup_cli_rejects_strings_for_json_array_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    nested: bool,
) -> None:
    request = _backup_request_for_cli_validation()
    if nested:
        request["external_artefacts"][0][field] = "evidence:external-availability"
    else:
        request[field] = "not-a-json-array"
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: object())
    monkeypatch.setattr(cli, "_read_json", lambda _path: request)

    with pytest.raises(ConfigurationError, match=rf"{field} must be a list"):
        cli._store_backup(_backup_cli_validation_args(tmp_path))


def test_store_backup_separates_local_command_authority_from_external_spec_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "control"
    schema_root = tmp_path / "schemas"
    source_root.mkdir()
    schema_root.mkdir()
    request = _backup_request_for_cli_validation()
    request.update(
        {
            "command_id": BACKUP_COMMAND_ID,
            "receipt_id": BACKUP_RECEIPT_ID,
            "receipt_revision": 1,
            "submitted_at": "2026-08-05T08:00:00Z",
            "actor_id": ACTOR_ID,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": GRANT_ID,
            "idempotency_key": "backup-authority-role-split",
            "correlation_id": "backup-authority-role-split",
            "causation_id": None,
            "reason": "prove the backup authority roles remain separate",
            "snapshot_id": "snapshot-role-split",
            "encryption_class": "test",
            "redaction_class": "test",
            "destination_class": "test",
            "verified_at": "2026-08-05T08:00:00Z",
            "verified_by_actor_id": ACTOR_ID,
            "verification_authority_grant_id": GRANT_ID,
        }
    )
    binding = SimpleNamespace(
        control_root=source_root,
        schema_root=schema_root,
        project_id=PROJECT_ID,
        store_identity="store-local",
        origin_witness={"witness": "local"},
        origin_witness_path=tmp_path / "local-witness.json",
    )
    schemas = object()
    local_authority = object()
    external_spec_authority = object()
    captured: dict[str, object] = {}

    class Materializer:
        def __init__(self, **kwargs: object) -> None:
            captured["materializer_authority"] = kwargs["authority_resolver"]

        def derive_event_payload(self, **_kwargs: object) -> dict[str, object]:
            return {"canonical_tail_position": 0}

    class Service:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            captured["command_authority"] = kwargs["authority_resolver"]
            captured["validator_factory"] = kwargs["spec_execution_authority_validator_factory"]

        def submit(self, _command: dict[str, object]) -> SimpleNamespace:
            return SimpleNamespace(status="rejected", reason_code="test-stop")

    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(cli, "_read_json", lambda _path: request)
    monkeypatch.setattr(cli, "runtime_schema_registry", lambda _path: schemas)
    monkeypatch.setattr(cli, "LedgerAuthorityGrantResolver", lambda *_args, **_kwargs: local_authority)
    monkeypatch.setattr(cli, "_authority_resolver_from_config", lambda *_args, **_kwargs: external_spec_authority)
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda *_args: object())
    monkeypatch.setattr(cli, "BackupMaterializer", Materializer)
    monkeypatch.setattr(
        cli,
        "EventLedger",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot=lambda: SimpleNamespace(events=(), stream_versions={PROJECT_ID: 0})
        ),
    )
    monkeypatch.setattr(cli, "CommandService", Service)
    monkeypatch.setattr(cli, "ObjectStore", lambda _root: object())
    monkeypatch.setattr(cli, "ReceiptStore", lambda _root: object())
    monkeypatch.setattr(cli, "asdict", lambda value: vars(value))
    monkeypatch.setattr(cli, "_print_json", lambda _value: None)
    monkeypatch.setattr(
        cli,
        "_spec_replay_validator",
        lambda _root, _schemas, resolver, _events: resolver,
    )
    args = _backup_cli_validation_args(tmp_path)
    args.authority_config = tmp_path / "external-authority.json"

    assert cli._store_backup(args) == 0

    assert captured["materializer_authority"] is external_spec_authority
    assert captured["command_authority"] is local_authority
    validator_factory = captured["validator_factory"]
    assert callable(validator_factory)
    assert validator_factory(()) is external_spec_authority


def test_store_verify_restore_separates_local_command_authority_from_external_spec_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "control"
    schema_root = tmp_path / "schemas"
    target_root = tmp_path / "restore"
    for root in (source_root, schema_root, target_root):
        root.mkdir()
    binding = SimpleNamespace(
        control_root=source_root,
        schema_root=schema_root,
        project_id=PROJECT_ID,
        store_identity="store-local",
        origin_witness={"witness": "local"},
        origin_witness_path=tmp_path / "local-witness.json",
    )
    local_authority = object()
    external_spec_authority = object()
    captured: dict[str, object] = {}

    class Service:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            captured["command_authority"] = kwargs["authority_resolver"]
            captured["validator_factory"] = kwargs["spec_execution_authority_validator_factory"]

        def submit(self, _command: dict[str, object]) -> SimpleNamespace:
            return SimpleNamespace(status="rejected", reason_code="test-stop")

    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(cli, "_read_json", lambda _path: {"command_type": "VerifyRestore"})
    monkeypatch.setattr(cli, "_read_canonical_json", lambda _path: {})
    monkeypatch.setattr(cli, "_backup_receipt_from_json", lambda _value: object())
    monkeypatch.setattr(cli, "runtime_schema_registry", lambda _path: object())
    monkeypatch.setattr(cli, "LedgerAuthorityGrantResolver", lambda *_args, **_kwargs: local_authority)
    monkeypatch.setattr(cli, "_authority_resolver_from_config", lambda *_args, **_kwargs: external_spec_authority)
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda *_args: object())
    monkeypatch.setattr(cli, "EventLedger", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(cli, "CommandService", Service)
    monkeypatch.setattr(cli, "ObjectStore", lambda _root: object())
    monkeypatch.setattr(cli, "ReceiptStore", lambda _root: object())
    monkeypatch.setattr(cli, "asdict", lambda value: vars(value))
    monkeypatch.setattr(cli, "_print_json", lambda _value: None)
    monkeypatch.setattr(cli, "_spec_replay_validator", lambda _root, _schemas, resolver, _events: resolver)
    args = argparse.Namespace(
        config=tmp_path / "binding.json",
        command=tmp_path / "command.json",
        receipt=tmp_path / "receipt.json",
        registry=tmp_path / "registry.yaml",
        target_root=target_root,
        snapshot=tmp_path / "snapshot.json",
        endpoint_ownership=tmp_path / "endpoint.json",
        artefact_manifest=tmp_path / "artefacts.json",
        authority_config=tmp_path / "external-authority.json",
    )

    assert cli._store_verify_restore(args) == 0

    assert captured["command_authority"] is local_authority
    validator_factory = captured["validator_factory"]
    assert callable(validator_factory)
    assert validator_factory(()) is external_spec_authority


def _activate_backup_grant(tmp_path: Path) -> tuple[ControlBinding, EventLedger]:
    control_root, schemas, resolver, ledger, objects, service = _system(tmp_path)
    command_binding = schemas.command_binding("CreateBackup")
    assert command_binding is not None
    command_identity = schemas.resolve_identity(command_binding.schema_id, command_binding.schema_version)
    verify_binding = schemas.command_binding("VerifyRestore")
    assert verify_binding is not None
    verify_identity = schemas.resolve_identity(verify_binding.schema_id, verify_binding.schema_version)
    grant = {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_actor_classes": ["human"],
        "allowed_commands": [
            {
                "command_type": "CreateBackup",
                "schema_id": command_identity.schema_id,
                "schema_version": command_identity.schema_version,
                "schema_sha256": command_identity.sha256,
            },
            {
                "command_type": "VerifyRestore",
                "schema_id": verify_identity.schema_id,
                "schema_version": verify_identity.schema_version,
                "schema_sha256": verify_identity.sha256,
            },
        ],
        "allowed_policy_actions": [],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "project_store", "id": PROJECT_ID},
        },
        "risk_ceiling": "R3",
        "effective_at": "2026-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    decision = _decision(
        resolver,
        schemas,
        grant,
        record_id=ACTIVATE_DECISION_ID,
        action="activate_authority_grant",
    )
    objects.write("assurance_record", ACTIVATE_DECISION_ID, 1, decision)
    assert service.submit(_activation_command(resolver, schemas, grant, decision)).status == "accepted"

    manifest = load_store_manifest(
        control_root,
        approved_witness=resolver.approved_witness,
        approved_witness_path=resolver.approved_witness_path,
    )
    binding = ControlBinding(
        code_roots=tuple(Path(root) for root in manifest["code_roots"]),
        control_root=control_root,
        project_id=PROJECT_ID,
        schema_root=Path(manifest["schema_root"]),
        store_identity=manifest["store_identity"],
        origin_authority_root=resolver.approved_witness_path.parents[1],
        origin_witness_path=resolver.approved_witness_path,
        origin_witness_sha256=resolver.approved_witness.raw_sha256,
        origin_witness=resolver.approved_witness,
    )
    return binding, ledger


def _registry(
    tmp_path: Path,
    binding: ControlBinding,
    destination: Path,
    *,
    command_id: str = BACKUP_COMMAND_ID,
) -> EvidenceStoreRegistry:
    runtime_root = tmp_path / "registry-runtime"
    staging_root = destination.parent / f".{destination.name}.{command_id}.stage"
    temp_root = tmp_path / "registry-temp"
    for root in (runtime_root, temp_root):
        root.mkdir(exist_ok=True)
    return EvidenceStoreRegistry(
        store_id="evidence-store:test",
        registry_hash=sha256_hex(canonical_bytes({"registry": "wp64-create-backup-test"})),
        policy_revision="test-v1",
        primary_root=binding.control_root,
        runtime_root=runtime_root,
        staging_root=staging_root,
        temp_root=temp_root,
        replicas=(),
        permitted_consumers=("restore-verifier",),
        retention_policy_ids=("test-retention",),
        verifier_authority_bindings=((ACTOR_ID, GRANT_ID),),
        unregistered_replicas_prohibited=True,
        backup_roots=(destination,),
        restore_roots=(),
    )


def test_store_restore_bind_preserves_optional_separate_spec_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public bind command passes external SPEC authority only to replay preflight."""

    code_root = tmp_path / "code"
    schema_root = code_root / ".research-system" / "schemas"
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    for directory in (schema_root, source_root, target_root):
        directory.mkdir(parents=True, exist_ok=True)
    approved = SimpleNamespace(
        control_root=source_root,
        project_id=PROJECT_ID,
        store_identity="a" * 64,
        endpoint_scheme="local-cli",
        code_roots=(code_root,),
        schema_root=schema_root,
        origin_witness="origin-witness",
        origin_witness_path=tmp_path / "origin-witness.json",
        origin_witness_sha256="b" * 64,
    )
    receipt = SimpleNamespace(
        project_id=PROJECT_ID,
        store_identity=approved.store_identity,
        source_endpoint_scheme=approved.endpoint_scheme,
        receipt_hash="c" * 64,
    )
    external_authority = object()
    preflight_calls: list[object | None] = []
    requires_external_authority = True

    def preflight(**kwargs: object) -> object:
        resolver = kwargs["authority_resolver"]
        preflight_calls.append(resolver)
        verified = resolver is external_authority or not requires_external_authority
        return SimpleNamespace(
            status="verified" if verified else "unverified",
            failed_predicates=() if verified else ("external_spec_authority_required",),
            source_snapshot_hash="d" * 64,
            target_manifest_bytes_sha256="e" * 64,
            result_hash="f" * 64,
        )

    def resolver_from_config(path: Path, **kwargs: object) -> object:
        assert kwargs == {
            "project_id": PROJECT_ID,
            "schemas": schemas,
            "expected_schema_root": schema_root,
        }
        if path.name == "mismatched-authority.json":
            raise ConfigurationError("authority binding project differs from the replayed control store")
        return external_authority

    schemas = object()
    monkeypatch.setattr(cli, "_load_canonical_approved_binding", lambda _path: approved)
    monkeypatch.setattr(cli, "runtime_schema_registry", lambda _path: schemas)
    monkeypatch.setattr(cli, "require_authority_schemas", lambda value: value)
    monkeypatch.setattr(cli, "_backup_receipt_from_json", lambda _value: receipt)
    monkeypatch.setattr(cli, "_read_canonical_json", lambda _path: {"snapshot_id": "snapshot"})
    monkeypatch.setattr(cli, "canonical_restore_binding_output", lambda *_args: b"bound-config\n")
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda *_args: object())
    monkeypatch.setattr(cli, "verify_restore_before_writer_lease", preflight)
    monkeypatch.setattr(cli, "_authority_resolver_from_config", resolver_from_config)
    monkeypatch.setattr(cli, "asdict", lambda _value: {"status": "verified"})
    monkeypatch.setattr(cli, "rebind_restored_store", lambda *_args, **_kwargs: {"manifest_hash": "a" * 64})

    def command(config_output: Path, authority_config: Path | None = None) -> list[str]:
        argv = [
            "store",
            "restore-bind",
            "--control-root",
            str(target_root),
            "--source-root",
            str(source_root),
            "--receipt",
            str(tmp_path / "receipt.json"),
            "--snapshot",
            str(tmp_path / "snapshot.json"),
            "--endpoint-ownership",
            str(tmp_path / "endpoint.json"),
            "--artefact-manifest",
            str(tmp_path / "artefacts.json"),
            "--registry",
            str(tmp_path / "registry.json"),
            "--actor-id",
            ACTOR_ID,
            "--authority-grant-id",
            GRANT_ID,
            "--foundation-config",
            str(tmp_path / "foundation.yaml"),
            "--schema-root",
            str(schema_root),
            "--config-output",
            str(config_output),
        ]
        if authority_config is not None:
            argv.extend(("--authority-config", str(authority_config)))
        return argv

    external_output = tmp_path / "external-binding.json"
    assert cli.main(command(external_output, tmp_path / "external-authority.json")) == 0
    assert preflight_calls == [external_authority]
    assert external_output.read_bytes() == b"bound-config\n"
    capsys.readouterr()

    missing_output = tmp_path / "missing-binding.json"
    with pytest.raises(ArsError, match="external_spec_authority_required"):
        cli.main(command(missing_output))
    assert preflight_calls[-1] is None
    assert not missing_output.exists()

    calls_before_mismatch = len(preflight_calls)
    with pytest.raises(ConfigurationError, match="authority binding project differs"):
        cli.main(command(tmp_path / "mismatched-binding.json", tmp_path / "mismatched-authority.json"))
    assert len(preflight_calls) == calls_before_mismatch

    requires_external_authority = False
    same_root_output = tmp_path / "same-root-binding.json"
    assert cli.main(command(same_root_output)) == 0
    assert preflight_calls[-1] is None
    assert same_root_output.read_bytes() == b"bound-config\n"


def test_restore_replay_authorities_keep_local_administration_distinct_from_external_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_root = tmp_path / "restored-store"
    external_root = tmp_path / "spec-authority-store"
    local_root.mkdir()
    external_root.mkdir()
    constructed: list[SimpleNamespace] = []

    def local_resolver(control_root: Path, *args: object, **kwargs: object) -> SimpleNamespace:
        value = SimpleNamespace(
            control_root=control_root,
            project_id=args[0],
            expected_store_identity=args[1],
            restore_source_alias=kwargs["restore_source_alias"],
        )
        constructed.append(value)
        return value

    external = SimpleNamespace(
        control_root=external_root,
        project_id=PROJECT_ID,
        expected_store_identity="external-store-identity",
    )
    monkeypatch.setattr(backups_module, "LedgerAuthorityGrantResolver", local_resolver)

    local, spec = backups_module._store_replay_authorities(
        control_root=local_root,
        project_id=PROJECT_ID,
        store_identity="restored-store-identity",
        schemas=object(),
        approved_witness=object(),
        approved_witness_path=tmp_path / "origin-witness.json",
        restore_source_alias=True,
        spec_authority_resolver=external,
    )

    assert spec is external
    assert local.control_root == local_root
    assert local.project_id == PROJECT_ID
    assert local.expected_store_identity == "restored-store-identity"
    assert local.restore_source_alias is True
    assert constructed == [local]

    with pytest.raises(IntegrityError, match="identity differs from the local store"):
        backups_module._store_replay_authorities(
            control_root=local_root,
            project_id=PROJECT_ID,
            store_identity="restored-store-identity",
            schemas=object(),
            approved_witness=object(),
            approved_witness_path=tmp_path / "origin-witness.json",
            restore_source_alias=True,
            spec_authority_resolver=SimpleNamespace(
                control_root=local_root,
                project_id=PROJECT_ID,
                expected_store_identity="wrong-local-store-identity",
            ),
        )


@pytest.mark.integration
def test_store_verify_restore_appends_evidence_without_cutover_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    binding, ledger = _activate_backup_grant(tmp_path)
    destination = tmp_path / "backup"
    artefact_path = tmp_path / "external-evidence.bin"
    artefact_path.write_bytes(b"owner-approved external evidence\n")
    registry = _registry(tmp_path, binding, destination)
    request = {
        "command_id": BACKUP_COMMAND_ID,
        "receipt_id": BACKUP_RECEIPT_ID,
        "receipt_revision": 1,
        "submitted_at": "2026-08-10T18:30:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": "wp61-r1:create-backup",
        "correlation_id": "wp61-r1",
        "causation_id": None,
        "reason": "create the governed R1 backup",
        "evidence_refs": ["evidence:external-availability"],
        "snapshot_id": "snapshot-wp61-r1",
        "schema_versions": ["ars-core@1.0.0"],
        "tool_versions": ["tdl@1.0.0"],
        "encryption_class": "test-owner-approved",
        "redaction_class": "test-owner-approved",
        "destination_class": "test-local-control-copy",
        "verified_at": "2026-08-10T18:30:00Z",
        "verified_by_actor_id": ACTOR_ID,
        "verification_authority_grant_id": GRANT_ID,
        "external_artefacts": [
            {
                "artefact_id": ARTEFACT_ID,
                "source_path": str(artefact_path.resolve()),
                "content_sha256": sha256_hex(artefact_path.read_bytes()),
                "availability": "available",
                "availability_evidence_refs": ["evidence:external-availability"],
                "observed_at": "2026-08-10T18:30:00Z",
            }
        ],
    }
    request_path = tmp_path / "backup-request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda _path, _schemas: registry)
    assert (
        cli.main(
            [
                "store",
                "backup",
                "--config",
                str(tmp_path / "binding.json"),
                "--request",
                str(request_path),
                "--registry",
                str(tmp_path / "registry.yaml"),
                "--destination-root",
                str(destination.resolve()),
            ]
        )
        == 0
    )
    backup_output = json.loads(capsys.readouterr().out)
    backup_receipt = backup_output["backup_receipt"]
    restore_registry = EvidenceStoreRegistry(
        store_id="evidence-store:restore-test",
        registry_hash=backup_receipt["evidence_registry_hash"],
        policy_revision="test-v1",
        primary_root=destination / "evidence-primary",
        runtime_root=destination / "evidence-runtime",
        staging_root=destination / "evidence-staging",
        temp_root=destination / "evidence-temp",
        replicas=(),
        permitted_consumers=("restore-verifier",),
        retention_policy_ids=("test-retention",),
        verifier_authority_bindings=((ACTOR_ID, GRANT_ID),),
        unregistered_replicas_prohibited=True,
        backup_roots=(binding.control_root,),
        restore_roots=(destination,),
    )
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda _path, _schemas: restore_registry)
    endpoint_path = destination / "manifests" / "endpoint-ownership.json"
    endpoint_path.write_bytes(
        canonical_bytes(
            {
                "target_root": str(destination.resolve(strict=False)),
                "endpoint_scheme": backup_receipt["source_endpoint_scheme"],
                "owner_actor_id": ACTOR_ID,
                "authority_grant_id": GRANT_ID,
                "observed_at": "2026-08-10T18:30:00Z",
            }
        )
    )
    target_ledger = EventLedger(destination, PROJECT_ID, runtime_schema_registry(binding.schema_root)).snapshot()
    supported_schema_ids = sorted({event["schema_id"] for event in target_ledger.events})
    from research_system.operations.backups import verify_restore_before_writer_lease

    preflight = verify_restore_before_writer_lease(
        target_root=destination,
        receipt=cli._backup_receipt_from_json(backup_receipt),
        snapshot_path=Path(backup_output["snapshot_path"]),
        endpoint_ownership_path=endpoint_path,
        artefact_manifest_path=destination / "manifests" / "external-artefacts.json",
        registry=restore_registry,
        actor_id=ACTOR_ID,
        authority_grant_id=GRANT_ID,
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    assert preflight.failed_predicates == ()
    assert preflight.status == "verified"
    command = {
        "command_id": VERIFY_COMMAND_ID,
        "command_type": "VerifyRestore",
        "schema_id": "ars://core/command/VerifyRestore",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-10T18:31:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": GRANT_ID,
        "target_stream_id": PROJECT_ID,
        "expected_stream_version": ledger.snapshot().stream_versions[PROJECT_ID],
        "idempotency_key": "wp61-r1:verify-restore",
        "correlation_id": "wp61-r1",
        "causation_id": BACKUP_COMMAND_ID,
        "reason": "record evidence-only restore verification",
        "evidence_refs": [preflight.result_hash],
        "payload": {
            "project_id": PROJECT_ID,
            "backup_receipt_id": BACKUP_RECEIPT_ID,
            "store_identity": binding.store_identity,
            "canonical_tail_position": preflight.tail_position,
            "canonical_tail_sha256": preflight.tail_hash,
            "hash_chain_verified": True,
            "snapshot_replay_verified": True,
            "endpoint_ownership_verified": True,
            "supported_schema_ids": supported_schema_ids,
            "external_artefacts": [
                {
                    "artefact_id": ARTEFACT_ID,
                    "content_sha256": sha256_hex(artefact_path.read_bytes()),
                    "availability": "available",
                    "availability_evidence_refs": [preflight.result_hash],
                }
            ],
            "verified_at": backup_receipt["verified_at"],
            "recovery_evidence_id": RECOVERY_EVIDENCE_ID,
        },
        "project_id": PROJECT_ID,
    }
    command_path = tmp_path / "verify-restore-command.json"
    command_path.write_text(json.dumps(command), encoding="utf-8")
    target_before = {
        str(path.relative_to(destination)): path.read_bytes() for path in destination.rglob("*") if path.is_file()
    }
    source_before_late_change = ledger.snapshot()
    receipts_before_late_change = {
        str(path.relative_to(binding.control_root)): path.read_bytes()
        for path in (binding.control_root / "receipts").rglob("*")
        if path.is_file()
    }
    endpoint_bytes = endpoint_path.read_bytes()
    changed = False

    def change_target_after_preflight(_service: CommandService, _command: Any) -> None:
        nonlocal changed
        if not changed:
            changed = True
            endpoint_path.write_bytes(endpoint_bytes + b" ")

    with monkeypatch.context() as late_change:
        late_change.setattr(
            CommandService,
            "_before_restore_verification_revalidation",
            change_target_after_preflight,
        )
        with pytest.raises(IntegrityError, match="changed after full preflight"):
            cli.main(
                [
                    "store",
                    "verify-restore",
                    "--config",
                    str(tmp_path / "binding.json"),
                    "--command",
                    str(command_path),
                    "--target-root",
                    str(destination),
                    "--receipt",
                    str(destination / "manifests" / "backup-receipt.json"),
                    "--snapshot",
                    backup_output["snapshot_path"],
                    "--endpoint-ownership",
                    str(endpoint_path),
                    "--artefact-manifest",
                    str(destination / "manifests" / "external-artefacts.json"),
                    "--registry",
                    str(tmp_path / "registry.yaml"),
                ]
            )
    endpoint_path.write_bytes(endpoint_bytes)
    assert ledger.snapshot() == source_before_late_change
    assert receipts_before_late_change == {
        str(path.relative_to(binding.control_root)): path.read_bytes()
        for path in (binding.control_root / "receipts").rglob("*")
        if path.is_file()
    }
    assert not list(destination.rglob("*.lock"))
    assert (
        cli.main(
            [
                "store",
                "verify-restore",
                "--config",
                str(tmp_path / "binding.json"),
                "--command",
                str(command_path),
                "--target-root",
                str(destination),
                "--receipt",
                str(destination / "manifests" / "backup-receipt.json"),
                "--snapshot",
                backup_output["snapshot_path"],
                "--endpoint-ownership",
                str(endpoint_path),
                "--artefact-manifest",
                str(destination / "manifests" / "external-artefacts.json"),
                "--registry",
                str(tmp_path / "registry.yaml"),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "accepted"
    assert output["verification_only"] is True
    assert output["cutover_authorized"] is False
    after = ledger.snapshot()
    event = [item for item in after.events if item.get("command_id") == VERIFY_COMMAND_ID]
    assert len(event) == 1 and event[0]["event_type"] == "RestoreVerified"
    replay_schemas = runtime_schema_registry(binding.schema_root)
    replay_resolver = LedgerAuthorityGrantResolver(
        binding.control_root,
        binding.project_id,
        binding.store_identity,
        replay_schemas,
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    replayed = replay(
        after.events,
        schema_registry=replay_schemas,
        authority_state_validator=replay_resolver.validate_replayed_administration_state,
    )
    assert replayed["streams"][PROJECT_ID]["restore_verifications"][RECOVERY_EVIDENCE_ID]["cutover_authorized"] is False
    assert target_before == {
        str(path.relative_to(destination)): path.read_bytes() for path in destination.rglob("*") if path.is_file()
    }
    assert not list(destination.rglob("*.lock"))

    bypass = {
        **command,
        "command_id": "cmd_01978abc-7709-7000-8000-000000007709",
        "idempotency_key": "wp61-r1:verify-restore-bypass",
        "expected_stream_version": after.stream_versions[PROJECT_ID],
    }
    bypass_path = tmp_path / "generic-verify-restore-command.json"
    bypass_path.write_text(json.dumps(bypass), encoding="utf-8")
    source_before = ledger.snapshot()
    receipts_before = {
        str(path.relative_to(binding.control_root)): path.read_bytes()
        for path in (binding.control_root / "receipts").rglob("*")
        if path.is_file()
    }
    with pytest.raises(ArsError, match="governed restore verification provider"):
        cli.main(["command", "submit", "--config", str(tmp_path / "binding.json"), "--command", str(bypass_path)])
    assert ledger.snapshot() == source_before
    assert receipts_before == {
        str(path.relative_to(binding.control_root)): path.read_bytes()
        for path in (binding.control_root / "receipts").rglob("*")
        if path.is_file()
    }


@pytest.mark.integration
def test_store_backup_cli_is_event_first_retryable_and_not_available_via_generic_submit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    binding, ledger = _activate_backup_grant(tmp_path)
    destination = tmp_path / "backup"
    artefact_path = tmp_path / "external-evidence.bin"
    artefact_path.write_bytes(b"owner-approved external evidence\n")
    registry = _registry(tmp_path, binding, destination)
    request = {
        "command_id": BACKUP_COMMAND_ID,
        "receipt_id": BACKUP_RECEIPT_ID,
        "receipt_revision": 1,
        "submitted_at": "2026-08-05T08:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": "wp64-create-backup:test",
        "correlation_id": "wp64-create-backup:test",
        "causation_id": None,
        "reason": "exercise the governed event-first backup seam",
        "evidence_refs": ["evidence:external-availability"],
        "snapshot_id": "snapshot-wp64-create-backup-test",
        "schema_versions": ["ars-core@1.0.0"],
        "tool_versions": ["tdl@1.0.0"],
        "encryption_class": "test-owner-approved",
        "redaction_class": "test-owner-approved",
        "destination_class": "test-local-control-copy",
        "verified_at": "2026-08-05T08:00:00Z",
        "verified_by_actor_id": ACTOR_ID,
        "verification_authority_grant_id": GRANT_ID,
        "external_artefacts": [
            {
                "artefact_id": ARTEFACT_ID,
                "source_path": str(artefact_path.resolve()),
                "content_sha256": sha256_hex(artefact_path.read_bytes()),
                "availability": "available",
                "availability_evidence_refs": ["evidence:external-availability"],
                "observed_at": "2026-08-05T08:00:00Z",
            }
        ],
    }
    request_path = tmp_path / "backup-request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda _path, _schemas: registry)
    arguments = [
        "store",
        "backup",
        "--config",
        str(tmp_path / "binding.json"),
        "--request",
        str(request_path),
        "--registry",
        str(tmp_path / "registry.yaml"),
        "--destination-root",
        str(destination.resolve()),
    ]
    before = ledger.snapshot()
    original_materialize = cli.BackupMaterializer.materialize
    failed_once = False

    def interrupt_after_event(self, command, committed_event):
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise RuntimeError("injected post-event backup interruption")
        return original_materialize(self, command, committed_event)

    monkeypatch.setattr(cli.BackupMaterializer, "materialize", interrupt_after_event)

    with pytest.raises(RuntimeError, match="injected post-event backup interruption"):
        cli.main(arguments)
    capsys.readouterr()
    event_only = ledger.snapshot()
    assert event_only.global_position == before.global_position + 1
    assert not destination.exists()
    assert (destination.parent / f".{destination.name}.{BACKUP_COMMAND_ID}.stage").is_dir()

    monkeypatch.setattr(cli.BackupMaterializer, "materialize", original_materialize)
    assert cli.main(arguments) == 0
    first = json.loads(capsys.readouterr().out)
    after = ledger.snapshot()

    created = [event for event in after.events if event.get("command_id") == BACKUP_COMMAND_ID]
    assert len(created) == 1
    assert created[0]["event_type"] == "BackupCreated"
    assert created[0]["payload"]["canonical_tail_position"] == before.global_position
    assert created[0]["payload"]["canonical_tail_sha256"] == before.event_hash
    assert after.global_position == event_only.global_position
    assert destination.is_dir()
    assert not (destination.parent / f".{destination.name}.{BACKUP_COMMAND_ID}.stage").exists()
    assert first["backup_receipt"]["receipt_id"] == BACKUP_RECEIPT_ID
    assert (
        EventLedger(destination, PROJECT_ID, runtime_schema_registry(binding.schema_root)).snapshot().global_position
        == before.global_position
    )

    assert cli.main(arguments) == 0
    retry = json.loads(capsys.readouterr().out)
    assert retry["backup_receipt"] == first["backup_receipt"]
    assert ledger.snapshot().global_position == after.global_position

    event_payload = created[0]["payload"]
    command_path = tmp_path / "generic-create-backup-command.json"
    command_path.write_text(
        json.dumps(
            {
                "command_id": request["command_id"],
                "command_type": "CreateBackup",
                "schema_id": "ars://core/command/CreateBackup",
                "schema_version": "1.0.0",
                "submitted_at": request["submitted_at"],
                "actor_id": request["actor_id"],
                "on_behalf_of_actor_id": request["on_behalf_of_actor_id"],
                "authority_grant_id": request["authority_grant_id"],
                "target_stream_id": PROJECT_ID,
                "expected_stream_version": created[0]["stream_version"] - 1,
                "idempotency_key": request["idempotency_key"],
                "correlation_id": request["correlation_id"],
                "causation_id": request["causation_id"],
                "reason": request["reason"],
                "evidence_refs": request["evidence_refs"],
                "payload": event_payload,
                "project_id": PROJECT_ID,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ArsError, match="governed backup materializer"):
        cli.main(
            [
                "command",
                "submit",
                "--config",
                str(tmp_path / "binding.json"),
                "--command",
                str(command_path),
            ]
        )
    assert ledger.snapshot().global_position == after.global_position

    duplicate_destination = tmp_path / "duplicate-backup"
    request.update(
        {
            "command_id": DUPLICATE_COMMAND_ID,
            "receipt_id": DUPLICATE_RECEIPT_ID,
            "idempotency_key": "wp64-create-backup:duplicate-snapshot",
            "correlation_id": "wp64-create-backup:duplicate-snapshot",
        }
    )
    request_path.write_text(json.dumps(request), encoding="utf-8")
    registry = _registry(
        tmp_path,
        binding,
        duplicate_destination,
        command_id=DUPLICATE_COMMAND_ID,
    )
    duplicate_arguments = [
        *arguments[:-1],
        str(duplicate_destination.resolve()),
    ]
    assert cli.main(duplicate_arguments) == 0
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["status"] == "rejected"
    assert rejected["command_receipt"]["reason_code"] == "backup_snapshot_identity_conflict"
    assert ledger.snapshot().global_position == after.global_position
    assert not duplicate_destination.exists()
    assert not (duplicate_destination.parent / f".{duplicate_destination.name}.{DUPLICATE_COMMAND_ID}.stage").exists()
