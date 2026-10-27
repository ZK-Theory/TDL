# Research context: docs/plans/agentic-research-system/implementation/06v-w9-implementation-plan.md (WP9.1; P-065, P-069)
# Purpose: static controls for the inert W9 ars://legacy/ schema family and its bootstrap contract (stage A).
"""Independent static controls for the inert W9 schema family (06v WP9.1, stage A).

This test owns the expected family, identity set, reference-kind table and edge table. It does not derive its expected
side from the files under test. Stage A materializes the schemas, the bootstrap contract and their generator only: no
catalogue, no acceptance envelope instance, and no runtime binding. Stage B2 adds the catalogue, which this test
checks only through the stage B verifier.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.schema_registry import _RUNTIME_BINDINGS, bundled_runtime_schema_registry

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "w9"
ALL_SCHEMAS_ROOT = REPO_ROOT / ".research-system" / "schemas"
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
    "legacy-adoption-use-mismatch",
)
BOOTSTRAP_KINDS = (
    "w9-catalogue-acceptance-envelope",
    "w9-materialization-bootstrap-contract",
    "import-accepted-w9-catalogue-genesis",
    "w9-schema-catalogue-content",
    "import-accepted-w9-catalogue-revision",
)
ALL_KINDS = RECORD_KINDS + BOOTSTRAP_KINDS
EXPECTED_IDS = {f"ars://legacy/{kind}" for kind in ALL_KINDS}

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
# The accepted W11 catalogue the W9 genesis requires in its store (06v O-5).
W11_CATALOGUE = {
    "repository_path": ".research-system/evals/expected/w11-portfolio-discovery-v1.json",
    "git_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
    "raw_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
    "raw_bytes": 136229,
}
# D-9's restricted suffixes (P-064 item 9), copied into the schemas under P-069 item 3.
D9_SUFFIXES = [".csv", ".pkl"]

# Every reference field of the family and the reference kind it takes (review B-1). The walk below must find exactly
# these keys, so a new reference field fails until it is classified here.
REF_FIELDS: dict[tuple[str, str], str] = {
    ("legacy-path-registration", "registration_decision_ref"): "decisionRef",
    ("legacy-field-family-membership", "review_ref"): "reviewRef",
    ("legacy-field-family-membership", "acceptance_decision_ref"): "decisionRef",
    ("legacy-light-inventory", "registration_ref"): "recordRef",
    ("legacy-light-inventory", "source_identity.frozen_copy_ref"): "artefactRef",
    ("legacy-light-inventory", "independent_reproduction_ref"): "anyRef",
    ("legacy-observation", "registration_ref"): "recordRef",
    ("legacy-observation", "selector.membership_ref"): "recordRef",
    ("legacy-observation", "selector.inventory_ref"): "recordRef",
    ("legacy-observation", "source_identity.frozen_copy_ref"): "artefactRef",
    ("legacy-observation", "families[].signed_w0_revision_ref"): "sourceRef",
    ("legacy-observation", "families[].signature_record_ref"): "anyRef",
    ("legacy-observation", "qualifiers[].source_ref"): "sourceRef",
    ("legacy-observation", "conflicts[].conflicting_record_refs[]"): "sourceRef",
    ("legacy-closed-reference-acceptance", "independent_review_ref"): "reviewRef",
    ("legacy-closed-reference-acceptance", "decision_ref"): "decisionRef",
    ("legacy-closed-reference-acceptance", "items[].observation_ref"): "recordRef",
    ("legacy-closed-reference-acceptance", "items[].pilot_promotion[].ref"): "anyRef",
    ("legacy-adoption-decision", "observation_ref"): "recordRef",
    ("legacy-adoption-decision", "intended_use.successor_ref"): "nullableAnyRef",
    ("legacy-adoption-decision", "qualifiers_to_discharge[].source_ref"): "sourceRef",
    ("legacy-adoption-decision", "decision_ref"): "decisionRef",
    ("legacy-discharge-relation", "successor_result_ref"): "artefactRef",
    ("legacy-discharge-relation", "reviewer_ref"): "reviewRef",
    ("legacy-discharge-relation", "decision_ref"): "decisionRef",
    ("legacy-paper-root", "qualifiers[].source_ref"): "sourceRef",
    ("legacy-paper-root", "recovery.predecessor_root_ref"): "recordRef",
    ("legacy-paper-root", "recovery.recovery_decision_ref"): "decisionRef",
    ("legacy-paper-citation-status", "root_ref"): "recordRef",
    ("legacy-paper-citation-status", "families[].observation_ref"): "recordRef",
    ("legacy-paper-citation-status", "families[].adoption_ref"): "nullableRecordRef",
    ("legacy-paper-citation-status", "supersedes_status_ref"): "nullableRecordRef",
    ("legacy-source-inventory", "root_registration_ref"): "recordRef",
    ("legacy-source-inventory", "rows[].observation_ref"): "recordRef",
    ("legacy-source-inventory", "reviewer_ref"): "reviewRef",
    ("legacy-source-inventory", "decision_ref"): "decisionRef",
    ("legacy-transition-mapping", "source_inventory_ref"): "recordRef",
    ("legacy-transition-mapping", "target_paper_root_ref"): "recordRef",
    ("legacy-transition-mapping", "reviewer_ref"): "reviewRef",
    ("legacy-transition-mapping", "decision_ref"): "decisionRef",
    ("legacy-ownership-transitioned", "mapping_ref"): "nullableRecordRef",
    ("legacy-ownership-transitioned", "subject_registration_ref"): "recordRef",
    ("legacy-ownership-transitioned", "paper_root_ref"): "nullableRecordRef",
    ("legacy-ownership-transitioned", "reviewer_ref"): "reviewRef",
    ("legacy-ownership-transitioned", "decision_ref"): "decisionRef",
    ("legacy-record-supersession", "superseded_ref"): "recordRef",
    ("legacy-record-supersession", "replacing_ref"): "recordRef",
    ("legacy-record-supersession", "reviewer_ref"): "reviewRef",
    ("legacy-record-supersession", "decision_ref"): "decisionRef",
    ("legacy-adoption-use-mismatch", "adoption_ref"): "recordRef",
    ("legacy-adoption-use-mismatch", "successor_task_ref"): "taskRef",
    ("w9-catalogue-acceptance-envelope", "independent_observation_ref"): "anyRef",
    ("w9-catalogue-acceptance-envelope", "independent_review_ref"): "reviewRef",
    ("w9-catalogue-acceptance-envelope", "acceptance_decision_ref"): "decisionRef",
}
REF_DEFS = {
    "recordRef",
    "decisionRef",
    "reviewRef",
    "artefactRef",
    "taskRef",
    "anyRef",
    "nullableRecordRef",
    "nullableAnyRef",
    "sourceRef",
}
SUPERSESSION_TARGETS = (
    "legacy-observation",
    "legacy-closed-reference-acceptance",
    "legacy-adoption-decision",
    "legacy-transition-mapping",
)
# Definitions whose fields the walk follows into, per host schema (a qualifier's source, a frozen copy).
INLINED_DEFS = {"qualifier", "sourceIdentity"}
# Definitions that admit a W9 record ID (`obj_`), so every field using one is an edge of the record graph.
OBJ_ADMITTING_DEFS = {"recordRef", "nullableRecordRef", "anyRef", "nullableAnyRef", "sourceRef"}
# The W9 record kinds each such field's `obj_` branch may name (review M-4; re-review N-3). An empty tuple means the
# field names no W9 record. Same-kind edges are declared apart.
RECORD_EDGES: dict[tuple[str, str], tuple[str, ...]] = {
    ("legacy-light-inventory", "registration_ref"): ("legacy-path-registration",),
    ("legacy-light-inventory", "independent_reproduction_ref"): (),
    ("legacy-observation", "registration_ref"): ("legacy-path-registration",),
    ("legacy-observation", "selector.membership_ref"): ("legacy-field-family-membership",),
    ("legacy-observation", "selector.inventory_ref"): ("legacy-light-inventory",),
    ("legacy-observation", "families[].signed_w0_revision_ref"): (),
    ("legacy-observation", "families[].signature_record_ref"): (),
    ("legacy-observation", "qualifiers[].source_ref"): ("legacy-observation",),
    ("legacy-observation", "conflicts[].conflicting_record_refs[]"): ("legacy-observation",),
    ("legacy-closed-reference-acceptance", "items[].observation_ref"): ("legacy-observation",),
    ("legacy-closed-reference-acceptance", "items[].pilot_promotion[].ref"): (),
    ("legacy-adoption-decision", "observation_ref"): ("legacy-observation",),
    ("legacy-adoption-decision", "intended_use.successor_ref"): (),
    ("legacy-adoption-decision", "qualifiers_to_discharge[].source_ref"): ("legacy-observation",),
    # Not a transition, a mapping or a citation status: a root naming its own transition is W9-T21's first control.
    ("legacy-paper-root", "qualifiers[].source_ref"): ("legacy-observation",),
    ("legacy-paper-root", "recovery.predecessor_root_ref"): ("legacy-paper-root",),
    ("legacy-paper-citation-status", "root_ref"): ("legacy-paper-root",),
    ("legacy-paper-citation-status", "families[].observation_ref"): ("legacy-observation",),
    ("legacy-paper-citation-status", "families[].adoption_ref"): ("legacy-adoption-decision",),
    ("legacy-paper-citation-status", "supersedes_status_ref"): ("legacy-paper-citation-status",),
    ("legacy-source-inventory", "root_registration_ref"): ("legacy-path-registration",),
    ("legacy-source-inventory", "rows[].observation_ref"): ("legacy-observation",),
    ("legacy-transition-mapping", "source_inventory_ref"): ("legacy-source-inventory",),
    ("legacy-transition-mapping", "target_paper_root_ref"): ("legacy-paper-root",),
    ("legacy-ownership-transitioned", "mapping_ref"): ("legacy-transition-mapping",),
    ("legacy-ownership-transitioned", "subject_registration_ref"): ("legacy-path-registration",),
    ("legacy-ownership-transitioned", "paper_root_ref"): ("legacy-paper-root",),
    # W9 §13.1-13.2 fix the targets, not §5.2's narrower row (P-070; re-review N-4).
    ("legacy-record-supersession", "superseded_ref"): SUPERSESSION_TARGETS,
    ("legacy-record-supersession", "replacing_ref"): SUPERSESSION_TARGETS,
    ("legacy-adoption-use-mismatch", "adoption_ref"): ("legacy-adoption-decision",),
    ("w9-catalogue-acceptance-envelope", "independent_observation_ref"): (),
}
# Same-kind edges: lineage (a recovery root's predecessor, a superseded citation status) and an observation that
# names another observation as a qualifier source or a conflicting record.
SAME_KIND_EDGES = {
    ("legacy-paper-root", "recovery.predecessor_root_ref"),
    ("legacy-paper-citation-status", "supersedes_status_ref"),
    ("legacy-observation", "qualifiers[].source_ref"),
    ("legacy-observation", "conflicts[].conflicting_record_refs[]"),
}
PAPER_ROOT_FIELDS = {"paper_key", "manuscript_root_path", "qualifiers", "owner_actor_id", "recovery"}

_HASH = "0" * 64
_SHA1 = "0" * 40
_UUID = "00000000-0000-7000-8000-000000000001"
_ACT = f"act_{_UUID}"


def _ref(prefix: str = "obj") -> dict[str, Any]:
    return {"id": f"{prefix}_{_UUID}", "record_revision": 1, "content_hash": _HASH}


def _rec() -> dict[str, Any]:
    return _ref("obj")


def _dec() -> dict[str, Any]:
    return _ref("dec")


def _rev() -> dict[str, Any]:
    return _ref("rev")


def _art() -> dict[str, Any]:
    return _ref("art")


def _header(kind: str) -> dict[str, Any]:
    return {
        "schema_id": f"ars://legacy/{kind}",
        "schema_version": "1.0.0",
        "record_id": f"obj_{_UUID}",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": f"prj_{_UUID}",
        "created_at": "2026-10-23T00:00:00Z",
        "created_by_actor_id": _ACT,
        "content_hash": _HASH,
    }


@lru_cache(maxsize=None)
def _schema(kind: str) -> dict[str, Any]:
    return json.loads((SCHEMA_ROOT / f"{kind}.schema.json").read_text(encoding="utf-8"))


def _valid(kind: str, instance: dict[str, Any]) -> bool:
    # The runtime registry checks formats, so the controls do too (review m-9).
    return Draft202012Validator(_schema(kind), format_checker=Draft202012Validator.FORMAT_CHECKER).is_valid(instance)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, check=True, text=True).stdout.strip()


def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO_ROOT, capture_output=True, check=True).stdout


def _load_tool(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_w9_{name}", REPO_ROOT / "tools" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _contract() -> dict[str, Any]:
    return yaml.safe_load(BOOTSTRAP_CONTRACT.read_text(encoding="utf-8"))


# --- The family, its generator and the registry ---------------------------------------------------------------------


def test_schema_files_are_exactly_the_owned_family() -> None:
    present = {path.name for path in SCHEMA_ROOT.glob("*.schema.json")}
    assert present == {f"{kind}.schema.json" for kind in ALL_KINDS}


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_schema_is_valid_closed_and_self_identified(kind: str) -> None:
    schema = _schema(kind)
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == f"ars://legacy/{kind}"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_id"] == {"const": schema["$id"]}
    assert schema["properties"]["schema_version"] == {"const": "1.0.0"}


def test_generator_reproduces_every_committed_schema() -> None:
    generator = _load_tool("w9_schema_gen")
    assert sorted(generator.SCHEMAS) == sorted(ALL_KINDS)
    for kind, schema in generator.SCHEMAS.items():
        # Bytes, not decoded text (re-review n-3).
        assert (SCHEMA_ROOT / f"{kind}.schema.json").read_bytes() == generator.render(schema).encode("utf-8"), kind


def test_inlined_definitions_are_identical_across_the_family() -> None:
    blocks = {json.dumps(_schema(kind)["$defs"], sort_keys=True) for kind in ALL_KINDS}
    assert len(blocks) == 1


def test_legacy_namespace_is_exactly_this_family() -> None:
    owners: dict[str, str] = {}
    for path in ALL_SCHEMAS_ROOT.rglob("*.schema.json"):
        schema_id = json.loads(path.read_text(encoding="utf-8")).get("$id", "")
        if schema_id.startswith("ars://legacy/"):
            owners[schema_id] = path.parent.name
    assert set(owners) == EXPECTED_IDS
    assert set(owners.values()) == {"w9"}


def test_family_loads_in_registry_and_is_not_runtime_activated() -> None:
    registry = bundled_runtime_schema_registry()
    for schema_id in EXPECTED_IDS:
        assert registry.resolve_identity(schema_id, "1.0.0").schema_id == schema_id
    active_ids = {binding.schema_id for binding in _RUNTIME_BINDINGS}
    assert not any(schema_id.startswith("ars://legacy/") for schema_id in active_ids)


def test_stage_b_catalogue_verifies() -> None:
    # Stage B2 replaces stage A's absence check (design note §6): the catalogue now exists, and the verifier passes it.
    assert STAGE_B_CATALOGUE.exists()
    assert _load_tool("verify_w9_materialization").main(["--require-catalogue"]) == 0


# --- The bootstrap contract -----------------------------------------------------------------------------------------


def test_bootstrap_contract_validates_and_matches_owned_values() -> None:
    contract = _contract()
    assert _valid("w9-materialization-bootstrap-contract", contract)
    assert tuple(contract["families"]["record"]) == RECORD_KINDS
    assert tuple(contract["families"]["bootstrap"]) == BOOTSTRAP_KINDS
    assert contract["refused_store_identities"] == [GATE6_STORE_IDENTITY]
    assert contract["runtime_activation"] == "forbidden"
    assert contract["segmentation_contract"] == "w9-segmentation/1.0.0"
    assert contract["required_w11_catalogue"] == W11_CATALOGUE
    assert contract["restricted_suffixes"] == D9_SUFFIXES
    # The schema pattern is derived from the generator's list, which must equal the contract's (re-review n-2).
    assert _load_tool("w9_schema_gen").RESTRICTED_SUFFIXES == contract["restricted_suffixes"]
    assert "the W9 runtime cannot produce or accept its own prerequisite" in contract["verification_rules"]


@pytest.mark.parametrize("field", sorted(SOURCE_TUPLES))
def test_bootstrap_source_tuples_match_pinned_commit_and_head(field: str) -> None:
    path, commit, blob = SOURCE_TUPLES[field]
    raw = _git_bytes(commit, path)
    assert _contract()[field] == {
        "repository_path": path,
        "reviewed_commit": commit,
        "git_blob": blob,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
    }
    assert _git("rev-parse", f"{commit}:{path}") == blob
    # A later edit on the checked-out line is a new identity, never silently accepted (review m-9).
    assert _git("rev-parse", f"HEAD:{path}") == blob


def test_required_w11_catalogue_matches_head() -> None:
    raw = _git_bytes("HEAD", W11_CATALOGUE["repository_path"])
    assert _git("rev-parse", f"HEAD:{W11_CATALOGUE['repository_path']}") == W11_CATALOGUE["git_blob"]
    assert (hashlib.sha256(raw).hexdigest(), len(raw)) == (W11_CATALOGUE["raw_sha256"], W11_CATALOGUE["raw_bytes"])


# --- Reference kinds (B-1) and the record graph (M-4) ---------------------------------------------------------------


def _ref_fields(node: Any, path: str, defs: dict[str, Any], root: bool = False) -> Iterator[tuple[str, str]]:
    if not isinstance(node, dict):
        return
    target = node.get("$ref", "")
    if target.startswith("#/$defs/"):
        name = target.removeprefix("#/$defs/")
        if name in REF_DEFS:
            yield path, name
        elif name in INLINED_DEFS:
            yield from _ref_fields(defs[name], path, defs)
        return
    if "items" in node:
        yield from _ref_fields(node["items"], f"{path}[]", defs)
    for key, child in node.get("properties", {}).items():
        yield from _ref_fields(child, f"{path}.{key}" if path else key, defs)
    if not root:
        for branch in node.get("oneOf", []):
            yield from _ref_fields(branch, path, defs)


def _walk_ref_fields() -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for kind in ALL_KINDS:
        schema = _schema(kind)
        for path, name in _ref_fields(schema, "", schema["$defs"], root=True):
            assert found.setdefault((kind, path), name) == name, (kind, path)
    return found


def test_every_reference_field_has_its_owned_kind() -> None:
    assert _walk_ref_fields() == REF_FIELDS


@pytest.mark.parametrize(
    ("ref_def", "accepted", "rejected"),
    [
        ("recordRef", "obj", ["dec", "rev", "art", "tsk", "evt"]),
        ("decisionRef", "dec", ["obj", "rev", "art"]),
        ("reviewRef", "rev", ["obj", "dec", "art"]),
        ("artefactRef", "art", ["obj", "dec", "rev"]),
    ],
)
def test_typed_references_accept_only_their_kind(ref_def: str, accepted: str, rejected: list[str]) -> None:
    validator = Draft202012Validator({"$ref": f"#/$defs/{ref_def}", "$defs": _schema(RECORD_KINDS[0])["$defs"]})
    assert validator.is_valid(_ref(accepted))
    for prefix in rejected:
        assert not validator.is_valid(_ref(prefix)), prefix


def test_any_reference_accepts_named_kinds_only() -> None:
    validator = Draft202012Validator({"$ref": "#/$defs/anyRef", "$defs": _schema(RECORD_KINDS[0])["$defs"]})
    for prefix in ("obj", "dec", "rev", "art", "tsk"):
        assert validator.is_valid(_ref(prefix))
    for prefix in ("evt", "xyz"):
        assert not validator.is_valid(_ref(prefix))


def test_source_reference_admits_an_unobserved_file_or_vault_entry() -> None:
    # Re-review N-2 (W9 §6.3, §6.4, W9-T4): a conflict or qualifier may name a file ARS has not observed.
    validator = Draft202012Validator({"$ref": "#/$defs/sourceRef", "$defs": _schema(RECORD_KINDS[0])["$defs"]})
    git_file = {
        "locator_kind": "git_file",
        "repository_path": "results/trajectory_tda_integration/w2_gap_closure_phase1_2026-07-16.json",
        "git_commit": _SHA1,
        "git_blob": _SHA1,
        "sha256": _HASH,
        "byte_length": 10,
        "line_span": None,
    }
    vault = {
        "locator_kind": "vault_file",
        "vault_path": "04-Methods/Computational-Log.md",
        "sha256": _HASH,
        "byte_length": 10,
        "heading_anchor": "2026-10-22 -- T1.20 correction",
    }
    for valid in (git_file, {**git_file, "line_span": {"first_line": 69, "last_line": 71}}, vault, _rec(), _dec()):
        assert validator.is_valid(valid), valid
    for invalid in ({**git_file, "repository_path": "x/cache.pkl"}, {**vault, "locator_kind": "git_file"}, _ref("evt")):
        assert not validator.is_valid(invalid), invalid


def _record_graph(edges: dict[tuple[str, str], tuple[str, ...]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {kind: set() for kind in RECORD_KINDS}
    for (source, path), targets in edges.items():
        if (source, path) not in SAME_KIND_EDGES:
            graph.setdefault(source, set()).update(targets)
    return graph


def _has_cycle(graph: dict[str, set[str]]) -> bool:
    state: dict[str, int] = {}

    def visit(node: str) -> bool:
        state[node] = 1
        for nxt in graph[node]:
            if state.get(nxt) == 1 or (state.get(nxt) is None and visit(nxt)):
                return True
        state[node] = 2
        return False

    return any(state.get(node) is None and visit(node) for node in graph)


def test_record_reference_graph_is_closed_and_acyclic() -> None:
    # Every field whose definition admits an obj_ ID is an edge (re-review N-3), not only the recordRef fields.
    obj_fields = {key for key, name in REF_FIELDS.items() if name in OBJ_ADMITTING_DEFS}
    assert set(RECORD_EDGES) == obj_fields
    assert all(target in RECORD_KINDS for targets in RECORD_EDGES.values() for target in targets)
    assert not _has_cycle(_record_graph(RECORD_EDGES))
    for source, path in SAME_KIND_EDGES:
        assert RECORD_EDGES[(source, path)] == (source,)
    # Negative controls (W9-T21): a root naming its transition, by a new field or by a qualifier source.
    for field in ("transition_event_ref", "qualifiers[].source_ref"):
        cyclic = {**RECORD_EDGES, ("legacy-paper-root", field): ("legacy-ownership-transitioned",)}
        assert _has_cycle(_record_graph(cyclic)), field


def test_supersession_targets_are_w9_section_13s_four_kinds() -> None:
    # P-070: W9 §13.1-13.2, not §5.2's row, fix the targets; a supersession is never itself a target.
    assert set(SUPERSESSION_TARGETS) == {
        "legacy-observation",
        "legacy-closed-reference-acceptance",
        "legacy-adoption-decision",
        "legacy-transition-mapping",
    }
    graph = _record_graph(RECORD_EDGES)
    assert not any("legacy-record-supersession" in targets for targets in graph.values())


def test_paper_root_fields_are_an_owned_allowlist() -> None:
    fields = set(_schema("legacy-paper-root")["properties"]) - set(_header("legacy-paper-root"))
    assert fields == PAPER_ROOT_FIELDS


# --- Records ---------------------------------------------------------------------------------------------------------


def _paper_root() -> dict[str, Any]:
    return {
        **_header("legacy-paper-root"),
        "paper_key": "P01-A",
        "manuscript_root_path": "papers/P01-A-JRSSA/",
        "qualifiers": [],
        "owner_actor_id": _ACT,
        "recovery": None,
    }


def test_paper_root_binds_its_path_and_is_never_revised() -> None:
    root = _paper_root()
    assert _valid("legacy-paper-root", root)
    assert not _valid("legacy-paper-root", {**root, "manuscript_root_path": "papers/P01-B-JRSSB/"})
    assert not _valid("legacy-paper-root", {**root, "record_revision": 2, "supersedes_revision": 1})
    recovery = {**root, "recovery": {"predecessor_root_ref": _rec(), "recovery_decision_ref": _dec()}}
    assert _valid("legacy-paper-root", recovery)
    recovery["recovery"]["recovery_decision_ref"] = _rec()
    assert not _valid("legacy-paper-root", recovery)


def _transition(from_mode: str, to_mode: str, *, mapping: bool) -> dict[str, Any]:
    return {
        **_header("legacy-ownership-transitioned"),
        "mapping_ref": _rec() if mapping else None,
        "subject_registration_ref": _rec(),
        "paper_root_ref": _rec() if mapping else None,
        "from_mode": from_mode,
        "to_mode": to_mode,
        "reviewer_ref": _rev(),
        "decision_ref": _dec(),
    }


def test_transitions_are_w9s_three_and_bind_their_refs() -> None:
    kind = "legacy-ownership-transitioned"
    assert _valid(kind, _transition("legacy_owned", "successor_owned", mapping=True))
    assert _valid(kind, _transition("legacy_owned", "closed_reference", mapping=False))
    assert _valid(kind, _transition("successor_owned", "closed_reference", mapping=False))
    assert not _valid(kind, _transition("successor_owned", "legacy_owned", mapping=True))
    assert not _valid(kind, _transition("legacy_owned", "successor_owned", mapping=False))
    # Review m-2: a closed-reference transition names no mapping or root.
    assert not _valid(kind, _transition("legacy_owned", "closed_reference", mapping=True))
    assert not _valid(kind, _transition("successor_owned", "closed_reference", mapping=True))


def _tracked(path: str = "results/x.json") -> dict[str, Any]:
    return {
        "identity_kind": "git_tracked",
        "repository_path": path,
        "git_commit": _SHA1,
        "git_blob": _SHA1,
        "sha256": _HASH,
        "byte_length": 1,
    }


def _observation(source: dict[str, Any]) -> dict[str, Any]:
    return {
        **_header("legacy-observation"),
        "registration_ref": _rec(),
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
                "signed_w0_revision_ref": _art(),
                "signature_record_ref": _art(),
            }
        ],
        "qualifiers": [],
        "conflicts": [],
        "non_inferences": ["no Git identity"],
    }


def test_restricted_bytes_never_carry_a_frozen_copy() -> None:
    restricted = {
        "identity_kind": "restricted_untracked_file",
        "path": "x/cache.pkl",
        "sha256": _HASH,
        "byte_length": 1,
    }
    assert _valid("legacy-observation", _observation(restricted))
    assert not _valid("legacy-observation", _observation({**restricted, "frozen_copy_ref": _art()}))
    # Review M-3 (P-069 item 3): a restricted suffix under any other label is refused, in either case, in every
    # non-restricted branch, for every suffix on the contract's list (re-review n-2).
    untracked = {"identity_kind": "untracked_file", "sha256": _HASH, "byte_length": 1, "frozen_copy_ref": _art()}
    vault = {"identity_kind": "vault_file", "sha256": _HASH, "byte_length": 1, "frozen_copy_ref": _art()}
    for suffix in _contract()["restricted_suffixes"]:
        for name in (f"x/data{suffix.lower()}", f"x/data{suffix.upper()}"):
            for source in ({**untracked, "path": name}, {**vault, "vault_path": name}, _tracked(name)):
                assert not _valid("legacy-observation", _observation(source)), source
    # Re-review n-1: a trailing dot or space, which Win32 strips, does not hide the suffix.
    for path in ("x/null_cache.pkl.", "x/null_cache.pkl ", "x/NULL_C~1.PKL"):
        assert not _valid("legacy-observation", _observation({**untracked, "path": path})), path
    assert _valid("legacy-observation", _observation({**untracked, "path": "x/notes.json"}))
    assert _valid("legacy-observation", _observation({**vault, "vault_path": "x/notes.md"}))


def test_observation_names_unobserved_sources_for_conflicts_and_qualifiers() -> None:
    # Re-review N-2: W9-T4 imports SUPERSEDED.md lines 69-71 alone, naming the tier-1 file; a corrected_by qualifier
    # cites a dated vault entry; the signed W0 revision is a repository document at a commit.
    summary = {
        "locator_kind": "git_file",
        "repository_path": "results/SUPERSEDED.md",
        "git_commit": _SHA1,
        "git_blob": _SHA1,
        "sha256": _HASH,
        "byte_length": 10,
        "line_span": {"first_line": 69, "last_line": 71},
    }
    tier1 = {**summary, "repository_path": "results/w2_gap_closure_phase1_2026-07-16.json", "line_span": None}
    vault = {
        "locator_kind": "vault_file",
        "vault_path": "04-Methods/Computational-Log.md",
        "sha256": _HASH,
        "byte_length": 10,
        "heading_anchor": "2026-10-22 -- T1.20 correction",
    }
    observation = _observation(_tracked())
    observation["conflicts"] = [
        {"conflicting_record_refs": [summary, tier1], "resolution": "resolved_by_precedence", "precedence_tier": 1}
    ]
    observation["qualifiers"] = [{"qualifier_kind": "corrected_by", "source_ref": vault, "text": "T1.20 correction"}]
    observation["families"][0]["signed_w0_revision_ref"] = {**summary, "line_span": None}
    assert _valid("legacy-observation", observation)


def test_vault_alias_of_conventions_is_never_an_observation_source() -> None:
    # Confirmation r-1 (W9 §7.3): the vault alias is a prohibited read path for observations, as a source identity
    # (V1) and as a source locator (L1); the repository path stays the only one.
    for name in ("CONVENTIONS.md", "conventions.md", "x/CONVENTIONS.md"):
        alias = {"identity_kind": "vault_file", "vault_path": name, "sha256": _HASH, "byte_length": 1}
        assert not _valid("legacy-observation", _observation({**alias, "frozen_copy_ref": _art()})), name
        locator = {"locator_kind": "vault_file", "vault_path": name, "sha256": _HASH, "byte_length": 1}
        observation = _observation(_tracked())
        observation["qualifiers"] = [
            {"qualifier_kind": "corrected_by", "source_ref": {**locator, "heading_anchor": None}, "text": "x"}
        ]
        assert not _valid("legacy-observation", observation), name
    assert _valid("legacy-observation", _observation(_tracked("CONVENTIONS.md")))


def test_observation_classes_require_a_signed_w0_record() -> None:
    observation = _observation(_tracked())
    assert _valid("legacy-observation", observation)
    for field in ("signature_record_ref", "signed_w0_revision_ref"):
        broken = deepcopy(observation)
        del broken["families"][0][field]
        assert not _valid("legacy-observation", broken), field
    observation["families"][0]["family_name"] = "Whole File"
    assert not _valid("legacy-observation", observation)


def test_observation_binds_its_selector_and_conflicts() -> None:
    observation = _observation(_tracked())
    item = {
        "selector_kind": "inventory_item",
        "inventory_ref": _rec(),
        "row_ordinal": 1,
        "anchor_text": "x",
        "raw_row_sha256": _HASH,
    }
    assert not _valid("legacy-observation", {**observation, "selector": item})
    assert _valid(
        "legacy-observation", {**observation, "selector": item, "segmentation_contract": "w9-segmentation/1.0.0"}
    )
    assert not _valid("legacy-observation", {**observation, "segmentation_contract": "w9-segmentation/1.0.0"})
    conflict = {
        "conflicting_record_refs": [_rec(), _dec()],
        "resolution": "resolved_by_precedence",
        "precedence_tier": 2,
    }
    assert _valid("legacy-observation", {**observation, "conflicts": [conflict]})
    assert not _valid("legacy-observation", {**observation, "conflicts": [{**conflict, "precedence_tier": None}]})
    assert not _valid(
        "legacy-observation", {**observation, "conflicts": [{**conflict, "conflicting_record_refs": [_rec(), _rec()]}]}
    )
    assert not _valid("legacy-observation", {**observation, "created_at": "notadateZ"})


def _acceptance() -> dict[str, Any]:
    return {
        **_header("legacy-closed-reference-acceptance"),
        "independent_review_ref": _rev(),
        "decision_ref": _dec(),
        "items": [
            {
                "observation_ref": _rec(),
                "pilot_promotion": [
                    {"fixture_id": "F-018", "disposition": "evidence", "ref": _art()},
                    {"fixture_id": "S-017", "disposition": "waiver", "ref": _dec()},
                ],
            }
        ],
        "threshold_preregistration_sha256": _HASH,
        "governing_record_set_sha256": _HASH,
        "anchors": [
            {"anchored": "threshold_preregistration", "anchor_kind": "git_commit", "value": _SHA1},
            {"anchored": "governing_record_set", "anchor_kind": "ars_event", "value": f"evt_{_UUID}"},
        ],
        "enforcement_change_list": None,
    }


def test_closed_reference_binds_per_fixture_evidence_or_waiver() -> None:
    kind = "legacy-closed-reference-acceptance"
    acceptance = _acceptance()
    assert _valid(kind, acceptance)
    # Fixture IDs follow the eval schemas (^[FS]-[0-9]{3}$), with no variant suffix (P-066: S-017).
    bad = deepcopy(acceptance)
    bad["items"][0]["pilot_promotion"][0]["fixture_id"] = "S-016/OM"
    assert not _valid(kind, bad)
    # Review M-5: a waiver is an owner Decision; every item names its fixtures; refs are typed.
    bad = deepcopy(acceptance)
    bad["items"][0]["pilot_promotion"][1]["ref"] = _art()
    assert not _valid(kind, bad)
    bad = deepcopy(acceptance)
    bad["items"][0]["pilot_promotion"] = []
    assert not _valid(kind, bad)
    assert not _valid(kind, {**acceptance, "decision_ref": _rec()})
    assert not _valid(kind, {**acceptance, "independent_review_ref": _dec()})
    assert not _valid(kind, {**acceptance, "items": acceptance["items"] * 2})


def test_closed_reference_anchors_both_hashes() -> None:
    kind = "legacy-closed-reference-acceptance"
    acceptance = _acceptance()
    assert not _valid(kind, {**acceptance, "threshold_preregistration_sha256": None})
    assert not _valid(kind, {**acceptance, "anchors": [acceptance["anchors"][0], acceptance["anchors"][0]]})
    one_kind = [{**anchor, "anchored": "governing_record_set"} for anchor in acceptance["anchors"]]
    assert not _valid(kind, {**acceptance, "anchors": one_kind})
    bad = deepcopy(acceptance)
    bad["anchors"][0]["value"] = "not-a-commit"
    assert not _valid(kind, bad)
    bad = deepcopy(acceptance)
    bad["anchors"][1]["value"] = _SHA1
    assert not _valid(kind, bad)
    # PR #394 review: each hash has exactly one anchor; two different threshold anchors leave no rule to choose.
    second = {"anchored": "threshold_preregistration", "anchor_kind": "git_commit", "value": "1" * 40}
    assert not _valid(kind, {**acceptance, "anchors": [*acceptance["anchors"], second]})


def test_membership_binds_the_accepted_table_and_the_bytes_its_author_read() -> None:
    # WP9.0 membership template §1, §3 rule 10 and §4 (re-review N-8, N-9).
    kind = "legacy-field-family-membership"
    membership = {
        **_header(kind),
        "file_schema_id": "usoc-headline-frozen-2026-05-28",
        "applies_to": [
            {
                "path": "results/example.json",
                "identity_kind": "git_tracked",
                "git_blob": _SHA1,
                "sha256": _HASH,
                "size_bytes": 10,
            }
        ],
        "table_sha256": _HASH,
        "families": [{"name": "h0_w2", "definition_source": "G7-A §6.1 row T1.37", "pointers": ["", "/result/[*]/h0"]}],
        "unassigned": [],
        "author_actor_id": _ACT,
        "review_ref": _rev(),
        "acceptance_decision_ref": _dec(),
    }
    assert _valid(kind, membership)
    untracked = {**membership["applies_to"][0], "identity_kind": "untracked_file"}
    assert not _valid(kind, {**membership, "applies_to": [untracked]})
    assert _valid(kind, {**membership, "applies_to": [{**untracked, "git_blob": None}]})
    assert not _valid(kind, {**membership, "applies_to": [{**membership["applies_to"][0], "git_blob": None}]})
    assert not _valid(kind, {k: v for k, v in membership.items() if k != "table_sha256"})
    assert not _valid(kind, {**membership, "families": [{"name": "h0_w2", "class_source": "x", "pointers": ["/a"]}]})
    assert not _valid(kind, {**membership, "review_ref": _dec()})


def _registration(role: str, path: str, mode: str, writers: list[str], **extra: Any) -> dict[str, Any]:
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
        "writer_classes": writers,
        "prohibited_consumers": [],
        "registration_decision_ref": _dec(),
        **extra,
    }


def _reg_valid(*args: Any, **kwargs: Any) -> bool:
    return _valid("legacy-path-registration", _registration(*args, **kwargs))


def test_registration_binds_the_successor_root_and_rejects_bad_paths() -> None:
    ars = ["ars_reviewed_pr"]
    assert _reg_valid("successor_results_root", "results/ars/", "successor_owned", ars)
    assert not _reg_valid("successor_results_root", "results/", "successor_owned", ars)
    assert not _reg_valid("successor_results_root", "results/ars/", "legacy_owned", ars)
    for path in (
        "../x.json",
        "/abs.json",
        "results\\x.json",
        "./x.json",
        "results//x.json",
        "results/./x.json",
        "x.json ",
        "~/x",
        "results/x.json.",
        "results/dir./x.json",
        "results/dir /x.json",
        "results/RESULT~1.JSO",
    ):
        assert not _reg_valid("legacy_research_result", path, "legacy_owned", []), path


def test_registration_writer_classes_follow_the_role() -> None:
    # Review M-1 (W9 §4.2, §4.3): no successor writer on a legacy file; the shared surface has exactly its class.
    assert _reg_valid("legacy_research_result", "results/x.json", "legacy_owned", ["owner_ruling"])
    assert not _reg_valid(
        "legacy_research_result", "results/x.json", "legacy_owned", ["ars_reviewed_pr_with_owner_note"]
    )
    assert not _reg_valid("legacy_research_result", "results/x.json", "legacy_owned", ["ars_reviewed_pr"])
    assert _reg_valid(
        "shared_enforcement_surface", "contracts/x.yaml", "legacy_owned", ["ars_reviewed_pr_with_owner_note"]
    )
    assert not _reg_valid("shared_enforcement_surface", "contracts/x.yaml", "legacy_owned", ["owner_ruling"])
    assert not _reg_valid("successor_results_root", "results/ars/", "successor_owned", ["legacy_lane_commit"])
    assert not _reg_valid("successor_results_root", "results/ars/", "successor_owned", ["ars_projection_rebuild"])


def test_projection_is_successor_owned_untracked_and_rebuilt() -> None:
    # Re-review N-1 (W9 §7.2, 06v O-16): the projection is gitignored and written only by `ars projection rebuild`.
    path = ".research-system/projections/legacy/accepted-observations.json"
    rebuild = ["ars_projection_rebuild"]
    untracked = {"source_identity_kind": "untracked_file"}
    assert _reg_valid("legacy_read_only_projection", path, "successor_owned", rebuild, **untracked)
    for writers in (["ars_reviewed_pr"], [], ["owner_ruling"]):
        assert not _reg_valid("legacy_read_only_projection", path, "successor_owned", writers, **untracked), writers
    for mode in ("legacy_owned", "closed_reference"):
        assert not _reg_valid("legacy_read_only_projection", path, mode, rebuild, **untracked), mode
    assert not _reg_valid("legacy_read_only_projection", path, "successor_owned", rebuild)
    assert not _reg_valid("legacy_read_only_projection", "projections/x.md", "successor_owned", rebuild, **untracked)
    vault = {"root_kind": "vault_root", "source_identity_kind": "vault_file"}
    assert not _reg_valid("legacy_read_only_projection", path, "successor_owned", rebuild, **vault)
    assert not _reg_valid("legacy_research_result", "results/x.json", "legacy_owned", rebuild)


def test_conventions_is_registrable_only_as_the_lock_at_its_repository_path() -> None:
    # Review M-2 (W9 §7.3): the vault alias is a prohibited read path.
    assert _reg_valid("conventions_lock", "CONVENTIONS.md", "legacy_owned", [])
    vault = {"root_kind": "vault_root", "source_identity_kind": "vault_file"}
    assert not _reg_valid("conventions_lock", "CONVENTIONS.md", "legacy_owned", [], **vault)
    assert not _reg_valid("conventions_lock", "CONVENTIONS.md", "legacy_owned", [], source_identity_kind="vault_file")
    for role in ("legacy_decision_log_entry", "legacy_contract"):
        assert not _reg_valid(role, "CONVENTIONS.md", "legacy_owned", [], **vault), role
        assert not _reg_valid(role, "conventions.md", "legacy_owned", [], **vault), role
        assert not _reg_valid(role, "docs/CONVENTIONS.md", "legacy_owned", []), role
        # Re-review n-1: Win32 aliases of the same name.
        for alias in ("CONVENTIONS.md.", "CONVENTIONS.md ", "CONVEN~1.MD"):
            assert not _reg_valid(role, alias, "legacy_owned", [], **vault), (role, alias)


def test_manuscript_roots_are_the_two_p01_roots() -> None:
    for path in ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/"):
        assert _reg_valid("legacy_manuscript_root", path, "legacy_owned", [])
    assert not _reg_valid("legacy_manuscript_root", "papers/P04-AOAS/", "legacy_owned", [])


def test_registration_root_and_identity_kinds_cohere() -> None:
    # Review m-3 and M-3.
    vault = {"root_kind": "vault_root", "source_identity_kind": "vault_file"}
    assert _reg_valid("legacy_decision_log_entry", "04-Methods/Computational-Log.md", "legacy_owned", [], **vault)
    assert not _reg_valid("legacy_decision_log_entry", "x.md", "legacy_owned", [], root_kind="vault_root")
    assert not _reg_valid("legacy_research_result", "x.md", "legacy_owned", [], source_identity_kind="vault_file")
    assert not _reg_valid(
        "legacy_research_result", "x/null_cache.pkl", "legacy_owned", [], source_identity_kind="untracked_file"
    )
    assert _reg_valid(
        "legacy_research_result",
        "x/null_cache.pkl",
        "legacy_owned",
        [],
        source_identity_kind="restricted_untracked_file",
    )


def test_citation_status_binds_adoption_refs_to_status() -> None:
    status = {
        **_header("legacy-paper-citation-status"),
        "root_ref": _rec(),
        "cited_family_set_sha256": _HASH,
        "derivation": {
            "extractor_output_sha256": _HASH,
            "reviewer_derivation_sha256": _HASH,
            "reviewer_actor_id": _ACT,
        },
        "families": [{"observation_ref": _rec(), "family_name": "h0_w2", "status": "adopted", "adoption_ref": _rec()}],
        "supersedes_status_ref": None,
    }
    assert _valid("legacy-paper-citation-status", status)
    status["families"][0]["adoption_ref"] = None
    assert not _valid("legacy-paper-citation-status", status)
    status["families"][0]["status"] = "unadopted"
    assert _valid("legacy-paper-citation-status", status)


# --- The light inventory and the accepted segmentation contract (B-2) -----------------------------------------------

_SEGMENTATION_INPUTS: dict[str, tuple[bytes, dict[str, Any]]] = {
    "heading_section": (
        b"## Lifecycle\n```\n## fake\n```\n---\n## item-a\nx\n## item-a\ny\n",
        {"level": 2, "structural": [(1, 5)]},
    ),
    "computational_log_entry": (b"# Log\n\n### 2026-01-01 a\nx\n### 2026-13x bad\ny\n", {}),
    "tracker_task_row": (b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.37 | a |\n| bad | b |\n", {}),
    "working_note_entry": (b"## Working Notes\n- **2026-01-01: a**\n- undated\nstray\n", {}),
    "log_frontmatter": (b"\xef\xbb\xbf---\r\na: b\r\n---\r\n", {}),
    "conventions_unit": (b"# C\n## S\n- x\n- x\n\nPara\n\n*Last updated: 2026-07-16*\n", {}),
}


def _inventory(selector: str, result: dict[str, Any], *, level: int | None = None) -> dict[str, Any]:
    rows = [
        {
            "selector_kind": selector,
            **{key: None for key in ("unit_hash", "unit_ordinal", "dated", "task_id")},
            **row,
        }
        for row in result["rows"]
    ]
    region: dict[str, Any] = {"form": "fixed_by_selector"}
    if selector == "heading_section":
        lines = result["file_facts"]["line_count"]
        region = {"form": "line_range", "first_line": 1, "last_line": lines, "anchor_line_sha256s": [_HASH]}
    return {
        **_header("legacy-light-inventory"),
        "registration_ref": _rec(),
        "source_identity": _tracked("legacy/source.md"),
        "segmentation_contract": result["segmentation_contract"],
        "selector_kind": selector,
        "heading_level": level,
        "covered_region": region,
        "structural_ranges": [{"first_line": 1, "last_line": 5}] if selector == "heading_section" else [],
        "suppressed_anchors": result["suppressed_anchors"],
        "file_facts": result["file_facts"],
        "read_started_at": "2026-10-23T09:07:42.990960Z",
        "read_ended_at": "2026-10-23T09:07:43.027460Z",
        "path_form": {"path_as_given": "legacy/source.md", "resolved_through_link": False, "resolved_target": None},
        "observer_actor_id": _ACT,
        "rows": rows,
        "independent_reproduction_ref": _rev(),
    }


@pytest.mark.parametrize("selector", sorted(_SEGMENTATION_INPUTS))
def test_inventory_holds_what_the_reference_tool_emits(selector: str) -> None:
    tool = _load_tool("w9_segmentation")
    data, options = _SEGMENTATION_INPUTS[selector]
    result = tool.segment(data, selector, **options)
    inventory = _inventory(selector, result, level=options.get("level"))
    validator = Draft202012Validator(
        _schema("legacy-light-inventory"), format_checker=Draft202012Validator.FORMAT_CHECKER
    )
    assert not list(validator.iter_errors(inventory))
    stripped = deepcopy(inventory)
    del stripped["rows"][0]["anchor_line_sha256"]
    assert not validator.is_valid(stripped)


def test_inventory_holds_the_empty_file_blocker_row() -> None:
    tool = _load_tool("w9_segmentation")
    result = tool.segment(b"", "log_frontmatter")
    inventory = _inventory("log_frontmatter", result)
    assert _valid("legacy-light-inventory", inventory)
    bad = deepcopy(inventory)
    bad["rows"][0]["byte_length"] = 1
    assert not _valid("legacy-light-inventory", bad)
    bad = deepcopy(inventory)
    bad["rows"][0]["row_kind"] = "item"
    bad["rows"][0]["blocker_reason"] = None
    bad["rows"][0]["anchor_text"] = "frontmatter"
    assert not _valid("legacy-light-inventory", bad)


def test_inventory_binds_selector_fields_region_and_read_record() -> None:
    tool = _load_tool("w9_segmentation")
    data, options = _SEGMENTATION_INPUTS["tracker_task_row"]
    inventory = _inventory("tracker_task_row", tool.segment(data, "tracker_task_row", **options))
    assert _valid("legacy-light-inventory", inventory)
    item = next(row for row in inventory["rows"] if row["row_kind"] == "item")
    for field, value in (("task_id", None), ("dated", True), ("unit_ordinal", 1), ("anchor_text", None)):
        bad = deepcopy(inventory)
        next(row for row in bad["rows"] if row["row_ordinal"] == item["row_ordinal"])[field] = value
        assert not _valid("legacy-light-inventory", bad), field
    for field, value in (
        ("covered_region", {"form": "line_range", "first_line": 1, "last_line": 2, "anchor_line_sha256s": []}),
        ("heading_level", 2),
        ("read_started_at", "2026-10-23T09:07:42Z"),
        ("independent_reproduction_ref", None),
        ("path_form", {"path_as_given": "x", "resolved_through_link": True, "resolved_target": None}),
    ):
        assert not _valid("legacy-light-inventory", {**inventory, field: value}), field
    data, options = _SEGMENTATION_INPUTS["heading_section"]
    heading = _inventory("heading_section", tool.segment(data, "heading_section", **options), level=2)
    assert _valid("legacy-light-inventory", heading)
    assert not _valid("legacy-light-inventory", {**heading, "covered_region": {"form": "fixed_by_selector"}})
    assert not _valid("legacy-light-inventory", {**heading, "heading_level": None})
    # Re-review n-4: every row carries its inventory's selector kind.
    mixed = deepcopy(heading)
    mixed["rows"][0]["selector_kind"] = "computational_log_entry"
    assert not _valid("legacy-light-inventory", mixed)


# --- Stage B1 additions: the use-time mismatch record and the inert revision import (P-072 items 3 and 5) ----------


def test_adoption_use_mismatch_binds_the_adoption_and_the_successor_task() -> None:
    kind = "legacy-adoption-use-mismatch"
    mismatch = {
        **_header(kind),
        "adoption_ref": _rec(),
        "successor_task_ref": _ref("tsk"),
        "expected_sha256": _HASH,
        "observed_sha256": "1" * 64,
        "observed_byte_length": 10,
        "detected_at": "2026-10-24T00:00:00Z",
        "guard_actor_id": _ACT,
    }
    assert _valid(kind, mismatch)
    assert not _valid(kind, {**mismatch, "adoption_ref": _dec()})
    assert not _valid(kind, {**mismatch, "successor_task_ref": _art()})
    assert not _valid(kind, {k: v for k, v in mismatch.items() if k != "observed_sha256"})


def test_catalogue_revision_import_is_inert_and_names_superseded_rows() -> None:
    kind = "import-accepted-w9-catalogue-revision"
    identity = {
        "repository_path": "x.json",
        "git_commit": _SHA1,
        "git_blob": _SHA1,
        "file_length": 1,
        "file_sha256": _HASH,
    }
    revision = {
        "schema_id": f"ars://legacy/{kind}",
        "schema_version": "1.0.0",
        "bootstrap_contract_identity": identity,
        "superseded_catalogue_identity": identity,
        "revision_envelope_identity": identity,
        # P-074 item 2: each superseded v1 row maps to its named replacing revision row.
        "row_supersessions": [{"superseded_owner_row_id": "LR-016", "replacing_owner_row_id": "LR-062"}],
        "requested_transaction_id": "txn",
        "refused_store_identities": [GATE6_STORE_IDENTITY],
        "verification_requirements": ["every v1 row unchanged or superseded"],
        "activation_status": "not_executed",
    }
    assert _valid(kind, revision)
    assert not _valid(kind, {**revision, "activation_status": "executed"})
    assert not _valid(kind, {**revision, "row_supersessions": [{"superseded_owner_row_id": "OR-016"}]})
    unnamed = [{"superseded_owner_row_id": "LR-016", "replacing_owner_row_id": None}]
    assert not _valid(kind, {**revision, "row_supersessions": unnamed})


def test_acceptance_envelope_names_the_owner_annex() -> None:
    # P-074 item 3: the O-8 envelope names the annex explicitly.
    envelope = _schema("w9-catalogue-acceptance-envelope")
    assert "owner_annex_identity" in envelope["required"]
