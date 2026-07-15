# Research context: contracts/README.md + contracts/stage1-output-schemas/
# Purpose: Pytest binding for the stage1-output-json-validation contract.
#   Validates every Stage-1 result JSON in the working tree against the
#   stage1-aggregate-output-cell schema. Passes trivially when no JSONs match.
"""Binding test for the stage1-output-json-validation contract.

Pairs one-to-one with
``contracts/stage1-output-schemas/stage1-output-json-validation.yaml``.

The pre-commit hook calls this test via ``pytest`` to gate JSON schema
fidelity at commit time. The test is independent of the hook *invocation*:
running ``pytest tests/trajectory_tda/test_stage1_output_json_validation.py``
directly performs the same validation against the on-disk JSONs.

It shares the hook's validator rather than reimplementing it. The earlier
reimplementation drifted: it honoured neither ``legacy_exempt`` nor
``exclude_filename_patterns`` nor the meta-schema's path-separator dispatch
branch, so the contract and its binding test disagreed about which files were
in scope. Sharing one validator means a scope rule can only be wrong in one
place.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "contract_binding_check.py"


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


def _load_contract(rel_path: str) -> dict:
    with (CONTRACTS_DIR / rel_path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_stage1_output_jsons_validate_against_aggregate_schema() -> None:
    """Validate every in-scope Stage-1 result JSON against the aggregate schema.

    Scope is decided by the contract: ``applies_to_glob`` selects candidates,
    then ``exclude_filename_patterns`` drops artifacts of a different kind and
    ``file_dispatch`` positively filters to the files this schema governs.
    Trivially passes when nothing is in scope (e.g. a fresh clone).
    """
    hook = _load_hook()
    ov_contract = _load_contract("stage1-output-schemas/stage1-output-json-validation.yaml")
    ov = ov_contract["output_validation"]
    glob_pattern = ov["applies_to_glob"]
    wrapper_key = ov.get("wrapper_key")

    failures: list[str] = []
    validated = 0
    for json_path in REPO_ROOT.rglob("*.json"):
        rel = json_path.relative_to(REPO_ROOT)
        if not rel.full_match(glob_pattern):
            continue
        if hook._is_legacy_exempt(ov_contract, rel):
            continue
        schema_id = hook._dispatch_schema_id(ov_contract, str(rel))
        if schema_id is None:
            # Excluded as a different artifact kind, or not positively
            # matched by file_dispatch. Pre-fix legacy JSONs and
            # different-shape Stage-1 outputs are deliberately out of scope.
            continue
        schema_contract = _load_contract(f"stage1-output-schemas/{schema_id}.yaml")
        errors, hardening = hook._validate_json_cells(json_path, schema_contract, REPO_ROOT, wrapper_key=wrapper_key)
        failures.extend(errors)
        failures.extend(hardening)
        validated += 1

    assert not failures, "Stage-1 JSON schema violations:\n  " + "\n  ".join(failures)

    # Guard against the exclusions silently emptying the contract's scope: if
    # any candidate matches the glob, at least one must still be validated.
    candidates = [p for p in REPO_ROOT.rglob("*.json") if p.relative_to(REPO_ROOT).full_match(glob_pattern)]
    if candidates:
        assert validated > 0, (
            f"{len(candidates)} JSON(s) match applies_to_glob '{glob_pattern}' but "
            f"exclude_filename_patterns/file_dispatch left none validated — the "
            f"contract has been narrowed into vacuity"
        )
