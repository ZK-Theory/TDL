"""Discovery dossier replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.canonical import canonical_bytes
from research_system.canonical import sha256_hex
from research_system.discovery.dossier import canonical_dossier_hash
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.rules import _accepted_dossier_admission_matches
from research_system.errors import IntegrityError
from research_system.errors import SchemaError
from typing import Mapping


def reduce_research_dossier_admitted(scope: EventScope) -> None:
    """Reduce ResearchDossierAdmitted."""

    payload = scope.payload
    aggregate_identity_exists = scope.aggregate_identity_exists
    event = scope.event
    state = scope.state
    active_schemas = scope.active_schemas

    dossier_id = payload.get("dossier_id")
    candidate_manifest = payload.get("candidate_manifest")
    if not isinstance(dossier_id, str) or aggregate_identity_exists(dossier_id):
        raise IntegrityError("Research dossier identity collision")
    if not _accepted_dossier_admission_matches(
        state["authorities"].get("dossier_expected_set"),
        event,
        payload,
    ):
        raise IntegrityError("Research dossier admission authority mismatch")
    if not isinstance(candidate_manifest, Mapping):
        raise IntegrityError("Research dossier materialization manifest mismatch")
    try:
        active_schemas.validate(
            "ars://portfolio/research-dossier-manifest",
            candidate_manifest,
            schema_version="1.0.0",
        )
        manifest_sha256 = canonical_dossier_hash(dict(candidate_manifest))
    except (SchemaError, TypeError, ValueError) as exc:
        raise IntegrityError("Research dossier materialization manifest mismatch") from exc
    if manifest_sha256 != payload.get("candidate_manifest_hash"):
        raise IntegrityError("Research dossier materialization manifest mismatch")
    state["dossiers"][dossier_id] = {**deepcopy(payload), "status": "admitted"}


def reduce_portfolio_object_registered(scope: EventScope) -> None:
    """Reduce PortfolioObjectRegistered."""

    payload = scope.payload
    dossier_materialization_transaction_matches = scope.dossier_materialization_transaction_matches
    event = scope.event
    aggregate_identity_exists = scope.aggregate_identity_exists
    state = scope.state

    record_id = payload.get("record_id")
    blueprint = payload.get("blueprint")
    if not dossier_materialization_transaction_matches(event, payload):
        raise IntegrityError("Research dossier materialization admission transaction mismatch")
    if isinstance(blueprint, dict) and "proposed_edge_id" in blueprint:
        blueprint_preimage = {
            key: deepcopy(value) for key, value in blueprint.items() if key != "expected_content_hash"
        }
    elif isinstance(blueprint, dict):
        blueprint_preimage = {
            key: deepcopy(value)
            for key, value in blueprint.items()
            if key not in {"blueprint_hash", "expected_content_hash"}
        }
    else:
        blueprint_preimage = {}
    blueprint_hash = sha256_hex(canonical_bytes(blueprint_preimage))
    if (
        not isinstance(record_id, str)
        or aggregate_identity_exists(record_id)
        or not isinstance(blueprint, dict)
        or blueprint.get("proposed_record_id", blueprint.get("proposed_edge_id")) != record_id
        or payload.get("record_revision") != 1
        or payload.get("content_sha256") != blueprint_hash
        or blueprint.get("expected_content_hash") != blueprint_hash
        or ("proposed_record_id" in blueprint and blueprint.get("blueprint_hash") != blueprint_hash)
    ):
        raise IntegrityError("Portfolio object identity collision")
    state["portfolio_objects"][record_id] = deepcopy(payload)


def reduce_scope_definition_registered(scope: EventScope) -> None:
    """Reduce ScopeDefinitionRegistered."""

    payload = scope.payload
    dossier_materialization_transaction_matches = scope.dossier_materialization_transaction_matches
    event = scope.event
    aggregate_identity_exists = scope.aggregate_identity_exists
    state = scope.state

    scope_id = payload.get("scope_id")
    blueprint = payload.get("blueprint")
    if not dossier_materialization_transaction_matches(event, payload):
        raise IntegrityError("Research dossier materialization admission transaction mismatch")
    blueprint_preimage = (
        {
            key: deepcopy(value)
            for key, value in blueprint.items()
            if key not in {"blueprint_hash", "expected_content_hash"}
        }
        if isinstance(blueprint, dict)
        else {}
    )
    blueprint_hash = sha256_hex(canonical_bytes(blueprint_preimage))
    if (
        not isinstance(scope_id, str)
        or aggregate_identity_exists(scope_id)
        or not isinstance(blueprint, dict)
        or blueprint.get("proposed_scope_id") != scope_id
        or payload.get("scope_revision") != 1
        or payload.get("content_sha256") != blueprint_hash
        or blueprint.get("blueprint_hash") != blueprint_hash
        or blueprint.get("expected_content_hash") != blueprint_hash
    ):
        raise IntegrityError("Scope identity collision")
    state["scopes"][scope_id] = deepcopy(payload)
