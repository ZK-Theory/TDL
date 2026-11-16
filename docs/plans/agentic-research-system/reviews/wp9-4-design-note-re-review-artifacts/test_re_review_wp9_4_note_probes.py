# Research context: docs/plans/agentic-research-system/reviews/wp9-4-design-note-re-review-4629d1fd-2026-11-16.md (P-085)
# Purpose: the WP9.4 design-note re-reviewer's asserting probes, at the note's revision 2 (4629d1fd). Stores are scratch
# stores under tmp_path; papers/ and results/ are read through Git only. A probe whose name contains ``defect`` passes
# while the defect it names is present (in the code at 4629d1fd, or in the note's design as written).
"""Re-review probes for the WP9.4 design note, revision 2, at ``4629d1fd``.

Run from the repository root:

    uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider \
        docs/plans/agentic-research-system/reviews/wp9-4-design-note-re-review-artifacts/
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system.artefacts.authority import (  # noqa: E402
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
)
from research_system.artefacts.runtime import (  # noqa: E402
    ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT,
    ControlRootArtefactContentReader,
)
from research_system.artefacts.use_resolver import ArtefactUseResolver, predicate_reference  # noqa: E402
from research_system.canonical import canonical_bytes, sha256_hex  # noqa: E402
from research_system.errors import ArsError, IntegrityError  # noqa: E402
from research_system.evidence.consumers import ArtefactConsumerContext, ArtefactEvidenceConsumers  # noqa: E402
from research_system.legacy.records import record_content_hash  # noqa: E402
from research_system.legacy.replay import reducers  # noqa: E402
from research_system.legacy.routes import assign_row, w9_row_ref  # noqa: E402
from research_system.projection.replay import replay  # noqa: E402

REVIEWED = "4629d1fd34b33b9c2b02e898225313f335a32ed6"
CODE_BASE = "4312dc63"
ANNEX = REPO_ROOT / "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
W9_SCHEMAS = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "w9"
T0 = "2026-11-16T10:00:00Z"
LATER = datetime(2026, 12, 31, tzinfo=UTC)


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True).stdout


def _tree(prefix: str) -> list[str]:
    raw = _git("ls-tree", "-r", "-z", "--name-only", REVIEWED, prefix)
    return [path for path in raw.decode("utf-8").split("\0") if path]


def _blob(path: str) -> bytes:
    return _git("show", f"{REVIEWED}:{path}")


def _annex_rows() -> dict[str, dict[str, Any]]:
    annex = yaml.safe_load(ANNEX.read_text(encoding="utf-8"))
    return {row["owner_row_id"]: row for row in annex["rows"]}


# --- Currency ---------------------------------------------------------------------------------------------------------


def test_reviewed_commit_changes_only_the_note_and_no_code_since_the_code_base() -> None:
    """The brief's two diffs: rev 1 to rev 2 is one file, and no code changed after the note's base."""
    assert _git("diff", "--name-only", "3c10de9a", REVIEWED).decode().split() == [
        "docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md"
    ]
    assert (
        _git("diff", "--name-only", CODE_BASE, REVIEWED, "--", "research_system", ".research-system", "tools", "tests")
        == b""
    )
    # The probes import the working tree, so it must be the reviewed commit's code.
    assert _git("diff", "--name-only", REVIEWED, "--", "research_system", ".research-system") == b""


# --- Claims 1, 2 and 12: the artefact claim path, end to end on a scratch store ---------------------------------------

LEGACY_BYTES = b'{"escape_rate": 0.0558, "wilson_ci": [0.0508, 0.0612], "n": 7453}\n'  # fixture bytes, not a result
LEGACY_SHA256 = sha256_hex(LEGACY_BYTES)
# A byte copy of a legacy result, under the control root, at a results-like path. Nothing in the flow reads this path.
COPY_PATH = "results/legacy_copy/escape_wilson_ci_2026-05-16.json"
SCOPE_ID = "release:wp9-4-re-review"
TASK_ID = "tsk_019fe47a-2001-7000-8000-000000002001"
CLAIM_ART = "art_019fe47a-2000-7000-8000-000000002000"
MS_ART = "art_019fe47a-3000-7000-8000-000000003000"
IDS = {
    CLAIM_ART: ("rev_019fe47a-2005-7000-8000-000000002005", "arec_019fe47a-2007-7000-8000-000000002007"),
    MS_ART: ("rev_019fe47a-3005-7000-8000-000000003005", "arec_019fe47a-3007-7000-8000-000000003007"),
}
CLAIM_DECISION_ID = "dec_019fe47a-2013-7000-8000-000000002013"
# The accepted flow (test_artefact_authority_commands) uses one review ID for the artefact's governing review and the
# Decision's satisfied review: _claim_promotion_binding requires considered_review_ids to equal the governing set.
DECISION_REVIEW_ID = IDS[CLAIM_ART][0]


class _GoverningReviews:
    """Governing scientific reviews of the fixture bytes, by evidence ID (the shape the accepted resolver returns)."""

    independence_grade = "I2"

    def resolve(self, reference_id: str, *, project_id: str, evaluation_time: datetime) -> GoverningEvidenceResolution:
        from tests.research_system.factories import ACTORS

        review_id = next(review for review, evidence in IDS.values() if evidence == reference_id)
        record = {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": project_id,
            "review_id": review_id,
            "subject_sha256": LEGACY_SHA256,
            "reviewer_actor_id": ACTORS["actor-a"],
            "eligible": True,
            "related": False,
            "independence_grade": self.independence_grade,
            "status": "active",
        }
        return GoverningEvidenceResolution(reference_id, sha256_hex(canonical_bytes(record)), record)


def _manifest(artefact_id: str) -> dict[str, Any]:
    from tests.research_system.integration.test_artefact_authority_commands import artefact_manifest

    manifest = deepcopy(artefact_manifest())
    manifest.update(
        artefact_id=artefact_id,
        task_id=TASK_ID,
        relative_path=COPY_PATH,
        size_bytes=len(LEGACY_BYTES),
        content_sha256=LEGACY_SHA256,
    )
    manifest["authority"]["accepted_scope"] = SCOPE_ID
    return manifest


def _register_and_review(harness: Any, artefact_id: str, prefix: str) -> str:
    from tests.research_system.factories import ACTORS, activate_lifecycle_grant
    from tests.research_system.integration.test_artefact_authority_commands import command

    review_id, evidence_id = IDS[artefact_id]
    grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=artefact_id,
        command_types=("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
    )
    register = command(
        command_id=f"cmd_019fe47a-{prefix}10-7000-8000-00000000{prefix}10",
        command_type="RegisterArtefact",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=0,
        payload={"new_artefact_id": artefact_id, "manifest": _manifest(artefact_id)},
        target_stream_id=artefact_id,
    )
    review = command(
        command_id=f"cmd_019fe47a-{prefix}11-7000-8000-00000000{prefix}11",
        command_type="RecordScientificReview",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=1,
        payload={
            "artefact_id": artefact_id,
            "review_id": review_id,
            "subject_sha256": LEGACY_SHA256,
            "scientific_review": "approved",
            "evidence_refs": [evidence_id],
        },
        target_stream_id=artefact_id,
    )
    assert harness.service.submit(register).status == "accepted"
    assert harness.service.submit(review).status == "accepted"
    return grant


def _claim_promotion_decision(harness: Any) -> None:
    """The owner's claim_promotion Decision on the claim artefact's review set, as the accepted flow requires."""
    from tests.research_system.factories import ACTORS, activate_lifecycle_grant
    from tests.research_system.integration.test_wp6_1_c3_completion_review_decision import ACTOR_C
    from tests.research_system.integration.test_wp6_1_task_scope_lifecycle import _command

    review_id, evidence_id = IDS[CLAIM_ART]
    proposer = activate_lifecycle_grant(
        harness,
        subject_kind="decision",
        subject_id=CLAIM_DECISION_ID,
        actor_id=ACTOR_C,
        allowed_actor_classes=("agent",),
        command_types=("ProposeDecision", "RequestDecisionReview"),
        grant_id="agr_019fe47a-2162-7000-8000-000000002162",
    )
    for index, (command_type, version, payload) in enumerate(
        (
            (
                "ProposeDecision",
                0,
                {
                    "new_decision_id": CLAIM_DECISION_ID,
                    "question": "May the exact claim evidence be promoted?",
                    "recommendation": "approve",
                    "options": ["approve", "deny"],
                    "decision_revision": 1,
                    "decision_kind": "claim_promotion",
                    "governing_evidence_refs": [evidence_id],
                    "affected_task_ids": [],
                    "affected_claim_ids": [],
                    "required_authority": "Stephen",
                    "expires_at": "2026-08-12T00:00:00Z",
                    "review_date": "2026-08-10T00:00:00Z",
                    "consequences": ["only the exact accepted scope may consume the evidence"],
                },
            ),
            (
                "RequestDecisionReview",
                1,
                {
                    "decision_id": CLAIM_DECISION_ID,
                    "decision_revision": 1,
                    "review_requirements": ["independent exact-subject review"],
                    "governing_evidence_refs": [evidence_id],
                },
            ),
        )
    ):
        envelope = _command(
            f"cmd_019fe47a-206{index}-7000-8000-00000000206{index}", command_type, CLAIM_DECISION_ID, version, payload
        )
        envelope["actor_id"], envelope["authority_grant_id"] = ACTOR_C, proposer
        assert harness.service.submit(envelope).status == "accepted"
    decision_hash = sha256_hex(
        canonical_bytes(
            replay(
                tuple(harness.ledger.iter_events()),
                schema_registry=harness.schemas,
                authority_state_validator=harness.authority_resolver.validate_replayed_administration_state,
            )["streams"][CLAIM_DECISION_ID]
        )
    )
    owner = activate_lifecycle_grant(
        harness,
        subject_kind="review",
        subject_id=DECISION_REVIEW_ID,
        command_types=("RequestReview", "AssignReview", "SatisfyReview"),
        grant_id="agr_019fe47a-2164-7000-8000-000000002164",
    )
    reviewer = activate_lifecycle_grant(
        harness,
        subject_kind="review",
        subject_id=DECISION_REVIEW_ID,
        actor_id=ACTORS["actor-b"],
        allowed_actor_classes=("agent",),
        command_types=("StartReview", "RecordReviewVerdict"),
        grant_id="agr_019fe47a-2165-7000-8000-000000002165",
    )
    steps = [
        (
            "RequestReview",
            ACTORS["actor-a"],
            owner,
            {
                "new_review_id": DECISION_REVIEW_ID,
                "review_type": "software",
                "subject_ids": [CLAIM_DECISION_ID],
                "subject_hashes": [decision_hash],
                "governing_refs": ["P-005"],
                "review_questions": ["Does the decision bind the exact governing review set?"],
                "required_evidence_refs": [evidence_id],
                "required_lanes": ["scientific", "provenance"],
                "reviewer_capability": ["claim-promotion"],
                "required_independence_grade": "independent_exact_subject",
                "visibility_policy": "owner_and_reviewer",
                "allowed_verdicts": ["accept_exact_subject", "rework_required"],
                "satisfaction_authority": "owner",
                "deadline": "2026-08-11T00:00:00Z",
                "escalation_rule": "rework on any binding mismatch",
            },
        ),
        (
            "AssignReview",
            ACTORS["actor-a"],
            owner,
            {
                "review_id": DECISION_REVIEW_ID,
                "reviewer_actor_id": ACTORS["actor-b"],
                "computed_independence_grade": "I2",
                "independence_evidence_refs": ["evidence:independent"],
            },
        ),
        (
            "StartReview",
            ACTORS["actor-b"],
            reviewer,
            {
                "review_id": DECISION_REVIEW_ID,
                "unchanged_subject_sha256": decision_hash,
                "visibility_policy": "owner_and_reviewer",
            },
        ),
        (
            "RecordReviewVerdict",
            ACTORS["actor-b"],
            reviewer,
            {
                "review_id": DECISION_REVIEW_ID,
                "verdict": "approve",
                "findings": [],
                "reviewer_actor_id": ACTORS["actor-b"],
                "required_evidence_refs": [evidence_id],
                "limitations": [],
                "conditions": [],
                "reviewer_profile": "independent-reviewer",
                "reviewer_session": "session:p005",
                "reviewer_model_metadata": "model:independent",
                "context_manifest_id": "ctx_019fe47a-1004-7000-8000-000000001004",
                "context_manifest_sha256": "a" * 64,
                "unchanged_subject_sha256": decision_hash,
                "producing_attempt_id": "att_019fe47a-1003-7000-8000-000000001003",
                "trace_visibility_evidence_refs": ["evidence:trace"],
                "computed_independence_grade": "I2",
            },
        ),
        (
            "SatisfyReview",
            ACTORS["actor-a"],
            owner,
            {
                "review_id": DECISION_REVIEW_ID,
                "prior_review_state": "verdict_recorded",
                "policy_evaluation_refs": ["policy-evaluation:p005"],
                "satisfaction_gate": "claim-promotion",
            },
        ),
    ]
    for offset, (command_type, actor, grant, payload) in enumerate(steps):
        envelope = _command(
            f"cmd_019fe47a-217{offset}-7000-8000-00000000217{offset}", command_type, DECISION_REVIEW_ID, offset, payload
        )
        envelope["actor_id"], envelope["authority_grant_id"] = actor, grant
        assert harness.service.submit(envelope).status == "accepted"
    resolver_grant = activate_lifecycle_grant(
        harness,
        subject_kind="decision",
        subject_id=CLAIM_DECISION_ID,
        command_types=("ResolveDecision",),
        grant_id="agr_019fe47a-2180-7000-8000-000000002180",
    )
    resolve = _command(
        "cmd_019fe47a-2080-7000-8000-000000002080",
        "ResolveDecision",
        CLAIM_DECISION_ID,
        2,
        {
            "decision_id": CLAIM_DECISION_ID,
            "selected_option": "approve",
            "effective_scope": f"claim_promotion:{SCOPE_ID}",
            "effective_at": "2026-08-08T19:00:00Z",
            "decision_revision": 1,
            "deciding_actor_id": ACTORS["actor-a"],
            "decision_authority_grant_id": resolver_grant,
            "governing_evidence_refs": [evidence_id],
            "considered_review_ids": [review_id],
            "permitted_commands": ["SetArtefactUseAuthority"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": ["subject or review change"],
        },
    )
    resolve["actor_id"], resolve["authority_grant_id"] = ACTORS["actor-a"], resolver_grant
    receipt = harness.service.submit(resolve)
    assert receipt.status == "accepted", receipt


def _set_use_authority(
    harness: Any, artefact_id: str, grant: str, kind: str, extra_refs: list[str], prefix: str
) -> Any:
    from tests.research_system.factories import ACTORS
    from tests.research_system.integration.test_artefact_authority_commands import command

    contract = ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load()
    predicate, predicate_sha256 = contract.predicate_for(kind)
    review_id, evidence_id = IDS[artefact_id]
    use = command(
        command_id=f"cmd_019fe47a-{prefix}81-7000-8000-00000000{prefix}81",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=2,
        payload={
            "artefact_id": artefact_id,
            "use_authority": "accepted_for_scope",
            "subject_sha256": LEGACY_SHA256,
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]), str(predicate["predicate_version"]), predicate_sha256
            ),
            "evidence_refs": [review_id, evidence_id, *extra_refs],
        },
        target_stream_id=artefact_id,
    )
    harness.service.clock = lambda: datetime.fromisoformat(use["submitted_at"].replace("Z", "+00:00"))
    return harness.service.submit(use)


@pytest.fixture
def promoted(tmp_path: Path) -> dict[str, Any]:
    """A scratch store holding two byte copies of one fixture 'legacy result', promoted for claim and for manuscript."""
    from tests.research_system.factories import control_plane

    base = control_plane(tmp_path)
    harness = replace(
        base,
        service=base.authority_service,
        ledger=base.authority_ledger,
        objects=base.authority_objects,
        receipts=base.authority_receipts,
    )
    harness.service.governing_evidence_resolver = _GoverningReviews()
    control_root = harness.ledger.root if hasattr(harness.ledger, "root") else tmp_path / ".control.authority"
    copy = Path(control_root) / COPY_PATH
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_bytes(LEGACY_BYTES)
    claim_grant = _register_and_review(harness, CLAIM_ART, "20")
    ms_grant = _register_and_review(harness, MS_ART, "30")
    _claim_promotion_decision(harness)
    claim_use = _set_use_authority(harness, CLAIM_ART, claim_grant, "claim_evidence", [CLAIM_DECISION_ID], "20")
    manuscript_use = _set_use_authority(harness, MS_ART, ms_grant, "manuscript_evidence", [], "30")
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT),
        governing_evidence=_GoverningReviews(),
        content_reader=ControlRootArtefactContentReader(Path(control_root)),
        authority_state_validator=harness.authority_resolver.validate_replayed_administration_state,
    )
    return {
        "harness": harness,
        "consumers": ArtefactEvidenceConsumers(resolver),
        "claim_use": claim_use,
        "manuscript_use": manuscript_use,
        "control_root": Path(control_root),
    }


def _context(artefact_id: str) -> ArtefactConsumerContext:
    return ArtefactConsumerContext(
        artefact_id=artefact_id,
        exact_content_sha256=LEGACY_SHA256,
        project_id=__import__("tests.research_system.factories", fromlist=["PROJECT_ID"]).PROJECT_ID,
        task_id=TASK_ID,
        scope_id=SCOPE_ID,
        evaluation_time=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
    )


def test_claim1_defect_a_legacy_byte_copy_is_registered_promoted_and_resolved_as_claim_evidence(promoted) -> None:
    """Claim 1 holds: no step from RegisterArtefact to resolve_for_claim reads the artefact's path for legacy status, and
    the only content check is that the bytes equal the registered hash (the copy passes it by construction)."""
    assert promoted["claim_use"].status == "accepted", promoted["claim_use"]
    resolved = promoted["consumers"].resolve_for_claim(_context(CLAIM_ART), consumer_id="rm03_claim_assessment")
    assert resolved.exact_content_sha256 == LEGACY_SHA256
    assert resolved.decision_id == CLAIM_DECISION_ID
    assert (promoted["control_root"] / COPY_PATH).read_bytes() == LEGACY_BYTES


def test_claim12_defect_manuscript_promotion_needs_no_claim_promotion_decision(promoted) -> None:
    """Claim 12 fails: accepted_for_scope under the manuscript predicate binds no Decision at all
    (``_claim_promotion_binding`` returns [] for any predicate but claim_evidence), and resolve_for_manuscript then
    resolves the same legacy bytes. §4.2's and §4.4's 'needs ... a claim_promotion Decision' holds for the claim
    predicate only."""
    assert promoted["manuscript_use"].status == "accepted", promoted["manuscript_use"]
    resolved = promoted["consumers"].resolve_for_manuscript(_context(MS_ART), consumer_id="rm03_brief_manuscript")
    assert resolved.exact_content_sha256 == LEGACY_SHA256
    assert resolved.decision_id is None
    state = replay(
        tuple(promoted["harness"].ledger.iter_events()),
        schema_registry=promoted["harness"].schemas,
        authority_state_validator=promoted["harness"].authority_resolver.validate_replayed_administration_state,
    )
    # A discharge (LR-030, §8) checks only this field, outside resolve_for_*: the byte copy satisfies it.
    assert state["streams"][MS_ART]["use_authority"] == "accepted_for_scope"
    assert state["streams"][CLAIM_ART]["use_authority"] == "accepted_for_scope"


def test_claim1_one_use_authority_binds_one_consumer_predicate(promoted) -> None:
    """resolve_for_manuscript on the claim-promoted copy is refused for its predicate binding, never for its content."""
    with pytest.raises(ArsError, match="predicate"):
        promoted["consumers"].resolve_for_manuscript(_context(CLAIM_ART), consumer_id="rm03_brief_manuscript")


# --- Claim 3: the stale rule -------------------------------------------------------------------------------------------


def _observation(record_id: str, families: list[str], blob: str) -> dict[str, Any]:
    record = {
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
    record["content_hash"] = record_content_hash(record)
    return record


def _observe(monkeypatch: pytest.MonkeyPatch, state: dict[str, Any], record: dict[str, Any]) -> None:
    monkeypatch.setattr(reducers, "_check_observation", lambda *args: "obj_reg")
    reducers.reduce_record(state, "LR-015", [{"payload": record}], {})


def _note_family_suspended(state: dict[str, Any], observation: str, adopted: set[str]) -> bool:
    """§7 cause 1 for a family adoption, revision 2: a later observation naming an adopted family, or stale."""
    history = state["observations_by_registration"]["obj_reg"]
    later = history[history.index(observation) + 1 :]
    names = state["records"]["legacy_observation"]
    return observation in state["stale_observations"] or any(
        set(names[other]["selector"]["family_names"]) & adopted for other in later
    )


def test_claim3_holds_the_first_reviews_case_now_suspends(monkeypatch: pytest.MonkeyPatch) -> None:
    state = reducers.new_legacy_state()
    _observe(monkeypatch, state, _observation("obj_o1", ["a"], "a" * 40))
    _observe(monkeypatch, state, _observation("obj_o2", ["b"], "b" * 40))
    assert _note_family_suspended(state, "obj_o1", {"a"}) is True


def test_claim3_defect_a_source_edit_with_no_reobservation_leaves_the_adoption_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """'No case leaves an adoption active on bytes that no longer exist' holds only over recorded observations. Replay
    marks stale only from a later recorded observation, so between an edit and its re-observation the projection is
    active, and §9 returns no observed blob for a family adoption that a guard could re-check."""
    state = reducers.new_legacy_state()
    _observe(monkeypatch, state, _observation("obj_o1", ["a"], "a" * 40))
    # The file's blob is now "c"*40 in Git; nothing is recorded.
    assert state["stale_observations"] == []
    assert _note_family_suspended(state, "obj_o1", {"a"}) is False


# --- Claim 4: review_id_for and the fail-open reads ---------------------------------------------------------------------


def test_claim4_holds_every_read_of_the_two_tables_is_a_listed_site() -> None:
    """Every read of _REQUEST_REVIEW_FIELD and _FAMILY_REVIEW_FIELD in production code, by file and line."""
    hits: set[tuple[str, int]] = set()
    for path in (REPO_ROOT / "research_system").rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"_(REQUEST|FAMILY)_REVIEW_FIELD\b", line) and not re.match(
                r"^_(REQUEST|FAMILY)_REVIEW_FIELD =", line
            ):
                hits.add((path.relative_to(REPO_ROOT).as_posix(), number))
    assert hits == {
        ("research_system/legacy/replay/reducers.py", 797),
        ("research_system/legacy/replay/reducers.py", 965),
        ("research_system/legacy/replay/reducers.py", 1092),
        ("research_system/legacy/preparers.py", 389),
        ("research_system/legacy/preparers.py", 512),
    }
    # The 'no review' default is then used at reducers 966-969, 1093, 1118 and preparers 521; §5.2 lists each.
    source = (REPO_ROOT / "research_system/legacy/replay/reducers.py").read_text(encoding="utf-8").splitlines()
    assert "review_field is None" in source[1092]
    assert source[1117].strip().startswith("if review_field and not review_satisfied")


def test_claim8_defect_review_id_for_at_the_decision_proposal_refuses_lr024_before_its_review_can_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§5.2 puts review_id_for at :965-969 for every adoption Decision proposal. LR-024 (eligibility) is a Decision
    proposal on the adoption proposal, and LR-026 cannot open the derived review until LR-025 resolves. Modelled by
    giving the adoption kind a review entry (what review_id_for returns) and running the generic check at LR-024."""
    record = {
        "schema_id": "ars://legacy/legacy-adoption-decision",
        "record_id": "obj_adoption",
        "derived_review": {"id": "rev_derived"},
        "eligibility_decision": {"id": "dec_eligibility"},
    }
    record["content_hash"] = record_content_hash(record)
    state = reducers.new_legacy_state()
    state["proposals"]["obj_adoption"] = {
        "kind": "legacy_adoption_decision",
        "record": record,
        "content_hash": record["content_hash"],
        "recorded": False,
        "actor_id": "act_analyst",
        "lapse_at": LATER,
    }
    monkeypatch.setitem(reducers._FAMILY_REVIEW_FIELD, "legacy_adoption_decision", "derived_review")
    monkeypatch.setitem(reducers._DECISION_PROPOSAL_FIELD, "LR-024", "eligibility_decision")
    payload = {
        "governing_evidence_refs": [
            "W9:LR-024",
            "w9-subject:obj_adoption",
            "w9-subject-sha256:" + record["content_hash"],
        ],
        "new_decision_id": "dec_eligibility",
        "decision_revision": 1,
        "decision_kind": "migration_authority",
        "options": ["accept", "reject"],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "review_date": T0,
        "expires_at": "2026-12-16T10:00:00Z",
    }
    with pytest.raises(IntegrityError, match="no satisfied review on the current hash"):
        reducers._check_decision_proposal(state, "LR-024", {"occurred_at": T0}, payload)


