"""Public eval CLI contract without runtime repository writes."""

import json

import pytest

from research_system.cli import main
from research_system.evals.harness import (
    run_p0_coverage,
    write_external_output,
)

CATALOGUE = '.research-system/evals/catalogue.yaml'
COVERAGE = '.research-system/evals/p0-coverage.yaml'


def _printed(capsys):
    return json.loads(capsys.readouterr().out)


def test_eval_validate_reports_exact_catalogue(capsys):
    assert main(['eval', 'validate', '--catalogue', CATALOGUE]) == 0
    assert _printed(capsys) == {
        'catalogue_revision': 'p0-catalogue-v1',
        'fixtures': 37,
        'status': 'valid',
    }


def test_eval_calibrate_uses_only_fake_transport(capsys):
    assert main(['eval', 'calibrate', '--coverage', COVERAGE, '--transport', 'fake']) == 0
    result = _printed(capsys)
    assert result['fixtures'] == 37
    assert result['repetitions'] == 2
    assert result['status'] == 'blocked'


def test_eval_run_reports_blocking_non_pass(capsys):
    assert main(['eval', 'run', '--coverage', COVERAGE, '--transport', 'fake']) == 0
    result = _printed(capsys)
    assert result['fixture_count'] == 37
    assert result['candidate_status'] == 'blocked'
    assert result['scenario_count'] == 5
def test_eval_release_serializes_immutable_decision_as_canonical_json(
    tmp_path,
    capsys,
):
    run_path = tmp_path / 'p0-run_2026-07-03.json'
    write_external_output(run_path, run_p0_coverage())
    assert main(
        [
            'eval',
            'release',
            '--evaluation-runs',
            str(run_path),
        ]
    ) == 0
    result = _printed(capsys)
    assert result['decision']['decision'] == 'blocked'
    assert result['missing'] == []
    assert result['gate5_authorized'] is False




def test_eval_rejects_non_fake_transport():
    with pytest.raises(SystemExit):
        main(['eval', 'run', '--coverage', COVERAGE, '--transport', 'live'])
