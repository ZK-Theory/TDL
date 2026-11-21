# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §§10–15, §19 O/K/I/N; P-086, P-087)
# Purpose: submit-level scratch-store tests for WP9.4-2 (full path LR-035..055, CLI cited-families, O/K5/G4, W9-T6/T17, Rulings 3 & 4).
"""WP9.4-2 runtime and CLI tests against consolidated scratch stores under ``tmp_path``."""

from __future__ import annotations

import functools
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import research_system.cli as cli
import research_system.legacy.replay.driver as legacy_driver
import research_system.legacy.runtime as legacy_runtime
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, IntegrityError
from research_system.ids import new_id
from research_system.legacy import citations, evidence as w9_evidence, preparers
from research_system.legacy.records import (
    adoption_eligibility_decision_id,
    adoption_review_id,
    citation_status_record_id,
    pre_assigned_ref,
)
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.replay.reducers import iso_z
from research_system.legacy.runtime import GATE6_REASON_CODE
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import (
    GATE6,
    SUBJECT_MISMATCH,
    _store,
    _tree_bytes,
)
from tests.research_system.integration.w9_runtime_harness import OWNER, W9Store, git, w9_store

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# --- Consolidated store setup and submission helpers ----------------------------------------------------------------


def _snapshot(
    store: W9Store,
) -> tuple[tuple[dict[str, Any], ...], dict[str, bytes | None], dict[str, bytes | None]]:
    return (
        store.events(),
        _tree_bytes(store.runtime.control_root),
        _tree_bytes(store.harness.ledger.control_root),
    )


def _state(store: W9Store, *, routed_rows: frozenset[str] = flows.TEST_FULL_ROUTES) -> dict[str, Any]:
    return replay_legacy(
        store.events(),
        schemas=store.harness.schemas,
        routed_rows=routed_rows,
        pinned_signatures=(store.pin,),
    )


def _enable_test_full_routes(store: W9Store, monkeypatch: pytest.MonkeyPatch) -> None:
    patched = functools.partial(replay_legacy, routed_rows=flows.TEST_FULL_ROUTES)
    monkeypatch.setattr(legacy_driver, "replay_legacy", patched)
    monkeypatch.setattr(legacy_runtime, "replay_legacy", patched)
    store.runtime.routed_rows = flows.TEST_FULL_ROUTES


def _init_repo_sources(
    store: W9Store,
    files: dict[str, bytes],
    *,
    manifest_paths: tuple[str, ...] = (),
    open_items: list[dict[str, Any]] | None = None,
    disambiguation_entries: list[dict[str, Any]] | None = None,
) -> str:
    """Turn off CRLF translation on scratch repo, commit files/evidence, rebind, and return open-items blob."""
    git(store.repo, "config", "core.autocrlf", "false")
    manifest_file = store.repo / w9_evidence.REGISTRATION_MANIFEST
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    for rel, raw in files.items():
        dest = store.repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    existing = {entry["normalized_path"] for entry in manifest["registrations"]}
    for rel in manifest_paths:
        if rel not in existing:
            manifest["registrations"].append(
                {"root_kind": "repository_root", "root_id": "repository", "normalized_path": rel}
            )
            existing.add(rel)
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    git(store.repo, "add", w9_evidence.REGISTRATION_MANIFEST)
    for rel in files:
        git(store.repo, "add", "-f", rel)
    if open_items is not None:
        oi_path = store.repo / w9_evidence.LEGACY_OPEN_ITEMS
        oi_path.parent.mkdir(parents=True, exist_ok=True)
        oi_path.write_text(
            json.dumps({"format": w9_evidence.LEGACY_OPEN_ITEMS_FORMAT, "items": open_items}),
            encoding="utf-8",
        )
        git(store.repo, "add", "-f", w9_evidence.LEGACY_OPEN_ITEMS)
    if disambiguation_entries is not None:
        cd_path = store.repo / w9_evidence.CITATION_DISAMBIGUATION
        cd_path.parent.mkdir(parents=True, exist_ok=True)
        cd_path.write_text(
            json.dumps({"format": w9_evidence.CITATION_DISAMBIGUATION_FORMAT, "entries": disambiguation_entries}),
            encoding="utf-8",
        )
        git(store.repo, "add", "-f", w9_evidence.CITATION_DISAMBIGUATION)
    git(store.repo, "commit", "-q", "-m", "update wp9.4-2 scratch sources")
    store.rebind()
    if open_items is not None:
        return git(store.repo, "rev-parse", f"{store.head}:{w9_evidence.LEGACY_OPEN_ITEMS}")
    return ""


def _seed_pilot_passed(store: W9Store) -> str:
    """Append passed LR-021 -> LR-022 directly on test-route ledgers (unrouted until WP9.7 on prod stores)."""
    did = new_id("decision")
    sub = new_id("scope_definition")
    cmd_binding = store.harness.schemas.resolve_identity("ars://core/command", "1.0.0")
    when_prop = iso_z(store.clock())
    proposal = {
        "new_decision_id": did,
        "question": "Did the integration pilot pass?",
        "recommendation": "passed",
        "options": ["passed", "missed"],
        "decision_revision": 1,
        "decision_kind": "result_interpretation",
        "governing_evidence_refs": ["W9:LR-021", f"w9-subject:{sub}", f"w9-subject-sha256:{'0' * 64}"],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": iso_z(store.clock().replace(year=store.clock().year + 1)),
        "review_date": when_prop,
        "consequences": ["integration pilot outcome passed"],
    }
    cmd_1 = new_id("command")
    grant_1 = store.grant("ProposeW9AuthorityDecision", "decision", did, store.actors.analyst)
    store.harness.ledger.append(
        [
            {
                "event_type": "DecisionProposed",
                "schema_id": "ars://core/event/DecisionProposed",
                "schema_version": "1.0.0",
                "stream_id": did,
                "command_id": cmd_1,
                "command_type": "ProposeW9AuthorityDecision",
                "command_schema_id": cmd_binding.schema_id,
                "command_schema_version": cmd_binding.schema_version,
                "command_schema_sha256": cmd_binding.raw_bytes_sha256,
                "idempotency_key": f"wp9.4-2:seed:{did}:prop",
                "command_payload_hash": sha256_hex(canonical_bytes(proposal)),
                "correlation_id": sha256_hex(canonical_bytes(proposal)),
                "causation_id": None,
                "actor_id": store.actors.analyst,
                "authority_grant_id": grant_1,
                "occurred_at": when_prop,
                "payload": proposal,
            }
        ]
    )
    store.clock.advance(minutes=1)
    when_res = iso_z(store.clock())
    grant_2 = store.grant("ResolveW9AuthorityDecision", "decision", did, OWNER)
    resolved = {
        "decision_id": did,
        "selected_option": "passed",
        "effective_scope": f"w9-record:{sub}",
        "decision_revision": 1,
        "deciding_actor_id": OWNER,
        "decision_authority_grant_id": grant_2,
        "governing_evidence_refs": ["W9:LR-022", f"w9-subject:{sub}", f"w9-subject-sha256:{'0' * 64}"],
        "considered_review_ids": [],
        "effective_at": when_res,
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    cmd_2 = new_id("command")
    store.harness.ledger.append(
        [
            {
                "event_type": "DecisionResolved",
                "schema_id": "ars://core/event/DecisionResolved",
                "schema_version": "1.0.0",
                "stream_id": did,
                "command_id": cmd_2,
                "command_type": "ResolveW9AuthorityDecision",
                "command_schema_id": cmd_binding.schema_id,
                "command_schema_version": cmd_binding.schema_version,
                "command_schema_sha256": cmd_binding.raw_bytes_sha256,
                "idempotency_key": f"wp9.4-2:seed:{did}:res",
                "command_payload_hash": sha256_hex(canonical_bytes(resolved)),
                "correlation_id": sha256_hex(canonical_bytes(resolved)),
                "causation_id": None,
                "actor_id": OWNER,
                "authority_grant_id": grant_2,
                "occurred_at": when_res,
                "payload": resolved,
            }
        ]
    )
    store.clock.advance(minutes=1)
    return did


def _register_root(
    store: W9Store, path: str = "papers/P01-A-JRSSA/", *, submit_resolve: bool = True
) -> tuple[dict[str, Any], dict[str, Any]]:
    physical = preparers.handle_bound_directory_identity(store.repo, path)
    rec_id = new_id("scope_definition")
    payload = {
        "schema_id": "ars://legacy/legacy-path-registration",
        "schema_version": "1.0.0",
        "record_id": rec_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "root_kind": "repository_root",
        "root_id": "repository",
        "normalized_path": path,
        "physical_identity": physical,
        "source_identity_kind": "git_tracked",
        "role": "legacy_manuscript_root",
        "ownership_mode": "legacy_owned",
        "writer_classes": ["owner_ruling"],
        "prohibited_consumers": [],
        "registration_decision_ref": pre_assigned_ref("decision", new_id("decision"), rec_id),
    }
    assert store.submit("ProposeLegacyRecord", store.actors.analyst, rec_id, 0, payload).status == "accepted"
    if not submit_resolve:
        return payload, payload
    dec_id = payload["registration_decision_ref"]["id"]
    decide = {
        "subject_record_id": rec_id,
        "question": "Register manuscript root?",
        "recommendation": "accept",
        "consequences": ["root registered"],
    }
    assert store.submit("ProposeW9AuthorityDecision", store.actors.analyst, dec_id, 0, decide).status == "accepted"
    resolve = {"decision_id": dec_id, "selected_option": "accept"}
    assert store.submit("ResolveW9AuthorityDecision", OWNER, dec_id, 1, resolve).status == "accepted"
    return _state(store)["records"]["legacy_path_registration"][rec_id], payload


def _observe_member(store: W9Store, reg_root: dict[str, Any], member_path: str) -> dict[str, Any]:
    payload = {**store.observation_payload(reg_root), "member_path": member_path}
    receipt, obs_id = store.observe(payload)
    assert receipt.status == "accepted", receipt
    return _state(store)["records"]["legacy_observation"][obs_id]


def _adopt_claim(
    store: W9Store,
    observation: dict[str, Any],
    *,
    subject: dict[str, Any],
    paper_key: str = "P01-A",
) -> dict[str, Any]:
    adp_id = new_id("scope_definition")
    payload = {
        "schema_id": "ars://legacy/legacy-adoption-decision",
        "schema_version": "1.0.0",
        "record_id": adp_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "observation_ref": flows.record_ref(observation),
        "subject": subject,
        "intended_use": {"description": f"w9-use:manuscript-claims/{paper_key}", "successor_ref": None},
        "w5_consequence": "admissible_for_named_use",
        "qualifiers_to_discharge": [],
        "decision_ref": pre_assigned_ref("decision", new_id("decision"), adp_id),
    }
    assert store.submit("ProposeLegacyRecord", store.actors.analyst, adp_id, 0, payload).status == "accepted"
    proposed = _state(store)["proposals"][adp_id]["record"]
    elig_id = adoption_eligibility_decision_id(adp_id, proposed["created_at"])
    assert (
        store.submit(
            "ProposeW9AuthorityDecision",
            store.actors.analyst,
            elig_id,
            0,
            {
                "subject_record_id": adp_id,
                "question": "Is reviewer session eligible?",
                "recommendation": "accept",
                "consequences": ["eligible"],
                "eligibility": dict(flows.ELIGIBILITY),
            },
        ).status
        == "accepted"
    )
    assert (
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, elig_id, 1, {"decision_id": elig_id, "selected_option": "accept"}
        ).status
        == "accepted"
    )
    rev_id = adoption_review_id(adp_id, proposed["created_at"])
    fixtures = ("F-019", "S-017")
    assert (
        store.submit(
            "RequestW9AuthorityReview",
            store.actors.analyst,
            rev_id,
            0,
            {
                "subject_record_id": adp_id,
                "reviewer_actor_id": store.actors.reviewer,
                "review_questions": ["Is adoption sound?", f"w9-applicable-fixtures:{','.join(fixtures)}"],
                "analyst_session": "session-analyst",
                "eligible_session": flows.ELIGIBILITY["session"],
            },
        ).status
        == "accepted"
    )
    assert (
        store.submit(
            "RecordW9AuthorityReview",
            store.actors.reviewer,
            rev_id,
            1,
            {
                "review_id": rev_id,
                "verdict": "approve",
                "findings": [],
                "limitations": [],
                "reviewer_session": flows.ELIGIBILITY["session"],
                "reviewer_model_metadata": f"{flows.ELIGIBILITY['family']}@{flows.ELIGIBILITY['version']}",
                "context_manifest_sha256": "9" * 64,
            },
        ).status
        == "accepted"
    )
    dec_id = payload["decision_ref"]["id"]
    assert (
        store.submit(
            "ProposeW9AuthorityDecision",
            store.actors.analyst,
            dec_id,
            0,
            {
                "subject_record_id": adp_id,
                "question": "Adopt?",
                "recommendation": "accept",
                "consequences": ["adopted"],
                "fixture_refs": [f"w9-fixture:{fid}:{new_id('review')}" for fid in fixtures],
            },
        ).status
        == "accepted"
    )
    assert (
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        ).status
        == "accepted"
    )
    return _state(store)["records"]["legacy_adoption_decision"][adp_id]


