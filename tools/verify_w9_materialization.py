# Research context: docs/plans/agentic-research-system/transition/w9/wp9-1-stage-b-design-note.md (WP9.1 B1; P-072)
# Purpose: derive the W9 catalogue's expected rows from the owner annex at a pinned commit and verify a catalogue.
"""Materialization verifier for the W9 catalogue (WP9.1 stage B; P-072 item 7).

This is a non-runtime tool. It reads the owner annex at a pinned Git commit, checks the annex's own rules, derives
each expected catalogue row by the annex's ``derivation_rules``, and, when a catalogue exists, compares it with the
derived rows field by field, as W11's verifier does from its owner table. It writes nothing.

Usage::

    python tools/verify_w9_materialization.py [--annex-commit HEAD] [--catalogue PATH]

Without ``--catalogue`` it verifies the annex only (stage B1). In stage B2 the catalogue names its own annex commit,
and that commit is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ANNEX_PATH = "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
CATALOGUE_PATH = ".research-system/evals/expected/w9-legacy-integration-v1.json"
SCHEMA_DIR = ".research-system/schemas/contracts/w9"
CATALOGUE_SCHEMA = f"{SCHEMA_DIR}/w9-schema-catalogue-content.schema.json"

ACTORS = {
    "migration_analyst",
    "membership_author",
    "observer",
    "independent_reviewer",
    "stephen",
    "operator",
    "system_guard",
}
W9C_REASONS = {"authority_flow_step", "discharge_no_w9_test"}
DERIVED_FIELDS = (
    "logical_key",
    "complete_write_set",
    "receipt_identity",
    "positive_test_identity",
    "negative_mutation_test_identity",
    "retry_test_identity",
    "owner_annex_ref",
)
# Annex fields copied to the catalogue row unchanged; ``source_refs`` stays in the annex as provenance.
COPIED_FIELDS = (
    "owner_row_id",
    "command_type",
    "payload_discriminant",
    "record_schema_id",
    "record_schema_version",
    "eligible_actor",
    "requester",
    "resolver",
    "authority_subject",
    "preconditions",
    "ordered_events",
    "affected_streams",
    "projection_targets",
    "reducer",
    "binding_tests",
    "w9c_only_reason",
    "pilot_promotion_fixtures",
)


class VerificationError(ValueError):
    """Raised when the annex or the catalogue fails verification."""


def canonical_json(value: Any) -> bytes:
    """Serialize with sorted keys and no whitespace, as the annex's derivation rules define a row hash."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Return the hex SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def _git(*args: str, binary: bool = False) -> Any:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, check=True)
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def annex_identity(commit: str) -> dict[str, Any]:
    """Return the annex's file identity at ``commit``: path, commit, blob, length and SHA-256.

    Args:
        commit: A Git revision; resolved to a full commit SHA.

    Returns:
        A ``CODE_IDENTITY``-shaped mapping for the annex at that commit.
    """
    full = _git("rev-parse", f"{commit}^{{commit}}")
    data = _git("show", f"{full}:{ANNEX_PATH}", binary=True)
    return {
        "repository_path": ANNEX_PATH,
        "git_commit": full,
        "git_blob": _git("rev-parse", f"{full}:{ANNEX_PATH}"),
        "file_length": len(data),
        "file_sha256": sha256_hex(data),
    }


def load_annex(commit: str) -> dict[str, Any]:
    """Load the annex as committed at ``commit``."""
    return yaml.safe_load(_git("show", f"{commit}:{ANNEX_PATH}", binary=True).decode("utf-8"))


