#!/usr/bin/env python3
# Research context: contracts/README.md
# Purpose: Pre-commit gate for math-correctness contracts. Validates contract
#   files against the meta-schema, verifies binding tests exist, runs the bound
#   tests via pytest, and validates staged output JSONs against schema contracts.
"""Math-correctness contract validator and pre-commit gate.

Runs four gates against the contracts/ framework:

1. Validate every contract YAML against contracts/schema/contract.schema.yaml.
2. Verify each contract's binding test_file exists and the named function is
   defined in it. Enforce the one-to-one binding rule.
3. Run pytest on all bound test functions in a single invocation.
4. Validate JSON files staged in the commit against their declared schema
   contracts via output_validation contracts.

Exit codes:
    0 — all gates passed; commit may proceed.
    1 — at least one gate failed; commit blocked with diagnostic on stderr.
    2 — framework-level error (missing contracts/, malformed meta-schema, etc.).

Invocation:
    contract_binding_check.py                # full pre-commit run
    contract_binding_check.py --validate-only # gates 1+2 only (skip pytest + JSONs)
    contract_binding_check.py --no-pytest     # gates 1+2+4 only
    contract_binding_check.py --all-jsons     # validate every output JSON in tree, not just staged
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import yaml


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) until a .git directory is found."""
    here = (start or Path.cwd()).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"No .git directory found above {here}")