def _create_root(store: W9Store, *, paper_key: str = "P01-A", root_path: str = "papers/P01-A-JRSSA/") -> dict[str, Any]:
    root_id = new_id("scope_definition")
    payload = {
        "schema_id": "ars://legacy/legacy-paper-root",
        "schema_version": "1.0.0",
        "record_id": root_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "paper_key": paper_key,
        "manuscript_root_path": root_path,
        "qualifiers": [],
        "owner_actor_id": store.actors.analyst,
        "recovery": None,
    }
    receipt = store.submit("CreateLegacyPaperRoot", store.actors.analyst, root_id, 0, payload)
    assert receipt.status == "accepted", receipt
    return _state(store)["records"]["legacy_paper_root"][root_id]


def _submit_inventory(
    store: W9Store,
    reg_root: dict[str, Any],
    obs_by_path: list[tuple[str, dict[str, Any]]],
    *,
    stop_after: str | None = None,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    inv_id = new_id("scope_definition")
    rows = [
        {
            "row_ordinal": idx,
            "repository_path": path,
            "git_blob": obs["source_identity"]["git_blob"],
            "observation_ref": flows.record_ref(obs),
        }
        for idx, (path, obs) in enumerate(obs_by_path, start=1)
    ]
    payload = {
        "schema_id": "ars://legacy/legacy-source-inventory",
        "schema_version": "1.0.0",
        "record_id": inv_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "root_registration_ref": flows.record_ref(reg_root),
        "segmentation_contract": "w9-segmentation/1.0.0",
        "rows": rows,
        "observer_actor_id": store.actors.observer,
        "reviewer_ref": pre_assigned_ref("review", new_id("review"), inv_id),
        "decision_ref": pre_assigned_ref("decision", new_id("decision"), inv_id),
    }
    steps: list[tuple[dict[str, Any], Any]] = []

    def send(cmd: str, actor: str, target: str, ver: int, body: dict[str, Any]) -> Any:
        env = store.envelope(cmd, actor, target, ver, body)
        rec = store.runtime.submit(env)
        assert rec.status == "accepted", rec
        store.log.append((env, rec))
        steps.append((env, rec))
        return rec

    send("ProposeLegacyRecord", store.actors.observer, inv_id, 0, payload)
    proposed = _state(store)["proposals"][inv_id]["record"]
    if stop_after == "LR-040":
        return proposed, steps
    rev_id = payload["reviewer_ref"]["id"]
    send(
        "RequestW9AuthorityReview",
        store.actors.analyst,
        rev_id,
        0,
        {
            "subject_record_id": inv_id,
            "reviewer_actor_id": store.actors.reviewer,
            "review_questions": ["Is root inventory complete?", "w9-applicable-fixtures:F-018,F-023,F-037"],
            "analyst_session": "session-analyst",
        },
    )
    send(
        "RecordW9AuthorityReview",
        store.actors.reviewer,
        rev_id,
        1,
        {
            "review_id": rev_id,
            "verdict": "approve",
            "findings": [],
            "limitations": [],
            "reviewer_session": "session-reviewer",
            "reviewer_model_metadata": "w9-test-model",
            "context_manifest_sha256": "9" * 64,
        },
    )
    dec_id = payload["decision_ref"]["id"]
    send(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        dec_id,
        0,
        {
            "subject_record_id": inv_id,
            "question": "Record root source inventory?",
            "recommendation": "accept",
            "consequences": ["inventory recorded"],
            "fixture_refs": [f"w9-fixture:{fid}:{new_id('review')}" for fid in ("F-018", "F-023", "F-037")],
        },
    )
    if stop_after == "LR-043":
        return proposed, steps
    send("ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"})
    return _state(store)["records"]["legacy_source_inventory"][inv_id], steps


def _submit_mapping(
    store: W9Store, inventory: dict[str, Any], paper_root: dict[str, Any], ordinals: list[int]
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    map_id = new_id("scope_definition")
    payload = {
        "schema_id": "ars://legacy/legacy-transition-mapping",
        "schema_version": "1.0.0",
        "record_id": map_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "source_inventory_ref": flows.record_ref(inventory),
        "target_paper_root_ref": flows.record_ref(paper_root),
        "mapped_row_ordinals": ordinals,
        "analyst_actor_id": store.actors.analyst,
        "reviewer_ref": pre_assigned_ref("review", new_id("review"), map_id),
        "decision_ref": pre_assigned_ref("decision", new_id("decision"), map_id),
    }
    steps: list[tuple[dict[str, Any], Any]] = []

    def send(cmd: str, actor: str, target: str, ver: int, body: dict[str, Any]) -> Any:
        env = store.envelope(cmd, actor, target, ver, body)
        rec = store.runtime.submit(env)
        assert rec.status == "accepted", rec
        store.log.append((env, rec))
        steps.append((env, rec))
        return rec

    send("ProposeLegacyRecord", store.actors.analyst, map_id, 0, payload)
    rev_id = payload["reviewer_ref"]["id"]
    send(
        "RequestW9AuthorityReview",
        store.actors.analyst,
        rev_id,
        0,
        {
            "subject_record_id": map_id,
            "reviewer_actor_id": store.actors.reviewer,
            "review_questions": ["Is mapping complete?", "w9-applicable-fixtures:"],
            "analyst_session": "session-analyst",
        },
    )
    send(
        "RecordW9AuthorityReview",
        store.actors.reviewer,
        rev_id,
        1,
        {
            "review_id": rev_id,
            "verdict": "approve",
            "findings": [],
            "limitations": [],
            "reviewer_session": "session-reviewer",
            "reviewer_model_metadata": "w9-test-model",
            "context_manifest_sha256": "9" * 64,
        },
    )
    dec_id = payload["decision_ref"]["id"]
    send(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        dec_id,
        0,
        {
            "subject_record_id": map_id,
            "question": "Record transition mapping?",
            "recommendation": "accept",
            "consequences": ["mapping recorded"],
        },
    )
    send("ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"})
    return _state(store)["records"]["legacy_transition_mapping"][map_id], steps


