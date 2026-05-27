# Research context: contracts/README.md + contracts/stage1-output-schemas/
# Purpose: Pytest binding for the stage1-output-json-validation contract.
#   Validates every Stage-1 result JSON in the working tree against the
#   stage1-aggregate-output-cell schema. Passes trivially when no JSONs match.
"""Binding test for the stage1-output-json-validation contract.

Pairs one-to-one with
``contracts/stage1-output-schemas/stage1-output-json-validation.yaml``.

The pre-commit hook calls this test via ``pytest`` to gate JSON schema
fidelity at commit time. The test is independent of the hook: invoking
``pytest tests/trajectory_tda/test_stage1_output_json_validation.py``
directly performs the same validation against the on-disk JSONs.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _h_cells(scope: dict) -> dict[str, dict]:
    """Return {'h0': ..., 'h1': ...} cells from a stage-1 JSON scope."""
    return {
        k: v
        for k, v in scope.items()
        if isinstance(k, str)
        and len(k) >= 2
        and k[0] == "h"
        and k[1:].isdigit()
        and isinstance(v, dict)
    }


def _descend(data: dict, wrapper_key: str | None) -> dict | None:
    """Apply wrapper_key descent if declared. None means wrapper missing."""
    if wrapper_key is None:
        return data
    if not isinstance(data, dict) or wrapper_key not in data:
        return None
    return data[wrapper_key]


def _matched_jsons(glob_pattern: str) -> list[Path]:
    """Find JSONs in the working tree matching the contract's applies_to_glob."""
    matched: list[Path] = []
    for path in REPO_ROOT.rglob("*.json"):
        rel = path.relative_to(REPO_ROOT)
        if rel.full_match(glob_pattern):
            matched.append(path)
    return matched


def _dispatch_filter(file_dispatch: list[dict] | None, json_path: Path) -> bool:
    """Positive filter: when file_dispatch is set, only validate filenames
    matching one of the dispatch patterns. Returns True if the file should
    be validated.
    """
    if not file_dispatch:
        return True
    fname = json_path.name
    return any(Path(fname).match(entry["filename_pattern"]) for entry in file_dispatch)


def test_stage1_output_jsons_validate_against_aggregate_schema() -> None:
    """Validate every Stage-1 result JSON against the aggregate cell schema.

    Trivially passes when no matching JSONs exist (e.g., fresh clone).
    """
    output_validation = _load_contract(
        "stage1-output-schemas/stage1-output-json-validation.yaml"
    )
    ov = output_validation["output_validation"]
    schema_id = ov["schema_contracts"][0]
    glob_pattern = ov["applies_to_glob"]
    wrapper_key = ov.get("wrapper_key")
    file_dispatch = ov.get("file_dispatch")

    # Load the referenced schema contract
    schema_contract = _load_contract(f"stage1-output-schemas/{schema_id}.yaml")
    schema_def = schema_contract["schema_def"]
    required_key_names = [k["name"] for k in schema_def["required_keys"]]
    forbidden = schema_def.get("forbidden_keys", [])

    jsons = _matched_jsons(glob_pattern)
    # Apply the positive-filter file_dispatch (when declared) to narrow to
    # files actually covered by the schema. Pre-fix legacy JSONs and
    # different-shape Stage-1 outputs are deliberately not in scope.
    jsons = [j for j in jsons if _dispatch_filter(file_dispatch, j)]
    if not jsons:
        # Pass trivially — framework is correctly installed but tree has no
        # matching JSONs. Common on a fresh clone or in CI before any
        # computational task has run.
        return

    failures: list[str] = []
    for json_path in jsons:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            failures.append(f"{json_path}: cannot load JSON: {e}")
            continue

        scope = _descend(data, wrapper_key)
        if scope is None:
            failures.append(
                f"{json_path}: declared wrapper_key '{wrapper_key}' "
                f"not present at top level"
            )
            continue

        cells = _h_cells(scope)
        if not cells:
            location = (
                f"under '{wrapper_key}'" if wrapper_key else "at top level"
            )
            failures.append(
                f"{json_path}: no h0/h1 cells found {location}; "
                f"output does not match the aggregate cell schema shape"
            )
            continue

        for cell_name, cell in cells.items():
            for key in required_key_names:
                if key not in cell:
                    failures.append(
                        f"{json_path}:{cell_name}: missing required key '{key}'"
                    )
            for fk in forbidden:
                if fk["name"] in cell:
                    failures.append(
                        f"{json_path}:{cell_name}: forbidden key '{fk['name']}' "
                        f"present (reason: {fk['reason']})"
                    )

        # Conditional key: lower_tail_pvalue is required on the h0 cell only.
        if "h0" in cells and "lower_tail_pvalue" not in cells["h0"]:
            failures.append(
                f"{json_path}:h0: missing conditional key 'lower_tail_pvalue' "
                f"(required when dim == 0)"
            )

    assert not failures, "Stage-1 JSON schema violations:\n  " + "\n  ".join(failures)
