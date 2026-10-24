# Research context: docs/plans/agentic-research-system/transition/w9/wp9-1-stage-b-design-note.md (WP9.1 B1; P-072, P-074)
# Purpose: derive the W9 catalogue's expected rows from the pinned owner annex and verify a catalogue against them.
"""Materialization verifier for the W9 catalogue (WP9.1 stage B; P-072 item 7).

This is a non-runtime tool. Its expected side is independent of the catalogue under test, as W11's is:

- the owner annex is pinned here by Git blob, SHA-256 and size, and its owner-row ID set and command-type set are
  pinned too. A catalogue cannot choose the annex it is compared against (B1 review B-2);
- the schema source rows, the owner specification and plan identities and the catalogue's own identities are derived
  here from Git and the bootstrap contract. The catalogue is validated against its schema, and its ``content_hash`` is
  recomputed (B1 review B-1).

Usage::

    python tools/verify_w9_materialization.py [--catalogue PATH] [--require-catalogue] [--main-ref origin/main]

Without a catalogue it verifies the pinned annex only. ``--require-catalogue`` (stage B2 onward) makes an absent
catalogue a failure. It writes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from research_system.canonical import canonical_bytes, sha256_hex

REPO_ROOT = Path(__file__).resolve().parents[1]
ANNEX_PATH = "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
CATALOGUE_PATH = ".research-system/evals/expected/w9-legacy-integration-v1.json"
CONTRACT_PATH = ".research-system/contracts/w9/w9-materialization-bootstrap-contract.yaml"
SCHEMA_DIR = ".research-system/schemas/contracts/w9"
CATALOGUE_SCHEMA = f"{SCHEMA_DIR}/w9-schema-catalogue-content.schema.json"

# The owner annex as confirmed and folded (stage B design note revision 3; P-072 item 6). Any annex change is a
# reviewed change to these constants (B1 review B-2).
W9_ANNEX_BLOB = "d8fbda416b016f5e19c03689f336caff3166d0d9"
W9_ANNEX_SHA256 = "36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc"
W9_ANNEX_BYTES = 85664
W9_OWNER_ROW_IDS = tuple(f"LR-{n:03d}" for n in range(1, 62))
W9_COMMAND_TYPES = frozenset(
    {
        "ImportAcceptedW9CatalogueGenesis",
        "ImportAcceptedW9CatalogueRevision",
        "ProposeLegacyRecord",
        "RequestW9AuthorityReview",
        "RecordW9AuthorityReview",
        "ProposeW9AuthorityDecision",
        "ResolveW9AuthorityDecision",
        "RecordLegacyLightInventory",
        "ObserveLegacyRecord",
        "CreateLegacyPaperRoot",
        "RecordPaperCitationStatus",
        "RecordAdoptionUseMismatch",
    }
)
W9_RECORD_KINDS = frozenset(
    {
        "legacy-path-registration",
        "legacy-field-family-membership",
        "legacy-light-inventory",
        "legacy-observation",
        "legacy-closed-reference-acceptance",
        "legacy-adoption-decision",
        "legacy-discharge-relation",
        "legacy-paper-root",
        "legacy-paper-citation-status",
        "legacy-source-inventory",
        "legacy-transition-mapping",
        "legacy-ownership-transitioned",
        "legacy-record-supersession",
        "legacy-adoption-use-mismatch",
    }
)
W9_IMPORT_KINDS = frozenset({"import-accepted-w9-catalogue-genesis", "import-accepted-w9-catalogue-revision"})
W9_CATALOGUE_TESTS = frozenset({"W9-C01", "W9-C03", "W9-C11", *(f"W9-C2{n}" for n in range(6))})
# The catalogue's own record identities, pinned as W11 pins its own (verify_w11_materialization.py:39-41).
W9_CATALOGUE_RECORD_ID = "obj_00000000-0000-7000-8000-000000000009"
W9_CATALOGUE_PROJECT_ID = "prj_00000000-0000-7000-8000-000000000001"
W9_CATALOGUE_ACTOR_ID = "act_00000000-0000-7000-8000-000000000001"

ACTORS = frozenset(
    {
        "migration_analyst",
        "membership_author",
        "observer",
        "independent_reviewer",
        "stephen",
        "operator",
        "system_guard",
    }
)
W9C_REASONS = frozenset({"authority_flow_step", "discharge_no_w9_test"})
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
DERIVED_FIELDS = (
    "logical_key",
    "complete_write_set",
    "receipt_identity",
    "positive_test_identity",
    "negative_mutation_test_identity",
    "retry_test_identity",
    "owner_annex_ref",
)
ANNEX_ROW_FIELDS = frozenset((*COPIED_FIELDS, "source_refs", "logical_key", "receipt_identity"))


class _StrictLoader(yaml.SafeLoader):
    """A safe YAML loader that refuses a duplicate mapping key (B1 review m-1)."""


def _construct_mapping(loader: _StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    keys = [loader.construct_object(key, deep=deep) for key, _ in node.value]
    duplicates = {key for key in keys if keys.count(key) > 1}
    if duplicates:
        raise yaml.constructor.ConstructorError(None, None, f"duplicate key(s) {sorted(duplicates)}", node.start_mark)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def strict_yaml(data: bytes) -> Any:
    """Parse YAML, refusing duplicate keys."""
    return yaml.load(data.decode("utf-8"), Loader=_StrictLoader)  # noqa: S506 - SafeLoader subclass


# Git reads are cached for the life of one process: every read names a commit or blob, whose bytes never change, or a
# ref (HEAD, the main ref), which a single verification run treats as fixed.
@lru_cache(maxsize=None)
def _git(*args: str, binary: bool = False) -> Any:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, check=True)
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


@lru_cache(maxsize=None)
def _git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, check=False).returncode == 0


def is_ancestor(commit: str, ref: str) -> bool:
    """Return whether ``commit`` is an ancestor of (or equal to) ``ref``."""
    return _git_ok("merge-base", "--is-ancestor", commit, ref)


def resolve_commit(revision: str) -> str | None:
    """Return the full commit SHA for ``revision``, or None when it does not resolve."""
    if not _git_ok("rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"):
        return None
    return _git("rev-parse", f"{revision}^{{commit}}")


def pinned_annex_bytes() -> bytes:
    """Return the pinned annex's bytes, read by blob, and check its SHA-256 and size."""
    data = _git("cat-file", "blob", W9_ANNEX_BLOB, binary=True)
    if sha256_hex(data) != W9_ANNEX_SHA256 or len(data) != W9_ANNEX_BYTES:
        raise ValueError("the pinned annex blob does not match its pinned SHA-256 and size")
    return data


