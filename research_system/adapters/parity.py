"""Typed W7 semantic parity reports with non-compensable critical controls."""

from __future__ import annotations

from dataclasses import dataclass

from research_system.adapters.parity_evidence import FakeAdapterParityEvidence
from research_system.canonical import canonical_bytes, sha256_hex
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


def build_parity_report(
    bundle: CanonicalPolicyBundle,
    applicability: PolicyControlApplicability,
    evidence_records: tuple[FakeAdapterParityEvidence, ...],
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
    expected = {
        (control.control_id, req.provider_variant)
        for control in applicability.controls
        for req in control.provider_requirements
    }
    observed = {(item.control_id, item.provider_variant) for item in evidence_records}
    if len(observed) != len(evidence_records) or not observed <= expected:
        raise ValueError("duplicate or unexpected parity evidence")
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