# --- Claim 6: the gate sites --------------------------------------------------------------------------------------------


def test_claim6_the_ten_gate_sites_are_where_section_5_1_says() -> None:
    source = (REPO_ROOT / "research_system/legacy/replay/reducers.py").read_text(encoding="utf-8").splitlines()
    lines = [n for n, line in enumerate(source, 1) if "row_id in WP9_3_ROWS" in line]
    assert lines == [703, 719, 737, 847, 908, 991, 1025, 1138, 1179, 1387]
    # 1387 gates the stale-list update too: the stale rule of §7 depends on LR-015 staying a gated row.
    assert "registration_id is not None" in source[1403]


# --- Claim 7: fixture entries after the three subject refs ---------------------------------------------------------------


def _fixture_refs(row: str) -> list[str]:
    return [
        f"W9:{row}",
        "w9-subject:obj_x",
        "w9-subject-sha256:" + "0" * 64,
        "w9-fixture:F-018:rev_x",
        "w9-fixture:S-017:art_y",
        "w9-open-items-blob:" + "1" * 40,
    ]


def test_claim7_holds_row_assignment_and_the_resolution_rewrite_carry_fixture_entries() -> None:
    assert w9_row_ref(_fixture_refs("LR-028")) == "LR-028"
    event = {
        "event_type": "DecisionProposed",
        "command_type": "ProposeW9AuthorityDecision",
        "payload": {"governing_evidence_refs": _fixture_refs("LR-028")},
    }
    assert assign_row([event], {}) == "LR-028"
    rewritten = ["W9:LR-029", *_fixture_refs("LR-028")[1:]]
    assert w9_row_ref(rewritten) == "LR-029" and rewritten[3:] == _fixture_refs("LR-028")[3:]