def iter_contract_files(contracts_dir: Path):
    """Yield every contract YAML, skipping schema/ and manifests/ subtrees."""
    for path in sorted(contracts_dir.rglob("*.yaml")):
        rel = path.relative_to(contracts_dir)
        if rel.parts[0] in ("schema", "manifests"):
            continue
        yield path


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def gate_1_validate_meta(
    meta_schema: dict, contracts_dir: Path
) -> tuple[list[tuple[Path, dict]], list[str]]:
    """Validate every contract against the meta-schema. Return parsed contracts and errors."""
    parsed: list[tuple[Path, dict]] = []
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(meta_schema)
    for path in iter_contract_files(contracts_dir):
        try:
            data = load_yaml(path)
        except yaml.YAMLError as e:
            errors.append(f"[gate 1] {path}: YAML parse error: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"[gate 1] {path}: top-level value is not a mapping")
            continue
        # Filename stem must match `id`
        if data.get("id") != path.stem:
            errors.append(
                f"[gate 1] {path}: id field '{data.get('id')}' does not match filename stem '{path.stem}'"
            )
            continue
        violations = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if violations:
            for v in violations:
                loc = "/".join(str(p) for p in v.absolute_path) or "<root>"
                errors.append(f"[gate 1] {path}: {loc}: {v.message}")
            continue
        parsed.append((path, data))
    return parsed, errors


def _is_pending(c: dict) -> bool:
    return bool(c.get("pending", False))


def gate_2_verify_bindings(
    contracts: list[tuple[Path, dict]], repo_root: Path
) -> list[str]:
    """Verify each binding's test_file exists, function is defined, one-to-one.

    Skips contracts marked `pending: true` — those are still validated against
    the meta-schema in gate 1, but their binding artefacts are not required
    to exist yet (typically because the bound test lives on a feature branch
    not yet merged to the base branch).
    """
    errors: list[str] = []
    bindings_seen: dict[tuple[str, str], str] = {}
    for path, c in contracts:
        if _is_pending(c):
            continue
        binding = c["binding"]
        test_file_rel = binding["test_file"]
        test_function = binding["test_function"]
        test_file_abs = repo_root / test_file_rel

        if not test_file_abs.exists():
            errors.append(
                f"[gate 2] {c['id']}: binding.test_file does not exist: {test_file_rel}"
            )
            continue

        try:
            tree = ast.parse(test_file_abs.read_text(encoding="utf-8"))
        except SyntaxError as e:
            errors.append(
                f"[gate 2] {c['id']}: test_file is not valid Python: {test_file_rel}: {e}"
            )
            continue

        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if test_function not in functions:
            errors.append(
                f"[gate 2] {c['id']}: function '{test_function}' not defined in {test_file_rel}"
            )
            continue

        binding_key = (test_file_rel, test_function)
        if binding_key in bindings_seen:
            other = bindings_seen[binding_key]
            errors.append(
                f"[gate 2] one-to-one violation: contracts '{other}' and '{c['id']}' both "
                f"bind to {test_file_rel}::{test_function}"
            )
        else:
            bindings_seen[binding_key] = c["id"]
    return errors


def gate_3_run_bindings(
    contracts: list[tuple[Path, dict]], repo_root: Path
) -> list[str]:
    """Run pytest on every contract's binding function in a single invocation.

    Pending contracts are excluded — their bound tests may not exist yet.
    """
    active = [(p, c) for p, c in contracts if not _is_pending(c)]
    if not active:
        return []
    test_ids = [
        f"{c['binding']['test_file']}::{c['binding']['test_function']}"
        for _, c in active
    ]
    cmd = [
        "uv",
        "run",
        "pytest",
        "--no-header",
        "--tb=short",
        "-q",
        "--no-cov",  # contract bindings don't need coverage instrumentation
        *test_ids,
    ]
    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return []
    # Compact failure message; full output preserved in stderr
    out = proc.stdout.strip()
    err_tail = "\n".join(out.splitlines()[-30:])
    return [
        f"[gate 3] pytest exited with code {proc.returncode}; tail of output:\n{err_tail}"
    ]


def _dispatch_schema_id(ov_contract: dict, filename_rel: str) -> str | None:
    """Pick a schema contract id for a filename using file_dispatch.

    When `file_dispatch` is set, acts as a positive filter: only filenames
    matching one of the dispatch patterns are validated; unmatched filenames
    return None. When `file_dispatch` is absent, all files matching the
    applies_to_glob are validated against schema_contracts[0].
    """
    ov = ov_contract["output_validation"]
    fname_only = Path(filename_rel).name
    dispatch = ov.get("file_dispatch")
    if dispatch:
        for entry in dispatch:
            if Path(fname_only).match(entry["filename_pattern"]):
                return entry["schema_contract"]
        return None
    return ov["schema_contracts"][0]


def _validate_json_cells(
    json_path: Path,
    schema_contract: dict,
    repo_root: Path,
    wrapper_key: str | None = None,
) -> list[str]:
    """Apply schema_def required_keys + forbidden_keys to each cell in the JSON.

    If wrapper_key is set, descend into data[wrapper_key] before looking for
    cells. Required when the persisted JSON nests the schema target under a
    named field alongside metadata (e.g., 'result').
    """
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"[gate 4] {json_path.relative_to(repo_root)}: cannot load JSON: {e}"]

    if wrapper_key is not None:
        if not isinstance(data, dict) or wrapper_key not in data:
            return [
                f"[gate 4] {json_path.relative_to(repo_root)}: declared "
                f"wrapper_key '{wrapper_key}' not present at top level"
            ]
        scope = data[wrapper_key]
    else:
        scope = data

    schema_def = schema_contract["schema_def"]
    required = schema_def.get("required_keys", [])
    forbidden = schema_def.get("forbidden_keys", [])

    # Heuristic: if scope has h{N} keys, validate each as a cell.
    # Otherwise treat scope itself as the validation target.
    cells: dict[str, Any] = {}
    if isinstance(scope, dict):
        for k, v in scope.items():
            if (
                isinstance(k, str)
                and len(k) >= 2
                and k[0] == "h"
                and k[1:].isdigit()
                and isinstance(v, dict)
            ):
                cells[k] = v
    if not cells and isinstance(scope, dict):
        cells = {"<root>": scope}

    rel = json_path.relative_to(repo_root)
    errors: list[str] = []
    schema_id = schema_contract["id"]
    for cell_name, cell in cells.items():
        for key_spec in required:
            if key_spec["name"] not in cell:
                errors.append(
                    f"[gate 4] {rel}:{cell_name}: missing required key "
                    f"'{key_spec['name']}' (schema: {schema_id})"
                )
        for fk in forbidden:
            if fk["name"] in cell:
                errors.append(
                    f"[gate 4] {rel}:{cell_name}: forbidden key '{fk['name']}' "
                    f"present (reason: {fk['reason']}; schema: {schema_id})"
                )
    return errors


