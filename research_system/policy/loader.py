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
        "cancel_provider_work",
        "query_provider_status",
        "request_model_work",
        "request_review",
    ),
    "no-raw-transcript-retention": ("deliver_context", "deliver_message", "request_model_work", "request_review"),
}
PROVIDERS = {
    "fake-claude-adapter-v1": "fake-claude-adapter-v1-windows-fake-transport",
    "fake-codex-adapter-v1": "fake-codex-adapter-v1-windows-fake-transport",
}
ACCEPTED_DG55_DECISION_PAYLOAD = {
    "owner": "Stephen",
    "accepted_on": "2026-07-12",
    "control_applicability": [
        {
            "control_id": control_id,
            "control_revision": "r1",
            "required_risk_tiers": list(RISK_TIERS),
            "required_operation_classes": list(operations),
        }
        for control_id, operations in OPERATIONS.items()
    ],
    "f020_binding": {
        "fixture_id": "F-020",
        "fixture_revision": "r2",
        "property": "adapter_policy_parity",
    },
}
ACCEPTED_DG55_DECISION_RECORD_HASH = sha256_hex(canonical_bytes(ACCEPTED_DG55_DECISION_PAYLOAD))
ACCEPTED_DG55_APPLICABILITY_HASH = "fa81d6de64ea73575ac3fe715b38984ef7c99e9ec1761736711094a26bb1d7b0"


def _read_yaml(path: Path | str) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("policy document must be an object")
    return value


def _require_nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def load_canonical_policy_bundle(path: Path | str) -> CanonicalPolicyBundle:
    """Load the sole provider-neutral canonical bundle with content identity.

    Args:
        path: UTF-8 YAML path containing the canonical policy bundle.

    Returns:
        An immutable, revisioned canonical policy bundle.

    Raises:
        ValueError: If the document or accepted control set is malformed.
    """
    return canonical_policy_bundle_from_payload(_read_yaml(path))


def canonical_policy_bundle_from_payload(
    payload: dict[str, Any],
) -> CanonicalPolicyBundle:
    """Validate and construct the canonical bundle from its exact preimage.

    Args:
        payload: Complete canonical policy document decoded from YAML or JSON.

    Returns:
        An immutable, content-addressed canonical policy bundle.

    Raises:
        ValueError: If the document or accepted control set is malformed.
    """
    required_top = {
        "schema_version",
        "canonical_policy_bundle_id",
        "revision",
        "controls",
    }
    if set(payload) != required_top or payload["schema_version"] != "1.0.0":
        raise ValueError("canonical policy bundle fields are invalid")
    bundle_id = _require_nonempty_string(
        payload["canonical_policy_bundle_id"],
        "canonical_policy_bundle_id",
    )
    bundle_revision = _require_nonempty_string(payload["revision"], "revision")
    controls_payload = payload.get("controls")
    if not isinstance(controls_payload, dict) or set(controls_payload) != set(OPERATIONS):
        raise ValueError("canonical controls must equal the accepted control set")
    controls = []
    for control_id, item in sorted(controls_payload.items()):
        if isinstance(item, dict) and "revision" not in item:
            raise ValueError(f"control {control_id} revision is required")
        if (
            not isinstance(item, dict)
            or set(item) != {"revision", "semantic_class", "critical", "failure_mode"}
            or item["critical"] is not True
        ):
            raise ValueError(f"control {control_id} fields are invalid")
        revision = _require_nonempty_string(
            item["revision"],
            f"control {control_id} revision",
        )
        semantic_class = _require_nonempty_string(
            item["semantic_class"],
            f"control {control_id} semantic_class",
        )
        failure_mode = _require_nonempty_string(
            item["failure_mode"],
            f"control {control_id} failure_mode",
        )
        if failure_mode != "block":
            raise ValueError(f"control {control_id} failure_mode must be block")
        controls.append(
            Control(
                control_id=control_id,
                revision=revision,
                semantic_class=semantic_class,
                critical=item["critical"] is True,
                failure_mode=failure_mode,
            )
        )
    return CanonicalPolicyBundle(
        canonical_policy_bundle_id=bundle_id,
        revision=bundle_revision,
        content_hash=sha256_hex(canonical_bytes(payload)),
        controls=tuple(controls),
    )


def _require_sha(value: object, label: str) -> str:
    text = str(value)
    if re.fullmatch(r"[0-9a-f]{64}", text) is None:
        raise ValueError(f"{label} must be sha256")
    return text