def test_claim7_holds_wp9_3_rows_still_refuse_a_fourth_ref() -> None:
    with pytest.raises(IntegrityError, match="does not encode its subject"):
        reducers._check_decision_proposal(
            reducers.new_legacy_state(),
            "LR-019",
            {"occurred_at": T0},
            {"governing_evidence_refs": _fixture_refs("LR-019")},
        )


def test_claim7_a_fixture_prefix_never_reads_as_a_row_ref() -> None:
    """w9_row_ref refuses any extra 'W9:' entry; 'w9-fixture:' is lower case, so a fixture ID cannot collide."""
    with pytest.raises(IntegrityError, match="exactly one W9 row"):
        w9_row_ref(["W9:LR-028", "W9:F-018"])


def test_claim7_holds_the_unconditional_fixture_sets_equal_the_annex() -> None:
    rows = _annex_rows()
    note = {
        "LR-029": {"S-017"},
        "LR-034": set(),
        "LR-044": {"F-018", "F-023", "F-037"},
        "LR-049": set(),
        "LR-054": {"F-006", "F-019", "F-023", "F-037"},
        "LR-055": {"F-006", "F-019", "F-037"},
    }
    annex = {row: {f["fixture_id"] for f in rows[row]["pilot_promotion_fixtures"] if f["when"] is None} for row in note}
    assert annex == note


