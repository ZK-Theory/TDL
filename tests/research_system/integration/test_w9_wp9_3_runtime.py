# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1; P-080, P-081)
# Purpose: LR-003 to LR-015 through the real LegacyRuntime.submit on scratch stores: flows, retries and preparer checks.
"""WP9.3-1 runtime tests (WP9.3 note §5 to §8, §17).

Every store is a scratch store under ``tmp_path``; every source is in a scratch Git repository under ``tmp_path``.
A refusal before append is checked with the ledger and the receipt root unchanged, and with the refusing check's own
message.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import research_system.legacy.accepted_w9 as accepted_w9
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.replay.driver import replay_legacy
from research_system.projection.replay import rebuild_projection
from research_system.projection.replay import replay as replay_projection
from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes
from tests.research_system.integration.w9_runtime_harness import OWNER, W9Store, w9_store


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> W9Store:
    return w9_store(tmp_path, monkeypatch)


def _unchanged(store: W9Store) -> tuple[tuple, dict]:
    return store.events(), _tree_bytes(store.runtime.control_root)


def _refused(store: W9Store, message: str, command_type: str, actor: str, target: str, version: int, payload: dict):
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match=message):
        store.submit(command_type, actor, target, version, payload)
    assert _unchanged(store) == before


# --- The whole flow through submit ------------------------------------------------------------------------------------


def test_whole_flow_through_submit_replays_through_every_public_replay(store: W9Store, monkeypatch, tmp_path) -> None:
    registration = store.register("results/x.json")
    table = store.membership()
    tracker = store.register("tracker.md", role="legacy_coordination")
    inventory = store.inventory(tracker)
    whole, whole_id = store.observe(store.observation_payload(registration))
    assert whole.status == "accepted"
    family_set = store.observation_payload(
        registration,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": {"id": table["record_id"], "record_revision": 1, "content_hash": table["content_hash"]},
            "family_names": ["headline"],
        },
        family="headline",
    )
    assert store.observe(family_set)[0].status == "accepted"
    row = inventory["rows"][0]
    item = store.observation_payload(
        tracker,
        selector={
            "selector_kind": "inventory_item",
            "inventory_ref": {
                "id": inventory["record_id"],
                "record_revision": 1,
                "content_hash": inventory["content_hash"],
            },
            "row_ordinal": 1,
            "anchor_text": row["anchor_text"],
            "raw_row_sha256": row["raw_row_sha256"],
        },
        family="item",
    )
    assert store.observe(item)[0].status == "accepted"
    events = store.events()
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (store.pin,))
    replay_projection(events, schema_registry=store.harness.schemas)
    rebuild_projection(events, tmp_path / "out" / "projection.json", store.harness.schemas)
    replay_discovery(events, schemas=store.harness.schemas)
    state = replay_legacy(events, schemas=store.harness.schemas)
    assert len(state["records"]["legacy_observation"]) == 3
    observed = state["records"]["legacy_observation"][whole_id]
    assert observed["importer"]["tool_id"] == "research_system.legacy.reader"
    assert observed["non_inferences"] == ["no authority from file presence (W0 §4)"]
    assert observed["source_identity"]["git_commit"] == store.head
    # W2 events are recorded under their producer bindings' schemas (C2); E: events under ars://core/event.
    by_type = {
        event["event_type"]: event["schema_id"]
        for event in events
        if event["command_type"]
        in {"RequestW9AuthorityReview", "RecordW9AuthorityReview", "ProposeW9AuthorityDecision", "ObserveLegacyRecord"}
    }
    assert by_type == {
        "ReviewRequested": "ars://core/event/ReviewRequested",
        "ReviewVerdictRecorded": "ars://core/event/ReviewVerdictRecorded",
        "DecisionProposed": "ars://core/event/DecisionProposed",
        "LegacyRecordObserved": "ars://core/event",
    }


# --- W9-C11: retries (note §17) ---------------------------------------------------------------------------------------


def test_w9_c11_every_wp9_3_command_retried_returns_its_receipt_and_appends_nothing(store: W9Store) -> None:
    registration = store.register("results/x.json")
    store.membership()
    tracker = store.register("tracker.md", role="legacy_coordination")
    store.inventory(tracker)
    store.observe(store.observation_payload(registration))
    before = store.events()
    assert {envelope["command_type"] for envelope, _ in store.log} == {
        "ProposeLegacyRecord",
        "RequestW9AuthorityReview",
        "RecordW9AuthorityReview",
        "ProposeW9AuthorityDecision",
        "ResolveW9AuthorityDecision",
        "RecordLegacyLightInventory",
        "ObserveLegacyRecord",
    }
    for envelope, receipt in store.log:
        assert store.runtime.submit(deepcopy(envelope)) == receipt
    assert store.events() == before


# --- Rows, roles and preparer-set fields (§2.2, §5.1, §5.5) ------------------------------------------------------------


def test_a_deferred_row_through_a_bound_command_is_refused_before_any_write(store: W9Store) -> None:
    """§2.2: ProposeLegacyRecord is bound, but LR-023 (WP9.4) is not routed; assign_row refuses it before append."""
    record_id = new_id("scope_definition")
    payload = {"schema_id": "ars://legacy/legacy-adoption-decision", "schema_version": "1.0.0", "record_id": record_id}
    _refused(
        store,
        r"W9 row not routed in this version: LR-023 \(WP9.4\)",
        "ProposeLegacyRecord",
        store.actors.analyst,
        record_id,
        0,
        payload,
    )


def test_the_owner_is_refused_on_every_non_resolver_row_and_required_on_a_resolver_row(store: W9Store) -> None:
    payload = store.registration_payload("results/x.json")
    _refused(store, "W9 LR-003 refuses the owner", "ProposeLegacyRecord", OWNER, payload["record_id"], 0, payload)
    assert store.submit("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 0, payload).status == (
        "accepted"
    )
    decision_id = payload["registration_decision_ref"]["id"]
    decide = {"subject_record_id": payload["record_id"], "question": "q", "recommendation": "r", "consequences": []}
    _refused(store, "W9 LR-004 refuses the owner", "ProposeW9AuthorityDecision", OWNER, decision_id, 0, decide)
    store.submit("ProposeW9AuthorityDecision", store.actors.analyst, decision_id, 0, decide)
    resolve = {"decision_id": decision_id, "selected_option": "accept"}
    _refused(
        store,
        "W9 LR-005 is resolved by the owner only",
        "ResolveW9AuthorityDecision",
        store.actors.analyst,
        decision_id,
        1,
        resolve,
    )


@pytest.mark.parametrize("field", ["content_hash", "created_at", "created_by_actor_id"])
def test_n2_a_payload_supplying_a_preparer_set_field_is_refused_before_append(store: W9Store, field: str) -> None:
    payload = store.registration_payload("results/x.json")
    payload[field] = {"content_hash": "0" * 64, "created_at": "2026-09-01T00:00:00Z"}.get(field, store.actors.analyst)
    _refused(
        store,
        f"W9 command payload supplies preparer-set fields: {field}",
        "ProposeLegacyRecord",
        store.actors.analyst,
        payload["record_id"],
        0,
        payload,
    )


def test_the_shadow_step_refuses_a_schema_invalid_payload_a_reducer_alone_admits(store: W9Store) -> None:
    """§6 (review m-6): the shadow run is replay's whole per-transaction step, schema validation included."""
    payload = store.registration_payload("results/x.json")
    del payload["prohibited_consumers"]
    _refused(
        store,
        "W9 event payload does not validate against its record schema",
        "ProposeLegacyRecord",
        store.actors.analyst,
        payload["record_id"],
        0,
        payload,
    )