def _submit_citation_status(
    store: W9Store,
    paper_root: dict[str, Any],
    families: list[dict[str, Any]],
    reviewer_sha256: str,
    *,
    supersedes_status: dict[str, Any] | None = None,
    reviewer: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    actor = reviewer or store.actors.reproducer
    extracted = citations.extract_citations(
        store.repo,
        store.head,
        preparers._latest_inventory_for_root_path(_state(store), paper_root["manuscript_root_path"]),
        _state(store),
    )
    assert not extracted["blockers"], extracted["blockers"]
    derived_id = citation_status_record_id(
        paper_root["record_id"],
        supersedes_status["record_id"] if supersedes_status else None,
        extracted["cited_family_set_sha256"],
        extracted["extractor_output_sha256"],
        reviewer_sha256,
        paper_root["created_at"],
    )
    payload = {
        "schema_id": "ars://legacy/legacy-paper-citation-status",
        "schema_version": "1.0.0",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "root_ref": flows.record_ref(paper_root),
        "derivation": {
            "reviewer_derivation_sha256": reviewer_sha256,
            "reviewer_actor_id": actor,
        },
        "families": families,
        "supersedes_status_ref": flows.record_ref(supersedes_status) if supersedes_status else None,
    }
    env = store.envelope("RecordPaperCitationStatus", actor, derived_id, 0, payload)
    receipt = store.runtime.submit(env)
    assert receipt.status == "accepted", receipt
    store.log.append((env, receipt))
    return _state(store)["records"]["legacy_paper_citation_status"][derived_id], env


def _ownership_propose_to_decision(
    store: W9Store,
    reg_root: dict[str, Any],
    *,
    from_mode: str,
    to_mode: str,
    mapping: dict[str, Any] | None,
    paper_root: dict[str, Any] | None,
    open_items_blob: str | None = None,
    stop_after: str | None = None,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    rec_id = new_id("scope_definition")
    payload = {
        "schema_id": "ars://legacy/legacy-ownership-transitioned",
        "schema_version": "1.0.0",
        "record_id": rec_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "mapping_ref": flows.record_ref(mapping) if mapping else None,
        "subject_registration_ref": flows.record_ref(reg_root),
        "paper_root_ref": flows.record_ref(paper_root) if paper_root else None,
        "from_mode": from_mode,
        "to_mode": to_mode,
        "reviewer_ref": pre_assigned_ref("review", new_id("review"), rec_id),
        "decision_ref": pre_assigned_ref("decision", new_id("decision"), rec_id),
    }
    steps: list[tuple[dict[str, Any], Any]] = []

    def send(cmd: str, actor: str, target: str, ver: int, body: dict[str, Any]) -> Any:
        env = store.envelope(cmd, actor, target, ver, body)
        rec = store.runtime.submit(env)
        assert rec.status == "accepted", rec
        store.log.append((env, rec))
        steps.append((env, rec))
        return rec

    send("ProposeLegacyRecord", store.actors.analyst, rec_id, 0, payload)
    proposed = _state(store)["proposals"][rec_id]["record"]
    rev_id = payload["reviewer_ref"]["id"]
    fixtures = ("F-006", "F-019", "F-023", "F-037") if to_mode == "successor_owned" else ("F-006", "F-019", "F-037")
    send(
        "RequestW9AuthorityReview",
        store.actors.analyst,
        rev_id,
        0,
        {
            "subject_record_id": rec_id,
            "reviewer_actor_id": store.actors.reviewer,
            "review_questions": [
                "Is ownership transition admissible?",
                f"w9-applicable-fixtures:{','.join(fixtures)}",
            ],
            "analyst_session": "session-analyst",
        },
    )
    send(
        "RecordW9AuthorityReview",
        store.actors.reviewer,
        rev_id,
        1,
        {
            "review_id": rev_id,
            "verdict": "approve",
            "findings": [],
            "limitations": [],
            "reviewer_session": "session-reviewer",
            "reviewer_model_metadata": "w9-test-model",
            "context_manifest_sha256": "9" * 64,
        },
    )
    if stop_after == "LR-052":
        return proposed, steps
    dec_id = payload["decision_ref"]["id"]
    dec_body: dict[str, Any] = {
        "subject_record_id": rec_id,
        "question": "Transition ownership?",
        "recommendation": "accept",
        "consequences": ["ownership transitioned"],
        "fixture_refs": [f"w9-fixture:{fid}:{new_id('review')}" for fid in fixtures],
    }
    if open_items_blob is not None:
        dec_body["open_items_blob"] = open_items_blob
    send("ProposeW9AuthorityDecision", store.actors.analyst, dec_id, 0, dec_body)
    if stop_after == "LR-053":
        return proposed, steps
    send("ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"})
    return _state(store)["records"]["legacy_ownership_transitioned"][rec_id], steps


# --- Store A: Positive full path + CLI cited-families + W9-C11 + Gate 6 ----------------------------------------------


def test_store_a_full_path_cli_idempotency_and_gate6(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = w9_store(tmp_path / "store-a", monkeypatch)
    _enable_test_full_routes(store, monkeypatch)

    draft_bytes = b"Headline in \\texttt{results/x.json} and disambiguated other/x.json.\n"
    oi_blob = _init_repo_sources(
        store,
        {
            "papers/P01-A-JRSSA/drafts/main.tex": draft_bytes,
            "papers/P01-A-JRSSA/drafts/.gitkeep": b"",
            "papers/P01-A-JRSSA/figures/.gitkeep": b"",
        },
        manifest_paths=("papers/P01-A-JRSSA/",),
        open_items=[],
        disambiguation_entries=[
            {
                "citing_path": "papers/P01-A-JRSSA/drafts/main.tex",
                "token": "other/x.json",
                "resolution": ["results/x.json"],
            }
        ],
    )

    reg_root, _ = _register_root(store, "papers/P01-A-JRSSA/")
    reg_x = store.register("results/x.json")

    # Membership covering all JSON pointers of results/x.json under one family so extract_citations has 0 blockers.
    single_family = [
        {"name": "headline", "definition_source": "w9 test", "pointers": ["", "/headline", "/other", "/other/[*]"]}
    ]
    tbl_x = store.membership("results/x.json", families=single_family)
    _, obs_x_id = store.observe(
        store.observation_payload(
            reg_x,
            selector={
                "selector_kind": "json_family_set",
                "membership_ref": flows.record_ref(tbl_x),
                "family_names": ["headline"],
            },
            family="headline",
        )
    )
    obs_main = _observe_member(store, reg_root, "papers/P01-A-JRSSA/drafts/main.tex")
    obs_gk1 = _observe_member(store, reg_root, "papers/P01-A-JRSSA/drafts/.gitkeep")
    obs_gk2 = _observe_member(store, reg_root, "papers/P01-A-JRSSA/figures/.gitkeep")

    obs_x = _state(store)["records"]["legacy_observation"][obs_x_id]

    # K reading 2 & 4: two .gitkeep members with identical Git blob + draft accepted together; root stays legacy_owned.
    acc_payload = store.acceptance_payload(
        [obs_x_id, obs_main["record_id"], obs_gk1["record_id"], obs_gk2["record_id"]]
    )
    assert store.accept(acc_payload).status == "accepted"
    st_acc = _state(store)
    assert reg_root["record_id"] not in st_acc["ownership"]
    assert set(st_acc["ownership"]) == {reg_x["record_id"]}

    adp_x = _adopt_claim(store, obs_x, subject={"subject_kind": "families", "family_names": ["headline"]})

    # Seed passed LR-021/LR-022 and create LR-035 paper root, LR-040..044 inventory, LR-045..049 mapping.
    _seed_pilot_passed(store)
    paper_root = _create_root(store)
    root_env = store.log[-1][0]
    root_rec = store.log[-1][1]

    # 1. LR-040 omitted file refusal + LR-040..044 with W9-T6 window edit inside LR-043->LR-044.
    inv_omit_id = new_id("scope_definition")
    grant_inv_omit = store.grant("ProposeLegacyRecord", "scope_definition", inv_omit_id, store.actors.observer)
    snap_omit = _snapshot(store)
    with pytest.raises(
        IntegrityError, match="W9 source inventory does not match tracked files under the root at git_head"
    ):
        store.runtime.submit(
            store.envelope(
                "ProposeLegacyRecord",
                store.actors.observer,
                inv_omit_id,
                0,
                {
                    "schema_id": "ars://legacy/legacy-source-inventory",
                    "schema_version": "1.0.0",
                    "record_id": inv_omit_id,
                    "record_revision": 1,
                    "supersedes_revision": None,
                    "project_id": store.harness.ledger.project_id,
                    "root_registration_ref": flows.record_ref(reg_root),
                    "segmentation_contract": "w9-segmentation/1.0.0",
                    "rows": [
                        {
                            "row_ordinal": 1,
                            "repository_path": "papers/P01-A-JRSSA/drafts/.gitkeep",
                            "git_blob": obs_gk1["source_identity"]["git_blob"],
                            "observation_ref": flows.record_ref(obs_gk1),
                        },
                        {
                            "row_ordinal": 2,
                            "repository_path": "papers/P01-A-JRSSA/drafts/main.tex",
                            "git_blob": obs_main["source_identity"]["git_blob"],
                            "observation_ref": flows.record_ref(obs_main),
                        },
                    ],
                    "observer_actor_id": store.actors.observer,
                    "reviewer_ref": pre_assigned_ref("review", new_id("review"), inv_omit_id),
                    "decision_ref": pre_assigned_ref("decision", new_id("decision"), inv_omit_id),
                },
                authority_grant_id=grant_inv_omit,
            )
        )
    assert _snapshot(store) == snap_omit

    proposed_inv, inv_steps = _submit_inventory(
        store,
        reg_root,
        [
            ("papers/P01-A-JRSSA/drafts/.gitkeep", obs_gk1),
            ("papers/P01-A-JRSSA/drafts/main.tex", obs_main),
            ("papers/P01-A-JRSSA/figures/.gitkeep", obs_gk2),
        ],
        stop_after="LR-043",
    )
    dec_inv = proposed_inv["decision_ref"]["id"]
    grant_dec_inv = store.grant("ResolveW9AuthorityDecision", "decision", dec_inv, OWNER)
    snap_inv_win = _snapshot(store)
    main_file = store.repo / "papers" / "P01-A-JRSSA" / "drafts" / "main.tex"
    main_file.write_bytes(b"Changed in LR-044 window!\n")
    with pytest.raises(IntegrityError, match="W9 source inventory row cannot be read"):
        store.runtime.submit(
            store.envelope(
                "ResolveW9AuthorityDecision",
                OWNER,
                dec_inv,
                1,
                {"decision_id": dec_inv, "selected_option": "accept"},
                authority_grant_id=grant_dec_inv,
            )
        )
    assert _snapshot(store) == snap_inv_win
    main_file.write_bytes(draft_bytes)
    inv_res_env = store.envelope(
        "ResolveW9AuthorityDecision",
        OWNER,
        dec_inv,
        1,
        {"decision_id": dec_inv, "selected_option": "accept"},
        authority_grant_id=grant_dec_inv,
    )
    inv_res_rec = store.runtime.submit(inv_res_env)
    assert inv_res_rec.status == "accepted", inv_res_rec
    store.log.append((inv_res_env, inv_res_rec))
    inv_steps.append((inv_res_env, inv_res_rec))
    inv = _state(store)["records"]["legacy_source_inventory"][proposed_inv["record_id"]]
    mapping, map_steps = _submit_mapping(store, inv, paper_root, [1, 2, 3])

    # CLI `ars legacy cited-families` (read-only, with and without --reviewer-sha256, plus Gate 6 refusal).
    control_root = store.harness.ledger.control_root
    before_bytes = _tree_bytes(control_root)
    monkeypatch.setattr(
        cli,
        "_legacy_current_binding",
        lambda root: SimpleNamespace(repository_root=store.repo, binding={"git_head": store.head}, control_root=root),
    )
    monkeypatch.setattr(
        cli,
        "_verified_ledger",
        lambda root, **kw: (store.harness.ledger, store.harness.schemas, store.harness.authority_resolver),
    )
    assert (
        cli.main(["legacy", "cited-families", "--root", paper_root["record_id"], "--control-root", str(control_root)])
        == 0
    )
    cli_plain = json.loads(capsys.readouterr().out)
    assert "derived_record_id" not in cli_plain
    ext_hash = cli_plain["extractor_output_sha256"]

    assert (
        cli.main(
            [
                "legacy",
                "cited-families",
                "--root",
                paper_root["record_id"],
                "--reviewer-sha256",
                ext_hash,
                "--control-root",
                str(control_root),
            ]
        )
        == 0
    )
    cli_derived = json.loads(capsys.readouterr().out)
    expected_status_id = citation_status_record_id(
        paper_root["record_id"],
        None,
        cli_derived["cited_family_set_sha256"],
        ext_hash,
        ext_hash,
        paper_root["created_at"],
    )
    assert cli_derived["derived_record_id"] == expected_status_id
    assert _tree_bytes(control_root) == before_bytes

    # Owner point N on LR-039 + record LR-039 citation status, then LR-050..054 (successor_owned), then LR-050..055 (closed_reference).
    families_payload = [
        {
            "observation_ref": flows.record_ref(obs_x),
            "family_name": "headline",
            "status": "adopted",
            "adoption_ref": flows.record_ref(adp_x),
        },
    ]
    grant_status = store.grant(
        "RecordPaperCitationStatus", "scope_definition", expected_status_id, store.actors.reproducer
    )
    snap_n = _snapshot(store)
    base_status_payload = {
        "schema_id": "ars://legacy/legacy-paper-citation-status",
        "schema_version": "1.0.0",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "root_ref": flows.record_ref(paper_root),
        "derivation": {"reviewer_derivation_sha256": ext_hash, "reviewer_actor_id": store.actors.reproducer},
        "families": families_payload,
        "supersedes_status_ref": None,
    }
    with pytest.raises(IntegrityError, match="W9 command payload supplies preparer-set fields: record_id"):
        store.runtime.submit(
            store.envelope(
                "RecordPaperCitationStatus",
                store.actors.reproducer,
                expected_status_id,
                0,
                {**base_status_payload, "record_id": expected_status_id},
                authority_grant_id=grant_status,
            )
        )
    with pytest.raises(IntegrityError, match="W9 command target is not the stream"):
        store.runtime.submit(
            store.envelope(
                "RecordPaperCitationStatus",
                store.actors.reproducer,
                expected_status_id,
                0,
                {
                    **base_status_payload,
                    "derivation": {
                        "reviewer_derivation_sha256": "d" * 64,
                        "reviewer_actor_id": store.actors.reproducer,
                    },
                },
                authority_grant_id=grant_status,
            )
        )
    with pytest.raises(
        IntegrityError, match="W9 citation status families differ from the extractor's cited-family set"
    ):
        store.runtime.submit(
            store.envelope(
                "RecordPaperCitationStatus",
                store.actors.reproducer,
                expected_status_id,
                0,
                {
                    **base_status_payload,
                    "families": [
                        {
                            "observation_ref": flows.record_ref(obs_x),
                            "family_name": "other",
                            "status": "adopted",
                            "adoption_ref": flows.record_ref(adp_x),
                        }
                    ],
                },
                authority_grant_id=grant_status,
            )
        )
    assert _snapshot(store) == snap_n

    status_rec, status_env = _submit_citation_status(store, paper_root, families_payload, ext_hash)
    status_receipt = store.log[-1][1]
    assert status_rec["record_id"] == expected_status_id

    # LR-050..054 (successor_owned): wrong open_items_blob at LR-053 + W9-T6 added/edited file at LR-054.
    prop_succ, succ_steps = _ownership_propose_to_decision(
        store,
        reg_root,
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=mapping,
        paper_root=paper_root,
        open_items_blob=oi_blob,
        stop_after="LR-052",
    )
    dec_succ = prop_succ["decision_ref"]["id"]
    grant_dec_succ = store.grant("ProposeW9AuthorityDecision", "decision", dec_succ, store.actors.analyst)
    snap_succ_dec = _snapshot(store)
    succ_dec_base = {
        "subject_record_id": prop_succ["record_id"],
        "question": "Transition ownership?",
        "recommendation": "accept",
        "consequences": ["ownership transitioned"],
        "fixture_refs": [f"w9-fixture:{fid}:{new_id('review')}" for fid in ("F-006", "F-019", "F-023", "F-037")],
    }
    with pytest.raises(IntegrityError, match="W9 open-item list blob differs from the list at git_head"):
        store.runtime.submit(
            store.envelope(
                "ProposeW9AuthorityDecision",
                store.actors.analyst,
                dec_succ,
                0,
                {**succ_dec_base, "open_items_blob": "0" * 40},
                authority_grant_id=grant_dec_succ,
            )
        )
    assert _snapshot(store) == snap_succ_dec
    succ_dec_env = store.envelope(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        dec_succ,
        0,
        {**succ_dec_base, "open_items_blob": oi_blob},
        authority_grant_id=grant_dec_succ,
    )
    succ_dec_rec = store.runtime.submit(succ_dec_env)
    assert succ_dec_rec.status == "accepted", succ_dec_rec
    store.log.append((succ_dec_env, succ_dec_rec))
    succ_steps.append((succ_dec_env, succ_dec_rec))

    grant_res_succ = store.grant("ResolveW9AuthorityDecision", "decision", dec_succ, OWNER)
    prior_head = store.head
    snap_succ_win = _snapshot(store)
    _init_repo_sources(store, {"papers/P01-A-JRSSA/drafts/late.tex": b"Late file\n"})
    with pytest.raises(
        IntegrityError, match="W9 source inventory does not match tracked files under the root at git_head"
    ):
        store.runtime.submit(
            store.envelope(
                "ResolveW9AuthorityDecision",
                OWNER,
                dec_succ,
                1,
                {"decision_id": dec_succ, "selected_option": "accept"},
                authority_grant_id=grant_res_succ,
            )
        )
    assert _snapshot(store) == snap_succ_win
    git(store.repo, "reset", "--hard", prior_head)
    store.rebind()

    main_file.write_bytes(b"Edited before LR-054!\n")
    with pytest.raises(IntegrityError, match="W9 source inventory row cannot be read"):
        store.runtime.submit(
            store.envelope(
                "ResolveW9AuthorityDecision",
                OWNER,
                dec_succ,
                1,
                {"decision_id": dec_succ, "selected_option": "accept"},
                authority_grant_id=grant_res_succ,
            )
        )
    assert _snapshot(store) == snap_succ_win
    main_file.write_bytes(draft_bytes)

    succ_res_env = store.envelope(
        "ResolveW9AuthorityDecision",
        OWNER,
        dec_succ,
        1,
        {"decision_id": dec_succ, "selected_option": "accept"},
        authority_grant_id=grant_res_succ,
    )
    succ_res_rec = store.runtime.submit(succ_res_env)
    assert succ_res_rec.status == "accepted", succ_res_rec
    store.log.append((succ_res_env, succ_res_rec))
    succ_steps.append((succ_res_env, succ_res_rec))
    assert _state(store)["ownership"][reg_root["record_id"]] == "successor_owned"

    # LR-050..055 (closed_reference): Ruling 3 at LR-053 + Ruling 4 window checks at LR-055.
    prop_close, close_steps = _ownership_propose_to_decision(
        store,
        reg_root,
        from_mode="successor_owned",
        to_mode="closed_reference",
        mapping=None,
        paper_root=None,
        open_items_blob=None,
        stop_after="LR-052",
    )
    dec_close = prop_close["decision_ref"]["id"]
    grant_dec_close = store.grant("ProposeW9AuthorityDecision", "decision", dec_close, store.actors.analyst)
    snap_close_dec = _snapshot(store)
    close_dec_base = {
        "subject_record_id": prop_close["record_id"],
        "question": "Transition ownership?",
        "recommendation": "accept",
        "consequences": ["ownership transitioned"],
        "fixture_refs": [f"w9-fixture:{fid}:{new_id('review')}" for fid in ("F-006", "F-019", "F-037")],
    }
    with pytest.raises(IntegrityError, match="W9 LR-055 does not accept open_items_blob"):
        store.runtime.submit(
            store.envelope(
                "ProposeW9AuthorityDecision",
                store.actors.analyst,
                dec_close,
                0,
                {**close_dec_base, "open_items_blob": oi_blob},
                authority_grant_id=grant_dec_close,
            )
        )
    assert _snapshot(store) == snap_close_dec
    close_dec_env = store.envelope(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        dec_close,
        0,
        close_dec_base,
        authority_grant_id=grant_dec_close,
    )
    close_dec_rec = store.runtime.submit(close_dec_env)
    assert close_dec_rec.status == "accepted", close_dec_rec
    store.log.append((close_dec_env, close_dec_rec))
    close_steps.append((close_dec_env, close_dec_rec))

    grant_res_close = store.grant("ResolveW9AuthorityDecision", "decision", dec_close, OWNER)
    snap_close_win = _snapshot(store)
    main_file.write_bytes(b"Edited inside LR-055 window\n")
    with pytest.raises(IntegrityError, match="W9 source inventory row cannot be read"):
        store.runtime.submit(
            store.envelope(
                "ResolveW9AuthorityDecision",
                OWNER,
                dec_close,
                1,
                {"decision_id": dec_close, "selected_option": "accept"},
                authority_grant_id=grant_res_close,
            )
        )
    assert _snapshot(store) == snap_close_win
    main_file.write_bytes(draft_bytes)

    _init_repo_sources(store, {"papers/P01-A-JRSSA/drafts/late2.tex": b"Late 2\n"})
    with pytest.raises(
        IntegrityError, match="W9 source inventory does not match tracked files under the root at git_head"
    ):
        store.runtime.submit(
            store.envelope(
                "ResolveW9AuthorityDecision",
                OWNER,
                dec_close,
                1,
                {"decision_id": dec_close, "selected_option": "accept"},
                authority_grant_id=grant_res_close,
            )
        )
    assert _snapshot(store) == snap_close_win
    git(store.repo, "reset", "--hard", prior_head)
    store.rebind()

    a_dir = store.repo / "papers" / "P01-A-JRSSA"
    a_backup = store.repo / "papers" / "P01-A-BACKUP"
    a_dir.rename(a_backup)
    try:
        a_dir.write_bytes(b"not-a-dir\n")
        with pytest.raises(IntegrityError, match="W9 registration path cannot be read handle-bound"):
            store.runtime.submit(
                store.envelope(
                    "ResolveW9AuthorityDecision",
                    OWNER,
                    dec_close,
                    1,
                    {"decision_id": dec_close, "selected_option": "accept"},
                    authority_grant_id=grant_res_close,
                )
            )
        assert _snapshot(store) == snap_close_win
        a_dir.unlink()
    finally:
        a_backup.rename(a_dir)

    close_res_env = store.envelope(
        "ResolveW9AuthorityDecision",
        OWNER,
        dec_close,
        1,
        {"decision_id": dec_close, "selected_option": "accept"},
        authority_grant_id=grant_res_close,
    )
    close_res_rec = store.runtime.submit(close_res_env)
    assert close_res_rec.status == "accepted", close_res_rec
    store.log.append((close_res_env, close_res_rec))
    close_steps.append((close_res_env, close_res_rec))
    assert _state(store)["ownership"][reg_root["record_id"]] == "closed_reference"

    # W9-C11 idempotency retries on every new / full-path step return identical receipt & append 0 events.
    snap_done = _snapshot(store)
    retry_pairs = [
        (root_env, root_rec),
        (status_env, status_receipt),
        inv_steps[0],
        inv_steps[-1],
        map_steps[0],
        map_steps[-1],
        succ_steps[0],
        succ_steps[-1],
        close_steps[0],
        close_steps[-1],
    ]
    for env, expected_rec in retry_pairs:
        retried = store.runtime.submit(deepcopy(env))
        if expected_rec is not None:
            assert retried == expected_rec
        else:
            assert retried.status == "accepted"
    assert _snapshot(store) == snap_done

    # Gate 6 CLI refusal before binding on `ars legacy cited-families`.
    g6_dir = tmp_path / "gate6-cli-a"
    g6_dir.mkdir()
    _, g6_harness = _store(g6_dir, store_identity=GATE6)
    monkeypatch.undo()
    monkeypatch.setattr(cli, "_verified_ledger", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("bound Gate 6")))
    g6_root = g6_harness.ledger.control_root
    g6_before = _tree_bytes(g6_root)
    assert (
        cli.main(["legacy", "cited-families", "--root", paper_root["record_id"], "--control-root", str(g6_root)]) == 1
    )
    assert GATE6_REASON_CODE in capsys.readouterr().err
    assert _tree_bytes(g6_root) == g6_before


# --- Store B: Production routes + Owner Point O + K5 + G4 grants -----------------------------------------------------


def test_store_b_production_routes_owner_point_o_k5_and_g4_grants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = w9_store(tmp_path / "store-b", monkeypatch)
    _init_repo_sources(
        store,
        {
            "papers/P01-A-JRSSA/drafts/.gitkeep": b"",
            "papers/P01-A-JRSSA/notes/bad.csv": b"a,b\n1,2\n",
            "papers/P01-A-JRSSA/notes/bad.pkl": b"pickle",
            "papers/P01-B-JRSSB/_project.md": b"# P01-B\n",
        },
        manifest_paths=("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/_project.md", "papers/P01-B-JRSSB/"),
        open_items=[],
    )

    # 1. Production-route refusals: LR-035 and LR-021 refuse on default LEGACY_ROUTED_ROWS.
    snap = _snapshot(store)
    root_id_prod = new_id("scope_definition")
    prod_root_payload = {
        "schema_id": "ars://legacy/legacy-paper-root",
        "schema_version": "1.0.0",
        "record_id": root_id_prod,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "paper_key": "P01-A",
        "manuscript_root_path": "papers/P01-A-JRSSA/",
        "qualifiers": [],
        "owner_actor_id": store.actors.analyst,
        "recovery": None,
    }
    with pytest.raises(
        IntegrityError, match=r"W9 LR-035 requires a passed integration-pilot outcome Decision \(LR-022\)"
    ):
        store.submit("CreateLegacyPaperRoot", store.actors.analyst, root_id_prod, 0, prod_root_payload)
    assert _snapshot(store) == snap

    rec_root_id = new_id("scope_definition")
    rec_root_payload = {
        **prod_root_payload,
        "record_id": rec_root_id,
        "recovery": {
            "predecessor_root_ref": {"id": new_id("scope_definition"), "record_revision": 1, "content_hash": "0" * 64},
            "recovery_decision_ref": {"id": new_id("decision"), "record_revision": 1, "content_hash": "0" * 64},
        },
    }
    with pytest.raises(IntegrityError, match=r"W9 row not routed in this version: LR-038 \(WP9\.6\)"):
        store.submit("CreateLegacyPaperRoot", store.actors.analyst, rec_root_id, 0, rec_root_payload)
    assert _snapshot(store) == snap

    # 2. Owner point O: non-git_tracked refused; R7-i3 decimal strings; R6-i1 subdir link_count change allowed at LR-005.
    bad_root_kind = {
        **store.registration_payload(
            "papers/P01-B-JRSSB/_project.md", role="legacy_manuscript_root", kind="untracked_file"
        ),
        "normalized_path": "papers/P01-A-JRSSA/",
        "physical_identity": preparers.handle_bound_directory_identity(store.repo, "papers/P01-A-JRSSA/"),
    }
    bad_root_kind["registration_decision_ref"] = pre_assigned_ref(
        "decision", new_id("decision"), bad_root_kind["record_id"]
    )
    snap = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 legacy_manuscript_root registration must be git_tracked"):
        store.submit("ProposeLegacyRecord", store.actors.analyst, bad_root_kind["record_id"], 0, bad_root_kind)
    assert _snapshot(store) == snap

    reg_a_prop, reg_a_raw = _register_root(store, "papers/P01-A-JRSSA/", submit_resolve=False)
    assert reg_a_prop["physical_identity"]["volume_serial_number"].isdigit()
    assert reg_a_prop["physical_identity"]["stable_file_id"].isdigit()
    (store.repo / "papers" / "P01-A-JRSSA" / "extra_subdir").mkdir()
    dec_a = reg_a_raw["registration_decision_ref"]["id"]
    assert (
        store.submit(
            "ProposeW9AuthorityDecision",
            store.actors.analyst,
            dec_a,
            0,
            {
                "subject_record_id": reg_a_raw["record_id"],
                "question": "Register?",
                "recommendation": "accept",
                "consequences": ["ok"],
            },
        ).status
        == "accepted"
    )
    assert (
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_a, 1, {"decision_id": dec_a, "selected_option": "accept"}
        ).status
        == "accepted"
    )
    reg_a = _state(store, routed_rows=store.runtime.routed_rows)["records"]["legacy_path_registration"][
        reg_a_raw["record_id"]
    ]

    # Prefix collision at preparer (root recorded -> child refused; child recorded -> root refused).
    snap = _snapshot(store)
    child_under_a = store.registration_payload("papers/P01-A-JRSSA/drafts/.gitkeep", role="legacy_coordination")
    with pytest.raises(
        IntegrityError, match="W9 registration of a path or physical identity already registered or proposed"
    ):
        store.submit("ProposeLegacyRecord", store.actors.analyst, child_under_a["record_id"], 0, child_under_a)
    assert _snapshot(store) == snap

    reg_b_child = store.register("papers/P01-B-JRSSB/_project.md", role="legacy_coordination")
    assert reg_b_child["normalized_path"] == "papers/P01-B-JRSSB/_project.md"
    env_b = preparers.Environment(store.runtime.reader, {}, store.harness.ledger.control_root, None)
    preparers._require_physical_identity(
        env_b,
        {**reg_a, "physical_identity": {**reg_a["physical_identity"], "link_count": 99}},
    )
    with pytest.raises(IntegrityError, match="W9 registration path does not resolve to its declared physical identity"):
        preparers._require_physical_identity(
            env_b,
            {**reg_b_child, "physical_identity": {**reg_b_child["physical_identity"], "link_count": 99}},
        )
    snap = _snapshot(store)
    root_over_b = {
        **store.registration_payload("papers/P01-B-JRSSB/_project.md", role="legacy_coordination"),
        "normalized_path": "papers/P01-B-JRSSB/",
        "role": "legacy_manuscript_root",
        "physical_identity": preparers.handle_bound_directory_identity(store.repo, "papers/P01-B-JRSSB/"),
    }
    root_over_b["registration_decision_ref"] = pre_assigned_ref(
        "decision", new_id("decision"), root_over_b["record_id"]
    )
    with pytest.raises(
        IntegrityError, match="W9 registration of a path or physical identity already registered or proposed"
    ):
        store.submit("ProposeLegacyRecord", store.actors.analyst, root_over_b["record_id"], 0, root_over_b)
    assert _snapshot(store) == snap

    # Regular file & directory junction refused at LR-003 and at LR-005 (using fresh root P01-B after cleanup).
    b_dir = store.repo / "papers" / "P01-B-JRSSB"
    shutil.rmtree(b_dir)
    b_dir.write_bytes(b"regular-file\n")
    snap = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 registration path cannot be read handle-bound"):
        preparers._require_physical_identity(
            preparers.Environment(store.runtime.reader, {}, store.harness.ledger.control_root, None),
            root_over_b,
        )
    b_dir.unlink()
    jtarget = store.repo / "outside-jtarget"
    jtarget.mkdir()
    subprocess.run(["cmd", "/c", "mklink", "/J", str(b_dir), str(jtarget)], check=True, capture_output=True)
    with pytest.raises(IntegrityError, match="W9 registration path cannot be read handle-bound"):
        preparers._require_physical_identity(
            preparers.Environment(store.runtime.reader, {}, store.harness.ledger.control_root, None),
            root_over_b,
        )
    assert _snapshot(store) == snap
    b_dir.rmdir()
    # LR-005 re-read failure when real directory papers/P01-A-JRSSA is swapped with regular file or junction.
    a_dir = store.repo / "papers" / "P01-A-JRSSA"
    a_backup = store.repo / "papers" / "P01-A-BACKUP"
    a_dir.rename(a_backup)
    try:
        a_dir.write_bytes(b"file-not-dir\n")
        with pytest.raises(IntegrityError, match="W9 registration path cannot be read handle-bound"):
            preparers._require_physical_identity(
                preparers.Environment(store.runtime.reader, {}, store.harness.ledger.control_root, None),
                reg_a,
            )
        a_dir.unlink()
        subprocess.run(["cmd", "/c", "mklink", "/J", str(a_dir), str(jtarget)], check=True, capture_output=True)
        with pytest.raises(IntegrityError, match="W9 registration path cannot be read handle-bound"):
            preparers._require_physical_identity(
                preparers.Environment(store.runtime.reader, {}, store.harness.ledger.control_root, None),
                reg_a,
            )
        a_dir.rmdir()
    finally:
        a_backup.rename(a_dir)

    # 3. Owner point K reading 5 & D-9 suffix check at preparer (R6-i2).
    bad_obs_id = new_id("scope_definition")
    grant_obs = store.grant("ObserveLegacyRecord", "scope_definition", bad_obs_id, store.actors.observer)
    snap = _snapshot(store)
    no_mp = store.observation_payload(reg_a)
    for mp_overrides, expected_msg in (
        ({}, "W9 observation of a legacy_manuscript_root requires member_path"),
        (
            {"member_path": "results/x.json"},
            "W9 source cannot be read: member path is not strictly under the registered root",
        ),
        ({"member_path": "papers/P01-A-JRSSA/notes/bad.csv"}, "W9 manuscript root member has a restricted D-9 suffix"),
        ({"member_path": "papers/P01-A-JRSSA/notes/bad.pkl"}, "W9 manuscript root member has a restricted D-9 suffix"),
    ):
        with pytest.raises(IntegrityError, match=expected_msg):
            store.runtime.submit(
                store.envelope(
                    "ObserveLegacyRecord",
                    store.actors.observer,
                    bad_obs_id,
                    0,
                    {**no_mp, **mp_overrides},
                    authority_grant_id=grant_obs,
                )
            )
    with pytest.raises(
        IntegrityError, match="W9 member_path is admitted only for a legacy_manuscript_root registration"
    ):
        store.runtime.submit(
            store.envelope(
                "ObserveLegacyRecord",
                store.actors.observer,
                bad_obs_id,
                0,
                {**store.observation_payload(reg_b_child), "member_path": "papers/P01-B-JRSSB/_project.md"},
                authority_grant_id=grant_obs,
            )
        )
    assert _snapshot(store) == snap

    # 4. Owner point N / G4 grants: wrong subject refused across CreateLegacyPaperRoot and LR-040 proposal.
    _enable_test_full_routes(store, monkeypatch)
    _seed_pilot_passed(store)
    wrong_target = new_id("scope_definition")
    # CreateLegacyPaperRoot with wrong-subject grant refused.
    grant_r = store.grant("CreateLegacyPaperRoot", "scope_definition", wrong_target, store.actors.analyst)
    snap = _snapshot(store)
    env_r = store.envelope(
        "CreateLegacyPaperRoot",
        store.actors.analyst,
        new_id("scope_definition"),
        0,
        {**prod_root_payload, "record_id": new_id("scope_definition")},
        authority_grant_id=grant_r,
    )
    with pytest.raises(ArsError, match=SUBJECT_MISMATCH):
        store.runtime.submit(env_r)
    assert _snapshot(store) == snap

    # Wrong proposal subject grant on LR-040 refused.
    inv_id_bad = new_id("scope_definition")
    grant_inv = store.grant("ProposeLegacyRecord", "scope_definition", wrong_target, store.actors.observer)
    snap = _snapshot(store)
    with pytest.raises(ArsError, match=SUBJECT_MISMATCH):
        store.runtime.submit(
            store.envelope(
                "ProposeLegacyRecord",
                store.actors.observer,
                inv_id_bad,
                0,
                {
                    "schema_id": "ars://legacy/legacy-source-inventory",
                    "schema_version": "1.0.0",
                    "record_id": inv_id_bad,
                    "record_revision": 1,
                    "supersedes_revision": None,
                    "project_id": store.harness.ledger.project_id,
                    "root_registration_ref": flows.record_ref(reg_a),
                    "segmentation_contract": "w9-segmentation/1.0.0",
                    "rows": [
                        {
                            "row_ordinal": 1,
                            "repository_path": "papers/P01-A-JRSSA/drafts/.gitkeep",
                            "git_blob": "a" * 40,
                            "observation_ref": {
                                "id": new_id("scope_definition"),
                                "record_revision": 1,
                                "content_hash": "b" * 64,
                            },
                        }
                    ],
                    "observer_actor_id": store.actors.observer,
                    "reviewer_ref": pre_assigned_ref("review", new_id("review"), inv_id_bad),
                    "decision_ref": pre_assigned_ref("decision", new_id("decision"), inv_id_bad),
                },
                authority_grant_id=grant_inv,
            )
        )
    assert _snapshot(store) == snap


