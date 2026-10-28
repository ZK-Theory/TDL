# Research context: docs/plans/agentic-research-system/transition/w9/wp9-2-design-note.md (WP9.2-2; P-076, P-077, P-078)
# Purpose: W9 genesis through the real LegacyRuntime on scratch stores: shared replay, retries, guards and W9-T20.
"""W9 legacy runtime integration tests (06v WP9.2; design note §§2, 7, 9).

Every store here is a scratch store a test creates under ``tmp_path`` (P-076 item 3). Each scratch store gets a 1.0.0
store-identity manifest, which may carry an arbitrary identity (06v §2.6), so the Gate 6 refusal has a manifest to
read. W11 genesis goes through the Discovery test harness; W9 genesis goes through the real ``LegacyRuntime``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.routes import shared_event_partition
from research_system.errors import ArsError, IntegrityError
from research_system.ids import new_id
from research_system.legacy.accepted_w9 import (
    ACCEPTED,
    CATALOGUE_STREAM_ID,
    RESERVED_IDS,
    accepted_genesis_payload,
)
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.runtime import (
    GATE6_REASON_CODE,
    LegacyRuntime,
    W9Gate6StoreRefused,
    refuse_gate6_lock_roots,
)
from research_system.projection.replay import rebuild_projection
from research_system.projection.replay import replay as replay_projection
from research_system.discovery.runtime import replay_discovery
from tests.research_system.factories import ACTORS, PROJECT_ID, activate_lifecycle_grant
from tests.research_system.integration.test_wp6_6_discovery_runtime import (
    _HARNESSES,
    _genesis,
    _rehash_events,
    _runtime,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTOR_ID = ACTORS["actor-a"]
GATE6 = ACCEPTED["gate6_store_identity"]
SCRATCH_IDENTITY = "a" * 64
# The resolver's refusal of a grant scoped to another subject (authority.py, resolve_lifecycle_command).
SUBJECT_MISMATCH = "authority subject scope mismatch"


def _write_manifest(control_root: Path, store_identity: str, *, recorded_root: Path | None = None) -> None:
    """Write a 1.0.0 scratch store-identity manifest (06v §2.6) into a control root."""
    manifest = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "store_identity": store_identity,
        "control_root": str((recorded_root or control_root).resolve()),
        "code_roots": [str(REPO_ROOT)],
        "endpoint_scheme": "local-cli",
    }
    manifest["manifest_hash"] = sha256_hex(canonical_bytes(manifest))
    path = control_root / "manifests" / "store-identity.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(manifest))


def _grant(
    harness: Any,
    command_type: str,
    subject_id: str,
    *,
    classes: tuple[str, ...] = ("human",),
    actor_id: str = ACTOR_ID,
) -> str:
    raw = bytearray(hashlib.sha256(f"w9:{command_type}:{subject_id}:{classes}:{actor_id}".encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    grant_id = f"agr_{uuid.UUID(bytes=bytes(raw))}"
    activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=subject_id,
        actor_id=actor_id,
        allowed_actor_classes=classes,
        command_types=(command_type,),
        grant_id=grant_id,
    )
    return grant_id


def _store(tmp_path: Path, *, w11: bool = True, store_identity: str = SCRATCH_IDENTITY, **kwargs: Any):
    """A scratch store with (optionally) W11 genesis, its manifest, and a LegacyRuntime bound to it."""
    discovery = _runtime(tmp_path)
    if w11:
        discovery.submit(_genesis())
    harness = _HARNESSES[tmp_path]
    _write_manifest(harness.ledger.control_root, store_identity)
    root = tmp_path / "legacy"
    root.mkdir(exist_ok=True)
    runtime = LegacyRuntime(
        root,
        harness.ledger,
        harness.schemas,
        repository_root=REPO_ROOT,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
        **kwargs,
    )
    return runtime, harness


def _genesis_command(harness: Any, **overrides: Any) -> dict[str, Any]:
    target = overrides.pop("target_stream_id", CATALOGUE_STREAM_ID)
    command = {
        "command_id": new_id("command"),
        "command_type": "ImportAcceptedW9CatalogueGenesis",
        "actor_id": ACTOR_ID,
        "authority_grant_id": _grant(harness, "ImportAcceptedW9CatalogueGenesis", target),
        "idempotency_key": "wp9.2:w9-genesis:v1",
        "target_stream_id": target,
        "expected_stream_version": 0,
        "payload": accepted_genesis_payload(),
    }
    command.update(overrides)
    return command


def _tree_bytes(root: Path) -> dict[str, bytes | None]:
    """Every file's bytes and every directory (as ``None``) under ``root``, so a created directory shows (review F-4)."""
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None for path in sorted(root.rglob("*"))
    }


