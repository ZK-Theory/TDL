"""SOURCE documents and causal registration proofs, without workflow state."""

from __future__ import annotations

import base64
from copy import deepcopy
from collections.abc import Iterable
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from research_system.schema_registry import SchemaRegistry
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.spec_source_git import parse_locator, resolve_source
from research_system.errors import ConflictError, IntegrityError

DOCUMENT_KIND = "spec_source_document"
OBSERVATION_SCHEMA = "ars://portfolio/spec-source-observation"
CORRECTION_SCHEMA = "ars://portfolio/spec-01-source-correction"
SOURCE_REF_PREFIX = "ars:source-registration:"


def source_ids(project_id: str, intent: dict) -> dict[str, str]:
    """Derive previewable subjects from a semantic action key, independent of actor."""
    from research_system.methods.registration import _stable_command_id

    key = canonical_bytes(
        [project_id, intent["production"]["task_id"], intent["action"], intent["source_key"]]
    ).decode()
    return {
        name: prefix + _stable_command_id(key + name)[3:]
        for name, prefix in (("artefact_id", "art"), ("observation_id", "obj"), ("candidate_id", "obj"))
    }


_LEDGER_PRODUCTION_FIELDS = ("dispatch_id", "attempt_id", "context_packet_id", "code_commit", "environment_fingerprint")


def _lineage_candidate(project_id: str, intent: dict, objects) -> str:
    """The Candidate a SOURCE lineage derives: its observation's, followed back through corrections."""
    seen: set[str] = set()
    while intent["action"] == "correct_spec_01_source":
        artefact_id = intent["corrects_artefact_id"]
        if artefact_id in seen or not objects.revision_exists(DOCUMENT_KIND, artefact_id, 1):
            raise IntegrityError("SOURCE correction lineage has no registered observation")
        seen.add(artefact_id)
        intent = objects.read(DOCUMENT_KIND, artefact_id, 1)["intent"]
    return source_ids(project_id, intent)["candidate_id"]


def verify_source_production(
    intent: dict,
    events: Iterable[dict],
    *,
    project_id: str,
    registered_candidates: Iterable[str],
    objects,
    schemas,
    authority_state_validator,
) -> None:
    """Refuse SOURCE production references the ledger does not show (P-058, 2026-10-07, M-2 and P5-7).

    The SOURCE manifest copies ``production`` from the intent, and admission checks none of it, so the
    route checks it against the one Task it names and that Task's started Attempt, as it does for the
    operator records and the project-use decision. The Task is the SPEC-01 Task, started before
    ``observe_source``; it may name the Candidate this lineage derives, and no other registered one.
    Its Attempt must be running and dispatched on the Task's current revision, and the intent's
    dispatch, Attempt, context packet, code commit and environment fingerprint must be that Attempt's.
    The producer profile, branch, worktree and accepted scope have no ledger record and stay caller
    strings (a known limit).
    """
    from research_system.discovery.spec_replay import replay

    production = intent["production"]
    task_id = production["task_id"]
    events = tuple(events)
    streams = replay(events, schema_registry=schemas, authority_state_validator=authority_state_validator)["streams"]
    task = streams.get(task_id)
    if not isinstance(task, dict) or not str(task_id).startswith("tsk_"):
        raise IntegrityError(f"SOURCE production names Task {task_id}, which the ledger does not hold")
    # The Task may name only Candidates that SOURCE observations citing this same Task derive: this one,
    # and any earlier one (a revisit observation runs under the SPEC-01 Task too).
    allowed = {_lineage_candidate(project_id, intent, objects)}
    for event in events:
        manifest = (
            (event.get("payload") or {}).get("manifest") if event.get("event_type") == "ArtefactRegistered" else None
        )
        if (
            isinstance(manifest, dict)
            and manifest.get("task_id") == task_id
            and manifest.get("artefact_type") in {"spec_source_observation", "spec_01_source_correction"}
            and objects.revision_exists(DOCUMENT_KIND, event["stream_id"], 1)
        ):
            allowed.add(
                _lineage_candidate(project_id, objects.read(DOCUMENT_KIND, event["stream_id"], 1)["intent"], objects)
            )
    named = set((task.get("definition") or {}).get("portfolio_refs") or ())
    if named & (set(registered_candidates) - allowed):
        raise IntegrityError(f"SOURCE production Task {task_id} names a registered Candidate no SOURCE of it derives")
    attempts = [
        stream_id
        for stream_id, stream in streams.items()
        if str(stream_id).startswith("att_")
        and isinstance(stream, dict)
        and stream.get("task_id") == task_id
        and isinstance(stream.get("start"), dict)
    ]
    if len(attempts) != 1:
        raise IntegrityError(f"SOURCE production requires exactly one started Attempt of Task {task_id}")
    attempt = streams[attempts[0]]
    if attempt.get("task_revision") != task.get("current_revision"):
        raise IntegrityError(f"SOURCE production requires Task {task_id} unamended since its Attempt's dispatch")
    if attempt.get("status") != "running":
        raise IntegrityError(f"SOURCE production requires Attempt {attempts[0]} to be running")
    start = attempt["start"]
    ledger_production = {
        "dispatch_id": attempt.get("dispatch_id"),
        "attempt_id": attempts[0],
        "context_packet_id": start.get("context_packet_id"),
        "code_commit": start.get("code_identity"),
        "environment_fingerprint": start.get("environment_fingerprint"),
    }
    for field in _LEDGER_PRODUCTION_FIELDS:
        if production[field] != ledger_production[field]:
            raise IntegrityError(f"SOURCE production {field} differs from Task {task_id}'s running Attempt")


