"""Materialize the exact ARS P0 fixture packages deterministically."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.catalogue import P0_CASES, CatalogueCase, load_catalogue
from research_system.evals.errors import FixtureDefinitionError

_PACKAGE_PATHS = (
    'fixture.yaml',
    'README.md',
    'input/source-manifest.json',
    'input/stimulus.json',
    'expected/pre-control.json',
    'expected/post-control.json',
    'expected/trajectory.json',
    'graders/required.json',
)


def _json(payload: dict[str, Any]) -> bytes:
    return canonical_bytes(payload) + b'\n'


def _yaml(payload: dict[str, Any]) -> bytes:
    return yaml.safe_dump(
        payload,
        allow_unicode=False,
        sort_keys=False,
    ).encode('utf-8')


def _load_variant_rows(catalogue_path: Path) -> list[dict[str, Any]]:
    path = catalogue_path.with_name('p0-variant-matrix.yaml')
    try:
        payload = yaml.safe_load(path.read_text(encoding='utf-8'))
        rows = payload['variants']
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise FixtureDefinitionError('invalid P0 variant matrix') from exc
    if not isinstance(rows, list):
        raise FixtureDefinitionError('variant matrix rows must be a list')
    keys = [(row.get('fixture_id'), row.get('variant_id')) for row in rows]
    if len(keys) != len(set(keys)) or {key[0] for key in keys} != P0_CASES:
        raise FixtureDefinitionError('variant matrix closure mismatch')
    if any('*' in str(row) or 'any' in str(row).lower() for row in rows):
        raise FixtureDefinitionError('wildcard variant activation prohibited')
    return rows


def _package_bytes(
    case: CatalogueCase,
    catalogue_revision: str,
    variants: list[dict[str, Any]],
) -> dict[str, bytes]:
    rows = [row for row in variants if row['fixture_id'] == case.fixture_id]
    required_variants = [row['variant_id'] for row in rows]
    grader_rows = [
        {
            'grader_id': f'{case.fixture_id.lower()}-{grader_class.lower()}',
            'grader_class': grader_class,
            'grader_version': 'v1',
            'critical': grader_class in {'D', 'T', 'P'},
            'required': True,
            'independence_requirement': (
                'cross_family_context_independent'
                if grader_class in {'R', 'M', 'H'}
                else 'deterministic_independent'
            ),
        }
        for grader_class in case.required_graders
    ]
    source_manifest = {
        'fixture_id': case.fixture_id,
        'fixture_revision': 'r1',
        'incident_basis': case.incident_basis,
        'input_fidelity': case.input_fidelity,
        'authoritative_refs': ['P-030', 'W6-v0.3', '06c-v0.2'],
        'reconstruction_method': 'synthetic_minimized_contract_case',
        'redaction_record': 'no_sensitive_payload_included',
        'source_snapshot_date': '2026-07-01',
    }
    source_bytes = _json(source_manifest)
    fixture = {
        'schema_version': '1.0.0',
        'fixture_id': case.fixture_id,
        'fixture_revision': 'r1',
        'catalogue_revision': catalogue_revision,
        'title': case.title,
        'status': 'authored',
        'owner': 'evaluation_owner',
        'incident_basis': case.incident_basis,
        'input_fidelity': case.input_fidelity,
        'priority': case.priority,
        'gate_stage': case.gate_stage,
        'variant': case.variant,
        'risk_tier': case.risk_tier,
        'assurance_lanes': list(case.assurance_lanes),
        'failure_class': case.failure_class,
        'source_manifest_hash': sha256_hex(source_bytes),
        'reconstruction_hash': sha256_hex(
            canonical_bytes({'fixture_id': case.fixture_id, 'method': 'synthetic'})
        ),
        'redaction_hash': sha256_hex(
            canonical_bytes({'fixture_id': case.fixture_id, 'redaction': 'minimized'})
        ),
        'policy_versions': ['p0-calibration-v1', 'p0-retention-v1'],
        'schema_versions': ['fixture-definition-v1'],
        'required_variants': required_variants,
        'required_graders': grader_rows,
        'threshold_policy_ids': list(case.threshold_policy_ids),
        'retention_class': case.retention_class,
        'allowed_consumers': ['eval', 'independent_review'],
        'mutation_ids': list(case.mutation_ids),
    }
    expected = {
        'fixture_id': case.fixture_id,
        'fixture_revision': 'r1',
        'known_bad_decision': 'fail',
        'known_good_decision': 'pass',
    }
    return {
        'fixture.yaml': _yaml(fixture),
        'README.md': (
            f'# {case.fixture_id} - {case.title}\n\n'
            'Synthetic/minimized P0 evaluation definition. No runtime evidence.\n'
        ).encode('utf-8'),
        'input/source-manifest.json': source_bytes,
        'input/stimulus.json': _json(
            {
                'fixture_id': case.fixture_id,
                'input_kind': 'synthetic_minimized',
                'immutable': True,
            }
        ),
        'expected/pre-control.json': _json(
            expected | {'system': 'known_bad', 'decision': 'fail'}
        ),
        'expected/post-control.json': _json(
            expected | {'system': 'known_good', 'decision': 'pass'}
        ),
        'expected/trajectory.json': _json(
            {
                'fixture_id': case.fixture_id,
                'required': ['normalized_trace_complete'],
                'forbidden': ['authority_or_evidence_bypass'],
            }
        ),
        'graders/required.json': _json(
            {'fixture_id': case.fixture_id, 'required_graders': grader_rows}
        ),
    }


def materialize_fixture_packages(
    catalogue_path: Path | str,
    root: Path | str,
    *,
    check: bool = False,
) -> int:
    """Create or verify the exact byte-deterministic 37-package closure."""
    catalogue_path = Path(catalogue_path)
    root = Path(root)
    catalogue = load_catalogue(catalogue_path)
    variants = _load_variant_rows(catalogue_path)
    for case in catalogue.cases:
        package = _package_bytes(case, catalogue.catalogue_revision, variants)
        if set(package) != set(_PACKAGE_PATHS):
            raise FixtureDefinitionError('fixture package path contract changed')
        case_root = root / case.fixture_id
        existing_files = {
            path.relative_to(case_root).as_posix()
            for path in case_root.rglob('*')
            if path.is_file()
        } if case_root.exists() else set()
        extras = existing_files - set(package)
        if extras:
            raise FixtureDefinitionError(
                f'fixture materializer refuses overwrite: {case.fixture_id}'
            )
        for relative, expected in package.items():
            path = case_root / relative
            if path.exists():
                if path.read_bytes() != expected:
                    raise FixtureDefinitionError(
                        f'fixture materializer refuses overwrite: {path}'
                    )
            elif check:
                raise FixtureDefinitionError(f'missing fixture package file: {path}')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    materialized = {
        path.name for path in root.iterdir() if path.is_dir()
    } if root.exists() else set()
    if materialized != P0_CASES:
        raise FixtureDefinitionError('materialized fixture closure mismatch')
    return len(catalogue.cases)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalogue', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    count = materialize_fixture_packages(args.catalogue, args.root, check=args.check)
    suffix = ' packages byte-identical' if args.check else ' packages materialized'
    print(f'{count}{suffix}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
