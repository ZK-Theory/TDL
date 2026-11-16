# Research context: docs/plans/agentic-research-system/reviews/wp9-4-design-note-review-3c10de9a-2026-11-16.md (P-085)
# Purpose: the WP9.4 design-note reviewer's asserting probes. Each runs on pure functions, in-memory legacy states and
# forged transactions, or on Git object reads at the reviewed commit. None opens a store or writes a file. A probe whose
# name starts with ``test_defect_`` passes when the defect it names is present at 3c10de9a.
"""Reviewer probes for the WP9.4 design note, revision 1, at ``3c10de9a``.

The note's §17 claims 1 to 7 and the findings of the review report. Run from the repository root:

    uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider \
        docs/plans/agentic-research-system/reviews/wp9-4-design-note-review-artifacts/
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system.artefacts import authority as artefact_authority  # noqa: E402
from research_system.command.service import CommandService  # noqa: E402
from research_system.errors import IntegrityError  # noqa: E402
from research_system.legacy.records import derived_id, record_content_hash, utc_milliseconds  # noqa: E402
from research_system.legacy.replay import reducers  # noqa: E402
from research_system.legacy.runtime import LegacyRuntime  # noqa: E402
from research_system.schema_registry import runtime_schema_registry  # noqa: E402

REVIEWED = "3c10de9a69c56d46d398fb327851ad11d1493d08"
SCHEMAS = REPO_ROOT / ".research-system" / "schemas"
W9_SCHEMAS = SCHEMAS / "contracts" / "w9"
T0 = "2026-11-16T10:00:00Z"
LATER = datetime(2026, 12, 31, tzinfo=UTC)


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True).stdout


def _tree_paths(prefix: str) -> list[str]:
    raw = _git("ls-tree", "-r", "-z", "--name-only", REVIEWED, prefix)
    return [path for path in raw.decode("utf-8").split("\0") if path]


def _blob(path: str) -> bytes:
    return _git("show", f"{REVIEWED}:{path}")


def _hashed(record: dict[str, Any]) -> dict[str, Any]:
    record = dict(record)
    record["content_hash"] = record_content_hash(record)
    return record


def _ref(record: dict[str, Any]) -> dict[str, Any]:
    return {"id": record["record_id"], "record_revision": 1, "content_hash": record_content_hash(record)}


def test_reviewed_code_is_unchanged_since_the_reviewed_commit() -> None:
    """The probes import the working tree, so its code and schemas must be the reviewed commit's."""
    diff = _git("diff", "--name-only", REVIEWED, "--", "research_system", ".research-system", "papers")
    assert diff == b""


# --- Claim 1: source_import_refs is read nowhere under research_system/command/ ------------------------------------


def test_claim1_holds_source_import_refs_unread_under_command() -> None:
    command_files = sorted((REPO_ROOT / "research_system" / "command").rglob("*.py"))
    assert command_files
    assert not [path for path in command_files if "source_import_refs" in path.read_text(encoding="utf-8")]
    writers = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "research_system").rglob("*.py")
        if "source_import_refs" in path.read_text(encoding="utf-8")
    ]
    assert writers == ["research_system/evals/executors/release_tranche.py"]


# --- Claim 2: no code path lets a claim take a legacy family as evidence ------------------------------------------


def test_defect_claim2_register_artefact_admits_a_legacy_result_path_today() -> None:
    """The claim path exists and is open to a legacy file until WP9.7's RegisterArtefact guard lands."""
    source = inspect.getsource(CommandService._prepare_artefact_authority_command)
    assert "legacy" not in source and "results/ars" not in source and "relative_path" not in source
    schema = json.loads((SCHEMAS / "core" / "commands" / "register_artefact.schema.json").read_text(encoding="utf-8"))
    relative_path = schema["$defs"]["artefact_manifest"]["properties"]["relative_path"]
    assert "pattern" not in relative_path and "not" not in relative_path
    # Both consumer kinds a manuscript or a claim reads are live, and the claim one needs claim_promotion only.
    assert {"claim_evidence", "manuscript_evidence"} <= set(artefact_authority._CONSUMER_KINDS)
    promotion = inspect.getsource(CommandService._prepare_artefact_authority_command)
    assert "_claim_promotion_binding" in promotion