def registration_ref(event: dict) -> dict:
    return {
        "artefact_id": event["stream_id"],
        "content_sha256": event["payload"]["manifest"]["content_sha256"],
        **{key: event[key] for key in ("event_id", "event_hash", "global_position")},
    }


def registration_event(events, artefact_id: str) -> dict:
    matches = [
        event for event in events if event["event_type"] == "ArtefactRegistered" and event["stream_id"] == artefact_id
    ]
    if len(matches) != 1:
        raise IntegrityError("SOURCE requires exactly one prior artefact registration")
    return matches[0]


def source_ref(event: dict) -> dict:
    ref = registration_ref(event)
    return {
        "ref_kind": "external",
        "locator": SOURCE_REF_PREFIX + ref["artefact_id"] + ":" + ref["event_hash"],
        "content_hash": ref["content_sha256"],
    }


def validate_source_refs(
    batch: dict[str, Any],
    events: Iterable[dict[str, Any]],
    *,
    before_position: int,
    objects: ObjectStore | None = None,
    schemas: SchemaRegistry | None = None,
    ledger: EventLedger | None = None,
) -> None:
    """Bind SOURCE references to exact earlier registration events.

    Args:
        batch: Observation batch containing raw source references.
        events: Persisted registration and observation events.
        before_position: Exclusive upper bound for referenced registrations.
        objects: Immutable store for document validation, when available.
        schemas: Registry used with objects and ledger for document validation.
        ledger: Ledger used with objects and schemas for causal-prefix checks.

    Raises:
        IntegrityError: A SOURCE reference or its registered document is invalid.
    """
    events = tuple(events)
    for ref in batch.get("raw_source_refs", []):
        locator = ref.get("locator", "")
        if not locator.startswith(SOURCE_REF_PREFIX):
            continue
        identity, separator, event_hash = locator[len(SOURCE_REF_PREFIX) :].partition(":")
        event = registration_event(events, identity)
        if objects is not None and schemas is not None and ledger is not None:
            read_document(identity, objects=objects, schemas=schemas, ledger=ledger)
        if (
            not separator
            or source_ref(event) != ref
            or event["event_hash"] != event_hash
            or event["global_position"] >= before_position
            or event["payload"]["manifest"]["artefact_schema_id"] != OBSERVATION_SCHEMA
        ):
            raise IntegrityError("SOURCE observation does not bind its earlier exact registration")


