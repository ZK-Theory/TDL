from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "contracts" / "fixtures"
RUNNER_PATH = REPO_ROOT / ".claude" / "hooks" / "contract_binding_check.py"

spec = importlib.util.spec_from_file_location("contract_binding_check", RUNNER_PATH)
contract_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(contract_runner)


def _load_fixture_contracts():
    meta_schema = yaml.safe_load(
        (REPO_ROOT / "contracts" / "schema" / "contract.schema.yaml").read_text(
            encoding="utf-8"
        )
    )
    contracts, errors = contract_runner.gate_1_validate_meta(meta_schema, FIXTURES)
    assert errors == []
    return {contract["id"]: (path, contract) for path, contract in contracts}


def test_meta_schema_accepts_hardening_fields_in_fixtures():
    contracts = _load_fixture_contracts()

    valid = contracts["valid-contract"][1]
    qualitative = contracts["qualitative-language"][1]
    json_schema = contracts["json-schema-contract"][1]

    assert valid["formula"]["variables"]["x"]["derivation"]
    assert qualitative["formula"]["invariants"][0]["enforced_by"]
    assert json_schema["schema_def"]["required_keys"][2]["type"] == "float | null"


def test_gate_1b_flags_qualitative_language_without_pinned_number():
    contracts = _load_fixture_contracts()

    issues = contract_runner.gate_1b_qualitative_language(
        [contracts["qualitative-language"]]
    )

    assert any("[gate 1b] qualitative-language:" in issue for issue in issues)
    assert any("binding.must_assert" in issue for issue in issues)


def test_gate_1c_flags_invariant_xor_both_and_neither_cases():
    contracts = _load_fixture_contracts()

    issues = contract_runner.gate_1c_invariant_enforcement(
        [contracts["missing-enforcement"], contracts["both-enforcement"]]
    )

    assert any("missing-enforcement" in issue and "neither" in issue for issue in issues)
    assert any("both-enforcement" in issue and "both" in issue for issue in issues)


def test_gate_2b_flags_clause_coverage_and_unreferenced_schema_key():
    contracts = _load_fixture_contracts()

    issues = contract_runner.gate_2b_claim_assertion_coverage(
        [contracts["claim-coverage-shortfall"]], REPO_ROOT
    )

    assert any("3 lettered clause" in issue for issue in issues)
    assert any("missing_key" in issue for issue in issues)


def test_pending_debt_flags_pending_contract_with_existing_binding():
    contracts = _load_fixture_contracts()

    issues = contract_runner.gate_pending_debt([contracts["pending-debt"]], REPO_ROOT)

    assert any("pending:true" in issue for issue in issues)


def test_valid_fixture_passes_all_new_contract_level_gates():
    contracts = _load_fixture_contracts()

    issues = contract_runner.hardening_gate_issues([contracts["valid-contract"]], REPO_ROOT)

    assert issues == []


def test_strengthened_gate_4_validates_types_bounds_and_null_allowed(tmp_path):
    contracts = _load_fixture_contracts()
    schema_contract = contracts["json-schema-contract"][1]

    valid_json = tmp_path / "valid.json"
    valid_json.write_text(
        json.dumps(
            {
                "score": 0.75,
                "count": 5,
                "optional_se": None,
                "labels": ["a", "b"],
                "metadata": {"source": "fixture"},
            }
        ),
        encoding="utf-8",
    )
    errors, hardening = contract_runner._validate_json_cells(
        valid_json, schema_contract, tmp_path
    )
    assert errors == []
    assert hardening == []

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text(
        json.dumps(
            {
                "score": 1.5,
                "count": True,
                "optional_se": None,
                "labels": ["ok", 3],
                "metadata": {"source": "fixture"},
            }
        ),
        encoding="utf-8",
    )
    errors, hardening = contract_runner._validate_json_cells(
        invalid_json, schema_contract, tmp_path
    )

    assert errors == []
    assert any("score" in issue and "outside declared range" in issue for issue in hardening)
    assert any("count" in issue and "does not match declared type" in issue for issue in hardening)
    assert any("labels" in issue and "does not match declared type" in issue for issue in hardening)
    assert not any("optional_se" in issue for issue in hardening)