# --- Genesis and shared replay ---------------------------------------------------------------------------------------


def test_w9_c01_lr_001_genesis_and_shared_replay(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    receipt = runtime.submit(_genesis_command(harness))
    assert receipt.status == "accepted"
    events = tuple(harness.ledger.iter_events())
    w9 = [event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis"]
    assert [event["event_type"] for event in w9] == ["W9CatalogueGenesisImported"]
    assert w9[0]["payload"] == accepted_genesis_payload()
    assert w9[0]["schema_id"] == "ars://core/event"
    assert shared_event_partition(w9[0]) == "legacy"
    # The generic boundary (also the verify-restore path, operations/backups.py), rebuild and Discovery all replay.
    replay_projection(events, schema_registry=harness.schemas)
    rebuild_projection(events, tmp_path / "out" / "projection.json", harness.schemas)
    replay_discovery(events, schemas=harness.schemas)
    legacy = replay_legacy(events, schemas=harness.schemas)
    assert legacy["catalogue"] == accepted_genesis_payload()
    assert set(legacy["reserved_ids"]) == RESERVED_IDS
    assert legacy["row_counts"] == {"LR-001": 1}


def test_w9_c11_lr_001_retry_returns_the_original_receipt(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    command = _genesis_command(harness)
    first = runtime.submit(command)
    before = tuple(harness.ledger.iter_events())
    assert runtime.submit(deepcopy(command)) == first
    assert tuple(harness.ledger.iter_events()) == before


def test_second_genesis_is_refused(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    second = _genesis_command(harness, idempotency_key="wp9.2:w9-genesis:second")
    receipt = runtime.submit(second)
    # The stream is at version 1, so a second request at version 0 is a stream conflict ...
    assert receipt.status == "conflict"
    # ... and one at version 1 reaches the guard.
    with pytest.raises(IntegrityError, match="second W9 genesis"):
        runtime.submit(_genesis_command(harness, idempotency_key="wp9.2:w9-genesis:third", expected_stream_version=1))


def test_genesis_requires_w11_genesis(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path, w11=False)
    with pytest.raises(IntegrityError, match="requires the W11 catalogue in the replayed Discovery projection"):
        runtime.submit(_genesis_command(harness))


def test_genesis_refuses_a_wrong_target_stream(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    with pytest.raises(IntegrityError, match="W9 genesis stream identity mismatch"):
        runtime.submit(_genesis_command(harness, target_stream_id=new_id("scope_definition")))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(activation_status="executed"),
        lambda payload: payload["bootstrap_contract_identity"].update(git_blob="0" * 40),
        lambda payload: payload.update(requested_genesis_transaction_id="txb_other"),
        lambda payload: payload["verification_requirements"].pop(),
    ],
)
def test_w9_c03_lr_001_owner_row_mutation_is_refused_before_binding(tmp_path: Path, mutate: Any) -> None:
    runtime, harness = _store(tmp_path)
    command = _genesis_command(harness)
    mutate(command["payload"])
    lock_root = tmp_path / "legacy"
    before = _tree_bytes(lock_root)
    with pytest.raises(IntegrityError, match="W9 genesis payload differs from the accepted identity"):
        runtime.submit(command)
    assert _tree_bytes(lock_root) == before


@pytest.mark.parametrize("prefix", ["catalogue", "annex", "bootstrap", "envelope"])
def test_genesis_refuses_tampered_accepted_bytes(tmp_path: Path, prefix: str) -> None:
    repository = tmp_path / "repo"
    for key in ("catalogue", "annex", "bootstrap", "envelope"):
        path = repository / ACCEPTED[f"{key}_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / ACCEPTED[f"{key}_path"], path)
    tampered = repository / ACCEPTED[f"{prefix}_path"]
    tampered.write_bytes(tampered.read_bytes() + b" ")
    runtime, harness = _store(tmp_path)
    runtime.repository_root = repository.resolve()
    with pytest.raises(IntegrityError, match="W9 accepted file identity mismatch"):
        runtime.submit(_genesis_command(harness))
    assert not any(
        event["command_type"] == "ImportAcceptedW9CatalogueGenesis" for event in harness.ledger.iter_events()
    )


def test_genesis_grant_must_be_scoped_to_the_catalogue_stream(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    command = _genesis_command(harness)
    command["authority_grant_id"] = _grant(harness, "ImportAcceptedW9CatalogueGenesis", new_id("scope_definition"))
    with pytest.raises(ArsError, match=SUBJECT_MISMATCH):
        runtime.submit(command)


def _non_owner_genesis(harness: Any, classes: tuple[str, ...]) -> dict[str, Any]:
    """A genesis command from a non-owner actor whose owner-issued grant names ``classes``.

    The owner's actor class is human whatever its grant says, so only a non-owner reaches the scoped actor class that
    the genesis guard reads (review F-1).
    """
    actor_id = ACTORS["actor-b"]
    return _genesis_command(
        harness,
        actor_id=actor_id,
        authority_grant_id=_grant(
            harness, "ImportAcceptedW9CatalogueGenesis", CATALOGUE_STREAM_ID, classes=classes, actor_id=actor_id
        ),
    )


def test_genesis_by_a_non_owner_with_an_agent_class_grant_is_refused(tmp_path: Path) -> None:
    """Design note §3 n-4 and §9: a genesis grant with an actor class other than exactly human is refused."""
    runtime, harness = _store(tmp_path)
    with pytest.raises(IntegrityError, match="W9 genesis requires a human actor"):
        runtime.submit(_non_owner_genesis(harness, ("agent",)))
    assert not any(
        event["command_type"] == "ImportAcceptedW9CatalogueGenesis" for event in harness.ledger.iter_events()
    )


def test_genesis_by_a_non_owner_with_a_human_class_grant_is_accepted(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    assert runtime.submit(_non_owner_genesis(harness, ("human",))).status == "accepted"


# --- W9-T20: the Gate 6 store refusal, before any lock ---------------------------------------------------------------


def test_w9_t20_the_frozen_identity_at_its_own_path_is_refused(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path, store_identity=GATE6)
    command = _genesis_command(harness)
    roots = (tmp_path / "legacy", harness.ledger.control_root)
    before = [_tree_bytes(root) for root in roots]
    with pytest.raises(W9Gate6StoreRefused, match=GATE6_REASON_CODE) as refused:
        runtime.submit(command)
    assert refused.value.reason_code == GATE6_REASON_CODE
    assert [_tree_bytes(root) for root in roots] == before


def test_w9_t20_a_byte_copy_at_a_second_path_is_refused(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    # The manifest records another control root, as a byte copy of the Gate 6 store would.
    _write_manifest(harness.ledger.control_root, GATE6, recorded_root=tmp_path / "elsewhere")
    command = _genesis_command(harness)
    roots = (tmp_path / "legacy", harness.ledger.control_root)
    before = [_tree_bytes(root) for root in roots]
    with pytest.raises(W9Gate6StoreRefused, match=GATE6_REASON_CODE):
        runtime.submit(command)
    assert [_tree_bytes(root) for root in roots] == before


def test_w9_t20_a_different_identity_passes_the_refusal(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path, store_identity="b" * 64)
    assert runtime.submit(_genesis_command(harness)).status == "accepted"


def test_a_store_without_a_readable_manifest_is_refused(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    (harness.ledger.control_root / "manifests" / "store-identity.json").unlink()
    with pytest.raises(IntegrityError, match="cannot read the target store identity"):
        runtime.submit(_genesis_command(harness))


def test_constructing_the_runtime_writes_nothing(tmp_path: Path) -> None:
    """Review F-4: the receipt store is built after the refusal, not at construction."""
    _, harness = _store(tmp_path)
    root = tmp_path / "receipts-root"
    root.mkdir()
    LegacyRuntime(
        root,
        harness.ledger,
        harness.schemas,
        repository_root=REPO_ROOT,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert _tree_bytes(root) == {}


def test_w9_t20_a_scratch_ledger_nested_inside_the_gate6_store_is_refused(tmp_path: Path) -> None:
    """CodeRabbit on PR #408: the ledger root's own scratch manifest must not hide a Gate 6 manifest above it."""
    gate6_root = tmp_path / "gate6-control"
    _write_manifest(gate6_root, GATE6)
    ledger_root = gate6_root / "scratch"
    _write_manifest(ledger_root, SCRATCH_IDENTITY)
    receipt_root = tmp_path / "elsewhere" / "legacy"
    receipt_root.mkdir(parents=True)
    with pytest.raises(W9Gate6StoreRefused, match=GATE6_REASON_CODE):
        refuse_gate6_lock_roots(ledger_root, (receipt_root,), {GATE6})


def test_w9_t20_an_unreadable_manifest_path_above_a_lock_root_is_refused(tmp_path: Path) -> None:
    """CodeRabbit on PR #408: a manifest path that is a directory is read and refused, not skipped."""
    ledger_root = tmp_path / "control"
    _write_manifest(ledger_root, SCRATCH_IDENTITY)
    odd_root = tmp_path / "odd"
    (odd_root / "manifests" / "store-identity.json").mkdir(parents=True)
    receipt_root = odd_root / "legacy"
    receipt_root.mkdir()
    with pytest.raises(IntegrityError, match="cannot read the target store identity"):
        refuse_gate6_lock_roots(ledger_root, (receipt_root,), {GATE6})


@pytest.mark.parametrize("inside", [False, True], ids=["at-the-root", "below-the-root"])
def test_w9_t20_a_receipt_root_in_the_gate6_store_is_refused(tmp_path: Path, inside: bool) -> None:
    """Review F-4: a scratch ledger cannot carry the lock into the Gate 6 store through the receipt root."""
    _, harness = _store(tmp_path)
    gate6_root = tmp_path / "gate6-control"
    _write_manifest(gate6_root, GATE6)
    receipt_root = gate6_root / "legacy" if inside else gate6_root
    receipt_root.mkdir(exist_ok=True)
    runtime = LegacyRuntime(
        receipt_root,
        harness.ledger,
        harness.schemas,
        repository_root=REPO_ROOT,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
    )
    before = _tree_bytes(gate6_root)
    with pytest.raises(W9Gate6StoreRefused, match=GATE6_REASON_CODE):
        runtime.submit(_genesis_command(harness))
    assert _tree_bytes(gate6_root) == before


# --- Unbound W9 commands ---------------------------------------------------------------------------------------------


def test_a_w9_command_without_a_binding_row_is_refused(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    command = _genesis_command(
        harness, command_type="ObserveLegacyRecord", payload={"record_id": new_id("scope_definition")}
    )
    with pytest.raises(IntegrityError, match="inactive W9 command binding: ObserveLegacyRecord"):
        runtime.submit(command)


# --- The asymmetry (design note §2.5) --------------------------------------------------------------------------------


def test_a_discovery_command_over_an_invalid_legacy_half_is_refused_at_the_next_generic_replay(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    events = list(deepcopy(tuple(harness.ledger.iter_events())))
    w9 = next(event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis")
    w9["payload"]["activation_status"] = "executed"
    tampered = _rehash_events(tuple(events))
    # Discovery's own pre-command replay never runs replay_legacy ...
    replay_discovery(tampered, schemas=harness.schemas)
    # ... but the next generic replay refuses the store, at site 4: the tampered genesis fails its record schema.
    with pytest.raises(IntegrityError, match="W9 event payload does not validate against its record schema"):
        replay_projection(tampered, schema_registry=harness.schemas)


# --- Genesis guards 2, 5 and 8 (design note §7.3; review F-6) --------------------------------------------------------


def test_genesis_guard_2_refuses_a_w11_catalogue_other_than_the_required_one(tmp_path: Path, monkeypatch) -> None:
    import research_system.legacy.runtime as legacy_runtime

    def other_w11(events: Any, **kwargs: Any) -> dict[str, Any]:
        state = replay_discovery(events, **kwargs)
        state["catalogue"] = {**state["catalogue"], "catalogue_blob": "0" * 40}
        return state

    runtime, harness = _store(tmp_path)
    monkeypatch.setattr(legacy_runtime, "replay_discovery", other_w11)
    with pytest.raises(IntegrityError, match="is not the W9 genesis's required W11 catalogue"):
        runtime.submit(_genesis_command(harness))


def test_genesis_guard_5_refuses_a_stream_version_other_than_zero(tmp_path: Path) -> None:
    """Guard 5 is defence in depth: through ``submit`` a version other than 0 meets a stream conflict or guard 3 first.

    No W9 command but genesis can write the catalogue stream, so the guard is called directly with an empty legacy
    projection and the replayed Discovery projection, which is what reaching it would take.
    """
    from research_system.command.models import Command

    runtime, harness = _store(tmp_path)
    discovery = replay_discovery(tuple(harness.ledger.iter_events()), schemas=harness.schemas)
    command = Command(_genesis_command(harness, expected_stream_version=1))
    with pytest.raises(IntegrityError, match="W9 genesis stream version mismatch"):
        runtime._prepare_genesis(command, discovery, {"catalogue": None})


def test_genesis_guard_8_refuses_a_route_registry_that_does_not_partition_the_catalogue(
    tmp_path: Path, monkeypatch
) -> None:
    import research_system.legacy.routes as legacy_routes

    runtime, harness = _store(tmp_path)
    deferred = dict(legacy_routes.LEGACY_DEFERRED_ROWS)
    deferred.pop("LR-061")
    monkeypatch.setattr(legacy_routes, "LEGACY_DEFERRED_ROWS", deferred)
    with pytest.raises(IntegrityError, match="W9 route registry does not partition the accepted W9 catalogue"):
        runtime.submit(_genesis_command(harness))


# --- LR-002 on the test registry (design note §§3, 9): inert in production ------------------------------------------


def _revision() -> dict[str, Any]:
    identity = accepted_genesis_payload()["bootstrap_contract_identity"]
    return {
        "schema_id": "ars://legacy/import-accepted-w9-catalogue-revision",
        "schema_version": "1.0.0",
        "bootstrap_contract_identity": identity,
        "superseded_catalogue_identity": {
            "repository_path": ACCEPTED["catalogue_path"],
            "git_commit": ACCEPTED["accepted_commit"],
            "git_blob": ACCEPTED["catalogue_blob"],
            "file_length": ACCEPTED["catalogue_bytes"],
            "file_sha256": ACCEPTED["catalogue_sha256"],
        },
        "revision_envelope_identity": {**identity, "repository_path": "test/revision-envelope.json"},
        "row_supersessions": [{"superseded_owner_row_id": "LR-015", "replacing_owner_row_id": "LR-062"}],
        "requested_transaction_id": "w9-revision-request-test",
        "refused_store_identities": [GATE6],
        "verification_requirements": ["test revision"],
        "activation_status": "not_executed",
    }


def _revision_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, accepted: tuple[dict[str, Any], ...]):
    import research_system.authority as authority_module
    import research_system.legacy.replay.driver as legacy_driver
    import research_system.schema_registry as registry_module
    from research_system.schema_registry import SchemaBinding

    # The test registry is in place before the scratch store is built, so every registry in the harness carries it.
    monkeypatch.setattr(
        registry_module,
        "_RUNTIME_BINDINGS",
        (
            *registry_module._RUNTIME_BINDINGS,
            SchemaBinding("ars://core/command", "1.0.0", command_type="ImportAcceptedW9CatalogueRevision"),
        ),
    )
    cached = registry_module._runtime_registry_for_resolved_root
    if hasattr(cached, "cache_clear"):
        cached.cache_clear()
    monkeypatch.setitem(
        authority_module._SCOPED_COMMAND_SUBJECT_KINDS, "ImportAcceptedW9CatalogueRevision", "scope_definition"
    )
    monkeypatch.setattr(
        legacy_driver,
        "replay_legacy",
        lambda events, **kwargs: replay_legacy(
            events, routed_rows={"LR-001", "LR-002"}, accepted_revisions=accepted, **kwargs
        ),
    )
    runtime, harness = _store(tmp_path, routed_rows={"LR-001", "LR-002"}, accepted_revisions=accepted)
    runtime.submit(_genesis_command(harness))
    return runtime, harness


def _revision_command(harness: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return _genesis_command(
        harness,
        command_type="ImportAcceptedW9CatalogueRevision",
        authority_grant_id=_grant(harness, "ImportAcceptedW9CatalogueRevision", CATALOGUE_STREAM_ID),
        idempotency_key="wp9.2:w9-revision:test",
        expected_stream_version=1,
        payload=payload,
    )


@pytest.fixture
def _clear_registry_cache() -> Any:
    yield
    import research_system.schema_registry as registry_module

    cached = registry_module._runtime_registry_for_resolved_root
    if hasattr(cached, "cache_clear"):
        cached.cache_clear()


def test_w9_c01_and_c11_lr_002_on_the_test_registry(tmp_path: Path, monkeypatch, _clear_registry_cache) -> None:
    revision = _revision()
    runtime, harness = _revision_store(tmp_path, monkeypatch, accepted=(revision,))
    command = _revision_command(harness, deepcopy(revision))
    receipt = runtime.submit(command)
    assert receipt.status == "accepted"
    before = tuple(harness.ledger.iter_events())
    assert runtime.submit(deepcopy(command)) == receipt
    assert tuple(harness.ledger.iter_events()) == before
    state = replay_legacy(
        before, schemas=runtime.schemas, routed_rows={"LR-001", "LR-002"}, accepted_revisions=(revision,)
    )
    assert state["catalogue_revisions"] == [revision]


def test_w9_c03_lr_002_an_unaccepted_revision_is_refused(tmp_path: Path, monkeypatch, _clear_registry_cache) -> None:
    revision = _revision()
    runtime, harness = _revision_store(tmp_path, monkeypatch, accepted=(revision,))
    mutated = deepcopy(revision)
    mutated["row_supersessions"][0]["replacing_owner_row_id"] = "LR-063"
    with pytest.raises(IntegrityError, match="not an accepted revision"):
        runtime.submit(_revision_command(harness, mutated))


def test_lr_002_is_refused_in_production(tmp_path: Path) -> None:
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    command = _genesis_command(
        harness,
        command_type="ImportAcceptedW9CatalogueRevision",
        idempotency_key="wp9.2:w9-revision:production",
        expected_stream_version=1,
        payload=_revision(),
    )
    with pytest.raises(IntegrityError, match="inactive W9 command binding: ImportAcceptedW9CatalogueRevision"):
        runtime.submit(command)


# --- CLI (design note §8) --------------------------------------------------------------------------------------------


def test_cli_legacy_status_and_show_are_read_only(tmp_path: Path, monkeypatch, capsys) -> None:
    from research_system import cli

    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    bindings: list[dict[str, Any]] = []

    def bind(root: Path, **kwargs: Any) -> Any:
        bindings.append(kwargs)
        return harness.ledger, harness.schemas, harness.authority_resolver

    monkeypatch.setattr(cli, "_verified_ledger", bind)
    control_root = harness.ledger.control_root
    before = _tree_bytes(control_root)
    assert cli.main(["legacy", "status", "--control-root", str(control_root)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["genesis_present"] is True
    assert status["row_counts"] == {"LR-001": 1}
    assert status["event_count"] == 1
    assert set(status["reserved_ids"]) == RESERVED_IDS
    decision = sorted(RESERVED_IDS)[0]
    assert cli.main(["legacy", "show", decision, "--control-root", str(control_root)]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "reserved_external_ref"
    assert cli.main(["legacy", "show", new_id("scope_definition"), "--control-root", str(control_root)]) == 1
    assert _tree_bytes(control_root) == before
    # Every binding the CLI made was read-only (Codex on PR #408).
    assert bindings and all(kwargs == {"read_only": True} for kwargs in bindings)


def test_cli_read_only_binding_refuses_a_missing_event_directory(tmp_path: Path, monkeypatch) -> None:
    """Codex on PR #408: a read-only query neither recreates a missing event directory nor reports an empty ledger."""
    from types import SimpleNamespace

    from research_system import cli

    control_root = tmp_path / "control"
    (control_root / "manifests").mkdir(parents=True)
    # The binding's inputs are stubbed: the test is about the directories, and must not read the canonical foundation.
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: tmp_path / "foundation.json")
    monkeypatch.setattr(
        cli.ApprovedProjectBinding,
        "load",
        lambda path: SimpleNamespace(origin_witness=None, origin_witness_path=None),
    )
    monkeypatch.setattr(
        cli,
        "load_store_manifest",
        lambda root, **kwargs: {"project_id": PROJECT_ID, "store_identity": SCRATCH_IDENTITY},
    )
    monkeypatch.setattr(cli, "_schemas_for_store_manifest", lambda manifest: None)
    before = _tree_bytes(control_root)
    with pytest.raises(IntegrityError, match="store project event directory is missing"):
        cli._verified_ledger(control_root, read_only=True)
    assert _tree_bytes(control_root) == before


def test_cli_legacy_status_refuses_the_gate6_store_before_binding(tmp_path: Path, monkeypatch, capsys) -> None:
    from research_system import cli

    _, harness = _store(tmp_path, store_identity=GATE6)

    def bind(root: Path) -> Any:
        raise AssertionError("bound a refused store")

    monkeypatch.setattr(cli, "_verified_ledger", bind)
    assert cli.main(["legacy", "status", "--control-root", str(harness.ledger.control_root)]) == 1
    assert GATE6_REASON_CODE in capsys.readouterr().err
