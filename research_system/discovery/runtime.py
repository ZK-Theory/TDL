from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command, Receipt
from research_system.errors import ConflictError, IntegrityError
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.receipts import ReceiptStore


_ACCEPTED = {
    "accepted_commit": "09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6",
    "accepted_tree": "151e0f8b24ad76913640aa0f1de66cd177a44f8f",
    "catalogue_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
    "catalogue_bytes": 136229,
    "catalogue_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
    "bootstrap_blob": "aac7242072c3ce62370dd74d9a27a29e1a33070d",
    "bootstrap_sha256": "ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38",
    "review_commit": "bd61f00d05191de1fd330e997d33ba74ac1b506c",
    "review_blob": "2e0deee51e526cc712c6b04a79695abaa4fb6442",
    "review_sha256": "beb96faa0b58d3ba5faf326b94bb7bc7e1d6649b00c577f2239e1083fe09eaf9",
    "owner_decision": "I accept the KAN 84 envelope, proceed.",
}
_ROW_IDS = tuple(
    [*(f"OR-{number:03d}" for number in range(1, 42)), *(f"OR-{number:03d}" for number in range(101, 141))]
)
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


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()  # noqa: S324


def _validate_hash_chain(events: tuple[dict[str, Any], ...]) -> None:
    last_position = 0
    last_hash = "0" * 64
    for event in events:
        if event.get("global_position") != last_position + 1 or event.get("previous_event_hash") != last_hash:
            raise IntegrityError("Discovery event chain mismatch")
        unsigned = dict(event)
        recorded = unsigned.pop("event_hash", None)
        if recorded != sha256_hex(canonical_bytes(unsigned)):
            raise IntegrityError("Discovery event hash mismatch")
        last_position = event["global_position"]
        last_hash = event["event_hash"]


