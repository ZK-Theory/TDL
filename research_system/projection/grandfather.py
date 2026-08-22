from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.schema_registry import SchemaRegistry
from research_system.store.durability import fsync_directory
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
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_DATA = Path(__file__).with_name("data")
_AUTHORITY_MANIFEST_PATH = _PACKAGE_DATA / "wp6_1_06h_grandfather_authority.yaml"
_SELECTED_DECISION_RELATIVE_PATH = (
    "research_system/projection/data/06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json"
)
_SELECTED_DECISION_PATH = _PACKAGE_DATA / "06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json"
_SELECTED_CANDIDATE_LINEAGE = "3c75d3d102d8fe14746b19662005e88c4b776ffa"


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
        """Return the exact serializable prefix-evidence record.

        Returns:
            A dictionary containing every field bound by the prefix evidence.
        """
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
        """Return the SHA-256 of the canonical prefix-evidence record.

        Returns:
            The lowercase hexadecimal SHA-256 digest.
        """
        return sha256_hex(canonical_bytes(self.as_record()))

    @classmethod
    def from_record(cls, value: Mapping[str, Any]) -> GrandfatherPrefixEvidence:
        """Reconstruct validated prefix evidence from a serialized record.

        Args:
            value: Candidate record containing the exact evidence fields.

        Returns:
            Validated immutable prefix evidence.

        Raises:
            IntegrityError: If fields, types, hashes, or numeric bounds are invalid.
        """
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
        """Return the SHA-256 of the canonical unsigned owner decision.

        Returns:
            The lowercase hexadecimal SHA-256 digest.
        """
        return sha256_hex(canonical_bytes(self._unsigned_record()))

    def as_record(self) -> dict[str, Any]:
        """Return the signed serializable owner-decision record.

        Returns:
            The complete decision record including its canonical SHA-256.
        """
        return {**self._unsigned_record(), "decision_sha256": self.sha256}

    @classmethod
    def from_record(cls, value: Mapping[str, Any]) -> GrandfatherDecision:
        """Reconstruct and authenticate an attributed owner decision.

        Args:
            value: Candidate record containing the exact decision fields.

        Returns:
            The validated immutable grandfather decision.

        Raises:
            IntegrityError: If structure, protocol, evidence, attribution, or hashes are invalid.
        """
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


def _file_identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _authenticate_published_destination(
    destination: Path,
    data: bytes,
    *,
    parent_identity: tuple[int, int],
    source_identity: tuple[int, int] | None,
) -> None:
    try:
        if destination.is_symlink():
            raise IntegrityError("grandfather decision destination must not be a symlink")
        if _file_identity(destination.parent.stat(follow_symlinks=False)) != parent_identity:
            raise ConflictError("grandfather decision destination parent changed")
        with destination.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise IntegrityError("grandfather decision published destination is not a regular file")
            if source_identity is not None and _file_identity(opened) != source_identity:
                raise ConflictError("grandfather decision published destination identity mismatch")
            if handle.read() != data:
                raise ConflictError("grandfather decision published destination conflicts")
            linked = destination.stat(follow_symlinks=False)
            if _file_identity(linked) != _file_identity(opened):
                raise ConflictError("grandfather decision published destination changed")
            if _file_identity(destination.parent.stat(follow_symlinks=False)) != parent_identity:
                raise ConflictError("grandfather decision destination parent changed")
    except FileNotFoundError as exc:
        raise ConflictError("grandfather decision published destination disappeared") from exc