@lru_cache(maxsize=1)
def _parsed_pinned_annex() -> dict[str, Any]:
    return strict_yaml(pinned_annex_bytes())


def pinned_annex() -> dict[str, Any]:
    """Return a fresh copy of the pinned annex, parsed strictly."""
    return deepcopy(_parsed_pinned_annex())


def annex_identity(commit: str) -> dict[str, Any]:
    """Return the annex's identity at ``commit`` (path, commit, blob, length, SHA-256)."""
    data = _git("show", f"{commit}:{ANNEX_PATH}", binary=True)
    return {
        "repository_path": ANNEX_PATH,
        "git_commit": commit,
        "git_blob": _git("rev-parse", f"{commit}:{ANNEX_PATH}"),
        "file_length": len(data),
        "file_sha256": sha256_hex(data),
    }


def check_annex(annex: Any) -> list[str]:
    """Check the annex's own rules and the pinned row, command and test sets.

    Args:
        annex: The parsed annex.

    Returns:
        A list of human-readable problems, empty when the annex passes.
    """
    if not isinstance(annex, dict) or not isinstance(annex.get("rows"), list):
        return ["the annex is not a mapping with a rows list"]
    problems: list[str] = []
    rows = annex["rows"]
    if set(annex.get("catalogue_tests", {})) != W9_CATALOGUE_TESTS:
        problems.append("catalogue_tests is not exactly P-073's W9-C01, W9-C03, W9-C11 and W9-C20 to W9-C25")
    if tuple(row.get("owner_row_id") for row in rows) != W9_OWNER_ROW_IDS:
        problems.append("owner_row_id values are not exactly LR-001 to LR-061, contiguous")
    keys = [row.get("payload_discriminant") for row in rows]
    if len(set(keys)) != len(keys):
        problems.append("payload_discriminant values are not unique")
    if {frozenset(row) for row in rows} != {ANNEX_ROW_FIELDS}:
        problems.append("rows do not all carry exactly the annex row fields")
    if {row.get("command_type") for row in rows} != W9_COMMAND_TYPES:
        problems.append("the command-type set is not the pinned twelve")
    named = {str(row.get("record_schema_id", "")).removeprefix("ars://legacy/") for row in rows}
    if not W9_RECORD_KINDS <= named:
        problems.append(f"record kinds named by no row: {sorted(W9_RECORD_KINDS - named)}")
    c2x = {name for name in W9_CATALOGUE_TESTS if name.startswith("W9-C2")}
    for row in rows:
        problems += _check_row(row, c2x)
    return problems


