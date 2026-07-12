from dataclasses import asdict
from pathlib import Path

import pytest

from research_system.canonical import jsonable
from research_system.errors import SchemaError
from research_system.policy.loader import load_canonical_policy_bundle
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / ".research-system" / "policies" / "canonical-policy.yaml"


def test_canonical_policy_loader_requires_revisioned_controls():
    bundle = load_canonical_policy_bundle(POLICY)
    assert tuple((item.control_id, item.revision) for item in bundle.controls) == (
        ("no-direct-event-write", "r1"),
        ("no-live-provider-by-default", "r1"),
        ("no-raw-transcript-retention", "r1"),
        ("no-shell", "r1"),
    )
    assert len(bundle.content_hash) == 64


def test_canonical_policy_loader_rejects_missing_control_revision(tmp_path):
    text = POLICY.read_text(encoding="utf-8").replace("    revision: r1\n", "", 1)
    path = tmp_path / "canonical-policy.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="revision"):
        load_canonical_policy_bundle(path)


def test_canonical_policy_schema_requires_every_loader_consumed_control_field():
    payload = jsonable(asdict(load_canonical_policy_bundle(POLICY)))
    payload.update(schema_id="ars://adapters/canonical-policy-bundle", schema_version="1.0.0")
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    registry.validate("ars://adapters/canonical-policy-bundle", payload)
    del payload["controls"][0]["semantic_class"]
    with pytest.raises(SchemaError, match="semantic_class"):
        registry.validate("ars://adapters/canonical-policy-bundle", payload)
