from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.replay.driver import replay_discovery
from research_system.errors import ArsError, ConfigurationError, ConflictError, IntegrityError
from research_system.git_execution import scrubbed_git_environment
from research_system.schema_registry import runtime_schema_registry
from research_system.store.current_binding import _schema_catalogue, load_current_binding
from research_system.store.identity import load_restore_binding_transaction
from research_system.store.ledger import EventLedger
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


def _rewrite_last_event(fixture: _Fixture, **updates: object) -> tuple[dict[str, object], ...]:
    paths = sorted(fixture.ledger.events_root.rglob("*.jsonl"))
    assert paths
    path = paths[-1]
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    changed = {**events[-1], **updates}
    changed.pop("event_hash", None)
    changed["event_hash"] = sha256_hex(canonical_bytes(changed))
    events[-1] = changed
    path.write_bytes(b"".join(canonical_bytes(event) + b"\n" for event in events))
    return tuple(fixture.ledger.iter_events())


def _rewrite_event_at_position(
    fixture: _Fixture,
    position: int,
    **updates: object,
) -> tuple[dict[str, object], ...]:
    batches: list[tuple[Path, list[dict[str, object]]]] = []
    found = False
    for path in sorted(fixture.ledger.events_root.rglob("*.jsonl")):
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        for event in events:
            if event["global_position"] == position:
                event.update(updates)
                found = True
        batches.append((path, events))
    assert found

    previous_event_hash = "0" * 64
    for _, events in batches:
        for event in events:
            event["previous_event_hash"] = previous_event_hash
            event.pop("event_hash", None)
            event["event_hash"] = sha256_hex(canonical_bytes(event))
            previous_event_hash = str(event["event_hash"])
    for path, events in batches:
        path.write_bytes(b"".join(canonical_bytes(event) + b"\n" for event in events))
    return tuple(fixture.ledger.iter_events())


@dataclass(frozen=True)
class _Fixture:
    repository_root: Path
    control_root: Path
    foundation_path: Path
    binding: dict[str, object]
    binding_raw: bytes
    schemas: object
    ledger: EventLedger


