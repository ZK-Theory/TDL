from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ArsError, ConfigurationError, ConflictError, IntegrityError
from research_system.ids import new_id
from research_system.schema_registry import runtime_schema_registry
from research_system.store.binding_service import (
    ADVANCE_COMMAND_SCHEMA_ID,
    AdvanceStoreBinding,
    RepairStoreBinding,
    StoreBindingService,
    read_advance_intent,
    read_repair_intent,
)
from research_system.store.current_binding import _schema_catalogue, load_current_binding
from research_system.store.ledger import EventLedger
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import PROJECT_ID, REPO_ROOT
from tests.research_system.integration.test_restore_recovery_origin_witness import _restored_fixture


_ROUTE = ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json"
_SOURCES = (
    ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
    ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
)
_NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True)


def _git_text(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def _candidate(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "research_system", root / "research_system")
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas", root / ".research-system" / "schemas")
    shutil.copytree(REPO_ROOT / ".research-system" / "contracts", root / ".research-system" / "contracts")
    for name in (".python-version", "pyproject.toml", "uv.lock"):
        shutil.copyfile(REPO_ROOT / name, root / name)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "gate6@example.invalid")
    _git(root, "config", "user.name", "Gate 6")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "remote", "add", "origin", "https://example.invalid/gate6.git")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "candidate")
    return root.resolve()


def _service_fixture(tmp_path: Path, *, stale: bool) -> tuple[StoreBindingService, RepairStoreBinding, Path]:
    initialized, witness, control, _rebound = _restored_fixture(
        tmp_path,
        include_retired_code_root=stale,
    )
    candidate = _candidate(tmp_path)
    bootstrap = json.loads((control / "manifests" / "authority-bootstrap.json").read_text(encoding="utf-8"))
    owner_actor_id = str(bootstrap["owner_actor_id"])
    intent = RepairStoreBinding(
        control.resolve(),
        candidate,
        PROJECT_ID,
        str(initialized),
        initialized.witness_path.parent.parent.resolve(),
        witness.raw_sha256,
        candidate / ".research-system" / "schemas",
        ("manifests/.restore-binding-transaction.json",),
        _ROUTE,
        _SOURCES,
        "2026-08-24T11:00:00Z",
        "2026-08-24T13:00:00Z",
        owner_actor_id,
        "repair-stale-store-binding",
        "repair-idempotency-1",
        "repair the unavailable historical store root",
    )
    return StoreBindingService(control, PROJECT_ID, str(initialized), now=lambda: _NOW), intent, candidate


def test_repair_publishes_once_recovers_retry_and_rejects_direct_ledger_append(tmp_path: Path) -> None:
    service, intent, candidate = _service_fixture(tmp_path, stale=True)

    first = service.repair(intent)
    second = service.repair(intent)

    assert first["status"] == second["status"] == "repaired"
    assert first["binding_sha256"] == second["binding_sha256"]
    assert (service.control_root / "manifests" / "binding-repair-current.json").is_file()
    assert not (service.control_root / "runtime" / ".binding-repair-transaction.json").exists()
    schemas = runtime_schema_registry(candidate / ".research-system" / "schemas")
    ledger = EventLedger(service.control_root, PROJECT_ID, schemas, store_identity=service.store_identity)
    command = schemas.resolve_identity("ars://wp6-6/gate6/binding-repair/command/RepairStoreBinding", "1.0.0")
    with pytest.raises(ArsError, match="validated repair-service continuation"):
        ledger.append(
            [
                {
                    "event_type": "StoreBindingRepaired",
                    "stream_id": PROJECT_ID,
                    "schema_id": "ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired",
                    "schema_version": "1.0.0",
                    "command_type": "RepairStoreBinding",
                    "command_schema_id": command.schema_id,
                    "command_schema_version": command.schema_version,
                    "command_schema_sha256": command.sha256,
                }
            ]
        )


def test_repair_rejects_a_nonstale_store(tmp_path: Path) -> None:
    service, intent, _candidate_root = _service_fixture(tmp_path, stale=False)

    with pytest.raises(ConflictError, match="demonstrably stale"):
        service.repair(intent)


