from pathlib import Path

import pytest
import yaml

from research_system.errors import SchemaError
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

@pytest.mark.parametrize(
    'field',
    [
        'design_hash',
        'code_hash',
        'environment_hash',
        'representation_hash',
        'parameters_hash',
        'rng_state_hash',
        'payload_hash',
    ],
)
def test_checkpoint_manifest_rejects_malformed_hashes(field):
    manifest = {
        'schema_id': 'ars://operations/checkpoint-manifest',
        'schema_version': '1.0.0',
        'checkpoint_manifest_id': 'cpm_' + '1' * 32,
        'attempt_id': 'att_' + '2' * 32,
        'execution_epoch': 1,
        'design_hash': 'a' * 64,
        'code_hash': 'b' * 64,
        'environment_hash': 'c' * 64,
        'input_hashes': ['d' * 64],
        'representation_hash': 'e' * 64,
        'parameters_hash': 'f' * 64,
        'rng_algorithm': 'PCG64',
        'rng_state_hash': '1' * 64,
        'completed_work_units': [0],
        'payload_hash': '2' * 64,
    }
    manifest[field] = 'not-a-hash'
    with pytest.raises(SchemaError, match=field):
        SchemaRegistry(ROOT / '.research-system' / 'schemas').validate(
            'ars://operations/checkpoint-manifest', manifest
        )


def test_checkpoint_manifest_rejects_malformed_input_hash():
    manifest = {
        'schema_id': 'ars://operations/checkpoint-manifest',
        'schema_version': '1.0.0',
        'checkpoint_manifest_id': 'cpm_' + '1' * 32,
        'attempt_id': 'att_' + '2' * 32,
        'execution_epoch': 1,
        'design_hash': 'a' * 64,
        'code_hash': 'b' * 64,
        'environment_hash': 'c' * 64,
        'input_hashes': ['not-a-hash'],
        'representation_hash': 'e' * 64,
        'parameters_hash': 'f' * 64,
        'rng_algorithm': 'PCG64',
        'rng_state_hash': '1' * 64,
        'completed_work_units': [0],
        'payload_hash': '2' * 64,
    }
    with pytest.raises(SchemaError, match='input_hashes'):
        SchemaRegistry(ROOT / '.research-system' / 'schemas').validate(
            'ars://operations/checkpoint-manifest', manifest
        )
