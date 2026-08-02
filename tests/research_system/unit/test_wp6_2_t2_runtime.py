from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
import threading
from typing import Any

import pytest

import research_system.command.t2 as t2_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.command.t2 import T2Receipt
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.projection.replay import rebuild_projection, replay
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    AUTHORITY_GRANT_ID,
    PROJECT_ID,
    REPO_ROOT,
)

UUIDS = {
    "cost": "019f8d00-0001-7000-8000-000000000001",
    "resource": "019f8d00-0002-7000-8000-000000000002",
    "task": "019f8d00-0003-7000-8000-000000000003",
    "dispatch": "019f8d00-0004-7000-8000-000000000004",
    "attempt": "019f8d00-0005-7000-8000-000000000005",
    "provider": "019f8d00-0006-7000-8000-000000000006",
    "secret": "019f8d00-0007-7000-8000-000000000007",
    "route": "019f8d00-0008-7000-8000-000000000008",
    "profile": "019f8d00-0009-7000-8000-000000000009",
    "rate": "019f8d00-000a-7000-8000-00000000000a",
    "receipt": "019f8d00-000b-7000-8000-00000000000b",
    "zero": "019f8d00-000c-7000-8000-00000000000c",
}
DIGESTS = {name: sha256_hex(name.encode()) for name in UUIDS}
COST_GRANT_ID = f"cgr_{UUIDS['cost']}"
RESOURCE_GRANT_ID = f"rgr_{UUIDS['resource']}"
TASK_ID = f"tsk_{UUIDS['task']}"
DISPATCH_ID = f"dsp_{UUIDS['dispatch']}"
ATTEMPT_ID = f"att_{UUIDS['attempt']}"
PROVIDER_COMMAND_ID = f"pcmd_{UUIDS['provider']}"
SECRET_REFERENCE_ID = f"srf_{UUIDS['secret']}"
RATE_EVIDENCE_ID = f"rat_{UUIDS['rate']}"
PROVIDER_RECEIPT_ID = f"prcp_{UUIDS['receipt']}"
ZERO_AUTHORITY = {
    "subject_id": f"zca_{UUIDS['zero']}",
    "subject_revision": 1,
    "subject_hash": DIGESTS["zero"],
}
NOW = datetime(2026, 7, 23, 12, tzinfo=UTC)
SCHEMAS = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")


def _subject(
    kind: str,
    subject_id: str,
    revision: int,
    content_hash: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": subject_id,
        "revision": revision,
        "content_hash": content_hash,
        f"{kind}_id": subject_id,
        f"{kind}_revision": revision,
        f"{kind}_hash": content_hash,
        **extra,
    }


def _resolved_provider_receipt(
    *,
    actual_input: int = 4,
    actual_output: int = 2,
    reserved_cost: int = 20,
    consumed_cost: int = 8,
) -> dict[str, Any]:
    actual_total = actual_input + actual_output
    reservation_id = "crs_019f8d10-0002-7000-8000-000000000002"

    def triple(subject_id: str, revision: int, content_hash: str) -> dict[str, Any]:
        return {
            "id": subject_id,
            "revision": revision,
            "content_hash": content_hash,
        }

    return {
        "schema_id": "ars://adapters/provider-receipt/v2",
        "schema_version": "2.0.0",
        "provider_receipt_id": PROVIDER_RECEIPT_ID,
        "revision": 1,
        "revision_hash": DIGESTS["receipt"],
        "command_binding": {
            "provider_command": triple(PROVIDER_COMMAND_ID, 1, DIGESTS["provider"]),
            "w2_command": triple(
                "cmd_019f8d10-0090-7000-8000-000000000090",
                1,
                sha256_hex(b"w2-command"),
            ),
            "idempotency_key_hash": sha256_hex(b"provider-call"),
            "payload_hash": sha256_hex(b"provider-payload"),
        },
        "provider_binding": {
            "provider": "claude",
            "provider_identity": triple(f"prv_{UUIDS['route']}", 1, DIGESTS["route"]),
            "model": triple(f"mdl_{UUIDS['route']}", 1, DIGESTS["route"]),
            "profile": triple(f"prf_{UUIDS['profile']}", 1, DIGESTS["profile"]),
            "adapter": triple(f"adp_{UUIDS['route']}", 1, DIGESTS["route"]),
            "policy": triple(f"pol_{UUIDS['route']}", 1, DIGESTS["route"]),
        },
        "authority_binding": {
            "task": triple(TASK_ID, 1, DIGESTS["task"]),
            "dispatch": triple(DISPATCH_ID, 1, DIGESTS["dispatch"]),
            "attempt": triple(ATTEMPT_ID, 1, DIGESTS["attempt"]),
            "resource_grant": triple(RESOURCE_GRANT_ID, 1, DIGESTS["resource"]),
            "cost_grant": triple(COST_GRANT_ID, 2, DIGESTS["cost"]),
            "reservation": triple(
                reservation_id,
                1,
                sha256_hex(reservation_id.encode()),
            ),
            "secret_reference": triple(SECRET_REFERENCE_ID, 1, DIGESTS["secret"]),
            "provider_receipt": triple(PROVIDER_RECEIPT_ID, 1, DIGESTS["receipt"]),
        },
        "delivery_binding": {
            "disposition": "proven",
            "rendered_payload_hash": sha256_hex(b"rendered"),
            "delivered_context_hash": sha256_hex(b"context"),
        },
        "timestamps": {
            "issued_at": "2026-07-23T12:00:00Z",
            "terminal_at": "2026-07-23T12:00:01Z",
        },
        "token_accounting": {
            "actual_input_tokens": actual_input,
            "actual_output_tokens": actual_output,
            "actual_total_tokens": actual_total,
            "accounting_method": "provider_receipt_exact",
            "reserved_cost_microunits": reserved_cost,
            "consumed_cost_microunits": consumed_cost,
            "refund_cost_microunits": reserved_cost - consumed_cost,
            "currency": "GBP",
            "rate_evidence_id": RATE_EVIDENCE_ID,
            "rate_evidence_revision": 1,
            "rate_evidence_hash": DIGESTS["rate"],
        },
        "terminal_outcome": {"status": "terminal", "normalized_error": None},
        "outputs": {
            "references": [],
            "aggregate_hash": sha256_hex(b"outputs"),
        },
        "lifecycle_evidence": {
            "retry_count": 0,
            "duplicate_of_receipt": None,
            "reconciliation": {
                "subject_id": f"rec_{UUIDS['receipt']}",
                "subject_revision": 1,
                "subject_hash": DIGESTS["receipt"],
            },
        },
        "evidence_disposition": {
            "redaction": "secret_and_restricted_material_removed",
            "omission_declarations": [],
        },
        "completeness": {
            "complete": True,
            "reconciliation_gate_satisfied": True,
            "diagnostic_only": False,
        },
    }


