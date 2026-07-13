from pathlib import Path

import pytest
import yaml

from research_system.errors import SchemaError
from research_system.policy.loader import load_canonical_policy_bundle, load_policy_control_applicability
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / ".research-system" / "policies" / "canonical-policy.yaml"
APPLICABILITY = ROOT / ".research-system" / "policies" / "gate5-policy-control-applicability.yaml"

EXPECTED_OPERATIONS = {
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


def test_dg55_source_is_exact_decision_and_execution_bound():
    bundle = load_canonical_policy_bundle(POLICY)
    applicability = load_policy_control_applicability(APPLICABILITY, bundle=bundle)
    assert applicability.decision_ref == "D-G5-5"
    assert applicability.bundle_hash == bundle.content_hash
    assert len(applicability.controls) == 4
    for control in applicability.controls:
        assert control.required_risk_tiers == ("R0", "R1", "R2", "R3")
        assert control.required_operation_classes == EXPECTED_OPERATIONS[control.control_id]
        assert len(control.provider_requirements) == 2
        assert {item.fixture_revision for item in control.provider_requirements} == {"r2"}


def test_dg55_source_rejects_semantic_class_substitution(tmp_path):
    bundle = load_canonical_policy_bundle(POLICY)
    head, controls = APPLICABILITY.read_text(encoding="utf-8").split("\ncontrols:\n", 1)
    text = head + "\ncontrols:\n" + controls.replace("required_operation_classes:", "semantic_class:", 1)
    path = tmp_path / "applicability.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="required_operation_classes"):
        load_policy_control_applicability(path, bundle=bundle)


def test_dg55_source_rejects_unsupported_schema_version(tmp_path):
    bundle = load_canonical_policy_bundle(POLICY)
    payload = yaml.safe_load(APPLICABILITY.read_text(encoding="utf-8"))
    payload["schema_version"] = "2.0.0"
    path = tmp_path / "applicability.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported applicability schema"):
        load_policy_control_applicability(path, bundle=bundle)


def test_dg55_schema_rejects_unbound_nested_objects():
    payload = yaml.safe_load(APPLICABILITY.read_text(encoding="utf-8"))
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    registry.validate("ars://adapters/policy-control-applicability", payload)
    payload["bundle"]["unexpected"] = True
    with pytest.raises(SchemaError, match="unexpected"):
        registry.validate("ars://adapters/policy-control-applicability", payload)
