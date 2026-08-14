from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

import research_system.config as config_module
from research_system.canonical import canonical_bytes
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.schema_registry import runtime_schema_registry
from research_system.store.binding_repair import (
    COMMAND_SCHEMA_ID,
    RepairStoreBinding,
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
    with pytest.raises(IntegrityError, match="successor object"):
        load_store_manifest(target, approved_witness=witness, approved_witness_path=initialized.witness_path)
    with pytest.raises(IntegrityError, match="successor object"):
        repair_store_binding(intent, now=lambda: datetime(2026, 8, 14, tzinfo=UTC))


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