class Records:
    def __init__(self, control_root: Path | None = None) -> None:
        self.control_root = control_root
        reservation_id = "crs_019f8d10-0002-7000-8000-000000000002"
        self.values: dict[tuple[str, str, int], dict[str, Any]] = {
            ("resource_grant", RESOURCE_GRANT_ID, 1): _subject(
                "resource_grant",
                RESOURCE_GRANT_ID,
                1,
                DIGESTS["resource"],
                status="active",
                expires_at="2026-07-24T00:00:00Z",
            ),
            ("authority_grant", AUTHORITY_GRANT_ID, 1): {
                "kind": "authority_grant",
                "authority_grant_id": AUTHORITY_GRANT_ID,
                "status": "active",
                "expires_at": "2026-07-24T00:00:00Z",
            },
            ("secret_reference", SECRET_REFERENCE_ID, 1): _subject(
                "secret_reference",
                SECRET_REFERENCE_ID,
                1,
                DIGESTS["secret"],
                status="active",
                expires_at="2026-07-24T00:00:00Z",
                allowed_scope="wp6.2.t2.provider.issue",
            ),
            ("task", TASK_ID, 1): _subject("task", TASK_ID, 1, DIGESTS["task"]),
            ("dispatch", DISPATCH_ID, 1): _subject("dispatch", DISPATCH_ID, 1, DIGESTS["dispatch"]),
            ("attempt", ATTEMPT_ID, 1): _subject("attempt", ATTEMPT_ID, 1, DIGESTS["attempt"]),
            ("provider_command", PROVIDER_COMMAND_ID, 1): _subject(
                "provider_command",
                PROVIDER_COMMAND_ID,
                1,
                DIGESTS["provider"],
            ),
            ("cost_grant", COST_GRANT_ID, 1): _subject(
                "cost_grant",
                COST_GRANT_ID,
                1,
                DIGESTS["cost"],
                status="active",
                expires_at="2026-07-24T00:00:00Z",
            ),
            ("cost_grant", COST_GRANT_ID, 2): _subject(
                "cost_grant",
                COST_GRANT_ID,
                2,
                DIGESTS["cost"],
                status="active",
                expires_at="2026-07-24T00:00:00Z",
            ),
            ("reservation", reservation_id, 1): _subject(
                "reservation",
                reservation_id,
                1,
                sha256_hex(reservation_id.encode()),
            ),
            ("rate_evidence", RATE_EVIDENCE_ID, 1): _subject(
                "rate_evidence",
                RATE_EVIDENCE_ID,
                1,
                DIGESTS["rate"],
            ),
            (
                "zero_cost_authority",
                ZERO_AUTHORITY["subject_id"],
                1,
            ): {
                "kind": "zero_cost_authority",
                "id": ZERO_AUTHORITY["subject_id"],
                "revision": 1,
                "content_hash": DIGESTS["zero"],
            },
            (
                "provider_receipt",
                PROVIDER_RECEIPT_ID,
                1,
            ): _resolved_provider_receipt(),
        }

    def __call__(self, kind: str, object_id: str, revision: int) -> dict[str, Any] | None:
        value = self.values.get((kind, object_id, revision))
        return None if value is None else dict(value)


def _service(
    tmp_path: Path,
    records: Records | None = None,
    schemas: SchemaRegistry = SCHEMAS,
    *,
    authority_root: Path | None = None,
) -> tuple[CommandService, EventLedger, ReceiptStore, Records]:
    root = tmp_path / "control"
    root.mkdir()
    authority_root = root if authority_root is None else authority_root
    authority_root.mkdir(parents=True, exist_ok=True)
    (authority_root / "runtime").mkdir(parents=True, exist_ok=True)
    resolver = records or Records(authority_root)
    ledger = EventLedger(root, PROJECT_ID, schemas)
    receipts = ReceiptStore(root)
    service = CommandService(
        root,
        ledger,
        ObjectStore(root),
        receipts,
        schemas,
        clock=lambda: NOW,
        t2_authority_resolver=resolver,
    )
    return service, ledger, receipts, resolver


