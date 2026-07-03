from dataclasses import dataclass

from research_system.adapters.parity import build_parity_report
from research_system.policy.models import CanonicalPolicyBundle, Control


@dataclass(frozen=True)
class _Manifest:
    provider: str
    dispositions: dict[str, str]

    def disposition(self, control_id):
        return self.dispositions.get(control_id, "unsupported")


def _bundle():
    control = Control("no-shell", "execution_boundary", True, "block")
    return CanonicalPolicyBundle("cpb_" + "1" * 32, "r1", "a" * 64, (control,))


def test_critical_control_missing_from_codex_blocks_parity():
    report = build_parity_report(_bundle(), [_Manifest("codex", {})])
    assert report == {
        "rows": [
            {
                "control_id": "no-shell",
                "providers": {"claude": "unsupported", "codex": "unsupported"},
            }
        ],
        "blocking_controls": ["no-shell"],
        "passed": False,
    }


def test_missing_required_provider_cannot_pass_parity():
    report = build_parity_report(
        _bundle(), [_Manifest("claude", {"no-shell": "supported"})]
    )
    assert report["passed"] is False
    assert report["rows"][0]["providers"]["codex"] == "unsupported"


def test_byte_difference_with_equivalent_semantics_can_pass():
    manifests = [
        _Manifest("codex", {"no-shell": "supported"}),
        _Manifest("claude", {"no-shell": "supported"}),
    ]
    assert build_parity_report(_bundle(), manifests)["passed"] is True