# --- Fast direct-preparer negative tests (P-087 item 7 budget optimization) -------------------------------------------


def test_preparer_negatives_blocker_open_items_and_disambiguation_drift(tmp_path: Path) -> None:
    """Blocker at LR-039, unequal LR-039 hash acceptance, undischarged A001-99 at LR-054, cd_v1->cd_v2 drift."""

    from datetime import UTC, datetime
    from research_system.legacy.reader import LegacyReader, git_blob_id
    from tests.research_system.integration.w9_runtime_harness import Clock

    repo = tmp_path / "prep-neg-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git(repo, "config", "core.autocrlf", "false")

    def commit_files(files: dict[str, bytes], msg: str) -> str:
        for rel, raw in files.items():
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            git(repo, "add", "-f", rel)
        git(repo, "commit", "-q", "-m", msg)
        return git(repo, "rev-parse", "HEAD")

    main_bytes = b"See results/x.json and other/x.json.\n"
    head_1 = commit_files(
        {
            "results/x.json": b'{"headline": 1}\n',
            "papers/P01-A-JRSSA/drafts/main.tex": main_bytes,
            w9_evidence.LEGACY_OPEN_ITEMS: json.dumps(
                {"format": w9_evidence.LEGACY_OPEN_ITEMS_FORMAT, "items": []}
            ).encode(),
            w9_evidence.CITATION_DISAMBIGUATION: json.dumps(
                {"format": w9_evidence.CITATION_DISAMBIGUATION_FORMAT, "entries": []}
            ).encode(),
        },
        "commit-1-empty-cd",
    )
    main_blob = git_blob_id(main_bytes)

    root_reg_id = new_id("scope_definition")
    reg_x_id = new_id("scope_definition")
    tbl_x_id = new_id("scope_definition")
    obs_x_id = new_id("scope_definition")
    acc_id = new_id("scope_definition")
    inv1_id = new_id("scope_definition")
    map1_id = new_id("scope_definition")
    paper_root_id = new_id("scope_definition")
    adp_x_id = new_id("scope_definition")
    status1_id = new_id("scope_definition")
    proj_id = new_id("project")
    reproducer = new_id("actor")
    when_root = "2026-09-01T00:00:00Z"

    inv1 = {
        "record_id": inv1_id,
        "root_registration_ref": {"id": root_reg_id, "record_revision": 1, "content_hash": "a" * 64},
        "rows": [
            {
                "row_ordinal": 1,
                "repository_path": "papers/P01-A-JRSSA/drafts/main.tex",
                "git_blob": main_blob,
                "observation_ref": {"id": "obs_main", "record_revision": 1, "content_hash": "b" * 64},
            }
        ],
    }
    legacy: dict[str, Any] = {
        "records": {
            "legacy_path_registration": {
                root_reg_id: {
                    "record_id": root_reg_id,
                    "role": "legacy_manuscript_root",
                    "normalized_path": "papers/P01-A-JRSSA/",
                    "source_identity_kind": "git_tracked",
                },
                reg_x_id: {
                    "record_id": reg_x_id,
                    "role": "legacy_research_result",
                    "normalized_path": "results/x.json",
                    "source_identity_kind": "git_tracked",
                },
            },
            "legacy_field_family_membership": {tbl_x_id: {"record_id": tbl_x_id, "families": [{"name": "headline"}]}},
            "legacy_observation": {
                obs_x_id: {
                    "record_id": obs_x_id,
                    "selector": {
                        "selector_kind": "json_family_set",
                        "membership_ref": {"id": tbl_x_id},
                        "family_names": ["headline"],
                    },
                }
            },
            "legacy_closed_reference_acceptance": {
                acc_id: {"record_id": acc_id, "items": [{"observation_ref": {"id": obs_x_id}}]}
            },
            "legacy_source_inventory": {inv1_id: inv1},
            "legacy_transition_mapping": {map1_id: {"record_id": map1_id, "source_inventory_ref": {"id": inv1_id}}},
            "legacy_paper_root": {
                paper_root_id: {
                    "record_id": paper_root_id,
                    "paper_key": "P01-A",
                    "manuscript_root_path": "papers/P01-A-JRSSA/",
                    "created_at": when_root,
                }
            },
            "legacy_discharge_relation": {},
            "legacy_paper_citation_status": {},
        },
        "observations_by_registration": {reg_x_id: [obs_x_id]},
        "current_citation_status_by_root": {},
        "supersessions": {},
    }
    fam_x = [
        {
            "observation_ref": {"id": obs_x_id, "record_revision": 1, "content_hash": "d" * 64},
            "family_name": "headline",
            "status": "adopted",
            "adoption_ref": {"id": adp_x_id, "record_revision": 1, "content_hash": "e" * 64},
        }
    ]
    now = datetime(2026, 9, 1, 0, 5, tzinfo=UTC)

    # 1. Blocker entry (ambiguous other/x.json with empty cd) refuses RecordPaperCitationStatus preparer.
    env1 = preparers.Environment(LegacyReader(repository_root=repo, git_head=head_1, clock=Clock()), {}, tmp_path, None)
    status_payload = {
        "schema_id": "ars://legacy/legacy-paper-citation-status",
        "schema_version": "1.0.0",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": proj_id,
        "root_ref": {"id": paper_root_id, "record_revision": 1, "content_hash": "f" * 64},
        "derivation": {"reviewer_derivation_sha256": "c" * 64, "reviewer_actor_id": reproducer},
        "families": fam_x,
        "supersedes_status_ref": None,
    }
    with pytest.raises(
        IntegrityError, match="W9 citation extractor has blocker entries; cannot record citation status"
    ):
        preparers.prepare_citation_status(status_payload, actor=reproducer, now=now, legacy=legacy, environment=env1)

    # 2. Commit cd_v1 + undischarged A001-99; unequal-hash status prepares cleanly; LR-054 refuses undischarged A001-99.
    cd_v1 = [
        {"citing_path": "papers/P01-A-JRSSA/drafts/main.tex", "token": "other/x.json", "resolution": ["results/x.json"]}
    ]
    head_2 = commit_files(
        {
            w9_evidence.CITATION_DISAMBIGUATION: json.dumps(
                {"format": w9_evidence.CITATION_DISAMBIGUATION_FORMAT, "entries": cd_v1}
            ).encode(),
            w9_evidence.LEGACY_OPEN_ITEMS: json.dumps(
                {
                    "format": w9_evidence.LEGACY_OPEN_ITEMS_FORMAT,
                    "items": [
                        {
                            "item_kind": "a001_item",
                            "item_id": "A001-99",
                            "source": "docs/a.md",
                            "feeds_papers": ["P01-A"],
                        }
                    ],
                }
            ).encode(),
        },
        "commit-2-cdv1-and-open-item",
    )
    oi_undischarged_blob = git(repo, "rev-parse", f"{head_2}:{w9_evidence.LEGACY_OPEN_ITEMS}")
    env2 = preparers.Environment(LegacyReader(repository_root=repo, git_head=head_2, clock=Clock()), {}, tmp_path, None)
    prepared_unequal = preparers.prepare_citation_status(
        status_payload, actor=reproducer, now=now, legacy=legacy, environment=env2
    )
    assert prepared_unequal.events[0][0] == "LegacyPaperCitationStatusRecorded"
    recorded_status = prepared_unequal.events[0][2]
    assert recorded_status["derivation"]["extractor_output_sha256"] != "c" * 64

    ext_v1 = citations.extract_citations(repo, head_2, inv1, legacy)
    legacy["records"]["legacy_paper_citation_status"][status1_id] = {
        "record_id": status1_id,
        "derivation": {"extractor_output_sha256": ext_v1["extractor_output_sha256"]},
    }
    legacy["current_citation_status_by_root"][paper_root_id] = status1_id
    trans_rec = {
        "from_mode": "legacy_owned",
        "to_mode": "successor_owned",
        "subject_registration_ref": {"id": root_reg_id},
        "mapping_ref": {"id": map1_id},
        "paper_root_ref": {"id": paper_root_id},
    }
    with pytest.raises(IntegrityError, match="W9 open item a001_item:A001-99 feeding P01-A has no recorded discharge"):
        preparers._check_ownership_transition_env(
            env2, legacy, trans_rec, expected_open_items_blob=oi_undischarged_blob, at_resolution=True
        )
    # Positive control once A001-99 discharge is recorded:
    legacy["records"]["legacy_discharge_relation"][new_id("scope_definition")] = {
        "legacy_item": {"item_kind": "a001_item", "item_id": "A001-99"}
    }
    preparers._check_ownership_transition_env(
        env2, legacy, trans_rec, expected_open_items_blob=oi_undischarged_blob, at_resolution=True
    )

    # 3. Commit cd_v2 (same inv1, changed citation-disambiguation.json) -> stale status1 refused at LR-054.
    cd_v2 = [
        *cd_v1,
        {
            "citing_path": "papers/P01-A-JRSSA/drafts/main.tex",
            "token": "note/unused.json",
            "resolution": "not_a_result",
        },
    ]
    head_3 = commit_files(
        {
            w9_evidence.CITATION_DISAMBIGUATION: json.dumps(
                {"format": w9_evidence.CITATION_DISAMBIGUATION_FORMAT, "entries": cd_v2}
            ).encode()
        },
        "commit-3-cdv2",
    )
    env3 = preparers.Environment(LegacyReader(repository_root=repo, git_head=head_3, clock=Clock()), {}, tmp_path, None)
    with pytest.raises(IntegrityError, match="W9 citation status does not cover the mapping's inventory"):
        preparers._check_ownership_transition_env(
            env3, legacy, trans_rec, expected_open_items_blob=oi_undischarged_blob, at_resolution=True
        )


