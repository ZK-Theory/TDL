"""The W9 legacy runtime: the single W9 append site (06v WP9.2; design note §7).

``LegacyRuntime`` follows ``DiscoveryRuntime``: scoped authority, the same three-root ``CompositeWriterLock``, a
receipt-first retry path, and a whole-ledger replay (generic, Discovery and legacy) before every command. Two things
come before any lock, because taking the lock writes into the control root (design note §7.2):

1. a genesis command's payload must equal :func:`accepted_genesis_payload`;
2. the Gate 6 store refusal: the target store's manifest is read unbound, and a refused store identity is refused with
   reason code ``w9_gate6_store_refused`` (catalogue precondition G1; W9-T20).

The runtime is handed an already bound ledger, as ``DiscoveryRuntime`` is; binding through ``load_store_manifest``
happens where the ledger is built. The refusal reads the ledger's own control root, and every other root the lock
writes into, so it holds whoever bound the ledger. Constructing the runtime writes nothing: the receipt store is built
after the refusal. A caller that builds the ledger must still refuse before binding, as ``ars legacy`` does, because
building an ``EventLedger`` creates its directories (review F-4).
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Collection, Mapping
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.authority import GrantedCommandIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command, Receipt
from research_system.discovery.replay.driver import replay_discovery
from research_system.errors import ConflictError, IntegrityError
from research_system.legacy.accepted_w9 import (
    ACCEPTED,
    ACCEPTED_REVISIONS,
    CATALOGUE_STREAM_ID,
    ROW_IDS,
    accepted_genesis_payload,
)
from research_system.legacy.commands import LEGACY_COMMAND_TYPES
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.routes import (
    LEGACY_DEFERRED_ROWS,
    LEGACY_ROUTED_ROWS,
    validate_legacy_route_registry,
    validate_transaction_shape,
)
from research_system.projection.replay import replay as replay_shared
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import load_store_manifest_unbound
from research_system.store.ledger import EventLedger
from research_system.store.lock import CompositeWriterLock, WriterLock
from research_system.store.receipts import ReceiptStore

_COMMAND_FIELDS = {
    "command_id",
    "command_type",
    "actor_id",
    "authority_grant_id",
    "idempotency_key",
    "target_stream_id",
    "expected_stream_version",
    "payload",
}
GATE6_REASON_CODE = "w9_gate6_store_refused"
# The row each admissible command executes. Only commands whose row is routed can reach preparation.
_COMMAND_ROWS = {"ImportAcceptedW9CatalogueGenesis": "LR-001", "ImportAcceptedW9CatalogueRevision": "LR-002"}


class W9Gate6StoreRefused(IntegrityError):
    """The target store is a refused store identity (W9-T20). Raised before any lock or write."""

    reason_code = GATE6_REASON_CODE


class LegacyLedgerReplayError(IntegrityError):
    """A persisted ledger cannot be reconstructed before W9 command preparation."""


def refuse_gate6_store(control_root: Path, refused_store_identities: Collection[str]) -> None:
    """Refuse a refused store identity from the unbound manifest, before binding or locking (design note §7.2).

    The identity check comes before ``load_store_manifest``'s control-root path check, so a moved or copied Gate 6
    store is refused by this guard itself. The read is read-only and adds no state.

    Args:
        control_root: The target store's control root.
        refused_store_identities: The store identities W9 refuses.

    Raises:
        W9Gate6StoreRefused: If the manifest's store identity is refused.
        IntegrityError: If the manifest cannot be read, so the identity cannot be shown not to be refused.
    """

    try:
        manifest = load_store_manifest_unbound(control_root)
    except (OSError, IntegrityError) as exc:
        raise IntegrityError("W9 cannot read the target store identity before binding") from exc
    if manifest.get("store_identity") in refused_store_identities:
        raise W9Gate6StoreRefused(f"W9 refuses the Gate 6 store ({GATE6_REASON_CODE})")


def refuse_gate6_lock_roots(
    ledger_root: Path, other_roots: Collection[Path], refused_store_identities: Collection[str]
) -> None:
    """Refuse before the lock if any root the lock writes into lies in a refused store (review F-4).

    The ledger's control root must carry a readable manifest with an identity that is not refused. Every lock root (the
    ledger root, the receipt root, the authority root) is refused if any directory at or above it holds a store manifest
    with a refused identity, or a manifest path that cannot be read. So neither a scratch manifest nested inside the
    Gate 6 store nor another root can carry the lock into it.

    Raises:
        W9Gate6StoreRefused: If a lock root lies in a refused store.
        IntegrityError: If the ledger's manifest, or a manifest path at or above any lock root, cannot be read.
    """

    refuse_gate6_store(ledger_root, refused_store_identities)
    checked = {ledger_root.resolve()}
    # The ledger root's own ancestors too: a scratch manifest nested inside the Gate 6 store must not hide it.
    for root in (ledger_root, *other_roots):
        resolved = root.resolve()
        for directory in (resolved, *resolved.parents):
            # lexists: a manifest path that is a directory or a dangling link is read, and refused as unreadable.
            if directory not in checked and os.path.lexists(directory / "manifests" / "store-identity.json"):
                refuse_gate6_store(directory, refused_store_identities)
            checked.add(directory)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False).hexdigest()


def _file_matches(path: Path, length: int, sha256: str, blob: str) -> bytes:
    """Re-hash one accepted file (design note §7.3 guard 6) and return its bytes."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise IntegrityError(f"W9 accepted file is unavailable: {path.name}") from exc
    if len(raw) != length or sha256_hex(raw) != sha256 or _git_blob(raw) != blob:
        raise IntegrityError(f"W9 accepted file identity mismatch: {path.name}")
    return raw