def _write_historical_binding_advance_event(
    ledger: EventLedger,
    schemas: object,
    binding: dict[str, object],
    *,
    occurred_at: str,
) -> dict[str, object]:
    """Persist one pre-service v1.1 event exactly as historical ledger bytes.

    Historical replay is a read concern.  Its fixture must not mint the
    production-only continuation that creates a new binding effect.
    """

    command = schemas.command_binding("AdvanceStoreBinding")
    assert command is not None
    command_identity = schemas.resolve_identity(command.schema_id, "1.0.0")
    snapshot = ledger.snapshot()
    global_position = snapshot.global_position + 1
    stream_version = snapshot.stream_versions.get(PROJECT_ID, 0) + 1
    payload_hash = str(binding["command_payload_hash"])
    idempotency_key = str(binding["idempotency_key"])
    transaction_id = f"txb_historical_binding_{global_position:020d}"
    event: dict[str, object] = {
        "event_id": f"evt_historical_binding_{global_position:020d}",
        "event_type": "StoreBindingAdvanced",
        "schema_id": "ars://wp6-6/gate6/binding-repair/event/StoreBindingAdvanced",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "stream_id": PROJECT_ID,
        "stream_version": stream_version,
        "global_position": global_position,
        "transaction_id": transaction_id,
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": f"binding-advance-{payload_hash}",
        "command_type": "AdvanceStoreBinding",
        "idempotency_key": idempotency_key,
        "command_payload_hash": payload_hash,
        "correlation_id": idempotency_key,
        "causation_id": None,
        "actor_id": ACTOR_ID,
        "authority_grant_id": "store-binding-recovery",
        "occurred_at": occurred_at,
        "recorded_at": occurred_at,
        "command_schema_id": command_identity.schema_id,
        "command_schema_version": command_identity.schema_version,
        "command_schema_sha256": command_identity.sha256,
        "payload": {
            "recovery_binding_sha256": sha256_hex(canonical_bytes(binding)),
            "recovery_binding_path": "manifests/binding-repair-current.json",
            "object_path": (f"objects/binding-repair/sha256-{sha256_hex(canonical_bytes(binding))}.json"),
            "git_head": binding["git_head"],
            "git_tree": binding["git_tree"],
            "predecessor_binding_sha256": binding["predecessor_binding_sha256"],
        },
        "previous_event_hash": snapshot.event_hash,
    }
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    batch_path = ledger.events_root / "2026" / "08" / f"{global_position:020d}-{transaction_id}.jsonl"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    assert not batch_path.exists()
    batch_path.write_bytes(canonical_bytes(event) + b"\n")
    return event


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
    event = _write_historical_binding_advance_event(
        ledger,
        schemas,
        binding,
        occurred_at="2026-08-23T12:00:00Z",
    )
    observed_version = int(event["stream_version"])
    receipt = {
        "schema_id": "ars://core/receipt",
        "schema_version": "1.0.0",
        "command_id": f"binding-advance-{payload_hash}",
        "status": "accepted",
        "payload_hash": payload_hash,
        "outcome": {
            "event_batch_id": event["transaction_id"],
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


def _publish_binding_advance(fixture: _Fixture, binding: dict[str, object]) -> str:
    binding_raw = canonical_bytes(binding)
    binding_sha256 = sha256_hex(binding_raw)
    object_path = fixture.control_root / "objects" / "binding-repair" / f"sha256-{binding_sha256}.json"
    object_path.write_bytes(binding_raw)
    payload_hash = str(binding["command_payload_hash"])
    idempotency_key = str(binding["idempotency_key"])
    event = _write_historical_binding_advance_event(
        fixture.ledger,
        fixture.schemas,
        binding,
        occurred_at="2026-08-23T13:00:00Z",
    )
    observed_version = int(event["stream_version"])
    receipt = {
        "schema_id": "ars://core/receipt",
        "schema_version": "1.0.0",
        "command_id": f"binding-advance-{payload_hash}",
        "status": "accepted",
        "payload_hash": payload_hash,
        "outcome": {
            "event_batch_id": event["transaction_id"],
            "observed_stream_version": observed_version,
            "reason_code": None,
        },
    }
    _write_json(fixture.control_root / "receipts" / f"binding-advance-{payload_hash}.json", receipt)
    scope = [ACTOR_ID, "store-binding-recovery", "AdvanceStoreBinding", idempotency_key]
    authority_hash = sha256_hex(canonical_bytes({"actor_id": ACTOR_ID, "action": binding["owner_action"]}))
    _write_json(
        fixture.control_root / "receipts" / "idempotency" / f"{sha256_hex(canonical_bytes(scope))}.json",
        {
            "schema_id": "ars://core/authority-receipt-index",
            "schema_version": "1.2.0",
            "scope": scope,
            "payload_hash": payload_hash,
            "authority_grant_sha256": authority_hash,
            "receipt": receipt,
            "project_id": PROJECT_ID,
            "target_stream_id": PROJECT_ID,
            "expected_stream_version": observed_version - 1,
        },
    )
    _write_json(fixture.control_root / "manifests" / "binding-repair-current.json", binding)
    return binding_sha256


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
    with pytest.raises(ConflictError, match="changed during the operation"):
        verified.revalidate()


def test_current_binding_translates_a_missing_foundation_control_root(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    foundation = yaml.safe_load(fixture.foundation_path.read_text(encoding="utf-8"))
    foundation["control_root"] = str(tmp_path / "missing-control-root")
    foundation["foundation_sha256"] = sha256_hex(
        canonical_bytes({key: value for key, value in foundation.items() if key != "foundation_sha256"})
    )
    fixture.foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="identity differs from the repository foundation"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_verified_current_binding_does_not_expose_mutable_admission_evidence(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    verified = load_current_binding(
        foundation_path=fixture.foundation_path,
        repository_root=fixture.repository_root,
        expected_control_root=fixture.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=str(fixture.binding["store_identity"]),
    )

    exposed_binding = verified.binding
    exposed_binding["git_head"] = "0" * 40
    exposed_binding["route"]["sha256"] = "0" * 64
    exposed_manifest = verified.manifest
    exposed_manifest["project_id"] = "prj_mutated"

    assert verified.binding["git_head"] == fixture.binding["git_head"]
    assert verified.binding["route"] == fixture.binding["route"]
    assert verified.manifest["project_id"] == PROJECT_ID


def test_clean_descendant_and_reviewed_successor_validate_their_exact_transition(tmp_path: Path) -> None:
    from research_system.store.current_binding import _validate_binding_transition

    fixture = _bound_fixture(tmp_path)
    object_root = fixture.control_root / "objects" / "binding-repair"
    predecessor_sha256 = str(fixture.binding["predecessor_binding_sha256"])
    predecessor = json.loads((object_root / f"sha256-{predecessor_sha256}.json").read_bytes())
    (fixture.repository_root / "docs-only.txt").write_text("documentation\n", encoding="utf-8")
    _git(fixture.repository_root, "add", "docs-only.txt")
    _git(fixture.repository_root, "commit", "-m", "documentation descendant")
    descendant = {
        **fixture.binding,
        "git_head": _git(fixture.repository_root, "rev-parse", "HEAD"),
        "git_tree": _git(fixture.repository_root, "rev-parse", "HEAD^{tree}"),
    }

    _validate_binding_transition(
        fixture.repository_root,
        fixture.control_root,
        descendant,
        predecessor,
        predecessor_sha256,
    )

    changed_route = {**descendant, "route": {**descendant["route"], "sha256": "1" * 64}}
    with pytest.raises(IntegrityError, match="governed evidence"):
        _validate_binding_transition(
            fixture.repository_root,
            fixture.control_root,
            changed_route,
            predecessor,
            predecessor_sha256,
        )

    unrelated_head = _git(
        fixture.repository_root,
        "commit-tree",
        str(descendant["git_tree"]),
        "-m",
        "unrelated root",
    )
    unrelated = {**descendant, "git_head": unrelated_head}
    with pytest.raises(IntegrityError, match="not a clean Git descendant"):
        _validate_binding_transition(
            fixture.repository_root,
            fixture.control_root,
            unrelated,
            predecessor,
            predecessor_sha256,
        )

    fixture_binding_sha256 = sha256_hex(fixture.binding_raw)
    reviewed = {
        **unrelated,
        "owner_action": "advance-reviewed-route-successor-store-binding",
        "predecessor_binding_sha256": fixture_binding_sha256,
        "route": {**unrelated["route"], "sha256": "2" * 64},
        "route_successor_authority": {
            "predecessor_binding_sha256": fixture_binding_sha256,
            "candidate_git_head": unrelated_head,
            "predecessor_route_sha256": fixture.binding["route"]["sha256"],
            "successor_route_sha256": "2" * 64,
        },
    }
    _validate_binding_transition(
        fixture.repository_root,
        fixture.control_root,
        reviewed,
        fixture.binding,
        fixture_binding_sha256,
    )

    repeated = {
        **reviewed,
        "command_payload_hash": sha256_hex(canonical_bytes({"fixture": "repeated-reviewed-successor"})),
        "idempotency_key": "gate6-repeated-reviewed-successor",
        "predecessor_binding_sha256": sha256_hex(canonical_bytes(reviewed)),
        "route_successor_authority": {
            **reviewed["route_successor_authority"],
            "predecessor_binding_sha256": sha256_hex(canonical_bytes(reviewed)),
            "predecessor_route_sha256": reviewed["route"]["sha256"],
        },
    }
    with pytest.raises(IntegrityError, match="clean legacy predecessor"):
        _validate_binding_transition(
            fixture.repository_root,
            fixture.control_root,
            repeated,
            reviewed,
            sha256_hex(canonical_bytes(reviewed)),
        )

    for field, wrong in (
        ("predecessor_binding_sha256", "3" * 64),
        ("candidate_git_head", "4" * 40),
        ("predecessor_route_sha256", "5" * 64),
        ("successor_route_sha256", "6" * 64),
    ):
        attacked = {
            **reviewed,
            "route_successor_authority": {**reviewed["route_successor_authority"], field: wrong},
        }
        with pytest.raises(IntegrityError, match="reviewed route successor authority"):
            _validate_binding_transition(
                fixture.repository_root,
                fixture.control_root,
                attacked,
                fixture.binding,
                fixture_binding_sha256,
            )


def test_current_binding_rejects_a_corrupted_historical_binding_event(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    first_binding_event = tuple(fixture.ledger.iter_events())[-1]
    successor = {
        **fixture.binding,
        "command_payload_hash": sha256_hex(canonical_bytes({"fixture": "second-current-binding"})),
        "idempotency_key": "gate6-second-current-binding-fixture",
        "predecessor_binding_sha256": sha256_hex(fixture.binding_raw),
    }
    _publish_binding_advance(fixture, successor)
    events = _rewrite_event_at_position(
        fixture,
        int(first_binding_event["global_position"]),
        command_schema_sha256="f" * 64,
    )

    with pytest.raises(IntegrityError, match="command schema identity mismatch"):
        replay_discovery(events, schemas=fixture.schemas)
    with pytest.raises(IntegrityError, match="event schema provenance"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_current_binding_requires_the_registered_binding_event_schema(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    _rewrite_last_event(fixture, schema_id="ars://core/event")

    with pytest.raises(IntegrityError, match="event schema provenance"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


@pytest.mark.parametrize(
    ("field", "wrong"),
    (
        ("command_id", "binding-advance-wrong"),
        ("project_id", "prj_wrong"),
        ("stream_id", "prj_wrong"),
        ("actor_id", "act_01978abc-4999-7000-8000-000000004999"),
        ("idempotency_key", "wrong-idempotency-key"),
        ("authority_grant_id", "wrong-authority"),
    ),
)
def test_current_binding_rejects_event_provenance_not_bound_to_the_object(
    tmp_path: Path,
    field: str,
    wrong: str,
) -> None:
    fixture = _bound_fixture(tmp_path)
    _rewrite_last_event(fixture, **{field: wrong})

    with pytest.raises(IntegrityError, match="event provenance"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_current_binding_rejects_scoped_index_from_another_stream_predecessor(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    index_path = next((fixture.control_root / "receipts" / "idempotency").glob("*.json"))
    index = json.loads(index_path.read_bytes())
    index["expected_stream_version"] = 99
    index_path.write_bytes(canonical_bytes(index))

    with pytest.raises(IntegrityError, match="scoped receipt"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_current_binding_rejects_an_advance_forked_from_the_preceding_binding_event(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    preceding_binding_sha256 = sha256_hex(fixture.binding_raw)
    fork = {
        **fixture.binding,
        "command_payload_hash": sha256_hex(canonical_bytes({"fixture": "forked-current-binding"})),
        "idempotency_key": "gate6-fork-binding-fixture",
    }
    assert fork["predecessor_binding_sha256"] != preceding_binding_sha256
    _publish_binding_advance(fixture, fork)

    with pytest.raises(IntegrityError, match="binding advance event continuity"):
        replay_discovery(tuple(fixture.ledger.iter_events()), schemas=fixture.schemas)
    with pytest.raises(IntegrityError, match="binding event lineage"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_current_binding_lineage_rejects_a_later_repair_root() -> None:
    from research_system.store.current_binding import _validate_binding_event_lineage

    with pytest.raises(IntegrityError, match="binding event lineage"):
        _validate_binding_event_lineage(
            [
                {"event_type": "StoreBindingAdvanced", "payload": {"recovery_binding_sha256": "a" * 64}},
                {"event_type": "StoreBindingRepaired", "payload": {"recovery_binding_sha256": "b" * 64}},
            ]
        )


def test_current_binding_rejects_hidden_modified_schema_history_inputs(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    schema_root = fixture.repository_root / ".research-system" / "schemas"
    command = fixture.schemas.command_binding("AdvanceStoreBinding")
    assert command is not None
    active = fixture.schemas.resolve_identity(command.schema_id, command.schema_version)
    altered_schema = json.loads(active.raw_bytes)
    altered_schema["description"] = "hidden alternate historical command bytes"
    altered_raw = canonical_bytes(altered_schema)
    altered_sha256 = sha256_hex(altered_raw)
    archive_relative = Path("history") / f"sha256-{altered_sha256}.json"
    (schema_root / archive_relative).write_bytes(altered_raw)
    manifest_path = schema_root / "schema-identity-history.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["aliases"].append(
        {
            "schema_id": command.schema_id,
            "schema_version": command.schema_version,
            "raw_bytes_sha256": altered_sha256,
            "archive_ref": archive_relative.as_posix(),
        }
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    _git(
        fixture.repository_root,
        "update-index",
        "--assume-unchanged",
        ".research-system/schemas/schema-identity-history.json",
    )
    exclude_path = fixture.repository_root / ".git" / "info" / "exclude"
    exclude_path.write_text(
        exclude_path.read_text(encoding="utf-8") + f"\n/.research-system/schemas/{archive_relative.as_posix()}\n",
        encoding="utf-8",
    )
    _rewrite_last_event(fixture, command_schema_sha256=altered_sha256)
    assert _git(fixture.repository_root, "status", "--porcelain=v1", "--untracked-files=all") == ""

    with pytest.raises(IntegrityError, match="schema catalogue differs"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_current_binding_rechecks_the_exact_git_subject_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.current_binding as current_binding_module

    fixture = _bound_fixture(tmp_path)
    original = current_binding_module._validate_receipt_and_event

    def switch_clean_head_after_validation(**kwargs: object) -> None:
        original(**kwargs)
        _git(fixture.repository_root, "commit", "--allow-empty", "-m", "concurrent clean head")

    monkeypatch.setattr(
        current_binding_module,
        "_validate_receipt_and_event",
        switch_clean_head_after_validation,
    )

    with pytest.raises(IntegrityError, match="Git subject changed during admission"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


@pytest.mark.parametrize(
    ("field", "wrong"),
    (
        ("schema_id", "ars://wrong/index"),
        ("schema_version", "1.1.0"),
        ("extra", "not-exact"),
    ),
)
def test_current_binding_rejects_noncanonical_publication_receipt_indexes(
    tmp_path: Path,
    field: str,
    wrong: str,
) -> None:
    fixture = _bound_fixture(tmp_path)
    index_path = next((fixture.control_root / "receipts" / "idempotency").glob("*.json"))
    index = json.loads(index_path.read_bytes())
    index[field] = wrong
    index_path.write_bytes(canonical_bytes(index))

    with pytest.raises(IntegrityError, match="scoped receipt is invalid"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )


def test_failed_current_binding_admission_does_not_create_the_project_event_directory(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    project_events = fixture.control_root / "events" / PROJECT_ID
    shutil.rmtree(project_events)

    with pytest.raises(IntegrityError, match="project event directory is unavailable"):
        load_current_binding(
            foundation_path=fixture.foundation_path,
            repository_root=fixture.repository_root,
            expected_control_root=fixture.control_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=str(fixture.binding["store_identity"]),
        )
    assert not project_events.exists()


def test_discovery_replay_accepts_current_and_registered_historical_binding_events(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    current_events = tuple(fixture.ledger.iter_events())

    assert replay_discovery(current_events, schemas=fixture.schemas)["candidates"] == {}

    historical_events = _rewrite_last_event(
        fixture,
        command_schema_version="1.0.0",
        command_schema_sha256="5f15223aeec3cbe0825a49b5395467a62cda255378496a04fc83941557dbc3cb",
    )
    assert replay_discovery(historical_events, schemas=fixture.schemas)["candidates"] == {}


def test_discovery_replay_rejects_a_control_event_from_another_registered_command_family(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    repair = fixture.schemas.command_binding("RepairStoreBinding")
    assert repair is not None
    repair_identity = fixture.schemas.resolve_identity(repair.schema_id, repair.schema_version)
    events = _rewrite_last_event(
        fixture,
        command_schema_id=repair_identity.schema_id,
        command_schema_version=repair_identity.schema_version,
        command_schema_sha256=repair_identity.sha256,
    )

    with pytest.raises(IntegrityError, match="schema provenance mismatch"):
        replay_discovery(events, schemas=fixture.schemas)


def test_discovery_replay_binds_the_binding_object_path_to_its_recovery_digest(tmp_path: Path) -> None:
    fixture = _bound_fixture(tmp_path)
    current = tuple(fixture.ledger.iter_events())[-1]
    events = _rewrite_last_event(
        fixture,
        payload={
            **current["payload"],
            "object_path": f"objects/binding-repair/sha256-{'f' * 64}.json",
        },
    )

    with pytest.raises(IntegrityError, match="binding advance event relation"):
        replay_discovery(events, schemas=fixture.schemas)


def test_scrubbed_git_environment_forces_literal_pathspecs() -> None:
    environment = scrubbed_git_environment(
        {
            "PATH": "preserved",
            "GIT_GLOB_PATHSPECS": "1",
            "git_noglob_pathspecs": "1",
            "Git_Icase_Pathspecs": "1",
            "GIT_LITERAL_PATHSPECS": "0",
        }
    )

    assert environment["PATH"] == "preserved"
    assert environment["GIT_LITERAL_PATHSPECS"] == "1"
    assert not any(
        key.casefold()
        in {
            "git_glob_pathspecs",
            "git_noglob_pathspecs",
            "git_icase_pathspecs",
        }
        for key in environment
    )


def test_binding_events_require_the_validated_service_continuation(tmp_path: Path) -> None:
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    ledger = EventLedger(tmp_path / "control", PROJECT_ID, schemas, store_identity="a" * 64)
    command = schemas.command_binding("AdvanceStoreBinding")
    assert command is not None
    identity = schemas.resolve_identity(command.schema_id, command.schema_version)
    with pytest.raises(TypeError, match="session"):
        ledger._append_binding_repair_from_validated_service(  # type: ignore[call-arg]
            {},
            snapshot=ledger.snapshot(),
        )
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
