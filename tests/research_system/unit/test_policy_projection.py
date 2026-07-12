from dataclasses import dataclass

from research_system.policy.compiler import compile_projection, projection_disposition
from research_system.policy.models import CanonicalPolicyBundle, Control


@dataclass(frozen=True)
class _Manifest:
    provider: str
    dispositions: dict[str, str]

    def disposition(self, control_id):
        return self.dispositions.get(control_id, "unsupported")


def _bundle():
    control = Control("no-shell", "r1", "execution_boundary", True, "block")
    return CanonicalPolicyBundle("cpb_" + "1" * 32, "r1", "a" * 64, (control,))


def test_richer_destination_is_not_overwritten_by_poorer_projection():
    existing = {
        "owner": "human",
        "semantic_controls": ["no-shell", "extra-review"],
    }
    assert projection_disposition(existing, _bundle()) == "divergent"


def test_generated_projection_binds_source_bundle_hash():
    projection = compile_projection(
        _bundle(), _Manifest("codex", {"no-shell": "supported"})
    )
    assert projection["metadata"]["canonical_policy_bundle_hash"] == "a" * 64
