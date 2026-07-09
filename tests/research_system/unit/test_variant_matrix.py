import math
from pathlib import Path

import yaml

from research_system.evals.coverage import P0_CASES

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
WILDCARDS = {"*", "any", "wildcard", ""}


def _matrix():
    return yaml.safe_load((EVALS / "p0-variant-matrix.yaml").read_text(encoding="utf-8"))


def test_every_p0_case_has_exactly_one_executed_p0_row_plus_f021_sizing():
    rows = _matrix()["rows"]
    p0_rows = {}
    for row in rows:
        if row["execution_stage"] == "p0":
            p0_rows.setdefault(row["fixture_id"], []).append(row)
    assert set(p0_rows) == P0_CASES
    for fixture_id, fixture_rows in p0_rows.items():
        expected = 3 if fixture_id == "F-021" else 1
        assert len(fixture_rows) == expected, fixture_id


def test_no_wildcard_rows_and_complete_tuples():
    for row in _matrix()["rows"]:
        for field in ("variant_id", "provider_variant", "runtime_variant", "os", "transport"):
            assert str(row[field]).lower() not in WILDCARDS, row


def test_f021_sizing_rows_record_recomputable_token_evidence():
    stimulus = (EVALS / "fixtures" / "F-021" / "input" / "stimulus.json").read_bytes()
    evaluated_bytes = stimulus + b"".join(
        (EVALS / "fixtures" / "F-021" / "expected" / name).read_bytes()
        for name in ("pre-control.json", "post-control.json")
    )
    divisors = {"fake-claude-count-v1": 4, "fake-codex-count-v1": 3}
    rows = [
        row for row in _matrix()["rows"]
        if row["fixture_id"] == "F-021" and row["variant_id"].startswith("mandatory_closure_sizing")
    ]
    assert len(rows) == 2 and all(row["execution_stage"] == "p0" for row in rows)
    for row in rows:
        divisor = divisors[row["provider_variant"]]
        assert row["exact_tokens"] == math.ceil(len(stimulus) / divisor)
        assert row["evaluated_tokens"] == math.ceil(len(evaluated_bytes) / divisor)
        assert row["reference_count"] >= 1


def test_adapter_cases_register_claude_and_codex_gate5_rows():
    rows = _matrix()["rows"]
    adapter_ids = {"F-007", "F-008", "F-009", "F-010", "F-011", "F-012", "F-013",
                   "F-014", "F-020", "F-032", "F-034", "F-036", "S-003", "S-004", "S-013"}
    for fixture_id in adapter_ids:
        providers = {
            row["provider_variant"] for row in rows
            if row["fixture_id"] == fixture_id and row["execution_stage"] == "gate5"
        }
        assert providers == {"fake-claude-adapter-v1", "fake-codex-adapter-v1"}, fixture_id


def test_package_bindings_are_matrix_rows():
    import json

    matrix_ids = {
        (row["fixture_id"], row["variant_id"]) for row in _matrix()["rows"]
    }
    for fixture_id in sorted(P0_CASES):
        manifest = json.loads(
            (EVALS / "fixtures" / fixture_id / "input" / "source-manifest.json").read_text(encoding="utf-8")
        )
        for binding in manifest["variant_bindings"]:
            assert (fixture_id, binding["variant_id"]) in matrix_ids, (fixture_id, binding["variant_id"])