def test_lr054_refuses_status_derived_from_different_inventory(tmp_path: Path) -> None:
    """§15: a status derived from inv1 is refused by LR-054 preparer when mapping names inv2 (unchanged cd)."""

    from research_system.legacy.reader import LegacyReader, git_blob_id
    from tests.research_system.integration.w9_runtime_harness import Clock

    repo = tmp_path / "diff-inv-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git(repo, "config", "core.autocrlf", "false")
    for rel, raw in {
        "results/x.json": b'{"headline": 1}\n',
        w9_evidence.CITATION_DISAMBIGUATION: json.dumps(
            {"format": w9_evidence.CITATION_DISAMBIGUATION_FORMAT, "entries": []}
        ).encode(),
        "papers/P01-A-JRSSA/drafts/main.tex": b"Cites results/x.json.\n",
    }.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        git(repo, "add", rel)
    git(repo, "commit", "-q", "-m", "inv1")
    blob_main_1 = git_blob_id(b"Cites results/x.json.\n")

    main_2 = b"Cites results/x.json and results/y.npy.\n"
    (repo / "results/y.npy").write_bytes(b"\x93NUMPY\x01\x00")
    (repo / "papers/P01-A-JRSSA/drafts/main.tex").write_bytes(main_2)
    git(repo, "add", "results/y.npy", "papers/P01-A-JRSSA/drafts/main.tex")
    git(repo, "commit", "-q", "-m", "inv2")
    head = git(repo, "rev-parse", "HEAD")
    blob_main_2 = git_blob_id(main_2)

    root_reg_id = new_id("scope_definition")
    reg_x_id = new_id("scope_definition")
    reg_y_id = new_id("scope_definition")
    tbl_x_id = new_id("scope_definition")
    obs_x_id = new_id("scope_definition")
    obs_y_id = new_id("scope_definition")
    acc_id = new_id("scope_definition")
    paper_root_id = new_id("scope_definition")
    inv1_id = new_id("scope_definition")
    inv2_id = new_id("scope_definition")
    map2_id = new_id("scope_definition")
    status1_id = new_id("scope_definition")

    legacy = {
        "records": {
            "legacy_path_registration": {
                root_reg_id: {
                    "record_id": root_reg_id,
                    "role": "legacy_manuscript_root",
                    "normalized_path": "papers/P01-A-JRSSA/",
                },
                reg_x_id: {
                    "record_id": reg_x_id,
                    "role": "legacy_research_result",
                    "normalized_path": "results/x.json",
                },
                reg_y_id: {
                    "record_id": reg_y_id,
                    "role": "legacy_research_result",
                    "normalized_path": "results/y.npy",
                },
            },
            "legacy_field_family_membership": {
                tbl_x_id: {
                    "record_id": tbl_x_id,
                    "families": [{"name": "headline"}],
                }
            },
            "legacy_observation": {
                obs_x_id: {
                    "record_id": obs_x_id,
                    "selector": {
                        "selector_kind": "json_family_set",
                        "membership_ref": {"id": tbl_x_id},
                        "family_names": ["headline"],
                    },
                },
                obs_y_id: {
                    "record_id": obs_y_id,
                    "selector": {"selector_kind": "whole_file"},
                },
            },
            "legacy_closed_reference_acceptance": {
                acc_id: {
                    "record_id": acc_id,
                    "items": [
                        {"observation_ref": {"id": obs_x_id}},
                        {"observation_ref": {"id": obs_y_id}},
                    ],
                }
            },
            "legacy_source_inventory": {
                inv1_id: {
                    "record_id": inv1_id,
                    "root_registration_ref": {"id": root_reg_id},
                    "rows": [
                        {
                            "row_ordinal": 1,
                            "repository_path": "papers/P01-A-JRSSA/drafts/main.tex",
                            "git_blob": blob_main_1,
                            "observation_ref": {"id": "obs_main_1"},
                        }
                    ],
                },
                inv2_id: {
                    "record_id": inv2_id,
                    "root_registration_ref": {"id": root_reg_id},
                    "rows": [
                        {
                            "row_ordinal": 1,
                            "repository_path": "papers/P01-A-JRSSA/drafts/main.tex",
                            "git_blob": blob_main_2,
                            "observation_ref": {"id": "obs_main_2"},
                        }
                    ],
                },
            },
            "legacy_transition_mapping": {
                map2_id: {
                    "record_id": map2_id,
                    "source_inventory_ref": {"id": inv2_id},
                }
            },
            "legacy_paper_root": {
                paper_root_id: {
                    "record_id": paper_root_id,
                    "paper_key": "P01-A",
                    "manuscript_root_path": "papers/P01-A-JRSSA/",
                }
            },
            "legacy_paper_citation_status": {
                status1_id: {
                    "record_id": status1_id,
                    "derivation": {
                        "extractor_output_sha256": citations.extract_citations(
                            repo,
                            head,
                            {
                                "record_id": inv1_id,
                                "root_registration_ref": {"id": root_reg_id},
                                "rows": [
                                    {
                                        "row_ordinal": 1,
                                        "repository_path": "papers/P01-A-JRSSA/drafts/main.tex",
                                        "git_blob": blob_main_1,
                                        "observation_ref": {"id": "obs_main_1"},
                                    }
                                ],
                            },
                            {
                                "records": {
                                    "legacy_path_registration": {
                                        root_reg_id: {
                                            "record_id": root_reg_id,
                                            "role": "legacy_manuscript_root",
                                            "normalized_path": "papers/P01-A-JRSSA/",
                                        },
                                        reg_x_id: {
                                            "record_id": reg_x_id,
                                            "role": "legacy_research_result",
                                            "normalized_path": "results/x.json",
                                        },
                                    },
                                    "legacy_field_family_membership": {
                                        tbl_x_id: {"record_id": tbl_x_id, "families": [{"name": "headline"}]}
                                    },
                                    "legacy_observation": {
                                        obs_x_id: {
                                            "record_id": obs_x_id,
                                            "selector": {
                                                "selector_kind": "json_family_set",
                                                "membership_ref": {"id": tbl_x_id},
                                                "family_names": ["headline"],
                                            },
                                        }
                                    },
                                    "legacy_closed_reference_acceptance": {
                                        acc_id: {"record_id": acc_id, "items": [{"observation_ref": {"id": obs_x_id}}]}
                                    },
                                },
                                "observations_by_registration": {reg_x_id: [obs_x_id]},
                            },
                        )["extractor_output_sha256"]
                    },
                }
            },
        },
        "observations_by_registration": {reg_x_id: [obs_x_id], reg_y_id: [obs_y_id]},
        "current_citation_status_by_root": {paper_root_id: status1_id},
        "supersessions": {},
    }
    env = preparers.Environment(LegacyReader(repository_root=repo, git_head=head, clock=Clock()), {}, tmp_path, None)
    record = {
        "from_mode": "legacy_owned",
        "to_mode": "successor_owned",
        "subject_registration_ref": {"id": root_reg_id},
        "mapping_ref": {"id": map2_id},
        "paper_root_ref": {"id": paper_root_id},
    }
    with pytest.raises(IntegrityError, match="W9 citation status does not cover the mapping's inventory"):
        preparers._check_ownership_transition_env(env, legacy, record, at_resolution=True)
