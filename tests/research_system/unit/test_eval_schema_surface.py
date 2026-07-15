from pathlib import Path


SCHEMAS = Path(".research-system/schemas/evals")
ADAPTER_SCHEMAS = Path(".research-system/schemas/adapters")


def test_eval_schema_set_matches_the_w6_contract_surface():
    paths = sorted(SCHEMAS.glob("*.schema.json"))
    assert {path.name for path in paths} == {
        "coverage-manifest.schema.json",
        "deletion-verification-manifest.schema.json",
        "evidence-store-registry.schema.json",
        "evaluation-run.schema.json",
        "fixture-definition.schema.json",
        "fixture-grader-manifest.schema.json",
        "fixture-oracle.schema.json",
        "fixture-source-manifest.schema.json",
        "fixture-stimulus.schema.json",
        "fixture-trajectory.schema.json",
        "grader-result.schema.json",
        "release-gate-decision.schema.json",
        "release-control-binding.schema.json",
        "release-publication-evidence.schema.json",
        "release-publication-request.schema.json",
        "trace-envelope.schema.json",
        "variant-execution-evidence.schema.json",
    }


def test_policy_and_parity_schemas_close_nested_contracts():
    import json

    canonical = json.loads((ADAPTER_SCHEMAS / "canonical-policy-bundle.schema.json").read_text(encoding="utf-8"))
    control = canonical["properties"]["controls"]["items"]
    assert {"control_id", "revision", "semantic_class", "critical", "failure_mode"} == set(control["required"])
    assert control["additionalProperties"] is False

    applicability = json.loads(
        (ADAPTER_SCHEMAS / "policy-control-applicability.schema.json").read_text(encoding="utf-8")
    )
    assert applicability["properties"]["decision_payload"]["additionalProperties"] is False
    assert applicability["properties"]["bundle"]["additionalProperties"] is False
    assert applicability["properties"]["controls"]["items"]["additionalProperties"] is False

    parity = json.loads((ADAPTER_SCHEMAS / "parity-report.schema.json").read_text(encoding="utf-8"))
    assert parity["properties"]["rows"]["items"] == {"$ref": "#/$defs/row"}
    assert parity["$defs"]["row"]["additionalProperties"] is False
