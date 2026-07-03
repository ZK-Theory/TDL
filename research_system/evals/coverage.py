"""Exact P0 coverage manifest and Gate 5 capability restrictions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.evals.catalogue import P0_CASES, load_fixture
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.models import ResultKey

_DEFAULT_THRESHOLDS = Path('.research-system/evals/threshold-policies.yaml')
_DEFAULT_COVERAGE = Path('.research-system/evals/p0-coverage.yaml')
_EXPECTED_DEFERRED = frozenset({'S-014', 'S-015', 'S-016'})


@dataclass(frozen=True, slots=True)
class DeferredCapability:
    """One explicit non-P0 capability that remains disabled before Gate 5."""

    fixture_id: str
    reason: str
    capability: str
    status: str
    required_before: str


@dataclass(frozen=True, slots=True)
class P0Coverage:
    """Validated exact fixture, policy, scenario, and deferral closure."""

    coverage_revision: str
    catalogue_revision: str
    calibration_policy_revision: str
    variant_matrix_revision: str
    threshold_policy_revision: str
    accepted_grader_classes: tuple[str, ...]
    unavailable_grader_classes: tuple[str, ...]
    transport: str
    selected_fixture_revisions: tuple[tuple[str, str], ...]
    omitted_gate5: tuple[DeferredCapability, ...]
    scenarios: tuple[str, ...]
    release_policy_revision: str
    owner_acceptance_required: bool
    gate5_authorized: bool

    @property
    def required_result_keys(self) -> tuple[ResultKey, ...]:
        keys = []
        for fixture_id, fixture_revision in self.selected_fixture_revisions:
            fixture = load_fixture(fixture_id)
            if fixture.fixture_revision != fixture_revision:
                raise FixtureDefinitionError(
                    f'coverage revision mismatch for {fixture_id}'
                )
            keys.extend(
                (
                    fixture_id,
                    fixture_revision,
                    str(grader['grader_id']),
                    str(grader['grader_class']),
                    str(grader['grader_version']),
                )
                for grader in fixture.required_graders
            )
        if len(keys) != len(set(keys)):
            raise FixtureDefinitionError('duplicate required result key')
        return tuple(keys)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise FixtureDefinitionError(f'invalid coverage YAML: {path}') from exc
    if not isinstance(payload, dict):
        raise FixtureDefinitionError('coverage must be an object')
    return payload


def load_threshold_policies(
    path: Path | str = _DEFAULT_THRESHOLDS,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Validate exact deterministic and unavailable-judgment policies."""
    payload = _read_yaml(Path(path))
    if payload.get('schema_version') != '1.0.0':
        raise FixtureDefinitionError('unsupported threshold policy schema')
    rows = payload.get('policies')
    if not isinstance(rows, list) or len(rows) != 2:
        raise FixtureDefinitionError('exact threshold policy rows required')
    accepted: set[str] = set()
    unavailable: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise FixtureDefinitionError('threshold policy row must be an object')
        classes = row.get('grader_classes')
        if not isinstance(classes, list) or not classes:
            raise FixtureDefinitionError('threshold grader classes required')
        if row.get('status') == 'accepted':
            if (
                row.get('repetitions') != 2
                or row.get('acceptance')
                != 'exact_property_satisfied_every_repetition'
            ):
                raise FixtureDefinitionError('invalid deterministic threshold policy')
            accepted.update(map(str, classes))
        elif row.get('status') == 'unavailable':
            if (
                row.get('acceptance') != 'unable_to_grade'
                or row.get('authority') != 'none'
                or row.get('live_provider_enabled') is not False
            ):
                raise FixtureDefinitionError('invalid unavailable judgment policy')
            unavailable.update(map(str, classes))
        else:
            raise FixtureDefinitionError('unknown threshold policy status')
    if accepted != {'D', 'T', 'O', 'P', 'R'} or unavailable != {'M', 'H'}:
        raise FixtureDefinitionError('threshold policy grader closure mismatch')
    return (
        str(payload['policy_revision']),
        tuple(sorted(accepted)),
        tuple(sorted(unavailable)),
    )


def load_p0_coverage(
    path: Path | str = _DEFAULT_COVERAGE,
    threshold_policy_path: Path | str = _DEFAULT_THRESHOLDS,
) -> P0Coverage:
    """Load the fail-closed exact P0 coverage and capability restrictions."""
    payload = _read_yaml(Path(path))
    selected = payload.get('selected_fixture_revisions')
    if not isinstance(selected, dict) or set(selected) != P0_CASES:
        raise FixtureDefinitionError('coverage must select exact P0_CASES')
    if set(selected.values()) != {'r1'}:
        raise FixtureDefinitionError('P0 fixture revisions must be exactly r1')
    omitted_rows = payload.get('omitted_gate5')
    if not isinstance(omitted_rows, list):
        raise FixtureDefinitionError('Gate 5 omissions must be explicit')
    try:
        omitted = tuple(DeferredCapability(**row) for row in omitted_rows)
    except (TypeError, AttributeError) as exc:
        raise FixtureDefinitionError('invalid Gate 5 omission') from exc
    if {item.fixture_id for item in omitted} != _EXPECTED_DEFERRED:
        raise FixtureDefinitionError('exact S-014/S-015/S-016 deferrals required')
    if any(
        item.status != 'capability_disabled'
        or item.required_before != 'gate5'
        or not item.reason
        or not item.capability
        for item in omitted
    ):
        raise FixtureDefinitionError('Gate 5 deferral must disable capability')
    if payload.get('transport') != 'fake':
        raise FixtureDefinitionError('P0 permits deterministic fake transport only')
    if tuple(payload.get('scenarios', ())) != ('A', 'B', 'C', 'D', 'E'):
        raise FixtureDefinitionError('exact scenarios A-E required')
    if payload.get('owner_acceptance_required') is not True:
        raise FixtureDefinitionError('owner acceptance gate is required')
    threshold_revision, accepted_classes, unavailable_classes = (
        load_threshold_policies(threshold_policy_path)
    )
    if threshold_revision != payload.get('threshold_policy_revision'):
        raise FixtureDefinitionError('threshold policy revision mismatch')
    if payload.get('gate5_authorized') is not False:
        raise FixtureDefinitionError('Gate 5 must remain unauthorized')
    coverage = P0Coverage(
        coverage_revision=str(payload['coverage_revision']),
        catalogue_revision=str(payload['catalogue_revision']),
        calibration_policy_revision=str(payload['calibration_policy_revision']),
        variant_matrix_revision=str(payload['variant_matrix_revision']),
        threshold_policy_revision=str(payload['threshold_policy_revision']),
        transport='fake',
        selected_fixture_revisions=tuple(sorted(selected.items())),
        omitted_gate5=tuple(sorted(omitted, key=lambda item: item.fixture_id)),
        scenarios=('A', 'B', 'C', 'D', 'E'),
        release_policy_revision=str(payload['release_policy_revision']),
        owner_acceptance_required=True,
        accepted_grader_classes=accepted_classes,
        unavailable_grader_classes=unavailable_classes,
        gate5_authorized=False,
    )
    coverage.required_result_keys
    return coverage