def test_owner_point_l_defect_lr029_conditional_f019_is_decidable_from_the_record_yet_left_optional() -> None:
    """F-019's condition on LR-029 is 'the intended use is evidence for a claim', which §6.2's use string decides
    exactly. Under §5.4's 'listed counts as applicable', a claim-use adoption that omits F-019 is admitted."""
    conditional = {f["fixture_id"]: f["when"] for f in _annex_rows()["LR-029"]["pilot_promotion_fixtures"] if f["when"]}
    assert conditional["F-019"] == "the intended use is evidence for a claim"


def test_owner_point_l_defect_decision_fixture_refs_are_outside_the_reviewed_hash() -> None:
    """LR-020's fixture list is inside the record the reviewer approves (P-084 i-3's premise). A WP9.4 record has no
    fixture field, so §5.4's entries are chosen at the Decision proposal, after the review, by the analyst."""
    acceptance = json.loads((W9_SCHEMAS / "legacy-closed-reference-acceptance.schema.json").read_text(encoding="utf-8"))
    assert "pilot_promotion" in json.dumps(acceptance)
    for kind in (
        "adoption-decision",
        "discharge-relation",
        "source-inventory",
        "transition-mapping",
        "ownership-transitioned",
    ):
        schema = json.loads((W9_SCHEMAS / f"legacy-{kind}.schema.json").read_text(encoding="utf-8"))
        assert "pilot_promotion" not in json.dumps(schema) and "fixture" not in json.dumps(schema)
    assert _annex_rows()["LR-028"]["eligible_actor"] == "migration_analyst"


