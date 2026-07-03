from pathlib import Path

import pytest
import yaml

from research_system.evals.catalogue import P0_CASES, load_catalogue, load_fixture
from research_system.evals.errors import FixtureDefinitionError
from tools.ars.materialize_p0_fixtures import materialize_fixture_packages


CATALOGUE = Path('.research-system/evals/catalogue.yaml')
FIXTURES = Path('.research-system/evals/fixtures')
CALIBRATION = Path('.research-system/evals/p0-calibration-policy.yaml')
VARIANTS = Path('.research-system/evals/p0-variant-matrix.yaml')
PACKAGE_FILES = {
    'fixture.yaml',
    'README.md',
    'input/source-manifest.json',
    'input/stimulus.json',
    'expected/pre-control.json',
    'expected/post-control.json',
    'expected/trajectory.json',
    'graders/required.json',
}


def test_p0_catalogue_contains_exactly_the_accepted_37_cases():
    catalogue = load_catalogue(CATALOGUE)
    assert set(catalogue.p0_materialization_ids) == P0_CASES
    assert len(catalogue.p0_materialization_ids) == 37
    assert len(P0_CASES) == 37
    assert {'S-014', 'S-015', 'S-016'}.isdisjoint(P0_CASES)


def test_f021_remains_p1_but_materializes_its_sizing_variant():
    fixture = load_fixture('F-021')
    assert fixture.priority == 'P1'
    assert fixture.gate_stage == 'p0_materialization'
    assert fixture.variant == 'mandatory_closure_sizing'
    assert set(fixture.required_variants) == {
        'reference_tokens',
        'claude_fake_provider_tokens',
        'codex_fake_provider_tokens',
    }


def test_every_fixture_package_has_exact_required_files_and_provenance():
    for fixture_id in sorted(P0_CASES):
        root = FIXTURES / fixture_id
        files = {
            path.relative_to(root).as_posix()
            for path in root.rglob('*')
            if path.is_file()
        }
        assert files == PACKAGE_FILES, fixture_id
        fixture = load_fixture(fixture_id)
        assert fixture.fixture_revision == 'r1'
        assert fixture.source_manifest_hash.isalnum()
        assert len(fixture.source_manifest_hash) == 64
        assert fixture.required_graders
        assert fixture.required_variants
        assert fixture.retention_class in {'R0', 'R1', 'R2'}


def test_materializer_is_byte_deterministic_and_refuses_changed_overwrite(tmp_path):
    root = tmp_path / 'fixtures'
    assert materialize_fixture_packages(CATALOGUE, root) == 37
    before = {
        path.relative_to(root): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }
    assert materialize_fixture_packages(CATALOGUE, root, check=True) == 37
    assert materialize_fixture_packages(CATALOGUE, root) == 37
    assert before == {
        path.relative_to(root): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }
    changed = root / 'F-001' / 'README.md'
    changed.write_text('changed\n', encoding='utf-8')
    with pytest.raises(FixtureDefinitionError, match='refuses overwrite'):
        materialize_fixture_packages(CATALOGUE, root)


def test_calibration_policy_freezes_two_runs_and_blocks_missing_judgment_policy():
    policy = yaml.safe_load(CALIBRATION.read_text(encoding='utf-8'))
    assert policy == {
        'schema_version': '1.0.0',
        'policy_revision': 'p0-calibration-v1',
        'deterministic_repetitions': 2,
        'identical_input_requirement': 'byte_identical_normalized_decision',
        'known_bad_requirement': 'intended_failure_in_every_repetition',
        'known_good_requirement': 'intended_pass_in_every_repetition',
        'declared_mutation_requirement': 'detected_in_every_repetition',
        'stochastic_policy_missing': 'fixture_error',
        'model_or_human_threshold_policy_missing': 'unable_to_grade',
        'live_provider_calibration_enabled': False,
    }


def test_variant_matrix_has_exact_rows_without_wildcards():
    matrix = yaml.safe_load(VARIANTS.read_text(encoding='utf-8'))
    rows = matrix['variants']
    keys = [(row['fixture_id'], row['variant_id']) for row in rows]
    assert len(keys) == len(set(keys))
    assert {row['fixture_id'] for row in rows} == P0_CASES
    for row in rows:
        assert '*' not in str(row)
        assert 'any' not in str(row).lower()
        assert row['transport'] in {'none', 'in_process_fake', 'fake'}
        assert row['os'] == 'windows'
    for fixture_id in P0_CASES:
        fixture = load_fixture(fixture_id)
        observed = {
            row['variant_id'] for row in rows if row['fixture_id'] == fixture_id
        }
        assert observed == set(fixture.required_variants), fixture_id


def test_f036_declares_all_three_independent_anti_gaming_mutations():
    fixture = load_fixture('F-036')
    assert set(fixture.mutation_ids) == {
        'expected_value_anchoring',
        'degenerate_fallback',
        'null_invariance',
    }


def test_fixture_definitions_contain_no_prohibited_runtime_or_sensitive_content():
    prohibited = (
        'ukda raw',
        'credential=',
        'provider token',
        'full transcript',
        'hidden reasoning',
        'active apm state',
    )
    for path in FIXTURES.rglob('*'):
        if path.is_file():
            content = path.read_text(encoding='utf-8').lower()
            assert not any(term in content for term in prohibited), path
