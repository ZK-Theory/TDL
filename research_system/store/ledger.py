from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError
from research_system.ids import new_id, validate_id
from research_system.schema_registry import SchemaBinding, SchemaRegistry

_PROTECTED_FIELDS = frozenset(
    {
        "event_id",
        "project_id",
        "stream_version",
        "global_position",
        "transaction_id",
        "transaction_index",
        "transaction_count",
        "previous_event_hash",
        "event_hash",
        "recorded_at",
    }
)
_COMMAND_SCHEMA_FIELDS = frozenset(
    {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }
)


@dataclass(frozen=True)
class LedgerSnapshot:
    """Materialized immutable ledger state used by one command transaction."""

    events: tuple[dict[str, Any], ...]
    global_position: int
    event_hash: str
    stream_versions: Mapping[str, int]
    fingerprint: tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class AllocatedEvent:
    """Ledger-owned identity and position exposed only to a draft finalizer."""

    event_id: str
    project_id: str
    stream_id: str
    stream_version: int
    global_position: int
    transaction_id: str
    transaction_index: int
    transaction_count: int
    recorded_at: str


@dataclass(frozen=True, init=False)
class EventDraft:
    """One-shot validated-submit event finalized after ledger allocation."""

    envelope: Mapping[str, Any]
    finalize_payload: Callable[[AllocatedEvent], Mapping[str, Any]]
    admission: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise ArsError("event drafts require CommandService capability")


def _release_draft_protocol():
    issued: dict[int, tuple[object, object, EventDraft]] = {}
    guard_claimed = False

    class _Session:
        __slots__ = ("ledger", "draft", "consumed")

        def __init__(self, ledger: object) -> None:
            self.ledger = ledger
            self.draft: EventDraft | None = None
            self.consumed = False

    def guard(submit_impl):
        def guarded_submit(self, envelope):
            release_used = False
            authority_used = False

            def append_release(
                ledger,
                event_envelope,
                finalize_payload,
                *,
                snapshot=None,
            ):
                nonlocal release_used
                if release_used or ledger is not self.ledger:
                    raise ArsError("release append continuation is one-shot and ledger-specific")
                release_used = True
                session = _Session(ledger)
                return ledger._append_release_from_validated_submit(
                    session,
                    event_envelope,
                    finalize_payload,
                    snapshot=snapshot,
                )

            def append_scoped_authority(
                ledger,
                event_envelope,
                *,
                snapshot=None,
            ):
                nonlocal authority_used
                if authority_used or ledger is not self.ledger:
                    raise ArsError("scoped-authority append continuation is one-shot and ledger-specific")
                authority_used = True
                session = _Session(ledger)
                return ledger._append_scoped_authority_from_validated_submit(
                    session,
                    event_envelope,
                    snapshot=snapshot,
                )

            return submit_impl(
                self,
                envelope,
                append_release,
                append_scoped_authority,
            )

        guarded_submit.__name__ = submit_impl.__name__
        guarded_submit.__qualname__ = submit_impl.__qualname__
        guarded_submit.__doc__ = submit_impl.__doc__
        guarded_submit.__module__ = submit_impl.__module__
        guarded_submit.__annotations__ = {key: submit_impl.__annotations__[key] for key in ("envelope", "return")}
        return guarded_submit

    def take_guard():
        nonlocal guard_claimed
        if guard_claimed:
            raise ArsError("release submit guard is already bound")
        guard_claimed = True
        return guard

    def register(session: object, ledger: object, draft: EventDraft) -> None:
        if (
            type(session) is not _Session
            or session.ledger is not ledger
            or session.draft is not None
            or session.consumed
        ):
            raise ArsError("release publication requires the validated CommandService.submit continuation")
        session.draft = draft
        issued[id(draft)] = (session, ledger, draft)

    def consume(ledger: object, draft: EventDraft) -> None:
        entry = issued.pop(id(draft), None)
        if entry is None:
            raise ArsError("release event draft requires the validated CommandService.submit continuation")
        session, issued_ledger, issued_draft = entry
        if issued_ledger is not ledger or issued_draft is not draft or session.draft is not draft or session.consumed:
            raise ArsError("release event draft is foreign, forged, or consumed")
        session.draft = None
        session.consumed = True

    def discard(session: object) -> None:
        if type(session) is not _Session:
            return
        draft = session.draft
        if draft is not None:
            entry = issued.get(id(draft))
            if entry is not None and entry[0] is session and entry[2] is draft:
                issued.pop(id(draft), None)
        session.draft = None
        session.consumed = True

    return take_guard, register, consume, discard


