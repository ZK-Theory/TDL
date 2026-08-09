from pathlib import Path

import yaml

from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]


def test_wp2_schema_catalogue_is_complete_and_valid():
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    expected = {
        "ars://context/context-candidate",
        "ars://context/context-manifest",
        "ars://assurance/assurance-requirement",
        "ars://routing/model-eval-profile",
        "ars://routing/route-request",
        "ars://routing/route-decision",
        "ars://routing/route-failure",
    }
    assert expected <= {schema_id for schema_id, _version in registry._schemas}


def test_context_profiles_and_risk_policy_match_owner_contracts():
    context = yaml.safe_load(
        (ROOT / ".research-system" / "policies" / "context-profiles.yaml").read_text(encoding="utf-8")
    )
    assert context["reference_limits"] == {
        "R0": 8000,
        "R1": 16000,
        "R2": 32000,
        "R3": 48000,
    }
    risk = yaml.safe_load(
        (ROOT / ".research-system" / "policies" / "risk-and-independence.yaml").read_text(encoding="utf-8")
    )
    assert risk["risk_order"] == ["R0", "R1", "R2", "R3"]
    assert risk["independence_order"] == ["I0", "I1", "I2", "I3"]


def test_core_assurance_pack_uses_exact_six_lanes():
    pack = yaml.safe_load((ROOT / ".research-system" / "packs" / "core-assurance.yaml").read_text(encoding="utf-8"))
    assert set(pack["lanes"]) == {
        "topology",
        "stochastic_null",
        "statistical_panel",
        "representation",
        "output_provenance",
        "paper_claim",
    }
