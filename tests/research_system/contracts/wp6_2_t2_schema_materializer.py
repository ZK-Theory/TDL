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


def _receipt_v2_schema() -> dict[str, Any]:
    event = _closed(
        {
            "event_id": _id("evt"),
            "transaction_position": {"type": "integer", "minimum": 0},
            "stream_id": _string(min_length=1),
            "resulting_stream_version": {"type": "integer", "minimum": 1},
        }
    )
    properties = {
        "schema_id": {"const": "ars://core/receipt/v2"},
        "schema_version": {"const": "2.0.0"},
        "receipt_id": _id("rcp"),
        "outcome": {"enum": ["accepted", "duplicate", "rejected", "conflict"]},
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


def _pre_issue_evidence_manifest_schema() -> dict[str, Any]:
    seam_ids = [
        "compiled_context_packet",
        "generated_adapter_provider_file",
        "rendered_provider_payload",
        "argv_environment_config_provider_options",
        "event_producer",
        "receipt_producer",
        "canonical_object_producer",
        "fixture_evaluation_evidence_producer",
    ]
    seam_items = []
    for seam_id in seam_ids:
        seam_items.append(
            _closed(
                {
                    "seam_id": {"const": seam_id},
                    "producer": _content_ref(),
                    "source_evidence": {
                        "type": "array",
                        "items": _content_ref(),
                        "minItems": 1,
                        "uniqueItems": True,
                    },
                    "serialized_payload_hash": dict(HASH),
                    "outcome": {"const": "no_prohibited_material_or_sentinel"},
                }
            )
        )
    return {
        "$schema": DRAFT,
        "$id": "ars://wp6-2/t2/pre-issue-evidence-manifest",
        "title": "WP6.2 T2 PreIssueEvidenceManifest",
        "type": "object",
        "required": [
            "schema_id",
            "schema_version",
            "pre_issue_evidence_manifest_id",
            "revision",
            "content_hash",
            "policy",
            "scanner",
            "safe_synthetic_sentinel_identity",
            "safe_synthetic_sentinel_hash",
            "seams",
            "aggregate_content_hash",
        ],
        "properties": {
            "schema_id": {"const": "ars://wp6-2/t2/pre-issue-evidence-manifest"},
            "schema_version": {"const": "1.0.0"},
            "pre_issue_evidence_manifest_id": _id("pem"),
            "revision": {"type": "integer", "minimum": 1},
            "content_hash": dict(HASH),
            "policy": _content_ref(),
            "scanner": _content_ref(),
            "safe_synthetic_sentinel_identity": _canonical_id(),
            "safe_synthetic_sentinel_hash": dict(HASH),
            "seams": {
                "type": "array",
                "prefixItems": seam_items,
                "items": False,
                "minItems": len(seam_ids),
                "maxItems": len(seam_ids),
            },
            "aggregate_content_hash": dict(HASH),
        },
        "additionalProperties": False,
        "x-prohibited-fields": ["credential", "secret", "sentinel_value"],
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
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
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


def _provider_command_v2_complete_schema() -> dict[str, Any]:
    identity = lambda prefix: _closed(  # noqa: E731 - local schema constructor
        {
            "id": _id(prefix),
            "revision": {"type": "integer", "minimum": 1},
            "content_hash": dict(HASH),
        }
    )
    token_gate = _closed(
        {
            "method": {"enum": ["exact", "evaluated_conservative_upper_bound"]},
            "method_version": _string(min_length=1),
            "observed_tokens": {"type": "integer", "minimum": 0},
            "ceiling_tokens": {"type": "integer", "minimum": 0},
            "passed": {"const": True},
            "evidence_hash": dict(HASH),
        }
    )
    properties = {
        "schema_id": {"const": "ars://adapters/provider-command/v2"},
        "schema_version": {"const": "2.0.0"},
        "provider_command_id": _id("pcmd"),
        "revision": {"type": "integer", "minimum": 1},
        "revision_hash": dict(HASH),
        "idempotency_key": _string(min_length=1),
        "w2_binding": _closed(
            {
                "command_id": _id("cmd"),
                "command_revision": {"type": "integer", "minimum": 1},
                "message_id": _id("msg"),
                "dispatch_id": _id("dsp"),
                "expected_control_store_position": {"type": "integer", "minimum": 0},
            }
        ),
        "provider_binding": _closed(
            {
                "provider": {"enum": ["claude", "codex"]},
                "model": _string(min_length=1),
                "model_version": _string(min_length=1),
                "adapter_revision": _string(min_length=1),
                "adapter_hash": dict(HASH),
            }
        ),
        "routing_binding": _closed(
            {
                "route": identity("rte"),
                "profile": identity("prf"),
                "evaluation": identity("evl"),
                "policy": identity("pol"),
                "routing_evidence_snapshot_id": _id("res"),
                "routing_evidence_snapshot_hash": dict(HASH),
            }
        ),
        "context_binding": _closed(
            {
                "context_candidate": identity("ctx"),
                "context_packet": identity("cpk"),
                "context_addendum": identity("cad"),
                "exact_content_hash": dict(HASH),
                "reference_token_gate": token_gate,
                "provider_usable_input_gate": token_gate,
                "rendered_provider_payload_hash": dict(HASH),
            }
        ),
        "assurance_binding": _closed(
            {
                "purpose": {"enum": ["model_work", "independent_review", "assurance_evidence"]},
                "review_id": {"oneOf": [_id("rev"), {"type": "null"}]},
                "subject_visibility": {"enum": ["public", "internal", "restricted_reference_only"]},
                "evidence_visibility": {"enum": ["public", "internal", "restricted_reference_only"]},
                "prohibited_producer_material": {
                    "type": "array",
                    "items": {"enum": ["credentials", "raw_restricted_data", "hidden_reasoning", "full_transcripts"]},
                    "uniqueItems": True,
                },
            }
        ),
        "resource_binding": _closed(
            {
                "resource_grant": identity("rgr"),
                "execution_lease": identity("els"),
                "stop_policy": identity("stp"),
            }
        ),
        "t2_authority_binding": _closed(
            {
                "task_id": _id("tsk"),
                "dispatch_id": _id("dsp"),
                "attempt_id": _id("att"),
                "secret_reference_id": _id("srf"),
                "secret_reference_revision": {"type": "integer", "minimum": 1},
                "secret_reference_hash": dict(HASH),
                "cost_grant_id": _id("cgr"),
                "cost_grant_revision": {"type": "integer", "minimum": 1},
                "cost_grant_hash": dict(HASH),
                "pre_issue_evidence_manifest_id": _id("pem"),
                "pre_issue_evidence_manifest_revision": {"type": "integer", "minimum": 1},
                "pre_issue_evidence_manifest_hash": dict(HASH),
                "token_ceilings": _token_amounts(minimum=0),
                "cost_ceiling_microunits": {"type": "integer", "minimum": 1},
                "currency": _string(pattern="^[A-Z]{3}$"),
                "rate_evidence_id": _canonical_id(),
                "rate_evidence_revision": {"type": "integer", "minimum": 1},
                "rate_evidence_hash": dict(HASH),
            }
        ),
        "operation": _closed(
            {
                "operation_class": {
                    "enum": [
                        "deliver_context",
                        "request_model_work",
                        "invoke_declared_tool",
                        "submit_ars_command",
                        "deliver_message",
                        "request_review",
                        "cancel_provider_work",
                        "query_provider_status",
                    ]
                },
                "rendered_payload_hash": dict(HASH),
            }
        ),
        "permissions": _closed(
            {
                "tools": {"type": "array", "items": _string(min_length=1), "uniqueItems": True},
                "roots": {"type": "array", "items": _content_ref(), "uniqueItems": True},
                "network": {"enum": ["denied", "allowlisted"]},
                "write": {"enum": ["denied", "scoped"]},
                "sensitivity": {"enum": ["public", "internal", "restricted_reference_only"]},
                "default_deny": {"type": "array", "items": _string(min_length=1), "minItems": 1, "uniqueItems": True},
            }
        ),
        "receipt_expectation": _closed(
            {
                "required_fields": {
                    "type": "array",
                    "items": _string(min_length=1),
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "exact_delivery_proof_required": {"const": True},
                "incomplete_is_diagnostic_only": {"const": True},
            }
        ),
        "lifecycle_policy": _closed(
            {
                "timeout_at": {"type": "string", "format": "date-time"},
                "expires_at": {"type": "string", "format": "date-time"},
                "retry": {"enum": ["never", "only_with_proven_provider_idempotency"]},
                "reconciliation": {"const": "receipt_or_safe_idempotent_retry_required"},
            }
        ),
    }
    return {
        "$schema": DRAFT,
        "$id": "ars://adapters/provider-command/v2",
        "title": "WP6.2 T2 complete W7 ProviderCommand successor",
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


def _provider_receipt_v2_complete_schema() -> dict[str, Any]:
    not_exposed = _closed(
        {
            "disposition": {"const": "not_exposed"},
            "evidence": _content_ref(),
        }
    )
    exposed_id = _closed({"disposition": {"const": "exposed"}, "value": _string(min_length=1)})
    native_id = {"oneOf": [exposed_id, not_exposed]}
    properties = {
        "schema_id": {"const": "ars://adapters/provider-receipt/v2"},
        "schema_version": {"const": "2.0.0"},
        "provider_receipt_id": _id("prcp"),
        "revision": {"type": "integer", "minimum": 1},
        "revision_hash": dict(HASH),
        "command_binding": _closed(
            {
                "provider_command_id": _id("pcmd"),
                "provider_command_revision": {"type": "integer", "minimum": 1},
                "provider_command_hash": dict(HASH),
            }
        ),
        "t2_authority_binding": _closed(
            {
                "secret_reference_id": _id("srf"),
                "secret_reference_revision": {"type": "integer", "minimum": 1},
                "secret_reference_hash": dict(HASH),
                "cost_grant_id": _id("cgr"),
                "cost_grant_revision": {"type": "integer", "minimum": 1},
                "cost_grant_hash": dict(HASH),
                "reservation_id": _id("crs"),
                "reservation_revision": {"type": "integer", "minimum": 1},
                "reservation_hash": dict(HASH),
                "pre_issue_evidence_manifest_id": _id("pem"),
                "pre_issue_evidence_manifest_revision": {"type": "integer", "minimum": 1},
                "pre_issue_evidence_manifest_hash": dict(HASH),
            }
        ),
        "provider_binding": _closed(
            {
                "provider": {"enum": ["claude", "codex"]},
                "model": _string(min_length=1),
                "model_version": _string(min_length=1),
                "profile_id": _id("prf"),
                "profile_hash": dict(HASH),
                "adapter_revision": _string(min_length=1),
                "adapter_hash": dict(HASH),
                "policy_id": _id("pol"),
                "policy_hash": dict(HASH),
            }
        ),
        "provider_native_ids": _closed({"request_id": native_id, "session_id": native_id, "response_id": native_id}),
        "timestamps": _closed(
            {
                "issued_at": {"type": "string", "format": "date-time"},
                "acknowledged_at": {"type": ["string", "null"], "format": "date-time"},
                "terminal_at": {"type": "string", "format": "date-time"},
            }
        ),
        "delivery_proof": {
            "oneOf": [
                _closed(
                    {
                        "disposition": {"const": "proven"},
                        "delivered_context_hash": dict(HASH),
                        "delivered_payload_hash": dict(HASH),
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
        "token_accounting": _closed(
            {
                "input_tokens": {"type": "integer", "minimum": 0},
                "output_tokens": {"type": "integer", "minimum": 0},
                "total_tokens": {"type": "integer", "minimum": 0},
                "method": _string(min_length=1),
                "method_version": _string(min_length=1),
                "capacity_outcome": {"enum": ["within_capacity", "capacity_exceeded", "unproven"]},
            }
        ),
        "actions": _closed(
            {
                name: {"type": "array", "items": _content_ref()}
                for name in ("attempted", "allowed", "denied", "completed")
            }
        ),
        "terminal_outcome": _closed(
            {
                "status": {"enum": ["terminal", "duplicate", "cancelled", "timed_out", "uncertain", "blocked"]},
                "provider_native_status": _string(min_length=1),
                "provider_error_class": {"type": ["string", "null"]},
            }
        ),
        "outputs": _closed(
            {
                "references": {"type": "array", "items": _content_ref()},
                "output_hash": dict(HASH),
            }
        ),
        "lifecycle_evidence": _closed(
            {name: _content_ref() for name in ("cancellation", "timeout", "retry", "duplicate", "reconciliation")}
        ),
        "resource_observations": _closed(
            {
                "resource_grant_id": _id("rgr"),
                "execution_lease_id": _id("els"),
                "process_evidence": _content_ref(),
            }
        ),
        "cost_evidence": _closed(
            {
                "currency": _string(pattern="^[A-Z]{3}$"),
                "rate_evidence_id": _canonical_id(),
                "rate_evidence_revision": {"type": "integer", "minimum": 1},
                "rate_evidence_hash": dict(HASH),
            }
        ),
        "evidence_disposition": _closed(
            {
                "redaction": {"const": "secret_and_restricted_material_removed"},
                "omitted_evidence": {"type": "array", "items": _content_ref()},
            }
        ),
        "completeness": _closed(
            {
                "complete": {"type": "boolean"},
                "dispatch_gate_satisfied": {"type": "boolean"},
                "delivery_gate_satisfied": {"type": "boolean"},
                "reconciliation_gate_satisfied": {"type": "boolean"},
                "review_gate_satisfied": {"type": "boolean"},
                "diagnostic_only": {"type": "boolean"},
            }
        ),
    }
    complete = {
        "if": {"properties": {"completeness": {"properties": {"complete": {"const": True}}}}},
        "then": {
            "properties": {
                "delivery_proof": {"properties": {"disposition": {"const": "proven"}}},
                "completeness": {
                    "properties": {
                        "dispatch_gate_satisfied": {"const": True},
                        "delivery_gate_satisfied": {"const": True},
                        "reconciliation_gate_satisfied": {"const": True},
                        "review_gate_satisfied": {"const": True},
                        "diagnostic_only": {"const": False},
                    }
                },
            }
        },
        "else": {
            "properties": {
                "completeness": {
                    "properties": {
                        "dispatch_gate_satisfied": {"const": False},
                        "delivery_gate_satisfied": {"const": False},
                        "reconciliation_gate_satisfied": {"const": False},
                        "review_gate_satisfied": {"const": False},
                        "diagnostic_only": {"const": True},
                    }
                }
            }
        },
    }
    return {
        "$schema": DRAFT,
        "$id": "ars://adapters/provider-receipt/v2",
        "title": "WP6.2 T2 complete W7 ProviderReceipt successor",
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
            "dispatch_id": _id("dsp"),
            "attempt_id": _id("att"),
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
    return _closed(
        {
            "cost_grant_id": _id("cgr"),
            "cost_grant_revision": {"type": "integer", "minimum": 1},
            "cost_grant_hash": dict(HASH),
            "reservation_id": _id("crs"),
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "secret_reference_id": _id("srf"),
            "secret_reference_revision": {"type": "integer", "minimum": 1},
            "secret_reference_hash": dict(HASH),
            "requested_tokens": _token_amounts(minimum=0),
            "reserved_cost_microunits": {"type": "integer", "minimum": 1},
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
            "pre_issue_evidence_manifest_id": _id("pem"),
            "pre_issue_evidence_manifest_revision": {"type": "integer", "minimum": 1},
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
            "reserved_cost_microunits": {"type": "integer", "minimum": 1},
            "remaining_cost_microunits": {"type": "integer", "minimum": 0},
            "currency": _string(pattern="^[A-Z]{3}$"),
            "rate_evidence_id": _canonical_id(),
            "rate_evidence_revision": {"type": "integer", "minimum": 1},
            "rate_evidence_hash": dict(HASH),
            "input_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "output_microunits_per_million_tokens": {"type": "integer", "minimum": 0},
            "rate_mode": {"enum": ["metered", "zero_cost_authorized"]},
            "zero_cost_authority": {"oneOf": [_content_ref(), {"type": "null"}]},
            "pre_issue_evidence_manifest_hash": dict(HASH),
            "pre_issue_evidence_manifest_id": _id("pem"),
            "pre_issue_evidence_manifest_revision": {"type": "integer", "minimum": 1},
        }
    )
    command_issued = _closed(
        {
            "provider_command_id": _id("pcmd"),
            "provider_command_revision": {"type": "integer", "minimum": 1},
            "provider_command_hash": dict(HASH),
            "cost_grant_id": _id("cgr"),
            "reservation_id": _id("crs"),
            "secret_reference_id": _id("srf"),
            "rendered_payload_hash": dict(HASH),
            "pre_issue_evidence_manifest_hash": dict(HASH),
            "pre_issue_evidence_manifest_id": _id("pem"),
            "pre_issue_evidence_manifest_revision": {"type": "integer", "minimum": 1},
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
            "finding_id": {"enum": ["C1", "C2", "C3", "C4", "M1", "M2", "M3"]},
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
            "crosswalk_id": {"const": "wp6-2-t2-r1-normative-crosswalk"},
            "status": {"const": "proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance"},
            "authorities": {
                "type": "array",
                "items": {"enum": ["W2", "W7", "W8", "06b", "P-037", "P-038"]},
                "minItems": 6,
                "maxItems": 6,
                "uniqueItems": True,
            },
            "oracle_source": {"const": "tests/research_system/contracts/wp6_2_t2_expectations.py#EXPECTED_CROSSWALK"},
            "rows": {
                "type": "array",
                "items": row,
                "minItems": 7,
                "maxItems": 7,
            },
        },
        "additionalProperties": False,
    }


def schemas() -> dict[str, dict[str, Any]]:
    payloads = _event_payloads()
    return {
        ".research-system/schemas/contracts/wp6-2-t2-normative-crosswalk.schema.json": (_normative_crosswalk_schema()),
        ".research-system/schemas/core/receipt-v2.schema.json": _receipt_v2_schema(),
        ".research-system/schemas/wp6-2-t2/secret-reference.schema.json": _secret_reference_schema(),
        ".research-system/schemas/wp6-2-t2/cost-grant.schema.json": _cost_grant_schema(),
        ".research-system/schemas/wp6-2-t2/pre-issue-evidence-manifest.schema.json": (
            _pre_issue_evidence_manifest_schema()
        ),
        ".research-system/schemas/wp6-2-t2/provider-command-v2.schema.json": (_provider_command_v2_complete_schema()),
        ".research-system/schemas/wp6-2-t2/provider-receipt-v2.schema.json": (_provider_receipt_v2_complete_schema()),
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
    from tests.research_system.contracts.wp6_2_t2_expectations import SCHEMA_IDENTITIES

    path = repo_root / ".research-system/contracts/wp6-2-t2-cost-grant-authority-catalogue.yaml"
    catalogue = yaml.safe_load(path.read_text(encoding="utf-8"))
    for row in catalogue["rows"]:
        row["command_schema_identity"] = _file_identity(repo_root, SCHEMA_IDENTITIES[row["command_type"]]["path"])
        row["event_schema_bindings"] = [
            {"event_type": event_type, **_file_identity(repo_root, SCHEMA_IDENTITIES[event_type]["path"])}
            for event_type in row["ordered_events"]
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
    if relative_path.endswith("authority-catalogue.schema.json"):
        return "authority_catalogue_schema"
    if relative_path.endswith("schema-identities.schema.json"):
        return "identity_manifest_schema"
    if relative_path.endswith("normative-crosswalk.schema.json"):
        return "normative_crosswalk_schema"
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
    from tests.research_system.contracts.wp6_2_t2_expectations import (
        CATALOGUE_PATH,
        EXPECTED_ROWS,
        IDENTITY_MANIFEST_PATH,
        MATERIALIZED_LEAF_PATHS,
        NEGATIVE_CASES,
    )

    catalogue = yaml.safe_load((repo_root / CATALOGUE_PATH).read_text(encoding="utf-8"))
    artifacts = []
    for relative_path in sorted(MATERIALIZED_LEAF_PATHS):
        raw = (repo_root / relative_path).read_bytes()
        schema_id = None
        schema_version = None
        if relative_path.endswith(".schema.json"):
            schema = json.loads(raw)
            schema_id = schema["$id"]
            schema_version = schema["properties"]["schema_version"]["const"]
        elif relative_path == CATALOGUE_PATH:
            schema_id = "ars://contracts/wp6-2-t2-cost-grant-authority-catalogue"
            schema_version = "1.0.0"
        elif relative_path.endswith("wp6-2-t2-normative-crosswalk.yaml"):
            schema_id = "ars://contracts/wp6-2-t2-normative-crosswalk"
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
            "repository_path": IDENTITY_MANIFEST_PATH,
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
            "start_revision": "69a0fee6171fc25f936c8e3e03343bfbd0338440",
            "protected_path_count": 214,
            "path_blob_rawsha_map_sha256": "b99f76f3406dc2bdf50b41051ffdb252681ea2ab7861d0fdc8a19da3dec52a65",
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
            "positive_tests": [row["positive_test"] for row in EXPECTED_ROWS],
            "negative_tests": list(NEGATIVE_CASES),
        },
        "hash_dependency_graph": [
            "leaf_exact_bytes_to_identity_manifest",
            "identity_manifest_to_external_independent_review",
            "external_independent_review_to_stephen_exact_hash_acceptance",
        ],
    }
    path = repo_root / IDENTITY_MANIFEST_PATH
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    materialize(root)
    refresh_catalogue_identities(root)
    materialize_identity_manifest(root)
