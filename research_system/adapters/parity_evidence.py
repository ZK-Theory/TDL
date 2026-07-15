"""Content-addressed fake-adapter parity evidence from completed executions."""

from __future__ import annotations

from dataclasses import dataclass

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.models import GraderResult
from research_system.evals.variants import Gate5VariantRow, VariantExecutionEvidence
from research_system.policy.loader import require_accepted_policy_control_applicability
from research_system.policy.models import CanonicalPolicyBundle, PolicyControlApplicability


def _record_payload(record: FakeAdapterParityEvidence) -> dict:
    return {
        "bundle": [
            record.canonical_policy_bundle_id,
            record.canonical_policy_bundle_revision,
            record.canonical_policy_bundle_hash,
        ],
        "applicability_hash": record.applicability_hash,
        "control": [record.control_id, record.control_revision],
        "provider_variant": record.provider_variant,
        "variant_id": record.variant_id,
        "matrix_tuple": list(record.matrix_tuple),
        "execution_evidence_hash": record.execution_evidence_hash,
        "observed": [
            record.observed_property,
            record.observed_json_pointer,
            record.observed_value_hash,
        ],
        "grader_result_keys": [list(item) for item in record.grader_result_keys],
    }


@dataclass(frozen=True, slots=True, order=True)
class FakeAdapterParityEvidence:
    evidence_id: str
    evidence_hash: str
    canonical_policy_bundle_id: str
    canonical_policy_bundle_revision: str
    canonical_policy_bundle_hash: str
    applicability_hash: str
    control_id: str
    control_revision: str
    provider_variant: str
    variant_id: str
    matrix_tuple: tuple[object, ...]
    execution_evidence_hash: str
    observed_property: str
    observed_json_pointer: str
    observed_value_hash: str
    grader_result_keys: tuple[tuple[str, str, str, str, str, str], ...]
    disposition: str

    def __post_init__(self) -> None:
        digest = sha256_hex(canonical_bytes(_record_payload(self)))
        if self.disposition != "adapter_enforced":
            raise ValueError("fake evidence disposition must be adapter_enforced")
        if (
            self.evidence_hash != digest
            or self.evidence_id != f"fpe_{digest}"
            or len(self.matrix_tuple) != 11
            or self.variant_id != self.matrix_tuple[2]
            or self.grader_result_keys != tuple(sorted(self.grader_result_keys))
            or len(set(self.grader_result_keys)) != len(self.grader_result_keys)
        ):
            raise ValueError("fake parity evidence identity mismatch")


def _grader_binding(result: GraderResult) -> tuple[object, ...]:
    return (
        result.result_key,
        result.verdict,
        result.trace_hash,
        result.oracle_hash,
        result.policy_hash,
        result.threshold_policy_hash,
    )