def test_repair_rejects_an_origin_authority_root_that_does_not_own_the_witness(tmp_path: Path) -> None:
    service, intent, _candidate_root = _service_fixture(tmp_path, stale=True)

    with pytest.raises(IntegrityError, match="origin authority"):
        service.repair(replace(intent, expected_origin_authority_root=tmp_path.resolve()))


def _admitted_legacy_predecessor(tmp_path: Path) -> tuple[StoreBindingService, RepairStoreBinding, Path, str]:
    """Create the actual v1.0 repair -> v1.1 advance history admission expects."""

    initialized, witness, control, _rebound = _restored_fixture(tmp_path, include_retired_code_root=True)
    candidate = _candidate(tmp_path)
    foundation = {
        "schema_version": "1.1.0",
        "project_id": PROJECT_ID,
        "control_root": str(control.resolve()),
        "store_identity": str(initialized),
        "origin_authority_root": str(initialized.witness_path.parent.parent.resolve()),
        "origin_witness_path": str(initialized.witness_path.resolve()),
        "origin_witness_sha256": witness.raw_sha256,
    }
    foundation["foundation_sha256"] = sha256_hex(canonical_bytes(foundation))
    foundation_path = candidate / ".research-system" / "config" / "foundation.yaml"
    foundation_path.parent.mkdir(parents=True, exist_ok=True)
    foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-m", "foundation")

    bootstrap = (control / "manifests" / "authority-bootstrap.json").read_bytes()
    owner_actor_id = str(json.loads(bootstrap)["owner_actor_id"])
    repair = RepairStoreBinding(
        control.resolve(),
        candidate,
        PROJECT_ID,
        str(initialized),
        initialized.witness_path.parent.parent.resolve(),
        witness.raw_sha256,
        candidate / ".research-system" / "schemas",
        ("manifests/.restore-binding-transaction.json",),
        _ROUTE,
        _SOURCES,
        "2026-08-24T11:00:00Z",
        "2026-08-24T13:00:00Z",
        owner_actor_id,
        "repair-stale-store-binding",
        "admitted-repair-intent",
        "repair the unavailable historical store root",
    )
    service = StoreBindingService(
        control, PROJECT_ID, str(initialized), now=lambda: _NOW, foundation_path=foundation_path
    )
    repaired = service.repair(repair)
    predecessor = repaired["binding"]
    predecessor_sha256 = str(repaired["binding_sha256"])

    (candidate / "docs").mkdir()
    (candidate / "docs" / "legacy-binding.md").write_text("legacy binding\n", encoding="utf-8")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-m", "legacy documentation")
    head = _git_text(candidate, "rev-parse", "HEAD")
    tree = _git_text(candidate, "rev-parse", "HEAD^{tree}")
    schemas = runtime_schema_registry(candidate / ".research-system" / "schemas")
    payload_hash = sha256_hex(canonical_bytes({"fixture": "admitted-legacy-v1.1"}))
    legacy = {
        **predecessor,
        "schema_version": "1.1.0",
        "git_head": head,
        "git_tree": tree,
        "schema_catalogue_sha256": _schema_catalogue(candidate, candidate / ".research-system" / "schemas", head),
        "command_payload_hash": payload_hash,
        "owner_action": "advance-clean-descendant-store-binding",
        "idempotency_key": "admitted-legacy-v1-1",
        "predecessor_binding_sha256": predecessor_sha256,
    }
    schemas.validate("ars://wp6-6/gate6/binding-repair/object/StoreBindingAdvance", legacy, schema_version="1.1.0")
    legacy_raw = canonical_bytes(legacy)
    legacy_sha256 = sha256_hex(legacy_raw)
    (control / "objects" / "binding-repair" / f"sha256-{legacy_sha256}.json").write_bytes(legacy_raw)

    ledger = EventLedger(control, PROJECT_ID, schemas, store_identity=str(initialized))
    snapshot = ledger.snapshot()
    command = schemas.resolve_identity(ADVANCE_COMMAND_SCHEMA_ID, "1.1.0")
    event = {
        "event_id": new_id("event"),
        "event_type": "StoreBindingAdvanced",
        "schema_id": "ars://wp6-6/gate6/binding-repair/event/StoreBindingAdvanced",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "stream_id": PROJECT_ID,
        "stream_version": snapshot.stream_versions[PROJECT_ID] + 1,
        "global_position": snapshot.global_position + 1,
        "transaction_id": new_id("event_batch"),
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": f"binding-advance-{payload_hash}",
        "command_type": "AdvanceStoreBinding",
        "command_schema_id": command.schema_id,
        "command_schema_version": command.schema_version,
        "command_schema_sha256": command.sha256,
        "idempotency_key": legacy["idempotency_key"],
        "command_payload_hash": payload_hash,
        "correlation_id": legacy["idempotency_key"],
        "causation_id": None,
        "actor_id": owner_actor_id,
        "authority_grant_id": "store-binding-recovery",
        "occurred_at": "2026-08-24T12:00:00Z",
        "recorded_at": "2026-08-24T12:00:00Z",
        "payload": {
            "recovery_binding_sha256": legacy_sha256,
            "recovery_binding_path": "manifests/binding-repair-current.json",
            "object_path": f"objects/binding-repair/sha256-{legacy_sha256}.json",
            "git_head": head,
            "git_tree": tree,
            "predecessor_binding_sha256": predecessor_sha256,
        },
        "previous_event_hash": snapshot.event_hash,
    }
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    event_path = (
        control
        / "events"
        / PROJECT_ID
        / "2026"
        / "08"
        / f"{event['global_position']:020d}-{event['transaction_id']}.jsonl"
    )
    event_path.parent.mkdir(parents=True, exist_ok=True)
    event_path.write_bytes(canonical_bytes(event) + b"\n")
    receipt = Receipt(
        "accepted",
        f"binding-advance-{payload_hash}",
        payload_hash,
        str(event["transaction_id"]),
        int(event["stream_version"]),
    )
    ReceiptStore(control).write_scoped(
        (owner_actor_id, "store-binding-recovery", "AdvanceStoreBinding", str(legacy["idempotency_key"])),
        sha256_hex(canonical_bytes({"actor_id": owner_actor_id, "action": legacy["owner_action"]})),
        snapshot.stream_versions[PROJECT_ID],
        receipt,
        project_id=PROJECT_ID,
        target_stream_id=PROJECT_ID,
    )
    (control / "manifests" / "binding-repair-current.json").write_bytes(legacy_raw)
    admitted = load_current_binding(
        foundation_path=foundation_path,
        repository_root=candidate,
        expected_control_root=control,
        expected_project_id=PROJECT_ID,
        expected_store_identity=str(initialized),
        expected_binding_sha256=legacy_sha256,
    )
    assert admitted.binding_sha256 == legacy_sha256
    return service, repair, candidate, legacy_sha256