def test_a_claiming_command_must_expect_stream_version_0(store: W9Store) -> None:
    payload = store.registration_payload("results/x.json")
    receipt = store.submit("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 1, payload)
    assert (receipt.status, receipt.reason_code) == ("conflict", "stream_version_conflict")


# --- The observation ID and its grant (§5.3) ---------------------------------------------------------------------------


def test_observation_id_is_known_before_submission_and_binds_the_full_subject(store: W9Store) -> None:
    registration = store.register("results/x.json")
    payload = store.observation_payload(registration)
    printed = store.observation_id(payload)
    store.clock.advance(hours=5)  # the record's created_at moves; the ID does not depend on it
    # A target other than the derived ID, under a grant on that target, is refused before append.
    other = new_id("scope_definition")
    _refused(
        store, "W9 command target is not the stream", "ObserveLegacyRecord", store.actors.observer, other, 0, payload
    )
    # A grant issued for this observation does not cover the same registration under another selector.
    table = store.membership()
    other_selector = store.observation_payload(
        registration,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": {"id": table["record_id"], "record_revision": 1, "content_hash": table["content_hash"]},
            "family_names": ["headline"],
        },
        family="headline",
    )
    grant = store.grant("ObserveLegacyRecord", "scope_definition", printed, store.actors.observer)
    envelope = store.envelope(
        "ObserveLegacyRecord",
        store.actors.observer,
        store.observation_id(other_selector),
        0,
        other_selector,
        authority_grant_id=grant,
    )
    with pytest.raises(Exception, match="authority subject scope mismatch"):
        store.runtime.submit(envelope)
    receipt, observed = store.observe(payload)
    assert receipt.status == "accepted" and observed == printed


