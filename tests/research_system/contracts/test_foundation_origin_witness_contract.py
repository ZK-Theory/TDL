from pathlib import Path

import yaml

from research_system.config import ApprovedProjectBinding


def test_foundation_materializes_approved_external_control_and_origin() -> None:
    path = Path(__file__).resolve().parents[3] / ".research-system" / "config" / "foundation.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(value, dict)
    assert value["control_root"] == r"C:\Users\steph\TDL-ARS-WP64-Control"
    assert value["origin_authority_root"] == r"C:\Users\steph\TDL-ARS-WP64-Origin-Authority"
    assert value["origin_witness_path"] == (
        r"C:\Users\steph\TDL-ARS-WP64-Origin-Authority\store-origins\sha256-"
        "f309842fa91a1b79aa22daf695c5cf581243a9a45f8bdf949b74843d576df18c.json"
    )
    assert value["origin_witness_sha256"] == ("1e565f988983e505802c779e4a02e5655e9c84e93ab02ddba4308deb02a417fa")

    approved = ApprovedProjectBinding.load(path)
    assert approved.control_root == Path(value["control_root"])
    assert approved.origin_witness.raw_sha256 == value["origin_witness_sha256"]
