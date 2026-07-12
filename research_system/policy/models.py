"""Immutable canonical policy models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    control_id: str
    revision: str
    semantic_class: str
    critical: bool
    failure_mode: str


@dataclass(frozen=True)
class CanonicalPolicyBundle:
    canonical_policy_bundle_id: str
    revision: str
    content_hash: str
    controls: tuple[Control, ...]


@dataclass(frozen=True, slots=True)
class ProviderEvidenceRequirement:
    provider_variant: str
    variant_id: str
    fixture_id: str
    fixture_revision: str
    property: str
    json_pointer: str
    canonical_observed_value: dict
    expected_observed_value_hash: str


@dataclass(frozen=True, slots=True)
class ControlApplicability:
    control_id: str
    control_revision: str
    required_risk_tiers: tuple[str, ...]
    required_operation_classes: tuple[str, ...]
    provider_requirements: tuple[ProviderEvidenceRequirement, ...]


@dataclass(frozen=True, slots=True)
class PolicyControlApplicability:
    applicability_id: str
    applicability_hash: str
    decision_ref: str
    decision_record_hash: str
    bundle_id: str
    bundle_revision: str
    bundle_hash: str
    controls: tuple[ControlApplicability, ...]
