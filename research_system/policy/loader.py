"""Strict loaders for the canonical policy and accepted D-G5-5 applicability."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.policy.models import (
    CanonicalPolicyBundle,
    Control,
    ControlApplicability,
    PolicyControlApplicability,
    ProviderEvidenceRequirement,
)

RISK_TIERS = ("R0", "R1", "R2", "R3")
OPERATIONS = {
    "no-shell": ("invoke_declared_tool",),
    "no-direct-event-write": ("submit_ars_command",),
    "no-live-provider-by-default": (
        "cancel_provider_work", "query_provider_status", "request_model_work", "request_review"
    ),
    "no-raw-transcript-retention": (
        "deliver_context", "deliver_message", "request_model_work", "request_review"
    ),
}
PROVIDERS = {
    "fake-claude-adapter-v1": "fake-claude-adapter-v1-windows-fake-transport",
    "fake-codex-adapter-v1": "fake-codex-adapter-v1-windows-fake-transport",
}


def _read_yaml(path: Path | str) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("policy document must be an object")
    return value


def load_canonical_policy_bundle(path: Path | str) -> CanonicalPolicyBundle:
    """Load the sole provider-neutral canonical bundle with content identity."""
    payload = _read_yaml(path)
    controls_payload = payload.get("controls")
    if not isinstance(controls_payload, dict) or set(controls_payload) != set(OPERATIONS):
        raise ValueError("canonical controls must equal the accepted control set")
    controls = []
    for control_id, item in sorted(controls_payload.items()):
        if not isinstance(item, dict) or not item.get("revision"):
            raise ValueError(f"control {control_id} revision is required")
        controls.append(Control(control_id=control_id, revision=str(item["revision"]), semantic_class=str(item["semantic_class"]), critical=item["critical"] is True, failure_mode=str(item["failure_mode"])))
    return CanonicalPolicyBundle(
        canonical_policy_bundle_id=str(payload["canonical_policy_bundle_id"]),
        revision=str(payload["revision"]),
        content_hash=sha256_hex(canonical_bytes(payload)),
        controls=tuple(controls),
    )


def _require_sha(value: object, label: str) -> str:
    text = str(value)
    if re.fullmatch(r"[0-9a-f]{64}", text) is None:
        raise ValueError(f"{label} must be sha256")
    return text


def load_policy_control_applicability(path: Path | str, *, bundle: CanonicalPolicyBundle) -> PolicyControlApplicability:
    """Load only the exact owner-approved, bundle-bound D-G5-5 mapping."""
    payload = _read_yaml(path)
    required_top = {"schema_id", "schema_version", "applicability_id", "applicability_hash", "decision_ref", "decision_payload", "decision_record_hash", "bundle", "controls"}
    if set(payload) != required_top:
        raise ValueError("applicability fields are incomplete or unexpected")
    if payload["decision_ref"] != "D-G5-5":
        raise ValueError("decision_ref must be D-G5-5")
    decision_hash = sha256_hex(canonical_bytes(payload["decision_payload"]))
    if payload["decision_record_hash"] != decision_hash:
        raise ValueError("decision_record_hash mismatch")
    binding = payload["bundle"]
    if binding != {"id": bundle.canonical_policy_bundle_id, "revision": bundle.revision, "hash": bundle.content_hash}:
        raise ValueError("canonical bundle binding mismatch")
    raw_controls = payload["controls"]
    if not isinstance(raw_controls, list) or len(raw_controls) != len(OPERATIONS):
        raise ValueError("controls must contain every canonical control exactly once")
    seen: set[str] = set()
    controls = []
    bundle_controls = {item.control_id: item for item in bundle.controls}
    for raw in raw_controls:
        if not isinstance(raw, dict) or "required_operation_classes" not in raw:
            raise ValueError("required_operation_classes is required")
        if set(raw) != {"control_id", "control_revision", "required_risk_tiers", "required_operation_classes", "provider_requirements"}:
            raise ValueError("control applicability has missing or unexpected fields")
        control_id = str(raw["control_id"])
        if control_id in seen or control_id not in OPERATIONS:
            raise ValueError("duplicate or unknown control")
        seen.add(control_id)
        if raw["control_revision"] != bundle_controls[control_id].revision:
            raise ValueError("stale control revision")
        risks = tuple(raw["required_risk_tiers"])
        operations = tuple(raw["required_operation_classes"])
        if risks != RISK_TIERS or operations != OPERATIONS[control_id] or any("*" in item for item in (*risks, *operations)):
            raise ValueError("risk tiers or required_operation_classes differ from D-G5-5")
        requirements = []
        raw_requirements = raw["provider_requirements"]
        if not isinstance(raw_requirements, list) or len(raw_requirements) != 2:
            raise ValueError("each control requires exactly two providers")
        provider_seen: set[str] = set()
        for req in raw_requirements:
            expected_fields = {"provider_variant", "variant_id", "fixture_id", "fixture_revision", "property", "json_pointer", "canonical_observed_value", "expected_observed_value_hash"}
            if not isinstance(req, dict) or set(req) != expected_fields:
                raise ValueError("provider requirement fields invalid")
            provider = str(req["provider_variant"])
            if provider in provider_seen or PROVIDERS.get(provider) != req["variant_id"]:
                raise ValueError("duplicate or incompatible provider selector")
            provider_seen.add(provider)
            if req["fixture_id"] != "F-020" or req["fixture_revision"] != "r2" or req["property"] != "adapter_policy_parity" or req["json_pointer"] != f"/controls/{control_id}":
                raise ValueError("stale or incompatible F-020 selector")
            observed = req["canonical_observed_value"]
            if not isinstance(observed, dict) or tuple(sorted(observed.get("operations", {}))) != operations:
                raise ValueError("operation evidence does not close exactly")
            expected_hash = sha256_hex(canonical_bytes({"property": req["property"], "json_pointer": req["json_pointer"], "canonical_observed_value": observed}))
            if req["expected_observed_value_hash"] != expected_hash:
                raise ValueError("expected_observed_value_hash mismatch")
            requirements.append(ProviderEvidenceRequirement(provider, str(req["variant_id"]), "F-020", "r2", "adapter_policy_parity", str(req["json_pointer"]), observed, expected_hash))
        controls.append(ControlApplicability(control_id, str(raw["control_revision"]), risks, operations, tuple(sorted(requirements, key=lambda item: item.provider_variant))))
    if seen != set(OPERATIONS):
        raise ValueError("missing canonical control")
    hash_payload = copy.deepcopy(payload)
    declared_hash = str(hash_payload.pop("applicability_hash"))
    hash_payload.pop("applicability_id")
    actual_hash = sha256_hex(canonical_bytes(hash_payload))
    if declared_hash != actual_hash or payload["applicability_id"] != f"pca_{actual_hash}":
        raise ValueError("applicability identity/hash mismatch")
    return PolicyControlApplicability(str(payload["applicability_id"]), actual_hash, "D-G5-5", _require_sha(payload["decision_record_hash"], "decision_record_hash"), bundle.canonical_policy_bundle_id, bundle.revision, bundle.content_hash, tuple(sorted(controls, key=lambda item: item.control_id)))