def require_accepted_policy_control_applicability(
    applicability: PolicyControlApplicability,
    bundle: CanonicalPolicyBundle,
) -> None:
    """Validate a typed applicability object against the accepted D-G5-5 scope."""
    if not isinstance(applicability, PolicyControlApplicability):
        raise TypeError("typed PolicyControlApplicability required")
    if (
        applicability.applicability_id != f"pca_{ACCEPTED_DG55_APPLICABILITY_HASH}"
        or applicability.applicability_hash != ACCEPTED_DG55_APPLICABILITY_HASH
        or applicability.decision_ref != "D-G5-5"
        or applicability.decision_record_hash != ACCEPTED_DG55_DECISION_RECORD_HASH
        or (
            applicability.bundle_id,
            applicability.bundle_revision,
            applicability.bundle_hash,
        )
        != (
            bundle.canonical_policy_bundle_id,
            bundle.revision,
            bundle.content_hash,
        )
    ):
        raise ValueError("typed applicability differs from accepted D-G5-5 decision")
    expected = {
        item["control_id"]: (
            item["control_revision"],
            tuple(item["required_risk_tiers"]),
            tuple(item["required_operation_classes"]),
        )
        for item in ACCEPTED_DG55_DECISION_PAYLOAD["control_applicability"]
    }
    observed = {
        item.control_id: (
            item.control_revision,
            item.required_risk_tiers,
            item.required_operation_classes,
        )
        for item in applicability.controls
    }
    if len(observed) != len(applicability.controls) or observed != expected:
        raise ValueError("typed applicability controls differ from accepted D-G5-5 decision")


def load_policy_control_applicability(
    path: Path | str,
    *,
    bundle: CanonicalPolicyBundle,
) -> PolicyControlApplicability:
    """Load only the exact owner-approved, bundle-bound D-G5-5 mapping.

    Args:
        path: UTF-8 YAML path containing the applicability decision.
        bundle: Accepted canonical bundle that the decision must bind.

    Returns:
        Immutable, execution-bound policy-control applicability.

    Raises:
        ValueError: If schema identity, decision authority, hashes, selectors,
            or provider/control closure are unsupported or inconsistent.
    """
    return policy_control_applicability_from_payload(
        _read_yaml(path),
        bundle=bundle,
    )


