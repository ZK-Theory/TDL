import json
from pathlib import Path

from research_system.cli import main


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


def test_eval_validate_calibrate_run_and_release_commands(capsys, tmp_path):
    assert main(["eval", "validate", "--catalogue", str(EVALS / "catalogue.yaml")]) == 0
    assert json.loads(capsys.readouterr().out)["fixture_count"] == 37

    assert main(["eval", "calibrate", "--coverage", str(EVALS / "p0-coverage.yaml"), "--transport", "fake"]) == 0
    assert json.loads(capsys.readouterr().out)["fixture_count"] == 37

    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"), "--transport", "fake"]) == 0
    assert json.loads(capsys.readouterr().out)["candidate_status"] == "blocked"

    manifest = tmp_path / "evaluation-runs.json"
    manifest.write_text(json.dumps({"coverage": str(EVALS / "p0-coverage.yaml")}), encoding="utf-8")
    assert main(["eval", "release", "--evaluation-runs", str(manifest)]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "blocked"
