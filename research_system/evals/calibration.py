"""Deterministic paired calibration over immutable P0 fixture packages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.catalogue import FixturePackage, load_fixture
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.reference_systems import (
    build_f036_mutation_evidence,
    build_reference_evidence,
    grade_f036_mutation,
    grade_reference_evidence,
)

_DEFAULT_POLICY = Path('.research-system/evals/p0-calibration-policy.yaml')
_DEFAULT_FIXTURES = Path('.research-system/evals/fixtures')
_LIVE_JUDGMENT_CLASSES = frozenset({'M', 'H'})


@dataclass(frozen=True, slots=True)
class CalibrationDecision:
    """One normalized result from a deterministic calibration repetition."""

    subject: str
    repetition: int
    verdict: str
    reason: str
    subject_hash: str
    oracle_hash: str
    independently_recomputed: bool
    normalized_bytes: bytes


@dataclass(frozen=True, slots=True)
class MutationCalibration:
    """Paired repeated challenge for one declared anti-gaming mutation."""

    mutation_id: str
    known_bad: tuple[CalibrationDecision, ...]
    known_good: tuple[CalibrationDecision, ...]


@dataclass(frozen=True, slots=True)
class PairedCalibration:
    """Closed calibration record for one immutable fixture revision."""

    fixture_id: str
    fixture_revision: str
    policy_revision: str
    repetitions: int
    failure_class: str
    required_grader_classes: tuple[str, ...]
    known_bad: tuple[CalibrationDecision, ...]
    known_good: tuple[CalibrationDecision, ...]
    mutations: tuple[MutationCalibration, ...]


def _load_policy(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise FixtureDefinitionError(f'invalid calibration policy: {path}') from exc
    if not isinstance(payload, dict):
        raise FixtureDefinitionError('calibration policy must be an object')
    return payload


def _oracle_hash(fixture: FixturePackage, *, mutation_id: str | None = None) -> str:
    payload = {
        'fixture_id': fixture.fixture_id,
        'fixture_revision': fixture.fixture_revision,
        'source_manifest_hash': fixture.source_manifest_hash,
        'failure_class': fixture.payload['failure_class'],
        'mutation_id': mutation_id,
        'oracle_authority': 'fixture_input_recomputation_v1',
    }
    return sha256_hex(canonical_bytes(payload))


def _decision(
    *,
    fixture: FixturePackage,
    subject: str,
    repetition: int,
    verdict: str,
    reason: str,
    evidence: dict[str, Any],
    mutation_id: str | None = None,
) -> CalibrationDecision:
    subject_hash = sha256_hex(
        canonical_bytes(
            {
                'fixture_id': fixture.fixture_id,
                'fixture_revision': fixture.fixture_revision,
                'subject': subject,
                'evidence': evidence,
                'mutation_id': mutation_id,
            }
        )
    )
    oracle_hash = _oracle_hash(fixture, mutation_id=mutation_id)
    normalized = canonical_bytes(
        {
            'fixture_id': fixture.fixture_id,
            'fixture_revision': fixture.fixture_revision,
            'subject': subject,
            'verdict': verdict,
            'reason': reason,
            'subject_hash': subject_hash,
            'oracle_hash': oracle_hash,
            'independently_recomputed': True,
            'mutation_id': mutation_id,
        }
    )
    return CalibrationDecision(
        subject=subject,
        repetition=repetition,
        verdict=verdict,
        reason=reason,
        subject_hash=subject_hash,
        oracle_hash=oracle_hash,
        independently_recomputed=True,
        normalized_bytes=normalized,
    )


def _repeated_decisions(
    fixture: FixturePackage,
    *,
    subject: str,
    repetitions: int,
    forced_error: str | None,
    requires_live_judgment: bool,
) -> tuple[CalibrationDecision, ...]:
    evidence = build_reference_evidence(
        fixture.fixture_id,
        str(fixture.payload['failure_class']),
        subject,
    )
    property_verdict = grade_reference_evidence(fixture.fixture_id, evidence)
    if forced_error is not None:
        verdict, reason = 'fixture_error', forced_error
    elif requires_live_judgment:
        verdict, reason = 'unable_to_grade', 'required_live_judgment_unavailable'
    elif property_verdict == 'pass':
        verdict, reason = 'pass', 'control_satisfied'
    else:
        verdict, reason = 'fail', str(fixture.payload['failure_class'])
    return tuple(
        _decision(
            fixture=fixture,
            subject=subject,
            repetition=repetition,
            verdict=verdict,
            reason=reason,
            evidence=evidence,
        )
        for repetition in range(1, repetitions + 1)
    )


def _mutation_calibrations(
    fixture: FixturePackage,
    repetitions: int,
) -> tuple[MutationCalibration, ...]:
    records = []
    for mutation_id in fixture.mutation_ids:
        decisions: dict[str, tuple[CalibrationDecision, ...]] = {}
        for subject in ('known_bad', 'known_good'):
            evidence = build_f036_mutation_evidence(mutation_id, subject)
            property_verdict = grade_f036_mutation(mutation_id, evidence)
            verdict = property_verdict
            reason = 'control_satisfied' if verdict == 'pass' else mutation_id
            decisions[subject] = tuple(
                _decision(
                    fixture=fixture,
                    subject=subject,
                    repetition=repetition,
                    verdict=verdict,
                    reason=reason,
                    evidence=evidence,
                    mutation_id=mutation_id,
                )
                for repetition in range(1, repetitions + 1)
            )
        records.append(
            MutationCalibration(
                mutation_id=mutation_id,
                known_bad=decisions['known_bad'],
                known_good=decisions['known_good'],
            )
        )
    return tuple(records)


def calibrate_fixture(
    fixture_id: str,
    *,
    fixture_root: Path | str = _DEFAULT_FIXTURES,
    policy_path: Path | str = _DEFAULT_POLICY,
    expected_fixture_revision: str = 'r1',
    expected_policy_revision: str = 'p0-calibration-v1',
) -> PairedCalibration:
    """Calibrate known-bad/good systems twice and fail closed on gaps."""
    fixture = load_fixture(fixture_id, fixture_root)
    policy = _load_policy(Path(policy_path))
    repetitions = policy.get('deterministic_repetitions')
    if not isinstance(repetitions, int) or repetitions <= 0:
        repetitions = 2
        forced_error = 'invalid_repetition_policy'
    elif fixture.fixture_revision != expected_fixture_revision:
        forced_error = 'fixture_revision_mismatch'
    elif (
        policy.get('schema_version') != '1.0.0'
        or policy.get('policy_revision') != expected_policy_revision
        or policy.get('deterministic_repetitions') != 2
    ):
        forced_error = 'calibration_policy_mismatch'
    elif expected_policy_revision not in fixture.payload.get('policy_versions', ()):
        forced_error = 'fixture_policy_binding_mismatch'
    else:
        forced_error = None

    required_grader_classes = tuple(
        str(item['grader_class']) for item in fixture.required_graders
    )
    requires_live_judgment = bool(
        _LIVE_JUDGMENT_CLASSES.intersection(required_grader_classes)
    )
    if requires_live_judgment and policy.get('live_provider_calibration_enabled') is True:
        forced_error = 'unbounded_live_calibration_prohibited'

    known_bad = _repeated_decisions(
        fixture,
        subject='known_bad',
        repetitions=repetitions,
        forced_error=forced_error,
        requires_live_judgment=requires_live_judgment,
    )
    known_good = _repeated_decisions(
        fixture,
        subject='known_good',
        repetitions=repetitions,
        forced_error=forced_error,
        requires_live_judgment=requires_live_judgment,
    )
    return PairedCalibration(
        fixture_id=fixture.fixture_id,
        fixture_revision=fixture.fixture_revision,
        policy_revision=str(policy.get('policy_revision', 'invalid')),
        repetitions=repetitions,
        failure_class=str(fixture.payload['failure_class']),
        required_grader_classes=required_grader_classes,
        known_bad=known_bad,
        known_good=known_good,
        mutations=_mutation_calibrations(fixture, repetitions),
    )