def _check_row(row: dict[str, Any], c2x: set[str]) -> list[str]:
    rid = row.get("owner_row_id")
    problems: list[str] = []
    if row.get("logical_key") != row.get("payload_discriminant"):
        problems.append(f"{rid}: logical_key is not the payload_discriminant")
    if row.get("receipt_identity") != f"R:{row.get('payload_discriminant')}":
        problems.append(f"{rid}: receipt_identity is not R:<logical_key>")
    kind = str(row.get("record_schema_id", "")).removeprefix("ars://legacy/")
    if kind not in W9_RECORD_KINDS | W9_IMPORT_KINDS or not str(row.get("record_schema_id")).startswith(
        "ars://legacy/"
    ):
        problems.append(f"{rid}: record_schema_id {row.get('record_schema_id')!r} is not a W9 record or import schema")
    if row.get("record_schema_version") != "1.0.0":
        problems.append(f"{rid}: record_schema_version is not 1.0.0")
    if row.get("eligible_actor") not in ACTORS:
        problems.append(f"{rid}: eligible_actor {row.get('eligible_actor')!r} is not in the closed set")
    if row.get("requester") is not None and row.get("requester") not in ACTORS:
        problems.append(f"{rid}: requester {row.get('requester')!r} is not in the closed set")
    if row.get("resolver") not in ("stephen", "none"):
        problems.append(f"{rid}: resolver {row.get('resolver')!r} is not stephen or none")
    if (row.get("resolver") == "stephen") != (row.get("eligible_actor") == "stephen"):
        problems.append(f"{rid}: a row resolved by Stephen must be submitted by Stephen, and only such a row")
    if not all(re.fullmatch(r"P:[a-z0-9-]+", str(p)) for p in row.get("projection_targets") or [None]):
        problems.append(f"{rid}: projection_targets are not P: tokens")
    if not re.fullmatch(r"U:[a-z0-9-]+(, U:[a-z0-9-]+)*", str(row.get("reducer"))):
        problems.append(f"{rid}: reducer is not a U: token list")
    tests = row.get("binding_tests") or []
    has_t = False
    for test in tests:
        match_t = re.fullmatch(r"W9-T([0-9]+)", test)
        if match_t:
            has_t = True
            if not 1 <= int(match_t.group(1)) <= 23:
                problems.append(f"{rid}: {test} is outside W9 §17 (W9-T1 to W9-T23)")
        elif test not in c2x:
            problems.append(f"{rid}: {test} is not a declared W9-C2x catalogue test")
    reason = row.get("w9c_only_reason")
    if has_t and reason is not None:
        problems.append(f"{rid}: a row with a W9-T test carries a w9c_only_reason")
    if not has_t and reason not in W9C_REASONS:
        problems.append(f"{rid}: a row with no W9-T test needs a w9c_only_reason")
    if not has_t and not any(test.startswith("W9-C2") for test in tests):
        problems.append(f"{rid}: a row with no W9-T test must bind a W9-C2x test")
    for fixture in row.get("pilot_promotion_fixtures") or []:
        match_f = re.fullmatch(r"([FS])-([0-9]{3})", str(fixture.get("fixture_id", "")))
        limit = {"F": 38, "S": 17}.get(match_f.group(1)) if match_f else None
        if not limit or not 1 <= int(match_f.group(2)) <= limit:
            problems.append(f"{rid}: fixture {fixture} is outside F-001 to F-038 and S-001 to S-017")
    for event in row.get("ordered_events") or []:
        if not re.fullmatch(r"(E|W2):[A-Za-z0-9-]+", str(event.get("event", ""))):
            problems.append(f"{rid}: event token {event.get('event')!r} is malformed")
        if event.get("multiplicity") not in ("1", "0..n"):
            problems.append(f"{rid}: event multiplicity {event.get('multiplicity')!r} is not 1 or 0..n")
        if event.get("multiplicity") == "0..n" and not event.get("condition"):
            problems.append(f"{rid}: a 0..n event needs its condition")
    return problems