def _reviewed_divergence_intent(
    tmp_path: Path,
) -> tuple[StoreBindingService, AdvanceStoreBinding, Path]:
    service, repair, predecessor_root, predecessor_sha256 = _admitted_legacy_predecessor(tmp_path)
    reviewed = tmp_path / "reviewed"
    # Copy the exact physical worktree so bound SPEC bytes stay byte-identical on Windows.
    shutil.copytree(predecessor_root, reviewed)
    _git(reviewed, "config", "user.email", "gate6@example.invalid")
    _git(reviewed, "config", "user.name", "Gate 6")
    (reviewed / "research_system" / "reviewed_divergence.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(reviewed, "add", ".")
    _git(reviewed, "commit", "-m", "reviewed divergence")
    reviewed = reviewed.resolve()
    head = _git_text(reviewed, "rev-parse", "HEAD")
    from research_system.store.governed_code import build_governed_code_manifest

    manifest = build_governed_code_manifest(reviewed)
    predecessor = load_current_binding(
        foundation_path=predecessor_root / ".research-system" / "config" / "foundation.yaml",
        repository_root=predecessor_root,
        expected_control_root=service.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=service.store_identity,
        expected_binding_sha256=predecessor_sha256,
    )
    intent = AdvanceStoreBinding(
        service.control_root,
        reviewed,
        PROJECT_ID,
        service.store_identity,
        repair.expected_origin_authority_root,
        repair.expected_origin_witness_sha256,
        reviewed / ".research-system" / "schemas",
        "2026-08-24T11:00:00Z",
        "2026-08-24T13:00:00Z",
        repair.owner_actor_id,
        "advance-reviewed-divergence-store-binding",
        "v12-divergence-advance",
        "reviewed governed divergence from the admitted legacy root",
        predecessor_sha256,
        head,
        head,
        "refs/heads/main",
        {
            "predecessor_binding_sha256": predecessor_sha256,
            "predecessor_git_head": predecessor.binding["git_head"],
            "candidate_git_head": head,
            "integration_ref": "refs/heads/main",
            "protected_route_sha256": predecessor.binding["route"]["sha256"],
            "protected_sources_sha256": sha256_hex(canonical_bytes(predecessor.binding["sources"])),
            "governed_code_manifest_sha256": manifest.manifest_sha256,
        },
    )

    return service, intent, reviewed


def _assert_one_binding_event(service: StoreBindingService, command_id: str) -> None:
    assert sum(event.get("command_id") == command_id for event in service.ledger.iter_events()) == 1


def test_first_v1_2_reviewed_divergence_advance_publishes_manifest_and_pointer(tmp_path: Path) -> None:
    service, intent, reviewed = _reviewed_divergence_intent(tmp_path)
    with pytest.raises(IntegrityError, match="origin authority"):
        service.advance(replace(intent, expected_origin_authority_root=tmp_path.resolve()))

    result = service.advance(intent)
    retry = service.advance(intent)

    assert result["status"] == retry["status"] == "advanced"
    assert retry["binding_sha256"] == result["binding_sha256"]
    assert result["binding"]["schema_version"] == "1.2.0"
    assert (
        service.control_root
        / "objects"
        / "governed-code"
        / f"sha256-{result['binding']['governed_code_manifest_sha256']}.json"
    ).is_file()
    assert (service.control_root / "manifests" / "binding-repair-current.json").read_bytes() == canonical_bytes(
        result["binding"]
    )
    admitted = load_current_binding(
        foundation_path=reviewed / ".research-system" / "config" / "foundation.yaml",
        repository_root=reviewed,
        expected_control_root=service.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=service.store_identity,
        expected_binding_sha256=str(result["binding_sha256"]),
    )
    assert admitted.binding_sha256 == result["binding_sha256"]


@pytest.mark.parametrize("crash_phase", ("event", "receipt"))
def test_repair_marker_recovery_replays_partial_publication(tmp_path: Path, crash_phase: str) -> None:
    service, intent, _candidate = _service_fixture(tmp_path, stale=True)
    crashed = False

    def crash(phase: str) -> None:
        nonlocal crashed
        if phase == crash_phase and not crashed:
            crashed = True
            raise OSError("simulated control-store interruption")

    service.phase_hook = crash
    with pytest.raises(OSError, match="simulated control-store interruption"):
        service.repair(intent)

    marker = service.control_root / "runtime" / ".binding-repair-transaction.json"
    assert marker.is_file()
    assert not (service.control_root / "manifests" / "binding-repair-current.json").exists()

    result = service.repair(intent)

    assert result["status"] == "repaired"
    assert not marker.exists()
    _assert_one_binding_event(service, f"binding-repair-{sha256_hex(canonical_bytes(intent.semantic_payload()))}")


@pytest.mark.parametrize("crash_phase", ("event", "receipt"))
def test_advance_marker_recovery_replays_partial_publication(tmp_path: Path, crash_phase: str) -> None:
    service, intent, _reviewed = _reviewed_divergence_intent(tmp_path)
    pointer_before = (service.control_root / "manifests" / "binding-repair-current.json").read_bytes()
    crashed = False

    def crash(phase: str) -> None:
        nonlocal crashed
        if phase == crash_phase and not crashed:
            crashed = True
            raise OSError("simulated control-store interruption")

    service.phase_hook = crash
    with pytest.raises(OSError, match="simulated control-store interruption"):
        service.advance(intent)

    marker = service.control_root / "runtime" / ".binding-advance-transaction.json"
    assert marker.is_file()
    assert (service.control_root / "manifests" / "binding-repair-current.json").read_bytes() == pointer_before

    result = service.advance(intent)

    assert result["status"] == "advanced"
    assert not marker.exists()
    _assert_one_binding_event(service, f"binding-advance-{sha256_hex(canonical_bytes(intent.semantic_payload()))}")


def test_v1_2_history_and_documentation_descendants_remain_admissible(tmp_path: Path) -> None:
    service, first_intent, reviewed = _reviewed_divergence_intent(tmp_path)
    first = service.advance(first_intent)

    successor = tmp_path / "successor"
    shutil.copytree(reviewed, successor)
    _git(successor, "config", "user.email", "gate6@example.invalid")
    _git(successor, "config", "user.name", "Gate 6")
    (successor / "research_system" / "second_reviewed_change.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(successor, "add", ".")
    _git(successor, "commit", "-m", "second reviewed code change")
    successor = successor.resolve()
    second_head = _git_text(successor, "rev-parse", "HEAD")
    second_intent = AdvanceStoreBinding(
        service.control_root,
        successor,
        PROJECT_ID,
        service.store_identity,
        first_intent.expected_origin_authority_root,
        first_intent.expected_origin_witness_sha256,
        successor / ".research-system" / "schemas",
        "2026-08-24T11:00:00Z",
        "2026-08-24T13:00:00Z",
        first_intent.owner_actor_id,
        "advance-clean-descendant-store-binding",
        "v12-clean-descendant",
        "reviewed governed descendant",
        str(first["binding_sha256"]),
        second_head,
        second_head,
        "refs/heads/main",
        None,
    )
    second = service.advance(second_intent)
    admitted = load_current_binding(
        foundation_path=successor / ".research-system" / "config" / "foundation.yaml",
        repository_root=successor,
        expected_control_root=service.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=service.store_identity,
        expected_binding_sha256=str(second["binding_sha256"]),
    )
    assert admitted.binding_sha256 == second["binding_sha256"]

    (successor / "docs").mkdir(exist_ok=True)
    (successor / "docs" / "binding-note.md").write_text("reviewed documentation only\n", encoding="utf-8")
    _git(successor, "add", ".")
    _git(successor, "commit", "-m", "reviewed documentation only")
    pointer_before = (service.control_root / "manifests" / "binding-repair-current.json").read_bytes()
    events_before = tuple(service.ledger.iter_events())
    documentation_admission = load_current_binding(
        foundation_path=successor / ".research-system" / "config" / "foundation.yaml",
        repository_root=successor,
        expected_control_root=service.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=service.store_identity,
        expected_binding_sha256=str(second["binding_sha256"]),
    )
    assert documentation_admission.binding_sha256 == second["binding_sha256"]
    assert (service.control_root / "manifests" / "binding-repair-current.json").read_bytes() == pointer_before
    assert tuple(service.ledger.iter_events()) == events_before

    (successor / "research_system" / "unbound_governed_change.py").write_text("VALUE = 3\n", encoding="utf-8")
    _git(successor, "add", ".")
    _git(successor, "commit", "-m", "unbound governed change")
    with pytest.raises(IntegrityError, match="governed code"):
        load_current_binding(
            foundation_path=successor / ".research-system" / "config" / "foundation.yaml",
            repository_root=successor,
            expected_control_root=service.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=service.store_identity,
            expected_binding_sha256=str(second["binding_sha256"]),
        )


@pytest.mark.parametrize("reader", (read_advance_intent, read_repair_intent))
def test_public_intent_readers_report_invalid_files_as_configuration(reader, tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        reader("not-a-path")  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError):
        reader(tmp_path / "missing.json")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        reader(malformed)
    schema_invalid = tmp_path / "schema-invalid.json"
    schema_invalid.write_bytes(canonical_bytes({}))
    with pytest.raises(ConfigurationError):
        reader(schema_invalid)
