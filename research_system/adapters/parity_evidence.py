"""Content-addressed fake-adapter parity evidence from completed executions."""

from __future__ import annotations

from dataclasses import dataclass

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.variants import VariantExecutionEvidence
from research_system.policy.models import CanonicalPolicyBundle, PolicyControlApplicability


@dataclass(frozen=True, slots=True, order=True)
class FakeAdapterParityEvidence:
    evidence_id: str
    evidence_hash: str
    control_id: str
    control_revision: str
    provider_variant: str
    variant_id: str
    execution_evidence_hash: str
    observed_property: str
    observed_json_pointer: str
    observed_value_hash: str
    grader_result_keys: tuple[tuple[str, str, str, str, str, str], ...]
    disposition: str


def build_fake_adapter_parity_evidence(
    executions: tuple[VariantExecutionEvidence, ...],
    applicability: PolicyControlApplicability,
    bundle: CanonicalPolicyBundle,
) -> tuple[FakeAdapterParityEvidence, ...]:
    """Close every D-G5-5 control/provider requirement from typed execution."""
    if not all(isinstance(item, VariantExecutionEvidence) for item in executions):
        raise TypeError("typed VariantExecutionEvidence required")
    if applicability.bundle_hash != bundle.content_hash:
        raise ValueError("applicability bundle mismatch")
    by_variant = {(item.matrix_row.fixture_id, item.matrix_row.variant_id): item for item in executions}
    if len(by_variant) != len(executions):
        raise ValueError("duplicate variant execution evidence")
    records = []
    for control in applicability.controls:
        for requirement in control.provider_requirements:
            execution = by_variant.get((requirement.fixture_id, requirement.variant_id))
            if execution is None or execution.matrix_row.fixture_id != requirement.fixture_id or execution.matrix_row.fixture_revision != requirement.fixture_revision or execution.matrix_row.provider_variant != requirement.provider_variant:
                raise ValueError("missing or incompatible bound execution evidence")
            matches = [item for item in execution.observed_assertions if item.property == requirement.property and item.json_pointer == requirement.json_pointer]
            if len(matches) != 1:
                raise ValueError("missing or duplicate observed assertion evidence")
            observed = matches[0]
            if observed.first_observed_value_hash != requirement.expected_observed_value_hash or observed.second_observed_value_hash != requirement.expected_observed_value_hash:
                raise ValueError("observed assertion differs from owner comparator")
            operations = observed.canonical_observed_value.get("operations", {}) if isinstance(observed.canonical_observed_value, dict) else {}
            if tuple(sorted(operations)) != control.required_operation_classes:
                raise ValueError("operation evidence does not close exactly")
            payload = {
                "bundle": [bundle.canonical_policy_bundle_id, bundle.revision, bundle.content_hash],
                "applicability_hash": applicability.applicability_hash,
                "control": [control.control_id, control.control_revision],
                "provider_variant": requirement.provider_variant,
                "matrix_tuple": list(execution.matrix_row.matrix_tuple),
                "execution_evidence_hash": execution.execution_evidence_hash,
                "observed": [observed.property, observed.json_pointer, observed.first_observed_value_hash],
                "grader_result_keys": [list(item) for item in execution.grader_result_keys],
            }
            digest = sha256_hex(canonical_bytes(payload))
            records.append(FakeAdapterParityEvidence(
                f"fpe_{digest}", digest, control.control_id, control.control_revision,
                requirement.provider_variant, requirement.variant_id,
                execution.execution_evidence_hash, observed.property,
                observed.json_pointer, observed.first_observed_value_hash,
                execution.grader_result_keys, "adapter_enforced",
            ))
    if len(records) != 8:
        raise ValueError("exact eight fake parity evidence records required")
    return tuple(sorted(records))