# --- Claim 3: a W9 record event needs no runtime-binding row --------------------------------------------------------


class _NoSchemas:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"an E: event consulted the schema registry: {name}")


def test_claim3_holds_e_event_needs_no_binding_row_and_census_is_273() -> None:
    fake = type("Fake", (), {"schemas": _NoSchemas()})()
    for event_type in ("LegacyAdoptionDecisionRecorded", "LegacyDischargeRelationRecorded"):
        assert LegacyRuntime._event_schema(fake, event_type, "ResolveW9AuthorityDecision") == (
            "ars://core/event",
            "1.0.0",
        )
    assert len(runtime_schema_registry(SCHEMAS).active_bindings()) == 273


# --- Claim 4 and owner point C: the adoption has no review field ----------------------------------------------------


def test_claim4_first_half_holds_adoption_schema_has_no_review_ref() -> None:
    schema = json.loads((W9_SCHEMAS / "legacy-adoption-decision.schema.json").read_text(encoding="utf-8"))
    properties = set(schema["properties"])
    assert not [name for name in properties if "review" in name]
    for kind in ("discharge-relation", "source-inventory", "transition-mapping", "ownership-transitioned"):
        other = json.loads((W9_SCHEMAS / f"legacy-{kind}.schema.json").read_text(encoding="utf-8"))
        assert "reviewer_ref" in other["properties"]


def test_claim4_derived_review_id_is_a_valid_deterministic_rev_id() -> None:
    record_id = "obj_0197aaaa-0000-7000-8000-000000000001"
    first = derived_id("rev", "w9-adoption-review:" + record_id, utc_milliseconds(T0))
    assert first == derived_id("rev", "w9-adoption-review:" + record_id, utc_milliseconds(T0))
    assert first.startswith("rev_")
    state = reducers.new_legacy_state()
    reducers._reserve(state, first, "review", record_id, {})
    assert state["reservations"][first]["kind"] == "review"


def _adoption_record() -> dict[str, Any]:
    return _hashed(
        {
            "schema_id": "ars://legacy/legacy-adoption-decision",
            "schema_version": "1.0.0",
            "record_id": "obj_adoption",
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": "prj_x",
            "created_at": T0,
            "created_by_actor_id": "act_analyst",
            "observation_ref": {"id": "obj_obs", "record_revision": 1, "content_hash": "0" * 64},
            "subject": {"subject_kind": "families", "family_names": ["a"]},
            "intended_use": {"description": "w9-use:task-input", "successor_ref": None},
            "w5_consequence": "admissible_for_named_use",
            "qualifiers_to_discharge": [],
            "decision_ref": {"id": "dec_adoption", "record_revision": 1, "content_hash": "1" * 64},
        }
    )


