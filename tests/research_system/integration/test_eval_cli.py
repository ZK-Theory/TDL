import json
from pathlib import Path

import pytest

from research_system.cli import main


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


def test_eval_validate_calibrate_and_run_commands(capsys, tmp_path):
    assert main(["eval", "validate", "--catalogue", str(EVALS / "catalogue.yaml")]) == 0
    assert json.loads(capsys.readouterr().out)["fixture_count"] == 40

    assert main(["eval", "calibrate", "--coverage", str(EVALS / "p0-coverage.yaml"), "--transport", "fake"]) == 0
    calibration = json.loads(capsys.readouterr().out)
    assert calibration["fixture_count"] == 40
    assert calibration["blocked_fixture_count"] == 15
    assert calibration["fixtures_with_uncalibrated_mutations"] == 0
    assert calibration["mutation_calibration"] == "calibrated"

    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"), "--transport", "fake"]) == 0
    assert json.loads(capsys.readouterr().out)["candidate_status"] == "blocked"

    output = tmp_path / "decision.json"
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) == 0
    capsys.readouterr()
    assert json.loads(output.read_text(encoding="utf-8"))["decision"] == "blocked"


def test_eval_calibrate_reports_real_mutation_calibration_status(capsys):
    assert main(["eval", "calibrate", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake"]) == 0
    payload = json.loads(capsys.readouterr().out)
    # Per-fixture mutations are actually executed (Tasks 1-3); the printed
    # top-level status must reflect the calibrate_fixture records rather
    # than a hardcoded constant.
    assert payload["mutation_calibration"] == "calibrated"
    assert payload["fixtures_with_uncalibrated_mutations"] == 0


def test_eval_run_persists_dated_schema_valid_decision(capsys, tmp_path):
    output = tmp_path / "release-gate-decision_2026-07-07.json"
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"] == "blocked"
    assert payload["operations_status"] == "pass"
    assert payload["parity_status"] == "pass"
    assert payload["policy_parity_report_id"].startswith("ppr_")
    assert payload["policy_control_applicability_id"].startswith("pca_")
    assert payload["release_gate_decision_id"].startswith("rgd_")
    assert payload["decided_at"].endswith("+00:00") or payload["decided_at"].endswith("Z")
    capsys.readouterr()


def test_eval_run_refuses_overwrite(tmp_path, capsys):
    output = tmp_path / "decision.json"
    output.write_text("{}", encoding="utf-8")
    # If cli.main maps ArsError to a nonzero exit code, assert on the return
    # value; if it propagates, replace this with pytest.raises(ArsError).
    # Either way the pre-existing file must be byte-identical afterwards.
    before = output.read_bytes()
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) != 0
    assert output.read_bytes() == before
    capsys.readouterr()


def test_eval_release_requires_canonical_control_binding(tmp_path, capsys):
    source = tmp_path / "decision.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        main(["eval", "release", "--evaluation-runs", str(source)])
    assert "--config" in capsys.readouterr().err