def test_gate_4_legacy_exempt_skips_listed_file_but_validates_others(tmp_path):
    """Gate 4 skips a JSON listed in an output_validation's legacy_exempt but validates others."""
    schema_contract = _load_fixture_contracts()["json-schema-contract"][1]
    ov_contract = {
        "id": "legacy-exempt-output-validation",
        "kind": "output_validation",
        "output_validation": {
            "applies_to_glob": "results/*.json",
            "schema_contracts": ["json-schema-contract"],
            "legacy_exempt": ["results/legacy.json"],
        },
    }
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "legacy.json").write_text(json.dumps({}), encoding="utf-8")
    (results_dir / "current.json").write_text(json.dumps({}), encoding="utf-8")

    errors, hardening = contract_runner.gate_4_validate_jsons(
        [(Path("output.yaml"), ov_contract), (Path("schema.yaml"), schema_contract)],
        tmp_path,
        all_jsons=True,
    )

    assert hardening == []
    assert not any("legacy.json" in issue for issue in errors)
    assert any("current.json" in issue and "missing required key 'score'" in issue for issue in errors)


def test_default_enforce_mode_blocks_defective_fixture_contract(tmp_path, monkeypatch):
    """A hardening defect is blocking by default once copied into a live contracts tree."""
    repo = tmp_path
    (repo / ".git").mkdir()
    contract_dir = repo / "contracts" / "fixtures"
    schema_dir = repo / "contracts" / "schema"
    binding_dir = repo / "tests" / "contracts" / "fixtures"
    contract_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    binding_dir.mkdir(parents=True)

    (schema_dir / "contract.schema.yaml").write_text(
        (REPO_ROOT / "contracts" / "schema" / "contract.schema.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (contract_dir / "enforce-block-missing-enforcement.yaml").write_text(
        (FIXTURES / "enforce-block-missing-enforcement.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    (binding_dir / "fixture_binding_tests.py").write_text(
        "def test_enforce_block_missing_enforcement_fixture():\n    assert True\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(repo)

    assert contract_runner.main(["--validate-only"]) == 1


def test_path_specific_dispatch_filters_non_fitting_panel_json(tmp_path):
    """E6 path-specific dispatch excludes non-fitting panel outputs."""
    ov_contract = yaml.safe_load(
        (
            REPO_ROOT
            / "contracts"
            / "stochastic-tests"
            / "sample-provenance-ledger.yaml"
        ).read_text(encoding="utf-8")
    )
    schema_contract = yaml.safe_load(
        (
            REPO_ROOT
            / "contracts"
            / "stochastic-tests"
            / "sample-provenance-ledger-block.yaml"
        ).read_text(encoding="utf-8")
    )
    regression_dir = tmp_path / "results" / "panel_methodology" / "regression"
    regression_dir.mkdir(parents=True)
    non_fitting = regression_dir / "nssec_regime_crosstab_2099-01-01.json"
    fitting = regression_dir / "tier1_clustered_firth_2099-01-01.json"
    non_fitting.write_text("{}", encoding="utf-8")
    fitting.write_text("{}", encoding="utf-8")

    errors, hardening = contract_runner.gate_4_validate_jsons(
        [
            (Path("sample-provenance-ledger.yaml"), ov_contract),
            (Path("sample-provenance-ledger-block.yaml"), schema_contract),
        ],
        tmp_path,
        all_jsons=True,
    )

    assert hardening == []
    assert not any("nssec_regime_crosstab" in issue for issue in errors)
    assert any("tier1_clustered_firth" in issue and "sample_provenance" in issue for issue in errors)
