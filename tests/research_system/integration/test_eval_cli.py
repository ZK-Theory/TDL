import json
from pathlib import Path

from research_system.cli import main


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


def test_eval_validate_calibrate_run_and_release_commands(capsys, tmp_path):
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
    document = json.loads(output.read_text(encoding="utf-8"))

    manifest = tmp_path / "evaluation-runs.json"
    manifest.write_text(json.dumps(
        {"coverage": str(EVALS / "p0-coverage.yaml"), "decision_document": document}
    ), encoding="utf-8")
    assert main(["eval", "release", "--evaluation-runs", str(manifest)]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "blocked"


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
    assert payload["parity_status"] == "not_evaluated"
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


def test_eval_release_verifies_the_supplied_document(tmp_path, capsys):
    good = tmp_path / "runs.json"
    output = tmp_path / "decision.json"
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) == 0
    capsys.readouterr()
    document = json.loads(output.read_text(encoding="utf-8"))
    good.write_text(json.dumps(
        {"coverage": str(EVALS / "p0-coverage.yaml"), "decision_document": document}
    ), encoding="utf-8")
    assert main(["eval", "release", "--evaluation-runs", str(good)]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "blocked"

    forged = dict(document)
    forged["decision"] = "pass"
    bad = tmp_path / "forged.json"
    bad.write_text(json.dumps(
        {"coverage": str(EVALS / "p0-coverage.yaml"), "decision_document": forged}
    ), encoding="utf-8")
    assert main(["eval", "release", "--evaluation-runs", str(bad)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "blocked"
    assert out["reason"] == "evaluation_document_divergence"