def validate_document(document: dict, *, schemas, ledger, registration: dict | None = None) -> None:
    schemas.validate(document["schema_id"], document, schema_version=document["schema_version"])
    intent = document["intent"]
    resolution = document["resolution"]
    _, subpath = parse_locator(intent["requested_locator"])
    if (
        resolution["repository_url"] != intent["repository_url"]
        or resolution["requested_locator"] != intent["requested_locator"]
        or resolution.get("subpath") != subpath
        or ("subpath" in resolution) != (subpath is not None)
    ):
        raise IntegrityError("SOURCE locator and resolved provenance disagree")
    try:
        raw = base64.b64decode(document["source_bytes_base64"], validate=True)
    except ValueError as exc:
        raise IntegrityError("SOURCE bytes are not canonical base64") from exc
    if (
        base64.b64encode(raw).decode() != document["source_bytes_base64"]
        or len(raw) != document["source_size_bytes"]
        or sha256_hex(raw) != document["source_sha256"]
    ):
        raise IntegrityError("SOURCE bytes do not match their exact hash and size")
    prefix = document["causal_prefix"]
    position = prefix["global_position"]
    snapshot = ledger.snapshot()
    event_hash = snapshot.events[position - 1]["event_hash"] if 0 < position <= snapshot.global_position else "0" * 64
    if (
        position > snapshot.global_position
        or prefix["event_hash"] != event_hash
        or prefix["raw_prefix_sha256"] != ledger.raw_prefix_sha256(position)
    ):
        raise IntegrityError("SOURCE causal prefix does not match exact persisted ledger bytes")
    if registration is not None and position >= registration["global_position"]:
        raise IntegrityError("SOURCE document cannot reference its own or a later registration")
    correction = intent["action"] == "correct_spec_01_source"
    if document["schema_id"] != (CORRECTION_SCHEMA if correction else OBSERVATION_SCHEMA):
        raise IntegrityError("SOURCE action and document family disagree")
    if correction:
        prior = registration_event(snapshot.events, intent["corrects_artefact_id"])
        prior_manifest = prior["payload"]["manifest"]
        if (
            prior_manifest.get("artefact_schema_id") not in {OBSERVATION_SCHEMA, CORRECTION_SCHEMA}
            or prior_manifest.get("artefact_schema_version") not in {"1.0.0", "2.0.0"}
            or prior_manifest.get("artefact_type") not in {"spec_source_observation", "spec_01_source_correction"}
        ):
            raise IntegrityError("SOURCE correction target is not a SOURCE document family")
        if prior["global_position"] > position or registration_ref(prior) != document["prior_evidence"]:
            raise IntegrityError("SOURCE correction does not bind exact prior evidence")


def read_document(artefact_id: str, *, objects, schemas, ledger) -> tuple[dict, dict]:
    event = registration_event(ledger.snapshot().events, artefact_id)
    document = objects.read(DOCUMENT_KIND, artefact_id, 1)
    raw = canonical_bytes(document)
    manifest = event["payload"]["manifest"]
    relative = f"objects/{DOCUMENT_KIND}/{artefact_id}/00000001-{sha256_hex(raw)}.json"
    if (
        manifest["content_sha256"] != sha256_hex(raw)
        or manifest["size_bytes"] != len(raw)
        or manifest["relative_path"] != relative
        or manifest["root_id"] != "control"
        or manifest["artefact_schema_id"] != document["schema_id"]
        or manifest["artefact_schema_version"] != document["schema_version"]
        or manifest["producer_actor_id"] != document["producer_actor_id"]
        or event["actor_id"] != document["producer_actor_id"]
    ):
        raise IntegrityError("SOURCE registered manifest and immutable document disagree")
    validate_document(document, schemas=schemas, ledger=ledger, registration=event)
    return document, event


