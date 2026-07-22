"""Deterministically materialize the strict WP6.2 T2 leaf JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DRAFT = "https://json-schema.org/draft/2020-12/schema"
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
SEMVER = {"type": "string", "pattern": r"^[0-9]+\.[0-9]+\.[0-9]+$"}


def _string(*, pattern: str | None = None, min_length: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "string"}
    if pattern is not None:
        value["pattern"] = pattern
    if min_length is not None:
        value["minLength"] = min_length
    return value


def _id(prefix: str) -> dict[str, Any]:
    return _string(pattern=rf"^{prefix}_[0-9a-f-]+$")


def _closed(properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required if required is not None else list(properties),
        "properties": properties,
        "additionalProperties": False,
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
            "subject_id": _string(min_length=1),
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
            "route_id": _string(min_length=1),
            "profile_id": _string(min_length=1),
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
    seams = [
        "compiled_context_packet",
        "generated_adapter_provider_file",
        "rendered_provider_payload",
        "argv_environment_config_provider_options",
        "event_producer",
        "receipt_producer",
        "canonical_object_producer",
        "fixture_evaluation_evidence_producer",
    ]
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
            "secret_reference_id": _id("sref"),
            "revision": {"const": 1},
            "content_hash": dict(HASH),
            "provider": {"enum": ["claude", "codex"]},
            "credential_class": {"enum": ["api_token", "oauth_session", "local_provider_session"]},
            "resolver_id": _string(min_length=1),
            "resolver_version": dict(SEMVER),
            "allowed_scope": _scope(),
            "expires_at": {"type": "string", "format": "date-time"},
            "revocation_binding": _revocation_binding(),
            "redaction_proof": _closed(
                {
                    "policy_id": {"const": "wp6-2-t2-secret-sentinel-policy"},
                    "policy_version": {"const": "1.0.0"},
                    "evidence_sha256": dict(HASH),
                    "status": {"const": "no_secret_material_observed"},
                    "checked_seams": _ordered_constants(seams),
                }
            ),
        },
        "additionalProperties": False,
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
    return _closed(
        {
            "currency": _string(pattern="^[A-Z]{3}$"),
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "source_id": _string(min_length=1),
            "source_version": _string(min_length=1),
            "source_hash": dict(HASH),
            "effective_at": {"type": "string", "format": "date-time"},
            "expires_at": {"type": "string", "format": "date-time"},
        }
    )


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
            "secret_reference_id": _id("sref"),
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
    }


def _provider_command_v2_schema() -> dict[str, Any]:
    wrapper = _closed(
        {
            "accounting_method": _string(min_length=1),
            "accounting_version": _string(min_length=1),
            "provider_capacity_tokens": {"type": "integer", "minimum": 1},
            "managed_packet_tokens": {"type": "integer", "minimum": 0},
            "reserved_wrapper_tokens": {"type": "integer", "minimum": 0},
            "rendered_total_tokens": {"type": "integer", "minimum": 0},
        }
    )
    return {
        "$schema": DRAFT,
        "$id": "ars://adapters/provider-command/v2",
        "title": "WP6.2 T2 ProviderCommand required-field successor",
        "x-successor-of": {"schema_id": "ars://adapters/provider-command", "schema_version": "1.0.0"},
        "x-reader-compatibility": {
            "v2_reader": "may_read_v1_for_audit_only",
            "v1_reader": "must_reject_v2",
            "t2_issue": "requires_v2",
        },
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "provider_command_id",
            "revision",
            "revision_hash",
            "provider",
            "model",
            "profile_id",
            "adapter_revision",
            "policy_hash",
            "context_hash",
            "rendered_payload_hash",
            "idempotency_key",
            "operation",
            "timeout_s",
            "wrapper_accounting",
            "resource_grant_id",
            "execution_lease_id",
            "t2_binding",
            "token_ceiling",
            "cost_ceiling_microunits",
            "currency",
            "rate_evidence_hash",
            "pre_issue_evidence_manifest_hash",
            "expires_at",
            "authorized",
        ],
        "properties": {
            "schema_id": {"const": "ars://adapters/provider-command/v2"},
            "schema_version": {"const": "2.0.0"},
            "provider_command_id": _id("pcmd"),
            "revision": {"type": "integer", "minimum": 1},
            "revision_hash": dict(HASH),
            "provider": {"enum": ["claude", "codex"]},
            "model": _string(min_length=1),
            "profile_id": _string(min_length=1),
            "adapter_revision": _string(min_length=1),
            "policy_hash": dict(HASH),
            "context_hash": dict(HASH),
            "rendered_payload_hash": dict(HASH),
            "idempotency_key": _string(min_length=1),
            "operation": {"enum": ["request_model_work"]},
            "timeout_s": {"type": "integer", "minimum": 1},
            "wrapper_accounting": wrapper,
            "resource_grant_id": _id("rgr"),
            "execution_lease_id": _id("els"),
            "t2_binding": _closed(
                {
                    "task_id": _id("tsk"),
                    "dispatch_id": _id("dsp"),
                    "attempt_id": _id("att"),
                    "route_id": _string(min_length=1),
                    "secret_reference_id": _id("sref"),
                    "secret_reference_revision": {"type": "integer", "minimum": 1},
                    "secret_reference_hash": dict(HASH),
                    "cost_grant_id": _id("cgr"),
                    "cost_grant_revision": {"type": "integer", "minimum": 1},
                    "cost_grant_hash": dict(HASH),
                }
            ),
            "token_ceiling": _token_amounts(minimum=0),
            "cost_ceiling_microunits": {"type": "integer", "minimum": 1},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_hash": dict(HASH),
            "pre_issue_evidence_manifest_hash": dict(HASH),
            "expires_at": {"type": "string", "format": "date-time"},
            "authorized": {"const": True},
        },
        "additionalProperties": False,
    }


def _provider_receipt_v2_schema() -> dict[str, Any]:
    return {
        "$schema": DRAFT,
        "$id": "ars://adapters/provider-receipt/v2",
        "title": "WP6.2 T2 ProviderReceipt required-field successor",
        "x-successor-of": {"schema_id": "ars://adapters/provider-receipt", "schema_version": "1.0.0"},
        "x-reader-compatibility": {
            "v2_reader": "may_read_v1_for_audit_only",
            "v1_reader": "must_reject_v2",
            "t2_reconciliation": "requires_v2",
        },
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "provider_receipt_id",
            "revision",
            "revision_hash",
            "provider_command_id",
            "command_revision",
            "command_revision_hash",
            "provider",
            "model",
            "profile_id",
            "adapter_revision",
            "policy_hash",
            "context_hash",
            "rendered_payload_hash",
            "status",
            "complete",
            "t2_binding",
            "actual_consumption",
            "refund",
            "redaction",
        ],
        "properties": {
            "schema_id": {"const": "ars://adapters/provider-receipt/v2"},
            "schema_version": {"const": "2.0.0"},
            "provider_receipt_id": _id("prcp"),
            "revision": {"type": "integer", "minimum": 1},
            "revision_hash": dict(HASH),
            "provider_command_id": _id("pcmd"),
            "command_revision": {"type": "integer", "minimum": 1},
            "command_revision_hash": dict(HASH),
            "provider": {"enum": ["claude", "codex"]},
            "model": _string(min_length=1),
            "profile_id": _string(min_length=1),
            "adapter_revision": _string(min_length=1),
            "policy_hash": dict(HASH),
            "context_hash": dict(HASH),
            "rendered_payload_hash": dict(HASH),
            "status": {"enum": ["terminal", "duplicate", "cancelled", "uncertain", "incomplete", "blocked"]},
            "complete": {"type": "boolean"},
            "t2_binding": _closed(
                {
                    "task_id": _id("tsk"),
                    "dispatch_id": _id("dsp"),
                    "attempt_id": _id("att"),
                    "route_id": _string(min_length=1),
                    "secret_reference_id": _id("sref"),
                    "cost_grant_id": _id("cgr"),
                    "reservation_id": _id("crsv"),
                }
            ),
            "actual_consumption": _closed(
                {
                    "input_tokens": {"type": "integer", "minimum": 0},
                    "output_tokens": {"type": "integer", "minimum": 0},
                    "total_tokens": {"type": "integer", "minimum": 0},
                    "consumed_cost_microunits": {"type": "integer", "minimum": 0},
                }
            ),
            "refund": _closed(
                {
                    "reserved_cost_microunits": {"type": "integer", "minimum": 0},
                    "refund_microunits": {"type": "integer", "minimum": 0},
                    "disposition": {"enum": ["fully_consumed", "refunded"]},
                }
            ),
            "redaction": {"const": "raw_transport_content_discarded"},
        },
        "additionalProperties": False,
    }


def _write_set(roles: list[str]) -> dict[str, Any]:
    prefix_items = []
    patterns = {"cost_grant": "^cgr_[0-9a-f-]+$", "provider_command": "^pcmd_[0-9a-f-]+$"}
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
            "on_behalf_of_actor_id": {"type": ["string", "null"], "pattern": "^act_[0-9a-f-]+$"},
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
            "dispatch_id": _id("dsp"),
            "attempt_id": _id("att"),
            "route_id": _string(min_length=1),
            "profile_id": _string(min_length=1),
            "adapter_revision": _string(min_length=1),
            "secret_reference_id": _id("sref"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "token_ceilings": _token_amounts(minimum=0),
            "cost_ceiling_microunits": {"type": "integer", "minimum": 1},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_hash": dict(HASH),
            "expires_at": {"type": "string", "format": "date-time"},
        }
    )


def _authorize_payload() -> dict[str, Any]:
    return _closed(
        {
            "cost_grant_id": _id("cgr"),
            "cost_grant_revision": {"type": "integer", "minimum": 1},
            "cost_grant_hash": dict(HASH),
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "secret_reference_id": _id("sref"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "requested_tokens": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 1},
            "expected_available_microunits": {"type": "integer", "minimum": 1},
            "rendered_payload_hash": dict(HASH),
            "pre_issue_evidence_manifest_id": _string(min_length=1),
            "pre_issue_evidence_manifest_hash": dict(HASH),
        }
    )


def _receipt_payload() -> dict[str, Any]:
    return _closed(
        {
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "provider_receipt_id": _id("prcp"),
            "provider_receipt_revision": {"type": "integer", "minimum": 1},
            "provider_receipt_hash": dict(HASH),
            "provider_receipt_schema_id": {"const": "ars://adapters/provider-receipt/v2"},
            "provider_receipt_schema_version": {"const": "2.0.0"},
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crsv"),
            "actual_tokens": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 0},
            "consumed_cost_microunits": {"type": "integer", "minimum": 0},
            "refund_microunits": {"type": "integer", "minimum": 0},
            "refund_disposition": {"enum": ["fully_consumed", "refunded"]},
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
            "reservation_id": _id("crsv"),
            "provider_command_id": _id("pcmd"),
            "reserved_tokens": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 1},
            "remaining_cost_microunits": {"type": "integer", "minimum": 0},
            "pre_issue_evidence_manifest_hash": dict(HASH),
        }
    )
    command_issued = _closed(
        {
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crsv"),
            "secret_reference_id": _id("sref"),
            "rendered_payload_hash": dict(HASH),
            "pre_issue_evidence_manifest_hash": dict(HASH),
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
            "reservation_id": _id("crsv"),
            "provider_terminal_status": {"enum": ["terminal", "duplicate", "cancelled"]},
            "receipt_complete": {"const": True},
        }
    )
    reconciled = _closed(
        {
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crsv"),
            "provider_command_id": _id("pcmd"),
            "provider_receipt_id": _id("prcp"),
            "actual_input_tokens": {"type": "integer", "minimum": 0},
            "actual_output_tokens": {"type": "integer", "minimum": 0},
            "actual_total_tokens": {"type": "integer", "minimum": 0},
            "reserved_cost_microunits": {"type": "integer", "minimum": 0},
            "consumed_cost_microunits": {"type": "integer", "minimum": 0},
            "refund_microunits": {"type": "integer", "minimum": 0},
            "refund_disposition": {"enum": ["fully_consumed", "refunded"]},
            "remaining_cost_microunits": {"type": "integer", "minimum": 0},
        }
    )
    return {
        "CostGrantIssued": issued,
        "CostGrantReserved": reserved,
        "ProviderCommandIssued": command_issued,
        "ProviderReceiptRecorded": receipt_recorded,
        "CostGrantReconciled": reconciled,
    }


def schemas() -> dict[str, dict[str, Any]]:
    payloads = _event_payloads()
    return {
        ".research-system/schemas/wp6-2-t2/secret-reference.schema.json": _secret_reference_schema(),
        ".research-system/schemas/wp6-2-t2/cost-grant.schema.json": _cost_grant_schema(),
        ".research-system/schemas/wp6-2-t2/provider-command-v2.schema.json": _provider_command_v2_schema(),
        ".research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json": _provider_receipt_v2_schema(),
        ".research-system/schemas/wp6-2-t2/commands/issue-cost-grant.schema.json": _command_schema(
            "IssueCostGrant",
            "issue-cost-grant",
            "wp6.2.t2.cost-grant.issue",
            "^cgr_[0-9a-f-]+$",
            ["cost_grant"],
            _issue_payload(),
        ),
        ".research-system/schemas/wp6-2-t2/commands/authorize-provider-issue.schema.json": _command_schema(
            "AuthorizeProviderIssue",
            "authorize-provider-issue",
            "wp6.2.t2.provider.issue",
            "^cgr_[0-9a-f-]+$",
            ["cost_grant", "provider_command"],
            _authorize_payload(),
        ),
        ".research-system/schemas/wp6-2-t2/commands/record-provider-receipt.schema.json": _command_schema(
            "RecordProviderReceipt",
            "record-provider-receipt",
            "wp6.2.t2.provider.receipt.record",
            "^pcmd_[0-9a-f-]+$",
            ["provider_command", "cost_grant"],
            _receipt_payload(),
        ),
        ".research-system/schemas/wp6-2-t2/events/cost-grant-issued.schema.json": _event_schema(
            "CostGrantIssued", 0, 1, "^cgr_[0-9a-f-]+$", payloads["CostGrantIssued"]
        ),
        ".research-system/schemas/wp6-2-t2/events/cost-grant-reserved.schema.json": _event_schema(
            "CostGrantReserved", 0, 2, "^cgr_[0-9a-f-]+$", payloads["CostGrantReserved"]
        ),
        ".research-system/schemas/wp6-2-t2/events/provider-command-issued.schema.json": _event_schema(
            "ProviderCommandIssued", 1, 2, "^pcmd_[0-9a-f-]+$", payloads["ProviderCommandIssued"]
        ),
        ".research-system/schemas/wp6-2-t2/events/provider-receipt-recorded.schema.json": _event_schema(
            "ProviderReceiptRecorded", 0, 2, "^pcmd_[0-9a-f-]+$", payloads["ProviderReceiptRecorded"]
        ),
        ".research-system/schemas/wp6-2-t2/events/cost-grant-reconciled.schema.json": _event_schema(
            "CostGrantReconciled", 1, 2, "^cgr_[0-9a-f-]+$", payloads["CostGrantReconciled"]
        ),
    }


def materialize(repo_root: Path) -> None:
    for relative_path, schema in schemas().items():
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    materialize(Path(__file__).resolve().parents[3])
