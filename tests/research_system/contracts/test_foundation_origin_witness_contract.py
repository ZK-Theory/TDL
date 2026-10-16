from pathlib import Path

import pytest
import yaml

from research_system.config import ApprovedProjectBinding


# This contract deliberately loads the operator's control store through the committed foundation.
# It is the check that caught the live store pinning a schema root inside a deleted disposable
# worktree (2026-10-02). Off the operator machine it cannot pass, so lanes there deselect it with
# -m "not live_store"; on the operator machine a failure is a real finding.
# Since the 06s Phase 5 re-pin (PR-F, P-058 P5-1/P5-2) the foundation names the fresh Gate 6 store
# reserved at A3; the WP6.4 store stays historical evidence. The load needs the control root, so
# this passes only once `store init` (runbook L6) has published that store.
@pytest.mark.live_store
def test_foundation_materializes_approved_external_control_and_origin() -> None:
    path = Path(__file__).resolve().parents[3] / ".research-system" / "config" / "foundation.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(value, dict)
    assert value["control_root"] == r"C:\Users\steph\TDL-ARS-G6-Control"
    assert value["origin_authority_root"] == r"C:\Users\steph\TDL-ARS-G6-Origin-Authority"
    assert value["origin_witness_path"] == (
        r"C:\Users\steph\TDL-ARS-G6-Origin-Authority\store-origins\sha256-"
        "200ee8f2ddb6ee387d208d57b8c427bb961ec3d7d0e021f53356fe0055095996.json"
    )
    assert value["origin_witness_sha256"] == ("1a7aa957917f20d537fbc99e23e23fc094f60e94906d80e4a2250577d7ffe7c4")
    assert value["code_roots"] == [r"C:\Users\steph\TDL-ARS-G6-Checkout"]

    approved = ApprovedProjectBinding.load(path)
    assert approved.control_root == Path(value["control_root"])
    assert approved.origin_witness.raw_sha256 == value["origin_witness_sha256"]