def test_a_grant_issued_before_another_observation_lands_is_refused(store: W9Store) -> None:
    """n moved (§5.3): the preparer derives another ID, so the earlier grant's target no longer matches."""
    registration = store.register("results/x.json")
    first = store.observation_payload(registration)
    stale_target = store.observation_id(first)
    table = store.membership()
    second = store.observation_payload(
        registration,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": {"id": table["record_id"], "record_revision": 1, "content_hash": table["content_hash"]},
            "family_names": ["other"],
        },
        family="other",
    )
    assert store.observe(second)[0].status == "accepted"
    _refused(
        store,
        "W9 command target is not the stream",
        "ObserveLegacyRecord",
        store.actors.observer,
        stale_target,
        0,
        first,
    )


# --- Untracked sources, frozen copies and the window (§5.3, §7.1 to §7.4) -----------------------------------------------


def _untracked(store: W9Store, content: bytes = b"note\n") -> tuple[dict, dict, Path]:
    path = store.repo / "notes" / "untracked.md"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(content)
    registration = store.register("notes/untracked.md", kind="untracked_file", role="legacy_coordination")
    payload = store.observation_payload(registration)
    payload["frozen_copy_ref"] = store.frozen_copy(content, "untracked.md")
    return registration, payload, path


def test_an_untracked_observation_runs_the_frozen_copy_seam_end_to_end(store: W9Store) -> None:
    _, payload, _ = _untracked(store)
    receipt, observation_id = store.observe(payload)
    assert receipt.status == "accepted"
    record = store.recorded("legacy_observation", observation_id)
    assert record["source_identity"]["frozen_copy_ref"] == payload["frozen_copy_ref"]
    assert record["non_inferences"] == ["no authority from file presence (W0 §4)", "no Git identity"]


def test_a_frozen_copy_whose_bytes_differ_is_refused(store: W9Store) -> None:
    _, payload, _ = _untracked(store)
    payload["frozen_copy_ref"] = store.frozen_copy(b"other bytes\n", "other.md")
    with pytest.raises(IntegrityError, match="W9 frozen copy ref differs from its registered artefact|bytes differ"):
        store.observe(payload)


