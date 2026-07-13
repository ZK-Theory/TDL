from pathlib import Path
from dataclasses import asdict
from dataclasses import replace

import pytest

from research_system.adapters.parity import build_parity_report
from research_system.adapters.parity_evidence import build_fake_adapter_parity_evidence
from research_system.canonical import jsonable
from research_system.errors import SchemaError
from research_system.evals.harness import run_p0_coverage
from research_system.policy.loader import load_canonical_policy_bundle, load_policy_control_applicability
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
POLICIES = ROOT / ".research-system" / "policies"


@pytest.fixture(scope="module")
def execution():
    return run_p0_coverage(
        EVALS / "p0-coverage.yaml",
        fixture_root=EVALS / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )


def test_real_typed_fake_evidence_closes_every_control_provider_pair(execution):
    assert execution.parity_report.passed is True
    assert execution.parity_report.blocking_controls == ()
    assert len(execution.parity_report.rows) == 4
    assert len(execution.parity_evidence) == 8
    payload = jsonable(asdict(execution.parity_report))
    payload.update(schema_id="ars://adapters/parity-report", schema_version="1.0.0")
    SchemaRegistry(ROOT / ".research-system" / "schemas").validate("ars://adapters/parity-report", payload)
    del payload["rows"][0]["control_revision"]
    with pytest.raises(SchemaError, match="control_revision"):
        SchemaRegistry(ROOT / ".research-system" / "schemas").validate("ars://adapters/parity-report", payload)


def test_plain_or_self_attested_manifest_is_rejected():
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    applicability = load_policy_control_applicability(
        POLICIES / "gate5-policy-control-applicability.yaml", bundle=bundle
    )
    with pytest.raises(TypeError, match="typed"):
        build_parity_report(bundle, applicability, ({"passed": True},))
    with pytest.raises(TypeError, match="typed"):
        build_fake_adapter_parity_evidence(({"disposition": "adapter_enforced"},), applicability, bundle)


def test_empty_applicability_cannot_produce_a_parity_percentage():
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    applicability = load_policy_control_applicability(
        POLICIES / "gate5-policy-control-applicability.yaml",
        bundle=bundle,
    )
    with pytest.raises(ValueError, match="at least one control"):
        build_parity_report(bundle, replace(applicability, controls=()), ())


def test_missing_or_diagnostic_critical_evidence_cannot_be_averaged_to_pass(execution):
    bundle = load_canonical_policy_bundle(POLICIES / "canonical-policy.yaml")
    missing = build_parity_report(bundle, execution.policy_applicability, execution.parity_evidence[:-1])
    assert missing.passed is False
    assert missing.diagnostic_percentage >= 75
    diagnostic = (
        *execution.parity_evidence[:-1],
        replace(execution.parity_evidence[-1], disposition="diagnostic_only"),
    )
    report = build_parity_report(bundle, execution.policy_applicability, diagnostic)
    assert report.passed is False
    assert report.blocking_controls