def policy_control_applicability_from_payload(
    payload: dict[str, Any],
    *,
    bundle: CanonicalPolicyBundle,
) -> PolicyControlApplicability:
    """Validate D-G5-5 applicability from its exact canonical preimage.

    Args:
        payload: Complete applicability decision decoded from YAML or JSON.
        bundle: Accepted canonical bundle that the decision must bind.

    Returns:
        Immutable, execution-bound policy-control applicability.

    Raises:
        ValueError: If identity, authority, hashes, selectors, provider mapping,
            or provider/control closure are unsupported or inconsistent.
    """
    required_top = {
        "schema_id",
        "schema_version",
        "applicability_id",
        "applicability_hash",
        "decision_ref",
        "decision_payload",
        "decision_record_hash",
        "bundle",
        "controls",
    }
    if set(payload) != required_top:
        raise ValueError("applicability fields are incomplete or unexpected")
    if payload["schema_id"] != "ars://adapters/policy-control-applicability" or payload["schema_version"] != "1.0.0":
        raise ValueError("unsupported applicability schema")
    if payload["decision_ref"] != "D-G5-5":
        raise ValueError("decision_ref must be D-G5-5")
    if payload["decision_payload"] != ACCEPTED_DG55_DECISION_PAYLOAD:
        raise ValueError("accepted D-G5-5 decision payload mismatch")
    decision_hash = sha256_hex(canonical_bytes(payload["decision_payload"]))
    if decision_hash != ACCEPTED_DG55_DECISION_RECORD_HASH or payload["decision_record_hash"] != decision_hash:
        raise ValueError("decision_record_hash mismatch")
    binding = payload["bundle"]
    if binding != {
        "id": bundle.canonical_policy_bundle_id,
        "revision": bundle.revision,
        "hash": bundle.content_hash,
    }:
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
        expected_control_fields = {
            "control_id",
            "control_revision",
            "required_risk_tiers",
            "required_operation_classes",
            "provider_requirements",
        }
        if set(raw) != expected_control_fields:
            raise ValueError("control applicability has missing or unexpected fields")
        control_id = str(raw["control_id"])
        if control_id in seen or control_id not in OPERATIONS:
            raise ValueError("duplicate or unknown control")
        seen.add(control_id)
        if raw["control_revision"] != bundle_controls[control_id].revision:
            raise ValueError("stale control revision")
        risks = tuple(raw["required_risk_tiers"])
        operations = tuple(raw["required_operation_classes"])
        if (
            risks != RISK_TIERS
            or operations != OPERATIONS[control_id]
            or any("*" in item for item in (*risks, *operations))
        ):
            raise ValueError("risk tiers or required_operation_classes differ from D-G5-5")
        requirements = []
        raw_requirements = raw["provider_requirements"]
        if not isinstance(raw_requirements, list) or len(raw_requirements) != 2:
            raise ValueError("each control requires exactly two providers")
        provider_seen: set[str] = set()
        for req in raw_requirements:
            expected_fields = {
                "provider_variant",
                "variant_id",
                "fixture_id",
                "fixture_revision",
                "property",
                "json_pointer",
                "canonical_observed_value",
                "expected_observed_value_hash",
            }
            if not isinstance(req, dict) or set(req) != expected_fields:
                raise ValueError("provider requirement fields invalid")
            provider = str(req["provider_variant"])
            if provider in provider_seen or PROVIDERS.get(provider) != req["variant_id"]:
                raise ValueError("duplicate or incompatible provider selector")
            provider_seen.add(provider)
            if (
                req["fixture_id"] != "F-020"
                or req["fixture_revision"] != "r2"
                or req["property"] != "adapter_policy_parity"
                or req["json_pointer"] != f"/controls/{control_id}"
            ):
                raise ValueError("stale or incompatible F-020 selector")
            observed = req["canonical_observed_value"]
            if not isinstance(observed, dict) or tuple(sorted(observed.get("operations", {}))) != operations:
                raise ValueError("operation evidence does not close exactly")
            expected_hash = sha256_hex(
                canonical_bytes(
                    {
                        "property": req["property"],
                        "json_pointer": req["json_pointer"],
                        "canonical_observed_value": observed,
                    }
                )
            )
            if req["expected_observed_value_hash"] != expected_hash:
                raise ValueError("expected_observed_value_hash mismatch")
            requirements.append(
                ProviderEvidenceRequirement(
                    provider_variant=provider,
                    variant_id=str(req["variant_id"]),
                    fixture_id="F-020",
                    fixture_revision="r2",
                    property="adapter_policy_parity",
                    json_pointer=str(req["json_pointer"]),
                    canonical_observed_value=observed,
                    expected_observed_value_hash=expected_hash,
                )
            )
        controls.append(
            ControlApplicability(
                control_id=control_id,
                control_revision=str(raw["control_revision"]),
                required_risk_tiers=risks,
                required_operation_classes=operations,
                provider_requirements=tuple(sorted(requirements, key=lambda item: item.provider_variant)),
            )
        )
    outer_scope = [
        {
            "control_id": raw["control_id"],
            "control_revision": raw["control_revision"],
            "required_risk_tiers": raw["required_risk_tiers"],
            "required_operation_classes": raw["required_operation_classes"],
        }
        for raw in raw_controls
    ]
    if outer_scope != ACCEPTED_DG55_DECISION_PAYLOAD["control_applicability"]:
        raise ValueError("outer controls differ from accepted D-G5-5 decision")
    if seen != set(OPERATIONS):
        raise ValueError("missing canonical control")
    hash_payload = copy.deepcopy(payload)
    declared_hash = str(hash_payload.pop("applicability_hash"))
    hash_payload.pop("applicability_id")
    actual_hash = sha256_hex(canonical_bytes(hash_payload))
    if declared_hash != actual_hash or payload["applicability_id"] != f"pca_{actual_hash}":
        raise ValueError("applicability identity/hash mismatch")
    applicability = PolicyControlApplicability(
        applicability_id=str(payload["applicability_id"]),
        applicability_hash=actual_hash,
        decision_ref="D-G5-5",
        decision_record_hash=_require_sha(
            payload["decision_record_hash"],
            "decision_record_hash",
        ),
        bundle_id=bundle.canonical_policy_bundle_id,
        bundle_revision=bundle.revision,
        bundle_hash=bundle.content_hash,
        controls=tuple(sorted(controls, key=lambda item: item.control_id)),
    )
    require_accepted_policy_control_applicability(applicability, bundle)
    return applicability