def replay_discovery(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    ordered = tuple(deepcopy(tuple(events)))
    _validate_hash_chain(ordered)
    state: dict[str, Any] = {"catalogue": None, "candidates": {}}
    for event in ordered:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if event_type == "W11CatalogueGenesisImported":
            if state["catalogue"] is not None:
                raise IntegrityError("W11 genesis appears more than once")
            state["catalogue"] = deepcopy(payload)
        elif event_type == "CandidateRegistered":
            if state["catalogue"] is None:
                raise IntegrityError("Candidate event predates W11 genesis")
            candidate_id = payload.get("candidate_id") if isinstance(payload, dict) else None
            if not isinstance(candidate_id, str) or candidate_id in state["candidates"]:
                raise IntegrityError("Candidate identity collision")
            state["candidates"][candidate_id] = {**deepcopy(payload), "status": "registered", "version": 1}
        else:
            raise IntegrityError(f"unsupported Discovery event: {event_type}")
    return state


class DiscoveryRuntime:
    """Public, provider-free W11 genesis and Discovery lifecycle seam."""

    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        schemas: SchemaRegistry,
        *,
        catalogue_path: Path,
    ) -> None:
        self.control_root = control_root
        self.ledger = ledger
        self.schemas = schemas
        self.catalogue_path = catalogue_path
        self.receipts = ReceiptStore(control_root)

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        if set(envelope) != _COMMAND_FIELDS or not isinstance(envelope.get("payload"), dict):
            raise IntegrityError("invalid Discovery command envelope")
        command = Command(deepcopy(envelope))
        if envelope["command_type"] == "ImportAcceptedW11CatalogueGenesis" and command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        existing = self.receipts.load(command.command_id)
        if existing is not None:
            if existing.payload_hash != command.payload_hash:
                raise ConflictError("command receipt payload mismatch")
            return existing

        snapshot = self.ledger.snapshot()
        committed = next(
            (event for event in snapshot.events if event.get("command_id") == command.command_id),
            None,
        )
        if committed is not None:
            if committed.get("command_payload_hash") != command.payload_hash:
                raise ConflictError("committed command payload mismatch")
            receipt = Receipt(
                status="accepted",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=committed["transaction_id"],
                observed_stream_version=committed["stream_version"],
                reason_code=None,
            )
            return self.receipts.write(receipt)
        observed = snapshot.stream_versions.get(command.target_stream_id, 0)
        if observed != command.expected_stream_version:
            receipt = Receipt(
                status="conflict",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=None,
                observed_stream_version=observed,
                reason_code="stream_version_conflict",
            )
            return self.receipts.write(receipt)

        projection = replay_discovery(snapshot.events)
        if envelope["command_type"] == "ImportAcceptedW11CatalogueGenesis":
            event_type, event_payload = self._prepare_genesis(command, projection)
        elif envelope["command_type"] == "RegisterCandidate":
            event_type, event_payload = self._prepare_candidate(command, projection)
        else:
            raise IntegrityError(f"unsupported Discovery command: {envelope['command_type']}")
        binding = self.schemas.resolve_identity("ars://core/command", "1.0.0")
        result = self.ledger.append(
            [
                {
                    "event_type": event_type,
                    "schema_id": "ars://core/event",
                    "schema_version": "1.0.0",
                    "stream_id": command.target_stream_id,
                    "command_id": command.command_id,
                    "command_type": envelope["command_type"],
                    "command_schema_id": binding.schema_id,
                    "command_schema_version": binding.schema_version,
                    "command_schema_sha256": binding.raw_bytes_sha256,
                    "idempotency_key": command.idempotency_key,
                    "command_payload_hash": command.payload_hash,
                    "correlation_id": command.idempotency_key,
                    "causation_id": None,
                    "actor_id": command.actor_id,
                    "authority_grant_id": envelope["authority_grant_id"],
                    "occurred_at": None,
                    "payload": event_payload,
                }
            ],
            snapshot=snapshot,
        )
        receipt = Receipt(
            status="accepted",
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=result["event_batch_id"],
            observed_stream_version=result["resulting_stream_versions"][command.target_stream_id],
            reason_code=None,
        )
        return self.receipts.write(receipt)

    def _prepare_genesis(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if projection["catalogue"] is not None:
            raise IntegrityError("W11 genesis already exists")
        if command.target_stream_id != "w11_catalogue" or command.expected_stream_version != 0:
            raise IntegrityError("W11 genesis stream identity mismatch")
        if command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        raw = self.catalogue_path.read_bytes()
        if (
            len(raw) != _ACCEPTED["catalogue_bytes"]
            or sha256_hex(raw) != _ACCEPTED["catalogue_sha256"]
            or _git_blob(raw) != _ACCEPTED["catalogue_blob"]
        ):
            raise IntegrityError("catalogue identity mismatch")
        repository_root = self.catalogue_path.resolve().parents[3]
        bootstrap = (
            repository_root / ".research-system" / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
        )
        bootstrap_raw = bootstrap.read_bytes()
        if (
            sha256_hex(bootstrap_raw) != _ACCEPTED["bootstrap_sha256"]
            or _git_blob(bootstrap_raw) != _ACCEPTED["bootstrap_blob"]
        ):
            raise IntegrityError("bootstrap identity mismatch")
        catalogue = json.loads(raw)
        row_ids = tuple(row.get("owner_row_id") for row in catalogue.get("owner_contract_rows", ()))
        if catalogue.get("owner_row_count") != 81 or row_ids != _ROW_IDS or len(set(row_ids)) != 81:
            raise IntegrityError("catalogue row set mismatch")
        return (
            "W11CatalogueGenesisImported",
            {
                "accepted_commit": _ACCEPTED["accepted_commit"],
                "accepted_tree": _ACCEPTED["accepted_tree"],
                "catalogue_blob": _ACCEPTED["catalogue_blob"],
                "catalogue_bytes": _ACCEPTED["catalogue_bytes"],
                "catalogue_sha256": _ACCEPTED["catalogue_sha256"],
                "bootstrap_blob": _ACCEPTED["bootstrap_blob"],
                "bootstrap_sha256": _ACCEPTED["bootstrap_sha256"],
                "review_commit": _ACCEPTED["review_commit"],
                "review_blob": _ACCEPTED["review_blob"],
                "review_sha256": _ACCEPTED["review_sha256"],
                "row_count": 81,
                "row_ids": list(_ROW_IDS),
            },
        )

    @staticmethod
    def _prepare_candidate(
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if projection["catalogue"] is None:
            raise IntegrityError("W11 genesis is required before Candidate registration")
        payload = command.envelope["payload"]
        required = {"candidate_id", "revision", "content_sha256", "source_observation_refs", "title"}
        if set(payload) != required or payload.get("candidate_id") != command.target_stream_id:
            raise IntegrityError("invalid Candidate registration")
        if payload.get("revision") != 1 or not isinstance(payload.get("title"), str) or not payload["title"]:
            raise IntegrityError("invalid Candidate registration")
        digest = payload.get("content_sha256")
        observations = payload.get("source_observation_refs")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not isinstance(observations, list)
            or not observations
            or not all(isinstance(item, str) and item for item in observations)
        ):
            raise IntegrityError("invalid Candidate registration")
        if command.target_stream_id in projection["candidates"]:
            raise IntegrityError("Candidate identity collision")
        return "CandidateRegistered", deepcopy(payload)
