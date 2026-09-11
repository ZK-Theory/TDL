"""SOURCE documents and causal registration proofs, without workflow state."""

from __future__ import annotations

import base64
from copy import deepcopy

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


def validate_source_refs(batch: dict, events, *, before_position: int) -> None:
    """Bind each SOURCE multiset member to an exact earlier AR event."""
    events = tuple(events)
    for ref in batch.get("raw_source_refs", []):
        locator = ref.get("locator", "")
        if not locator.startswith(SOURCE_REF_PREFIX):
            continue
        identity, separator, event_hash = locator[len(SOURCE_REF_PREFIX) :].partition(":")
        event = registration_event(events, identity)
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
