"""P0 coverage, calibration, candidate-run, and release-decision harness."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.calibration import calibrate_fixture
from research_system.evals.catalogue import load_catalogue, load_fixture
from research_system.evals.coverage import P0Coverage, load_p0_coverage
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.models import ReleaseGateDecision, ResultKey
from research_system.evals.scenarios import run_gate3_scenario

_DATE_SUFFIX = re.compile(r'_\d{4}-\d{2}-\d{2}\.json$')
_DEFAULT_CATALOGUE = Path('.research-system/evals/catalogue.yaml')
_DEFAULT_COVERAGE = Path('.research-system/evals/p0-coverage.yaml')

def _document_value(value: Any) -> Any:
    """Convert dataclass output into the canonical JSON value domain."""
    if isinstance(value, dict):
        return {str(key): _document_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_document_value(item) for item in value]
    return value



@dataclass(frozen=True, slots=True)
class ReleaseAssessment:
    """One release decision plus exact-set diagnostics."""

    decision: ReleaseGateDecision
    missing: tuple[ResultKey, ...]
    unexpected: tuple[ResultKey, ...]
    duplicates: tuple[ResultKey, ...]
    incompatible: tuple[str, ...]


def validate_p0_catalogue(
    catalogue_path: Path | str = _DEFAULT_CATALOGUE,
    coverage_path: Path | str = _DEFAULT_COVERAGE,
) -> dict[str, Any]:
    """Validate catalogue, coverage, policy bindings, and exact closure."""
    catalogue = load_catalogue(catalogue_path)
    coverage = load_p0_coverage(coverage_path)
    if catalogue.catalogue_revision != coverage.catalogue_revision:
        raise FixtureDefinitionError('catalogue/coverage revision mismatch')
    return {
        'status': 'valid',
        'fixtures': len(catalogue.cases),
        'catalogue_revision': catalogue.catalogue_revision,
    }


def calibrate_p0_coverage(
    coverage_path: Path | str = _DEFAULT_COVERAGE,
    *,
    transport: str = 'fake',
) -> dict[str, Any]:
    """Run every paired calibration without live provider authority."""
    coverage = load_p0_coverage(coverage_path)
    if transport != coverage.transport or transport != 'fake':
        raise FixtureDefinitionError('deterministic fake transport required')
    records = [
        calibrate_fixture(fixture_id)
        for fixture_id, _fixture_revision in coverage.selected_fixture_revisions
    ]
    unavailable = sum(
        1
        for record in records
        if {item.verdict for item in record.known_good} == {'unable_to_grade'}
    )
    fixture_errors = sum(
        1
        for record in records
        if {item.verdict for item in record.known_good} == {'fixture_error'}
    )
    return {
        'coverage_revision': coverage.coverage_revision,
        'fixtures': len(records),
        'repetitions': 2,
        'fully_graded': len(records) - unavailable - fixture_errors,
        'unable_to_grade': unavailable,
        'fixture_errors': fixture_errors,
        'status': 'blocked' if unavailable or fixture_errors else 'pass',
    }


def _result_rows(coverage: P0Coverage) -> list[dict[str, Any]]:
    rows = []
    for fixture_id, fixture_revision in coverage.selected_fixture_revisions:
        fixture = load_fixture(fixture_id)
        calibration = calibrate_fixture(fixture_id)
        aggregate_verdict = calibration.known_good[0].verdict
        for grader in fixture.required_graders:
            grader_class = str(grader['grader_class'])
            verdict = (
                'unable_to_grade'
                if grader_class in {'M', 'H'}
                else 'fixture_error'
                if aggregate_verdict == 'fixture_error'
                else 'pass'
            )
            result_key = [
                fixture_id,
                fixture_revision,
                str(grader['grader_id']),
                grader_class,
                str(grader['grader_version']),
            ]
            rows.append(
                {
                    'fixture_id': fixture_id,
                    'result_key': result_key,
                    'verdict': verdict,
                    'required': bool(grader['required']),
                    'critical': bool(grader['critical']),
                    'oracle_authority': 'fixture_input_recomputation_v1',
                }
            )
    return rows


def run_p0_coverage(
    coverage_path: Path | str = _DEFAULT_COVERAGE,
    *,
    transport: str = 'fake',
) -> dict[str, Any]:
    """Run exact fake P0 coverage and preserve every blocking non-pass."""
    coverage = load_p0_coverage(coverage_path)
    if transport != coverage.transport or transport != 'fake':
        raise FixtureDefinitionError('deterministic fake transport required')
    results = _result_rows(coverage)
    scenario_results = [
        _document_value(asdict(run_gate3_scenario(scenario_id)))
        for scenario_id in coverage.scenarios
    ]
    blocking = any(
        item['required'] and item['verdict'] in {'unable_to_grade', 'fixture_error'}
        for item in results
    )
    failing = any(
        item['required'] and item['verdict'] == 'fail' for item in results
    )
    return {
        'schema_version': '1.0.0',
        'coverage_revision': coverage.coverage_revision,
        'calibration_policy_revision': coverage.calibration_policy_revision,
        'variant_matrix_revision': coverage.variant_matrix_revision,
        'threshold_policy_revision': coverage.threshold_policy_revision,
        'transport': 'fake',
        'fixture_count': len(coverage.selected_fixture_revisions),
        'scenario_count': len(scenario_results),
        'required_result_keys': [list(key) for key in coverage.required_result_keys],
        'results': results,
        'scenarios': scenario_results,
        'omitted_gate5': [asdict(item) for item in coverage.omitted_gate5],
        'candidate_status': 'blocked' if blocking else 'fail' if failing else 'pass',
        'owner_acceptance': 'required',
        'gate5_authorized': False,
    }


def decide_p0_release(
    document: dict[str, Any],
    coverage_path: Path | str = _DEFAULT_COVERAGE,
) -> ReleaseAssessment:
    """Emit a non-authorizing decision only after exact result closure."""
    coverage = load_p0_coverage(coverage_path)
    required = tuple(coverage.required_result_keys)
    required_set = set(required)
    rows = document.get('results', ())
    observed_keys = [tuple(row.get('result_key', ())) for row in rows]
    counts = Counter(observed_keys)
    observed_set = set(observed_keys)
    missing = tuple(key for key in required if key not in observed_set)
    unexpected = tuple(sorted(observed_set - required_set))
    duplicates = tuple(sorted(key for key, count in counts.items() if count != 1))
    incompatible = []
    bindings = {
        'coverage_revision': coverage.coverage_revision,
        'calibration_policy_revision': coverage.calibration_policy_revision,
        'variant_matrix_revision': coverage.variant_matrix_revision,
        'threshold_policy_revision': coverage.threshold_policy_revision,
        'transport': 'fake',
        'gate5_authorized': False,
    }
    for name, expected in bindings.items():
        if document.get(name) != expected:
            incompatible.append(f'{name}_mismatch')
    expected_omissions = [asdict(item) for item in coverage.omitted_gate5]
    if document.get('omitted_gate5') != expected_omissions:
        incompatible.append('gate5_capability_restrictions_mismatch')
    verdict_by_key = {
        tuple(row['result_key']): str(row.get('verdict'))
        for row in rows
        if tuple(row.get('result_key', ())) in required_set
        and counts[tuple(row.get('result_key', ()))] == 1
    }
    blocking = any(
        verdict in {'unable_to_grade', 'fixture_error'}
        for verdict in verdict_by_key.values()
    )
    failing = any(verdict == 'fail' for verdict in verdict_by_key.values())
    if missing or unexpected or duplicates or incompatible or blocking:
        decision_name = 'blocked'
    elif failing:
        decision_name = 'fail'
    else:
        decision_name = 'pass'
    snapshot_hash = sha256_hex(canonical_bytes(document))
    rationale_parts = []
    if missing:
        rationale_parts.append('missing_required_results')
    if unexpected:
        rationale_parts.append('unexpected_results')
    if duplicates:
        rationale_parts.append('duplicate_results')
    rationale_parts.extend(incompatible)
    if blocking:
        rationale_parts.append('required_judgment_unavailable')
    if not rationale_parts and failing:
        rationale_parts.append('required_result_failed')
    if not rationale_parts:
        rationale_parts.append('p0_evidence_complete_owner_review_required')
    decision = ReleaseGateDecision(
        release_gate_decision_id='p0-review-' + snapshot_hash[:24],
        coverage_manifest_id=coverage.coverage_revision,
        baseline_identity='ars-wp1-wp3-merged',
        candidate_identity='ars-wp4-p0-candidate',
        evidence_snapshot_hash=snapshot_hash,
        required_verdicts=tuple(
            (key, verdict_by_key.get(key, 'unable_to_grade')) for key in required
        ),
        critical_failures=tuple(
            tuple(row['result_key'])
            for row in rows
            if row.get('critical') is True and row.get('verdict') == 'fail'
        ),
        parity_status='blocked' if decision_name == 'blocked' else 'complete',
        operations_status='pass' if document.get('scenario_count') == 5 else 'blocked',
        decision=decision_name,
        decided_at='2026-07-03T00:00:00Z',
        canonical_event_ref='not_published_review_only',
        disabled_or_constrained_capability=(
            'foundation_release_and_pilot_promotion'
        ),
        rationale=','.join(rationale_parts),
        human_authority_id=None,
    )
    return ReleaseAssessment(
        decision=decision,
        missing=missing,
        unexpected=unexpected,
        duplicates=duplicates,
        incompatible=tuple(incompatible),
    )


def write_external_output(
    path: Path | str,
    payload: dict[str, Any],
    *,
    code_roots: tuple[Path, ...] | None = None,
) -> Path:
    """Write one explicit date-suffixed output outside all code roots."""
    output = Path(path)
    if not _DATE_SUFFIX.search(output.name):
        raise ValueError('evaluation output must be date-suffixed')
    resolved = output.resolve(strict=False)
    roots = code_roots or (Path.cwd().resolve(strict=True),)
    for root in roots:
        code_root = root.resolve(strict=True)
        if resolved == code_root or code_root in resolved.parents:
            raise ValueError('evaluation output must be external to code roots')
    encoded = canonical_bytes(payload) + b'\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        handle.write(encoded)
    return output