def _triples(payload: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for key in payload:
        if not key.endswith("_id"):
            continue
        stem = key.removesuffix("_id")
        if f"{stem}_revision" in payload and f"{stem}_hash" in payload:
            evidence.append(
                {
                    "subject_id": payload[key],
                    "subject_revision": payload[f"{stem}_revision"],
                    "subject_hash": payload[f"{stem}_hash"],
                }
            )
    zero = payload.get("zero_cost_authority")
    if isinstance(zero, dict):
        evidence.append(dict(zero))
    return evidence


def _envelope(
    command_type: str,
    command_uuid: str,
    payload: dict[str, Any],
    write_set: list[dict[str, Any]],
    scope: str,
    *,
    key: str,
) -> dict[str, Any]:
    envelope = {
        "schema_id": f"ars://wp6-2/t2/command/{command_type}",
        "schema_version": "1.0.0",
        "command_id": f"cmd_{command_uuid}",
        "command_type": command_type,
        "submitted_at": "2026-07-23T12:00:00Z",
        "actor_id": ACTORS["actor-a"],
        "on_behalf_of_actor_id": None,
        "authority_grant_id": AUTHORITY_GRANT_ID,
        "authority_scope": scope,
        "target_stream_id": write_set[0]["stream_id"],
        "write_set": write_set,
        "idempotency_key": key,
        "payload_hash": sha256_hex(canonical_bytes(payload)),
        "correlation_id": "wp6-2-t2-runtime-test",
        "causation_id": None,
        "reason": "literal runtime T2 test",
        "evidence_refs": _triples(payload),
        "payload": payload,
    }
    return envelope


def issue_command(*, zero_cost: bool = False) -> dict[str, Any]:
    payload = {
        "cost_grant_id": COST_GRANT_ID,
        "cost_grant_revision": 1,
        "cost_grant_hash": DIGESTS["cost"],
        "resource_grant_id": RESOURCE_GRANT_ID,
        "resource_grant_revision": 1,
        "resource_grant_hash": DIGESTS["resource"],
        "task_id": TASK_ID,
        "task_revision": 1,
        "task_hash": DIGESTS["task"],
        "dispatch_id": DISPATCH_ID,
        "dispatch_revision": 1,
        "dispatch_hash": DIGESTS["dispatch"],
        "attempt_id": ATTEMPT_ID,
        "attempt_revision": 1,
        "attempt_hash": DIGESTS["attempt"],
        "route_id": f"rte_{UUIDS['route']}",
        "profile_id": f"prf_{UUIDS['profile']}",
        "adapter_revision": "adapter-r1",
        "secret_reference_id": SECRET_REFERENCE_ID,
        "secret_reference_revision": 1,
        "secret_reference_hash": DIGESTS["secret"],
        "provider_command_id": PROVIDER_COMMAND_ID,
        "provider_command_revision": 1,
        "provider_command_hash": DIGESTS["provider"],
        "token_ceilings": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        "cost_ceiling_microunits": 100,
        "currency": "GBP",
        "rate_evidence_id": RATE_EVIDENCE_ID,
        "rate_evidence_revision": 1,
        "rate_evidence_hash": DIGESTS["rate"],
        "expires_at": "2026-07-24T00:00:00Z",
    }
    return _envelope(
        "IssueCostGrant",
        "019f8d10-0001-7000-8000-000000000001",
        payload,
        [{"stream_role": "cost_grant", "stream_id": COST_GRANT_ID, "expected_stream_version": 0}],
        "wp6.2.t2.cost-grant.issue",
        key="issue-cost-grant",
    )


def authorize_command(
    *,
    zero_cost: bool = False,
    command_uuid: str = "019f8d10-0002-7000-8000-000000000002",
    key: str = "authorize-provider",
) -> dict[str, Any]:
    reservation_id = f"crs_{command_uuid}"
    payload = {
        "cost_grant_id": COST_GRANT_ID,
        "cost_grant_revision": 1,
        "cost_grant_hash": DIGESTS["cost"],
        "resource_grant_id": RESOURCE_GRANT_ID,
        "resource_grant_revision": 1,
        "resource_grant_hash": DIGESTS["resource"],
        "task_id": TASK_ID,
        "task_revision": 1,
        "task_hash": DIGESTS["task"],
        "dispatch_id": DISPATCH_ID,
        "dispatch_revision": 1,
        "dispatch_hash": DIGESTS["dispatch"],
        "attempt_id": ATTEMPT_ID,
        "attempt_revision": 1,
        "attempt_hash": DIGESTS["attempt"],
        "reservation_id": reservation_id,
        "reservation_revision": 1,
        "reservation_hash": sha256_hex(reservation_id.encode()),
        "provider_command_id": PROVIDER_COMMAND_ID,
        "provider_command_revision": 1,
        "provider_command_hash": DIGESTS["provider"],
        "secret_reference_id": SECRET_REFERENCE_ID,
        "secret_reference_revision": 1,
        "secret_reference_hash": DIGESTS["secret"],
        "requested_tokens": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        "reserved_cost_microunits": 0 if zero_cost else 20,
        "expected_available_microunits": 100,
        "currency": "GBP",
        "rate_evidence_id": RATE_EVIDENCE_ID,
        "rate_evidence_revision": 1,
        "rate_evidence_hash": DIGESTS["rate"],
        "input_microunits_per_million_tokens": 0 if zero_cost else 1_000_000,
        "output_microunits_per_million_tokens": 0 if zero_cost else 2_000_000,
        "rate_mode": "zero_cost_authorized" if zero_cost else "metered",
        "zero_cost_authority": ZERO_AUTHORITY if zero_cost else None,
        "rendered_payload_hash": sha256_hex(b"rendered"),
    }
    return _envelope(
        "AuthorizeProviderIssue",
        command_uuid,
        payload,
        [
            {"stream_role": "cost_grant", "stream_id": COST_GRANT_ID, "expected_stream_version": 1},
            {"stream_role": "provider_command", "stream_id": PROVIDER_COMMAND_ID, "expected_stream_version": 0},
        ],
        "wp6.2.t2.provider.issue",
        key=key,
    )


def record_command(authorize: dict[str, Any], *, zero_cost: bool = False) -> dict[str, Any]:
    reserved = 0 if zero_cost else 20
    consumed = 0 if zero_cost else 8
    payload = {
        "provider_command_id": PROVIDER_COMMAND_ID,
        "provider_command_revision": 1,
        "provider_command_hash": DIGESTS["provider"],
        "resource_grant_id": RESOURCE_GRANT_ID,
        "resource_grant_revision": 1,
        "resource_grant_hash": DIGESTS["resource"],
        "task_id": TASK_ID,
        "task_revision": 1,
        "task_hash": DIGESTS["task"],
        "dispatch_id": DISPATCH_ID,
        "dispatch_revision": 1,
        "dispatch_hash": DIGESTS["dispatch"],
        "attempt_id": ATTEMPT_ID,
        "attempt_revision": 1,
        "attempt_hash": DIGESTS["attempt"],
        "secret_reference_id": SECRET_REFERENCE_ID,
        "secret_reference_revision": 1,
        "secret_reference_hash": DIGESTS["secret"],
        "provider_receipt_id": PROVIDER_RECEIPT_ID,
        "provider_receipt_revision": 1,
        "provider_receipt_hash": DIGESTS["receipt"],
        "provider_receipt_schema_id": "ars://adapters/provider-receipt/v2",
        "provider_receipt_schema_version": "2.0.0",
        "cost_grant_id": COST_GRANT_ID,
        "cost_grant_revision": 2,
        "cost_grant_hash": DIGESTS["cost"],
        "reservation_id": authorize["payload"]["reservation_id"],
        "reservation_revision": 1,
        "reservation_hash": authorize["payload"]["reservation_hash"],
        "actual_tokens": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
        "reserved_token_ceilings": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        "reserved_cost_microunits": reserved,
        "consumed_cost_microunits": consumed,
        "refund_cost_microunits": reserved - consumed,
        "refund_disposition": "fully_consumed" if reserved == consumed else "refunded",
        "currency": "GBP",
        "rate_evidence_id": RATE_EVIDENCE_ID,
        "rate_evidence_revision": 1,
        "rate_evidence_hash": DIGESTS["rate"],
        "input_microunits_per_million_tokens": 0 if zero_cost else 1_000_000,
        "output_microunits_per_million_tokens": 0 if zero_cost else 2_000_000,
        "rate_mode": "zero_cost_authorized" if zero_cost else "metered",
        "zero_cost_authority": ZERO_AUTHORITY if zero_cost else None,
        "provider_terminal_status": "terminal",
        "receipt_complete": True,
    }
    return _envelope(
        "RecordProviderReceipt",
        "019f8d10-0003-7000-8000-000000000003",
        payload,
        [
            {"stream_role": "provider_command", "stream_id": PROVIDER_COMMAND_ID, "expected_stream_version": 1},
            {"stream_role": "cost_grant", "stream_id": COST_GRANT_ID, "expected_stream_version": 2},
        ],
        "wp6.2.t2.provider.receipt.record",
        key="record-provider-receipt",
    )


T2_AUTHORITY_COMMANDS = ("IssueCostGrant", "AuthorizeProviderIssue")


def _command_for_authority_lock(service: CommandService, command_type: str) -> dict[str, Any]:
    if command_type == "IssueCostGrant":
        return issue_command()
    assert command_type == "AuthorizeProviderIssue"
    assert service.submit(issue_command()).status == "accepted"
    return authorize_command()


@pytest.mark.parametrize("command_type", T2_AUTHORITY_COMMANDS)
def test_t2_authority_lock_domain_wins_before_revocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command_type: str,
) -> None:
    authority_root = tmp_path / "authority"
    service, ledger, _, resolver = _service(tmp_path, authority_root=authority_root)
    command = _command_for_authority_lock(service, command_type)
    resolution_ready = threading.Event()
    release_resolution = threading.Event()
    append_entered = threading.Event()
    release_append = threading.Event()
    revocation_committed = threading.Event()
    results: dict[str, Any] = {}
    errors: list[BaseException] = []

    original_lookup = t2_module._lookup

    def paused_lookup(service_value, kind, object_id, revision):
        value = original_lookup(service_value, kind, object_id, revision)
        if kind == "authority_grant" and not resolution_ready.is_set():
            resolution_ready.set()
            if not release_resolution.wait(2):
                raise AssertionError("authority-resolution barrier was not released")
        return value

    monkeypatch.setattr(t2_module, "_lookup", paused_lookup)
    original_append = ledger.append

    def paused_append(*args, **kwargs):
        value = original_append(*args, **kwargs)
        append_entered.set()
        if not release_append.wait(2):
            raise AssertionError("append barrier was not released")
        return value

    monkeypatch.setattr(ledger, "append", paused_append)

    def revoke() -> None:
        for _ in range(2000):
            try:
                with WriterLock(
                    authority_root / "runtime" / "writer.lock",
                    {"command_id": "cmd_t2-revoker"},
                ):
                    resolver.values[("authority_grant", AUTHORITY_GRANT_ID, 1)] = {
                        **resolver.values[("authority_grant", AUTHORITY_GRANT_ID, 1)],
                        "revoked": True,
                    }
                    revocation_committed.set()
                    return
            except ConflictError:
                threading.Event().wait(0.001)
        errors.append(AssertionError("authority revoker did not acquire its lock"))

    def submit() -> None:
        try:
            results["receipt"] = service.submit(command)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    submit_thread = threading.Thread(target=submit)
    revocation_thread = threading.Thread(target=revoke)
    submit_thread.start()
    assert resolution_ready.wait(2)
    revocation_thread.start()
    try:
        assert not revocation_committed.wait(0.2)
        release_resolution.set()
        assert append_entered.wait(2)
        assert not revocation_committed.wait(0.2)
    finally:
        release_resolution.set()
        release_append.set()
        submit_thread.join(4)
        revocation_thread.join(4)

    assert not submit_thread.is_alive()
    assert not revocation_thread.is_alive()
    assert errors == []
    assert results["receipt"].status == "accepted"
    assert revocation_committed.is_set()