def gate_4_validate_jsons(
    contracts: list[tuple[Path, dict]], repo_root: Path, all_jsons: bool
) -> list[str]:
    """Validate JSON output files against their schema contracts."""
    ov_contracts = [c for _, c in contracts if c["kind"] == "output_validation"]
    if not ov_contracts:
        return []
    schema_by_id = {c["id"]: c for _, c in contracts if c["kind"] == "schema"}

    # Collect files to validate. Targets carry (path, schema_id, ov_id) so
    # we can recover the wrapper_key declared by the matching ov contract.
    targets: list[tuple[Path, str, str]] = []
    if all_jsons:
        for ov in ov_contracts:
            pattern = ov["output_validation"]["applies_to_glob"]
            for p in repo_root.rglob("*.json"):
                rel = p.relative_to(repo_root)
                if rel.full_match(pattern):
                    schema_id = _dispatch_schema_id(ov, str(rel))
                    if schema_id is None:
                        continue  # file_dispatch positive-filter rejected this file
                    targets.append((p, schema_id, ov["id"]))
    else:
        # Staged files via git
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            # Not in a commit context (e.g., manual run with no staged files).
            return []
        staged = [s for s in proc.stdout.splitlines() if s.endswith(".json")]
        for sf in staged:
            sf_path = Path(sf)
            for ov in ov_contracts:
                pattern = ov["output_validation"]["applies_to_glob"]
                if sf_path.full_match(pattern):
                    schema_id = _dispatch_schema_id(ov, sf)
                    if schema_id is None:
                        continue
                    targets.append((repo_root / sf, schema_id, ov["id"]))
                    break

    # Map ov_id -> wrapper_key for descent.
    wrapper_by_ov = {
        c["id"]: c["output_validation"].get("wrapper_key") for c in ov_contracts
    }

    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for json_path, schema_id, ov_id in targets:
        rel = json_path.relative_to(repo_root)
        key = (str(rel), schema_id)
        if key in seen:
            continue
        seen.add(key)
        schema_contract = schema_by_id.get(schema_id)
        if schema_contract is None:
            errors.append(
                f"[gate 4] {rel}: declared schema contract '{schema_id}' "
                f"not found among loaded schema contracts"
            )
            continue
        errors.extend(
            _validate_json_cells(
                json_path,
                schema_contract,
                repo_root,
                wrapper_key=wrapper_by_ov[ov_id],
            )
        )
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Math-correctness contract validator and pre-commit gate."
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run only gates 1 and 2 (skip pytest and JSON validation).",
    )
    parser.add_argument(
        "--no-pytest",
        action="store_true",
        help="Skip gate 3 (pytest of bindings); still run gate 4.",
    )
    parser.add_argument(
        "--all-jsons",
        action="store_true",
        help="Validate every output JSON in the working tree, not just staged files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo_root = find_repo_root()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    contracts_dir = repo_root / "contracts"
    if not contracts_dir.exists():
        print("contracts/ directory not found at repo root", file=sys.stderr)
        return 2

    meta_schema_path = contracts_dir / "schema" / "contract.schema.yaml"
    if not meta_schema_path.exists():
        print(f"meta-schema not found: {meta_schema_path}", file=sys.stderr)
        return 2
    try:
        meta_schema = load_yaml(meta_schema_path)
    except yaml.YAMLError as e:
        print(f"ERROR: meta-schema is unparseable YAML: {e}", file=sys.stderr)
        return 2

    contracts, errs = gate_1_validate_meta(meta_schema, contracts_dir)
    errors: list[str] = list(errs)

    errors.extend(gate_2_verify_bindings(contracts, repo_root))

    # Gates 3 and 4 only run if 1 and 2 passed (avoids confusing noise stack).
    if not errors:
        if not args.validate_only and not args.no_pytest:
            errors.extend(gate_3_run_bindings(contracts, repo_root))
        if not args.validate_only:
            errors.extend(gate_4_validate_jsons(contracts, repo_root, args.all_jsons))

    if errors:
        print(
            "Contract framework: pre-commit gate FAILED with "
            f"{len(errors)} issue(s):",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        print(
            "\nSee contracts/README.md for the framework, or "
            "`git commit --no-verify` only in a documented emergency.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Contract framework: all gates passed against {len(contracts)} contract(s).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