class _PublicationDirectory:
    """Replacement-fenced directory operations for the grandfather writer."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._parent_identity = _file_identity(path.stat(follow_symlinks=False))
        self._anchor = None
        self._descriptor: int | None = None
        if os.name == "nt":
            from research_system.store.lock import _open_directory_anchor

            self._anchor = _open_directory_anchor(
                path,
                reject_reparse=True,
                delete_protect=True,
            )
        else:
            directory_flag = getattr(os, "O_DIRECTORY", 0)
            nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
            if not directory_flag or not nofollow_flag:
                raise IntegrityError("platform cannot pin grandfather destination parent")
            try:
                self._descriptor = os.open(path, os.O_RDONLY | directory_flag | nofollow_flag)
            except OSError as exc:
                raise IntegrityError("grandfather decision destination parent is unavailable") from exc
        self.ensure_current()

    def ensure_current(self) -> None:
        try:
            if _file_identity(self.path.stat(follow_symlinks=False)) != self._parent_identity:
                raise ConflictError("grandfather decision destination parent changed")
            if self._anchor is not None:
                identity, final_path = self._anchor.refresh()
                if identity != self._anchor.identity or final_path != self._anchor.final_path:
                    raise ConflictError("grandfather decision destination parent changed")
            elif self._descriptor is not None:
                observed = os.fstat(self._descriptor)
                if not stat.S_ISDIR(observed.st_mode) or _file_identity(observed) != self._parent_identity:
                    raise ConflictError("grandfather decision destination parent changed")
        except FileNotFoundError as exc:
            raise ConflictError("grandfather decision destination parent disappeared") from exc

    def exists(self, name: str) -> bool:
        self.ensure_current()
        if self._descriptor is None:
            return (self.path / name).exists()
        try:
            os.stat(name, dir_fd=self._descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return True

    def open_new(self, name: str):
        self.ensure_current()
        if self._descriptor is None:
            return (self.path / name).open("xb")
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=self._descriptor,
        )
        return os.fdopen(descriptor, "wb")

    def link(self, source_name: str, destination_name: str) -> None:
        self.ensure_current()
        if self._descriptor is None:
            os.link(self.path / source_name, self.path / destination_name)
        else:
            os.link(
                source_name,
                destination_name,
                src_dir_fd=self._descriptor,
                dst_dir_fd=self._descriptor,
                follow_symlinks=False,
            )
        self.ensure_current()
        self.fsync()

    def authenticate(
        self,
        name: str,
        data: bytes,
        *,
        source_identity: tuple[int, int] | None,
    ) -> None:
        self.ensure_current()
        if self._descriptor is None:
            _authenticate_published_destination(
                self.path / name,
                data,
                parent_identity=self._parent_identity,
                source_identity=source_identity,
            )
            self.ensure_current()
            return
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(name, flags, dir_fd=self._descriptor)
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode):
                    raise IntegrityError("grandfather decision published destination is not a regular file")
                if source_identity is not None and _file_identity(opened) != source_identity:
                    raise ConflictError("grandfather decision published destination identity mismatch")
                with os.fdopen(descriptor, "rb", closefd=False) as handle:
                    if handle.read() != data:
                        raise ConflictError("grandfather decision published destination conflicts")
                linked = os.stat(name, dir_fd=self._descriptor, follow_symlinks=False)
                if _file_identity(linked) != _file_identity(opened):
                    raise ConflictError("grandfather decision published destination changed")
            finally:
                os.close(descriptor)
        except FileNotFoundError as exc:
            raise ConflictError("grandfather decision published destination disappeared") from exc
        self.ensure_current()

    def cleanup_created_link(
        self,
        name: str,
        data: bytes,
        *,
        source_name: str,
        source_identity: tuple[int, int],
    ) -> None:
        """Remove a prohibited generation after this writer created the link."""
        self.authenticate(source_name, data, source_identity=source_identity)
        try:
            self.authenticate(name, data, source_identity=None)
        except (ConflictError, IntegrityError):
            try:
                self.unlink(name, missing_ok=True)
            except (OSError, ConflictError, IntegrityError) as exc:
                raise ConflictError("grandfather decision destination cleanup failed") from exc
        try:
            if self.exists(name):
                self.authenticate(name, data, source_identity=None)
        except (OSError, ConflictError, IntegrityError) as exc:
            raise ConflictError("grandfather decision destination cleanup failed") from exc

    def unlink(self, name: str, *, missing_ok: bool) -> None:
        try:
            if self._descriptor is None:
                (self.path / name).unlink(missing_ok=missing_ok)
            else:
                os.unlink(name, dir_fd=self._descriptor)
        except FileNotFoundError:
            if not missing_ok:
                raise
            return
        self.fsync()

    def fsync(self) -> None:
        if self._descriptor is None:
            fsync_directory(self.path)
        else:
            os.fsync(self._descriptor)

    def close(self) -> None:
        if self._anchor is not None:
            self._anchor.close()
            self._anchor = None
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None


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
    snapshot_prefix_events = tuple(
        event
        for event in snapshot.events
        if event.get("global_position", max_global_position + 1) <= max_global_position
    )

    prefix_digest = hashlib.sha256()
    batch_count = 0
    captured_events: list[Mapping[str, Any]] = []
    try:
        batch_paths = sorted(
            ledger._batch_paths(),
            key=lambda path: (
                int(path.name.partition("-")[0]),
                path.relative_to(ledger.events_root).as_posix(),
            ),
        )
    except ValueError as exc:
        raise IntegrityError("grandfather prefix batch path is invalid") from exc
    for path in batch_paths:
        try:
            raw = path.read_bytes()
            batch = tuple(json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip())
            batch_positions = [event["global_position"] for event in batch]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise IntegrityError("grandfather prefix batch is unreadable") from exc
        if not batch_positions:
            raise IntegrityError("grandfather prefix batch is empty")
        if min(batch_positions) <= max_global_position < max(batch_positions):
            raise IntegrityError("grandfather prefix boundary splits an event batch")
        if max(batch_positions) > max_global_position:
            continue
        captured_events.extend(batch)
        relative = path.relative_to(ledger.events_root).as_posix().encode("utf-8")
        prefix_digest.update(len(relative).to_bytes(8, "big"))
        prefix_digest.update(relative)
        prefix_digest.update(len(raw).to_bytes(8, "big"))
        prefix_digest.update(raw)
        batch_count += 1

    prefix_events = tuple(captured_events)
    positions = [event.get("global_position") for event in prefix_events]
    if positions != list(range(1, max_global_position + 1)):
        raise IntegrityError("grandfather prefix positions are not exact and contiguous")
    if prefix_events != snapshot_prefix_events:
        raise ConflictError("grandfather prefix content changed during capture")

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
    if type(max_global_position) is not int or max_global_position < 1:
        raise IntegrityError("grandfather maximum global position must be positive")
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
    if expected.missing_triple_set_sha256 != sha256_hex(canonical_bytes(list(expected.missing_triple_positions))):
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
    authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
    registered_source_resolver: Callable[[Mapping[str, object]], Mapping[str, object]] | None = None,
) -> dict[str, Any]:
    """Replay a ledger only after exact G-RM-8 prefix admission."""
    if not isinstance(schema_registry, SchemaRegistry):
        raise IntegrityError("grandfather schema registry is invalid")
    selected = load_selected_grandfather_decision()
    if decision.as_record() != selected.as_record():
        raise IntegrityError("grandfather decision authority mismatch")
    snapshot = _verify_decision(ledger, decision)
    from research_system.projection.replay import _replay

    state = _replay(
        snapshot.events,
        supported_major=1,
        schema_registry=schema_registry,
        grandfathered_missing_positions=frozenset(decision.evidence.missing_triple_positions),
        authority_state_validator=authority_state_validator,
        registered_source_resolver=registered_source_resolver,
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
    if destination.parent.is_symlink() or destination.parent.resolve(strict=True) != destination.parent.absolute():
        raise IntegrityError("grandfather decision destination parent must not use symlinks")
    publication = _PublicationDirectory(destination.parent)
    try:
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
        if publication.exists(destination.name):
            publication.authenticate(destination.name, data, source_identity=None)
            _verify_decision(ledger, decision)
            _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
            return decision.sha256
        temporary_name = f".{destination.name}.{os.getpid()}-{secrets.token_hex(8)}.tmp"
        try:
            with publication.open_new(temporary_name) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_identity = _file_identity(os.fstat(handle.fileno()))
            _verify_decision(ledger, decision)
            _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
            created_link = False
            try:
                publication.link(temporary_name, destination.name)
                created_link = True
            except FileExistsError:
                temporary_identity = None
            try:
                publication.authenticate(
                    destination.name,
                    data,
                    source_identity=temporary_identity,
                )
            except (ConflictError, IntegrityError) as publish_error:
                if created_link:
                    if temporary_identity is None:
                        raise IntegrityError("grandfather decision publication source identity is unavailable")
                    try:
                        publication.cleanup_created_link(
                            destination.name,
                            data,
                            source_name=temporary_name,
                            source_identity=temporary_identity,
                        )
                    except ConflictError as cleanup_error:
                        raise cleanup_error from publish_error
                raise
            _verify_decision(ledger, decision)
            _require_expected_snapshot(ledger.snapshot(), expected_snapshot)
        except BaseException:
            publication.unlink(temporary_name, missing_ok=True)
            raise
        publication.unlink(temporary_name, missing_ok=True)
        return decision.sha256
    finally:
        publication.close()


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


def load_selected_grandfather_decision() -> GrandfatherDecision:
    """Resolve the owner-selected decision through its independent manifest pin."""
    try:
        manifest = yaml.safe_load(_AUTHORITY_MANIFEST_PATH.read_text(encoding="utf-8"))
        historical = manifest["historical_evidence"]
    except (OSError, UnicodeError, yaml.YAMLError, KeyError, TypeError) as exc:
        raise IntegrityError("grandfather authority manifest is invalid") from exc
    if (
        not isinstance(manifest, Mapping)
        or not isinstance(historical, Mapping)
        or manifest.get("schema_id") != "ars://tests/wp6-1/06h-current-append-manifest"
        or manifest.get("schema_version") != "1.0.0"
        or historical.get("protocol_activation") != _PROTOCOL_VERSION
        or historical.get("decision_record") != _SELECTED_DECISION_RELATIVE_PATH
        or historical.get("selected_lineage") != _SELECTED_CANDIDATE_LINEAGE
    ):
        raise IntegrityError("grandfather authority manifest is invalid")
    decision = load_grandfather_decision(_SELECTED_DECISION_PATH)
    if (
        historical.get("owner_protocol_decision") != decision.sha256
        or decision.candidate_lineage != _SELECTED_CANDIDATE_LINEAGE
    ):
        raise IntegrityError("grandfather authority manifest pin mismatch")
    return decision
