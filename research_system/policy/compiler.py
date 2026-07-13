"""Deterministic policy projection with generated-ownership protection."""

from research_system.policy.models import CanonicalPolicyBundle


GENERATOR_VERSION = "ars-policy-projection-v1"


def compile_projection(bundle: CanonicalPolicyBundle, manifest) -> dict:
    """Compile sorted semantic controls for one provider manifest.

    Args:
        bundle: Revisioned canonical policy bundle to project.
        manifest: Provider manifest supplying each control disposition.

    Returns:
        A generated projection whose ``semantic_controls`` entries include
        ``control_id``, ``control_revision``, semantic class, disposition, and
        failure mode.
    """
    controls = [
        {
            "control_id": control.control_id,
            "control_revision": control.revision,
            "semantic_class": control.semantic_class,
            "disposition": manifest.disposition(control.control_id),
            "failure_mode": control.failure_mode,
        }
        for control in sorted(bundle.controls, key=lambda item: item.control_id)
    ]
    return {
        "metadata": {
            "owner": "generated",
            "generator_version": GENERATOR_VERSION,
            "canonical_policy_bundle_id": bundle.canonical_policy_bundle_id,
            "canonical_policy_bundle_hash": bundle.content_hash,
            "provider": manifest.provider,
        },
        "semantic_controls": controls,
    }


def projection_disposition(existing: dict, bundle: CanonicalPolicyBundle) -> str:
    """Permit replacement only for matching generated lineage without loss."""
    metadata = existing.get("metadata", {})
    if (
        metadata.get("owner") != "generated"
        or metadata.get("generator_version") != GENERATOR_VERSION
        or metadata.get("canonical_policy_bundle_id") != bundle.canonical_policy_bundle_id
        or metadata.get("canonical_policy_bundle_hash") != bundle.content_hash
    ):
        return "divergent"
    existing_ids = {
        item["control_id"] if isinstance(item, dict) else item for item in existing.get("semantic_controls", ())
    }
    projected_ids = {control.control_id for control in bundle.controls}
    if not existing_ids <= projected_ids:
        return "divergent"
    return "replaceable"