(
    _take_release_submit_guard,
    _register_release_draft,
    _consume_release_draft,
    _discard_release_session,
) = _release_draft_protocol()
del _release_draft_protocol


class EventLedger:
    def __init__(
        self,
        control_root: Path,
        project_id: str,
        schemas: SchemaRegistry | None = None,
    ) -> None:
        self.control_root = control_root
        self.project_id = validate_id(project_id, "project")
        if schemas is not None and not isinstance(schemas, SchemaRegistry):
            raise TypeError("EventLedger requires a trusted SchemaRegistry")
        self.schemas = schemas
        self.events_root = control_root / "events" / project_id
        self.runtime_root = control_root / "runtime"
        self.events_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._snapshot: LedgerSnapshot | None = None

    def _append_release_from_validated_submit(
        self,
        session: object,
        envelope: Mapping[str, Any],
        finalize_payload: Callable[[AllocatedEvent], Mapping[str, Any]],
        *,
        snapshot: LedgerSnapshot | None = None,
    ) -> dict[str, Any]:
        """Append one release draft from the validated submit continuation."""
        draft = object.__new__(EventDraft)
        object.__setattr__(draft, "envelope", envelope)
        object.__setattr__(draft, "finalize_payload", finalize_payload)
        object.__setattr__(draft, "admission", "release")
        _register_release_draft(session, self, draft)
        try:
            return self.append([draft], snapshot=snapshot)
        finally:
            _discard_release_session(session)

    def _append_scoped_authority_from_validated_submit(
        self,
        session: object,
        envelope: Mapping[str, Any],
        *,
        snapshot: LedgerSnapshot | None = None,
    ) -> dict[str, Any]:
        """Append one scoped administration event from its verified continuation."""
        candidate = dict(envelope)
        payload = candidate.pop("payload", None)
        if not isinstance(payload, Mapping):
            raise ArsError("scoped-authority continuation requires an event payload")
        draft = object.__new__(EventDraft)
        object.__setattr__(draft, "envelope", candidate)
        object.__setattr__(
            draft,
            "finalize_payload",
            lambda _allocated: dict(payload),
        )
        object.__setattr__(draft, "admission", "scoped_authority")
        _register_release_draft(session, self, draft)
        try:
            return self.append([draft], snapshot=snapshot)
        finally:
            _discard_release_session(session)

    def snapshot(self) -> LedgerSnapshot:
        """Return a verified-state input, reloading only when ledger files change."""
        fingerprint = self._fingerprint()
        if self._snapshot is not None and self._snapshot.fingerprint == fingerprint:
            return self._snapshot
        events = tuple(self.iter_events())
        if self._fingerprint() != fingerprint:
            raise ConflictError("ledger changed while materializing snapshot")
        stream_versions: dict[str, int] = {}
        for event in events:
            stream_versions[event["stream_id"]] = event["stream_version"]
        self._snapshot = LedgerSnapshot(
            events=events,
            global_position=events[-1]["global_position"] if events else 0,
            event_hash=events[-1]["event_hash"] if events else "0" * 64,
            stream_versions=stream_versions,
            fingerprint=fingerprint,
        )
        return self._snapshot

    def _validate_event_schema(
        self,
        validation_payload: dict[str, Any],
        *,
        t2_event: bool,
        event_type: str,
        event_schema: str,
        event_schema_version: str,
        event_binding: SchemaBinding | None,
    ) -> None:
        schemas = self.schemas
        if schemas is None:
            raise ArsError("event append requires an explicit SchemaRegistry")
        if t2_event:
            schemas.validate(
                event_schema,
                validation_payload,
                schema_version=event_schema_version,
            )
            return
        if event_type == "ReleaseGateDecisionPublished":
            schemas.validate(
                event_schema,
                validation_payload,
                schema_version=event_schema_version,
            )
            return
        schemas.validate("ars://core/event", validation_payload)
        if event_binding is not None:
            schemas.validate_active(
                event_binding.schema_id,
                validation_payload,
                schema_version=event_binding.schema_version,
            )
            return
        payload_schema = f"{event_schema}/payload"
        if event_schema != "ars://core/event":
            if schemas.requires_command_provenance and schemas.contains(payload_schema):
                schemas.validate(payload_schema, validation_payload.get("payload"))
            elif schemas.contains(event_schema):
                schemas.validate(
                    event_schema,
                    validation_payload,
                    schema_version=event_schema_version,
                )
            elif schemas.contains(payload_schema):
                schemas.validate(payload_schema, validation_payload.get("payload"))

    def append(
        self,
        proposed_events: Iterable[Mapping[str, Any] | EventDraft],
        *,
        snapshot: LedgerSnapshot | None = None,
    ) -> dict[str, Any]:
        """Atomically append a batch using a caller-verified materialized state."""
        if self.schemas is None:
            raise ArsError("event append requires an explicit SchemaRegistry")
        proposed = list(proposed_events)
        if not proposed:
            raise ArsError("event batch must not be empty")
        current = self.snapshot() if snapshot is None else snapshot
        if self._fingerprint() != current.fingerprint:
            self._snapshot = None
            raise ConflictError("ledger changed since materialized snapshot")
        if self._persisted_tail() != (current.global_position, current.event_hash):
            self._snapshot = None
            raise ConflictError("persisted ledger tail differs from snapshot")
        next_position = current.global_position + 1
        previous_hash = current.event_hash
        stream_versions = dict(current.stream_versions)
        transaction_id = new_id("event_batch")
        recorded_at = datetime.now(UTC)
        count = len(proposed)
        events: list[dict[str, Any]] = []
        for offset, proposed_event in enumerate(proposed):
            draft = proposed_event if isinstance(proposed_event, EventDraft) else None
            if draft is not None:
                _consume_release_draft(self, draft)
            candidate = dict(draft.envelope if draft is not None else proposed_event)
            protected = _PROTECTED_FIELDS.intersection(candidate)
            if protected:
                raise ArsError(f"caller supplied protected event fields: {sorted(protected)}")
            recorded_provenance = _COMMAND_SCHEMA_FIELDS.intersection(candidate)
            if self.schemas.requires_command_provenance and recorded_provenance != _COMMAND_SCHEMA_FIELDS:
                raise ArsError("runtime event requires complete command schema identity")
            if recorded_provenance == _COMMAND_SCHEMA_FIELDS:
                self.schemas.resolve_identity(
                    str(candidate["command_schema_id"]),
                    str(candidate["command_schema_version"]),
                    expected_sha256=str(candidate["command_schema_sha256"]),
                )
            try:
                event_type = candidate.pop("event_type")
                stream_id = candidate.pop("stream_id")
            except KeyError as exc:
                raise ArsError(f"missing event field: {exc.args[0]}") from exc
            producer = str(candidate.get("command_type", ""))
            scoped_authority_event = (event_type, producer) in {
                ("AuthorityGrantActivated", "ActivateAuthorityGrant"),
                ("AuthorityGrantRevoked", "RevokeAuthorityGrant"),
                ("AuthorityGrantRevoked", "RevokeIssuedAuthorityGrant"),
                ("AuthorityGrantActivated", "ActivateExternalAssuranceRecordGrant"),
                ("AuthorityGrantRevoked", "RevokeExternalAssuranceRecordGrant"),
            }
            if scoped_authority_event and (draft is None or draft.admission != "scoped_authority"):
                raise ArsError(
                    "scoped authority administration requires the validated "
                    "CommandService scoped-authority continuation"
                )
            if draft is not None and (
                (draft.admission == "release" and event_type != "ReleaseGateDecisionPublished")
                or (draft.admission == "scoped_authority" and not scoped_authority_event)
                or draft.admission not in {"release", "scoped_authority"}
            ):
                raise ArsError("event draft admission does not match its event family")
            stream_version = stream_versions.get(stream_id, 0) + 1
            stream_versions[stream_id] = stream_version
            event_id = new_id("event")
            recorded_at_text = recorded_at.isoformat().replace("+00:00", "Z")
            t2_event = str(candidate.get("schema_id", "")).startswith("ars://wp6-2/t2/event/")
            transaction_index = offset if t2_event else offset + 1
            if draft is None and event_type == "ReleaseGateDecisionPublished":
                raise ArsError("release publication requires a ledger event finalizer")
            if draft is not None and "payload" in candidate:
                raise ArsError("event draft payload must be ledger-finalized")
            allocated = AllocatedEvent(
                event_id=event_id,
                project_id=self.project_id,
                stream_id=stream_id,
                stream_version=stream_version,
                global_position=next_position + offset,
                transaction_id=transaction_id,
                transaction_index=transaction_index,
                transaction_count=count,
                recorded_at=recorded_at_text,
            )
            payload = dict(draft.finalize_payload(allocated)) if draft is not None else candidate.pop("payload", {})
            if draft is None and not t2_event:
                internal_key = f"ledger-internal:{transaction_id}:{offset + 1}"
                candidate.setdefault("schema_id", f"ars://core/event/{event_type}")
                candidate.setdefault("schema_version", "1.0.0")
                candidate.setdefault("command_id", new_id("command"))
                candidate.setdefault("command_type", "LedgerInternalAppend")
                candidate.setdefault("idempotency_key", internal_key)
                candidate.setdefault("command_payload_hash", sha256_hex(canonical_bytes(payload)))
                candidate.setdefault("correlation_id", internal_key)
                candidate.setdefault("causation_id", None)
                candidate.setdefault("actor_id", new_id("actor"))
                candidate.setdefault("authority_grant_id", new_id("authority_grant"))
                candidate.setdefault("occurred_at", None)
            event = {
                "event_id": event_id,
                "event_type": event_type,
                "project_id": self.project_id,
                "stream_id": stream_id,
                "stream_version": stream_version,
                "global_position": next_position + offset,
                "transaction_id": transaction_id,
                "transaction_index": transaction_index,
                "transaction_count": count,
                "recorded_at": recorded_at_text,
                "payload": payload,
                **candidate,
                "previous_event_hash": previous_hash,
            }
            if draft is not None and event_type == "ReleaseGateDecisionPublished":
                decision = payload.get("release_decision")
                if (
                    candidate.get("occurred_at") is not None
                    or not isinstance(decision, dict)
                    or decision.get("release_gate_decision_id") != stream_id
                    or decision.get("canonical_event_ref") != event_id
                ):
                    raise ArsError("release event finalizer violated ledger allocation")
            prehash = {**event, "event_hash": "0" * 64}
            event_schema_version = str(event.get("schema_version", ""))
            event_binding = self.schemas.event_binding(
                event_type,
                str(candidate.get("command_type", "")),
            )
            event_schema = str(event.get("schema_id", ""))
            legacy_authority_event = (
                event_type,
                str(candidate.get("command_type", "")),
                event_schema,
                event_schema_version,
            ) in {
                (
                    "AuthorityGrantActivated",
                    "InitializeAuthorityRoot",
                    "ars://core/event/AuthorityGrantActivated",
                    "1.0.0",
                ),
                (
                    "AuthorityGrantRevoked",
                    "RevokeAuthorityGrant",
                    "ars://core/event",
                    "1.0.0",
                ),
            }
            if event_binding is None and self.schemas.has_producer_bindings(event_type) and not legacy_authority_event:
                raise ArsError(f"unbound event producer: {event_type} from {candidate.get('command_type', '')}")
            payload_schema = f"{event_schema}/payload"
            payload_backed_event = self.schemas.contains(payload_schema)
            if event_binding is not None and (
                event_schema,
                event_schema_version,
            ) != (
                event_binding.schema_id,
                event_binding.schema_version,
            ):
                raise ArsError(
                    f"active event binding mismatch: {event_type} requires "
                    f"{event_binding.schema_id} version {event_binding.schema_version}"
                )
            if (
                self.schemas.requires_command_provenance
                and event_binding is None
                and event_type != "ReleaseGateDecisionPublished"
                and not t2_event
                and not payload_backed_event
                and event_schema != "ars://core/event"
            ):
                raise ArsError(f"inactive event schema: {event_schema} version {event_schema_version}")
            self._validate_event_schema(
                prehash,
                t2_event=t2_event,
                event_type=event_type,
                event_schema=event_schema,
                event_schema_version=event_schema_version,
                event_binding=event_binding,
            )
            event["event_hash"] = sha256_hex(canonical_bytes(event))
            self._validate_event_schema(
                event,
                t2_event=t2_event,
                event_type=event_type,
                event_schema=event_schema,
                event_schema_version=event_schema_version,
                event_binding=event_binding,
            )
            previous_hash = event["event_hash"]
            events.append(event)
        date_root = self.events_root / f"{recorded_at.year:04d}" / f"{recorded_at.month:02d}"
        date_root.mkdir(parents=True, exist_ok=True)
        target = date_root / f"{next_position:020d}-{transaction_id}.jsonl"
        if target.exists():
            raise ConflictError(f"event batch already exists: {target}")
        temporary = self.runtime_root / f"{transaction_id}.jsonl.tmp"
        with temporary.open("xb") as handle:
            for event in events:
                handle.write(canonical_bytes(event) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._after_batch_fsync(temporary)
        self._publish(temporary, target)
        self._after_publish(target)
        self._snapshot = LedgerSnapshot(
            events=current.events + tuple(events),
            global_position=events[-1]["global_position"],
            event_hash=events[-1]["event_hash"],
            stream_versions=stream_versions,
            fingerprint=self._fingerprint(),
        )
        return {
            "event_batch_id": transaction_id,
            "event_ids": [event["event_id"] for event in events],
            "global_positions": [event["global_position"] for event in events],
            "resulting_stream_versions": stream_versions,
        }

    def iter_events(self) -> Iterator[dict[str, Any]]:
        for batch in self.iter_batches():
            yield from batch

    def iter_batches(self) -> Iterator[tuple[dict[str, Any], ...]]:
        for path in self._batch_paths():
            with path.open(encoding="utf-8") as handle:
                batch = tuple(json.loads(line) for line in handle if line.strip())

            if not batch:
                raise ArsError(f"invalid event batch: empty file {path}")

            try:
                transaction_id = batch[0]["transaction_id"]
                transaction_count = batch[0]["transaction_count"]
            except KeyError as exc:
                raise ArsError(f"event batch missing required field: {exc.args[0]}") from exc

            if transaction_count != len(batch):
                raise ArsError("invalid event batch envelope: transaction_count does not match physical line count")

            transaction_indexes: list[int] = []
            for event in batch:
                try:
                    if event["transaction_id"] != transaction_id:
                        raise ArsError("invalid event batch envelope: batch contains multiple transaction_ids")
                    if event["transaction_count"] != transaction_count:
                        raise ArsError("invalid event batch envelope: transaction_count is not contiguous")
                except KeyError as exc:
                    raise ArsError(f"event batch missing required field: {exc.args[0]}") from exc
                transaction_indexes.append(event["transaction_index"])

            expected_zero = list(range(len(batch)))
            expected_one = list(range(1, len(batch) + 1))
            if sorted(transaction_indexes) not in (expected_zero, expected_one):
                raise ArsError("invalid event batch envelope: invalid transaction_index sequence")

            yield batch

    def _batch_paths(self) -> list[Path]:
        paths = list(self.events_root.rglob("*.jsonl"))
        try:
            return sorted(
                paths,
                key=lambda path: int(path.name.partition("-")[0]),
            )
        except ValueError as exc:
            raise ConflictError("invalid event batch filename") from exc

    def _persisted_tail(self) -> tuple[int, str]:
        paths = self._batch_paths()
        if not paths:
            return 0, "0" * 64
        tail_path = max(
            paths,
            key=lambda path: int(path.name.partition("-")[0]),
        )
        lines = [line for line in tail_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            raise ConflictError("persisted ledger tail batch is empty")
        tail = json.loads(lines[-1])
        return tail["global_position"], tail["event_hash"]

    def _fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        records = []
        for path in sorted(self.events_root.rglob("*.jsonl")):
            stat = path.stat()
            records.append(
                (
                    path.relative_to(self.events_root).as_posix(),
                    stat.st_size,
                    stat.st_mtime_ns,
                )
            )
        return tuple(records)

    def _after_batch_fsync(self, temporary: Path) -> None:
        pass

    def _after_publish(self, target: Path) -> None:
        pass

    def _publish(self, source: Path, target: Path) -> None:
        os.replace(source, target)
