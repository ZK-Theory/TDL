from pathlib import Path

import yaml


def test_foundation_declares_unmaterialized_external_origin_pins() -> None:
    path = Path(__file__).resolve().parents[3] / ".research-system" / "config" / "foundation.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(value, dict)
    assert value["origin_authority_root"] is None
    assert value["origin_witness_path"] is None
    assert value["origin_witness_sha256"] is None