@pytest.mark.parametrize("command_type", T2_AUTHORITY_COMMANDS)
def test_t2_authority_lock_revocation_wins_and_rechecks_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command_type: str,
) -> None:
    authority_root = tmp_path / "authority"
    service, ledger, _, resolver = _service(tmp_path, authority_root=authority_root)
    command = _command_for_authority_lock(service, command_type)
    before_events = tuple(ledger.iter_events())
    authority_locked = threading.Event()
    release_authority = threading.Event()
    lookup_started = threading.Event()
    results: dict[str, Any] = {}
    errors: list[BaseException] = []

    def revoke() -> None:
        try:
            with WriterLock(
                authority_root / "runtime" / "writer.lock",
                {"command_id": "cmd_t2-revoker"},
            ):
                resolver.values[("authority_grant", AUTHORITY_GRANT_ID, 1)] = {
                    **resolver.values[("authority_grant", AUTHORITY_GRANT_ID, 1)],
                    "revoked": True,
                }
                authority_locked.set()
                if not release_authority.wait(2):
                    raise AssertionError("authority barrier was not released")
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    original_lookup = t2_module._lookup

    def observed_lookup(service_value, kind, object_id, revision):
        lookup_started.set()
        return original_lookup(service_value, kind, object_id, revision)

    monkeypatch.setattr(t2_module, "_lookup", observed_lookup)

    def submit() -> None:
        try:
            results["receipt"] = service.submit(command)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    revocation_thread = threading.Thread(target=revoke)
    submit_thread = threading.Thread(target=submit)
    revocation_thread.start()
    assert authority_locked.wait(2)
    submit_thread.start()
    try:
        assert not lookup_started.wait(0.2)
    finally:
        release_authority.set()
        revocation_thread.join(4)
        submit_thread.join(4)

    assert not revocation_thread.is_alive()
    assert not submit_thread.is_alive()
    assert errors == []
    assert results["receipt"].status == "rejected"
    assert results["receipt"].record["stable_reason"] == "schema_identity_mismatch"
    assert tuple(ledger.iter_events()) == before_events


