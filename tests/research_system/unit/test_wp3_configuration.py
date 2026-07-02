from pathlib import Path

import yaml

from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]


def test_wp3_schema_catalogue_is_complete_and_valid():
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    expected = {
        "ars://adapters/canonical-policy-bundle",
        "ars://adapters/capability-manifest",
        "ars://adapters/provider-command",
        "ars://adapters/provider-receipt",
        "ars://adapters/parity-report",
        "ars://operations/resource-request",
        "ars://operations/resource-grant",
        "ars://operations/execution-lease",
        "ars://operations/checkpoint-manifest",
        "ars://operations/stop-record",
        "ars://operations/recovery-evidence",
    }
    assert expected <= set(registry._schemas)


def test_canonical_policy_keeps_critical_controls_provider_neutral():
    policy = yaml.safe_load(
        (
            ROOT
            / ".research-system"
            / "policies"
            / "canonical-policy.yaml"
        ).read_text(encoding="utf-8")
    )
    assert policy["controls"]["no-shell"]["critical"] is True
    assert policy["controls"]["no-direct-event-write"]["critical"] is True


def test_provider_manifests_are_argument_arrays_and_live_disabled():
    for provider in ("claude", "codex"):
        manifest = yaml.safe_load(
            (
                ROOT
                / ".research-system"
                / "adapters"
                / f"{provider}.yaml"
            ).read_text(encoding="utf-8")
        )
        assert isinstance(manifest["argv"], list)
        assert manifest["live_enabled"] is False
