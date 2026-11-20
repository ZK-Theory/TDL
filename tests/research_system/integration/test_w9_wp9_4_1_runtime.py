# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §5 to §9, §13, §15)
# Purpose: submit-level scratch-store controls for WP9.4-1 (LR-023 to LR-034, W9-T6/O-33, W9-T9, W9-C11, CLI adoption-status).
"""WP9.4-1 runtime and CLI tests against scratch stores under ``tmp_path``."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from research_system import cli
from research_system.artefacts.authority import ArtefactAuthorityContractLoader, GoverningEvidenceResolution
from research_system.artefacts.runtime import ControlRootArtefactContentReader
from research_system.artefacts.use_resolver import predicate_reference
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy import evidence as w9_evidence
from research_system.legacy import preparers, projection_read
from research_system.legacy.records import adoption_eligibility_decision_id, adoption_review_id, pre_assigned_ref
from research_system.legacy.replay import reducers
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.runtime import GATE6_REASON_CODE, LegacyRuntime
from tests.research_system.factories import ACTORS, activate_lifecycle_grant
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_artefact_authority_commands import SUBJECT, artefact_manifest, command
from tests.research_system.integration.test_w9_legacy_runtime import GATE6, _store, _tree_bytes
from tests.research_system.integration.w9_runtime_harness import OWNER, RESULT, W9Store, git, w9_store


class _MapEvidenceResolver:
    """Resolve test scientific-review evidence records keyed by assurance_record ID."""

    def __init__(self) -> None:
        self.entries: dict[str, tuple[str, str]] = {}

    def register(self, reference_id: str, review_id: str, subject_sha256: str) -> None:
        self.entries[reference_id] = (review_id, subject_sha256)

    def resolve(self, reference_id: str, *, project_id: str, evaluation_time: Any) -> GoverningEvidenceResolution:
        review_id, subject_sha256 = self.entries[reference_id]
        assert evaluation_time.tzinfo is not None
        record = {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": project_id,
            "review_id": review_id,
            "subject_sha256": subject_sha256,
            "reviewer_actor_id": OWNER,
            "eligible": True,
            "related": False,
            "independence_grade": "I1",
            "status": "active",
        }
        return GoverningEvidenceResolution(
            reference_id=reference_id,
            canonical_sha256=sha256_hex(canonical_bytes(record)),
            record=record,
        )


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> W9Store:
    return w9_store(tmp_path, monkeypatch)


def _snapshot(store: W9Store) -> tuple[tuple[dict[str, Any], ...], dict[str, bytes]]:
    return store.events(), _tree_bytes(store.runtime.control_root)


def _state(store: W9Store) -> dict[str, Any]:
    return replay_legacy(store.events(), schemas=store.harness.schemas, pinned_signatures=(store.pin,))


def _add_repo_sources(
    store: W9Store,
    files: dict[str, bytes],
    *,
    track: tuple[str, ...] = (),
    manifest_paths: tuple[str, ...] = (),
) -> None:
    """Write repo files, add any newly tracked files + manifest entries to Git, commit, and rebind."""
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
    for rel in track:
        git(store.repo, "add", "-f", rel)
    git(store.repo, "commit", "-q", "-m", "update scratch sources")
    store.rebind()


def _commit_open_items(store: W9Store, items: list[dict[str, Any]]) -> str:
    """Commit ``legacy-open-items.json`` into the scratch repo (never the real repo), rebind, and return its blob."""
    path = store.repo / w9_evidence.LEGACY_OPEN_ITEMS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"format": w9_evidence.LEGACY_OPEN_ITEMS_FORMAT, "items": items}), encoding="utf-8")
    git(store.repo, "add", "-f", w9_evidence.LEGACY_OPEN_ITEMS)
    git(store.repo, "commit", "-q", "-m", "update open items")
    store.rebind()
    return git(store.repo, "rev-parse", f"{store.head}:{w9_evidence.LEGACY_OPEN_ITEMS}")


def _adoption_payload(
    store: W9Store,
    observation: dict[str, Any],
    *,
    subject: dict[str, Any] | None = None,
    intended_use: dict[str, Any] | None = None,
    w5_consequence: str = "admissible_for_named_use",
    qualifiers_to_discharge: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record_id = new_id("scope_definition")
    return {
        "schema_id": "ars://legacy/legacy-adoption-decision",
        "schema_version": "1.0.0",
        "record_id": record_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "observation_ref": flows.record_ref(observation),
        "subject": subject or {"subject_kind": "families", "family_names": ["headline"]},
        "intended_use": intended_use or {"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
        "w5_consequence": w5_consequence,
        "qualifiers_to_discharge": [] if qualifiers_to_discharge is None else qualifiers_to_discharge,
        "decision_ref": pre_assigned_ref("decision", new_id("decision"), record_id),
    }


def _discharge_payload(
    store: W9Store,
    artefact_ref: dict[str, Any],
    *,
    item_kind: str = "a001_item",
    item_id: str = "A001-01",
) -> dict[str, Any]:
    record_id = new_id("scope_definition")
    return {
        "schema_id": "ars://legacy/legacy-discharge-relation",
        "schema_version": "1.0.0",
        "record_id": record_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": store.harness.ledger.project_id,
        "successor_result_ref": artefact_ref,
        "legacy_item": {"item_kind": item_kind, "item_id": item_id},
        "reviewer_ref": pre_assigned_ref("review", new_id("review"), record_id),
        "decision_ref": pre_assigned_ref("decision", new_id("decision"), record_id),
    }


def _adopt_via_submit(
    store: W9Store,
    payload: dict[str, Any],
    *,
    fixtures: tuple[str, ...],
    stop_after: str | None = None,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    """Drive LR-023 -> LR-029 through ``store.submit``, returning the proposed record and envelope/receipt log."""
    steps: list[tuple[dict[str, Any], Any]] = []

    def send(cmd: str, actor: str, target: str, ver: int, body: dict[str, Any]) -> Any:
        env = store.envelope(cmd, actor, target, ver, body)
        rec = store.runtime.submit(env)
        assert rec.status == "accepted", rec
        store.log.append((env, rec))
        steps.append((env, rec))
        return rec

    adp_id = payload["record_id"]
    send("ProposeLegacyRecord", store.actors.analyst, adp_id, 0, payload)
    proposed = _state(store)["proposals"][adp_id]["record"]
    if stop_after == "LR-023":
        return proposed, steps

    elig_id = adoption_eligibility_decision_id(adp_id, proposed["created_at"])
    send(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        elig_id,
        0,
        {
            "subject_record_id": adp_id,
            "question": "Is the named reviewer session eligible for this adoption?",
            "recommendation": "accept",
            "consequences": ["the named session may review the adoption"],
            "eligibility": dict(flows.ELIGIBILITY),
        },
    )
    if stop_after == "LR-024":
        return proposed, steps

    send("ResolveW9AuthorityDecision", OWNER, elig_id, 1, {"decision_id": elig_id, "selected_option": "accept"})
    if stop_after == "LR-025":
        return proposed, steps

    rev_id = adoption_review_id(adp_id, proposed["created_at"])
    send(
        "RequestW9AuthorityReview",
        store.actors.analyst,
        rev_id,
        0,
        {
            "subject_record_id": adp_id,
            "reviewer_actor_id": store.actors.reviewer,
            "review_questions": [
                "Is this legacy adoption decision sound?",
                f"w9-applicable-fixtures:{','.join(fixtures)}",
            ],
            "analyst_session": "session-analyst",
            "eligible_session": flows.ELIGIBILITY["session"],
        },
    )
    if stop_after == "LR-026":
        return proposed, steps

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
            "reviewer_session": flows.ELIGIBILITY["session"],
            "reviewer_model_metadata": f"{flows.ELIGIBILITY['family']}@{flows.ELIGIBILITY['version']}",
            "context_manifest_sha256": "9" * 64,
        },
    )
    if stop_after == "LR-027":
        return proposed, steps

    dec_id = payload["decision_ref"]["id"]
    send(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        dec_id,
        0,
        {
            "subject_record_id": adp_id,
            "question": "Adopt this legacy observation for the named use?",
            "recommendation": "accept",
            "consequences": ["recorded legacy adoption"],
            "fixture_refs": [f"w9-fixture:{fid}:{new_id('review')}" for fid in fixtures],
        },
    )
    if stop_after == "LR-028":
        return proposed, steps

    send("ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"})
    return proposed, steps


def _make_generic_artefact(
    store: W9Store,
    raw: bytes,
    rel_path: str,
    *,
    accept: bool = True,
) -> tuple[dict[str, Any], str, Path]:
    """Register (and optionally accept_for_scope) a generic artefact under the scratch control root."""
    control = store.harness.ledger.control_root
    dest = control / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    artefact_id = new_id("artefact")
    review_id = new_id("review")
    evidence_id = new_id("assurance_record")
    digest = sha256_hex(raw)
    resolver = store.harness.service.governing_evidence_resolver
    if not isinstance(resolver, _MapEvidenceResolver):
        resolver = _MapEvidenceResolver()
        store.harness.service.governing_evidence_resolver = resolver
    resolver.register(evidence_id, review_id, digest)
    owner_grant = activate_lifecycle_grant(
        store.harness,
        subject_kind="artefact",
        subject_id=artefact_id,
        actor_id=OWNER,
        allowed_actor_classes=("human",),
        command_types=("RegisterArtefact", "SetArtefactUseAuthority", "SupersedeArtefact"),
        grant_id=new_id("authority_grant"),
    )
    review_grant = activate_lifecycle_grant(
        store.harness,
        subject_kind="artefact",
        subject_id=artefact_id,
        actor_id=OWNER,
        allowed_actor_classes=("human",),
        command_types=("RecordScientificReview",),
        grant_id=new_id("authority_grant"),
    )
    manifest = deepcopy(artefact_manifest())
    manifest.update(
        artefact_id=artefact_id,
        producer_actor_id=ACTORS["actor-b"],
        relative_path=rel_path,
        size_bytes=len(raw),
        content_sha256=digest,
    )
    submitted_at = store.harness.service.clock().isoformat().replace("+00:00", "Z")
    project_id = store.harness.ledger.project_id
    reg_cmd = {
        **command(
            command_id=new_id("command"),
            command_type="RegisterArtefact",
            actor_id=OWNER,
            authority_grant_id=owner_grant,
            expected_stream_version=0,
            payload={"new_artefact_id": artefact_id, "manifest": manifest},
            target_stream_id=artefact_id,
        ),
        "project_id": project_id,
        "submitted_at": submitted_at,
    }
    assert store.harness.service.submit(reg_cmd).status == "accepted"
    rev_cmd = {
        **command(
            command_id=new_id("command"),
            command_type="RecordScientificReview",
            actor_id=OWNER,
            authority_grant_id=review_grant,
            expected_stream_version=1,
            payload={
                "artefact_id": artefact_id,
                "review_id": review_id,
                "subject_sha256": digest,
                "scientific_review": "approved",
                "evidence_refs": [evidence_id],
            },
            target_stream_id=artefact_id,
        ),
        "project_id": project_id,
        "submitted_at": submitted_at,
    }
    assert store.harness.service.submit(rev_cmd).status == "accepted"
    if accept:
        predicate, pred_sha = ArtefactAuthorityContractLoader(SUBJECT).load().predicate_for("result_evidence")
        use_cmd = {
            **command(
                command_id=new_id("command"),
                command_type="SetArtefactUseAuthority",
                actor_id=OWNER,
                authority_grant_id=owner_grant,
                expected_stream_version=2,
                payload={
                    "artefact_id": artefact_id,
                    "use_authority": "accepted_for_scope",
                    "subject_sha256": digest,
                    "consumer_predicate": predicate_reference(
                        str(predicate["predicate_id"]), str(predicate["predicate_version"]), pred_sha
                    ),
                    "evidence_refs": [review_id, evidence_id],
                },
                target_stream_id=artefact_id,
            ),
            "project_id": project_id,
            "submitted_at": submitted_at,
        }
        assert store.harness.service.submit(use_cmd).status == "accepted"
    return {"id": artefact_id, "record_revision": 1, "content_hash": digest}, owner_grant, dest


def _discharge_via_submit(
    store: W9Store,
    payload: dict[str, Any],
    *,
    open_items_blob: str,
    stop_after: str | None = None,
) -> list[tuple[dict[str, Any], Any]]:
    """Drive LR-030 -> LR-034 through ``store.submit``, returning the envelope/receipt pairs."""
    steps: list[tuple[dict[str, Any], Any]] = []

    def send(cmd: str, actor: str, target: str, ver: int, body: dict[str, Any]) -> Any:
        env = store.envelope(cmd, actor, target, ver, body)
        rec = store.runtime.submit(env)
        assert rec.status == "accepted", rec
        store.log.append((env, rec))
        steps.append((env, rec))
        return rec

    dis_id = payload["record_id"]
    send("ProposeLegacyRecord", store.actors.analyst, dis_id, 0, payload)
    if stop_after == "LR-030":
        return steps

    rev_id = payload["reviewer_ref"]["id"]
    send(
        "RequestW9AuthorityReview",
        store.actors.analyst,
        rev_id,
        0,
        {
            "subject_record_id": dis_id,
            "reviewer_actor_id": store.actors.reviewer,
            "review_questions": ["Does this successor result discharge the open item?", "w9-applicable-fixtures:"],
            "analyst_session": "session-analyst",
        },
    )
    if stop_after == "LR-031":
        return steps

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
    if stop_after == "LR-032":
        return steps

    dec_id = payload["decision_ref"]["id"]
    send(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        dec_id,
        0,
        {
            "subject_record_id": dis_id,
            "question": "Accept this discharge relation?",
            "recommendation": "accept",
            "consequences": ["legacy item discharged"],
            "fixture_refs": [],
            "open_items_blob": open_items_blob,
        },
    )
    if stop_after == "LR-033":
        return steps

    send("ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"})
    return steps


# --- Positive adoptions (§6, §7, §9) ---------------------------------------------------------------------------------


def test_positive_family_adoptions_and_open_findings_active_through_submit(store: W9Store) -> None:
    """LR-023..LR-029 via submit for manuscript-claims/P01-A and task-input with an open review finding."""
    reg = store.register("results/x.json")
    table = store.membership()
    sections_raw = (store.repo / "sections.md").read_bytes()
    finding_src = {
        "locator_kind": "git_file",
        "repository_path": "sections.md",
        "git_commit": store.head,
        "git_blob": git(store.repo, "rev-parse", f"{store.head}:sections.md"),
        "sha256": sha256_hex(sections_raw),
        "byte_length": len(sections_raw),
        "line_span": None,
    }
    p_head = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        family="headline",
    )
    p_meta = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["meta"],
        },
        family="meta",
    )
    p_meta["qualifiers"] = [
        {"qualifier_kind": "open_review_finding", "source_ref": finding_src, "text": "Calibration finding"}
    ]
    _, obs_head_id = store.observe(p_head)
    _, obs_meta_id = store.observe(p_meta)
    assert store.accept(store.acceptance_payload([obs_head_id, obs_meta_id])).status == "accepted"

    obs_head = store.recorded("legacy_observation", obs_head_id)
    obs_meta = store.recorded("legacy_observation", obs_meta_id)
    adp_claim, _ = _adopt_via_submit(
        store,
        _adoption_payload(
            store,
            obs_head,
            subject={"subject_kind": "families", "family_names": ["headline"]},
            intended_use={"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
        ),
        fixtures=("F-019", "S-017"),
    )
    adp_task, _ = _adopt_via_submit(
        store,
        _adoption_payload(
            store,
            obs_meta,
            subject={"subject_kind": "families", "family_names": ["meta"]},
            intended_use={"description": "w9-use:task-input/calib", "successor_ref": None},
            w5_consequence="task_input_with_open_findings",
            qualifiers_to_discharge=list(obs_meta["qualifiers"]),
        ),
        fixtures=("S-017",),
    )

    state = _state(store)
    assert projection_read.adoption_status(state, adp_claim["record_id"]) == {
        "adoption_id": adp_claim["record_id"],
        "status": "active",
        "cause": None,
    }
    assert projection_read.adoption_status(state, adp_task["record_id"]) == {
        "adoption_id": adp_task["record_id"],
        "status": "active",
        "cause": None,
    }
    assert projection_read.family_admissible(state, obs_head_id, "headline", "w9-use:manuscript-claims/P01-A")[
        "admissible"
    ]
    assert not projection_read.family_admissible(state, obs_head_id, "other", "w9-use:manuscript-claims/P01-A")[
        "admissible"
    ]


def test_whole_file_adoption_admits_binary_and_restricted_refuses_unrestricted_utf8(store: W9Store) -> None:
    """§6.1: whole-file admits non-UTF-8 tracked binary and restricted_untracked_file; refuses plain UTF-8 text."""
    _add_repo_sources(
        store,
        {
            "data/embed.bin": b"\xff\xfe\x00\x80",
            "notes/plain.txt": b"plain utf8 text\n",
            "data/restricted.csv": b"col\n1\n",
        },
        track=("data/embed.bin", "notes/plain.txt"),
        manifest_paths=("data/embed.bin", "notes/plain.txt", "data/restricted.csv"),
    )
    r_bin = store.register("data/embed.bin")
    r_res = store.register("data/restricted.csv", kind="restricted_untracked_file")
    r_txt = store.register("notes/plain.txt")
    _, o_bin_id = store.observe(store.observation_payload(r_bin))
    _, o_res_id = store.observe(store.observation_payload(r_res))
    _, o_txt_id = store.observe(store.observation_payload(r_txt))
    assert store.accept(store.acceptance_payload([o_bin_id, o_res_id, o_txt_id])).status == "accepted"

    o_txt = store.recorded("legacy_observation", o_txt_id)
    bad_plain = _adoption_payload(
        store,
        o_txt,
        subject={"subject_kind": "whole_file", "rehash_at_use": True},
        intended_use={"description": "w9-use:task-input/plain", "successor_ref": None},
    )
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 whole-file adoption requires a binary or restricted source"):
        store.submit("ProposeLegacyRecord", store.actors.analyst, bad_plain["record_id"], 0, bad_plain)
    assert _snapshot(store) == before

    for obs_id, use_key in ((o_bin_id, "embed"), (o_res_id, "restricted")):
        obs = store.recorded("legacy_observation", obs_id)
        adp, _ = _adopt_via_submit(
            store,
            _adoption_payload(
                store,
                obs,
                subject={"subject_kind": "whole_file", "rehash_at_use": True},
                intended_use={"description": f"w9-use:task-input/{use_key}", "successor_ref": None},
            ),
            fixtures=("S-017",),
        )
        assert projection_read.adoption_status(_state(store), adp["record_id"])["status"] == "active"


# --- Positive discharge + W9-C11 across all 12 rows (§8, §17) --------------------------------------------------------


def test_positive_discharge_through_submit_and_w9_c11_retries_across_all_twelve_rows(store: W9Store) -> None:
    """Drive all 12 new rows (LR-023..LR-034) through submit and replay every envelope identically (W9-C11)."""
    blob = _commit_open_items(
        store, [{"item_kind": "a001_item", "item_id": "A001-01", "source": "audit/w0.md#L1", "feeds_papers": ["P01-A"]}]
    )
    art_ref, _, _ = _make_generic_artefact(store, b'{"successor": true}\n', "evidence/successor/result.json")

    reg = store.register("results/x.json")
    table = store.membership()
    obs_p = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        family="headline",
    )
    _, obs_id = store.observe(obs_p)
    assert store.accept(store.acceptance_payload([obs_id])).status == "accepted"

    obs = store.recorded("legacy_observation", obs_id)
    adp, adp_steps = _adopt_via_submit(store, _adoption_payload(store, obs), fixtures=("F-019", "S-017"))
    dis_payload = _discharge_payload(store, art_ref)
    dis_steps = _discharge_via_submit(store, dis_payload, open_items_blob=blob)

    state = _state(store)
    assert dis_payload["record_id"] in state["records"][reducers.DISCHARGE]
    for row in sorted(reducers.WP9_4_1_ROWS):
        assert state["row_counts"].get(row) == 1
    assert state["records"][reducers.ADOPTION][adp["record_id"]]["record_id"] == adp["record_id"]

    all_steps = [*adp_steps, *dis_steps]
    assert len(all_steps) == 12
    before_events = store.events()
    for env, receipt in all_steps:
        retried = store.runtime.submit(deepcopy(env))
        assert retried.status == receipt.status == "accepted"
        assert (retried.command_id, retried.event_batch_id) == (receipt.command_id, receipt.event_batch_id)
    assert store.events() == before_events


# --- Roles & G4 grant subjects (§5.1, §5.5) --------------------------------------------------------------------------


def test_roles_and_g4_grant_subjects_for_all_twelve_rows(store: W9Store) -> None:
    """Owner refused on all 9 non-resolver rows; non-owner refused on 3 resolver rows; G4 checks target vs grant."""
    blob = _commit_open_items(
        store, [{"item_kind": "a001_item", "item_id": "A001-01", "source": "audit/w0.md#L1", "feeds_papers": ["P01-A"]}]
    )
    art_ref, _, _ = _make_generic_artefact(store, b'{"successor": "roles"}\n', "evidence/successor/roles.json")

    reg = store.register("results/x.json")
    table = store.membership()
    obs_p = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        family="headline",
    )
    _, obs_id = store.observe(obs_p)
    assert store.accept(store.acceptance_payload([obs_id])).status == "accepted"
    obs = store.recorded("legacy_observation", obs_id)

    def assert_refused(cmd: str, actor: str, target: str, ver: int, body: dict[str, Any], msg: str, **ov: Any) -> None:
        before = _snapshot(store)
        with pytest.raises(Exception, match=msg):
            env = store.envelope(cmd, actor, target, ver, body, **ov)
            store.runtime.submit(env)
        assert _snapshot(store) == before

    adp = _adoption_payload(store, obs)
    adp_id = adp["record_id"]
    wrong_adp_grant = store.grant(
        "ProposeLegacyRecord", "scope_definition", new_id("scope_definition"), store.actors.analyst
    )
    assert_refused(
        "ProposeLegacyRecord",
        store.actors.analyst,
        adp_id,
        0,
        adp,
        "authority subject scope mismatch",
        authority_grant_id=wrong_adp_grant,
    )
    assert_refused("ProposeLegacyRecord", OWNER, adp_id, 0, adp, "W9 LR-023 refuses the owner")
    proposed, _ = _adopt_via_submit(store, adp, fixtures=("F-019", "S-017"), stop_after="LR-023")

    elig_id = adoption_eligibility_decision_id(adp_id, proposed["created_at"])
    elig_prop = {
        "subject_record_id": adp_id,
        "question": "Eligible?",
        "recommendation": "accept",
        "consequences": ["c"],
        "eligibility": dict(flows.ELIGIBILITY),
    }
    wrong_dec_grant = store.grant(
        "ProposeW9AuthorityDecision", "decision", adp["decision_ref"]["id"], store.actors.analyst
    )
    assert_refused(
        "ProposeW9AuthorityDecision",
        store.actors.analyst,
        elig_id,
        0,
        elig_prop,
        "authority subject scope mismatch",
        authority_grant_id=wrong_dec_grant,
    )
    assert_refused("ProposeW9AuthorityDecision", OWNER, elig_id, 0, elig_prop, "W9 LR-024 refuses the owner")
    assert store.submit("ProposeW9AuthorityDecision", store.actors.analyst, elig_id, 0, elig_prop).status == "accepted"

    assert_refused(
        "ResolveW9AuthorityDecision",
        store.actors.analyst,
        elig_id,
        1,
        {"decision_id": elig_id, "selected_option": "accept"},
        "W9 LR-025 is resolved by the owner only",
    )
    assert (
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, elig_id, 1, {"decision_id": elig_id, "selected_option": "accept"}
        ).status
        == "accepted"
    )

    rev_id = adoption_review_id(adp_id, proposed["created_at"])
    rev_req = {
        "subject_record_id": adp_id,
        "reviewer_actor_id": store.actors.reviewer,
        "review_questions": ["q", "w9-applicable-fixtures:F-019,S-017"],
        "analyst_session": "session-analyst",
        "eligible_session": flows.ELIGIBILITY["session"],
    }
    assert_refused("RequestW9AuthorityReview", OWNER, rev_id, 0, rev_req, "W9 LR-026 refuses the owner")
    assert store.submit("RequestW9AuthorityReview", store.actors.analyst, rev_id, 0, rev_req).status == "accepted"

    verdict_body = {
        "review_id": rev_id,
        "verdict": "approve",
        "findings": [],
        "limitations": [],
        "reviewer_session": flows.ELIGIBILITY["session"],
        "reviewer_model_metadata": f"{flows.ELIGIBILITY['family']}@{flows.ELIGIBILITY['version']}",
        "context_manifest_sha256": "9" * 64,
    }
    assert_refused(
        "RecordW9AuthorityReview",
        OWNER,
        rev_id,
        1,
        verdict_body,
        "W9 verdict is not recorded by the reviewer the request named",
    )
    assert store.submit("RecordW9AuthorityReview", store.actors.reviewer, rev_id, 1, verdict_body).status == "accepted"

    dec_id = adp["decision_ref"]["id"]
    dec_body = {
        "subject_record_id": adp_id,
        "question": "Adopt?",
        "recommendation": "accept",
        "consequences": ["c"],
        "fixture_refs": [f"w9-fixture:F-019:{new_id('review')}", f"w9-fixture:S-017:{new_id('review')}"],
    }
    assert_refused("ProposeW9AuthorityDecision", OWNER, dec_id, 0, dec_body, "W9 LR-028 refuses the owner")
    assert store.submit("ProposeW9AuthorityDecision", store.actors.analyst, dec_id, 0, dec_body).status == "accepted"
    assert_refused(
        "ResolveW9AuthorityDecision",
        store.actors.analyst,
        dec_id,
        1,
        {"decision_id": dec_id, "selected_option": "accept"},
        "W9 LR-029 is resolved by the owner only",
    )

    dis = _discharge_payload(store, art_ref)
    dis_id = dis["record_id"]
    wrong_dis_grant = store.grant(
        "ProposeLegacyRecord", "scope_definition", new_id("scope_definition"), store.actors.analyst
    )
    assert_refused(
        "ProposeLegacyRecord",
        store.actors.analyst,
        dis_id,
        0,
        dis,
        "authority subject scope mismatch",
        authority_grant_id=wrong_dis_grant,
    )
    assert_refused("ProposeLegacyRecord", OWNER, dis_id, 0, dis, "W9 LR-030 refuses the owner")
    _discharge_via_submit(store, dis, open_items_blob=blob, stop_after="LR-030")

    d_rev = dis["reviewer_ref"]["id"]
    d_req = {
        "subject_record_id": dis_id,
        "reviewer_actor_id": store.actors.reviewer,
        "review_questions": ["q", "w9-applicable-fixtures:"],
        "analyst_session": "session-analyst",
    }
    assert_refused("RequestW9AuthorityReview", OWNER, d_rev, 0, d_req, "W9 LR-031 refuses the owner")
    assert store.submit("RequestW9AuthorityReview", store.actors.analyst, d_rev, 0, d_req).status == "accepted"

    d_ver = {
        "review_id": d_rev,
        "verdict": "approve",
        "findings": [],
        "limitations": [],
        "reviewer_session": "session-reviewer",
        "reviewer_model_metadata": "w9-test-model",
        "context_manifest_sha256": "9" * 64,
    }
    assert_refused(
        "RecordW9AuthorityReview",
        OWNER,
        d_rev,
        1,
        d_ver,
        "W9 verdict is not recorded by the reviewer the request named",
    )
    assert store.submit("RecordW9AuthorityReview", store.actors.reviewer, d_rev, 1, d_ver).status == "accepted"

    auth_ctx = SimpleNamespace(administration_context=SimpleNamespace(owner_actor_id=OWNER))
    for role_row in ("LR-027", "LR-032"):
        with pytest.raises(IntegrityError, match=f"W9 {role_row} refuses the owner"):
            LegacyRuntime._require_role(SimpleNamespace(actor_id=OWNER), role_row, auth_ctx)

    d_dec = dis["decision_ref"]["id"]
    d_dec_body = {
        "subject_record_id": dis_id,
        "question": "Discharge?",
        "recommendation": "accept",
        "consequences": ["c"],
        "fixture_refs": [],
        "open_items_blob": blob,
    }
    assert_refused("ProposeW9AuthorityDecision", OWNER, d_dec, 0, d_dec_body, "W9 LR-033 refuses the owner")
    assert store.submit("ProposeW9AuthorityDecision", store.actors.analyst, d_dec, 0, d_dec_body).status == "accepted"
    assert_refused(
        "ResolveW9AuthorityDecision",
        store.actors.analyst,
        d_dec,
        1,
        {"decision_id": d_dec, "selected_option": "accept"},
        "W9 LR-034 is resolved by the owner only",
    )


# --- W9-T6 and O-33 source window on adoption (§6.5, §7.2) ------------------------------------------------------------


def _setup_binary_untracked_adp(store: W9Store) -> tuple[Path, bytes, dict[str, Any]]:
    bin_path = store.repo / "notes" / "raw.bin"
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    initial = b"\xff\xfe\x01\x02"
    bin_path.write_bytes(initial)
    _add_repo_sources(store, {}, manifest_paths=("notes/raw.bin",))
    reg = store.register("notes/raw.bin", kind="untracked_file", role="legacy_research_result")
    obs_p = store.observation_payload(reg)
    obs_p["frozen_copy_ref"] = store.frozen_copy(initial, "raw.bin")
    _, obs_id = store.observe(obs_p)
    assert store.accept(store.acceptance_payload([obs_id])).status == "accepted"
    obs = store.recorded("legacy_observation", obs_id)
    adp = _adoption_payload(
        store,
        obs,
        subject={"subject_kind": "whole_file", "rehash_at_use": True},
        intended_use={"description": "w9-use:task-input/win", "successor_ref": None},
    )
    return bin_path, initial, adp


def test_w9_t6_and_o33_adoption_source_window(store: W9Store, monkeypatch: pytest.MonkeyPatch) -> None:
    """Source changed before LR-023, before LR-029, or at commit reread refuses; O-33 post-reread gap commits."""
    bin_path, initial, adp = _setup_binary_untracked_adp(store)

    # Altered on disk before LR-023.
    bin_path.write_bytes(b"\xff\xfe\x99\x99")
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 adoption source re-reads differently from its observation"):
        store.submit("ProposeLegacyRecord", store.actors.analyst, adp["record_id"], 0, adp)
    assert _snapshot(store) == before
    bin_path.write_bytes(initial)

    # Commit-time reread abort at LR-023.
    reader = store.runtime.reader
    orig_read = reader.read
    calls = []

    def mutate_on_first_read(registration: Any) -> Any:
        out = orig_read(registration)
        calls.append(1)
        if len(calls) == 1:
            bin_path.write_bytes(b"\xff\xfe\x77\x77")
        return out

    monkeypatch.setattr(reader, "read", mutate_on_first_read)
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 adoption source re-reads differently from its observation"):
        store.submit("ProposeLegacyRecord", store.actors.analyst, adp["record_id"], 0, adp)
    assert _snapshot(store) == before
    monkeypatch.setattr(reader, "read", orig_read)
    bin_path.write_bytes(initial)

    # Drive LR-023..LR-028, then mutate before LR-029.
    _adopt_via_submit(store, adp, fixtures=("S-017",), stop_after="LR-028")
    dec_id = adp["decision_ref"]["id"]
    bin_path.write_bytes(b"\xff\xfe\x88\x88")
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 adoption source re-reads differently from its observation"):
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        )
    assert _snapshot(store) == before
    bin_path.write_bytes(initial)

    # Commit-time reread abort at LR-029.
    calls.clear()
    monkeypatch.setattr(reader, "read", mutate_on_first_read)
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 adoption source re-reads differently from its observation"):
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        )
    assert _snapshot(store) == before
    monkeypatch.setattr(reader, "read", orig_read)
    bin_path.write_bytes(initial)

    # O-33: change after commit reread (during binding_check) commits cleanly with prior hashes.
    orig_check = store.runtime.binding_check
    store.runtime.binding_check = lambda: bin_path.write_bytes(b"\xff\xfe\xaa\xaa")
    receipt = store.submit(
        "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
    )
    store.runtime.binding_check = orig_check
    assert receipt.status == "accepted"
    assert dec_id in _state(store)["decisions"]


# --- W9-T9 real scratch-store re-observations (§7, owner point D) -----------------------------------------------------


def test_w9_t9_reobservations_on_scratch_store_suspend_or_preserve_adoption(store: W9Store) -> None:
    """W9-T9 (a) same-family new blob, (b) same-family same blob, (c) disjoint-family new blob; control: disjoint same blob."""
    _add_repo_sources(
        store,
        {"results/t9_a.json": RESULT, "results/t9_c.json": RESULT},
        track=("results/t9_a.json", "results/t9_c.json"),
        manifest_paths=("results/t9_a.json", "results/t9_c.json"),
    )
    regs = {
        k: store.register(p)
        for k, p in (("a", "results/x.json"), ("b", "results/t9_a.json"), ("c", "results/t9_c.json"))
    }
    tables = {
        k: store.membership(p)
        for k, p in (("a", "results/x.json"), ("b", "results/t9_a.json"), ("c", "results/t9_c.json"))
    }
    obs_ids = {}
    for k in ("a", "b", "c"):
        _, oid = store.observe(
            store.observation_payload(
                regs[k],
                selector={
                    "selector_kind": "json_family_set",
                    "membership_ref": flows.record_ref(tables[k]),
                    "family_names": ["headline"],
                },
                family="headline",
            )
        )
        obs_ids[k] = oid
    assert store.accept(store.acceptance_payload([obs_ids["a"], obs_ids["b"], obs_ids["c"]])).status == "accepted"

    adps = {}
    for k in ("a", "b", "c"):
        obs = store.recorded("legacy_observation", obs_ids[k])
        adp, _ = _adopt_via_submit(store, _adoption_payload(store, obs), fixtures=("F-019", "S-017"))
        adps[k] = adp["record_id"]

    # Control: disjoint family ("other"), same blob -> active.
    assert (
        store.observe(
            store.observation_payload(
                regs["a"],
                selector={
                    "selector_kind": "json_family_set",
                    "membership_ref": flows.record_ref(tables["a"]),
                    "family_names": ["other"],
                },
                family="other",
            )
        )[0].status
        == "accepted"
    )
    assert projection_read.adoption_status(_state(store), adps["a"]) == {
        "adoption_id": adps["a"],
        "status": "active",
        "cause": None,
    }

    # (b) Same family ("headline"), same blob -> suspended / later_observation.
    assert (
        store.observe(
            store.observation_payload(
                regs["a"],
                selector={
                    "selector_kind": "json_family_set",
                    "membership_ref": flows.record_ref(tables["a"]),
                    "family_names": ["headline"],
                },
                family="headline",
            )
        )[0].status
        == "accepted"
    )
    assert projection_read.adoption_status(_state(store), adps["a"]) == {
        "adoption_id": adps["a"],
        "status": "suspended",
        "cause": "later_observation",
    }

    # (a) Same family ("headline"), new blob -> suspended / observation_stale.
    _add_repo_sources(
        store, {"results/t9_a.json": b'{"headline": 2.0, "other": [1, 2]}\n'}, track=("results/t9_a.json",)
    )
    new_table_b = store.membership("results/t9_a.json")
    assert (
        store.observe(
            store.observation_payload(
                regs["b"],
                selector={
                    "selector_kind": "json_family_set",
                    "membership_ref": flows.record_ref(new_table_b),
                    "family_names": ["headline"],
                },
                family="headline",
            )
        )[0].status
        == "accepted"
    )
    assert projection_read.adoption_status(_state(store), adps["b"]) == {
        "adoption_id": adps["b"],
        "status": "suspended",
        "cause": "observation_stale",
    }

    # (c) Disjoint family ("other"), new blob -> suspended / observation_stale (M-1).
    _add_repo_sources(
        store, {"results/t9_c.json": b'{"headline": 1.0, "other": [1, 3]}\n'}, track=("results/t9_c.json",)
    )
    new_table_c = store.membership("results/t9_c.json")
    assert (
        store.observe(
            store.observation_payload(
                regs["c"],
                selector={
                    "selector_kind": "json_family_set",
                    "membership_ref": flows.record_ref(new_table_c),
                    "family_names": ["other"],
                },
                family="other",
            )
        )[0].status
        == "accepted"
    )
    assert projection_read.adoption_status(_state(store), adps["c"]) == {
        "adoption_id": adps["c"],
        "status": "suspended",
        "cause": "observation_stale",
    }


# --- LR-025 record-less eligibility resolution (§5.5) -----------------------------------------------------------------


def test_lr025_is_record_less_and_admits_accept_or_reject(store: W9Store) -> None:
    """LR-025 writes only DecisionResolved (1 event), has no rereads, and accepts either 'accept' or 'reject'."""
    reg = store.register("results/x.json")
    table = store.membership()
    obs_p = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        family="headline",
    )
    _, obs_id = store.observe(obs_p)
    assert store.accept(store.acceptance_payload([obs_id])).status == "accepted"
    obs = store.recorded("legacy_observation", obs_id)

    # 1. Accept branch: inspect preparer directly, then submit.
    adp_acc = _adoption_payload(store, obs)
    prop_acc, _ = _adopt_via_submit(store, adp_acc, fixtures=("F-019", "S-017"), stop_after="LR-024")
    elig_acc = adoption_eligibility_decision_id(adp_acc["record_id"], prop_acc["created_at"])
    env_stub = preparers.Environment(store.runtime.reader, {}, store.harness.ledger.control_root, None)
    prep = preparers.prepare_resolution(
        {"decision_id": elig_acc, "selected_option": "accept"},
        actor=OWNER,
        now=store.clock(),
        legacy=_state(store),
        environment=env_stub,
        grant_id=new_id("authority_grant"),
    )
    assert [et for et, _, _ in prep.events] == ["DecisionResolved"]
    assert prep.rereads == []
    before_ev = store.events()
    assert (
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, elig_acc, 1, {"decision_id": elig_acc, "selected_option": "accept"}
        ).status
        == "accepted"
    )
    after_ev = store.events()
    assert len(after_ev) - len(before_ev) == 1
    assert after_ev[-1]["event_type"] == "DecisionResolved"

    # 2. Reject branch: accepted DecisionResolved with 'reject', blocking LR-026.
    adp_rej = _adoption_payload(store, obs)
    prop_rej, _ = _adopt_via_submit(store, adp_rej, fixtures=("F-019", "S-017"), stop_after="LR-024")
    elig_rej = adoption_eligibility_decision_id(adp_rej["record_id"], prop_rej["created_at"])
    before_ev = store.events()
    assert (
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, elig_rej, 1, {"decision_id": elig_rej, "selected_option": "reject"}
        ).status
        == "accepted"
    )
    after_ev = store.events()
    assert len(after_ev) - len(before_ev) == 1
    assert after_ev[-1]["event_type"] == "DecisionResolved"
    rev_id = adoption_review_id(adp_rej["record_id"], prop_rej["created_at"])
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 adoption review requires an accepted eligibility Decision"):
        store.submit(
            "RequestW9AuthorityReview",
            store.actors.analyst,
            rev_id,
            0,
            {
                "subject_record_id": adp_rej["record_id"],
                "reviewer_actor_id": store.actors.reviewer,
                "review_questions": ["q", "w9-applicable-fixtures:F-019,S-017"],
                "analyst_session": "session-analyst",
                "eligible_session": flows.ELIGIBILITY["session"],
            },
        )
    assert _snapshot(store) == before


# --- Discharge preparer controls (LR-030..LR-034; §8, R-M2, G3) -------------------------------------------------------


def test_discharge_preparer_controls_from_lr030_to_lr034(store: W9Store, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test LR-030..LR-034 refusals: unknown item, uncommitted list, candidate/copy artefact, G3, blob drift, demotion, reread."""
    _add_repo_sources(
        store,
        {"results/unadopted.json": b'{"unadopted": 1}\n'},
        track=("results/unadopted.json",),
        manifest_paths=("results/unadopted.json",),
    )
    reg_x = store.register("results/x.json")
    reg_u = store.register("results/unadopted.json")
    table = store.membership()
    _, obs_head_id = store.observe(
        store.observation_payload(
            reg_x,
            selector={
                "selector_kind": "json_family_set",
                "membership_ref": flows.record_ref(table),
                "family_names": ["headline"],
            },
            family="headline",
        )
    )
    _, obs_u_id = store.observe(store.observation_payload(reg_u))  # deliberately NOT in LR-016 batch
    assert store.accept(store.acceptance_payload([obs_head_id])).status == "accepted"
    assert obs_u_id  # recorded unadopted legacy observation

    items = [
        {"item_kind": "a001_item", "item_id": "A001-01", "source": "audit/w0.md#L1", "feeds_papers": ["P01-A"]},
        {"item_kind": "a001_item", "item_id": "A001-02", "source": "audit/w0.md#L2", "feeds_papers": ["P01-A"]},
    ]
    blob = _commit_open_items(store, items)

    ok_bytes = b'{"successor_discharge": 1}\n'
    art_ok, ok_grant, ok_file = _make_generic_artefact(store, ok_bytes, "evidence/successor/ok.json")
    art_cand, _, _ = _make_generic_artefact(
        store, b'{"candidate": true}\n', "evidence/successor/cand.json", accept=False
    )
    art_copy_adopted, _, _ = _make_generic_artefact(store, RESULT, "evidence/successor/copy_a.json")
    art_copy_unadopted, _, _ = _make_generic_artefact(store, b'{"unadopted": 1}\n', "evidence/successor/copy_u.json")
    art_rep, _, _ = _make_generic_artefact(store, b'{"replacement": true}\n', "evidence/successor/rep.json")

    def refuse_lr030(payload: dict[str, Any], msg: str) -> None:
        before = _snapshot(store)
        with pytest.raises(IntegrityError, match=msg):
            store.submit("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 0, payload)
        assert _snapshot(store) == before

    # Unknown item, uncommitted list, unregistered artefact, candidate artefact, adopted/unadopted legacy byte copies.
    refuse_lr030(
        _discharge_payload(store, art_ok, item_id="A001-99"),
        "W9 discharge item is not in the open-item list at git_head",
    )
    open_path = store.repo / w9_evidence.LEGACY_OPEN_ITEMS
    open_path.write_text(
        json.dumps(
            {
                "format": w9_evidence.LEGACY_OPEN_ITEMS_FORMAT,
                "items": [{"item_kind": "a001_item", "item_id": "A001-NEW", "source": "x", "feeds_papers": ["P01-A"]}],
            }
        ),
        encoding="utf-8",
    )
    refuse_lr030(
        _discharge_payload(store, art_ok, item_id="A001-NEW"),
        "W9 discharge item is not in the open-item list at git_head",
    )
    open_path.write_text(json.dumps({"format": w9_evidence.LEGACY_OPEN_ITEMS_FORMAT, "items": items}), encoding="utf-8")

    missing_ref = {"id": new_id("artefact"), "record_revision": 1, "content_hash": sha256_hex(ok_bytes)}
    refuse_lr030(_discharge_payload(store, missing_ref), "W9 discharge successor result names no registered artefact")
    refuse_lr030(_discharge_payload(store, art_cand), "W9 discharge successor result is not accepted_for_scope")
    refuse_lr030(
        _discharge_payload(store, art_copy_adopted),
        "W9 discharge successor result matches a recorded legacy observation",
    )
    refuse_lr030(
        _discharge_payload(store, art_copy_unadopted),
        "W9 discharge successor result matches a recorded legacy observation",
    )

    # Propose valid LR-030 -> check G3 at LR-031 -> finish LR-031..LR-032.
    dis = _discharge_payload(store, art_ok, item_id="A001-01")
    _discharge_via_submit(store, dis, open_items_blob=blob, stop_after="LR-030")
    rev_id = dis["reviewer_ref"]["id"]
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 discharge reviewer is the successor result's producer"):
        store.submit(
            "RequestW9AuthorityReview",
            store.actors.analyst,
            rev_id,
            0,
            {
                "subject_record_id": dis["record_id"],
                "reviewer_actor_id": ACTORS["actor-b"],
                "review_questions": ["q", "w9-applicable-fixtures:"],
                "analyst_session": "session-analyst",
            },
        )
    assert _snapshot(store) == before
    assert (
        store.submit(
            "RequestW9AuthorityReview",
            store.actors.analyst,
            rev_id,
            0,
            {
                "subject_record_id": dis["record_id"],
                "reviewer_actor_id": store.actors.reviewer,
                "review_questions": ["q", "w9-applicable-fixtures:"],
                "analyst_session": "session-analyst",
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
                "reviewer_session": "session-reviewer",
                "reviewer_model_metadata": "w9-test-model",
                "context_manifest_sha256": "9" * 64,
            },
        ).status
        == "accepted"
    )

    # At LR-033: wrong open_items_blob refused; missing item from updated list refused.
    dec_id = dis["decision_ref"]["id"]
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 LR-033 requires open_items_blob"):
        store.submit(
            "ProposeW9AuthorityDecision",
            store.actors.analyst,
            dec_id,
            0,
            {"subject_record_id": dis["record_id"], "question": "q", "recommendation": "accept", "consequences": []},
        )
    assert _snapshot(store) == before
    with pytest.raises(IntegrityError, match="W9 open-item list blob differs from the list at git_head"):
        store.submit(
            "ProposeW9AuthorityDecision",
            store.actors.analyst,
            dec_id,
            0,
            {
                "subject_record_id": dis["record_id"],
                "question": "q",
                "recommendation": "accept",
                "consequences": [],
                "fixture_refs": [],
                "open_items_blob": "f" * 40,
            },
        )
    assert _snapshot(store) == before

    # Advance LR-033 cleanly, then test LR-034 refusals.
    assert (
        store.submit(
            "ProposeW9AuthorityDecision",
            store.actors.analyst,
            dec_id,
            0,
            {
                "subject_record_id": dis["record_id"],
                "question": "q",
                "recommendation": "accept",
                "consequences": [],
                "fixture_refs": [],
                "open_items_blob": blob,
            },
        ).status
        == "accepted"
    )

    # 1. Control-root bytes altered before LR-034.
    ok_file.write_bytes(b"corrupted bytes\n")
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 discharge successor result bytes differ from its manifest"):
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        )
    assert _snapshot(store) == before
    ok_file.write_bytes(ok_bytes)

    # 2. Commit-time reread failure on ControlRootArtefactContentReader.read at LR-034.
    orig_art_read = ControlRootArtefactContentReader.read
    art_calls: list[int] = []

    def mutate_on_artefact_read(self: ControlRootArtefactContentReader, *, root_id: str, relative_path: str) -> bytes:
        art_calls.append(1)
        if len(art_calls) == 2:
            return b"altered before commit reread"
        return orig_art_read(self, root_id=root_id, relative_path=relative_path)

    monkeypatch.setattr(ControlRootArtefactContentReader, "read", mutate_on_artefact_read)
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 discharge successor result bytes differ from its manifest"):
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        )
    assert _snapshot(store) == before
    monkeypatch.setattr(ControlRootArtefactContentReader, "read", orig_art_read)

    # 3. Direct G3 defense-in-depth check on LR-034 prepare_resolution.
    tampered_state = deepcopy(_state(store))
    tampered_state["reviews"][rev_id]["reviewer"] = ACTORS["actor-b"]
    generic_view = {
        "streams": {
            art_ok["id"]: {
                "use_authority": "accepted_for_scope",
                "manifest": {
                    **artefact_manifest(),
                    "artefact_id": art_ok["id"],
                    "producer_actor_id": ACTORS["actor-b"],
                    "relative_path": "evidence/successor/ok.json",
                    "size_bytes": len(ok_bytes),
                    "content_sha256": art_ok["content_hash"],
                },
            }
        }
    }
    env_g3 = preparers.Environment(store.runtime.reader, generic_view, store.harness.ledger.control_root, None)
    with pytest.raises(IntegrityError, match="W9 discharge reviewer is the successor result's producer"):
        preparers.prepare_resolution(
            {"decision_id": dec_id, "selected_option": "accept"},
            actor=OWNER,
            now=store.clock(),
            legacy=tampered_state,
            environment=env_g3,
            grant_id=new_id("authority_grant"),
        )

    # 4. Change open-items blob at git_head after LR-033 -> LR-034 refuses.
    _commit_open_items(
        store,
        [
            {"item_kind": "a001_item", "item_id": "A001-01", "source": "audit/w0.md#L1", "feeds_papers": ["P01-A"]},
            {"item_kind": "a001_item", "item_id": "A001-03", "source": "audit/w0.md#L3", "feeds_papers": ["P01-A"]},
        ],
    )
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 open-item list blob differs from the list at git_head"):
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        )
    assert _snapshot(store) == before

    # Restore exact blob at git_head via amending? No, commit exact initial bytes back -> same blob SHA-1!
    restored_blob = _commit_open_items(store, items)
    assert restored_blob == blob

    # 5. Demote / supersede the artefact after LR-033 -> LR-034 refuses.
    sup_cmd = {
        **command(
            command_id=new_id("command"),
            command_type="SupersedeArtefact",
            actor_id=OWNER,
            authority_grant_id=ok_grant,
            expected_stream_version=3,
            payload={
                "artefact_id": art_ok["id"],
                "replacement_artefact_id": art_rep["id"],
                "supersession_reason": "superseded before discharge resolution",
                "supersession_scope": "release:wp6.4",
                "replacement_sha256": art_rep["content_hash"],
                "effective_at": "2026-08-08T21:00:00Z",
                "continuing_consumer_dispositions": ["use replacement"],
            },
            target_stream_id=art_ok["id"],
        ),
        "project_id": store.harness.ledger.project_id,
        "submitted_at": store.harness.service.clock().isoformat().replace("+00:00", "Z"),
    }
    assert store.harness.service.submit(sup_cmd).status == "accepted"
    before = _snapshot(store)
    with pytest.raises(IntegrityError, match="W9 discharge successor result is not accepted_for_scope"):
        store.submit(
            "ResolveW9AuthorityDecision", OWNER, dec_id, 1, {"decision_id": dec_id, "selected_option": "accept"}
        )
    assert _snapshot(store) == before