def check_annex(annex: dict[str, Any], record_schema_ids: set[str]) -> list[str]:
    """Check the annex's own rules and return every problem found (empty when it passes).

    Args:
        annex: The parsed annex.
        record_schema_ids: The ``$id`` of every committed ``ars://legacy/`` schema.

    Returns:
        A list of human-readable problems.
    """
    problems: list[str] = []
    rows = annex.get("rows", [])
    known_c = {name for name in annex.get("catalogue_tests", {}) if re.fullmatch(r"W9-C2[0-9]", name)}
    ids = [row.get("owner_row_id") for row in rows]
    if ids != [f"LR-{n:03d}" for n in range(1, len(rows) + 1)]:
        problems.append("owner_row_id values are not LR-001 onward, contiguous and unique")
    keys = [row.get("payload_discriminant") for row in rows]
    if len(set(keys)) != len(keys):
        problems.append("payload_discriminant values are not unique")
    # The annex also states logical_key and receipt_identity; they must equal their derivations.
    annex_fields = frozenset((*COPIED_FIELDS, "source_refs", "logical_key", "receipt_identity"))
    if {frozenset(row) for row in rows} != {annex_fields}:
        problems.append("rows do not all carry exactly the annex row fields")
    for row in rows:
        rid = row.get("owner_row_id")
        if row.get("logical_key") != row.get("payload_discriminant"):
            problems.append(f"{rid}: logical_key is not the payload_discriminant")
        if row.get("receipt_identity") != f"R:{row.get('payload_discriminant')}":
            problems.append(f"{rid}: receipt_identity is not R:<logical_key>")
        tests = row.get("binding_tests") or []
        has_t = False
        for test in tests:
            match_t = re.fullmatch(r"W9-T([0-9]+)", test)
            if match_t:
                has_t = True
                if not 1 <= int(match_t.group(1)) <= 23:
                    problems.append(f"{rid}: {test} is outside W9 §17 (W9-T1 to W9-T23)")
            elif test not in known_c:
                problems.append(f"{rid}: {test} is not a declared W9-C2x catalogue test")
        reason = row.get("w9c_only_reason")
        if has_t and reason is not None:
            problems.append(f"{rid}: a row with a W9-T test carries a w9c_only_reason")
        if not has_t and reason not in W9C_REASONS:
            problems.append(f"{rid}: a row with no W9-T test needs a w9c_only_reason")
        if not has_t and not any(test.startswith("W9-C2") for test in tests):
            problems.append(f"{rid}: a row with no W9-T test must bind a W9-C2x test")
        for fixture in row.get("pilot_promotion_fixtures") or []:
            match_f = re.fullmatch(r"([FS])-([0-9]{3})", fixture.get("fixture_id", ""))
            limit = {"F": 38, "S": 17}.get(match_f.group(1)) if match_f else None
            if not limit or not 1 <= int(match_f.group(2)) <= limit:
                problems.append(f"{rid}: fixture {fixture} is outside F-001 to F-038 and S-001 to S-017")
        for event in row.get("ordered_events") or []:
            if not re.fullmatch(r"(E|W2):[A-Za-z0-9-]+", event.get("event", "")):
                problems.append(f"{rid}: event token {event.get('event')!r} is malformed")
            if event.get("multiplicity") not in ("1", "0..n"):
                problems.append(f"{rid}: event multiplicity {event.get('multiplicity')!r} is not 1 or 0..n")
            if event.get("multiplicity") == "0..n" and not event.get("condition"):
                problems.append(f"{rid}: a 0..n event needs its condition")
        if row.get("eligible_actor") not in ACTORS:
            problems.append(f"{rid}: eligible_actor {row.get('eligible_actor')!r} is not in the closed set")
        if row.get("requester") is not None and row.get("requester") not in ACTORS:
            problems.append(f"{rid}: requester {row.get('requester')!r} is not in the closed set")
        if row.get("record_schema_id") not in record_schema_ids:
            problems.append(f"{rid}: record_schema_id {row.get('record_schema_id')!r} is not a committed schema")
    return problems