def test_a_file_replaced_at_its_registered_path_is_the_same_source(store: W9Store) -> None:
    """§5.3's reading: identical bytes under a new file ID are admitted; different bytes, or an alias, are refused."""
    _, payload, path = _untracked(store)
    printed = store.observation_id(payload)
    path.unlink()
    path.write_bytes(b"note\n")
    receipt = store.submit("ObserveLegacyRecord", store.actors.observer, printed, 0, payload)
    assert receipt.status == "accepted"
    # The ID printed for the current bytes; then the file is replaced with other bytes, and their own frozen copy, so
    # the copy check passes and the subject digest, hence the ID, no longer matches the grant's target.
    target = store.observation_id(payload)
    second = deepcopy(payload)
    second["frozen_copy_ref"] = store.frozen_copy(b"changed\n", "changed.md")
    path.unlink()
    path.write_bytes(b"changed\n")
    _refused(
        store, "W9 command target is not the stream", "ObserveLegacyRecord", store.actors.observer, target, 0, second
    )
    path.unlink()
    path.write_bytes(b"note\n")
    import os

    os.link(path, path.parent / "second-link.md")
    with pytest.raises(IntegrityError, match="the registered file has more than one link"):
        store.observe(payload)


def test_w9_t6_a_source_changed_within_the_window_aborts_with_no_event_and_no_receipt(store, monkeypatch) -> None:
    _, payload, path = _untracked(store)
    reader = store.runtime.reader
    original = reader.read
    calls = []

    def read_then_change(registration):
        result = original(registration)
        calls.append(1)
        if len(calls) == 1:
            path.write_bytes(b"edited after the first read\n")
        return result

    target = store.observation_id(payload)
    monkeypatch.setattr(reader, "read", read_then_change)
    _refused(
        store,
        "W9 source changed within the observation window",
        "ObserveLegacyRecord",
        store.actors.observer,
        target,
        0,
        payload,
    )


def test_o33_a_change_after_the_final_re_read_is_a_change_after_the_observation(store: W9Store) -> None:
    """§7.2: the observation commits with the final re-read's hashes; replay marks nothing stale from a live edit."""
    _, payload, path = _untracked(store)
    target = store.observation_id(payload)
    store.runtime.binding_check = lambda: path.write_bytes(b"edited in the gap\n")
    receipt = store.submit("ObserveLegacyRecord", store.actors.observer, target, 0, payload)
    assert receipt.status == "accepted"
    record = store.recorded("legacy_observation", target)
    assert record["source_identity"]["sha256"] == payload["frozen_copy_ref"]["content_hash"]
    state = replay_legacy(store.events(), schemas=store.harness.schemas, pinned_signatures=(store.pin,))
    assert state["stale_observations"] == []


def test_w9_t11_reader_half_a_restricted_source_has_no_frozen_copy(store: W9Store) -> None:
    path = store.repo / "data" / "rows.pkl"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"\x80\x04restricted")
    registration = store.register("data/rows.pkl", kind="restricted_untracked_file", role="legacy_research_result")
    payload = store.observation_payload(registration)
    payload["frozen_copy_ref"] = {"id": new_id("artefact"), "record_revision": 1, "content_hash": "0" * 64}
    with pytest.raises(IntegrityError, match="W9 source of this kind carries no frozen copy"):
        store.observe(payload)
    del payload["frozen_copy_ref"]
    receipt, observation_id = store.observe(payload)
    assert receipt.status == "accepted"
    source = store.recorded("legacy_observation", observation_id)["source_identity"]
    assert set(source) == {"identity_kind", "path", "sha256", "byte_length"}


# --- W9-T2 and W9-T4 on committed fixture copies (§8.2, §9.4) ----------------------------------------------------------


def test_fixture_copies_re_derive_their_source_blobs() -> None:
    import json

    from research_system.legacy.reader import git_blob_id
    from tests.research_system.integration.w9_runtime_harness import FIXTURES

    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["fixtures"]:
        raw = (FIXTURES / entry["fixture"]).read_bytes()
        assert len(raw) == entry["byte_length"]
        if entry["line_span"] is None:
            assert git_blob_id(raw) == entry["source_blob"]
        else:
            import subprocess

            source = subprocess.run(
                ["git", "cat-file", "blob", entry["source_blob"]], check=True, capture_output=True
            ).stdout
            span = entry["line_span"]
            lines = source.split(b"\n")
            assert b"\n".join(lines[span["first_line"] - 1 : span["last_line"]]) + b"\n" == raw


