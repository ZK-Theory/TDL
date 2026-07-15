# Research context: contracts/stage1-output-schemas/ + WT-6 exact-W2 re-derivation (commit b17d9da)
# Purpose: Pytest bindings for the two corrected-headline contracts.
#   Validates every WT-6 exact-W2 corrected-headline artifact in the working
#   tree against its own cell schema, and asserts that the corrected-headline
#   and Stage-1 battery contracts partition their shared glob exactly.
"""Binding tests for the corrected-headline contracts.

Pairs one-to-one with:

* ``contracts/stage1-output-schemas/w2-exact-corrected-headline-cell.yaml``
  (``test_corrected_headline_cell_schema``)
* ``contracts/stage1-output-schemas/w2-exact-corrected-headline-json-validation.yaml``
  (``test_corrected_headline_jsons_validate_against_cell_schema``)

These tests drive the *same* validator the pre-commit hook uses
(``.claude/hooks/contract_binding_check.py``) rather than reimplementing cell
descent and type checking. A reimplementation is what let the scope rules
drift apart in the first place: the earlier
``test_stage1_output_json_validation.py`` honoured neither ``legacy_exempt``
nor the meta-schema's path-separator dispatch branch, so contract and binding
disagreed about which files were in scope. Both bindings now share one
validator.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts" / "stage1-output-schemas"
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "contract_binding_check.py"

CELL_SCHEMA_ID = "w2-exact-corrected-headline-cell"
CORRECTED_OV_ID = "w2-exact-corrected-headline-json-validation"
STAGE1_OV_ID = "stage1-output-json-validation"


def _load_hook() -> ModuleType:
    """Import the pre-commit contract validator as a module.

    ``.claude/hooks`` is not an importable package, so load it by path.
    """
    spec = importlib.util.spec_from_file_location("contract_binding_check", HOOK_PATH)
    if spec is None or spec.loader is None:
        pytest.fail(f"cannot load the contract validator from {HOOK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract(contract_id: str) -> dict:
    with (CONTRACTS_DIR / f"{contract_id}.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    return [p for p in REPO_ROOT.rglob("*.json") if p.relative_to(REPO_ROOT).full_match(glob_pattern)]


def _corrected_headline_jsons() -> list[Path]:
    """Working-tree files claimed by the corrected-headline contract."""
    hook = _load_hook()
    ov = _load_contract(CORRECTED_OV_ID)
    glob_pattern = ov["output_validation"]["applies_to_glob"]
    return [
        p
        for p in _matched_jsons(glob_pattern)
        if hook._dispatch_schema_id(ov, str(p.relative_to(REPO_ROOT))) is not None
    ]


def _minimal_valid_cell() -> dict:
    """A corrected-headline h1 cell carrying every required key."""
    return {
        "committed_greedy": {"mean_obs_null": 190.6, "w2_pvalue": 0.019},
        "corrected_exact": {"mean_obs_null": 7.09, "w2_pvalue": 0.000999},
        "diagonal_bound_mean": 19.7,
        "diagonal_bound_max": 20.3,
        "committed_exceeds_diagonal_bound": True,
        "rejection_at_alpha_0.05": {
            "committed": True,
            "corrected": True,
            "flips": False,
        },
        "per_pair": {
            "obs_null_exact": [6.8, 7.1],
            "null_null_exact": [3.2, 3.3],
            "null_null_pair_indices": [[0, 1], [2, 3]],
        },
    }


def _validate_payload(payload: dict, tmp_path: Path) -> list[str]:
    """Run the hook's gate-4 cell validation over an in-memory artifact."""
    hook = _load_hook()
    schema_contract = _load_contract(CELL_SCHEMA_ID)
    tmp_path.mkdir(parents=True, exist_ok=True)
    json_path = tmp_path / "bhps_headline_frozen_corrected_2099-01-01.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    ov = _load_contract(CORRECTED_OV_ID)
    errors, hardening = hook._validate_json_cells(
        json_path,
        schema_contract,
        tmp_path,
        wrapper_key=ov["output_validation"].get("wrapper_key"),
    )
    return errors + hardening


