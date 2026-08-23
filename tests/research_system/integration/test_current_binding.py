from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.schema_registry import runtime_schema_registry
from research_system.store.current_binding import _schema_catalogue, load_current_binding
from research_system.store.identity import load_restore_binding_transaction
from research_system.store.ledger import EventLedger, _issue_validated_service_session
from tests.research_system.factories import PROJECT_ID, REPO_ROOT
from tests.research_system.integration.test_restore_recovery_origin_witness import (
    ACTOR_ID,
    _restored_fixture,
)


_ROUTE = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_SOURCES = (
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md"),
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md"),
)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_json(path: Path, value: dict[str, object]) -> bytes:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


@dataclass(frozen=True)
class _Fixture:
    repository_root: Path
    control_root: Path
    foundation_path: Path
    binding: dict[str, object]
    binding_raw: bytes
    schemas: object
    ledger: EventLedger


def _bound_fixture(tmp_path: Path) -> _Fixture:
    initialized, witness, control_root, rebound = _restored_fixture(tmp_path)
    repository_root = tmp_path / "repo"
    schema_root = repository_root / ".research-system" / "schemas"
    for relative in (*_SOURCES, _ROUTE):
        target = repository_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, target)
    foundation = {
        "schema_version": "1.1.0",
        "project_id": PROJECT_ID,
        "control_root": str(control_root.resolve()),
        "store_identity": str(initialized),
        "origin_authority_root": str(initialized.witness_path.parent.parent.resolve()),
        "origin_witness_path": str(initialized.witness_path.resolve()),
        "origin_witness_sha256": witness.raw_sha256,
    }
    foundation["foundation_sha256"] = sha256_hex(canonical_bytes(foundation))
    foundation_path = repository_root / ".research-system/config/foundation.yaml"
    foundation_path.parent.mkdir(parents=True, exist_ok=True)
    foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8")

    _git(repository_root, "init")
    _git(repository_root, "config", "user.email", "gate6@example.invalid")
    _git(repository_root, "config", "user.name", "Gate 6 fixture")
    _git(repository_root, "config", "core.autocrlf", "false")
    _git(repository_root, "add", ".")
    _git(repository_root, "commit", "-m", "fixture")
    head = _git(repository_root, "rev-parse", "HEAD")
    tree = _git(repository_root, "rev-parse", "HEAD^{tree}")
    catalogue_sha256 = _schema_catalogue(repository_root, schema_root, head)

    route_raw = (repository_root / _ROUTE).read_bytes()
    sources = [
        {
            "ref": relative.as_posix(),
            "sha256": sha256_hex((repository_root / relative).read_bytes()),
            "size_bytes": len((repository_root / relative).read_bytes()),
        }
        for relative in _SOURCES
    ]
    restore = load_restore_binding_transaction(control_root)
    assert restore is not None
    payload_hash = sha256_hex(canonical_bytes({"fixture": "current-binding"}))
    common = {
        "schema_id": "ars://internal/store-binding-recovery",
        "project_id": PROJECT_ID,
        "store_identity": str(initialized),
        "control_root": str(control_root.resolve()),
        "code_roots": [str(repository_root.resolve())],
        "schema_root": str(schema_root.resolve()),
        "origin_witness_sha256": witness.raw_sha256,
        "git_head": head,
        "git_tree": tree,
        "git_clean": True,
        "schema_catalogue_sha256": catalogue_sha256,
        "route": {"ref": _ROUTE.as_posix(), "sha256": sha256_hex(route_raw)},
        "sources": sources,
        "stale_evidence": {
            "refs": ["manifests/.restore-binding-transaction.json"],
            "missing_paths": [],
        },
        "command_payload_hash": payload_hash,
        "owner_actor_id": ACTOR_ID,
        "idempotency_key": "gate6-current-binding-fixture",
        "prior_restore_transaction_id": restore["transaction_id"],
        "prior_restore_intended_manifest_sha256": restore["intended_manifest_sha256"],
        "binding_config_path": "manifests/binding-repair-control-binding.json",
    }
    binding_config = {
        "code_roots": common["code_roots"],
        "control_root": common["control_root"],
        "project_id": PROJECT_ID,
        "schema_root": common["schema_root"],
        "store_identity": str(initialized),
    }
    binding_config_raw = _write_json(
        control_root / "manifests/binding-repair-control-binding.json",
        binding_config,
    )
    common["binding_config_sha256"] = sha256_hex(binding_config_raw)
    predecessor = {
        **common,
        "schema_version": "1.0.0",
        "owner_action": "repair-stale-store-binding",
    }
    predecessor_raw = canonical_bytes(predecessor)
    predecessor_sha256 = sha256_hex(predecessor_raw)
    object_root = control_root / "objects" / "binding-repair"
    object_root.mkdir(parents=True, exist_ok=True)
    (object_root / f"sha256-{predecessor_sha256}.json").write_bytes(predecessor_raw)
    binding: dict[str, object] = {
        **common,
        "schema_version": "1.1.0",
        "owner_action": "advance-clean-descendant-store-binding",
        "predecessor_binding_sha256": predecessor_sha256,
    }
    binding_raw = canonical_bytes(binding)
    binding_sha256 = sha256_hex(binding_raw)
    (object_root / f"sha256-{binding_sha256}.json").write_bytes(binding_raw)

    schemas = runtime_schema_registry(schema_root)
    ledger = EventLedger(control_root, PROJECT_ID, schemas, store_identity=str(initialized))
    command = schemas.command_binding("AdvanceStoreBinding")
    assert command is not None
    command_identity = schemas.resolve_identity(command.schema_id, command.schema_version)
    result = ledger._append_binding_repair_from_validated_service(
        {
            "event_type": "StoreBindingAdvanced",
            "stream_id": PROJECT_ID,
            "schema_id": "ars://wp6-6/gate6/binding-repair/event/StoreBindingAdvanced",
            "schema_version": "1.0.0",
            "command_id": f"binding-advance-{payload_hash}",
            "command_type": "AdvanceStoreBinding",
            "idempotency_key": common["idempotency_key"],
            "command_payload_hash": payload_hash,
            "correlation_id": common["idempotency_key"],
            "causation_id": None,
            "actor_id": ACTOR_ID,
            "authority_grant_id": "store-binding-recovery",
            "occurred_at": "2026-08-23T12:00:00Z",
            "command_schema_id": command_identity.schema_id,
            "command_schema_version": command_identity.schema_version,
            "command_schema_sha256": command_identity.sha256,
            "payload": {
                "recovery_binding_sha256": binding_sha256,
                "recovery_binding_path": "manifests/binding-repair-current.json",
                "object_path": f"objects/binding-repair/sha256-{binding_sha256}.json",
                "git_head": head,
                "git_tree": tree,
                "predecessor_binding_sha256": predecessor_sha256,
            },
        },
        snapshot=ledger.snapshot(),
        session=_issue_validated_service_session(ledger),
    )
    observed_version = result["resulting_stream_versions"][PROJECT_ID]
    receipt = {
        "schema_id": "ars://core/receipt",
        "schema_version": "1.0.0",
        "command_id": f"binding-advance-{payload_hash}",
        "status": "accepted",
        "payload_hash": payload_hash,
        "outcome": {
            "event_batch_id": result["event_batch_id"],
            "observed_stream_version": observed_version,
            "reason_code": None,
        },
    }
    _write_json(control_root / "receipts" / f"binding-advance-{payload_hash}.json", receipt)
    scope = [ACTOR_ID, "store-binding-recovery", "AdvanceStoreBinding", common["idempotency_key"]]
    authority_hash = sha256_hex(canonical_bytes({"actor_id": ACTOR_ID, "action": binding["owner_action"]}))
    _write_json(
        control_root / "receipts" / "idempotency" / f"{sha256_hex(canonical_bytes(scope))}.json",
        {
            "schema_id": "ars://core/authority-receipt-index",
            "schema_version": "1.2.0",
            "scope": scope,
            "payload_hash": payload_hash,
            "authority_grant_sha256": authority_hash,
            "receipt": receipt,
            "project_id": PROJECT_ID,
            "target_stream_id": PROJECT_ID,
            "expected_stream_version": 0,
        },
    )
    _write_json(control_root / "manifests/binding-repair-current.json", binding)
    assert rebound["code_roots"] == [str(repository_root.resolve())]
    return _Fixture(
        repository_root=repository_root.resolve(),
        control_root=control_root.resolve(),
        foundation_path=foundation_path,
        binding=binding,
        binding_raw=binding_raw,
        schemas=schemas,
        ledger=ledger,
    )