def test_t2_authority_resolver_requires_existing_control_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(ArsError, match="control_root"):
        _service(tmp_path, records=Records())


def test_closed_family_receipt_v2_reducers_projection_and_legacy_indices(tmp_path: Path) -> None:
    service, ledger, receipts, _ = _service(tmp_path)
    invocations = {"count": 0}

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        invocations["count"] += 1
        raise AssertionError("provider invocation is outside runtime T2")

    service.provider_invocation_canary = fail_if_called
    issue = issue_command()
    authorize = authorize_command()
    record = record_command(authorize)
    accepted = [service.submit(issue), service.submit(authorize), service.submit(record)]
    assert all(isinstance(item, T2Receipt) and item.status == "accepted" for item in accepted)
    batches = list(ledger.iter_batches())
    assert [[event["event_type"] for event in batch] for batch in batches] == [
        ["CostGrantIssued"],
        ["CostGrantReserved", "ProviderCommandIssued"],
        ["ProviderReceiptRecorded", "CostGrantReconciled"],
    ]
    assert [[event["transaction_index"] for event in batch] for batch in batches] == [[0], [0, 1], [0, 1]]
    assert [event["schema_id"] for batch in batches for event in batch] == [
        "ars://wp6-2/t2/event/CostGrantIssued",
        "ars://wp6-2/t2/event/CostGrantReserved",
        "ars://wp6-2/t2/event/ProviderCommandIssued",
        "ars://wp6-2/t2/event/ProviderReceiptRecorded",
        "ars://wp6-2/t2/event/CostGrantReconciled",
    ]
    expected_command_schemas = {
        command["command_type"]: service.schemas.resolve_identity(
            command["schema_id"],
            command["schema_version"],
        )
        for command in (issue, authorize, record)
    }
    for batch in batches:
        for event in batch:
            identity = expected_command_schemas[event["command_type"]]
            assert event["schema_version"] == "1.1.0"
            assert event["command_schema_id"] == identity.schema_id
            assert event["command_schema_version"] == identity.schema_version
            assert event["command_schema_sha256"] == identity.sha256
    assert accepted[1].events[0]["resulting_stream_version"] == 2
    assert accepted[1].events[1]["resulting_stream_version"] == 1
    assert receipts.load_t2(record["command_id"]) == accepted[2]
    projected = replay(ledger.iter_events(), schema_registry=service.schemas)
    assert projected["cost_grants"][COST_GRANT_ID]["available_cost_microunits"] == 92
    assert projected["provider_commands"][PROVIDER_COMMAND_ID]["status"] == "receipt_recorded"
    rebuilt = rebuild_projection(ledger.iter_events(), tmp_path / "projection.json", service.schemas)
    assert rebuilt == projected
    duplicate = service.submit(record)
    assert duplicate.status == "duplicate"
    assert duplicate.events == accepted[2].events
    assert duplicate.record["outcome_binding_hash"] == accepted[2].record["outcome_binding_hash"]
    assert duplicate.record["original_accepted_receipt_hash"] == sha256_hex(canonical_bytes(accepted[2].to_record()))
    assert duplicate.record["new_event_count"] == 0
    assert len(list(ledger.iter_batches())) == 3
    assert invocations["count"] == 0

    legacy_root = tmp_path / "legacy-control"
    legacy_ledger = EventLedger(
        legacy_root,
        PROJECT_ID,
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
    )
    legacy_ledger.append(
        [
            {
                "event_type": "LegacyIndexProbe",
                "stream_id": "tsk_019f8d10-0005-7000-8000-000000000005",
                "occurred_at": "2026-07-23T12:00:00Z",
                "payload": {},
            }
        ]
    )
    legacy_event = list(legacy_ledger.iter_batches())[-1][0]
    assert legacy_event["transaction_index"] == 1
    assert legacy_event["schema_id"] == "ars://core/event/LegacyIndexProbe"


