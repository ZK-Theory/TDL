"""A hash-consistent but semantically tampered oracle must fail closed."""

import json
import shutil
from pathlib import Path

import yaml

from research_system.canonical import sha256_hex
from research_system.evals.harness import decide_p0_release, run_p0_coverage

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
SCHEMAS = ROOT / ".research-system" / "schemas"


def _tamper_post_control(fixtures: Path, fixture_id: str) -> None:
    """Flip one expected value, then rewrite every dependent hash binding."""
    package = fixtures / fixture_id
    post_path = package / "expected" / "post-control.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    evidence = post["assertions"][0]["expected_evidence"]
    key = sorted(evidence)[0]
    evidence[key] = "tampered-value"
    post_path.write_bytes(json.dumps(post, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    source_path = package / "input" / "source-manifest.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["content_hashes"]["expected/post-control.json"] = sha256_hex(post_path.read_bytes())
    source_path.write_bytes(json.dumps(source, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    definition_path = package / "fixture.yaml"
    definition = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    definition["post_control_oracle_hash"] = sha256_hex(post_path.read_bytes())
    definition["known_good_reference_hash"] = sha256_hex(post_path.read_bytes())
    definition["source_manifest_hash"] = sha256_hex(source_path.read_bytes())
    definition_path.write_text(yaml.safe_dump(definition, sort_keys=False), encoding="utf-8")


def test_tampered_oracle_yields_fixture_error_and_blocked(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(EVALS / "fixtures", fixtures)
    coverage = tmp_path / "p0-coverage.yaml"
    coverage.write_text((EVALS / "p0-coverage.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    for policy in ("threshold-policies.yaml", "p0-calibration-policy.yaml"):
        (tmp_path / policy).write_bytes((EVALS / policy).read_bytes())
    _tamper_post_control(fixtures, "F-001")

    evidence = run_p0_coverage(
        coverage,
        fixture_root=fixtures,
        schema_root=SCHEMAS,
        variant_matrix_path=EVALS / "p0-variant-matrix.yaml",
        policy_root=ROOT / ".research-system" / "policies",
    )
    tampered = {r.verdict for r in evidence.results if r.fixture_id == "F-001"}
    assert "fixture_error" in tampered
    assert "pass" not in tampered
    assessment = decide_p0_release(evidence)
    assert assessment["decision"] == "blocked"
    assert any(r.fixture_id == "F-001" for r in assessment["blocking"])
