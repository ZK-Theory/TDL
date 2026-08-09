from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import load_store_manifest_unbound
from research_system.store.ledger import EventLedger, LedgerSnapshot


_COMMAND_SCHEMA_FIELDS = frozenset(
    {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }
)
_DECISION_SCHEMA_ID = "ars://core/decision/grandfather-command-provenance-prefix"
_PROTOCOL_VERSION = "G-RM-8-GRANDFATHER/1.0.0"
_SHA256_LENGTH = 64


def _require_sha256(value: str, label: str) -> None:
    if len(value) != _SHA256_LENGTH or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a lowercase SHA-256")


def _require_commit_sha(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a full lowercase Git commit SHA")


@dataclass(frozen=True)
class GrandfatherPrefixEvidence:
    """Exact store prefix admitted by one attributed G-RM-8 decision."""

    store_identity: str
    project_id: str
    max_global_position: int
    tail_event_hash: str
    ledger_prefix_sha256: str
    historical_event_set_sha256: str
    missing_triple_positions: tuple[int, ...]
    missing_triple_set_sha256: str
    event_count: int
    batch_count: int

    def __post_init__(self) -> None:
        _require_sha256(self.store_identity, "store identity")
        _require_sha256(self.tail_event_hash, "tail event hash")
        _require_sha256(self.ledger_prefix_sha256, "ledger prefix")
        _require_sha256(self.historical_event_set_sha256, "historical event set")
        _require_sha256(self.missing_triple_set_sha256, "missing-triple set")
        if type(self.max_global_position) is not int or self.max_global_position < 1:
            raise ValueError("grandfather maximum global position must be positive")
        if type(self.event_count) is not int or self.event_count < 1:
            raise ValueError("grandfather event count must be positive")
        if type(self.batch_count) is not int or self.batch_count < 1:
            raise ValueError("grandfather batch count must be positive")
        if any(type(position) is not int or position < 1 for position in self.missing_triple_positions):
            raise ValueError("grandfather missing-triple positions must be positive integers")

    def as_record(self) -> dict[str, Any]:
        return {
            "store_identity": self.store_identity,
            "project_id": self.project_id,
            "max_global_position": self.max_global_position,
            "tail_event_hash": self.tail_event_hash,
            "ledger_prefix_sha256": self.ledger_prefix_sha256,
            "historical_event_set_sha256": self.historical_event_set_sha256,
            "missing_triple_positions": list(self.missing_triple_positions),
            "missing_triple_set_sha256": self.missing_triple_set_sha256,
            "event_count": self.event_count,
            "batch_count": self.batch_count,
        }

    @property
    def sha256(self) -> str:
        return sha256_hex(canonical_bytes(self.as_record()))

    @classmethod
    def from_record(cls, value: Mapping[str, Any]) -> GrandfatherPrefixEvidence:
        expected = {
            "store_identity",
            "project_id",
            "max_global_position",
            "tail_event_hash",
            "ledger_prefix_sha256",
            "historical_event_set_sha256",
            "missing_triple_positions",
            "missing_triple_set_sha256",
            "event_count",
            "batch_count",
        }
        if set(value) != expected or not isinstance(value.get("missing_triple_positions"), list):
            raise IntegrityError("invalid grandfather prefix evidence record")
        try:
            return cls(
                store_identity=str(value["store_identity"]),
                project_id=str(value["project_id"]),
                max_global_position=value["max_global_position"],
                tail_event_hash=str(value["tail_event_hash"]),
                ledger_prefix_sha256=str(value["ledger_prefix_sha256"]),
                historical_event_set_sha256=str(value["historical_event_set_sha256"]),
                missing_triple_positions=tuple(value["missing_triple_positions"]),
                missing_triple_set_sha256=str(value["missing_triple_set_sha256"]),
                event_count=value["event_count"],
                batch_count=value["batch_count"],
            )
        except (TypeError, ValueError) as exc:
            raise IntegrityError("invalid grandfather prefix evidence record") from exc


@dataclass(frozen=True)
class GrandfatherDecision:
    """Attributed owner selection bound to one exact ledger prefix."""

    selected_by: str
    selected_at: str
    owner_statement: str
    candidate_lineage: str
    evidence: GrandfatherPrefixEvidence

    def __post_init__(self) -> None:
        _require_commit_sha(self.candidate_lineage, "candidate lineage")
        if not all((self.selected_by, self.selected_at, self.owner_statement)):
            raise ValueError("grandfather decision attribution is incomplete")

    @classmethod
    def select(
        cls,
        *,
        selected_by: str,
        selected_at: str,
        owner_statement: str,
        candidate_lineage: str,
        evidence: GrandfatherPrefixEvidence,
    ) -> GrandfatherDecision:
        return cls(
            selected_by=selected_by,
            selected_at=selected_at,
            owner_statement=owner_statement,
            candidate_lineage=candidate_lineage,
            evidence=evidence,
        )

    def _unsigned_record(self) -> dict[str, Any]:
        return {
            "schema_id": _DECISION_SCHEMA_ID,
            "schema_version": "1.0.0",
            "protocol": _PROTOCOL_VERSION,
            "selected_by": self.selected_by,
            "selected_at": self.selected_at,
            "owner_statement": self.owner_statement,
            "candidate_lineage": self.candidate_lineage,
            "evidence": self.evidence.as_record(),
            "evidence_sha256": self.evidence.sha256,
        }

    @property
    def sha256(self) -> str:
        return sha256_hex(canonical_bytes(self._unsigned_record()))

    def as_record(self) -> dict[str, Any]:
        return {**self._unsigned_record(), "decision_sha256": self.sha256}

    @classmethod
    def from_record(cls, value: Mapping[str, Any]) -> GrandfatherDecision:
        expected = {
            "schema_id",
            "schema_version",
            "protocol",
            "selected_by",
            "selected_at",
            "owner_statement",
            "candidate_lineage",
            "evidence",
            "evidence_sha256",
            "decision_sha256",
        }
        if (
            set(value) != expected
            or value.get("schema_id") != _DECISION_SCHEMA_ID
            or value.get("schema_version") != "1.0.0"
            or value.get("protocol") != _PROTOCOL_VERSION
            or not isinstance(value.get("evidence"), dict)
        ):
            raise IntegrityError("invalid grandfather decision record")
        evidence = GrandfatherPrefixEvidence.from_record(value["evidence"])
        if value.get("evidence_sha256") != evidence.sha256:
            raise IntegrityError("grandfather evidence hash mismatch")
        try:
            decision = cls(
                selected_by=str(value["selected_by"]),
                selected_at=str(value["selected_at"]),
                owner_statement=str(value["owner_statement"]),
                candidate_lineage=str(value["candidate_lineage"]),
                evidence=evidence,
            )
        except (TypeError, ValueError) as exc:
            raise IntegrityError("invalid grandfather decision record") from exc
        if value.get("decision_sha256") != decision.sha256:
            raise IntegrityError("grandfather decision hash mismatch")
        return decision


def _require_expected_snapshot(current: LedgerSnapshot, expected: LedgerSnapshot) -> None:
    if (
        current.global_position != expected.global_position
        or current.event_hash != expected.event_hash
        or current.fingerprint != expected.fingerprint
    ):
        raise ConflictError("expected ledger tail changed during grandfather capture")


def _store_manifest(ledger: EventLedger) -> dict[str, Any]:
    manifest = load_store_manifest_unbound(ledger.control_root)
    if manifest.get("project_id") != ledger.project_id:
        raise IntegrityError("grandfather store project identity mismatch")
    return manifest


def _derive_prefix_evidence(
    ledger: EventLedger,
    snapshot: LedgerSnapshot,
    *,
    store_identity: str,
    max_global_position: int,
) -> GrandfatherPrefixEvidence:
    if snapshot.global_position < max_global_position:
        raise IntegrityError("grandfather ledger is shorter than the bound prefix")
    prefix_events = tuple(
        event
        for event in snapshot.events
        if event.get("global_position", max_global_position + 1) <= max_global_position
    )
    positions = [event.get("global_position") for event in prefix_events]
    if positions != list(range(1, max_global_position + 1)):
        raise IntegrityError("grandfather prefix positions are not exact and contiguous")

    prefix_digest = hashlib.sha256()
    batch_count = 0
    for path in ledger._batch_paths():
        try:
            batch = tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            batch_positions = [event["global_position"] for event in batch]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise IntegrityError("grandfather prefix batch is unreadable") from exc
        if not batch_positions:
            raise IntegrityError("grandfather prefix batch is empty")
        if min(batch_positions) <= max_global_position < max(batch_positions):
            raise IntegrityError("grandfather prefix boundary splits an event batch")
        if max(batch_positions) > max_global_position:
            continue
        raw = path.read_bytes()
        relative = path.relative_to(ledger.events_root).as_posix().encode("utf-8")
        prefix_digest.update(len(relative).to_bytes(8, "big"))
        prefix_digest.update(relative)
        prefix_digest.update(len(raw).to_bytes(8, "big"))
        prefix_digest.update(raw)
        batch_count += 1

    event_set = [
        {
            "global_position": event["global_position"],
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
        }
        for event in prefix_events
    ]
    missing = tuple(
        event["global_position"]
        for event in prefix_events
        if _COMMAND_SCHEMA_FIELDS.intersection(event) != _COMMAND_SCHEMA_FIELDS
    )
    return GrandfatherPrefixEvidence(
        store_identity=store_identity,
        project_id=ledger.project_id,
        max_global_position=max_global_position,
        tail_event_hash=str(prefix_events[-1]["event_hash"]),
        ledger_prefix_sha256=prefix_digest.hexdigest(),
        historical_event_set_sha256=sha256_hex(canonical_bytes(event_set)),
        missing_triple_positions=missing,
        missing_triple_set_sha256=sha256_hex(canonical_bytes(list(missing))),
        event_count=len(prefix_events),
        batch_count=batch_count,
    )


def capture_grandfather_prefix(
    ledger: EventLedger,
    *,
    expected_snapshot: LedgerSnapshot,
    store_identity: str,
    max_global_position: int,
    expected_tail_hash: str,
) -> GrandfatherPrefixEvidence:
    """Capture one exact prefix cut, guarded by a caller-witnessed ledger tail."""
    current = ledger.snapshot()
    _require_expected_snapshot(current, expected_snapshot)
    if current.global_position != max_global_position or current.event_hash != expected_tail_hash:
        raise ConflictError("expected ledger tail changed during grandfather capture")
    manifest = _store_manifest(ledger)
    if manifest.get("store_identity") != store_identity:
        raise IntegrityError("grandfather store identity mismatch")
    evidence = _derive_prefix_evidence(
        ledger,
        current,
        store_identity=store_identity,
        max_global_position=max_global_position,
    )
    if evidence.missing_triple_positions:
        raise IntegrityError("grandfather capture found non-empty missing-triple evidence")
    if evidence.tail_event_hash != expected_tail_hash:
        raise IntegrityError("grandfather prefix tail hash mismatch")
    _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
    repeated = _derive_prefix_evidence(
        ledger,
        ledger.snapshot(),
        store_identity=store_identity,
        max_global_position=max_global_position,
    )
    if repeated != evidence:
        raise ConflictError("grandfather prefix changed during capture")
    return evidence


def _verify_decision(ledger: EventLedger, decision: GrandfatherDecision) -> LedgerSnapshot:
    expected = decision.evidence
    if expected.missing_triple_positions:
        raise IntegrityError("grandfather decision contains non-empty missing-triple evidence")
    if expected.missing_triple_set_sha256 != sha256_hex(canonical_bytes([])):
        raise IntegrityError("grandfather missing-triple set hash mismatch")
    manifest = _store_manifest(ledger)
    actual_identity = str(manifest.get("store_identity", ""))
    snapshot = ledger.snapshot()
    actual = _derive_prefix_evidence(
        ledger,
        snapshot,
        store_identity=actual_identity,
        max_global_position=expected.max_global_position,
    )
    if actual != expected:
        raise IntegrityError("grandfather prefix evidence mismatch")
    return snapshot


def replay_grandfathered(
    ledger: EventLedger,
    decision: GrandfatherDecision,
    *,
    schema_registry: SchemaRegistry,
    expected_decision_sha256: str,
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Replay a ledger only after exact G-RM-8 prefix admission."""
    try:
        _require_sha256(expected_decision_sha256, "expected grandfather decision")
    except ValueError as exc:
        raise IntegrityError("grandfather decision identity is invalid") from exc
    if decision.sha256 != expected_decision_sha256:
        raise IntegrityError("grandfather decision identity mismatch")
    snapshot = _verify_decision(ledger, decision)
    from research_system.projection.replay import replay

    state = replay(
        snapshot.events,
        schema_registry=schema_registry,
        authority_state_validator=authority_state_validator,
    )
    _verify_decision(ledger, decision)
    _require_expected_snapshot(ledger.snapshot(), snapshot)
    return state


def materialize_grandfather_decision(
    ledger: EventLedger,
    decision: GrandfatherDecision,
    destination: Path,
    *,
    expected_snapshot: LedgerSnapshot,
) -> str:
    """Atomically publish a decision file only while its exact capture tail holds."""
    control_root = ledger.control_root.resolve(strict=True)
    resolved_destination = destination.resolve(strict=False)
    if resolved_destination == control_root or control_root in resolved_destination.parents:
        raise IntegrityError("grandfather decision must not be materialized inside the control store")
    if not destination.parent.is_dir():
        raise IntegrityError("grandfather decision destination parent is unavailable")
    evidence = capture_grandfather_prefix(
        ledger,
        expected_snapshot=expected_snapshot,
        store_identity=decision.evidence.store_identity,
        max_global_position=decision.evidence.max_global_position,
        expected_tail_hash=decision.evidence.tail_event_hash,
    )
    if evidence != decision.evidence:
        raise IntegrityError("grandfather decision evidence does not match the captured prefix")
    data = canonical_bytes(decision.as_record()) + b"\n"
    if destination.exists():
        if destination.read_bytes() != data:
            raise ConflictError("grandfather decision destination conflicts")
        _verify_decision(ledger, decision)
        _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
        return decision.sha256
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _verify_decision(ledger, decision)
        _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
        os.replace(temporary, destination)
        _verify_decision(ledger, decision)
        _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return decision.sha256


def load_grandfather_decision(path: Path) -> GrandfatherDecision:
    """Load and verify one canonical materialized G-RM-8 decision."""
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("invalid grandfather decision file") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value) + b"\n":
        raise IntegrityError("grandfather decision file is noncanonical")
    return GrandfatherDecision.from_record(value)
