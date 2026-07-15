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
    """One provider-specific execution binding required by D-G5-5.

    Attributes:
        provider_variant: Accepted fake provider adapter revision.
        variant_id: Exact matrix variant used for execution.
        fixture_id: Bound fixture identifier.
        fixture_revision: Bound fixture revision.
        property: Oracle property observed during execution.
        json_pointer: Pointer selecting the relevant control evidence.
        canonical_observed_value: Owner-accepted normalized evidence value.
        expected_observed_value_hash: Hash of the accepted observation.
    """

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
    """Accepted risk, operation, and provider scope for one control.

    Attributes:
        control_id: Canonical control identifier.
        control_revision: Accepted control revision.
        required_risk_tiers: Risk tiers to which the control applies.
        required_operation_classes: Exact covered operation classes.
        provider_requirements: Provider-specific execution bindings.
    """

    control_id: str
    control_revision: str
    required_risk_tiers: tuple[str, ...]
    required_operation_classes: tuple[str, ...]
    provider_requirements: tuple[ProviderEvidenceRequirement, ...]


@dataclass(frozen=True, slots=True)
class PolicyControlApplicability:
    """Owner-approved D-G5-5 applicability bound to a canonical bundle.

    Attributes:
        applicability_id: Content-addressed applicability identifier.
        applicability_hash: Hash of the accepted applicability document.
        decision_ref: Governing owner decision reference.
        decision_record_hash: Hash of the owner decision payload.
        bundle_id: Bound canonical policy bundle identifier.
        bundle_revision: Bound canonical policy bundle revision.
        bundle_hash: Bound canonical policy bundle hash.
        controls: Exact accepted control applicability records.
    """

    applicability_id: str
    applicability_hash: str
    decision_ref: str
    decision_record_hash: str
    bundle_id: str
    bundle_revision: str
    bundle_hash: str
    controls: tuple[ControlApplicability, ...]