def test_inactive_t2_command_binding_rejects_before_event_publication(tmp_path: Path) -> None:
    inert = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service, ledger, _, _ = _service(tmp_path, schemas=inert)

    receipt = service.submit(issue_command())

    assert receipt.status == "rejected"
    assert receipt.record["stable_reason"] == "schema_identity_mismatch"
    assert tuple(ledger.iter_events()) == ()


def test_caller_provenance_cannot_override_validated_t2_command_identity(tmp_path: Path) -> None:
    service, ledger, _, _ = _service(tmp_path)
    command = issue_command()
    command.update(
        {
            "command_schema_id": "ars://caller/forged",
            "command_schema_version": "9.0.0",
            "command_schema_sha256": "0" * 64,
        }
    )

    receipt = service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.record["stable_reason"] == "schema_identity_mismatch"
    assert tuple(ledger.iter_events()) == ()


@pytest.mark.parametrize("mutation", ["version", "missing_provenance"])
def test_replay_rejects_t2_event_schema_or_provenance_drift(
    tmp_path: Path,
    mutation: str,
) -> None:
    service, ledger, _, _ = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    event = deepcopy(tuple(ledger.iter_events())[0])
    if mutation == "version":
        event["schema_version"] = "1.0.0"
    else:
        event.pop("command_schema_sha256")
    unsigned = dict(event)
    unsigned.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(unsigned))

    expected = "event schema validation" if mutation == "version" else "incomplete command schema identity"
    with pytest.raises(IntegrityError, match=expected):
        replay([event], schema_registry=service.schemas)


def test_atomic_append_failure_publishes_no_partial_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, ledger, _, _ = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    before = tuple(ledger.iter_events())

    def crash(_path: Path) -> None:
        raise OSError("synthetic pre-publication crash")

    monkeypatch.setattr(ledger, "_after_batch_fsync", crash)
    with pytest.raises(OSError, match="pre-publication"):
        service.submit(authorize_command())
    # No partial batch must have been written.
    assert tuple(ledger.iter_events()) == before

    # After removing the fault the ledger must accept the next natural command
    # (authorize_command reads the cost grant from ledger state; the resolver
    # holds all other required records) and the ledger must be consistent.
    monkeypatch.undo()
    result = service.submit(authorize_command())
    assert result.status == "accepted"
    all_events = tuple(ledger.iter_events())
    assert all_events[: len(before)] == before
    assert len(all_events) == len(before) + 2
    assert [e["event_type"] for e in all_events[len(before) :]] == [
        "CostGrantReserved",
        "ProviderCommandIssued",
    ]


def test_stale_multi_stream_and_over_reservation_have_one_winner(tmp_path: Path) -> None:
    service, ledger, _, _ = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    winner = service.submit(authorize_command())
    loser_command = authorize_command(
        command_uuid="019f8d10-0012-7000-8000-000000000012",
        key="second-reservation",
    )
    loser_command["payload"]["provider_command_id"] = "pcmd_019f8d10-0013-7000-8000-000000000013"
    loser_command["payload"]["provider_command_hash"] = sha256_hex(b"second-provider")
    loser_command["write_set"][1]["stream_id"] = loser_command["payload"]["provider_command_id"]
    loser_command["evidence_refs"] = _triples(loser_command["payload"])
    loser_command["payload_hash"] = sha256_hex(canonical_bytes(loser_command["payload"]))
    loser = service.submit(loser_command)
    assert winner.status == "accepted"
    assert loser.status == "conflict"
    assert loser.record["stable_reason"] == "stale_stream_version"
    assert [event["event_type"] for event in ledger.iter_events()].count("CostGrantReserved") == 1