def test_current_binding_loads_exact_subject_and_fails_closed_on_drift(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    verified = load_current_binding(
        foundation_path=fixture.foundation_path,
        repository_root=fixture.repository_root,
        expected_control_root=fixture.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=str(fixture.binding["store_identity"]),
    )
    assert verified.binding_sha256 == sha256_hex(fixture.binding_raw)

    untracked = fixture.repository_root / "drift.txt"
    untracked.write_text("drift", encoding="utf-8")
    with pytest.raises(IntegrityError, match="repository is dirty"):
        verified.revalidate()
    untracked.unlink()

    pointer = fixture.control_root / "manifests/binding-repair-current.json"
    changed = {**fixture.binding, "git_tree": "0" * 40}
    pointer.write_bytes(canonical_bytes(changed))
    with pytest.raises((ConflictError, IntegrityError)):
        verified.revalidate()


def test_binding_events_require_the_validated_service_continuation(tmp_path: Path) -> None:
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    ledger = EventLedger(tmp_path / "control", PROJECT_ID, schemas, store_identity="a" * 64)
    command = schemas.command_binding("AdvanceStoreBinding")
    assert command is not None
    identity = schemas.resolve_identity(command.schema_id, command.schema_version)
    with pytest.raises(ArsError, match="validated repair-service continuation"):
        ledger.append(
            [
                {
                    "event_type": "StoreBindingAdvanced",
                    "stream_id": PROJECT_ID,
                    "schema_id": "ars://wp6-6/gate6/binding-repair/event/StoreBindingAdvanced",
                    "schema_version": "1.0.0",
                    "command_id": "binding-advance-" + "b" * 64,
                    "command_type": "AdvanceStoreBinding",
                    "idempotency_key": "binding-event-direct-append",
                    "command_payload_hash": "b" * 64,
                    "correlation_id": "binding-event-direct-append",
                    "causation_id": None,
                    "actor_id": ACTOR_ID,
                    "authority_grant_id": "store-binding-recovery",
                    "occurred_at": "2026-08-23T12:00:00Z",
                    "command_schema_id": identity.schema_id,
                    "command_schema_version": identity.schema_version,
                    "command_schema_sha256": identity.sha256,
                    "payload": {},
                }
            ]
        )
    assert tuple(ledger.iter_events()) == ()
