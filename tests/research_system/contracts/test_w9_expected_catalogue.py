# Research context: docs/plans/agentic-research-system/transition/w9/wp9-1-stage-b-design-note.md (WP9.1 B1; P-072, P-073)
# Purpose: controls for tools/verify_w9_materialization.py and the owner annex it derives the W9 catalogue from.
"""Controls for the W9 catalogue verifier (WP9.1 stage B1).

The annex is the expected side (P-072 item 6; note §3). These controls check that:
- the verifier accepts the committed annex;
- every derived row fits the widened catalogue row schema;
- the annex covers the owned record family and command set;
- the verifier refuses each rule violation and detects a mutation of any catalogue field.

No catalogue exists in B1. Comparison is exercised against a catalogue built here from the derived rows.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = REPO_ROOT / ".research-system" / "contracts" / "w9" / "w9-materialization-bootstrap-contract.yaml"

# The command types the annex may use (re-review I-2: the WP9.2 census grows by these, not by the row count).
COMMAND_TYPES = {
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
_HASH = "0" * 64
_SHA1 = "0" * 40
_UUID = "00000000-0000-7000-8000-000000000001"


@lru_cache(maxsize=None)
def _verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_w9_verify", REPO_ROOT / "tools" / "verify_w9_materialization.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def _annex() -> dict[str, Any]:
    return _verifier().load_annex("HEAD")


@lru_cache(maxsize=None)
def _identity() -> dict[str, Any]:
    return _verifier().annex_identity("HEAD")


def _schema_ids() -> set[str]:
    return _verifier().committed_record_schema_ids()


def _catalogue() -> dict[str, Any]:
    rows = _verifier().expected_rows(_annex(), _identity())
    return {
        "schema_id": "ars://legacy/w9-schema-catalogue-content",
        "schema_version": "1.0.0",
        "record_id": f"obj_{_UUID}",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": f"prj_{_UUID}",
        "created_at": "2026-10-24T00:00:00Z",
        "created_by_actor_id": f"act_{_UUID}",
        "content_hash": _HASH,
        "owner_spec_identity": {
            "repository_path": "docs/w9.md",
            "reviewed_commit": _SHA1,
            "git_blob": _SHA1,
            "raw_sha256": _HASH,
            "raw_bytes": 1,
        },
        "owner_plan_identity": {
            "repository_path": "docs/06v.md",
            "reviewed_commit": _SHA1,
            "git_blob": _SHA1,
            "raw_sha256": _HASH,
            "raw_bytes": 1,
        },
        "owner_annex_identity": dict(_identity()),
        "global_preconditions": list(_annex()["global_preconditions"]),
        "owner_row_count": len(rows),
        "owner_row_range_hash": _verifier().sha256_hex(_verifier().canonical_json(rows)),
        "schema_source_rows": [
            {
                "repository_path": "x.schema.json",
                "schema_id": "ars://legacy/legacy-observation",
                "schema_version": "1.0.0",
                "git_commit": _SHA1,
                "git_blob": _SHA1,
                "file_length": 1,
                "file_sha256": _HASH,
            }
        ],
        "owner_contract_rows": rows,
    }


def _catalogue_validator() -> Draft202012Validator:
    schema_path = REPO_ROOT / _verifier().CATALOGUE_SCHEMA
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def test_committed_annex_passes_its_own_rules() -> None:
    assert _verifier().check_annex(_annex(), _schema_ids()) == []


def test_derived_catalogue_fits_the_widened_row_schema() -> None:
    errors = [error.message for error in _catalogue_validator().iter_errors(_catalogue())]
    assert errors == []


def test_annex_covers_the_owned_family_and_command_set() -> None:
    rows = _annex()["rows"]
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    records = {f"ars://legacy/{kind}" for kind in contract["families"]["record"]}
    named = {row["record_schema_id"] for row in rows}
    # Every W9 record is created or worked on by at least one row; the bootstrap rows name their two import inputs.
    assert records <= named
    assert named - records == {
        "ars://legacy/import-accepted-w9-catalogue-genesis",
        "ars://legacy/import-accepted-w9-catalogue-revision",
    }
    assert {row["command_type"] for row in rows} == COMMAND_TYPES


def test_every_row_resolved_by_stephen_is_submitted_by_stephen() -> None:
    for row in _annex()["rows"]:
        assert (row["resolver"] == "stephen") == (row["eligible_actor"] == "stephen"), row["owner_row_id"]


def test_matching_catalogue_verifies_clean() -> None:
    assert _verifier().compare_catalogue(_catalogue(), _annex(), _identity()) == []


@pytest.mark.parametrize("field", sorted(_verifier().COPIED_FIELDS + _verifier().DERIVED_FIELDS))
def test_mutating_any_field_of_a_row_is_detected(field: str) -> None:
    # W9-C03: a mutation of any one catalogue field is detected against the annex.
    catalogue = _catalogue()
    row = catalogue["owner_contract_rows"][19]
    row[field] = {"mutated": True} if isinstance(row[field], dict) else "mutated"
    catalogue["owner_row_range_hash"] = _verifier().sha256_hex(
        _verifier().canonical_json(catalogue["owner_contract_rows"])
    )
    problems = _verifier().compare_catalogue(catalogue, _annex(), _identity())
    assert any(field in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda c: c.update(owner_row_count=1), "owner_row_count"),
        (lambda c: c.update(owner_row_range_hash=_HASH), "owner_row_range_hash"),
        (lambda c: c["owner_contract_rows"].pop(), "rows in the catalogue"),
        (lambda c: c.update(global_preconditions=["G1"]), "global_preconditions"),
        (lambda c: c["owner_annex_identity"].update(git_commit=_SHA1), "owner_annex_identity"),
    ],
)
def test_catalogue_level_differences_are_detected(change: Any, expected: str) -> None:
    catalogue = _catalogue()
    change(catalogue)
    assert any(expected in problem for problem in _verifier().compare_catalogue(catalogue, _annex(), _identity()))


def _first_flow_row(annex: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in annex["rows"] if row["w9c_only_reason"] == "authority_flow_step")


def _first_t_row(annex: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in annex["rows"] if row["w9c_only_reason"] is None)


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        # P-073 item 1: a W9-C-only row must carry a reason and bind a W9-C2x test.
        (lambda a: _first_flow_row(a).update(binding_tests=[]), "must bind a W9-C2x test"),
        (lambda a: _first_flow_row(a).update(w9c_only_reason=None), "needs a w9c_only_reason"),
        (lambda a: _first_t_row(a).update(w9c_only_reason="authority_flow_step"), "carries a w9c_only_reason"),
        (lambda a: _first_flow_row(a).update(binding_tests=["W9-C29"]), "not a declared W9-C2x"),
        (lambda a: _first_t_row(a).update(binding_tests=["W9-T24"]), "outside W9 §17"),
        (lambda a: a["rows"][0].update(owner_row_id="LR-099"), "contiguous"),
        (lambda a: a["rows"][1].update(payload_discriminant=a["rows"][0]["payload_discriminant"]), "unique"),
        (lambda a: a["rows"][0].update(eligible_actor="manager"), "closed set"),
        (lambda a: a["rows"][0].update(record_schema_id="ars://legacy/none"), "not a committed schema"),
        (
            lambda a: _first_t_row(a).update(pilot_promotion_fixtures=[{"fixture_id": "F-039", "when": None}]),
            "outside F-001",
        ),
        (lambda a: a["rows"][0]["ordered_events"][0].update(multiplicity="many"), "multiplicity"),
        (lambda a: a["rows"][0]["ordered_events"][0].update(event="E:bad token"), "malformed"),
        (lambda a: a["rows"][0].update(receipt_identity="R:other"), "receipt_identity"),
        (lambda a: a["rows"][0].pop("source_refs"), "annex row fields"),
    ],
)
def test_annex_rule_violations_are_refused(mutate: Any, expected: str) -> None:
    annex = deepcopy(_annex())
    mutate(annex)
    problems = _verifier().check_annex(annex, _schema_ids())
    assert any(expected in problem for problem in problems), problems


def test_a_conditional_event_needs_its_condition() -> None:
    annex = deepcopy(_annex())
    row = next(r for r in annex["rows"] if any(e["multiplicity"] == "0..n" for e in r["ordered_events"]))
    next(e for e in row["ordered_events"] if e["multiplicity"] == "0..n")["condition"] = None
    assert any("needs its condition" in p for p in _verifier().check_annex(annex, _schema_ids()))