# --- Claim 8: the eligibility encoding ---------------------------------------------------------------------------------


def test_claim8_defect_the_verdict_session_is_bound_to_no_eligible_session() -> None:
    """Replay checks only that the verdict's reviewer_session differs from the request's sessions. §5.5 and §6.5 add a
    profile and model-metadata check at LR-027 but no session check, so any other session of the named reviewer
    records the adoption's verdict. reviewer_model_metadata is one string; §5.5 binds two values to it."""
    review = {
        "reviewer": "act_reviewer",
        "allowed_verdicts": ["approve"],
        "subject": ("obj_adoption", "h" * 64),
        "required_evidence_refs": ["w9-analyst-session:s-analyst"],
        "requested_at": T0,
        "sessions": ["s-analyst"],
    }
    state = reducers.new_legacy_state()
    state["proposals"]["obj_adoption"] = {"kind": "k", "recorded": False, "lapse_at": LATER, "content_hash": "h" * 64}
    from research_system.legacy.records import review_attempt_id, review_context_manifest_id

    payload = {
        "review_id": "rev_derived",
        "reviewer_actor_id": "act_reviewer",
        "verdict": "approve",
        "unchanged_subject_sha256": "h" * 64,
        "conditions": [],
        "required_evidence_refs": ["w9-analyst-session:s-analyst"],
        "reviewer_profile": reducers.REVIEWER_PROFILE,
        "context_manifest_id": review_context_manifest_id("rev_derived", T0),
        "producing_attempt_id": review_attempt_id("rev_derived", T0),
        "trace_visibility_evidence_refs": ["h" * 64],
        "computed_independence_grade": "independent",
        "reviewer_session": "some-session-stephen-never-named",
    }
    event = {"actor_id": "act_reviewer", "occurred_at": T0, "stream_id": "rev_derived", "stream_version": 2}
    reducers._check_verdict(state, review, event, payload)  # no raise
    schema = json.loads(
        (REPO_ROOT / ".research-system/schemas/core/events/review_verdict_recorded.schema.json").read_text(
            encoding="utf-8"
        )
    )
    props = schema["$defs"]["payload"]["oneOf"][0]["properties"]
    assert props["reviewer_model_metadata"]["type"] == "string"