def derive_row(annex_row: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    """Derive one expected catalogue row from one annex row, by the annex's derivation rules.

    Args:
        annex_row: One row of the annex.
        identity: The annex's file identity at its pinned commit (see :func:`annex_identity`).

    Returns:
        The expected catalogue row, with every one of the 24 catalogue fields.
    """
    rid = annex_row["owner_row_id"]
    row = {field: annex_row[field] for field in COPIED_FIELDS}
    row["logical_key"] = annex_row["payload_discriminant"]
    row["complete_write_set"] = [event["event"] for event in annex_row["ordered_events"]] + list(
        annex_row["affected_streams"]
    )
    row["receipt_identity"] = f"R:{annex_row['payload_discriminant']}"
    row["positive_test_identity"] = f"W9-C01-{rid}"
    row["negative_mutation_test_identity"] = f"W9-C03-{rid}-owner-row-mutation"
    row["retry_test_identity"] = f"W9-C11-{rid}"
    row["owner_annex_ref"] = {
        "repository_path": identity["repository_path"],
        "git_commit": identity["git_commit"],
        "git_blob": identity["git_blob"],
        "file_sha256": identity["file_sha256"],
        "row_sha256": sha256_hex(canonical_json(annex_row)),
    }
    return row


def expected_rows(annex: dict[str, Any], identity: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive every expected catalogue row, in annex order."""
    return [derive_row(row, identity) for row in annex["rows"]]


def compare_catalogue(catalogue: dict[str, Any], annex: dict[str, Any], identity: dict[str, Any]) -> list[str]:
    """Compare a catalogue with the annex-derived expectation and return every difference.

    Args:
        catalogue: The parsed catalogue content.
        annex: The parsed annex at the catalogue's pinned annex commit.
        identity: The annex's file identity at that commit.

    Returns:
        A list of human-readable differences (empty when the catalogue matches).
    """
    problems: list[str] = []
    expected = expected_rows(annex, identity)
    actual = catalogue.get("owner_contract_rows", [])
    if catalogue.get("owner_annex_identity") != identity:
        problems.append("owner_annex_identity does not equal the annex's identity at its pinned commit")
    if catalogue.get("global_preconditions") != annex.get("global_preconditions"):
        problems.append("global_preconditions differ from the annex")
    if catalogue.get("owner_row_count") != len(expected):
        problems.append(f"owner_row_count {catalogue.get('owner_row_count')} != {len(expected)}")
    if catalogue.get("owner_row_range_hash") != sha256_hex(canonical_json(actual)):
        problems.append("owner_row_range_hash is not the SHA-256 of the rows' canonical JSON")
    if len(actual) != len(expected):
        problems.append(f"{len(actual)} rows in the catalogue, {len(expected)} derived from the annex")
    for want, got in zip(expected, actual, strict=False):
        rid = want["owner_row_id"]
        if got.keys() != want.keys():
            problems.append(f"{rid}: field set differs: {sorted(set(got) ^ set(want))}")
            continue
        for field, value in want.items():
            if got[field] != value:
                problems.append(f"{rid}: field {field} differs from the annex-derived value")
    return problems


def committed_record_schema_ids() -> set[str]:
    """Return the ``$id`` of every committed W9 schema in the working tree."""
    return {
        json.loads(path.read_text(encoding="utf-8"))["$id"] for path in (REPO_ROOT / SCHEMA_DIR).glob("*.schema.json")
    }


def main(argv: list[str] | None = None) -> int:
    """Verify the annex, and the catalogue when one is given or present.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        0 when everything verifies; 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--annex-commit", default="HEAD")
    parser.add_argument("--catalogue", type=Path)
    args = parser.parse_args(argv)
    catalogue_path = args.catalogue or (REPO_ROOT / CATALOGUE_PATH)
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8")) if catalogue_path.exists() else None
    commit = catalogue["owner_annex_identity"]["git_commit"] if catalogue else args.annex_commit
    annex = load_annex(commit)
    identity = annex_identity(commit)
    problems = check_annex(annex, committed_record_schema_ids())
    if catalogue is not None:
        problems += compare_catalogue(catalogue, annex, identity)
    for problem in problems:
        print(problem, file=sys.stderr)
    scope = "annex and catalogue" if catalogue is not None else "annex"
    print(f"{scope}: {len(annex['rows'])} rows at {identity['git_commit'][:8]}; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
