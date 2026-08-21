from __future__ import annotations

import json
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

import research_system.config as config_module
import research_system.store.binding_repair as binding_repair_module
import research_system.store.contained_files as contained_files_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.schema_registry import runtime_schema_registry
from research_system.store.binding_repair import (
    AdvanceStoreBinding,
    COMMAND_SCHEMA_ID,
    RepairStoreBinding,
    advance_store_binding,
    load_recovery_binding,
    repair_store_binding,
)
from research_system.store.identity import load_store_manifest
from research_system.store.ledger import EventLedger
from tests.research_system.factories import REPO_ROOT
from tests.research_system.integration.test_restore_recovery_origin_witness import (
    ACTOR_ID,
    _restored_fixture,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    initialized, witness, target, _rebound = _restored_fixture(tmp_path)
    stale_repo = tmp_path / "repo"
    source = tmp_path / "source"
    candidate = tmp_path / "candidate"
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas", candidate / ".research-system" / "schemas")
    shutil.copytree(
        REPO_ROOT / ".research-system" / "contracts" / "wp6-6" / "spec-gate6-run-v1",
        candidate / ".research-system" / "contracts" / "wp6-6" / "spec-gate6-run-v1",
    )
    foundation = {
        "binding_source": "store-recovery",
        "project_id": witness.project_id,
        "control_root": str(target.resolve()),
        "store_identity": witness.store_identity,
        "origin_authority_root": str(initialized.witness_path.parent.parent.resolve()),
        "origin_witness_path": str(initialized.witness_path.resolve()),
        "origin_witness_sha256": witness.raw_sha256,
    }
    foundation_path = candidate / ".research-system" / "config" / "foundation.yaml"
    foundation_path.parent.mkdir(parents=True)
    foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8")
    _git(candidate, "init", "-q")
    _git(candidate, "config", "core.autocrlf", "false")
    _git(candidate, "config", "user.email", "binding-repair@example.invalid")
    _git(candidate, "config", "user.name", "Binding Repair Test")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-q", "-m", "fixture")
    shutil.rmtree(source)
    shutil.rmtree(stale_repo)
    intent = RepairStoreBinding(
        target.resolve(),
        candidate.resolve(),
        witness.project_id,
        witness.store_identity,
        initialized.witness_path.parent.parent.resolve(),
        witness.raw_sha256,
        (candidate / ".research-system" / "schemas").resolve(),
        ("manifests/.restore-binding-transaction.json",),
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json",
        (
            ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
            ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
        ),
        "2026-01-01T00:00:00Z",
        "2027-01-01T00:00:00Z",
        ACTOR_ID,
        "repair-stale-store-binding",
        "binding-repair:test:1",
        "Recover the retired schema binding.",
    )
    monkeypatch.setattr(config_module, "canonical_foundation_path", lambda: foundation_path)
    return initialized, witness, target, candidate, foundation_path, intent


def _binding_file(tmp_path: Path, target: Path, candidate: Path, witness) -> Path:
    path = tmp_path / "repaired-binding.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "code_roots": [str(candidate.resolve())],
                "control_root": str(target.resolve()),
                "project_id": witness.project_id,
                "schema_root": str((candidate / ".research-system" / "schemas").resolve()),
                "store_identity": witness.store_identity,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _publication_snapshot(target: Path) -> tuple[bytes, tuple[tuple[str, bytes], ...], tuple[tuple[str, bytes], ...]]:
    events = tuple(
        (path.relative_to(target).as_posix(), path.read_bytes())
        for path in sorted((target / "events").rglob("*.jsonl"))
    )
    receipts = tuple(
        (path.relative_to(target).as_posix(), path.read_bytes())
        for path in sorted((target / "receipts").rglob("*.json"))
    )
    return (target / "manifests" / "store-identity.json").read_bytes(), events, receipts


def test_binding_artifact_publication_ignores_foreign_hidden_debris(tmp_path: Path) -> None:
    """Unrecognized hidden debris is inert and cannot wedge a publication."""
    control = tmp_path / "control"
    target = control / "manifests" / "published.json"
    data = canonical_bytes({"kind": "published", "revision": 1})
    control.mkdir()
    abandoned = target.with_name(f".{target.name}.{sha256_hex(data)[:16]}.tmp")
    abandoned.parent.mkdir()
    abandoned.write_bytes(b"tampered abandoned staging")

    binding_repair_module._publish(control, target, data)

    assert target.read_bytes() == data
    assert abandoned.read_bytes() == b"tampered abandoned staging"


def test_binding_repair_ignores_foreign_manifest_debris(tmp_path: Path, monkeypatch) -> None:
    """A repair preserves unrelated hidden debris while publishing its manifest."""
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    target_manifest = target / "manifests" / "store-identity.json"
    repaired_manifest = json.loads(target_manifest.read_bytes())
    repaired_manifest["code_roots"] = [str(candidate.resolve())]
    repaired_manifest["schema_root"] = str((candidate / ".research-system" / "schemas").resolve())
    repaired_manifest["schema_binding_version"] = "1.0.0"
    restore = json.loads((target / "manifests" / ".restore-binding-transaction.json").read_bytes())
    repaired_manifest["manifest_hash"] = binding_repair_module._restored_manifest_hash(
        repaired_manifest, str(restore["approval_sha256"])
    )
    repaired_raw = canonical_bytes(repaired_manifest)
    abandoned = target_manifest.with_name(f".{target_manifest.name}.{sha256_hex(repaired_raw)[:16]}.replace")
    abandoned.write_bytes(b"tampered abandoned staging")

    result = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert result["status"] == "repaired"
    assert target_manifest.read_bytes() == repaired_raw
    assert abandoned.read_bytes() == b"tampered abandoned staging"


def test_binding_artifact_publication_never_replaces_a_competing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent final leaf wins as a conflict, never an overwrite."""
    control = tmp_path / "control"
    target = control / "manifests" / "published.json"
    data = canonical_bytes({"kind": "published", "revision": 1})
    competing = b"competing durable artifact"
    control.mkdir()
    target.parent.mkdir()

    def publish_competitor(source: str | Path, destination: str | Path, **_kwargs: object) -> None:
        Path(destination).write_bytes(competing)
        raise FileExistsError

    monkeypatch.setattr(contained_files_module.os, "link", publish_competitor)

    with pytest.raises(ConflictError, match="conflicts"):
        binding_repair_module._publish(control, target, data)

    assert target.read_bytes() == competing


def test_binding_artifact_replacement_refuses_a_competing_predecessor(tmp_path: Path) -> None:
    """Mutable binding state is replaced only from its exact verified predecessor."""
    control = tmp_path / "control"
    target = control / "manifests" / "current.json"
    predecessor = canonical_bytes({"revision": 1})
    successor = canonical_bytes({"revision": 2})
    competing = canonical_bytes({"revision": "competing"})
    control.mkdir()
    target.parent.mkdir()
    target.write_bytes(competing)

    with pytest.raises(ConflictError, match="replacement conflicts"):
        binding_repair_module._replace(control, target, successor, expected=predecessor)

    assert target.read_bytes() == competing


def test_binding_artifact_replacement_refuses_a_competitor_after_predecessor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The replacement rechecks the held final leaf immediately before mutation."""
    control = tmp_path / "control"
    target = control / "manifests" / "current.json"
    predecessor = canonical_bytes({"revision": 1})
    successor = canonical_bytes({"revision": 2})
    competing = canonical_bytes({"revision": "competing"})
    control.mkdir()
    target.parent.mkdir()
    target.write_bytes(predecessor)

    def inject_competitor(_temporary: Path, destination: Path) -> None:
        destination.write_bytes(competing)

    monkeypatch.setattr(contained_files_module, "_after_contained_file_predecessor_verified", inject_competitor)

    with pytest.raises(ConflictError, match="replacement conflicts"):
        binding_repair_module._replace(control, target, successor, expected=predecessor)

    assert target.read_bytes() == competing


def test_binding_artifact_replacement_preserves_competitor_after_predecessor_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A competitor claiming the final name after unlink wins and leaves no attempt debris."""
    control = tmp_path / "control"
    target = control / "manifests" / "current.json"
    predecessor = canonical_bytes({"revision": 1})
    successor = canonical_bytes({"revision": 2})
    competing = canonical_bytes({"revision": "competing"})
    control.mkdir()
    target.parent.mkdir()
    target.write_bytes(predecessor)

    def inject_competitor(_temporary: Path, destination: Path) -> None:
        destination.write_bytes(competing)

    monkeypatch.setattr(contained_files_module, "_after_contained_file_predecessor_removed", inject_competitor)

    with pytest.raises(ConflictError, match="replacement conflicts"):
        binding_repair_module._replace(control, target, successor, expected=predecessor)

    assert target.read_bytes() == competing
    assert not list(target.parent.glob(f".{target.name}.*.replace"))
    assert not list(target.parent.glob(f".{target.name}.*.previous"))


@pytest.mark.parametrize(
    "seam_name",
    (
        "_after_contained_file_replacement_staged",
        "_after_contained_file_predecessor_backed_up",
        "_after_contained_file_predecessor_removed",
        "_after_contained_file_successor_linked",
    ),
)
def test_binding_artifact_replacement_retries_after_hard_stop_at_each_swap_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seam_name: str
) -> None:
    """A fresh binding retry reconciles each durable exact swap state."""
    control = tmp_path / "control"
    target = control / "manifests" / "current.json"
    predecessor = canonical_bytes({"revision": 1})
    successor = canonical_bytes({"revision": 2})
    stage = target.with_name(f".{target.name}.{sha256_hex(successor)}.replace")
    backup = target.with_name(f".{target.name}.{sha256_hex(predecessor)}.previous")
    control.mkdir()
    target.parent.mkdir()
    target.write_bytes(predecessor)

    class SimulatedHardStop(BaseException):
        pass

    def crash(_temporary: Path, _destination: Path) -> None:
        raise SimulatedHardStop(seam_name)

    with monkeypatch.context() as crash_patch:
        crash_patch.setattr(contained_files_module, seam_name, crash)
        with pytest.raises(SimulatedHardStop, match=seam_name):
            binding_repair_module._replace(control, target, successor, expected=predecessor)

    binding_repair_module._replace(control, target, successor, expected=predecessor)

    assert target.read_bytes() == successor
    assert not stage.exists()
    assert not backup.exists()


def test_repair_is_replayable_and_enables_only_governed_repaired_loader(tmp_path: Path, monkeypatch):
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    result = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    retry = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert retry == result
    manifest = load_store_manifest(target, approved_witness=witness, approved_witness_path=initialized.witness_path)
    assert manifest["code_roots"] == [str(candidate.resolve())]
    binding_path = _binding_file(tmp_path, target, candidate, witness)
    with pytest.raises(Exception):
        ControlBinding.load(binding_path)
    assert ControlBinding.load_repaired(binding_path).schema_root == candidate / ".research-system" / "schemas"
    changed = deepcopy(intent)
    object.__setattr__(changed, "reason", "A different semantic repair reason.")
    with pytest.raises(ConflictError):
        repair_store_binding(changed, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    second_repair = deepcopy(intent)
    object.__setattr__(second_repair, "idempotency_key", "binding-repair:test:2")
    with pytest.raises(ConflictError, match="currently valid"):
        repair_store_binding(second_repair, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))


def test_repair_scrubs_repository_overriding_git_environment(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, _target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "not-the-candidate.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "not-the-candidate"))
    monkeypatch.setenv("GIT_REPLACE_REF_BASE", "refs/replace/hostile/")
    assert repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))["status"] == "repaired"


def test_repair_rejects_a_clean_committed_route_symlink_before_publication(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    route = candidate / intent.spec_route_ref
    external = tmp_path / "external-route.json"
    external.write_bytes(route.read_bytes())
    route.unlink()
    try:
        route.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-q", "-m", "committed redirected route")
    before = _publication_snapshot(target)

    with pytest.raises(IntegrityError, match="physical path|redirected"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert _publication_snapshot(target) == before


def test_repair_rejects_a_clean_committed_schema_symlink_before_publication(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    schema = next((candidate / ".research-system" / "schemas").rglob("*.schema.json"))
    external = tmp_path / "external-schema.json"
    external.write_bytes(schema.read_bytes())
    schema.unlink()
    try:
        schema.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-q", "-m", "committed redirected schema")
    before = _publication_snapshot(target)

    with pytest.raises(IntegrityError, match="schema.*physical path|schema.*redirected"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert _publication_snapshot(target) == before


def test_repair_rejects_redirected_object_parent_before_publication(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    object_parent = target / "objects" / "binding-repair"
    external = tmp_path / "external-binding-repair"
    external.mkdir()
    try:
        object_parent.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    before = _publication_snapshot(target)

    with pytest.raises(IntegrityError, match="artifact parent is redirected"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert _publication_snapshot(target) == before
    assert not list(external.iterdir())


def test_repair_publication_schemas_reject_underbound_object_event_and_receipt(tmp_path: Path, monkeypatch):
    _initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    result = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    registry = runtime_schema_registry(candidate / ".research-system" / "schemas")
    event = tuple(
        EventLedger(target, witness.project_id, registry, store_identity=witness.store_identity).iter_events()
    )[-1]
    receipt_path = next((target / "receipts").glob("binding-repair-*.json"))
    receipt = json.loads(receipt_path.read_bytes())
    recovery = result["recovery_binding"]

    registry.validate("ars://wp6-6/gate6/binding-repair/object/StoreBindingRepair", recovery)
    registry.validate("ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired", event)
    registry.validate("ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair", receipt)

    invalid_object = deepcopy(recovery)
    invalid_object.pop("owner_actor_id")
    invalid_event = deepcopy(event)
    invalid_event["actor_id"] = "not-an-actor"
    invalid_receipt = deepcopy(receipt)
    invalid_receipt["unexpected"] = True
    for schema_id, invalid in (
        ("ars://wp6-6/gate6/binding-repair/object/StoreBindingRepair", invalid_object),
        ("ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired", invalid_event),
        ("ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair", invalid_receipt),
    ):
        with pytest.raises(SchemaError):
            registry.validate(schema_id, invalid)


def test_binding_receipt_schemas_are_active_and_command_specific(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, _target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    registry = runtime_schema_registry(candidate / ".research-system" / "schemas")
    repair_schema = "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair"
    advance_schema = "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingAdvance"
    assert registry.is_active(repair_schema, "1.0.0")
    assert registry.is_active(advance_schema, "1.0.0")
    repair_receipt = json.loads(
        (intent.control_root / "receipts" / f"{repair['receipt']['command_id']}.json").read_bytes()
    )
    registry.validate(repair_schema, repair_receipt)
    with pytest.raises(SchemaError):
        registry.validate(advance_schema, repair_receipt)

    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")
    advance = advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    advance_receipt = json.loads(
        (intent.control_root / "receipts" / f"{advance['receipt']['command_id']}.json").read_bytes()
    )
    registry.validate(advance_schema, advance_receipt)
    with pytest.raises(SchemaError):
        registry.validate(repair_schema, advance_receipt)


def test_repair_receipt_schema_rejects_invalid_identity_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialized, _witness, _target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    result = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    receipt = json.loads((intent.control_root / "receipts" / f"{result['receipt']['command_id']}.json").read_bytes())
    invalid_receipts = []
    for mutation in ("missing", "wrong_type", "null", "cross_command"):
        invalid = deepcopy(receipt)
        if mutation == "missing":
            invalid.pop("status")
        elif mutation == "wrong_type":
            invalid["outcome"]["observed_stream_version"] = "1"
        elif mutation == "null":
            invalid["command_id"] = None
        else:
            invalid["command_id"] = invalid["command_id"].replace("binding-repair-", "binding-advance-")
        invalid_receipts.append(invalid)
    registry = runtime_schema_registry(candidate / ".research-system" / "schemas")
    for invalid in invalid_receipts:
        with pytest.raises(SchemaError):
            registry.validate(
                "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair",
                invalid,
            )


def test_repaired_loader_rejects_invalid_typed_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    result = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    receipt_path = target / "receipts" / f"{result['receipt']['command_id']}.json"
    receipt = json.loads(receipt_path.read_bytes())
    index_path = next((target / "receipts" / "idempotency").glob("*.json"))
    index = json.loads(index_path.read_bytes())
    binding_path = _binding_file(tmp_path, target, candidate, witness)
    for mutation in ("missing", "wrong_type", "null", "cross_command"):
        invalid = deepcopy(receipt)
        if mutation == "missing":
            invalid.pop("status")
        elif mutation == "wrong_type":
            invalid["outcome"]["observed_stream_version"] = "1"
        elif mutation == "null":
            invalid["command_id"] = None
        else:
            invalid["command_id"] = invalid["command_id"].replace("binding-repair-", "binding-advance-")
        receipt_path.write_bytes(canonical_bytes(invalid))
        invalid_index = deepcopy(index)
        invalid_index["receipt"] = invalid
        index_path.write_bytes(canonical_bytes(invalid_index))
        with pytest.raises(IntegrityError, match="receipt is invalid"):
            ControlBinding.load_repaired(binding_path)


def test_repaired_loader_requires_executing_repository_in_governed_code_roots(tmp_path: Path, monkeypatch):
    _initialized, _witness, target, _candidate, foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    foreign_foundation = tmp_path / "foreign-repository" / ".research-system" / "config" / "foundation.yaml"
    foreign_foundation.parent.mkdir(parents=True)
    foreign_foundation.write_bytes(foundation.read_bytes())
    monkeypatch.setattr(config_module, "canonical_foundation_path", lambda: foreign_foundation)

    with pytest.raises(Exception, match="executing repository root"):
        ControlBinding.load_repaired(target / "manifests" / "binding-repair-control-binding.json")


def _advance_intent(intent: RepairStoreBinding) -> AdvanceStoreBinding:
    return AdvanceStoreBinding(
        intent.control_root,
        intent.candidate_repository_root,
        intent.expected_project_id,
        intent.expected_store_identity,
        intent.expected_origin_authority_root,
        intent.expected_origin_witness_sha256,
        intent.intended_schema_root,
        intent.valid_from,
        intent.expires_at,
        intent.owner_actor_id,
        "advance-clean-descendant-store-binding",
        "binding-advance:test:1",
        "Advance the valid repaired binding to its tested clean descendant.",
    )


def test_valid_repaired_binding_reopens_source_bound_manifest_only_for_clean_protected_byte_preserving_descendant(
    tmp_path: Path, monkeypatch
) -> None:
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repaired = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    old_head = repaired["recovery_binding"]["git_head"]
    note = candidate / "descendant.txt"
    note.write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")

    # The recovery binding deliberately pins ``old_head`` until this command
    # validates the clean descendant and publishes its governed successor.
    result = advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    retry = advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert result == retry
    assert result["status"] == "advanced"
    assert result["recovery_binding"]["schema_version"] == "1.1.0"
    assert result["recovery_binding"]["git_head"] != old_head
    binding_path = _binding_file(tmp_path, target, candidate, witness)
    assert ControlBinding.load_repaired(binding_path).schema_root == candidate / ".research-system" / "schemas"
    events = tuple(
        EventLedger(
            target,
            witness.project_id,
            runtime_schema_registry(candidate / ".research-system" / "schemas"),
            store_identity=witness.store_identity,
        ).iter_events()
    )
    assert [event["event_type"] for event in events[-2:]] == ["StoreBindingRepaired", "StoreBindingAdvanced"]


def test_binding_advance_rejects_changed_spec_bytes_without_store_mutation(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    route = candidate / ".research-system" / "contracts" / "wp6-6" / "spec-gate6-run-v1" / "route-package.json"
    route.write_bytes(route.read_bytes() + b" ")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-q", "-m", "tamper protected route")
    before = _publication_snapshot(target)
    with pytest.raises(IntegrityError, match="protected route or SPEC bytes"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert _publication_snapshot(target) == before


def test_binding_advance_rejects_rehashed_misbound_manifest_without_mutation(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")
    foreign_root = tmp_path / "misbound-code-root"
    foreign_schema_root = foreign_root / ".research-system" / "schemas"
    foreign_schema_root.mkdir(parents=True)
    manifest_path = target / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["code_roots"] = [str(foreign_root.resolve())]
    manifest["schema_root"] = str(foreign_schema_root.resolve())
    restore = json.loads((target / "manifests" / ".restore-binding-transaction.json").read_bytes())
    manifest["manifest_hash"] = binding_repair_module._restored_manifest_hash(manifest, str(restore["approval_sha256"]))
    manifest_path.write_bytes(canonical_bytes(manifest))
    before = _publication_snapshot(target)

    with pytest.raises(IntegrityError, match="source-bound manifest identity"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert _publication_snapshot(target) == before


@pytest.mark.parametrize("phase", ["marker", "object", "event", "receipt", "recovery"])
def test_binding_advance_recovers_after_each_publication_phase(tmp_path: Path, monkeypatch, phase: str) -> None:
    _initialized, _witness, _target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")

    def crash(observed: str) -> None:
        if observed == phase:
            raise RuntimeError(phase)

    with pytest.raises(RuntimeError, match=phase):
        advance_store_binding(
            _advance_intent(intent),
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
            phase_hook=crash,
        )
    assert (
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))["status"]
        == "advanced"
    )


def test_started_binding_advance_recovers_after_owner_window_expires(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, _target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")

    def crash(observed: str) -> None:
        if observed == "event":
            raise RuntimeError("crash after event")

    with pytest.raises(RuntimeError, match="crash after event"):
        advance_store_binding(
            _advance_intent(intent),
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
            phase_hook=crash,
        )
    result = advance_store_binding(
        _advance_intent(intent),
        now=lambda: datetime(2028, 8, 14, tzinfo=UTC),
    )
    assert result["status"] == "advanced"


def test_binding_advance_serializes_predecessor_selection_and_leaves_no_losing_residue(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Only the lock holder may select the predecessor and publish its successor."""
    _initialized, witness, target, candidate, _foundation, repair_intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(repair_intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")

    winner_intent = _advance_intent(repair_intent)
    loser_intent = replace(winner_intent, idempotency_key="binding-advance:test:loser")
    winner_locked = threading.Event()
    loser_waiting = threading.Event()
    winner_done = threading.Event()
    original_lock = binding_repair_module.WriterLock
    winner_writer_id = f"binding-advance:{sha256_hex(canonical_bytes(winner_intent.semantic_payload()))}"

    class OrderedWriterLock:
        def __init__(self, path: Path, identity: dict[str, str]):
            self._delegate = original_lock(path, identity)
            self._is_winner = identity["writer_id"] == winner_writer_id

        def __enter__(self):
            if not self._is_winner:
                loser_waiting.set()
                assert winner_done.wait(timeout=60)
            held = self._delegate.__enter__()
            if self._is_winner:
                winner_locked.set()
            return held

        def __exit__(self, exc_type, exc, traceback):
            try:
                return self._delegate.__exit__(exc_type, exc, traceback)
            finally:
                if self._is_winner:
                    winner_done.set()

    monkeypatch.setattr(binding_repair_module, "WriterLock", OrderedWriterLock)

    def hold_winner_until_loser_reaches_the_transaction_boundary(phase: str) -> None:
        if phase == "object":
            assert loser_waiting.wait(timeout=60)

    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(
            advance_store_binding,
            winner_intent,
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
            phase_hook=hold_winner_until_loser_reaches_the_transaction_boundary,
        )
        assert winner_locked.wait(timeout=60)
        loser = pool.submit(
            advance_store_binding,
            loser_intent,
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
        )
        assert winner.result(timeout=60)["status"] == "advanced"
        with pytest.raises(ConflictError, match="strict Git descendant"):
            loser.result(timeout=60)

    ledger = EventLedger(
        target,
        witness.project_id,
        runtime_schema_registry(candidate / ".research-system" / "schemas"),
        store_identity=witness.store_identity,
    )
    advances = tuple(event for event in ledger.iter_events() if event["event_type"] == "StoreBindingAdvanced")
    assert [event["idempotency_key"] for event in advances] == [winner_intent.idempotency_key]
    loser_payload_hash = sha256_hex(canonical_bytes(loser_intent.semantic_payload())).encode("ascii")
    owned_residue = tuple(
        path.relative_to(target).as_posix()
        for root in (target / "objects", target / "events", target / "receipts")
        for path in root.rglob("*")
        if path.is_file() and loser_payload_hash in path.read_bytes()
    )
    assert owned_residue == ()
    assert not (target / "runtime" / ".binding-advance-transaction.json").exists()
    assert len(tuple((target / "objects" / "binding-repair").glob("*.json"))) == 2
    assert len(tuple((target / "receipts").glob("binding-advance-*.json"))) == 1


def test_binding_advance_rejects_dirty_or_non_descendant_candidate(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    before = _publication_snapshot(target)
    (candidate / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ConflictError, match="dirty"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert _publication_snapshot(target) == before
    (candidate / "dirty.txt").unlink()
    with pytest.raises(ConflictError, match="strict Git descendant"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert _publication_snapshot(target) == before


def test_binding_advance_rejects_redirected_marker_and_recovery(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")
    external = tmp_path / "external.json"
    external.write_bytes(canonical_bytes({"external": True}))
    marker = target / "runtime" / ".binding-advance-transaction.json"
    try:
        marker.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(IntegrityError, match="marker"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert external.read_bytes() == canonical_bytes({"external": True})
    marker.unlink()
    recovery = target / "manifests" / "binding-repair-current.json"
    recovery.unlink()
    recovery.symlink_to(external)
    with pytest.raises(IntegrityError, match="binding repair successor"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert external.read_bytes() == canonical_bytes({"external": True})


def test_binding_advance_rejects_redirected_runtime_before_external_lock_publication(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")
    runtime = target / "runtime"
    runtime.rename(target / "runtime-physical")
    external = tmp_path / "external-runtime"
    external.mkdir()
    try:
        runtime.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")

    with pytest.raises(IntegrityError, match="binding advance runtime"):
        advance_store_binding(_advance_intent(intent), now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert tuple(external.iterdir()) == ()


def test_binding_advance_rejects_redirected_object_without_touching_external_target(
    tmp_path: Path, monkeypatch
) -> None:
    _initialized, _witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "descendant.txt").write_text("tested descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")
    external = tmp_path / "external-object.json"
    external_raw = canonical_bytes({"external": True})
    external.write_bytes(external_raw)
    existing = set((target / "objects" / "binding-repair").glob("*.json"))

    def redirect(observed: str) -> None:
        if observed != "object":
            return
        created = set((target / "objects" / "binding-repair").glob("*.json")) - existing
        assert len(created) == 1
        object_path = created.pop()
        object_path.unlink()
        object_path.symlink_to(external)
        raise RuntimeError("redirected object")

    with pytest.raises(IntegrityError, match="binding advance object"):
        advance_store_binding(
            _advance_intent(intent),
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
            phase_hook=redirect,
        )
    assert external.read_bytes() == external_raw


@pytest.mark.parametrize("phase", ["manifest", "object", "event", "receipt"])
def test_crash_at_each_publication_phase_recovers_in_a_fresh_call(tmp_path: Path, monkeypatch, phase: str):
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)

    def crash(observed: str) -> None:
        if observed == phase:
            raise RuntimeError(f"crash after {phase}")

    with pytest.raises(RuntimeError, match=phase):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC), phase_hook=crash)
    result = repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert result["status"] == "repaired"
    assert load_store_manifest(target, approved_witness=witness, approved_witness_path=initialized.witness_path)[
        "code_roots"
    ] == [str(candidate)]


def test_started_repair_recovers_after_owner_intent_window_expires(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, _target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)

    def crash(observed: str) -> None:
        if observed == "event":
            raise RuntimeError("crash after event")

    with pytest.raises(RuntimeError, match="crash after event"):
        repair_store_binding(
            intent,
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
            phase_hook=crash,
        )

    result = repair_store_binding(intent, now=lambda: datetime(2028, 8, 14, tzinfo=UTC))
    assert result["status"] == "repaired"


def test_started_repair_rejects_candidate_advance_before_recovery(tmp_path: Path, monkeypatch) -> None:
    _initialized, _witness, _target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)

    def crash(observed: str) -> None:
        if observed == "event":
            raise RuntimeError("crash after event")

    with pytest.raises(RuntimeError, match="crash after event"):
        repair_store_binding(
            intent,
            now=lambda: datetime(2026, 8, 14, tzinfo=UTC),
            phase_hook=crash,
        )
    (candidate / "descendant.txt").write_text("new clean descendant\n", encoding="utf-8")
    _git(candidate, "add", "descendant.txt")
    _git(candidate, "commit", "-q", "-m", "descendant")

    with pytest.raises(IntegrityError, match="Git candidate changed"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))


def test_crash_marker_redirect_is_rejected_without_retry_publication(tmp_path: Path, monkeypatch):
    _initialized, _witness, target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)

    def crash(observed: str) -> None:
        if observed == "manifest":
            raise RuntimeError("crash after manifest")

    with pytest.raises(RuntimeError, match="manifest"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC), phase_hook=crash)
    marker_path = target / "runtime" / ".binding-repair-transaction.json"
    marker_raw = marker_path.read_bytes()
    external_marker = tmp_path / "external-marker.json"
    external_marker.write_bytes(marker_raw)
    marker_path.unlink()
    marker_path.symlink_to(external_marker)
    expected = _publication_snapshot(target)

    with pytest.raises(IntegrityError, match="recovery marker.*reparse"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))

    assert marker_path.is_symlink()
    assert external_marker.read_bytes() == marker_raw
    assert _publication_snapshot(target) == expected
    assert not any((target / "receipts").rglob("binding-repair-*.json"))


def test_current_binding_dirty_candidate_and_generic_append_fail_without_repair_publication(
    tmp_path: Path, monkeypatch
):
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    non_owner = deepcopy(intent)
    object.__setattr__(non_owner, "owner_actor_id", "act_01978abc-1002-7000-8000-000000009999")
    with pytest.raises(IntegrityError, match="not the immutable authority owner"):
        repair_store_binding(non_owner, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert not (target / "manifests" / "binding-repair-current.json").exists()
    # Restoring the retired root makes the stale predicate false.
    stale = tmp_path / "repo" / ".research-system" / "schemas"
    stale.mkdir(parents=True)
    (tmp_path / "source").mkdir()
    with pytest.raises(ConflictError, match="currently valid"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    shutil.rmtree(tmp_path / "repo")
    (tmp_path / "source").rmdir()
    (candidate / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ConflictError, match="dirty"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    (candidate / "dirty.txt").unlink()
    ledger = EventLedger(
        target, witness.project_id, runtime_schema_registry(candidate / ".research-system" / "schemas")
    )
    command_schema = ledger.schemas.resolve_identity(COMMAND_SCHEMA_ID, "1.0.0")
    with pytest.raises(ArsError, match="validated repair-service continuation"):
        ledger._append_binding_repair_from_validated_service(
            {"payload": {}},
            snapshot=ledger.snapshot(),
        )
    with pytest.raises(ArsError, match="validated repair-service continuation"):
        ledger.append(
            [
                {
                    "event_type": "StoreBindingRepaired",
                    "stream_id": witness.project_id,
                    "schema_id": "ars://wp6-6/gate6/binding-repair/event/StoreBindingRepaired",
                    "schema_version": "1.0.0",
                    "command_type": "RepairStoreBinding",
                    "command_schema_id": command_schema.schema_id,
                    "command_schema_version": command_schema.schema_version,
                    "command_schema_sha256": command_schema.sha256,
                    "payload": {},
                }
            ]
        )
    assert not (target / "manifests" / "binding-repair-current.json").exists()


def test_source_mismatch_and_successor_tamper_or_clean_git_drift_fail_closed(tmp_path: Path, monkeypatch):
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    source = candidate / intent.spec_source_refs[0]
    source.write_bytes(source.read_bytes() + b"tamper")
    _git(candidate, "add", ".")
    _git(candidate, "commit", "-q", "-m", "tampered source")
    with pytest.raises(IntegrityError, match="route/source SHA"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    _git(candidate, "reset", "--hard", "HEAD~1")
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    binding = target / "manifests" / "binding-repair-control-binding.json"
    _git(candidate, "commit", "--allow-empty", "-q", "-m", "clean subject drift")
    with pytest.raises(IntegrityError, match="Git subject changed"):
        ControlBinding.load_repaired(binding)
    _git(candidate, "reset", "--hard", "HEAD~1")
    recovery_path = target / "manifests" / "binding-repair-current.json"
    recovery = json.loads(recovery_path.read_bytes())
    recovery["schema_catalogue_sha256"] = "f" * 64
    recovery_path.write_bytes(canonical_bytes(recovery))
    with pytest.raises(IntegrityError, match="schema catalogue changed"):
        load_store_manifest(target, approved_witness=witness, approved_witness_path=initialized.witness_path)
    with pytest.raises(IntegrityError, match="schema catalogue changed"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))


def test_recovery_recomputes_the_schema_catalogue_before_returning_a_binding(tmp_path: Path, monkeypatch) -> None:
    initialized, witness, target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    before = _publication_snapshot(target)
    recovery_path = target / "manifests" / "binding-repair-current.json"
    recovery = json.loads(recovery_path.read_bytes())
    recovery["schema_catalogue_sha256"] = "f" * 64
    recovery_path.write_bytes(canonical_bytes(recovery))

    with pytest.raises(IntegrityError, match="schema catalogue changed"):
        load_recovery_binding(
            target,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        )

    assert _publication_snapshot(target) == before
    assert initialized.witness_path.exists()


def test_repaired_manifest_loader_rejects_a_mutated_schema_leaf_without_publication(
    tmp_path: Path, monkeypatch
) -> None:
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    before = _publication_snapshot(target)
    schema = next((candidate / ".research-system" / "schemas").rglob("*.schema.json"))
    schema.write_bytes(schema.read_bytes() + b"\n")

    for load in (
        lambda: load_recovery_binding(
            target,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        ),
        lambda: load_store_manifest(
            target,
            approved_witness=witness,
            approved_witness_path=initialized.witness_path,
        ),
    ):
        with pytest.raises(IntegrityError, match="repository is dirty"):
            load()

    assert _publication_snapshot(target) == before


def test_recovery_binding_rejects_duplicate_spec_source_identity(tmp_path: Path, monkeypatch):
    initialized, witness, target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    recovery_path = target / "manifests" / "binding-repair-current.json"
    recovery = json.loads(recovery_path.read_bytes())
    recovery["sources"] = [recovery["sources"][0], recovery["sources"][0]]
    recovery_path.write_bytes(canonical_bytes(recovery))

    with pytest.raises(IntegrityError, match="route evidence is invalid"):
        load_recovery_binding(
            target,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        )

    assert initialized.witness_path.exists()


def test_repaired_loaders_reject_redirected_successor_paths_without_publication(tmp_path: Path, monkeypatch):
    initialized, witness, target, candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    binding = target / "manifests" / "binding-repair-control-binding.json"
    expected = _publication_snapshot(target)

    recovery_path = target / "manifests" / "binding-repair-current.json"
    recovery_raw = recovery_path.read_bytes()
    external_recovery = tmp_path / "external-recovery.json"
    external_recovery.write_bytes(recovery_raw)
    recovery_path.unlink()
    recovery_path.symlink_to(external_recovery)
    for load in (
        lambda: load_store_manifest(
            target,
            approved_witness=witness,
            approved_witness_path=initialized.witness_path,
        ),
        lambda: load_recovery_binding(
            target,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        ),
        lambda: ControlBinding.load_repaired(binding),
    ):
        with pytest.raises(IntegrityError, match="reparse"):
            load()
    assert _publication_snapshot(target) == expected
    recovery_path.unlink()
    recovery_path.write_bytes(recovery_raw)

    binding_raw = binding.read_bytes()
    external_binding = tmp_path / "external-binding.json"
    external_binding.write_bytes(binding_raw)
    binding.unlink()
    binding.symlink_to(external_binding)
    with pytest.raises(IntegrityError, match="reparse"):
        ControlBinding.load_repaired(binding)
    assert _publication_snapshot(target) == expected
    binding.unlink()
    binding.write_bytes(binding_raw)

    real_candidate = tmp_path / "candidate-real"
    candidate.rename(real_candidate)
    candidate.symlink_to(real_candidate, target_is_directory=True)
    for load in (
        lambda: load_store_manifest(
            target,
            approved_witness=witness,
            approved_witness_path=initialized.witness_path,
        ),
        lambda: load_recovery_binding(
            target,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        ),
        lambda: ControlBinding.load_repaired(binding),
    ):
        with pytest.raises(IntegrityError, match="reparse"):
            load()
    assert _publication_snapshot(target) == expected
    candidate.unlink()
    shutil.copytree(real_candidate, candidate)

    schema = candidate / ".research-system" / "schemas"
    real_schema = candidate / ".research-system" / "schemas-real"
    schema.rename(real_schema)
    schema.symlink_to(real_schema, target_is_directory=True)
    with pytest.raises(IntegrityError, match="reparse"):
        load_recovery_binding(
            target,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        )
    with pytest.raises(IntegrityError, match="reparse"):
        load_store_manifest(target, approved_witness=witness, approved_witness_path=initialized.witness_path)
    assert _publication_snapshot(target) == expected
    schema.unlink()
    shutil.copytree(real_schema, schema)
    shutil.rmtree(real_schema)

    alias = tmp_path / "target-alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(IntegrityError, match="reparse"):
        load_recovery_binding(
            alias,
            expected_project_id=witness.project_id,
            expected_store_identity=witness.store_identity,
            expected_origin_witness_sha256=witness.raw_sha256,
        )
    with pytest.raises(IntegrityError, match="reparse"):
        load_store_manifest(alias, approved_witness=witness, approved_witness_path=initialized.witness_path)
    assert _publication_snapshot(target) == expected
    assert ControlBinding.load_repaired(binding).control_root == target


def test_repair_rejects_redirected_or_omitted_restore_anchor_without_publication(tmp_path: Path, monkeypatch):
    _initialized, _witness, target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    expected = _publication_snapshot(target)
    restore_path = target / "manifests" / ".restore-binding-transaction.json"
    restore_raw = restore_path.read_bytes()
    external_restore = tmp_path / "external-restore.json"
    external_restore.write_bytes(restore_raw)
    restore_path.unlink()
    restore_path.symlink_to(external_restore)
    omitted = deepcopy(intent)
    object.__setattr__(omitted, "stale_evidence_refs", ("manifests/store-identity.json",))
    with pytest.raises(IntegrityError, match="reparse"):
        repair_store_binding(omitted, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert _publication_snapshot(target) == expected
    assert not (target / "manifests" / "binding-repair-current.json").exists()
    restore_path.unlink()
    restore_path.write_bytes(restore_raw)
    with pytest.raises(ArsError, match="must include the exact cleared restore transaction"):
        repair_store_binding(omitted, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))
    assert _publication_snapshot(target) == expected