def build_fake_adapter_parity_evidence(
    executions: tuple[VariantExecutionEvidence, ...],
    applicability: PolicyControlApplicability,
    bundle: CanonicalPolicyBundle,
    *,
    matrix_rows: tuple[Gate5VariantRow, ...],
    results: tuple[GraderResult, ...],
) -> tuple[FakeAdapterParityEvidence, ...]:
    """Close every D-G5-5 requirement from the exact matrix and release results."""
    if not all(isinstance(item, VariantExecutionEvidence) for item in executions):
        raise TypeError("typed VariantExecutionEvidence required")
    if not all(isinstance(item, Gate5VariantRow) for item in matrix_rows):
        raise TypeError("typed Gate5VariantRow required")
    if not all(isinstance(item, GraderResult) for item in results):
        raise TypeError("typed GraderResult required")
    require_accepted_policy_control_applicability(applicability, bundle)
    if len(matrix_rows) != 46 or len(executions) != 46:
        raise ValueError("exact 46-row matrix and execution closure required")
    if len(set(matrix_rows)) != 46:
        raise ValueError("duplicate expected matrix row")
    execution_rows = tuple(item.matrix_row for item in executions)
    if len(set(execution_rows)) != 46 or set(execution_rows) != set(matrix_rows):
        raise ValueError("missing, extra, or unrelated variant execution")
    if len(results) != 302 or len({item.result_key for item in results}) != 302:
        raise ValueError("exact 302 unique release results required")
    variant_results = tuple(item for item in results if item.variant_id != "baseline")
    if len(variant_results) != 170:
        raise ValueError("exact 170 variant release results required")
    row_selectors = {
        (item.fixture_id, item.fixture_revision, item.variant_id) for item in matrix_rows
    }
    if any(
        (item.fixture_id, item.fixture_revision, item.variant_id) not in row_selectors
        for item in variant_results
    ):
        raise ValueError("unrelated variant release result")
    by_selector: dict[tuple[str, str, str], list[GraderResult]] = {}
    for result in variant_results:
        by_selector.setdefault(
            (result.fixture_id, result.fixture_revision, result.variant_id), []
        ).append(result)
    for execution in executions:
        selector = (
            execution.matrix_row.fixture_id,
            execution.matrix_row.fixture_revision,
            execution.matrix_row.variant_id,
        )
        bound_results = tuple(sorted(by_selector.get(selector, ()), key=lambda item: item.result_key))
        expected_keys = tuple(item.result_key for item in bound_results)
        expected_bindings = tuple(_grader_binding(item) for item in bound_results)
        if (
            execution.grader_result_keys != expected_keys
            or execution.grader_result_bindings != expected_bindings
        ):
            raise ValueError("execution grader result binding mismatch")
        assertion_keys = tuple(
            (item.property, item.json_pointer) for item in execution.observed_assertions
        )
        if not assertion_keys or len(set(assertion_keys)) != len(assertion_keys):
            raise ValueError("missing or duplicate observed assertion evidence")

    by_variant = {
        (item.matrix_row.fixture_id, item.matrix_row.variant_id): item
        for item in executions
    }
    records = []
    for control in applicability.controls:
        for requirement in control.provider_requirements:
            execution = by_variant.get((requirement.fixture_id, requirement.variant_id))
            if (
                execution is None
                or execution.matrix_row.fixture_id != requirement.fixture_id
                or execution.matrix_row.fixture_revision != requirement.fixture_revision
                or execution.matrix_row.provider_variant != requirement.provider_variant
            ):
                raise ValueError("missing or incompatible bound execution evidence")
            matches = [
                item
                for item in execution.observed_assertions
                if item.property == requirement.property
                and item.json_pointer == requirement.json_pointer
            ]
            if len(matches) != 1:
                raise ValueError("missing or duplicate observed assertion evidence")
            observed = matches[0]
            if (
                observed.first_observed_value_hash
                != requirement.expected_observed_value_hash
                or observed.second_observed_value_hash
                != requirement.expected_observed_value_hash
            ):
                raise ValueError("observed assertion differs from owner comparator")
            operations = (
                observed.canonical_observed_value.get("operations", {})
                if isinstance(observed.canonical_observed_value, dict)
                else {}
            )
            if tuple(sorted(operations)) != control.required_operation_classes:
                raise ValueError("operation evidence does not close exactly")
            payload = {
                "bundle": [
                    bundle.canonical_policy_bundle_id,
                    bundle.revision,
                    bundle.content_hash,
                ],
                "applicability_hash": applicability.applicability_hash,
                "control": [control.control_id, control.control_revision],
                "provider_variant": requirement.provider_variant,
                "variant_id": requirement.variant_id,
                "matrix_tuple": list(execution.matrix_row.matrix_tuple),
                "execution_evidence_hash": execution.execution_evidence_hash,
                "observed": [
                    observed.property,
                    observed.json_pointer,
                    observed.first_observed_value_hash,
                ],
                "grader_result_keys": [list(item) for item in execution.grader_result_keys],
            }
            digest = sha256_hex(canonical_bytes(payload))
            records.append(
                FakeAdapterParityEvidence(
                    evidence_id=f"fpe_{digest}",
                    evidence_hash=digest,
                    canonical_policy_bundle_id=bundle.canonical_policy_bundle_id,
                    canonical_policy_bundle_revision=bundle.revision,
                    canonical_policy_bundle_hash=bundle.content_hash,
                    applicability_hash=applicability.applicability_hash,
                    control_id=control.control_id,
                    control_revision=control.control_revision,
                    provider_variant=requirement.provider_variant,
                    variant_id=requirement.variant_id,
                    matrix_tuple=execution.matrix_row.matrix_tuple,
                    execution_evidence_hash=execution.execution_evidence_hash,
                    observed_property=observed.property,
                    observed_json_pointer=observed.json_pointer,
                    observed_value_hash=observed.first_observed_value_hash,
                    grader_result_keys=execution.grader_result_keys,
                    disposition="adapter_enforced",
                )
            )
    if len(records) != 8:
        raise ValueError("exact eight fake parity evidence records required")
    return tuple(sorted(records))