def derive_row(annex_row: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    """Derive one expected catalogue row from one annex row, by the annex's derivation rules.

    Args:
        annex_row: One row of the annex.
        identity: The annex's identity at its pinned commit (see :func:`annex_identity`).

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
        "row_sha256": sha256_hex(canonical_bytes(annex_row)),
    }
    return row


def expected_rows(annex: dict[str, Any], identity: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive every expected catalogue row, in annex order."""
    return [derive_row(row, identity) for row in annex["rows"]]


def owner_row_range_hash() -> str:
    """W11's definition: SHA-256 of the canonical JSON of the sorted owner row IDs (P-074 item 1)."""
    return sha256_hex(canonical_bytes(sorted(W9_OWNER_ROW_IDS)))


def owner_row_multiset_hash(rows: list[dict[str, Any]]) -> str:
    """SHA-256 of the canonical JSON of the sorted per-row canonical-JSON SHA-256s (P-074 item 1)."""
    return sha256_hex(canonical_bytes(sorted(sha256_hex(canonical_bytes(row)) for row in rows)))


def family_files(commit: str) -> list[str]:
    """Return the W9 family's schema file names, as the bootstrap contract at ``commit`` lists them."""
    contract = strict_yaml(_git("show", f"{commit}:{CONTRACT_PATH}", binary=True))
    return [*contract["families"]["record"], *contract["families"]["bootstrap"]]


def expected_schema_source_rows(commit: str) -> list[dict[str, Any]]:
    """Derive the schema source rows for the family at ``commit``, one per schema file, in contract order."""
    rows = []
    for kind in family_files(commit):
        path = f"{SCHEMA_DIR}/{kind}.schema.json"
        data = _git("show", f"{commit}:{path}", binary=True)
        rows.append(
            {
                "repository_path": path,
                "schema_id": f"ars://legacy/{kind}",
                "schema_version": "1.0.0",
                "git_commit": commit,
                "git_blob": _git("rev-parse", f"{commit}:{path}"),
                "file_length": len(data),
                "file_sha256": sha256_hex(data),
            }
        )
    return rows


def expected_owner_identities(commit: str) -> dict[str, Any]:
    """Return the owner specification and plan identities from the bootstrap contract at ``commit``."""
    contract = strict_yaml(_git("show", f"{commit}:{CONTRACT_PATH}", binary=True))
    return {"owner_spec_identity": contract["source_spec"], "owner_plan_identity": contract["source_plan"]}


def expected_catalogue(schema_commit: str, annex_commit: str) -> dict[str, Any]:
    """Build the catalogue this verifier expects for the given schema and annex commits (stage B2's generator).

    Args:
        schema_commit: The single commit every schema source row names.
        annex_commit: A commit holding the pinned annex blob.

    Returns:
        The complete expected catalogue, with its ``content_hash``.
    """
    identity = annex_identity(annex_commit)
    rows = expected_rows(pinned_annex(), identity)
    catalogue: dict[str, Any] = {
        "schema_id": "ars://legacy/w9-schema-catalogue-content",
        "schema_version": "1.0.0",
        "record_id": W9_CATALOGUE_RECORD_ID,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": W9_CATALOGUE_PROJECT_ID,
        "created_at": "2026-10-24T00:00:00Z",
        "created_by_actor_id": W9_CATALOGUE_ACTOR_ID,
        **expected_owner_identities(schema_commit),
        "owner_annex_identity": identity,
        "global_preconditions": list(pinned_annex()["global_preconditions"]),
        "owner_row_count": len(W9_OWNER_ROW_IDS),
        "owner_row_range_hash": owner_row_range_hash(),
        "schema_source_rows": expected_schema_source_rows(schema_commit),
        "owner_contract_rows": rows,
    }
    catalogue["content_hash"] = sha256_hex(canonical_bytes(catalogue))
    return catalogue


def verify_catalogue(catalogue: Any, main_ref: str = "origin/main") -> list[str]:
    """Verify a catalogue against the pinned annex, Git and the bootstrap contract.

    Args:
        catalogue: The parsed catalogue.
        main_ref: The ref whose history every pinned commit must belong to.

    Returns:
        A list of human-readable problems, empty when the catalogue verifies.
    """
    if not isinstance(catalogue, dict):
        return ["the catalogue is not a JSON object"]
    problems: list[str] = []

    # B-2: the annex is the pinned blob, at a commit on main_ref.
    identity = catalogue.get("owner_annex_identity")
    annex_commit = None
    if not isinstance(identity, dict):
        problems.append("owner_annex_identity is missing")
    else:
        if (identity.get("git_blob"), identity.get("file_sha256"), identity.get("file_length")) != (
            W9_ANNEX_BLOB,
            W9_ANNEX_SHA256,
            W9_ANNEX_BYTES,
        ) or identity.get("repository_path") != ANNEX_PATH:
            problems.append("owner_annex_identity does not name the pinned annex blob, SHA-256 and size")
        annex_commit = resolve_commit(str(identity.get("git_commit")))
        if annex_commit is None or annex_commit != identity.get("git_commit"):
            problems.append("owner_annex_identity.git_commit is not a full commit SHA in this repository")
            annex_commit = None
        elif not _git_ok("cat-file", "-e", f"{annex_commit}:{ANNEX_PATH}") or (
            _git("rev-parse", f"{annex_commit}:{ANNEX_PATH}") != W9_ANNEX_BLOB
        ):
            problems.append("owner_annex_identity.git_commit does not hold the pinned annex blob")
            annex_commit = None
        elif not is_ancestor(annex_commit, main_ref):
            problems.append(f"owner_annex_identity.git_commit is not on {main_ref}")

    # B-1: schema source rows name one commit on main_ref, with blobs unchanged at HEAD.
    source_rows = catalogue.get("schema_source_rows")
    commits = {row.get("git_commit") for row in source_rows} if isinstance(source_rows, list) and source_rows else set()
    schema_commit = resolve_commit(next(iter(commits))) if len(commits) == 1 else None
    if schema_commit is None or schema_commit not in commits:
        problems.append("schema_source_rows do not all name one full commit SHA in this repository")
        schema_commit = None
    else:
        if not is_ancestor(schema_commit, main_ref):
            problems.append(f"the schema source commit is not on {main_ref}")
        expected_sources = expected_schema_source_rows(schema_commit)
        if source_rows != expected_sources:
            problems.append("schema_source_rows do not match the family's files at their commit")
        for row in expected_sources:
            if _git("rev-parse", f"HEAD:{row['repository_path']}") != row["git_blob"]:
                problems.append(f"{row['repository_path']} changed after the schema source commit")

    # B-1: validate against the catalogue schema as committed at the schema commit.
    if schema_commit is not None:
        schema = json.loads(_git("show", f"{schema_commit}:{CATALOGUE_SCHEMA}", binary=True))
        validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
        problems += [f"schema: {error.message}" for error in validator.iter_errors(catalogue)]
        if {k: catalogue.get(k) for k in ("owner_spec_identity", "owner_plan_identity")} != expected_owner_identities(
            schema_commit
        ):
            problems.append("owner_spec_identity or owner_plan_identity differs from the bootstrap contract")

    # B-1: pinned record identities, and the content hash over the object without itself.
    pins = {
        "record_id": W9_CATALOGUE_RECORD_ID,
        "project_id": W9_CATALOGUE_PROJECT_ID,
        "created_by_actor_id": W9_CATALOGUE_ACTOR_ID,
    }
    for field, value in pins.items():
        if catalogue.get(field) != value:
            problems.append(f"{field} is not the pinned W9 catalogue identity")
    unsigned = {key: value for key, value in catalogue.items() if key != "content_hash"}
    if catalogue.get("content_hash") != sha256_hex(canonical_bytes(unsigned)):
        problems.append("content_hash does not hash the catalogue without itself")

    # The rows, the counts and the global preconditions, against the pinned annex.
    annex = pinned_annex()
    if catalogue.get("global_preconditions") != annex["global_preconditions"]:
        problems.append("global_preconditions differ from the annex")
    if catalogue.get("owner_row_count") != len(W9_OWNER_ROW_IDS):
        problems.append(f"owner_row_count is not {len(W9_OWNER_ROW_IDS)}")
    if catalogue.get("owner_row_range_hash") != owner_row_range_hash():
        problems.append("owner_row_range_hash is not the SHA-256 of the sorted owner row IDs")
    actual = catalogue.get("owner_contract_rows")
    if annex_commit is not None and isinstance(actual, list):
        problems += compare_rows(actual, expected_rows(annex, annex_identity(annex_commit)))
    elif not isinstance(actual, list):
        problems.append("owner_contract_rows is not a list")
    return problems


def compare_rows(actual: list[Any], expected: list[dict[str, Any]]) -> list[str]:
    """Compare catalogue rows with annex-derived rows, field by field (W9-C01, W9-C03).

    Args:
        actual: The catalogue's ``owner_contract_rows``.
        expected: The rows derived from the pinned annex.

    Returns:
        A list of human-readable differences, empty when every row matches.
    """
    problems: list[str] = []
    if len(actual) != len(expected):
        problems.append(f"{len(actual)} rows in the catalogue, {len(expected)} derived from the annex")
    for want, got in zip(expected, actual, strict=False):
        rid = want["owner_row_id"]
        if not isinstance(got, dict) or got.keys() != want.keys():
            problems.append(f"{rid}: field set differs from the annex-derived row")
            continue
        for field, value in want.items():
            if got[field] != value:
                problems.append(f"{rid}: field {field} differs from the annex-derived value")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Verify the pinned annex, and a catalogue when one is given or required.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        0 when everything verifies; 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalogue", type=Path, help="a catalogue to verify; it must exist when given")
    parser.add_argument("--require-catalogue", action="store_true", help="fail when no catalogue exists (B2 onward)")
    parser.add_argument("--main-ref", default="origin/main", help="the ref every pinned commit must belong to")
    args = parser.parse_args(argv)
    problems: list[str] = []
    try:
        problems += check_annex(pinned_annex())
    except (subprocess.CalledProcessError, ValueError, yaml.YAMLError) as error:
        problems.append(f"the pinned annex cannot be read: {error}")
    path = args.catalogue or (REPO_ROOT / CATALOGUE_PATH)
    checked = False
    if path.exists():
        try:
            problems += verify_catalogue(json.loads(path.read_text(encoding="utf-8")), args.main_ref)
        except json.JSONDecodeError as error:
            problems.append(f"the catalogue is not JSON: {error}")
        checked = True
    elif args.catalogue is not None or args.require_catalogue:
        problems.append(f"no catalogue at {path}")
    for problem in problems:
        print(problem, file=sys.stderr)
    scope = "annex and catalogue" if checked else "annex"
    print(f"{scope}: {len(W9_OWNER_ROW_IDS)} pinned rows; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
