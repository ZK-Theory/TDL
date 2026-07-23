"""Deterministically materialize the strict WP6.2 T2 leaf JSON Schemas."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

DRAFT = "https://json-schema.org/draft/2020-12/schema"
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
SEMVER = {"type": "string", "pattern": r"^[0-9]+\.[0-9]+\.[0-9]+$"}
UUID7 = r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"


def _string(*, pattern: str | None = None, min_length: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "string"}
    if pattern is not None:
        value["pattern"] = pattern
    if min_length is not None:
        value["minLength"] = min_length
    return value


def _id(prefix: str) -> dict[str, Any]:
    return _string(pattern=rf"^{prefix}_{UUID7}$")


def _canonical_id() -> dict[str, Any]:
    return _string(pattern=rf"^[a-z][a-z0-9]*_{UUID7}$")


def _closed(properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required if required is not None else list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def _reserved_cost_mode_constraint() -> dict[str, Any]:
    return {
        "allOf": [
            {
                "if": {
                    "properties": {"rate_mode": {"const": "metered"}},
                    "required": ["rate_mode"],
                },
                "then": {
                    "properties": {
                        "reserved_cost_microunits": {"minimum": 1},
                    }
                },
                "else": {
                    "properties": {
                        "reserved_cost_microunits": {"const": 0},
                    }
                },
            }
        ]
    }


def _ordered_constants(values: list[str]) -> dict[str, Any]:
    return {
        "type": "array",
        "prefixItems": [{"const": value} for value in values],
        "items": False,
        "minItems": len(values),
        "maxItems": len(values),
    }


def _content_ref() -> dict[str, Any]:
    return _closed(
        {
            "subject_id": _canonical_id(),
            "subject_revision": {"type": "integer", "minimum": 1},
            "subject_hash": dict(HASH),
        }
    )


def _scope() -> dict[str, Any]:
    return _closed(
        {
            "task_id": _id("tsk"),
            "dispatch_id": _id("dsp"),
            "attempt_id": _id("att"),
            "route_id": _id("rte"),
            "profile_id": _id("prf"),
            "adapter_revision": _string(min_length=1),
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
        }
    )


def _revocation_binding() -> dict[str, Any]:
    return _closed(
        {
            "authority_grant_id": _id("agr"),
            "resource_grant_id": _id("rgr"),
            "new_issue_rule": {"const": "require_both_current_projections_active"},
            "reconciliation_rule": {"const": "reconcile_every_previously_accepted_reservation"},
        }
    )


def _secret_reference_schema() -> dict[str, Any]:
    return {
        "$schema": DRAFT,
        "$id": "ars://wp6-2/t2/secret-reference",
        "title": "WP6.2 T2 SecretReference",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "secret_reference_id",
            "revision",
            "content_hash",
            "provider",
            "credential_class",
            "resolver_id",
            "resolver_version",
            "allowed_scope",
            "expires_at",
            "revocation_binding",
            "redaction_proof",
        ],
        "properties": {
            "schema_id": {"const": "ars://wp6-2/t2/secret-reference"},
            "schema_version": {"const": "1.0.0"},
            "secret_reference_id": _id("srf"),
            "revision": {"const": 1},
            "content_hash": dict(HASH),
            "provider": {"enum": ["claude", "codex"]},
            "credential_class": {"enum": ["api_token", "oauth_session", "local_provider_session"]},
            "resolver_id": _closed(
                {
                    "registry_type": {"const": "secret_resolver"},
                    "canonical_uri": _string(pattern=r"^ars://registry/secret-resolver/[a-z0-9][a-z0-9._/-]*$"),
                    "revision": {"type": "integer", "minimum": 1},
                    "content_hash": dict(HASH),
                }
            ),
            "resolver_version": dict(SEMVER),
            "allowed_scope": _scope(),
            "expires_at": {"type": "string", "format": "date-time"},
            "revocation_binding": _revocation_binding(),
            "redaction_proof": _closed(
                {
                    "policy_id": {"const": "wp6-2-t2-opaque-secret-reference-policy"},
                    "policy_version": {"const": "1.0.0"},
                    "evidence_sha256": dict(HASH),
                    "status": {"const": "opaque_metadata_only_no_raw_credential_or_resolution"},
                }
            ),
        },
        "additionalProperties": False,
    }


def _receipt_v2_schema() -> dict[str, Any]:
    event = _closed(
        {
            "event_id": _id("evt"),
            "event_type": {
                "enum": [
                    "CostGrantIssued",
                    "CostGrantReserved",
                    "ProviderCommandIssued",
                    "ProviderReceiptRecorded",
                    "CostGrantReconciled",
                ]
            },
            "transaction_position": {"type": "integer", "minimum": 0},
            "stream_id": {
                "oneOf": [_id("cgr"), _id("pcmd")],
            },
            "prior_stream_version": {"type": "integer", "minimum": 0},
            "resulting_stream_version": {"type": "integer", "minimum": 1},
        }
    )
    properties = {
        "schema_id": {"const": "ars://core/receipt/v2"},
        "schema_version": {"const": "2.0.0"},
        "receipt_id": _id("rcp"),
        "outcome": {"enum": ["accepted", "duplicate", "rejected", "conflict"]},
        "command_type": {
            "enum": ["IssueCostGrant", "AuthorizeProviderIssue", "RecordProviderReceipt"],
        },
        "command_id": _id("cmd"),
        "idempotency_key_hash": dict(HASH),
        "payload_hash": dict(HASH),
        "event_batch_id": {"oneOf": [_id("txb"), {"type": "null"}]},
        "events": {"type": "array", "items": event},
        "stable_reason": {"type": ["string", "null"]},
        "unmet_preconditions": {
            "type": "array",
            "items": _string(min_length=1),
            "uniqueItems": True,
        },
        "original_accepted_receipt_hash": {"oneOf": [dict(HASH), {"type": "null"}]},
        "outcome_binding_hash": dict(HASH),
        "new_event_count": {"type": "integer", "minimum": 0},
        "new_invocation_count": {"type": "integer", "minimum": 0},
    }
    required = list(properties)
    accepted = {
        "properties": {
            "outcome": {"const": "accepted"},
            "event_batch_id": _id("txb"),
            "events": {"minItems": 1},
            "stable_reason": {"type": "null"},
            "unmet_preconditions": {"maxItems": 0},
            "original_accepted_receipt_hash": {"type": "null"},
            "new_event_count": {"minimum": 1},
            "new_invocation_count": {"const": 0},
        }
    }
    duplicate = {
        "properties": {
            "outcome": {"const": "duplicate"},
            "event_batch_id": _id("txb"),
            "events": {"minItems": 1},
            "stable_reason": {"type": "null"},
            "unmet_preconditions": {"maxItems": 0},
            "original_accepted_receipt_hash": dict(HASH),
            "new_event_count": {"const": 0},
            "new_invocation_count": {"const": 0},
        }
    }
    rejected = {
        "properties": {
            "outcome": {"enum": ["rejected", "conflict"]},
            "event_batch_id": {"type": "null"},
            "events": {"maxItems": 0},
            "stable_reason": _string(min_length=1),
            "unmet_preconditions": {"minItems": 1},
            "original_accepted_receipt_hash": {"type": "null"},
            "new_event_count": {"const": 0},
            "new_invocation_count": {"const": 0},
        }
    }
    return {
        "$schema": DRAFT,
        "$id": "ars://core/receipt/v2",
        "title": "ARS Receipt 2.0 exact T2 proof surface",
        "type": "object",
        "required": required,
        "properties": properties,
        "oneOf": [accepted, duplicate, rejected],
        "additionalProperties": False,
        "x-successor-of": {"schema_id": "ars://core/receipt", "schema_version": "1.0.0"},
        "x-major-version-dispatch": "exact_major_version_required",
        "x-duplicate-proof": "outcome_binding_hash_and_ordered_events_equal_original_accepted_receipt",
    }


def _token_amounts(*, minimum: int = 0) -> dict[str, Any]:
    return _closed(
        {
            "input_tokens": {"type": "integer", "minimum": minimum},
            "output_tokens": {"type": "integer", "minimum": minimum},
            "total_tokens": {"type": "integer", "minimum": minimum},
        }
    )


def _rate_evidence() -> dict[str, Any]:
    common = {
        "currency": _string(pattern="^[A-Z]{3}$"),
        "rate_evidence_id": _canonical_id(),
        "rate_evidence_revision": {"type": "integer", "minimum": 1},
        "rate_evidence_hash": dict(HASH),
        "effective_at": {"type": "string", "format": "date-time"},
        "expires_at": {"type": "string", "format": "date-time"},
    }
    metered = _closed(
        {
            **common,
            "mode": {"const": "metered"},
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 1},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 1},
            "zero_cost_authority": {"type": "null"},
        }
    )
    zero = _closed(
        {
            **common,
            "mode": {"const": "zero_cost_authorized"},
            "input_microunits_per_million_tokens": {"const": 0},
            "output_microunits_per_million_tokens": {"const": 0},
            "zero_cost_authority": _content_ref(),
        }
    )
    return {"oneOf": [metered, zero]}


def _cost_grant_schema() -> dict[str, Any]:
    return {
        "$schema": DRAFT,
        "$id": "ars://wp6-2/t2/cost-grant",
        "title": "WP6.2 T2 CostGrant",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "cost_grant_id",
            "revision",
            "content_hash",
            "resource_grant_id",
            "resource_grant_revision",
            "resource_grant_hash",
            "authority_grant_id",
            "scope",
            "secret_reference_id",
            "secret_reference_revision",
            "secret_reference_hash",
            "provider_command_schema_id",
            "provider_command_schema_version",
            "token_ceilings",
            "cost_ceiling_microunits",
            "rate_evidence",
            "initial_accounting",
            "expires_at",
            "idempotency_identity",
            "revocation_binding",
        ],
        "properties": {
            "schema_id": {"const": "ars://wp6-2/t2/cost-grant"},
            "schema_version": {"const": "1.0.0"},
            "cost_grant_id": _id("cgr"),
            "revision": {"const": 1},
            "content_hash": dict(HASH),
            "resource_grant_id": _id("rgr"),
            "resource_grant_revision": {"type": "integer", "minimum": 1},
            "resource_grant_hash": dict(HASH),
            "authority_grant_id": _id("agr"),
            "scope": _scope(),
            "secret_reference_id": _id("srf"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "provider_command_schema_id": {"const": "ars://adapters/provider-command/v2"},
            "provider_command_schema_version": {"const": "2.0.0"},
            "token_ceilings": _token_amounts(minimum=0),
            "cost_ceiling_microunits": {"type": "integer", "minimum": 1},
            "rate_evidence": _rate_evidence(),
            "initial_accounting": _closed(
                {
                    "reserved_microunits": {"const": 0},
                    "consumed_microunits": {"const": 0},
                    "refunded_microunits": {"const": 0},
                }
            ),
            "expires_at": {"type": "string", "format": "date-time"},
            "idempotency_identity": _closed(
                {
                    "actor_id": _id("act"),
                    "authority_scope": {"const": "wp6.2.t2.cost-grant.issue"},
                    "command_type": {"const": "IssueCostGrant"},
                    "idempotency_key": _string(min_length=1),
                }
            ),
            "revocation_binding": _revocation_binding(),
        },
        "additionalProperties": False,
        "x-cost-formula": (
            "ceil_div(actual_input_tokens*input_microunits_per_million_tokens,1000000)"
            "+ceil_div(actual_output_tokens*output_microunits_per_million_tokens,1000000)"
        ),
    }


def _triple(id_schema: dict[str, Any]) -> dict[str, Any]:
    return _closed(
        {
            "id": id_schema,
            "revision": {"type": "integer", "minimum": 1},
            "content_hash": dict(HASH),
        }
    )


def _authority_binding(*, include_receipt: bool) -> dict[str, Any]:
    properties = {
        "task": _triple(_id("tsk")),
        "dispatch": _triple(_id("dsp")),
        "attempt": _triple(_id("att")),
        "resource_grant": _triple(_id("rgr")),
        "cost_grant": _triple(_id("cgr")),
        "reservation": _triple(_id("crs")),
        "secret_reference": _triple(_id("srf")),
    }
    if include_receipt:
        properties["provider_receipt"] = _triple(_id("prcp"))
    return _closed(properties)


def _provider_binding() -> dict[str, Any]:
    return _closed(
        {
            "provider": {"enum": ["claude", "codex"]},
            "provider_identity": _triple(_canonical_id()),
            "model": _triple(_canonical_id()),
            "profile": _triple(_id("prf")),
            "adapter": _triple(_id("adp")),
            "policy": _triple(_id("pol")),
        }
    )


def _provider_command_v2_subset_schema() -> dict[str, Any]:
    properties = {
        "schema_id": {"const": "ars://adapters/provider-command/v2"},
        "schema_version": {"const": "2.0.0"},
        "provider_command_id": _id("pcmd"),
        "revision": {"type": "integer", "minimum": 1},
        "revision_hash": dict(HASH),
        "provider_binding": _provider_binding(),
        "w2_binding": _closed(
            {
                "command": _triple(_id("cmd")),
                "expected_control_store_position": {"type": "integer", "minimum": 0},
                "idempotency_key": _string(min_length=1),
                "idempotency_key_hash": dict(HASH),
                "payload_hash": dict(HASH),
            }
        ),
        "authority_binding": _authority_binding(include_receipt=False),
        "payload_binding": _closed(
            {
                "rendered_payload_hash": dict(HASH),
                "context_hash": dict(HASH),
            }
        ),
        "permission_binding": _closed(
            {
                "summary": {"type": "array", "items": _string(min_length=1), "uniqueItems": True},
                "effective_permissions_hash": dict(HASH),
            }
        ),
        "accounting_ceiling": _closed(
            {
                "token_ceilings": _token_amounts(minimum=0),
                "cost_ceiling_microunits": {"type": "integer", "minimum": 1},
                "currency": _string(pattern="^[A-Z]{3}$"),
                "rate_evidence_id": _canonical_id(),
                "rate_evidence_revision": {"type": "integer", "minimum": 1},
                "rate_evidence_hash": dict(HASH),
            }
        ),
        "lifecycle": _closed(
            {
                "issued_at": {"type": "string", "format": "date-time"},
                "expires_at": {"type": "string", "format": "date-time"},
                "retry": {"enum": ["never", "only_with_proven_provider_idempotency"]},
                "reconciliation": {"const": "receipt_or_safe_idempotent_retry_required"},
            }
        ),
    }
    return {
        "$schema": DRAFT,
        "$id": "ars://adapters/provider-command/v2",
        "title": "WP6.2 T2 authority and cost subset ProviderCommand successor",
        "x-t2-validation-scope": "t2_authority_cost_subset",
        "x-deferred-qualification": "remaining_W7_sections_9_and_10_require_T3_T4_runtime_evidence",
        "x-successor-of": {"schema_id": "ars://adapters/provider-command", "schema_version": "1.0.0"},
        "x-reader-compatibility": {
            "v2_reader": "may_read_v1_for_audit_only",
            "v1_reader": "must_reject_v2",
            "t2_issue": "requires_v2",
        },
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def _provider_receipt_v2_subset_schema() -> dict[str, Any]:
    properties = {
        "schema_id": {"const": "ars://adapters/provider-receipt/v2"},
        "schema_version": {"const": "2.0.0"},
        "provider_receipt_id": _id("prcp"),
        "revision": {"type": "integer", "minimum": 1},
        "revision_hash": dict(HASH),
        "command_binding": _closed(
            {
                "provider_command": _triple(_id("pcmd")),
                "w2_command": _triple(_id("cmd")),
                "idempotency_key_hash": dict(HASH),
                "payload_hash": dict(HASH),
            }
        ),
        "provider_binding": _provider_binding(),
        "authority_binding": _authority_binding(include_receipt=True),
        "delivery_binding": {
            "oneOf": [
                _closed(
                    {
                        "disposition": {"const": "proven"},
                        "rendered_payload_hash": dict(HASH),
                        "delivered_context_hash": dict(HASH),
                    }
                ),
                _closed(
                    {
                        "disposition": {"const": "unable_to_prove"},
                        "evidence": _content_ref(),
                    }
                ),
            ]
        },
        "timestamps": _closed(
            {
                "issued_at": {"type": "string", "format": "date-time"},
                "terminal_at": {"type": "string", "format": "date-time"},
            }
        ),
        "token_accounting": _closed(
            {
                "actual_input_tokens": {"type": "integer", "minimum": 0},
                "actual_output_tokens": {"type": "integer", "minimum": 0},
                "actual_total_tokens": {"type": "integer", "minimum": 0},
                "accounting_method": _string(min_length=1),
                "reserved_cost_microunits": {"type": "integer", "minimum": 0},
                "consumed_cost_microunits": {"type": "integer", "minimum": 0},
                "refund_cost_microunits": {"type": "integer", "minimum": 0},
                "currency": _string(pattern="^[A-Z]{3}$"),
                "rate_evidence_id": _canonical_id(),
                "rate_evidence_revision": {"type": "integer", "minimum": 1},
                "rate_evidence_hash": dict(HASH),
            }
        ),
        "terminal_outcome": _closed(
            {
                "status": {"enum": ["terminal", "duplicate", "timed_out", "uncertain", "blocked"]},
                "normalized_error": {"type": ["string", "null"]},
            }
        ),
        "outputs": _closed(
            {
                "references": {"type": "array", "items": _content_ref()},
                "aggregate_hash": dict(HASH),
            }
        ),
        "lifecycle_evidence": _closed(
            {
                "retry_count": {"type": "integer", "minimum": 0},
                "duplicate_of_receipt": {"oneOf": [_triple(_id("prcp")), {"type": "null"}]},
                "reconciliation": _content_ref(),
            }
        ),
        "evidence_disposition": _closed(
            {
                "redaction": {"const": "secret_and_restricted_material_removed"},
                "omission_declarations": {"type": "array", "items": _string(min_length=1), "uniqueItems": True},
            }
        ),
        "completeness": _closed(
            {
                "complete": {"type": "boolean"},
                "reconciliation_gate_satisfied": {"type": "boolean"},
                "diagnostic_only": {"type": "boolean"},
            }
        ),
    }
    complete = {
        "if": {"properties": {"completeness": {"properties": {"complete": {"const": True}}}}},
        "then": {
            "properties": {
                "delivery_binding": {"properties": {"disposition": {"const": "proven"}}},
                "completeness": {
                    "properties": {
                        "reconciliation_gate_satisfied": {"const": True},
                        "diagnostic_only": {"const": False},
                    }
                },
            }
        },
        "else": {
            "properties": {
                "completeness": {
                    "properties": {
                        "reconciliation_gate_satisfied": {"const": False},
                        "diagnostic_only": {"const": True},
                    }
                }
            }
        },
    }
    return {
        "$schema": DRAFT,
        "$id": "ars://adapters/provider-receipt/v2",
        "title": "WP6.2 T2 authority and cost subset ProviderReceipt successor",
        "x-t2-validation-scope": "t2_authority_cost_subset",
        "x-deferred-qualification": "remaining_W7_sections_9_and_10_require_T3_T4_runtime_evidence",
        "x-successor-of": {"schema_id": "ars://adapters/provider-receipt", "schema_version": "1.0.0"},
        "x-reader-compatibility": {
            "v2_reader": "may_read_v1_for_audit_only",
            "v1_reader": "must_reject_v2",
            "t2_reconciliation": "requires_v2",
        },
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "allOf": [complete],
        "additionalProperties": False,
    }


def _write_set(roles: list[str]) -> dict[str, Any]:
    prefix_items = []
    patterns = {"cost_grant": rf"^cgr_{UUID7}$", "provider_command": rf"^pcmd_{UUID7}$"}
    for role in roles:
        prefix_items.append(
            _closed(
                {
                    "stream_role": {"const": role},
                    "stream_id": _string(pattern=patterns[role]),
                    "expected_stream_version": {"type": "integer", "minimum": 0},
                }
            )
        )
    return {
        "type": "array",
        "prefixItems": prefix_items,
        "items": False,
        "minItems": len(roles),
        "maxItems": len(roles),
    }


def _command_schema(
    command_type: str,
    slug: str,
    authority_scope: str,
    target_pattern: str,
    write_roles: list[str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    schema_id = f"ars://wp6-2/t2/command/{command_type}"
    return {
        "$schema": DRAFT,
        "$id": schema_id,
        "title": f"WP6.2 T2 {command_type}",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "command_id",
            "command_type",
            "submitted_at",
            "actor_id",
            "on_behalf_of_actor_id",
            "authority_grant_id",
            "authority_scope",
            "target_stream_id",
            "write_set",
            "idempotency_key",
            "payload_hash",
            "correlation_id",
            "causation_id",
            "reason",
            "evidence_refs",
            "payload",
        ],
        "properties": {
            "schema_id": {"const": schema_id},
            "schema_version": {"const": "1.0.0"},
            "command_id": _id("cmd"),
            "command_type": {"const": command_type},
            "submitted_at": {"type": "string", "format": "date-time"},
            "actor_id": _id("act"),
            "on_behalf_of_actor_id": {"type": ["string", "null"], "pattern": rf"^act_{UUID7}$"},
            "authority_grant_id": _id("agr"),
            "authority_scope": {"const": authority_scope},
            "target_stream_id": _string(pattern=target_pattern),
            "write_set": _write_set(write_roles),
            "idempotency_key": _string(min_length=1),
            "payload_hash": dict(HASH),
            "correlation_id": _string(min_length=1),
            "causation_id": {"type": ["string", "null"]},
            "reason": _string(min_length=1),
            "evidence_refs": {"type": "array", "items": _content_ref(), "minItems": 1, "uniqueItems": True},
            "payload": payload,
        },
        "additionalProperties": False,
        "x-materialized-filename": f"{slug}.schema.json",
        "x-semantic-validation": [
            "target_write_set_payload_identity",
            "issue_expected_version_zero",
            "deterministic_reservation_identity",
            "authority_subject_identity_revision_hash",
            "receipt_grant_and_reservation_identity_revision_hash",
            "ordered_events_and_resulting_versions",
        ],
    }


def _issue_payload() -> dict[str, Any]:
    return _closed(
        {
            "cost_grant_id": _id("cgr"),
            "cost_grant_revision": {"const": 1},
            "cost_grant_hash": dict(HASH),
            "resource_grant_id": _id("rgr"),
            "resource_grant_revision": {"type": "integer", "minimum": 1},
            "resource_grant_hash": dict(HASH),
            "task_id": _id("tsk"),
            "task_revision": {"type": "integer", "minimum": 1},
            "task_hash": dict(HASH),
            "dispatch_id": _id("dsp"),
            "dispatch_revision": {"type": "integer", "minimum": 1},
            "dispatch_hash": dict(HASH),
            "attempt_id": _id("att"),
            "attempt_revision": {"type": "integer", "minimum": 1},
            "attempt_hash": dict(HASH),
            "route_id": _id("rte"),
            "profile_id": _id("prf"),
            "adapter_revision": _string(min_length=1),
            "secret_reference_id": _id("srf"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "token_ceilings": _token_amounts(minimum=0),
            "cost_ceiling_microunits": {"type": "integer", "minimum": 1},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
            "rate_evidence_hash": dict(HASH),
            "expires_at": {"type": "string", "format": "date-time"},
        }
    )


def _authorize_payload() -> dict[str, Any]:
    payload = _closed(
        {
            "cost_grant_id": _id("cgr"),
            "cost_grant_revision": {"type": "integer", "minimum": 1},
            "cost_grant_hash": dict(HASH),
            "resource_grant_id": _id("rgr"),
            "resource_grant_revision": {"type": "integer", "minimum": 1},
            "resource_grant_hash": dict(HASH),
            "task_id": _id("tsk"),
            "task_revision": {"type": "integer", "minimum": 1},
            "task_hash": dict(HASH),
            "dispatch_id": _id("dsp"),
            "dispatch_revision": {"type": "integer", "minimum": 1},
            "dispatch_hash": dict(HASH),
            "attempt_id": _id("att"),
            "attempt_revision": {"type": "integer", "minimum": 1},
            "attempt_hash": dict(HASH),
            "reservation_id": _id("crs"),
            "reservation_revision": {"type": "integer", "minimum": 1},
            "reservation_hash": dict(HASH),
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "secret_reference_id": _id("srf"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "requested_tokens": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 0},
            "expected_available_microunits": {"type": "integer", "minimum": 1},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
            "rate_evidence_hash": dict(HASH),
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "rate_mode": {"enum": ["metered", "zero_cost_authorized"]},
            "zero_cost_authority": {"oneOf": [_content_ref(), {"type": "null"}]},
            "rendered_payload_hash": dict(HASH),
        }
    )
    payload.update(_reserved_cost_mode_constraint())
    return payload


def _receipt_payload() -> dict[str, Any]:
    return _closed(
        {
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "resource_grant_id": _id("rgr"),
            "resource_grant_revision": {"type": "integer", "minimum": 1},
            "resource_grant_hash": dict(HASH),
            "task_id": _id("tsk"),
            "task_revision": {"type": "integer", "minimum": 1},
            "task_hash": dict(HASH),
            "dispatch_id": _id("dsp"),
            "dispatch_revision": {"type": "integer", "minimum": 1},
            "dispatch_hash": dict(HASH),
            "attempt_id": _id("att"),
            "attempt_revision": {"type": "integer", "minimum": 1},
            "attempt_hash": dict(HASH),
            "secret_reference_id": _id("srf"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "provider_receipt_id": _id("prcp"),
            "provider_receipt_revision": {"type": "integer", "minimum": 1},
            "provider_receipt_hash": dict(HASH),
            "provider_receipt_schema_id": {"const": "ars://adapters/provider-receipt/v2"},
            "provider_receipt_schema_version": {"const": "2.0.0"},
            "cost_grant_id": _id("cgr"),
            "cost_grant_revision": {"type": "integer", "minimum": 1},
            "cost_grant_hash": dict(HASH),
            "reservation_id": _id("crs"),
            "reservation_revision": {"type": "integer", "minimum": 1},
            "reservation_hash": dict(HASH),
            "actual_tokens": _token_amounts(minimum=0),
            "reserved_token_ceilings": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 0},
            "consumed_cost_microunits": {"type": "integer", "minimum": 0},
            "refund_cost_microunits": {"type": "integer", "minimum": 0},
            "refund_disposition": {"enum": ["fully_consumed", "refunded"]},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
            "rate_evidence_hash": dict(HASH),
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "rate_mode": {"enum": ["metered", "zero_cost_authorized"]},
            "zero_cost_authority": {"oneOf": [_content_ref(), {"type": "null"}]},
            "provider_terminal_status": {"enum": ["terminal", "duplicate", "cancelled"]},
            "receipt_complete": {"const": True},
        }
    )


def _event_schema(
    event_type: str,
    transaction_index: int,
    transaction_count: int,
    stream_pattern: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    schema_id = f"ars://wp6-2/t2/event/{event_type}"
    command_type = {
        "CostGrantIssued": "IssueCostGrant",
        "CostGrantReserved": "AuthorizeProviderIssue",
        "ProviderCommandIssued": "AuthorizeProviderIssue",
        "ProviderReceiptRecorded": "RecordProviderReceipt",
        "CostGrantReconciled": "RecordProviderReceipt",
    }[event_type]
    authority_scope = {
        "IssueCostGrant": "wp6.2.t2.cost-grant.issue",
        "AuthorizeProviderIssue": "wp6.2.t2.provider.issue",
        "RecordProviderReceipt": "wp6.2.t2.provider.receipt.record",
    }[command_type]
    return {
        "$schema": DRAFT,
        "$id": schema_id,
        "title": f"WP6.2 T2 {event_type}",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "event_id",
            "event_type",
            "project_id",
            "stream_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "command_id",
            "authority_scope",
            "command_type",
            "idempotency_key",
            "idempotency_key_hash",
            "payload_hash",
            "correlation_id",
            "causation_id",
            "actor_id",
            "authority_grant_id",
            "recorded_at",
            "payload",
            "previous_event_hash",
            "event_hash",
        ],
        "properties": {
            "schema_id": {"const": schema_id},
            "schema_version": {"const": "1.0.0"},
            "event_id": _id("evt"),
            "event_type": {"const": event_type},
            "project_id": _id("prj"),
            "stream_id": _string(pattern=stream_pattern),
            "stream_version": {"type": "integer", "minimum": 1},
            "global_position": {"type": "integer", "minimum": 0},
            "transaction_id": _id("txb"),
            "transaction_index": {"const": transaction_index},
            "transaction_count": {"const": transaction_count},
            "command_id": _id("cmd"),
            "authority_scope": {"const": authority_scope},
            "command_type": {"const": command_type},
            "idempotency_key": _string(min_length=1),
            "idempotency_key_hash": dict(HASH),
            "payload_hash": dict(HASH),
            "correlation_id": _string(min_length=1),
            "causation_id": _string(min_length=1),
            "actor_id": _id("act"),
            "authority_grant_id": _id("agr"),
            "recorded_at": {"type": "string", "format": "date-time"},
            "payload": payload,
            "previous_event_hash": dict(HASH),
            "event_hash": dict(HASH),
        },
        "additionalProperties": False,
    }


def _event_payloads() -> dict[str, dict[str, Any]]:
    issued = _issue_payload()
    issued["properties"]["grant_status"] = {"const": "active"}
    issued["properties"]["available_cost_microunits"] = {"type": "integer", "minimum": 1}
    issued["required"].extend(["grant_status", "available_cost_microunits"])
    reserved = _closed(
        {
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crs"),
            "provider_command_id": _id("pcmd"),
            "reserved_tokens": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 0},
            "remaining_cost_microunits": {"type": "integer", "minimum": 0},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
            "rate_evidence_hash": dict(HASH),
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "rate_mode": {"enum": ["metered", "zero_cost_authorized"]},
            "zero_cost_authority": {"oneOf": [_content_ref(), {"type": "null"}]},
        }
    )
    reserved.update(_reserved_cost_mode_constraint())
    command_issued = _closed(
        {
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crs"),
            "secret_reference_id": _id("srf"),
            "rendered_payload_hash": dict(HASH),
            "transport_invocation_authorized": {"const": True},
        }
    )
    receipt_recorded = _closed(
        {
            "provider_command_id": _id("pcmd"),
            "provider_receipt_id": _id("prcp"),
            "provider_receipt_revision": {"type": "integer", "minimum": 1},
            "provider_receipt_hash": dict(HASH),
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crs"),
            "provider_terminal_status": {"enum": ["terminal", "duplicate", "cancelled"]},
            "receipt_complete": {"const": True},
        }
    )
    reconciled = _closed(
        {
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crs"),
            "provider_command_id": _id("pcmd"),
            "provider_receipt_id": _id("prcp"),
            "actual_input_tokens": {"type": "integer", "minimum": 0},
            "actual_output_tokens": {"type": "integer", "minimum": 0},
            "actual_total_tokens": {"type": "integer", "minimum": 0},
            "reserved_input_tokens": {"type": "integer", "minimum": 0},
            "reserved_output_tokens": {"type": "integer", "minimum": 0},
            "reserved_total_tokens": {"type": "integer", "minimum": 0},
            "reserved_cost_microunits": {"type": "integer", "minimum": 0},
            "consumed_cost_microunits": {"type": "integer", "minimum": 0},
            "refund_cost_microunits": {"type": "integer", "minimum": 0},
            "refund_disposition": {"enum": ["fully_consumed", "refunded"]},
            "remaining_cost_microunits": {"type": "integer", "minimum": 0},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
            "rate_evidence_hash": dict(HASH),
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "rate_mode": {"enum": ["metered", "zero_cost_authorized"]},
            "zero_cost_authority": {"oneOf": [_content_ref(), {"type": "null"}]},
        }
    )
    return {
        "CostGrantIssued": issued,
        "CostGrantReserved": reserved,
        "ProviderCommandIssued": command_issued,
        "ProviderReceiptRecorded": receipt_recorded,
        "CostGrantReconciled": reconciled,
    }


def _normative_crosswalk_schema() -> dict[str, Any]:
    string_list = {
        "type": "array",
        "items": _string(min_length=1),
        "minItems": 1,
        "uniqueItems": True,
    }
    row = _closed(
        {
            "finding_id": {"enum": ["C1", "C2", "C3", "C4", "M1", "M2", "M3", "I1"]},
            "authority_refs": dict(string_list),
            "schema_properties": dict(string_list),
            "semantic_validators": dict(string_list),
            "positive_tests": dict(string_list),
            "negative_tests": dict(string_list),
        }
    )
    return {
        "$schema": DRAFT,
        "$id": "ars://contracts/wp6-2-t2-normative-crosswalk",
        "title": "WP6.2 T2 normative crosswalk",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "crosswalk_id",
            "status",
            "authorities",
            "oracle_source",
            "rows",
        ],
        "properties": {
            "schema_id": {"const": "ars://contracts/wp6-2-t2-normative-crosswalk"},
            "schema_version": {"const": "1.0.0"},
            "crosswalk_id": {"const": "wp6-2-t2-r3-normative-crosswalk"},
            "status": {"const": "proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance"},
            "authorities": {
                "type": "array",
                "items": {"enum": ["W2", "W7", "W8", "06b", "P-037", "P-038", "P-039", "R2"]},
                "minItems": 8,
                "maxItems": 8,
                "uniqueItems": True,
            },
            "oracle_source": {"const": "tests/research_system/contracts/wp6_2_t2_expectations.py#EXPECTED_CROSSWALK"},
            "rows": {
                "type": "array",
                "items": row,
                "minItems": 8,
                "maxItems": 8,
            },
        },
        "additionalProperties": False,
    }


def _protected_membership_schema() -> dict[str, Any]:
    member = _closed(
        {
            "repository_path": _string(min_length=1),
            "git_blob_id": _string(pattern="^[0-9a-f]{40}$"),
            "raw_git_blob_sha256": dict(HASH),
        }
    )
    return {
        "$schema": DRAFT,
        "$id": "ars://contracts/wp6-2-t2-protected-membership",
        "title": "WP6.2 T2 exact protected predecessor membership",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "contract_id",
            "status",
            "baseline_revision",
            "derivation",
            "protected_path_count",
            "aggregate_algorithm",
            "path_blob_rawsha_map_sha256",
            "members",
        ],
        "properties": {
            "schema_id": {"const": "ars://contracts/wp6-2-t2-protected-membership"},
            "schema_version": {"const": "1.0.0"},
            "contract_id": {"const": "wp6-2-t2-r3-protected-membership"},
            "status": {"const": "proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance"},
            "baseline_revision": {"const": "69a0fee6171fc25f936c8e3e03343bfbd0338440"},
            "derivation": {
                "const": "exact_union_of_accepted_core_wp6_1_t1a_and_provider_1_0_paths_at_baseline_revision"
            },
            "protected_path_count": {"const": 220},
            "aggregate_algorithm": {"const": "sha256_utf8_lf_sorted_path_pipe_git_blob_pipe_raw_git_blob_sha256_rows"},
            "path_blob_rawsha_map_sha256": dict(HASH),
            "members": {
                "type": "array",
                "items": member,
                "minItems": 220,
                "maxItems": 220,
                "uniqueItems": True,
            },
        },
        "additionalProperties": False,
    }


def schemas() -> dict[str, dict[str, Any]]:
    payloads = _event_payloads()
    return {
        ".research-system/schemas/contracts/wp6-2-t2-normative-crosswalk.schema.json": (_normative_crosswalk_schema()),
        ".research-system/schemas/contracts/wp6-2-t2-protected-membership.schema.json": (
            _protected_membership_schema()
        ),
        ".research-system/schemas/core/receipt-v2.schema.json": _receipt_v2_schema(),
        ".research-system/schemas/wp6-2-t2/secret-reference.schema.json": _secret_reference_schema(),
        ".research-system/schemas/wp6-2-t2/cost-grant.schema.json": _cost_grant_schema(),
        ".research-system/schemas/wp6-2-t2/provider-command-v2.schema.json": (_provider_command_v2_subset_schema()),
        ".research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json": (_provider_receipt_v2_subset_schema()),
        ".research-system/schemas/wp6-2-t2/commands/issue-cost-grant.schema.json": _command_schema(
            "IssueCostGrant",
            "issue-cost-grant",
            "wp6.2.t2.cost-grant.issue",
            rf"^cgr_{UUID7}$",
            ["cost_grant"],
            _issue_payload(),
        ),
        ".research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json": _command_schema(
            "AuthorizeProviderIssue",
            "authorize-provider-issue",
            "wp6.2.t2.provider.issue",
            rf"^cgr_{UUID7}$",
            ["cost_grant", "provider_command"],
            _authorize_payload(),
        ),
        ".research-system/schemas/wp6-2-t2/commands/record-provider-receipt.schema.json": _command_schema(
            "RecordProviderReceipt",
            "record-provider-receipt",
            "wp6.2.t2.provider.receipt.record",
            rf"^pcmd_{UUID7}$",
            ["provider_command", "cost_grant"],
            _receipt_payload(),
        ),
        ".research-system/schemas/wp6-2-t2/events/cost-grant-issued.schema.json": _event_schema(
            "CostGrantIssued", 0, 1, rf"^cgr_{UUID7}$", payloads["CostGrantIssued"]
        ),
        ".research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json": _event_schema(
            "CostGrantReserved", 0, 2, rf"^cgr_{UUID7}$", payloads["CostGrantReserved"]
        ),
        ".research-system/schemas/wp6-2-t2/events/provider-command-issued.schema.json": _event_schema(
            "ProviderCommandIssued", 1, 2, rf"^pcmd_{UUID7}$", payloads["ProviderCommandIssued"]
        ),
        ".research-system/schemas/wp6-2-t2/events/provider-receipt-recorded.schema.json": _event_schema(
            "ProviderReceiptRecorded", 0, 2, rf"^pcmd_{UUID7}$", payloads["ProviderReceiptRecorded"]
        ),
        ".research-system/schemas/wp6-2-t2/events/cost-grant-reconciled.schema.json": _event_schema(
            "CostGrantReconciled", 1, 2, rf"^cgr_{UUID7}$", payloads["CostGrantReconciled"]
        ),
    }


def materialize(repo_root: Path) -> None:
    for relative_path, schema in schemas().items():
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


def _git_blob(repo_root: Path, relative_path: str) -> str:
    return subprocess.run(
        ["git", "hash-object", "--no-filters", "--", relative_path],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _file_identity(repo_root: Path, relative_path: str) -> dict[str, str]:
    raw = (repo_root / relative_path).read_bytes()
    schema = json.loads(raw)
    return {
        "repository_path": relative_path,
        "schema_id": schema["$id"],
        "schema_version": schema["properties"]["schema_version"]["const"],
        "git_blob_id": _git_blob(repo_root, relative_path),
        "raw_utf8_lf_sha256": hashlib.sha256(raw).hexdigest(),
    }


def refresh_catalogue_identities(repo_root: Path) -> None:
    path = repo_root / ".research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml"
    catalogue = yaml.safe_load(path.read_text(encoding="utf-8"))
    for row in catalogue["rows"]:
        command_path = row["command_schema_identity"]["repository_path"]
        row["command_schema_identity"] = _file_identity(repo_root, command_path)
        row["event_schema_bindings"] = [
            {
                "event_type": binding["event_type"],
                **_file_identity(repo_root, binding["repository_path"]),
            }
            for binding in row["event_schema_bindings"]
        ]
    path.write_text(yaml.safe_dump(catalogue, sort_keys=False), encoding="utf-8", newline="\n")


def _artifact_role(relative_path: str) -> str:
    if relative_path == ".gitattributes":
        return "line_ending_control"
    if relative_path.endswith("09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md"):
        return "authority_addendum"
    if relative_path.endswith("authority-catalogue.yaml"):
        return "authority_catalogue"
    if relative_path.endswith("normative-crosswalk.yaml"):
        return "normative_crosswalk"
    if relative_path.endswith("protected-membership.yaml"):
        return "protected_membership_contract"
    if relative_path.endswith("authority-catalogue.schema.json"):
        return "authority_catalogue_schema"
    if relative_path.endswith("schema-identities.schema.json"):
        return "identity_manifest_schema"
    if relative_path.endswith("normative-crosswalk.schema.json"):
        return "normative_crosswalk_schema"
    if relative_path.endswith("protected-membership.schema.json"):
        return "protected_membership_schema"
    if "/commands/" in relative_path:
        return "command_schema"
    if "/events/" in relative_path:
        return "event_schema"
    if relative_path.endswith(".schema.json"):
        return "record_schema"
    if relative_path.endswith("expectations.py"):
        return "independent_oracle"
    if relative_path.endswith("schema_materializer.py"):
        return "schema_materializer"
    if relative_path.endswith("authority_validation.py"):
        return "semantic_validator"
    return "contract_test"


def materialize_identity_manifest(repo_root: Path) -> None:
    catalogue_path = ".research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml"
    identity_manifest_path = ".research-system/contracts/wp6-2-t2-schema-identities.yaml"
    protected_membership_path = ".research-system/contracts/wp6-2-t2-protected-membership.yaml"
    materialized_leaf_paths = {
        ".gitattributes",
        "docs/plans/agentic-research-system/design/09-wp6-2-t2-cost-grant-authority-addendum-2026-07-22.md",
        catalogue_path,
        ".research-system/contracts/wp6-2-t2-normative-crosswalk.yaml",
        protected_membership_path,
        ".research-system/schemas/contracts/wp6-2-t2-cost-grant-authority-catalogue.schema.json",
        ".research-system/schemas/contracts/wp6-2-t2-schema-identities.schema.json",
        "tests/research_system/contracts/wp6_2_t2_authority_validation.py",
        "tests/research_system/contracts/wp6_2_t2_schema_materializer.py",
        "tests/research_system/contracts/wp6_2_t2_expectations.py",
        "tests/research_system/contracts/test_wp6_2_t2_authority_contract.py",
        "tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py",
        *schemas(),
    }
    catalogue = yaml.safe_load((repo_root / catalogue_path).read_text(encoding="utf-8"))
    protected = yaml.safe_load((repo_root / protected_membership_path).read_text(encoding="utf-8"))
    artifacts = []
    for relative_path in sorted(materialized_leaf_paths):
        raw = (repo_root / relative_path).read_bytes()
        schema_id = None
        schema_version = None
        if relative_path.endswith(".schema.json"):
            schema = json.loads(raw)
            schema_id = schema["$id"]
            schema_version = schema["properties"]["schema_version"]["const"]
        elif relative_path == catalogue_path:
            schema_id = "ars://contracts/wp6-2-t2-cost-grant-authority-catalogue"
            schema_version = "1.0.0"
        elif relative_path.endswith("wp6-2-t2-normative-crosswalk.yaml"):
            schema_id = "ars://contracts/wp6-2-t2-normative-crosswalk"
            schema_version = "1.0.0"
        elif relative_path == protected_membership_path:
            schema_id = "ars://contracts/wp6-2-t2-protected-membership"
            schema_version = "1.0.0"
        artifacts.append(
            {
                "artifact_role": _artifact_role(relative_path),
                "repository_path": relative_path,
                "canonical_schema_id": schema_id,
                "schema_version": schema_version,
                "git_blob_id": _git_blob(repo_root, relative_path),
                "raw_utf8_lf_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    authority_rows = []
    for row in catalogue["rows"]:
        authority_rows.append(
            {
                "key": row["key"],
                "ordered_event_set": row["ordered_events"],
                "reducers": row["reducers"],
                "projections": row["projections"],
                "stream_write_set": row["write_set"],
                "authority": {
                    "scope": row["authority_scope"],
                    "subject": row["authority_subject"],
                    "subject_fields": row["authority_subject_fields"],
                },
                "receipt": row["receipt_binding"],
                "test_identity": {"positive": row["positive_test"], "negative": row["negative_tests"]},
            }
        )
    manifest = {
        "schema_id": "ars://contracts/wp6-2-t2-schema-identities",
        "schema_version": "1.0.0",
        "manifest_id": "wp6-2-t2-schema-identities",
        "manifest_version": "1.0.0",
        "status": "proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance",
        "self_identity": {
            "repository_path": identity_manifest_path,
            "schema_id": "ars://contracts/wp6-2-t2-schema-identities",
            "schema_version": "1.0.0",
            "hash_binding": "external_exact_state_review_and_owner_acceptance_only",
        },
        "candidate_lifecycle": {
            "review_status": "pending_fresh_independent_review",
            "acceptance_status": "pending_stephen_exact_hash_acceptance",
            "runtime_implementation_authorized": False,
        },
        "protected_baseline": {
            "start_revision": protected["baseline_revision"],
            "protected_path_count": protected["protected_path_count"],
            "path_blob_rawsha_map_sha256": protected["path_blob_rawsha_map_sha256"],
            "membership_contract_path": protected_membership_path,
            "command_tree": "9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea",
            "event_tree": "154ffc4bdde82fe903718734687e7a62797b1f69",
            "core_tree": "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46",
            "receipt_1_0_0_blob": "f204b3b71d6839bc866ba1251c8b87cc814ee0ce",
            "provider_command_1_0_0_blob": "9eb58609b9703674912e64f019db3cd4fb147a9c",
            "provider_receipt_1_0_0_blob": "8ac904e6c0b16e45034bcdc2221970d6a3ef13a8",
        },
        "artifacts": artifacts,
        "authority_rows": authority_rows,
        "test_identities": {
            "expected_set_path": "tests/research_system/contracts/wp6_2_t2_expectations.py",
            "semantic_validator_path": "tests/research_system/contracts/wp6_2_t2_authority_validation.py",
            "binding_test_paths": [
                "tests/research_system/contracts/test_wp6_2_t2_authority_contract.py",
                "tests/research_system/contracts/test_wp6_2_t2_authority_mutations.py",
            ],
            "positive_tests": [row["positive_test"] for row in catalogue["rows"]],
            "negative_tests": list(catalogue["negative_controls"]),
        },
        "hash_dependency_graph": [
            "leaf_exact_bytes_to_identity_manifest",
            "identity_manifest_to_external_independent_review",
            "external_independent_review_to_stephen_exact_hash_acceptance",
        ],
    }
    path = repo_root / identity_manifest_path
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    materialize(root)
    refresh_catalogue_identities(root)
    materialize_identity_manifest(root)