def test_w9_t2_the_frozen_headline_observes_its_h1_w2_family_as_superseded(store: W9Store) -> None:
    from tests.research_system.integration import w9_flows as flows

    store_path = "fixtures/usoc_headline_frozen_2026-05-28.json"
    registration = store.register(store_path)
    headline = [
        "/result/h1/w2_pvalue",
        "/result/h1/t_ratio",
        "/result/h1/bca_ci_lower",
        "/result/h1/bca_ci_upper",
        "/result/h1/d_perm",
        "/result/h1/mean_obs_null",
        "/result/h1/mean_null_null",
    ]
    from research_system.legacy.json_families import observed_pointers, parse_strict

    value = parse_strict((store.repo / store_path).read_bytes()).value
    h0 = [pointer for pointer in observed_pointers(value) if pointer.startswith("/result/h0/")]
    meta = [pointer for pointer in observed_pointers(value) if pointer not in headline and pointer not in h0]
    # A fixture table (template §5's worked example): H0 and H1 W2 apart, everything else in one metadata family.
    table = store.membership(
        store_path,
        families=[
            {"name": "meta", "definition_source": "fixture: G7-A §6.1 row T1.37", "pointers": meta},
            {"name": "h0_w2", "definition_source": "fixture: G7-A §6.1 row T1.37", "pointers": h0},
            {"name": "h1_w2", "definition_source": "fixture: SUPERSEDED.md 2026-07-14", "pointers": headline},
        ],
    )
    payload = store.observation_payload(
        registration,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": {"id": table["record_id"], "record_revision": 1, "content_hash": table["content_hash"]},
            "family_names": ["h1_w2"],
        },
    )
    payload["families"] = [flows.signed_family("h1_w2", store.pin, "superseded")]
    receipt, observation_id = store.observe(payload)
    assert receipt.status == "accepted"
    assert store.recorded("legacy_observation", observation_id)["families"][0]["w0_class"] == "superseded"


def test_w9_t4_the_superseded_lines_record_a_stale_projection_resolved_at_tier_1(store: W9Store) -> None:
    from tests.research_system.integration import w9_flows as flows

    path = "fixtures/SUPERSEDED.md"
    registration = store.register(path, role="legacy_supersession_manifest")
    raw = (store.repo / path).read_bytes()
    from research_system.canonical import sha256_hex

    own = {
        "locator_kind": "git_file",
        "repository_path": path,
        "git_commit": store.head,
        "git_blob": __import__("research_system.legacy.reader", fromlist=["git_blob_id"]).git_blob_id(raw),
        "sha256": sha256_hex(raw),
        "byte_length": len(raw),
        "line_span": {"first_line": 1, "last_line": 3},
    }
    stronger = {
        **own,
        "repository_path": "results/trajectory_tda_integration/stage1/w2_gap_closure_phase1_2026-07-16.json",
        "line_span": None,
    }
    payload = store.observation_payload(registration)
    payload["families"] = [flows.signed_family("whole_file", store.pin, "stale_projection")]
    payload["conflicts"] = [
        {"conflicting_record_refs": [own, stronger], "resolution": "resolved_by_precedence", "precedence_tier": 1}
    ]
    payload["qualifiers"] = [
        {"qualifier_kind": "stale_projection_of", "source_ref": stronger, "text": "the summary's W2 family: unverified"}
    ]
    receipt, observation_id = store.observe(payload)
    assert receipt.status == "accepted"
    record = store.recorded("legacy_observation", observation_id)
    assert record["families"][0]["w0_class"] == "stale_projection"
    assert record["conflicts"][0]["precedence_tier"] == 1