def _resolution(row: str, record: dict[str, Any] | None, considered: list[str]) -> tuple[dict, list]:
    record_id = record["record_id"] if record else "obj_none"
    subject_hash = record_content_hash(record) if record else "2" * 64
    refs = [f"W9:{row}", f"w9-subject:{record_id}", f"w9-subject-sha256:{subject_hash}"]
    decision = {"subject": (record_id, subject_hash), "governing_evidence_refs": refs, "expires_at": LATER}
    payload = {
        "decision_id": "dec_adoption",
        "selected_option": "accept",
        "effective_scope": f"w9-record:{record_id}",
        "decision_revision": 1,
        "deciding_actor_id": "act_stephen",
        "decision_authority_grant_id": "grt_1",
        "governing_evidence_refs": list(refs),
        "considered_review_ids": considered,
        "effective_at": T0,
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    events = [
        {
            "occurred_at": T0,
            "actor_id": "act_stephen",
            "authority_grant_id": "grt_1",
            "stream_id": "dec_adoption",
            "stream_version": 2,
            "payload": payload,
        }
    ]
    if record is not None:
        events.append({"stream_id": record_id, "stream_version": 2, "payload": record})
    return decision, events


def test_defect_wp9_3_g5_check_passes_an_adoption_with_no_review_at_all() -> None:
    """Every G5 table keys on a record field. With no review field the generic check skips review satisfaction."""
    assert reducers._FAMILY_REVIEW_FIELD.get("legacy_adoption_decision") is None
    record = _adoption_record()
    state = reducers.new_legacy_state()
    state["proposals"]["obj_adoption"] = {"recorded": False, "lapse_at": LATER}
    decision, transaction = _resolution("LR-029", record, considered=[])
    reducers._check_resolution(state, "LR-029", decision, transaction)  # no raise
    assert state["reviews"] == {}


def test_defect_session_rule_refuses_the_analyst_on_every_analyst_proposed_wp9_4_kind() -> None:
    """§5.1 says WP9.4 changes none of the session rules; unchanged, they refuse LR-026/031/046/051 and the Decisions."""
    for kind in (
        "legacy_adoption_decision",
        "legacy_discharge_relation",
        "legacy_transition_mapping",
        "legacy_ownership_transitioned",
    ):
        with pytest.raises(IntegrityError, match="analyst is the proposal's creator"):
            reducers._refuse_analyst_creator({"kind": kind, "actor_id": "act_analyst", "record": {}}, "act_analyst")
    reducers._refuse_analyst_creator(
        {"kind": "legacy_path_registration", "actor_id": "act_analyst", "record": {}}, "act_analyst"
    )


# --- Owner point B: the eligibility Decision does not fit the WP9.3 Decision checks ---------------------------------


def test_defect_eligibility_resolution_has_no_record_event_for_the_generic_g5_check() -> None:
    """LR-025 writes no record. Run through the WP9.3 resolution check, it fails on a missing event, not a rule."""
    state = reducers.new_legacy_state()
    decision, transaction = _resolution("LR-025", None, considered=[])
    assert len(transaction) == 1
    with pytest.raises(IndexError):
        reducers._check_resolution(state, "LR-025", decision, transaction)


def test_defect_decision_proposal_admits_exactly_three_refs_so_no_fixture_or_eligibility_ref_fits() -> None:
    """P-072 item 4: fixture evidence or waiver refs travel in the resolving Decision. WP9.3 fixes three refs."""
    payload = {
        "governing_evidence_refs": [
            "W9:LR-019",
            "w9-subject:obj_x",
            "w9-subject-sha256:" + "0" * 64,
            "w9-fixture:F-018:rev_x",
        ]
    }
    with pytest.raises(IntegrityError, match="does not encode its subject"):
        reducers._check_decision_proposal(reducers.new_legacy_state(), "LR-019", {"occurred_at": T0}, payload)
    record = _adoption_record()
    decision, transaction = _resolution("LR-029", record, considered=[])
    transaction[0]["payload"]["governing_evidence_refs"].append("w9-fixture:F-015:rev_x")
    with pytest.raises(IntegrityError, match="governing_evidence_refs"):
        reducers._check_resolution(
            {**reducers.new_legacy_state(), "proposals": {"obj_adoption": {"recorded": False, "lapse_at": LATER}}},
            "LR-029",
            decision,
            transaction,
        )


# --- Claim 5: a root registration is never closed by LR-020 ---------------------------------------------------------


def test_claim5_holds_only_at_the_reader_replay_would_close_a_root_registration() -> None:
    registration = {"role": "legacy_manuscript_root", "ownership_mode": "legacy_owned"}
    observation = _hashed(
        {
            "schema_id": "ars://legacy/legacy-observation",
            "record_id": "obj_root_obs",
            "record_revision": 1,
            "registration_ref": {"id": "obj_root_reg", "record_revision": 1, "content_hash": "3" * 64},
            "selector": {"selector_kind": "whole_file"},
        }
    )
    state = reducers.new_legacy_state()
    state["records"]["legacy_path_registration"] = {"obj_root_reg": registration}
    state["records"]["legacy_observation"] = {"obj_root_obs": observation}
    acceptance = {
        "record_id": "obj_acceptance",
        "created_at": T0,
        "created_by_actor_id": "act_analyst",
        "project_id": "prj_x",
        "items": [{"observation_ref": _ref(observation)}],
        "independent_review_ref": {"id": "rev_x"},
        "decision_ref": {"id": "dec_x"},
    }
    emitted = reducers.derive_ownership(state, acceptance)
    assert [(t["subject_registration_ref"]["id"], t["to_mode"]) for t in emitted] == [
        ("obj_root_reg", "closed_reference")
    ]
    reader = (REPO_ROOT / "research_system" / "legacy" / "reader.py").read_text(encoding="utf-8")
    assert "the registered path is not a regular file" in reader


# --- Claim 6: "later" for family adoptions with disjoint family sets ------------------------------------------------


def _observation(record_id: str, families: list[str], blob: str) -> dict[str, Any]:
    return _hashed(
        {
            "schema_id": "ars://legacy/legacy-observation",
            "record_id": record_id,
            "record_revision": 1,
            "registration_ref": {"id": "obj_reg", "record_revision": 1, "content_hash": "4" * 64},
            "selector": {
                "selector_kind": "json_family_set",
                "membership_ref": {"id": "obj_table", "record_revision": 1, "content_hash": "5" * 64},
                "family_names": families,
            },
            "source_identity": {"identity_kind": "git_tracked", "repository_path": "results/x.json", "git_blob": blob},
        }
    )


def _note_cause_one(state: dict[str, Any], adopted_observation: str, adopted: set[str]) -> bool:
    """§7 cause 1, as the note writes it for a family adoption."""
    history = state["observations_by_registration"]["obj_reg"]
    later = history[history.index(adopted_observation) + 1 :]
    return any(set(state["records"]["legacy_observation"][o]["selector"]["family_names"]) & adopted for o in later)


def _observe(monkeypatch: pytest.MonkeyPatch, state: dict[str, Any], record: dict[str, Any]) -> None:
    monkeypatch.setattr(reducers, "_check_observation", lambda *args: "obj_reg")
    reducers.reduce_record(state, "LR-015", [{"payload": record}], {})


def test_claim6_ordering_holds_a_later_observation_naming_the_family_is_after(monkeypatch: pytest.MonkeyPatch) -> None:
    state = reducers.new_legacy_state()
    _observe(monkeypatch, state, _observation("obj_o1", ["a", "b"], "a" * 40))
    _observe(monkeypatch, state, _observation("obj_o2", ["a"], "a" * 40))
    assert state["observations_by_registration"]["obj_reg"] == ["obj_o1", "obj_o2"]
    assert _note_cause_one(state, "obj_o1", {"a"}) is True
    assert _note_cause_one(state, "obj_o2", {"a"}) is False


def test_defect_claim6_stale_observation_leaves_family_adoption_active_under_note_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The blob changes, seen by an observation of a disjoint family set: WP9.3 projects O1 stale; §7 does not suspend."""
    state = reducers.new_legacy_state()
    _observe(monkeypatch, state, _observation("obj_o1", ["a"], "a" * 40))
    _observe(monkeypatch, state, _observation("obj_o2", ["b"], "b" * 40))
    assert "obj_o1" in state["stale_observations"]
    assert _note_cause_one(state, "obj_o1", {"a"}) is False


# --- Claim 7: the path-literal extractor on the real P01 drafts -----------------------------------------------------


def _note_rule(data: bytes, candidates: set[str]) -> set[str]:
    text = data.replace(b"\\", b"/").decode("utf-8", "replace")
    return {path for path in candidates if path in text}


def _results() -> set[str]:
    return set(_tree_paths("results/"))


def test_defect_claim7_basename_citations_in_p01a_drafts_are_missed() -> None:
    results = _results()
    drafts = [p for p in _tree_paths("papers/P01-A-JRSSA/drafts/")]
    found = set().union(*(_note_rule(_blob(p), results) for p in drafts))
    text = "".join(_blob(p).decode("utf-8", "replace") for p in drafts)
    by_basename: dict[str, list[str]] = {}
    for name in sorted(set(re.findall(r"[A-Za-z0-9_.-]+\.json", text))):
        matches = sorted(p for p in results if p.rsplit("/", 1)[-1] == name)
        if matches and not set(matches) & found:
            by_basename[name] = matches
    unique = {name: paths[0] for name, paths in by_basename.items() if len(paths) == 1}
    assert set(unique) >= {
        "03_multi_threshold.json",
        "ari_om_gmm_normalised_2026-06-24.json",
        "bhps_headline_frozen_2026-05-28.json",
        "escape_wilson_ci_2026-05-16.json",
        "stability_se_stored_2026-06-22.json",
        "sub_regime_thresh_sweep_2026-06-07.json",
    }
    assert len(by_basename["05_analysis.json"]) == 3


def test_defect_claim7_json_escaped_windows_paths_are_not_read_as_paths() -> None:
    path = "papers/P01-A-JRSSA/drafts/sections/table1_effects_2026-05-22.json"
    data = _blob(path)
    cited: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and "\\results\\" in node:
            cited.add("results/" + node.replace("\\", "/").split("/results/", 1)[1])

    walk(json.loads(data))
    assert len(cited) == 7 and cited <= _results()
    assert _note_rule(data, cited) == set()


def test_claim7_whole_root_scan_adds_files_cited_only_outside_the_drafts() -> None:
    results = _results()
    for root, extra_at_least in (("papers/P01-A-JRSSA/", 19), ("papers/P01-B-JRSSB/", 4)):
        files = _tree_paths(root)
        drafts = set().union(*(_note_rule(_blob(p), results) for p in files if "/drafts/" in p))
        whole = set().union(*(_note_rule(_blob(p), results) for p in files))
        assert len(whole - drafts) >= extra_at_least


# --- §5.1: the WP9_3_ROWS gate sites --------------------------------------------------------------------------------


def test_defect_note_counts_eight_row_gate_sites_the_reducers_have_ten() -> None:
    source = (REPO_ROOT / "research_system" / "legacy" / "replay" / "reducers.py").read_text(encoding="utf-8")
    lines = [n for n, line in enumerate(source.splitlines(), 1) if "row_id in WP9_3_ROWS" in line]
    assert lines == [703, 719, 737, 847, 908, 991, 1025, 1138, 1179, 1387]


# --- §11.3: the citation status names neither the inventory, the mapping nor the transition ------------------------


def test_defect_citation_status_carries_no_ref_to_inventory_mapping_or_transition() -> None:
    schema = json.loads((W9_SCHEMAS / "legacy-paper-citation-status.schema.json").read_text(encoding="utf-8"))
    refs = {name for name in schema["properties"] if name.endswith("_ref")}
    assert refs == {"root_ref", "supersedes_status_ref"}
    ownership = json.loads((W9_SCHEMAS / "legacy-ownership-transitioned.schema.json").read_text(encoding="utf-8"))
    assert "citation_status_ref" not in ownership["properties"]
    discharge = json.loads((W9_SCHEMAS / "legacy-discharge-relation.schema.json").read_text(encoding="utf-8"))
    assert not [name for name in discharge["properties"] if "producer" in name]


def test_replay_context_carries_no_generic_artefact_state() -> None:
    source = inspect.getsource(sys.modules["research_system.legacy.replay.driver"].replay_legacy)
    keys = set(re.findall(r'"([a-z0-9_]+)":', source.split("context = {", 1)[1].split("}", 1)[0]))
    assert keys == {"w11_genesis_seen", "accepted_revisions", "pinned_signatures", "accepted_cl_export", "foreign_ids"}


def test_annex_lr029_fixture_s017_is_unconditional() -> None:
    annex = (REPO_ROOT / "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml").read_text(
        encoding="utf-8"
    )
    row = annex.split("- owner_row_id: LR-029", 1)[1].split("- owner_row_id: LR-030", 1)[0]
    assert re.search(r"fixture_id: S-017\n\s+when: null", row)