def test_exact_replay_and_idempotency_conflicts_are_command_specific(tmp_path: Path) -> None:
    service, ledger, _, _ = _service(tmp_path)
    issue = issue_command()
    accepted = service.submit(issue)
    assert service.submit(issue).status == "duplicate"
    conflicting = deepcopy(issue)
    conflicting["command_id"] = "cmd_019f8d10-0021-7000-8000-000000000021"
    assert service.submit(conflicting).record["stable_reason"] == "idempotency_conflict"
    changed = deepcopy(issue)
    changed["payload"]["cost_ceiling_microunits"] = 99
    changed["payload_hash"] = sha256_hex(canonical_bytes(changed["payload"]))
    assert service.submit(changed).record["stable_reason"] == "idempotency_conflict"
    assert len(tuple(ledger.iter_batches())) == 1
    assert accepted.status == "accepted"


def test_accepted_command_id_payload_cannot_replay_under_different_scope_tuple(
    tmp_path: Path,
) -> None:
    service, ledger, _, _ = _service(tmp_path)
    command = issue_command()
    assert service.submit(command).status == "accepted"

    changed_actor = deepcopy(command)
    changed_actor["actor_id"] = ACTORS["actor-b"]
    actor_result = service.submit(changed_actor)
    assert actor_result.status == "conflict"
    assert actor_result.record["stable_reason"] == "idempotency_conflict"

    changed_key = deepcopy(command)
    changed_key["idempotency_key"] = "different-key"
    key_result = service.submit(changed_key)
    assert key_result.status == "conflict"
    assert key_result.record["stable_reason"] == "idempotency_conflict"
    assert len(tuple(ledger.iter_batches())) == 1


def test_stored_receipt_proof_is_reconstructed_from_ledger_before_duplicate(
    tmp_path: Path,
) -> None:
    service, ledger, receipts, _ = _service(tmp_path)
    command = issue_command()
    accepted = service.submit(command)
    corrupted = accepted.to_record()
    corrupted["events"][0]["resulting_stream_version"] = 2
    binding = dict(corrupted)
    binding.pop("outcome_binding_hash")
    corrupted["outcome_binding_hash"] = sha256_hex(canonical_bytes(binding))
    path = receipts.receipts_root / f"{command['command_id']}.json"
    path.write_bytes(canonical_bytes(corrupted))

    with pytest.raises(IntegrityError, match="differs from ledger proof"):
        service.submit(command)
    assert len(tuple(ledger.iter_batches())) == 1


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "secret_reference_missing"),
        ("wrong_type", "secret_reference_wrong_type"),
        ("expired", "secret_reference_expired"),
        ("revoked", "secret_reference_revoked"),
        ("identity", "secret_reference_identity_mismatch"),
    ],
)
def test_secret_reference_lifecycle_rejections(tmp_path: Path, mutation: str, reason: str) -> None:
    service, ledger, _, records = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    key = ("secret_reference", SECRET_REFERENCE_ID, 1)
    if mutation == "missing":
        records.values.pop(key)
    elif mutation == "wrong_type":
        records.values[key]["kind"] = "credential"
    elif mutation == "expired":
        records.values[key]["expires_at"] = "2026-07-23T11:00:00Z"
    elif mutation == "revoked":
        records.values[key]["revoked"] = True
    else:
        records.values[key]["secret_reference_hash"] = "f" * 64
    receipt = service.submit(authorize_command())
    assert receipt.status == "rejected"
    assert receipt.record["stable_reason"] == reason
    assert len(tuple(ledger.iter_batches())) == 1


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "cost_grant_missing"),
        ("wrong_type", "cost_grant_wrong_type"),
        ("zero", "cost_grant_zero"),
        ("exhausted", "cost_grant_exhausted"),
        ("revoked", "cost_grant_revoked"),
        ("expired", "cost_grant_expired"),
        ("insufficient", "cost_grant_insufficient_balance"),
        ("identity", "cost_grant_identity_mismatch"),
    ],
)
def test_cost_grant_preconditions(tmp_path: Path, mutation: str, reason: str) -> None:
    service, ledger, _, records = _service(tmp_path)
    command = authorize_command()
    if mutation != "missing":
        issue = issue_command()
        assert service.submit(issue).status == "accepted"
        if mutation in {"wrong_type", "zero", "exhausted", "revoked", "expired"}:
            records.values[("cost_grant", COST_GRANT_ID, 1)] = {
                "kind": "provider_command" if mutation == "wrong_type" else "cost_grant",
                "cost_grant_id": COST_GRANT_ID,
                "cost_grant_revision": 1,
                "cost_grant_hash": DIGESTS["cost"],
                "status": mutation if mutation in {"zero", "exhausted", "revoked"} else "active",
                "expires_at": ("2026-07-24T00:00:00Z" if mutation != "expired" else "2026-07-23T11:00:00Z"),
            }
    if mutation == "insufficient":
        command["payload"]["reserved_cost_microunits"] = 101
    elif mutation == "identity":
        command["payload"]["cost_grant_hash"] = "f" * 64
    command["evidence_refs"] = _triples(command["payload"])
    command["payload_hash"] = sha256_hex(canonical_bytes(command["payload"]))
    receipt = service.submit(command)
    assert receipt.record["stable_reason"] == reason
    assert [event["event_type"] for event in ledger.iter_events()].count("CostGrantReserved") == 0


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("schema_alias", "schema_identity_mismatch"),
        ("schema_version", "schema_identity_mismatch"),
        ("write_set", "schema_identity_mismatch"),
        ("target", "schema_identity_mismatch"),
        ("payload_hash", "schema_hash_mismatch"),
        ("rate", "schema_identity_mismatch"),
    ],
)
def test_identity_and_rate_evidence_mismatches(tmp_path: Path, mutation: str, reason: str) -> None:
    service, ledger, _, _ = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    command = authorize_command()
    if mutation == "schema_alias":
        command["schema_id"] = "ars://wp6-2/t2/command/alias"
    elif mutation == "schema_version":
        command["schema_version"] = "2.0.0"
    elif mutation == "write_set":
        command["write_set"][1]["stream_id"] = "pcmd_019f8d10-0030-7000-8000-000000000030"
    elif mutation == "target":
        command["target_stream_id"] = "cgr_019f8d10-0031-7000-8000-000000000031"
    elif mutation == "payload_hash":
        command["payload_hash"] = "f" * 64
    else:
        command["payload"]["rate_evidence_hash"] = "f" * 64
        command["evidence_refs"] = _triples(command["payload"])
        command["payload_hash"] = sha256_hex(canonical_bytes(command["payload"]))
    receipt = service.submit(command)
    assert receipt.record["stable_reason"] == reason
    assert len(tuple(ledger.iter_batches())) == 1