def test_claim8_the_preparer_payloads_have_no_field_for_the_new_refs() -> None:
    """The Decision-proposal and review-request preparers take fixed key sets. §5.4's fixture entries, §5.5's eligibility
    refs and §8's open-items blob have no field to arrive in, and a proposal kind maps to one Decision row."""
    source = (REPO_ROOT / "research_system/legacy/preparers.py").read_text(encoding="utf-8")
    assert '{"subject_record_id", "question", "recommendation", "consequences"}' in source
    assert 'row = DECISION_ROWS.get(proposal["kind"])' in source


# --- Claim 9 and owner point F: the task-input key ----------------------------------------------------------------------


def test_owner_point_f_defect_a_task_carries_no_field_named_for_the_use_key() -> None:
    """§6.2 keys a task-input use by a pre-registration ID or plan task key that 'nothing in the store resolves'. The
    Task definition has no such field, so J's guard has nothing to compare it with: one task-input adoption is
    admissible to every Task that names it, the M-7 defect moved to the guard."""
    schema = json.loads(
        (REPO_ROOT / ".research-system/schemas/core/commands/create_task.schema.json").read_text(encoding="utf-8")
    )
    fields = set(schema["$defs"]["task_definition"]["properties"])
    assert not {name for name in fields if "pre_registration" in name or "plan_key" in name or "use" in name}
    assert "aliases" in fields  # a candidate carrier, which the note does not name