def test_corrected_headline_cell_schema(tmp_path: Path) -> None:
    """Every required key is enforced on every corrected-headline cell.

    Positive case: a complete cell validates clean. Negative cases: dropping
    any single required key, or mistyping one, is rejected — the schema must
    not pass a truncated artifact over silently.
    """
    schema_contract = _load_contract(CELL_SCHEMA_ID)
    required = [k["name"] for k in schema_contract["schema_def"]["required_keys"]]

    # The schema must actually name the fields a P01 H1 claim reads.
    assert set(required) == {
        "committed_greedy",
        "corrected_exact",
        "diagonal_bound_mean",
        "diagonal_bound_max",
        "committed_exceeds_diagonal_bound",
        "rejection_at_alpha_0.05",
        "per_pair",
    }

    # Positive: a complete cell passes.
    assert not _validate_payload({"h1": _minimal_valid_cell()}, tmp_path / "ok")

    # Negative: dropping any one required key is caught.
    for key in required:
        cell = _minimal_valid_cell()
        del cell[key]
        issues = _validate_payload({"h1": cell}, tmp_path / f"missing_{key.replace('.', '_')}")
        assert any(key in issue for issue in issues), f"dropping required key '{key}' was not rejected"

    # Negative: a mistyped key is caught by the strengthened type check.
    cell = _minimal_valid_cell()
    cell["committed_exceeds_diagonal_bound"] = "yes"
    issues = _validate_payload({"h1": cell}, tmp_path / "mistyped")
    assert any("committed_exceeds_diagonal_bound" in issue for issue in issues), (
        "a str in place of the declared bool was not rejected"
    )


def test_corrected_headline_jsons_validate_against_cell_schema(
    tmp_path: Path,
) -> None:
    """Working-tree corrected-headline artifacts conform, and the glob partitions.

    Trivially passes the conformance half when no matching JSONs exist (e.g.
    on a fresh clone); the partition half is checked against the contracts
    themselves and always runs.
    """
    hook = _load_hook()
    corrected_ov = _load_contract(CORRECTED_OV_ID)
    stage1_ov = _load_contract(STAGE1_OV_ID)
    schema_contract = _load_contract(CELL_SCHEMA_ID)

    # The two contracts share a glob; they must partition it, never overlap.
    glob_pattern = corrected_ov["output_validation"]["applies_to_glob"]
    assert glob_pattern == stage1_ov["output_validation"]["applies_to_glob"], (
        "partition check assumes both contracts share one applies_to_glob"
    )

    failures: list[str] = []
    for json_path in _matched_jsons(glob_pattern):
        rel = str(json_path.relative_to(REPO_ROOT))
        claimed_by_corrected = hook._dispatch_schema_id(corrected_ov, rel) is not None
        claimed_by_stage1 = hook._dispatch_schema_id(stage1_ov, rel) is not None
        if claimed_by_corrected and claimed_by_stage1:
            failures.append(
                f"{rel}: claimed by BOTH {CORRECTED_OV_ID} and {STAGE1_OV_ID}; "
                f"the exclusion and dispatch patterns overlap"
            )

    # Conformance: every artifact this contract claims validates against the
    # cell schema via the same validator the pre-commit hook runs.
    for json_path in _corrected_headline_jsons():
        errors, hardening = hook._validate_json_cells(
            json_path,
            schema_contract,
            REPO_ROOT,
            wrapper_key=corrected_ov["output_validation"].get("wrapper_key"),
        )
        failures.extend(errors)
        failures.extend(hardening)

        data = json.loads(json_path.read_text(encoding="utf-8"))
        if "result" in data:
            failures.append(
                f"{json_path.relative_to(REPO_ROOT)}: carries a top-level 'result' "
                f"wrapper, which is the Stage-1 battery discriminator; a "
                f"corrected-headline artifact must not adopt it"
            )

    assert not failures, "Corrected-headline contract violations:\n  " + "\n  ".join(failures)
