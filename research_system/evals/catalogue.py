"""Exact P0 fixture catalogue and materialized package loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.evals.errors import FixtureDefinitionError

P0_CASES = frozenset(
    {
        'F-001', 'F-002', 'F-003', 'F-004', 'F-005',
        'F-007', 'F-008', 'F-009', 'F-010', 'F-011', 'F-012', 'F-013',
        'F-014', 'F-020', 'F-021', 'F-022', 'F-025', 'F-026', 'F-027',
        'F-028', 'F-031', 'F-032', 'F-033', 'F-034', 'F-035', 'F-036',
        'S-001', 'S-002', 'S-003', 'S-004', 'S-006', 'S-008', 'S-009',
        'S-010', 'S-011', 'S-012', 'S-013',
    }
)

_DEFAULT_CATALOGUE = Path('.research-system/evals/catalogue.yaml')
_DEFAULT_FIXTURES = Path('.research-system/evals/fixtures')


@dataclass(frozen=True, slots=True)
class CatalogueCase:
    fixture_id: str
    title: str
    priority: str
    gate_stage: str
    variant: str
    profile: str
    incident_basis: str
    input_fidelity: str
    risk_tier: str
    assurance_lanes: tuple[str, ...]
    failure_class: str
    required_graders: tuple[str, ...]
    threshold_policy_ids: tuple[str, ...]
    retention_class: str
    mutation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Catalogue:
    schema_version: str
    catalogue_revision: str
    cases: tuple[CatalogueCase, ...]

    @property
    def p0_materialization_ids(self) -> tuple[str, ...]:
        return tuple(case.fixture_id for case in self.cases)

    def case(self, fixture_id: str) -> CatalogueCase:
        for case in self.cases:
            if case.fixture_id == fixture_id:
                return case
        raise FixtureDefinitionError(f'unknown fixture: {fixture_id}')


@dataclass(frozen=True, slots=True)
class FixturePackage:
    fixture_id: str
    fixture_revision: str
    priority: str
    gate_stage: str
    variant: str
    required_variants: tuple[str, ...]
    required_graders: tuple[dict[str, Any], ...]
    source_manifest_hash: str
    retention_class: str
    mutation_ids: tuple[str, ...]
    payload: dict[str, Any]


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise FixtureDefinitionError(f'invalid YAML: {path}') from exc
    if not isinstance(payload, dict):
        raise FixtureDefinitionError(f'YAML object required: {path}')
    return payload


def load_catalogue(path: Path | str = _DEFAULT_CATALOGUE) -> Catalogue:
    """Load and validate the immutable exact 37-case catalogue."""
    payload = _read_yaml(Path(path))
    if payload.get('schema_version') != '1.0.0':
        raise FixtureDefinitionError('unsupported catalogue schema')
    rows = payload.get('cases')
    if not isinstance(rows, list):
        raise FixtureDefinitionError('catalogue cases must be a list')
    cases = []
    for row in rows:
        if not isinstance(row, dict):
            raise FixtureDefinitionError('catalogue case must be an object')
        try:
            cases.append(
                CatalogueCase(
                    fixture_id=str(row['fixture_id']),
                    title=str(row['title']),
                    priority=str(row['priority']),
                    gate_stage=str(row.get('gate_stage', 'p0_materialization')),
                    variant=str(row.get('variant', 'default')),
                    profile=str(row['profile']),
                    incident_basis=str(row['incident_basis']),
                    input_fidelity=str(row['input_fidelity']),
                    risk_tier=str(row['risk_tier']),
                    assurance_lanes=tuple(row['assurance_lanes']),
                    failure_class=str(row['failure_class']),
                    required_graders=tuple(row['required_graders']),
                    threshold_policy_ids=tuple(row.get('threshold_policy_ids', ())),
                    retention_class=str(row['retention_class']),
                    mutation_ids=tuple(row.get('mutation_ids', ())),
                )
            )
        except (KeyError, TypeError) as exc:
            raise FixtureDefinitionError('incomplete catalogue case') from exc
    ids = [case.fixture_id for case in cases]
    if len(ids) != len(set(ids)):
        raise FixtureDefinitionError('duplicate catalogue fixture ID')
    if set(ids) != P0_CASES:
        raise FixtureDefinitionError('catalogue must contain exact P0_CASES')
    f021 = next(case for case in cases if case.fixture_id == 'F-021')
    if (
        f021.priority != 'P1'
        or f021.gate_stage != 'p0_materialization'
        or f021.variant != 'mandatory_closure_sizing'
    ):
        raise FixtureDefinitionError('F-021 staging contract changed')
    if any(case.retention_class == 'R3' for case in cases):
        raise FixtureDefinitionError('R3 fixture storage is prohibited')
    return Catalogue(
        schema_version='1.0.0',
        catalogue_revision=str(payload['catalogue_revision']),
        cases=tuple(cases),
    )


def load_fixture(
    fixture_id: str,
    root: Path | str = _DEFAULT_FIXTURES,
) -> FixturePackage:
    """Load one materialized fixture definition through a stable API."""
    payload = _read_yaml(Path(root) / fixture_id / 'fixture.yaml')
    if payload.get('fixture_id') != fixture_id:
        raise FixtureDefinitionError('fixture package identity mismatch')
    return FixturePackage(
        fixture_id=fixture_id,
        fixture_revision=str(payload['fixture_revision']),
        priority=str(payload['priority']),
        gate_stage=str(payload['gate_stage']),
        variant=str(payload['variant']),
        required_variants=tuple(payload['required_variants']),
        required_graders=tuple(payload['required_graders']),
        source_manifest_hash=str(payload['source_manifest_hash']),
        retention_class=str(payload['retention_class']),
        mutation_ids=tuple(payload.get('mutation_ids', ())),
        payload=payload,
    )