# --- Claim 10 and owner point K ------------------------------------------------------------------------------------------


def test_claim10_holds_no_member_role_and_w9_reads_the_root_as_the_one_directory_registration() -> None:
    schema = json.loads((W9_SCHEMAS / "legacy-path-registration.schema.json").read_text(encoding="utf-8"))
    roles = set(schema["properties"]["role"]["enum"])
    assert not {role for role in roles if "member" in role or "draft" in role}
    design = (
        REPO_ROOT / "docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md"
    ).read_text(encoding="utf-8")
    # W9 §3.1 states the reading the note does not weigh: members are listed by the root's inventory, not registered.
    assert "A root is the one directory registration W9 allows" in design
    assert "the root's full-path inventory lists every file under it" in design
    assert "Registration is per exact file, never by glob" in design


# --- Claim 5: the §11.1 rule on the real roots, read through Git ------------------------------------------------------------

_TOKEN = re.compile(r"[^\s`'\"()\[\]<>,;|*]+")


def _strings(node: Any):
    if isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)
    elif isinstance(node, str):
        yield node


class _Rule:
    """§11.1 as written, with one tokenizer the note does not fix (whitespace and Markdown/code punctuation)."""

    def __init__(self) -> None:
        self.results = set(_tree("results/"))
        self.by_base: dict[str, list[str]] = defaultdict(list)
        for path in self.results:
            self.by_base[path.rsplit("/", 1)[-1]].append(path)

    def texts(self, path: str) -> list[str]:
        text = _blob(path).decode("utf-8")  # step 1; every file in both roots decodes
        out = [text]
        if path.endswith(".json"):
            out += list(_strings(json.loads(text)))
        return [re.sub(r"/+", "/", t.replace("\\", "/")) for t in out]  # step 2

    def classify(self, raw: str) -> tuple[str, str] | None:
        token = raw.rstrip(".:")
        base = token.rsplit("/", 1)[-1]
        if not (base in self.by_base or "results/" in token):  # step 3
            return None
        for registered in self.results:
            if token == registered or token.endswith("/" + registered):
                return ("cited", registered)
        if "/" not in token:
            return ("cited", self.by_base[base][0]) if len(self.by_base[base]) == 1 else ("ambiguous", token)
        if "results/" in token:
            return ("unregistered", token)
        return ("unclassified", token)

    def run(self, root: str, *, drafts_only: bool = False, split=_TOKEN.finditer) -> dict[str, set[str]]:
        found: dict[str, set[str]] = defaultdict(set)
        for path in _tree(root):
            if drafts_only and "/drafts/" not in path:
                continue
            for text in self.texts(path):
                for match in split(text):
                    token = match.group(0) if hasattr(match, "group") else match
                    verdict = self.classify(token)
                    if verdict:
                        found[verdict[0]].add(verdict[1])
        return found


@pytest.fixture(scope="module")
def rule() -> _Rule:
    return _Rule()


ROOTS = ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/")


def test_claim5_the_rule_runs_on_both_roots_and_leaves_nothing_unclassified(rule: _Rule) -> None:
    counts = {root: {k: len(v) for k, v in rule.run(root).items()} for root in ROOTS}
    assert counts["papers/P01-A-JRSSA/"]["cited"] == 47 and counts["papers/P01-B-JRSSB/"]["cited"] == 10
    assert counts["papers/P01-A-JRSSA/"]["ambiguous"] == 4 and counts["papers/P01-B-JRSSB/"]["ambiguous"] == 2
    assert counts["papers/P01-A-JRSSA/"]["unregistered"] == 36 and counts["papers/P01-B-JRSSB/"]["unregistered"] == 28
    assert all("unclassified" not in c for c in counts.values())