def test_zero_cost_mode_and_reconcile_after_lifecycle_expiry(tmp_path: Path) -> None:
    service, ledger, _, records = _service(tmp_path)
    assert service.submit(issue_command(zero_cost=True)).status == "accepted"
    authorize = authorize_command(zero_cost=True)
    assert service.submit(authorize).status == "accepted"
    records.values[("provider_receipt", PROVIDER_RECEIPT_ID, 1)] = _resolved_provider_receipt(
        reserved_cost=0, consumed_cost=0
    )
    records.values[("secret_reference", SECRET_REFERENCE_ID, 1)]["revoked"] = True
    records.values[("resource_grant", RESOURCE_GRANT_ID, 1)]["expires_at"] = "2026-07-23T11:00:00Z"
    receipt = service.submit(record_command(authorize, zero_cost=True))
    assert receipt.status == "accepted"
    reconciled = list(ledger.iter_batches())[-1][1]["payload"]
    assert reconciled["consumed_cost_microunits"] == 0
    assert reconciled["refund_cost_microunits"] == 0
    assert reconciled["remaining_cost_microunits"] == 100


@pytest.mark.parametrize("mutation", ["actuals", "cost", "status"])
def test_conflicting_independently_resolved_provider_receipt_rejects_atomically(
    tmp_path: Path,
    mutation: str,
) -> None:
    service, ledger, _, records = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    authorize = authorize_command()
    assert service.submit(authorize).status == "accepted"
    resolved = records.values[("provider_receipt", PROVIDER_RECEIPT_ID, 1)]
    if mutation == "actuals":
        resolved["token_accounting"]["actual_input_tokens"] = 5
        resolved["token_accounting"]["actual_total_tokens"] = 7
    elif mutation == "cost":
        resolved["token_accounting"]["consumed_cost_microunits"] = 9
        resolved["token_accounting"]["refund_cost_microunits"] = 11
    else:
        resolved["terminal_outcome"]["status"] = "blocked"

    result = service.submit(record_command(authorize))
    assert result.status == "rejected"
    assert result.record["stable_reason"] == "reconciliation_actuals_invalid"
    assert len(tuple(ledger.iter_batches())) == 2
    assert not any(event["event_type"] == "ProviderReceiptRecorded" for event in ledger.iter_events())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actual_tokens", {"input_tokens": 11, "output_tokens": 2, "total_tokens": 13}),
        ("consumed_cost_microunits", 9),
        ("refund_cost_microunits", 13),
        ("receipt_complete", False),
        ("provider_receipt_hash", "f" * 64),
    ],
)
def test_receipt_actuals_bounds_and_identity_rejections(tmp_path: Path, field: str, value: Any) -> None:
    service, ledger, _, _ = _service(tmp_path)
    assert service.submit(issue_command()).status == "accepted"
    authorize = authorize_command()
    assert service.submit(authorize).status == "accepted"
    command = record_command(authorize)
    command["payload"][field] = value
    command["evidence_refs"] = _triples(command["payload"])
    command["payload_hash"] = sha256_hex(canonical_bytes(command["payload"]))
    receipt = service.submit(command)
    expected = (
        "provider_receipt_incomplete"
        if field == "receipt_complete"
        else "provider_receipt_identity_mismatch"
        if field == "provider_receipt_hash"
        else "reconciliation_actuals_invalid"
    )
    assert receipt.record["stable_reason"] == expected
    assert [event["event_type"] for event in ledger.iter_events()].count("ProviderReceiptRecorded") == 0
