import pytest

from research_system.adapters.parity_evidence import FakeAdapterParityEvidence


def test_typed_fake_evidence_rejects_caller_supplied_identity_and_bindings():
    with pytest.raises(ValueError, match="evidence identity"):
        FakeAdapterParityEvidence(
            evidence_id="fpe_" + "0" * 64,
            evidence_hash="0" * 64,
            canonical_policy_bundle_id="cpb_p0_foundation",
            canonical_policy_bundle_revision="r1",
            canonical_policy_bundle_hash="0" * 64,
            applicability_hash="0" * 64,
            control_id="no-shell",
            control_revision="r1",
            provider_variant="fake-claude-adapter-v1",
            variant_id="fake-claude-adapter-v1-windows-fake-transport",
            matrix_tuple=(
                "F-020",
                "r2",
                "fake-claude-adapter-v1-windows-fake-transport",
                "fake-claude-adapter-v1",
                "fake-runtime-v1",
                "windows",
                "fake",
                "gate5",
                None,
                None,
                None,
            ),
            execution_evidence_hash="0" * 64,
            observed_property="adapter_policy_parity",
            observed_json_pointer="/controls/no-shell",
            observed_value_hash="0" * 64,
            grader_result_keys=(),
            disposition="adapter_enforced",
        )
