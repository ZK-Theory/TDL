import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import research_system.cli as cli
from research_system.cli import main
from research_system.errors import ArsError


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


@pytest.mark.parametrize(
    ("field", "value"),
    (("content_sha256", []), ("task_id", None), ("accepted_scope", {})),
)
def test_release_publication_context_rejects_malformed_authority_fields(monkeypatch, tmp_path, field, value):
    """Remediation-red: replay evidence is decoded without string coercion."""

    stream = {
        "content_sha256": "a" * 64,
        "manifest": {"task_id": "tsk_valid", "authority": {"accepted_scope": "release:valid"}},
    }
    if field == "content_sha256":
        stream[field] = value
    elif field == "task_id":
        stream["manifest"][field] = value
    else:
        stream["manifest"]["authority"][field] = value
    monkeypatch.setattr(
        cli, "EventLedger", lambda *_args, **_kwargs: SimpleNamespace(snapshot=lambda: SimpleNamespace(events=()))
    )
    monkeypatch.setattr(
        cli,
        "LedgerAuthorityGrantResolver",
        lambda *_args, **_kwargs: SimpleNamespace(validate_replayed_administration_state=lambda _state: None),
    )
    monkeypatch.setattr(cli, "replay", lambda *_args, **_kwargs: {"streams": {"art_evidence": stream}})
    binding = SimpleNamespace(
        control_root=tmp_path,
        project_id="prj_valid",
        store_identity="store_valid",
        origin_witness=object(),
        origin_witness_path=tmp_path / "witness.json",
    )
    resolve = cli._publication_context_for_reference(binding, object(), datetime(2026, 8, 1, tzinfo=UTC))

    with pytest.raises(ArsError, match="field is invalid"):
        resolve("art_evidence")


def test_release_publication_context_uses_one_authority_validated_snapshot(monkeypatch, tmp_path):
    calls = {"snapshot": 0, "replay": 0, "validated": 0}
    streams = {
        reference: {
            "content_sha256": digest * 64,
            "manifest": {"task_id": f"tsk_{reference}", "authority": {"accepted_scope": "release:valid"}},
        }
        for reference, digest in (("art_one", "a"), ("art_two", "b"))
    }

    def snapshot():
        calls["snapshot"] += 1
        return SimpleNamespace(events=(object(),))

    def validate(_state):
        calls["validated"] += 1

    def replay(_events, **kwargs):
        calls["replay"] += 1
        kwargs["authority_state_validator"]({"authority": "checked"})
        return {"streams": streams}

    monkeypatch.setattr(cli, "EventLedger", lambda *_args, **_kwargs: SimpleNamespace(snapshot=snapshot))
    monkeypatch.setattr(
        cli,
        "LedgerAuthorityGrantResolver",
        lambda *_args, **_kwargs: SimpleNamespace(validate_replayed_administration_state=validate),
    )
    monkeypatch.setattr(cli, "replay", replay)
    binding = SimpleNamespace(
        control_root=tmp_path,
        project_id="prj_valid",
        store_identity="store_valid",
        origin_witness=object(),
        origin_witness_path=tmp_path / "witness.json",
    )

    resolve = cli._publication_context_for_reference(binding, object(), datetime(2026, 8, 1, tzinfo=UTC))
    assert resolve("art_one").exact_content_sha256 == "a" * 64
    assert resolve("art_two").exact_content_sha256 == "b" * 64
    assert calls == {"snapshot": 1, "replay": 1, "validated": 1}


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
    assert (
        main(
            [
                "eval",
                "run",
                "--coverage",
                str(EVALS / "p0-coverage.yaml"),
                "--transport",
                "fake",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert json.loads(output.read_text(encoding="utf-8"))["decision"] == "blocked"


def test_eval_calibrate_reports_real_mutation_calibration_status(capsys):
    assert main(["eval", "calibrate", "--coverage", str(EVALS / "p0-coverage.yaml"), "--transport", "fake"]) == 0
    payload = json.loads(capsys.readouterr().out)
    # Per-fixture mutations are actually executed (Tasks 1-3); the printed
    # top-level status must reflect the calibrate_fixture records rather
    # than a hardcoded constant.
    assert payload["mutation_calibration"] == "calibrated"
    assert payload["fixtures_with_uncalibrated_mutations"] == 0


def test_eval_run_persists_dated_schema_valid_decision(capsys, tmp_path):
    output = tmp_path / "release-gate-decision_2026-07-07.json"
    assert (
        main(
            [
                "eval",
                "run",
                "--coverage",
                str(EVALS / "p0-coverage.yaml"),
                "--transport",
                "fake",
                "--output",
                str(output),
            ]
        )
        == 0
    )
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
    assert (
        main(
            [
                "eval",
                "run",
                "--coverage",
                str(EVALS / "p0-coverage.yaml"),
                "--transport",
                "fake",
                "--output",
                str(output),
            ]
        )
        != 0
    )
    assert output.read_bytes() == before
    capsys.readouterr()


def test_eval_release_requires_canonical_control_binding(tmp_path, capsys):
    source = tmp_path / "decision.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        main(["eval", "release", "--evaluation-runs", str(source)])
    assert "--config" in capsys.readouterr().err
