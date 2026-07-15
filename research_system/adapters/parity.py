"""Typed W7 semantic parity reports with non-compensable critical controls."""

from __future__ import annotations

from dataclasses import dataclass

from research_system.adapters.parity_evidence import (
    FakeAdapterParityEvidence,
    build_fake_adapter_parity_evidence,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.models import GraderResult
from research_system.evals.variants import Gate5VariantRow, VariantExecutionEvidence
from research_system.policy.loader import require_accepted_policy_control_applicability
from research_system.policy.models import CanonicalPolicyBundle, PolicyControlApplicability


@dataclass(frozen=True, slots=True)
class PolicyParityReport:
    policy_parity_report_id: str
    report_hash: str
    canonical_policy_bundle_id: str
    canonical_policy_bundle_hash: str
    applicability_id: str
    applicability_hash: str
    rows: tuple[dict, ...]
    blocking_controls: tuple[str, ...]
    passed: bool
    diagnostic_percentage: int

    def __post_init__(self) -> None:
        payload = {
            "canonical_policy_bundle_id": self.canonical_policy_bundle_id,
            "canonical_policy_bundle_hash": self.canonical_policy_bundle_hash,
            "applicability_id": self.applicability_id,
            "applicability_hash": self.applicability_hash,
            "rows": list(self.rows),
            "blocking_controls": list(self.blocking_controls),
            "passed": self.passed,
            "diagnostic_percentage": self.diagnostic_percentage,
        }
        digest = sha256_hex(canonical_bytes(payload))
        control_ids = tuple(str(item.get("control_id")) for item in self.rows)
        derived_blockers = tuple(
            sorted(
                str(item.get("control_id"))
                for item in self.rows
                if item.get("consequence") == "blocked"
            )
        )
        expected_percentage = int(
            100 * (len(self.rows) - len(derived_blockers)) / len(self.rows)
        ) if self.rows else 0
        if (
            self.report_hash != digest
            or self.policy_parity_report_id != f"ppr_{digest}"
            or len(self.rows) != 4
            or len(set(control_ids)) != 4
            or self.blocking_controls != derived_blockers
            or self.passed != (not derived_blockers)
            or self.diagnostic_percentage != expected_percentage
        ):
            raise ValueError("parity report identity or closure mismatch")


def build_parity_report(
    bundle: CanonicalPolicyBundle,
    applicability: PolicyControlApplicability,
    evidence_records: tuple[FakeAdapterParityEvidence, ...],
    *,
    executions: tuple[VariantExecutionEvidence, ...],
    matrix_rows: tuple[Gate5VariantRow, ...],
    results: tuple[GraderResult, ...],
) -> PolicyParityReport:
    """Compute a report only from exact typed D-G5-5 evidence closure."""
    if (
        not isinstance(bundle, CanonicalPolicyBundle)
        or not isinstance(applicability, PolicyControlApplicability)
        or not all(isinstance(item, FakeAdapterParityEvidence) for item in evidence_records)
    ):
        raise TypeError("typed bundle, applicability, and fake parity evidence required")
    if not applicability.controls:
        raise ValueError("applicability requires at least one control")
    require_accepted_policy_control_applicability(applicability, bundle)
    derived_records = build_fake_adapter_parity_evidence(
        executions,
        applicability,
        bundle,
        matrix_rows=matrix_rows,
        results=results,
    )
    derived_by_pair = {
        (item.control_id, item.provider_variant): item for item in derived_records
    }
    expected = {
        (control.control_id, req.provider_variant)
        for control in applicability.controls
        for req in control.provider_requirements
    }
    observed = {(item.control_id, item.provider_variant) for item in evidence_records}
    if len(observed) != len(evidence_records) or not observed <= expected:
        raise ValueError("duplicate or unexpected parity evidence")
    requirements = {
        (control.control_id, requirement.provider_variant): (control, requirement)
        for control in applicability.controls
        for requirement in control.provider_requirements
    }
    for item in evidence_records:
        item.__post_init__()
        if derived_by_pair.get((item.control_id, item.provider_variant)) != item:
            raise ValueError("parity evidence differs from execution-derived evidence")
        control, requirement = requirements[(item.control_id, item.provider_variant)]
        if (
            item.canonical_policy_bundle_id != bundle.canonical_policy_bundle_id
            or item.canonical_policy_bundle_revision != bundle.revision
            or item.canonical_policy_bundle_hash != bundle.content_hash
            or item.applicability_hash != applicability.applicability_hash
            or item.control_revision != control.control_revision
            or item.variant_id != requirement.variant_id
            or item.observed_property != requirement.property
            or item.observed_json_pointer != requirement.json_pointer
            or item.observed_value_hash != requirement.expected_observed_value_hash
            or item.matrix_tuple[0] != requirement.fixture_id
            or item.matrix_tuple[1] != requirement.fixture_revision
            or item.matrix_tuple[2] != requirement.variant_id
            or item.matrix_tuple[3] != requirement.provider_variant
        ):
            raise ValueError("parity evidence binding mismatch")
    by_pair = {(item.control_id, item.provider_variant): item for item in evidence_records}
    rows = []
    blocking = []
    for control in applicability.controls:
        providers = {}
        evidence = {}
        for requirement in control.provider_requirements:
            item = by_pair.get((control.control_id, requirement.provider_variant))
            providers[requirement.provider_variant] = item.disposition if item else "unsupported"
            evidence[requirement.provider_variant] = [item.evidence_id, item.evidence_hash] if item else []
        is_blocked = any(value in {"unsupported", "divergent", "diagnostic_only"} for value in providers.values())
        if is_blocked:
            blocking.append(control.control_id)
        rows.append(
            {
                "control_id": control.control_id,
                "control_revision": control.control_revision,
                "required_risk_tiers": list(control.required_risk_tiers),
                "required_operation_classes": list(control.required_operation_classes),
                "providers": providers,
                "evidence": evidence,
                "consequence": "blocked" if is_blocked else "eligible",
                "owner_resume_condition": "replace missing or divergent typed evidence" if is_blocked else "none",
            }
        )
    report_payload = {
        "canonical_policy_bundle_id": bundle.canonical_policy_bundle_id,
        "canonical_policy_bundle_hash": bundle.content_hash,
        "applicability_id": applicability.applicability_id,
        "applicability_hash": applicability.applicability_hash,
        "rows": rows,
        "blocking_controls": sorted(blocking),
        "passed": not blocking,
        "diagnostic_percentage": int(100 * (len(rows) - len(blocking)) / len(rows)),
    }
    digest = sha256_hex(canonical_bytes(report_payload))
    return PolicyParityReport(
        f"ppr_{digest}",
        digest,
        bundle.canonical_policy_bundle_id,
        bundle.content_hash,
        applicability.applicability_id,
        applicability.applicability_hash,
        tuple(rows),
        tuple(sorted(blocking)),
        not blocking,
        report_payload["diagnostic_percentage"],
    )
