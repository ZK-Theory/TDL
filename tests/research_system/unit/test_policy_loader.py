from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from research_system.canonical import canonical_bytes, jsonable, sha256_hex
from research_system.errors import SchemaError
from research_system.policy.loader import (
    canonical_policy_bundle_from_payload,
    load_canonical_policy_bundle,
)
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / ".research-system" / "policies" / "canonical-policy.yaml"
INVALID_RAW_STRINGS = pytest.mark.parametrize(
    "invalid",
    (1, True, None, "", [], {}),
    ids=("integer", "boolean", "null", "empty", "list", "mapping"),
)


def _canonical_payload():
    return yaml.safe_load(POLICY.read_text(encoding="utf-8"))


def test_canonical_policy_loader_requires_revisioned_controls():
    bundle = load_canonical_policy_bundle(POLICY)
    assert tuple((item.control_id, item.revision) for item in bundle.controls) == (
        ("no-direct-event-write", "r1"),
        ("no-live-provider-by-default", "r1"),
        ("no-raw-transcript-retention", "r1"),
        ("no-shell", "r1"),
    )
    assert len(bundle.content_hash) == 64


def test_canonical_policy_payload_and_loader_preserve_exact_identity_and_hash():
    payload = _canonical_payload()
    constructed = canonical_policy_bundle_from_payload(payload)
    loaded = load_canonical_policy_bundle(POLICY)

    assert constructed == loaded
    assert constructed.canonical_policy_bundle_id == "cpb_p0_foundation"
    assert constructed.revision == "r1"
    assert constructed.content_hash == sha256_hex(canonical_bytes(payload))
    assert tuple(
        (
            item.control_id,
            item.revision,
            item.semantic_class,
            item.failure_mode,
        )
        for item in constructed.controls
    ) == (
        ("no-direct-event-write", "r1", "single_writer_boundary", "block"),
        ("no-live-provider-by-default", "r1", "provider_enablement", "block"),
        ("no-raw-transcript-retention", "r1", "privacy_retention", "block"),
        ("no-shell", "r1", "execution_boundary", "block"),
    )


@pytest.mark.parametrize("field", ("canonical_policy_bundle_id", "revision"))
@INVALID_RAW_STRINGS
def test_canonical_policy_payload_rejects_malformed_top_level_strings(field, invalid):
    payload = _canonical_payload()
    payload[field] = invalid

    with pytest.raises(ValueError, match=field):
        canonical_policy_bundle_from_payload(payload)


@pytest.mark.parametrize("field", ("revision", "semantic_class", "failure_mode"))
@INVALID_RAW_STRINGS
def test_canonical_policy_payload_rejects_malformed_control_strings(field, invalid):
    payload = _canonical_payload()
    payload["controls"]["no-shell"][field] = invalid

    with pytest.raises(ValueError, match=field):
        canonical_policy_bundle_from_payload(payload)


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