# --- CLI ars legacy adoption-status (§9, §13) ------------------------------------------------------------------------


def test_cli_legacy_adoption_status_active_suspended_unknown_and_gate6(
    store: W9Store,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``ars legacy adoption-status`` prints active/suspended JSON read-only, exits 1 on unknown, and refuses Gate 6."""
    reg = store.register("results/x.json")
    table = store.membership()
    p_head = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        family="headline",
    )
    p_meta = store.observation_payload(
        reg,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["meta"],
        },
        family="meta",
    )
    _, obs_head_id = store.observe(p_head)
    _, obs_meta_id = store.observe(p_meta)
    assert store.accept(store.acceptance_payload([obs_head_id, obs_meta_id])).status == "accepted"

    adp_susp, _ = _adopt_via_submit(
        store,
        _adoption_payload(
            store,
            store.recorded("legacy_observation", obs_head_id),
            subject={"subject_kind": "families", "family_names": ["headline"]},
        ),
        fixtures=("F-019", "S-017"),
    )
    adp_act, _ = _adopt_via_submit(
        store,
        _adoption_payload(
            store,
            store.recorded("legacy_observation", obs_meta_id),
            subject={"subject_kind": "families", "family_names": ["meta"]},
        ),
        fixtures=("F-019", "S-017"),
    )
    # Suspend adp_susp by re-observing headline while keeping meta active.
    assert store.observe(p_head)[0].status == "accepted"

    bindings: list[dict[str, Any]] = []

    def bind(root: Path, **kwargs: Any) -> Any:
        bindings.append(kwargs)
        return store.harness.ledger, store.harness.schemas, store.harness.authority_resolver

    monkeypatch.setattr(cli, "_verified_ledger", bind)
    control_root = store.harness.ledger.control_root
    before = _tree_bytes(control_root)

    assert cli.main(["legacy", "adoption-status", adp_act["record_id"], "--control-root", str(control_root)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "adoption_id": adp_act["record_id"],
        "status": "active",
        "cause": None,
    }

    assert cli.main(["legacy", "adoption-status", adp_susp["record_id"], "--control-root", str(control_root)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "adoption_id": adp_susp["record_id"],
        "status": "suspended",
        "cause": "later_observation",
    }

    assert cli.main(["legacy", "adoption-status", new_id("scope_definition"), "--control-root", str(control_root)]) == 1
    assert "W9 adoption record not found" in capsys.readouterr().err
    assert _tree_bytes(control_root) == before
    assert bindings == [{"read_only": True}, {"read_only": True}, {"read_only": True}]

    # Gate 6 store refused before binding.
    gate6_dir = tmp_path / "gate6-cli"
    gate6_dir.mkdir()
    _, g6_harness = _store(gate6_dir, store_identity=GATE6)

    def never_bind(root: Path, **kwargs: Any) -> Any:
        raise AssertionError("bound a Gate 6 store")

    monkeypatch.setattr(cli, "_verified_ledger", never_bind)
    g6_root = g6_harness.ledger.control_root
    g6_before = _tree_bytes(g6_root)
    assert cli.main(["legacy", "adoption-status", adp_act["record_id"], "--control-root", str(g6_root)]) == 1
    assert GATE6_REASON_CODE in capsys.readouterr().err
    assert _tree_bytes(g6_root) == g6_before