class LegacyRuntime:
    """Public, provider-free W9 command seam: genesis in WP9.2, later rows with their packages."""

    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        schemas: SchemaRegistry,
        *,
        repository_root: Path,
        authority_resolver: LedgerAuthorityGrantResolver,
        clock: Callable[[], datetime],
        routed_rows: Collection[str] = LEGACY_ROUTED_ROWS,
        accepted_revisions: Collection[Mapping[str, Any]] = ACCEPTED_REVISIONS,
    ) -> None:
        """Bind the runtime to its receipt root, bound ledger and repository.

        Args:
            control_root: W9 receipt and writer-lock root.
            ledger: The bound shared event ledger.
            schemas: Active schema registry used for command and event identities.
            repository_root: Repository root holding the accepted catalogue, annex, contract and envelope.
            authority_resolver: Canonical current-grant resolver.
            clock: Trusted timezone-aware runtime clock.
            routed_rows: Rows this runtime may execute. Production routes LR-001 only.
            accepted_revisions: Accepted catalogue revisions LR-002 may import. None exists in v1.

        Raises:
            IntegrityError: If the repository root is unavailable.
            TypeError: If a canonical authority resolver is not supplied.
        """
        self.control_root = control_root
        self.ledger = ledger
        self.schemas = schemas
        try:
            self.repository_root = repository_root.resolve(strict=True)
        except OSError as exc:
            raise IntegrityError("configured repository root is unavailable") from exc
        if not isinstance(authority_resolver, LedgerAuthorityGrantResolver):
            raise TypeError("LegacyRuntime requires LedgerAuthorityGrantResolver")
        self.authority_resolver = authority_resolver
        self.clock = clock
        self.routed_rows = frozenset(routed_rows)
        self.accepted_revisions = tuple(accepted_revisions)
        # Built in submit, after the Gate 6 refusal: ReceiptStore creates its directories (review F-4).
        self._receipts: ReceiptStore | None = None
        self.refused_store_identities = frozenset(accepted_genesis_payload()["refused_store_identities"])

    @property
    def receipts(self) -> ReceiptStore:
        """The W9 receipt store, which ``submit`` creates after the Gate 6 refusal.

        Raises:
            IntegrityError: If it is used before ``submit`` has passed the refusal.
        """
        if self._receipts is None:
            raise IntegrityError("W9 receipt store used before the Gate 6 refusal")
        return self._receipts

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Authorize and atomically submit one W9 command.

        Args:
            envelope: Complete governed command envelope.

        Returns:
            Durable accepted or conflict receipt for the exact command.

        Raises:
            W9Gate6StoreRefused: If the bound store is a refused store identity.
            ConflictError: If a committed receipt or writer state conflicts with the command identity.
            IntegrityError: If the payload, authority, replay state or requested row is invalid.
        """
        if set(envelope) != _COMMAND_FIELDS or not isinstance(envelope.get("payload"), dict):
            raise IntegrityError("invalid W9 command envelope")
        command = Command(deepcopy(envelope))
        try:
            command.payload_hash
        except (TypeError, ValueError) as exc:
            raise IntegrityError("W9 command payload is not P0-canonical") from exc
        command_type = envelope["command_type"]
        if command_type not in LEGACY_COMMAND_TYPES:
            raise IntegrityError(f"not a W9 command: {command_type}")
        if command_type == "ImportAcceptedW9CatalogueGenesis" and envelope["payload"] != accepted_genesis_payload():
            raise IntegrityError("W9 genesis payload differs from the accepted identity")
        refuse_gate6_lock_roots(
            self.ledger.control_root,
            (self.control_root, self.authority_resolver.control_root),
            self.refused_store_identities,
        )
        if getattr(self.ledger, "store_identity", None) in self.refused_store_identities:
            raise W9Gate6StoreRefused(f"W9 refuses the Gate 6 store ({GATE6_REASON_CODE})")
        if self._receipts is None:
            # The first write, after the refusal: the receipt store creates the directories the writer lock takes.
            self._receipts = ReceiptStore(self.control_root)
        with CompositeWriterLock(
            (self.control_root, self.authority_resolver.control_root, self.ledger.control_root),
            {"command_id": command.command_id},
            lock_factory=WriterLock,
        ):
            authority_evidence = self._resolve_authority(command)
            return self._submit_authorized(command, authority_evidence)

    def _resolve_authority(self, command: Command) -> Any:
        """Resolve current scoped authority: subject ``scope_definition``, the exact target stream (O-4; G4)."""
        command_type = command.envelope["command_type"]
        binding = self.schemas.command_binding(command_type)
        if binding is None:
            raise IntegrityError(f"inactive W9 command binding: {command_type}")
        identity = self.schemas.resolve_identity(binding.schema_id, binding.schema_version)
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("W9 authority clock must return an aware datetime")
        evidence = self.authority_resolver.resolve_lifecycle_command(
            command.envelope["authority_grant_id"],
            command.actor_id,
            GrantedCommandIdentity(
                command_type=command_type,
                schema_id=identity.schema_id,
                schema_version=identity.schema_version,
                schema_sha256=identity.sha256,
            ),
            "R2",
            self.ledger.project_id,
            "scope_definition",
            command.target_stream_id,
            now.astimezone(UTC),
        )
        # The genesis grant's one actor class is human: LR-001's operator is a role that maps to it (n-4).
        if command_type == "ImportAcceptedW9CatalogueGenesis" and evidence.actor_class != "human":
            raise IntegrityError("W9 genesis requires a human actor")
        return evidence

    def _replay(self, events: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Replay the whole ledger (generic, Discovery and legacy) and return the Discovery and legacy projections."""
        validator = self.authority_resolver.validate_replayed_administration_state
        try:
            replay_shared(events, schema_registry=self.schemas, authority_state_validator=validator)
            discovery = replay_discovery(events, schemas=self.schemas, authority_state_validator=validator)
            legacy = replay_legacy(
                events,
                schemas=self.schemas,
                routed_rows=self.routed_rows,
                accepted_revisions=self.accepted_revisions,
            )
        except (IntegrityError, TypeError, ValueError) as exc:
            raise LegacyLedgerReplayError("persisted ledger failed replay before W9 command preparation") from exc
        return discovery, legacy

    def _submit_authorized(self, command: Command, authority_evidence: Any) -> Receipt:
        """Answer a retry from receipts, else prepare, append and receipt one authorized command."""
        envelope = command.envelope
        authority_sha256 = authority_evidence.command_resolution.authority_grant_sha256
        idempotency_scope = (
            command.actor_id,
            envelope["authority_grant_id"],
            envelope["command_type"],
            command.idempotency_key,
        )

        def immutable_envelope_sha256(command_id: str) -> str:
            """Hash the complete envelope persisted for one command identity."""
            return sha256_hex(
                canonical_bytes(
                    {
                        "command_id": command_id,
                        "command_type": envelope["command_type"],
                        "actor_id": command.actor_id,
                        "authority_grant_id": envelope["authority_grant_id"],
                        "authority_grant_sha256": authority_sha256,
                        "idempotency_key": command.idempotency_key,
                        "target_stream_id": command.target_stream_id,
                        "expected_stream_version": command.expected_stream_version,
                        "payload_hash": command.payload_hash,
                    }
                )
            )

        envelope_sha256 = immutable_envelope_sha256(command.command_id)

        def committed_transaction(command_id: str) -> tuple[Mapping[str, Any] | None, tuple[dict[str, Any], ...]]:
            """Resolve one command's exact contiguous committed transaction."""
            committed_event = next((event for event in snapshot.events if event.get("command_id") == command_id), None)
            if not isinstance(committed_event, Mapping):
                return None, ()
            members = tuple(
                event
                for event in snapshot.events
                if event.get("transaction_id") == committed_event.get("transaction_id")
            )
            if (
                any(event.get("command_id") != command_id for event in members)
                or committed_event.get("command_payload_hash") != command.payload_hash
                or committed_event.get("command_type") != envelope["command_type"]
                or committed_event.get("actor_id") != command.actor_id
                or committed_event.get("authority_grant_id") != envelope["authority_grant_id"]
                or committed_event.get("idempotency_key") != command.idempotency_key
                or committed_event.get("correlation_id") != immutable_envelope_sha256(command_id)
            ):
                raise ConflictError("committed command envelope mismatch")
            return committed_event, members

        def accepted_receipt(committed_event: Mapping[str, Any], members: tuple[dict[str, Any], ...]) -> Receipt:
            versions = [
                event["stream_version"] for event in members if event.get("stream_id") == command.target_stream_id
            ]
            if not versions:
                raise ConflictError("committed command target transaction mismatch")
            return Receipt(
                status="accepted",
                command_id=str(committed_event["command_id"]),
                payload_hash=str(committed_event["command_payload_hash"]),
                event_batch_id=str(committed_event["transaction_id"]),
                observed_stream_version=max(versions),
                reason_code=None,
            )

        def persist(receipt: Receipt) -> Receipt:
            return self.receipts.write_scoped(
                idempotency_scope,
                authority_sha256,
                command.expected_stream_version,
                receipt,
                project_id=self.ledger.project_id,
                target_stream_id=command.target_stream_id,
            )

        snapshot = self.ledger.snapshot()
        discovery, legacy = self._replay(tuple(snapshot.events))
        # Retries come first (confirmation n-2): the guards below never see a retry.
        scoped = self.receipts.load_scoped(
            idempotency_scope,
            command.payload_hash,
            authority_sha256,
            command.expected_stream_version,
            project_id=self.ledger.project_id,
            target_stream_id=command.target_stream_id,
        )
        if scoped is not None:
            scoped_committed, scoped_members = committed_transaction(scoped.command_id)
            if scoped.status == "accepted" and (
                scoped_committed is None or scoped != accepted_receipt(scoped_committed, scoped_members)
            ):
                raise ConflictError("idempotency receipt committed transaction mismatch")
            if scoped.status != "accepted" and scoped_committed is not None:
                raise ConflictError("idempotency receipt committed transaction mismatch")
            primary = self.receipts.load(scoped.command_id)
            if primary is not None and primary != scoped:
                raise ConflictError("idempotency primary receipt mismatch")
            if primary is None:
                self.receipts.write(scoped)
            return scoped
        committed, members = committed_transaction(command.command_id)
        existing = self.receipts.load(command.command_id)
        if existing is not None:
            if committed is None or existing != accepted_receipt(committed, members):
                raise ConflictError("command receipt committed transaction mismatch")
            return persist(existing)
        if committed is not None:
            return persist(accepted_receipt(committed, members))
        observed = snapshot.stream_versions.get(command.target_stream_id, 0)
        if observed != command.expected_stream_version:
            return persist(
                Receipt(
                    status="conflict",
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=None,
                    observed_stream_version=observed,
                    reason_code="stream_version_conflict",
                )
            )
        row_id = _COMMAND_ROWS.get(envelope["command_type"])
        if row_id is None or row_id not in self.routed_rows:
            tag = LEGACY_DEFERRED_ROWS.get(row_id or "", "unrouted")
            raise IntegrityError(f"W9 row not routed in this version: {row_id or envelope['command_type']} ({tag})")
        if row_id == "LR-001":
            prepared = [
                ("W9CatalogueGenesisImported", CATALOGUE_STREAM_ID, self._prepare_genesis(command, discovery, legacy))
            ]
        else:
            prepared = [("W9CatalogueRevisionImported", CATALOGUE_STREAM_ID, self._prepare_revision(command, legacy))]
        validate_transaction_shape(row_id, [event_type for event_type, _, _ in prepared])
        binding = self.schemas.resolve_identity(*self._command_schema(envelope["command_type"]))
        occurred_at = self.clock()
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise IntegrityError("W9 runtime clock must return an aware datetime")
        occurred_at_value = occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        event_records = [
            {
                "event_type": event_type,
                # E: events have no producer binding and fall back to ars://core/event (design note §4).
                "schema_id": "ars://core/event",
                "schema_version": "1.0.0",
                "stream_id": stream_id,
                "command_id": command.command_id,
                "command_type": envelope["command_type"],
                "command_schema_id": binding.schema_id,
                "command_schema_version": binding.schema_version,
                "command_schema_sha256": binding.raw_bytes_sha256,
                "idempotency_key": command.idempotency_key,
                "command_payload_hash": command.payload_hash,
                "correlation_id": envelope_sha256,
                "causation_id": None,
                "actor_id": command.actor_id,
                "authority_grant_id": envelope["authority_grant_id"],
                "occurred_at": occurred_at_value,
                "payload": deepcopy(payload),
            }
            for event_type, stream_id, payload in prepared
        ]
        result = self.ledger.append(event_records, snapshot=snapshot)
        return persist(
            Receipt(
                status="accepted",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=result["event_batch_id"],
                observed_stream_version=result["resulting_stream_versions"][command.target_stream_id],
                reason_code=None,
            )
        )

    def _command_schema(self, command_type: str) -> tuple[str, str]:
        binding = self.schemas.command_binding(command_type)
        if binding is None:
            raise IntegrityError(f"inactive W9 command binding: {command_type}")
        return binding.schema_id, binding.schema_version

    def _prepare_genesis(
        self, command: Command, discovery: Mapping[str, Any], legacy: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Verify and prepare the one-time W9 genesis: design note §7.3 guards 1 to 8, in order, under the lock."""
        payload = command.envelope["payload"]
        w11 = discovery.get("catalogue")
        if not isinstance(w11, Mapping):
            raise IntegrityError("W9 genesis requires the W11 catalogue in the replayed Discovery projection")
        required = payload["required_w11_catalogue"]
        if (w11.get("catalogue_blob"), w11.get("catalogue_sha256"), w11.get("catalogue_bytes")) != (
            required["git_blob"],
            required["raw_sha256"],
            required["raw_bytes"],
        ):
            raise IntegrityError("the replayed W11 catalogue is not the W9 genesis's required W11 catalogue")
        if legacy.get("catalogue") is not None:
            raise IntegrityError("second W9 genesis")
        if command.target_stream_id != CATALOGUE_STREAM_ID:
            raise IntegrityError("W9 genesis stream identity mismatch")
        if command.expected_stream_version != 0:
            raise IntegrityError("W9 genesis stream version mismatch")
        root = self.repository_root
        raw = _file_matches(
            root / ACCEPTED["catalogue_path"],
            ACCEPTED["catalogue_bytes"],
            ACCEPTED["catalogue_sha256"],
            ACCEPTED["catalogue_blob"],
        )
        for prefix in ("annex", "bootstrap"):
            _file_matches(
                root / ACCEPTED[f"{prefix}_path"],
                ACCEPTED[f"{prefix}_bytes"],
                ACCEPTED[f"{prefix}_sha256"],
                ACCEPTED[f"{prefix}_blob"],
            )
        envelope_raw = _file_matches(
            root / ACCEPTED["envelope_path"],
            ACCEPTED["envelope_bytes"],
            ACCEPTED["envelope_sha256"],
            ACCEPTED["envelope_blob"],
        )
        catalogue = json.loads(raw)
        envelope = json.loads(envelope_raw)
        row_ids = tuple(row.get("owner_row_id") for row in catalogue.get("owner_contract_rows", ()))
        if catalogue.get("owner_row_count") != 61 or row_ids != ROW_IDS:
            raise IntegrityError("W9 catalogue row set mismatch")
        if envelope.get("owner_row_multiset_hash") != ACCEPTED["owner_row_multiset_hash"]:
            raise IntegrityError("W9 owner-row multiset hash mismatch")
        validate_legacy_route_registry(catalogue)
        return accepted_genesis_payload()

    def _prepare_revision(self, command: Command, legacy: Mapping[str, Any]) -> dict[str, Any]:
        """LR-002: import an accepted catalogue revision. Inert in v1, where none exists."""
        if legacy.get("catalogue") is None:
            raise IntegrityError("W9 genesis is required before LR-002")
        if command.target_stream_id != CATALOGUE_STREAM_ID:
            raise IntegrityError("W9 catalogue revision stream identity mismatch")
        payload = command.envelope["payload"]
        if payload not in self.accepted_revisions:
            raise IntegrityError("W9 catalogue revision is not an accepted revision")
        if payload in legacy.get("catalogue_revisions", []):
            raise IntegrityError("W9 catalogue revision already imported")
        return deepcopy(payload)