def prepare_document(intent: dict, artefact_id: str, *, actor_id: str, now: str, objects, schemas, ledger) -> dict:
    if objects.revision_exists(DOCUMENT_KIND, artefact_id, 1):
        document = objects.read(DOCUMENT_KIND, artefact_id, 1)
        if document["intent"] != intent or document["producer_actor_id"] != actor_id:
            raise ConflictError("SOURCE action key already binds different production intent")
        validate_document(document, schemas=schemas, ledger=ledger)
        return document
    snapshot = ledger.snapshot()
    prior = None
    if intent["action"] == "correct_spec_01_source":
        event = registration_event(snapshot.events, intent["corrects_artefact_id"])
        manifest = event["payload"]["manifest"]
        if (
            manifest.get("artefact_schema_id") not in {OBSERVATION_SCHEMA, CORRECTION_SCHEMA}
            or manifest.get("artefact_schema_version") not in {"1.0.0", "2.0.0"}
            or manifest.get("artefact_type") not in {"spec_source_observation", "spec_01_source_correction"}
        ):
            raise IntegrityError("SOURCE correction target is not a SOURCE document family")
        read_document(intent["corrects_artefact_id"], objects=objects, schemas=schemas, ledger=ledger)
        from pathlib import Path
        from research_system.discovery.spec_source_git import _physical_repository

        relative = Path(manifest["relative_path"])
        if manifest["root_id"] != "control" or relative.is_absolute() or ".." in relative.parts:
            raise IntegrityError("SOURCE correction prior bytes have an invalid control path")
        prior_path = _physical_repository(objects.control_root / relative)
        prior_raw = prior_path.read_bytes()
        if sha256_hex(prior_raw) != manifest["content_sha256"] or len(prior_raw) != manifest["size_bytes"]:
            raise IntegrityError("SOURCE correction prior bytes differ from their registration")
        prior = registration_ref(event)
    resolution, raw = resolve_source(intent["repository_url"], intent["requested_locator"])
    schemas.validate("ars://portfolio/git-reference-resolution", resolution)
    if raw is None:
        raise IntegrityError(f"SOURCE resolution is {resolution['status']}: {resolution}")
    correction = prior is not None
    document = {
        "schema_id": CORRECTION_SCHEMA if correction else OBSERVATION_SCHEMA,
        "schema_version": "2.0.0" if correction else "1.0.0",
        "document_type": "spec_01_source_correction" if correction else "spec_source_observation",
        "intent": deepcopy(intent),
        "recorded_at": now,
        "producer_actor_id": actor_id,
        "resolution": resolution,
        "source_bytes_base64": base64.b64encode(raw).decode(),
        "source_sha256": sha256_hex(raw),
        "source_size_bytes": len(raw),
        "causal_prefix": {
            "global_position": snapshot.global_position,
            "event_hash": snapshot.event_hash,
            "raw_prefix_sha256": ledger.raw_prefix_sha256(snapshot.global_position),
        },
    }
    if prior is not None:
        document["prior_evidence"] = prior
    validate_document(document, schemas=schemas, ledger=ledger)
    return document


def document_manifest(document: dict, artefact_id: str) -> dict:
    raw = canonical_bytes(document)
    production = deepcopy(document["intent"]["production"])
    scope = production.pop("accepted_scope")
    return {
        **production,
        "artefact_id": artefact_id,
        "aliases": [],
        "artefact_type": document["document_type"],
        "artefact_schema_id": document["schema_id"],
        "artefact_schema_version": document["schema_version"],
        "producer_actor_id": document["producer_actor_id"],
        "created_at": document["recorded_at"],
        "observed_at": document["recorded_at"],
        "root_id": "control",
        "relative_path": f"objects/{DOCUMENT_KIND}/{artefact_id}/00000001-{sha256_hex(raw)}.json",
        "size_bytes": len(raw),
        "media_type": "application/json",
        "content_sha256": sha256_hex(raw),
        "availability_check_evidence_refs": [],
        "input_dependencies": [],
        "research_provenance": {
            key: []
            for key in (
                "dataset_ids",
                "dataset_vintages",
                "representation_ids",
                "parameter_ids",
                "seed_ids",
                "sample_restriction_ids",
            )
        },
        "validation": {
            "validation_record_refs": [],
            "expected_contract_ids": [],
            "expected_schema_ids": [document["schema_id"]],
        },
        "authority": {
            "availability": "available",
            "regenerability": "non_regenerable",
            "integrity": "verified",
            "structural_validation": "passed",
            "scientific_review": "pending",
            "use_authority": "candidate",
            "accepted_scope": scope,
            "consumer_restrictions": [],
        },
        "operations": {
            "no_overwrite_evidence_refs": [],
            "retention_class": "durable",
            "confidentiality_class": "internal",
            "external_data_constraints": [],
        },
    }