def test_claim5_defect_most_unregistered_entries_name_no_file_so_no_registration_can_clear_them(rule: _Rule) -> None:
    """A directory, a filename stem or a template is an 'unregistered' blocker under §11.1, and registration is per
    exact file (W9 §3.1), so the blocker can be cleared only by editing a registered legacy file."""
    tree_dirs = {path.rsplit("/", 1)[0] + "/" for path in rule.results} | {
        "/".join(path.split("/")[:i]) + "/" for path in rule.results for i in range(1, path.count("/") + 1)
    }
    for root, at_least in (("papers/P01-A-JRSSA/", 29), ("papers/P01-B-JRSSB/", 28)):
        unregistered = rule.run(root)["unregistered"]
        not_a_file = {
            t for t in unregistered if t.endswith("/") or (t + "/") in tree_dirs or not re.search(r"\.[a-z0-9]+$", t)
        }
        assert len(not_a_file) >= at_least
    assert "results/trajectory_tda_bhps/post_audit/" in rule.run("papers/P01-A-JRSSA/")["unregistered"]


def test_claim5_defect_drafts_only_scope_still_blocks_both_roots(rule: _Rule) -> None:
    a = rule.run("papers/P01-A-JRSSA/", drafts_only=True)
    b = rule.run("papers/P01-B-JRSSB/", drafts_only=True)
    assert "results/trajectory_tda_bhps/post_audit/" in a["unregistered"]  # supplement-S0 and compute_table1_effects.py
    assert {"04_nulls_wasserstein_w2_20260407.json", "05_analysis.json"} <= a["ambiguous"]
    assert b["unregistered"] == {
        "results/trajectory_tda_bhps/post_audit/",
        "results/trajectory_tda_integration/post_audit/",
    }


def test_claim5_defect_the_cited_set_depends_on_a_tokenizer_the_note_does_not_fix(rule: _Rule) -> None:
    """Whitespace tokens keep backticks and Markdown table pipes attached, so 30 of P01-A's 47 cited files and 9 of
    P01-B's 10 vanish. Both readings satisfy §11.1's words ('take every token')."""
    for root, punct, ws in (("papers/P01-A-JRSSA/", 47, 17), ("papers/P01-B-JRSSB/", 10, 1)):
        assert len(rule.run(root)["cited"]) == punct
        assert len(rule.run(root, split=lambda text: text.split())["cited"]) == ws


def test_claim5_defect_a_bare_untracked_result_name_is_dropped_silently(rule: _Rule) -> None:
    """'Nothing is dropped silently' fails for a bare basename that no registered result has: step 3 never takes it."""
    text = "\n".join(rule.texts("papers/P01-A-JRSSA/notes/2026-05-01-reviewer-response-plan.md"))
    assert "regime_labels.npy" in text
    assert "regime_labels.npy" not in rule.by_base
    assert rule.classify("regime_labels.npy") is None


def test_claim5_defect_a_cited_npy_has_no_membership_table_so_it_is_always_a_blocker(rule: _Rule) -> None:
    """§11.1's cited-family set projects only through membership tables; a cited whole-file result (an embedding) is
    a blocker entry however it is adopted, though §6.1 adopts it whole."""
    cited = rule.run("papers/P01-A-JRSSA/")["cited"]
    assert {
        "results/trajectory_tda_integration/embeddings.npy",
        "results/trajectory_tda_integration/embeddings_umap16.npy",
    } <= cited


def test_owner_point_i_the_artifact_map_is_a_committed_prose_list() -> None:
    """§11.1 says the author has not read the map's format. It is §3.2 of the claim-trace audit, prose with elided
    basenames, and the audit covers drafts/sections/ only."""
    audit = _blob("docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md").decode("utf-8")
    assert "### 3.2 Definitive citable-artifact list for the two papers" in audit
    assert "`…_2026-06-01.json`" in audit
    assert "## Part 1 — P01-B (JRSS-B) `drafts/sections/`" in audit
    assert "## Part 2 — P01-A (JRSS-A) `drafts/sections/`" in audit


# --- §10.2 and M-13's qualification ------------------------------------------------------------------------------------------


def test_m13_qualification_defect_the_second_batch_is_refused_unconditionally_not_after_lr022() -> None:
    """§10.2 and §20 say batches after the first 'need LR-022'. The code refuses any second batch whatever LR-022 says:
    the branch that admits one after a passed pilot does not exist, and no package is named to write it."""
    state = reducers.new_legacy_state()
    state["records"][reducers.ACCEPTANCE] = {"obj_first": {}}
    state["decisions"]["dec_pilot"] = {"propose_row": "LR-021", "resolve_row": "LR-022"}
    with pytest.raises(IntegrityError, match="after the first batch"):
        reducers._batch_rules(state, {"items": []})
    source = (REPO_ROOT / "research_system/legacy/replay/reducers.py").read_text(encoding="utf-8")
    assert "LR-022" not in source.split("def _batch_rules", 1)[1].split("def _selector_key", 1)[0]


def test_m13_the_two_roots_hold_55_tracked_files() -> None:
    assert len(_tree(ROOTS[0])) + len(_tree(ROOTS[1])) == 55
