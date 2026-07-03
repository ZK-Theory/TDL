from pathlib import Path


SCHEMAS = Path('.research-system/schemas/evals')


def test_eval_schema_set_matches_the_w6_contract_surface():
    paths = sorted(SCHEMAS.glob('*.schema.json'))
    assert {path.name for path in paths} == {
        'coverage-manifest.schema.json',
        'deletion-verification-manifest.schema.json',
        'evidence-store-registry.schema.json',
        'evaluation-run.schema.json',
        'fixture-definition.schema.json',
        'grader-result.schema.json',
        'release-gate-decision.schema.json',
        'trace-envelope.schema.json',
    }
