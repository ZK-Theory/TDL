# Research context: docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md (WP9.1, P-065)
# Purpose: static controls for the inert W9 ars://legacy/ schema family and its bootstrap contract (stage A).
"""Independent static controls for the inert W9 schema family (06v WP9.1, stage A).

This test owns the expected family and identity set. It does not read a catalogue or derive its expected side from
the files under test. Stage A materializes schemas and the bootstrap contract only: no catalogue, no acceptance
envelope instance, and no runtime binding.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.schema_registry import _RUNTIME_BINDINGS, bundled_runtime_schema_registry

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "w9"
BOOTSTRAP_CONTRACT = REPO_ROOT / ".research-system" / "contracts" / "w9" / "w9-materialization-bootstrap-contract.yaml"
STAGE_B_CATALOGUE = REPO_ROOT / ".research-system" / "evals" / "expected" / "w9-legacy-integration-v1.json"

RECORD_KINDS = (
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
)
BOOTSTRAP_KINDS = (
    "w9-catalogue-acceptance-envelope",
    "w9-materialization-bootstrap-contract",
    "import-accepted-w9-catalogue-genesis",
    "w9-schema-catalogue-content",
)
EXPECTED_IDS = {f"ars://legacy/{kind}" for kind in RECORD_KINDS + BOOTSTRAP_KINDS}

# 06v §2.6: the Gate 6 store identity, frozen from foundation.yaml at M2 4d867d85 (P-058).
GATE6_STORE_IDENTITY = "5e3b95a956a8a416accd697f250088b5c8723924eb68544f01064ede6eb18d69"
SOURCE_TUPLES = {
    "source_spec": (
        "docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md",
        "50371fac50f6c600f552ae687b0cea90dca1d0a6",
        "ea3a8e4a5e89a599c255fd881c2a040db4f2d3c5",
    ),
    "source_plan": (
        "docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md",
        "4999111c078ddf7bae6766c86c1d077833182d2d",
        "2b40fae441e07536ce729ef36f1ec69b1a1f7953",
    ),
}

_HASH = "0" * 64
_SHA1 = "0" * 40
_OBJ = "obj_00000000-0000-7000-8000-000000000001"
_ACT = "act_00000000-0000-7000-8000-000000000001"


def _ref() -> dict[str, Any]:
    return {"id": _OBJ, "record_revision": 1, "content_hash": _HASH}


def _header(kind: str) -> dict[str, Any]:
    return {
        "schema_id": f"ars://legacy/{kind}",
        "schema_version": "1.0.0",
        "record_id": _OBJ,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": "prj_00000000-0000-7000-8000-000000000001",
        "created_at": "2026-10-23T00:00:00Z",
        "created_by_actor_id": _ACT,
        "content_hash": _HASH,
    }


@lru_cache(maxsize=None)
def _schema(kind: str) -> dict[str, Any]:
    return json.loads((SCHEMA_ROOT / f"{kind}.schema.json").read_text(encoding="utf-8"))


def _validator(kind: str) -> Draft202012Validator:
    return Draft202012Validator(_schema(kind))


def _valid(kind: str, instance: dict[str, Any]) -> bool:
    return _validator(kind).is_valid(instance)


def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO_ROOT, capture_output=True, check=True).stdout


def _git_blob(commit: str, path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{commit}:{path}"], cwd=REPO_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()


def test_schema_files_are_exactly_the_owned_family() -> None:
    present = {path.name for path in SCHEMA_ROOT.glob("*.schema.json")}
    expected = {f"{kind}.schema.json" for kind in RECORD_KINDS + BOOTSTRAP_KINDS}
    assert present == expected


@pytest.mark.parametrize("kind", RECORD_KINDS + BOOTSTRAP_KINDS)
def test_schema_is_valid_closed_and_self_identified(kind: str) -> None:
    schema = _schema(kind)
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == f"ars://legacy/{kind}"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_id"] == {"const": schema["$id"]}
    assert schema["properties"]["schema_version"] == {"const": "1.0.0"}


def test_family_loads_in_registry_without_collision() -> None:
    registry = bundled_runtime_schema_registry()
    for schema_id in EXPECTED_IDS:
        assert registry.resolve_identity(schema_id, "1.0.0").schema_id == schema_id
    assert all(schema_id.startswith("ars://legacy/") for schema_id in EXPECTED_IDS)


def test_legacy_ids_are_not_runtime_activated() -> None:
    active_ids = {binding.schema_id for binding in _RUNTIME_BINDINGS}
    assert not (EXPECTED_IDS & active_ids)
    assert not any(schema_id.startswith("ars://legacy/") for schema_id in active_ids)


def test_stage_a_materializes_no_catalogue() -> None:
    assert not STAGE_B_CATALOGUE.exists()


def test_bootstrap_contract_validates_and_matches_owned_values() -> None:
    contract = yaml.safe_load(BOOTSTRAP_CONTRACT.read_text(encoding="utf-8"))
    assert _valid("w9-materialization-bootstrap-contract", contract)
    assert tuple(contract["families"]["record"]) == RECORD_KINDS
    assert tuple(contract["families"]["bootstrap"]) == BOOTSTRAP_KINDS
    assert contract["refused_store_identities"] == [GATE6_STORE_IDENTITY]
    assert contract["runtime_activation"] == "forbidden"
    assert contract["segmentation_contract"] == "w9-segmentation/1.0.0"


@pytest.mark.parametrize("field", sorted(SOURCE_TUPLES))
def test_bootstrap_source_tuples_match_main(field: str) -> None:
    contract = yaml.safe_load(BOOTSTRAP_CONTRACT.read_text(encoding="utf-8"))
    path, commit, blob = SOURCE_TUPLES[field]
    raw = _git_bytes(commit, path)
    assert contract[field] == {
        "repository_path": path,
        "reviewed_commit": commit,
        "git_blob": blob,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
    }
    assert _git_blob(commit, path) == blob


def _paper_root() -> dict[str, Any]:
    return {
        **_header("legacy-paper-root"),
        "paper_key": "P01-A",
        "manuscript_root_path": "papers/P01-A-JRSSA/",
        "qualifiers": [],
        "owner_actor_id": _ACT,
        "recovery": None,
    }


def test_paper_root_names_no_transition_or_citation_status() -> None:
    root = _paper_root()
    assert _valid("legacy-paper-root", root)
    for forbidden in ("transition_ref", "citation_status", "citation_status_ref"):
        bad = {**deepcopy(root), forbidden: _ref()}
        assert not _valid("legacy-paper-root", bad)
    assert not _valid("legacy-paper-root", {**root, "manuscript_root_path": "papers/P01-B-JRSSB/"})


def _transition(from_mode: str, to_mode: str, *, mapping: bool = True) -> dict[str, Any]:
    return {
        **_header("legacy-ownership-transitioned"),
        "mapping_ref": _ref() if mapping else None,
        "subject_registration_ref": _ref(),
        "paper_root_ref": _ref() if mapping else None,
        "from_mode": from_mode,
        "to_mode": to_mode,
        "reviewer_ref": _ref(),
        "decision_ref": _ref(),
    }


def test_transitions_never_return_to_legacy_owned() -> None:
    assert _valid("legacy-ownership-transitioned", _transition("legacy_owned", "successor_owned"))
    assert _valid("legacy-ownership-transitioned", _transition("legacy_owned", "closed_reference", mapping=False))
    assert _valid("legacy-ownership-transitioned", _transition("successor_owned", "closed_reference", mapping=False))
    assert not _valid("legacy-ownership-transitioned", _transition("successor_owned", "legacy_owned"))
    assert not _valid("legacy-ownership-transitioned", _transition("legacy_owned", "successor_owned", mapping=False))


def _observation(source: dict[str, Any]) -> dict[str, Any]:
    return {
        **_header("legacy-observation"),
        "registration_ref": _ref(),
        "selector": {"selector_kind": "whole_file"},
        "source_identity": source,
        "segmentation_contract": None,
        "file_facts": None,
        "importer": {"actor_id": _ACT, "tool_id": "w9-reader", "tool_version": "1", "tool_sha256": _HASH},
        "observer_actor_id": _ACT,
        "observed_at": "2026-10-23T00:00:00Z",
        "families": [
            {
                "family_name": "whole_file",
                "w0_class": "authoritative",
                "signed_w0_revision_ref": _ref(),
                "signature_record_ref": _ref(),
            }
        ],
        "qualifiers": [],
        "conflicts": [],
        "non_inferences": ["no Git identity"],
    }


def test_restricted_sources_cannot_carry_a_frozen_copy() -> None:
    restricted = {
        "identity_kind": "restricted_untracked_file",
        "path": "x/cache.pkl",
        "sha256": _HASH,
        "byte_length": 1,
    }
    assert _valid("legacy-observation", _observation(restricted))
    assert not _valid("legacy-observation", _observation({**restricted, "frozen_copy_ref": _ref()}))


def test_observation_classes_require_a_signed_w0_record() -> None:
    tracked = {
        "identity_kind": "git_tracked",
        "repository_path": "results/x.json",
        "git_commit": _SHA1,
        "git_blob": _SHA1,
        "sha256": _HASH,
        "byte_length": 1,
    }
    observation = _observation(tracked)
    assert _valid("legacy-observation", observation)
    del observation["families"][0]["signature_record_ref"]
    assert not _valid("legacy-observation", observation)


def test_inventory_blocker_rows_carry_a_reason_and_items_do_not() -> None:
    row = {
        "row_ordinal": 1,
        "row_kind": "item",
        "selector_kind": "heading_section",
        "anchor_text": "Entry",
        "unit_hash": None,
        "start_byte": 0,
        "byte_length": 10,
        "start_line": 1,
        "line_count": 1,
        "raw_row_sha256": _HASH,
        "blocker_reason": None,
    }
    inventory = {
        **_header("legacy-light-inventory"),
        "registration_ref": _ref(),
        "source_identity": {
            "identity_kind": "git_tracked",
            "repository_path": ".apm/tracker.md",
            "git_commit": _SHA1,
            "git_blob": _SHA1,
            "sha256": _HASH,
            "byte_length": 10,
        },
        "segmentation_contract": "w9-segmentation/1.0.0",
        "file_facts": {"line_ending": "LF", "ends_with_terminator": True, "has_utf8_bom": False, "line_count": 1},
        "observed_at": "2026-10-23T00:00:00Z",
        "observer_actor_id": _ACT,
        "rows": [row],
        "independent_reproduction_ref": None,
    }
    assert _valid("legacy-light-inventory", inventory)
    inventory["rows"] = [{**row, "row_kind": "blocker"}]
    assert not _valid("legacy-light-inventory", inventory)
    inventory["rows"] = [{**row, "row_kind": "blocker", "blocker_reason": "duplicate_anchor"}]
    assert _valid("legacy-light-inventory", inventory)
    inventory["rows"] = [{**row, "blocker_reason": "duplicate_anchor"}]
    assert not _valid("legacy-light-inventory", inventory)


def test_closed_reference_items_carry_pilot_promotion_refs() -> None:
    acceptance = {
        **_header("legacy-closed-reference-acceptance"),
        "observation_refs": [_ref()],
        "independent_review_ref": _ref(),
        "decision_ref": _ref(),
        "items": [
            {
                "observation_ref": _ref(),
                "pilot_promotion": {
                    "fixture_ids": ["F-018", "S-016/OM"],
                    "evidence_refs": [_ref()],
                    "waiver_ref": None,
                },
            }
        ],
        "threshold_preregistration_sha256": _HASH,
        "governing_record_set_sha256": _HASH,
        "anchors": [{"anchor_kind": "git_commit", "value": _SHA1}],
        "enforcement_change_list": None,
    }
    assert _valid("legacy-closed-reference-acceptance", acceptance)
    del acceptance["items"][0]["pilot_promotion"]
    assert not _valid("legacy-closed-reference-acceptance", acceptance)


def _registration(role: str, path: str, mode: str) -> dict[str, Any]:
    return {
        **_header("legacy-path-registration"),
        "root_kind": "repository_root",
        "root_id": "repo",
        "normalized_path": path,
        "physical_identity": {
            "canonical_target": path,
            "reparse_chain": [],
            "volume_serial_number": "1",
            "stable_file_id": "1",
            "link_count": 1,
            "case_aliases": [],
            "unicode_aliases": [],
            "short_name_aliases": [],
        },
        "source_identity_kind": "git_tracked",
        "role": role,
        "ownership_mode": mode,
        "writer_classes": [],
        "prohibited_consumers": [],
        "registration_decision_ref": _ref(),
    }


def test_registration_binds_the_successor_root_and_rejects_traversal() -> None:
    assert _valid(
        "legacy-path-registration", _registration("successor_results_root", "results/ars/", "successor_owned")
    )
    assert not _valid(
        "legacy-path-registration", _registration("successor_results_root", "results/", "successor_owned")
    )
    assert not _valid(
        "legacy-path-registration", _registration("successor_results_root", "results/ars/", "legacy_owned")
    )
    assert not _valid("legacy-path-registration", _registration("legacy_research_result", "../x.json", "legacy_owned"))
    assert not _valid("legacy-path-registration", _registration("legacy_research_result", "/abs.json", "legacy_owned"))


def test_citation_status_binds_adoption_refs_to_status() -> None:
    status = {
        **_header("legacy-paper-citation-status"),
        "root_ref": _ref(),
        "cited_family_set_sha256": _HASH,
        "derivation": {
            "extractor_output_sha256": _HASH,
            "reviewer_derivation_sha256": _HASH,
            "reviewer_actor_id": _ACT,
        },
        "families": [{"observation_ref": _ref(), "family_name": "h0_w2", "status": "adopted", "adoption_ref": _ref()}],
        "supersedes_status_ref": None,
    }
    assert _valid("legacy-paper-citation-status", status)
    status["families"][0]["adoption_ref"] = None
    assert not _valid("legacy-paper-citation-status", status)
    status["families"][0]["status"] = "unadopted"
    assert _valid("legacy-paper-citation-status", status)
