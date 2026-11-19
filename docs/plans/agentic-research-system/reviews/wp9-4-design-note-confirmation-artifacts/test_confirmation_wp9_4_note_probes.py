# Research context: docs/plans/agentic-research-system/reviews/wp9-4-design-note-confirmation-ede231e5-2026-11-19.md (P-085)
# Purpose: the confirming re-reviewer's asserting probes for the WP9.4 design note, revision 3 (ede231e5). Stores are
# scratch stores under tmp_path; papers/ and results/ are read through Git only. A probe whose name contains ``defect``
# passes while the defect it names is present (in the code at ede231e5, or in the note's design as written).
"""Confirmation probes for the WP9.4 design note, revision 3, at ``ede231e5``.

Run from the repository root:

    uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider \
        docs/plans/agentic-research-system/reviews/wp9-4-design-note-confirmation-artifacts/
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
from research_system.errors import IntegrityError  # noqa: E402
from research_system.evidence.consumers import ArtefactConsumerContext, ArtefactEvidenceConsumers  # noqa: E402
from research_system.legacy import preparers  # noqa: E402
from research_system.legacy.records import (  # noqa: E402
    derived_id,
    record_content_hash,
    review_attempt_id,
    review_context_manifest_id,
)
from research_system.legacy.replay import reducers  # noqa: E402

REVIEWED = "ede231e55bbc653580528870778e2224674da8b3"
REVISION_2 = "4629d1fd"
CODE_BASE = "4312dc63"
NOTE = "docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md"
ANNEX = REPO_ROOT / "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
SCHEMAS = REPO_ROOT / ".research-system" / "schemas"
T0 = "2026-11-19T10:00:00Z"
LATER = datetime(2026, 12, 31, tzinfo=UTC)
ROOTS = ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/")


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True).stdout


def _tree(prefix: str = "") -> list[str]:
    raw = _git("ls-tree", "-r", "-z", "--name-only", REVIEWED, *([prefix] if prefix else []))
    return [path for path in raw.decode("utf-8").split("\0") if path]


def _blob(path: str) -> bytes:
    return _git("show", f"{REVIEWED}:{path}")


def _source(path: str) -> list[str]:
    return _blob(path).decode("utf-8").splitlines()


def _annex_rows() -> dict[str, dict[str, Any]]:
    annex = yaml.safe_load(ANNEX.read_text(encoding="utf-8"))
    return {row["owner_row_id"]: row for row in annex["rows"]}


def _note() -> str:
    return _blob(NOTE).decode("utf-8")


# --- Currency -----------------------------------------------------------------------------------------------------------


def test_reviewed_commit_changes_only_the_note_and_no_code_since_the_code_base() -> None:
    assert _git("diff", "--name-only", REVISION_2, REVIEWED).decode().split() == [NOTE]
    assert (
        _git("diff", "--name-only", CODE_BASE, REVIEWED, "--", "research_system", ".research-system", "tools", "tests")
        == b""
    )
    # The probes import the working tree, so it must be the reviewed commit's code.
    assert _git("diff", "--name-only", REVIEWED, "--", "research_system", ".research-system") == b""


# --- Claim 1 (R-M1): only the claim predicate binds a claim_promotion Decision --------------------------------------------

LEGACY_BYTES = b'{"escape_rate": 0.0558, "wilson_ci": [0.0508, 0.0612], "n": 7453}\n'  # fixture bytes, not a result
LEGACY_SHA256 = sha256_hex(LEGACY_BYTES)
COPY_PATH = "results/legacy_copy/escape_wilson_ci_2026-05-16.json"
SCOPE_ID = "release:wp9-4-confirmation"
TASK_ID = "tsk_019fe47a-4001-7000-8000-000000004001"
MS_ART = "art_019fe47a-4000-7000-8000-000000004000"
MS_REVIEW = "rev_019fe47a-4005-7000-8000-000000004005"
MS_EVIDENCE = "arec_019fe47a-4007-7000-8000-000000004007"


class _GoverningReview:
    """One governing scientific review of the fixture bytes, in the shape the accepted resolver returns."""

    def resolve(self, reference_id: str, *, project_id: str, evaluation_time: datetime) -> GoverningEvidenceResolution:
        from tests.research_system.factories import ACTORS

        assert reference_id == MS_EVIDENCE
        record = {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": project_id,
            "review_id": MS_REVIEW,
            "subject_sha256": LEGACY_SHA256,
            "reviewer_actor_id": ACTORS["actor-a"],
            "eligible": True,
            "related": False,
            "independence_grade": "I2",
            "status": "active",
        }
        return GoverningEvidenceResolution(reference_id, sha256_hex(canonical_bytes(record)), record)


@pytest.fixture
def manuscript_copy(tmp_path: Path) -> dict[str, Any]:
    """A scratch store in which a byte copy of fixture 'legacy' bytes is registered, reviewed and promoted for
    manuscript evidence, with no Decision anywhere in the flow."""
    from tests.research_system.factories import ACTORS, activate_lifecycle_grant, control_plane
    from tests.research_system.integration.test_artefact_authority_commands import artefact_manifest, command

    base = control_plane(tmp_path)
    harness = replace(
        base,
        service=base.authority_service,
        ledger=base.authority_ledger,
        objects=base.authority_objects,
        receipts=base.authority_receipts,
    )
    harness.service.governing_evidence_resolver = _GoverningReview()
    control_root = Path(harness.ledger.root if hasattr(harness.ledger, "root") else tmp_path / ".control.authority")
    (control_root / COPY_PATH).parent.mkdir(parents=True, exist_ok=True)
    (control_root / COPY_PATH).write_bytes(LEGACY_BYTES)
    manifest = deepcopy(artefact_manifest())
    manifest.update(
        artefact_id=MS_ART,
        task_id=TASK_ID,
        relative_path=COPY_PATH,
        size_bytes=len(LEGACY_BYTES),
        content_sha256=LEGACY_SHA256,
    )
    manifest["authority"]["accepted_scope"] = SCOPE_ID
    grant = activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=MS_ART,
        command_types=("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
    )
    steps = [
        ("RegisterArtefact", 0, {"new_artefact_id": MS_ART, "manifest": manifest}),
        (
            "RecordScientificReview",
            1,
            {
                "artefact_id": MS_ART,
                "review_id": MS_REVIEW,
                "subject_sha256": LEGACY_SHA256,
                "scientific_review": "approved",
                "evidence_refs": [MS_EVIDENCE],
            },
        ),
    ]
    for number, (command_type, version, payload) in enumerate(steps):
        envelope = command(
            command_id=f"cmd_019fe47a-401{number}-7000-8000-00000000401{number}",
            command_type=command_type,
            actor_id=ACTORS["actor-a"],
            authority_grant_id=grant,
            expected_stream_version=version,
            payload=payload,
            target_stream_id=MS_ART,
        )
        assert harness.service.submit(envelope).status == "accepted"
    contract = ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load()
    predicate, predicate_sha256 = contract.predicate_for("manuscript_evidence")
    use = command(
        command_id="cmd_019fe47a-4019-7000-8000-000000004019",
        command_type="SetArtefactUseAuthority",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant,
        expected_stream_version=2,
        payload={
            "artefact_id": MS_ART,
            "use_authority": "accepted_for_scope",
            "subject_sha256": LEGACY_SHA256,
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]), str(predicate["predicate_version"]), predicate_sha256
            ),
            "evidence_refs": [MS_REVIEW, MS_EVIDENCE],
        },
        target_stream_id=MS_ART,
    )
    harness.service.clock = lambda: datetime.fromisoformat(use["submitted_at"].replace("Z", "+00:00"))
    receipt = harness.service.submit(use)
    resolver = ArtefactUseResolver(
        ledger=harness.ledger,
        objects=harness.objects,
        schemas=harness.schemas,
        contract_loader=ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT),
        governing_evidence=_GoverningReview(),
        content_reader=ControlRootArtefactContentReader(control_root),
        authority_state_validator=harness.authority_resolver.validate_replayed_administration_state,
    )
    return {"receipt": receipt, "consumers": ArtefactEvidenceConsumers(resolver)}


def test_claim1_holds_manuscript_promotion_of_a_legacy_copy_needs_no_decision(manuscript_copy) -> None:
    """§4.2 now says what the code does: a governing review alone reaches accepted_for_scope under the manuscript
    predicate, and resolve_for_manuscript (a production consumer ID) resolves the copied bytes."""
    from tests.research_system.factories import PROJECT_ID

    assert manuscript_copy["receipt"].status == "accepted", manuscript_copy["receipt"]
    context = ArtefactConsumerContext(
        artefact_id=MS_ART,
        exact_content_sha256=LEGACY_SHA256,
        project_id=PROJECT_ID,
        task_id=TASK_ID,
        scope_id=SCOPE_ID,
        evaluation_time=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
    )
    resolved = manuscript_copy["consumers"].resolve_for_manuscript(context, consumer_id="rm03_brief_manuscript")
    assert resolved.exact_content_sha256 == LEGACY_SHA256 and resolved.decision_id is None
    service = _source("research_system/command/service.py")
    assert (
        service[4900].strip().startswith('if command.envelope["payload"].get("consumer_predicate") != claim_reference')
    )
    assert service[4901].strip() == "return []"


# --- Claim 2 (R-M2): the readers the note names, and the ones it does not ------------------------------------------------


def test_claim2_defect_the_at_use_rule_names_two_of_five_consumer_kinds() -> None:
    """§4.2 item 3 binds the content rule at use in resolve_for_claim and resolve_for_manuscript only. The consumer
    facade has five kinds; resolve_for_result and resolve_for_review have production callers (release publication;
    brief review, follow-up review and session exchange). Only the promotion-site option of E reaches them."""
    consumers = "\n".join(_source("research_system/evidence/consumers.py"))
    kinds = set(re.findall(r'consumer_kind="([a-z_]+)"', consumers))
    assert kinds == {"result_evidence", "review_evidence", "manuscript_evidence", "claim_evidence", "sensitive_sidecar"}
    assert 'consumer_id="release_publication"' in "\n".join(_source("research_system/evals/release_publication.py"))
    assert "resolve_for_review" in "\n".join(_source("research_system/session_exchange/exchange.py"))
    assert 'consumer_id="rm04_followup_review"' in "\n".join(_source("research_system/methods/brief.py"))
    note = _note()
    assert "at use: `resolve_for_claim` and `resolve_for_manuscript` refuse" in note
    assert "resolve_for_result" not in note and "resolve_for_review" not in note


def test_claim2_holds_the_direct_readers_the_note_names_are_all_of_them() -> None:
    hits = set()
    for path in (REPO_ROOT / "research_system").rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if 'use_authority") == "accepted_for_scope"' in line or 'use_authority"] == "accepted_for_scope"' in line:
                hits.add((path.relative_to(REPO_ROOT).as_posix(), number))
    assert hits == {
        ("research_system/cli.py", 2258),
        ("research_system/command/service.py", 4618),
        ("research_system/discovery/spec.py", 533),
        ("research_system/discovery/spec_result.py", 248),
    }


# --- Claim 3 (R-M3): the stale rule over recorded observations -----------------------------------------------------------


def _observation(record_id: str, registration: str, path: str, blob: str, selector: dict[str, Any]) -> dict[str, Any]:
    record = {
        "schema_id": "ars://legacy/legacy-observation",
        "record_id": record_id,
        "record_revision": 1,
        "registration_ref": {"id": registration, "record_revision": 1, "content_hash": "4" * 64},
        "selector": selector,
        "source_identity": {"identity_kind": "git_tracked", "repository_path": path, "git_blob": blob},
    }
    record["content_hash"] = record_content_hash(record)
    return record


def _observe(monkeypatch: pytest.MonkeyPatch, state: dict[str, Any], record: dict[str, Any]) -> None:
    registration = record["registration_ref"]["id"]
    monkeypatch.setattr(reducers, "_check_observation", lambda *args: registration)
    reducers.reduce_record(state, "LR-015", [{"payload": record}], {})


def _ref(record: dict[str, Any]) -> dict[str, Any]:
    return {"id": record["record_id"], "record_revision": 1, "content_hash": record["content_hash"]}


FAMILY = {"selector_kind": "json_family_set", "membership_ref": {"id": "obj_t"}, "family_names": ["a"]}
OTHER_FAMILY = {"selector_kind": "json_family_set", "membership_ref": {"id": "obj_t"}, "family_names": ["b"]}
WHOLE = {"selector_kind": "whole_file"}


def test_claim3_holds_a_disjoint_reobservation_with_a_new_blob_marks_the_adopted_observation_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = reducers.new_legacy_state()
    _observe(monkeypatch, state, _observation("obj_o1", "obj_reg", "results/x.json", "a" * 40, FAMILY))
    _observe(monkeypatch, state, _observation("obj_o2", "obj_reg", "results/x.json", "b" * 40, OTHER_FAMILY))
    assert state["stale_observations"] == ["obj_o1"]


def test_claim3_holds_and_the_note_states_the_unobserved_edit_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = reducers.new_legacy_state()
    _observe(monkeypatch, state, _observation("obj_o1", "obj_reg", "results/x.json", "a" * 40, FAMILY))
    assert state["stale_observations"] == []  # the file's blob may have changed in Git; nothing is recorded
    note = _note()
    assert "A registered file that changes and is not yet\nre-observed leaves its adoption projected `active`" in note
    assert "compares the artefact's Git blob with the blob, at the binding's `git_head`, of every registered" in note


# --- Claim 4 (R-M4): the eligibility encoding -------------------------------------------------------------------------------


def _verdict(session: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "review_id": "rev_derived",
        "reviewer_actor_id": "act_reviewer",
        "verdict": "approve",
        "unchanged_subject_sha256": "h" * 64,
        "conditions": [],
        "required_evidence_refs": ["w9-analyst-session:s-analyst", "w9-eligible-session:s-eligible"],
        "reviewer_profile": reducers.REVIEWER_PROFILE,
        "context_manifest_id": review_context_manifest_id("rev_derived", T0),
        "producing_attempt_id": review_attempt_id("rev_derived", T0),
        "trace_visibility_evidence_refs": ["h" * 64],
        "computed_independence_grade": "independent",
        "reviewer_session": session,
    }
    event = {"actor_id": "act_reviewer", "occurred_at": T0, "stream_id": "rev_derived", "stream_version": 2}
    return payload, event


def test_claim4_defect_the_unchanged_session_exclusion_refuses_the_eligible_session() -> None:
    """§5.5 makes LR-026's request carry ``w9-eligible-session:<s>`` as its second session ref, through
    ``_session_refs``, which returns every session it parses; replay stores them as the sessions the request records.
    §5.3 keeps 'the reviewer's session differs from every session the request records' unchanged (:893-895). So the
    one session §5.5 requires at LR-027 is the one session that check refuses. The note must say the eligible session is
    not among the excluded sessions."""
    review = {
        "reviewer": "act_reviewer",
        "allowed_verdicts": ["approve"],
        "subject": ("obj_adoption", "h" * 64),
        "required_evidence_refs": ["w9-analyst-session:s-analyst", "w9-eligible-session:s-eligible"],
        "requested_at": T0,
        "sessions": ["s-analyst", "s-eligible"],  # what _session_refs returns for two parsed refs
    }
    state = reducers.new_legacy_state()
    state["proposals"]["obj_adoption"] = {"kind": "k", "recorded": False, "lapse_at": LATER, "content_hash": "h" * 64}
    with pytest.raises(IntegrityError, match="session the request records"):
        reducers._check_verdict(state, review, *reversed(_verdict("s-eligible")))
    reducers._check_verdict(state, review, *reversed(_verdict("s-colleague")))  # and the wrong session passes
    note = _note()
    assert "The reviewer exclusions are unchanged" in note
    assert "For an adoption verdict it must **equal** the\n  request's eligible session" in note


def test_claim4_holds_lr024_cannot_use_the_generic_check_so_its_own_branch_is_needed() -> None:
    """The generic check fixes three refs; §5.5's eight-ref branch, with no review, is the only way LR-024 can pass."""
    refs = ["W9:LR-024", "w9-subject:obj_a", "w9-subject-sha256:" + "0" * 64] + [
        f"w9-eligible-{name}:x" for name in ("session", "family", "version", "profile", "grade")
    ]
    with pytest.raises(IntegrityError, match="does not encode its subject"):
        reducers._check_decision_proposal(
            reducers.new_legacy_state(), "LR-024", {"occurred_at": T0}, {"governing_evidence_refs": refs}
        )
    assert "**LR-024 has a proposal branch of its own.**" in _note()


def test_claim4_defect_the_resolution_preparer_always_appends_a_record_event() -> None:
    """LR-025 writes no record (annex G5), and §5.5 gives it a record-less replay branch. prepare_resolution always
    appends RECORDED_EVENTS[row]; §5.5's preparer bullet names the proposal and request preparers only."""
    source = "\n".join(_source("research_system/legacy/preparers.py"))
    assert "(RECORDED_EVENTS[row], record_id, record)" in source
    assert "LR-025" not in preparers.RECORDED_EVENTS
    assert _annex_rows()["LR-025"]["ordered_events"] == [
        {"event": "W2:DecisionResolved", "multiplicity": "1", "condition": None}
    ]


def test_claim4_holds_the_verdict_metadata_is_one_string() -> None:
    schema = json.loads((SCHEMAS / "core/events/review_verdict_recorded.schema.json").read_text(encoding="utf-8"))
    assert schema["$defs"]["payload"]["oneOf"][0]["properties"]["reviewer_model_metadata"]["type"] == "string"


# --- Claim 5 (R-M5): fixture applicability -----------------------------------------------------------------------------------


def test_claim5_the_applicable_set_is_written_by_the_items_producer() -> None:
    """§5.4 puts the applicable set in the review request. The requester is migration_analyst, who is also the
    proposer (the producer) of the adoption, discharge, mapping and ownership proposals. W9 §12.3 says 'never by the
    item's producer'. The approve-only verdict cannot carry another set (conditions are fixed to [])."""
    rows = _annex_rows()
    for proposal, request in (("LR-023", "LR-026"), ("LR-030", "LR-031"), ("LR-045", "LR-046"), ("LR-050", "LR-051")):
        assert rows[proposal]["eligible_actor"] == "migration_analyst"
        assert rows[request]["requester"] == "migration_analyst"
    design = (
        REPO_ROOT / "docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md"
    ).read_text(encoding="utf-8")
    assert "Per-item applicability is proposed by the item's independent reviewer and fixed by Stephen" in design
    assert "never by the item's producer" in design
    register = (REPO_ROOT / "docs/plans/agentic-research-system/03-decisions-and-open-questions.md").read_text(
        encoding="utf-8"
    )
    # The precedent Stephen accepted for LR-020: the analyst lists, the reviewer approves the hash (P-084 i-3).
    assert "a conditional `pilot_promotion` fixture that is listed is applicable" in register
    reducer = "\n".join(_source("research_system/legacy/replay/reducers.py"))
    assert '"conditions": [],' in reducer


def test_claim5_holds_f019_is_conditional_on_claim_use_at_lr029_and_unconditional_where_the_note_says() -> None:
    rows = _annex_rows()
    when = {f["fixture_id"]: f["when"] for f in rows["LR-029"]["pilot_promotion_fixtures"]}
    assert when["F-019"] == "the intended use is evidence for a claim" and when["S-017"] is None
    unconditional = {
        row: {f["fixture_id"] for f in rows[row]["pilot_promotion_fixtures"] if f["when"] is None}
        for row in ("LR-034", "LR-044", "LR-049", "LR-054", "LR-055")
    }
    assert unconditional == {
        "LR-034": set(),
        "LR-044": {"F-018", "F-023", "F-037"},
        "LR-049": set(),
        "LR-054": {"F-006", "F-019", "F-023", "F-037"},
        "LR-055": {"F-006", "F-019", "F-037"},
    }


# --- Claim 6 (R-M6): §11.1's rule, as written, over both roots through Git -----------------------------------------------------

_SEPARATORS = re.compile(r"[\s`'\"()\[\]<>,;|*]+")
_RESULT_EXTENSIONS = (".json", ".npy", ".npz", ".csv", ".pkl")
_EXTENSION = re.compile(r"\.[A-Za-z0-9]+$")


def _json_strings(node: Any):
    if isinstance(node, dict):
        for value in node.values():
            yield from _json_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _json_strings(value)
    elif isinstance(node, str):
        yield node


class Extractor:
    """§11.1 items 1 to 3 and 7, with no disambiguation file. ``suffix`` picks the reading of 'ends in a registered
    result's basename': as a path component, or as a string suffix."""

    def __init__(self, *, suffix: str = "component") -> None:
        self.registered = set(_tree("results/"))
        self.directories = {"/".join(p.split("/")[:i]) for p in _tree() for i in range(1, p.count("/") + 1)}
        self.by_base: dict[str, list[str]] = defaultdict(list)
        for path in self.registered:
            self.by_base[path.rsplit("/", 1)[-1]].append(path)
        self.suffix = suffix

    def texts(self, path: str) -> list[str] | None:
        raw = _blob(path)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
        texts = [text, *(_json_strings(json.loads(text)) if path.endswith(".json") else [])]
        return [re.sub(r"/+", "/", t.replace("\\", "/")) for t in texts]

    def _candidate(self, token: str) -> bool:
        base = token.rsplit("/", 1)[-1]
        ends = base in self.by_base if self.suffix == "component" else any(token.endswith(b) for b in self.by_base)
        return "results/" in token or ends or ("/" not in token and token.lower().endswith(_RESULT_EXTENSIONS))

    def classify(self, raw: str) -> tuple[str, str] | None:
        token = raw.rstrip(".:")
        if not token or not self._candidate(token):
            return None
        bare = "/" not in token
        for path in self.registered:
            if token == path or token.endswith("/" + path):
                return ("cited", path)
        if bare and token in self.by_base:
            return ("cited", self.by_base[token][0]) if len(self.by_base[token]) == 1 else ("ambiguous", token)
        if "results/" in token:
            under = token[token.index("results/") :].rstrip("/")
            if token.endswith("/") or under in self.directories or not _EXTENSION.search(under.rsplit("/", 1)[-1]):
                return ("not_a_file", token)
            return ("unregistered", token)
        if bare and token.lower().endswith(_RESULT_EXTENSIONS):
            return ("unregistered", token)
        return ("unclassified", token)

    def run(self, root: str) -> dict[str, Any]:
        out: dict[str, Any] = {"blocking": defaultdict(set), "reported": defaultdict(set), "not_text": []}
        for path in _tree(root):
            texts = self.texts(path)
            if texts is None:
                out["not_text"].append(path)
                continue
            scope = "blocking" if path.startswith(root + "drafts/") else "reported"
            for text in texts:
                for token in _SEPARATORS.split(text):
                    verdict = self.classify(token)
                    if verdict:
                        out[scope][verdict[0]].add(verdict[1])
        return out


@pytest.fixture(scope="module")
def extracted() -> dict[str, dict[str, Any]]:
    extractor = Extractor()
    return {root: extractor.run(root) for root in ROOTS}


AMBIGUOUS_P01A = {
    "04_nulls_wasserstein_w2_20260407.json",
    "04_nulls_wasserstein_w2_L5000_20260502.json",
    "05_analysis.json",
    "stratified_markov1_W2_L5000_20260502.json",
}


def test_claim6_holds_p01b_drafts_leave_no_blocker(extracted) -> None:
    drafts = extracted["papers/P01-B-JRSSB/"]["blocking"]
    assert drafts["cited"] == {
        "results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json",
        "results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json",
    }
    assert drafts["not_a_file"] == {
        "results/trajectory_tda_bhps/post_audit/",
        "results/trajectory_tda_integration/post_audit/",
    }
    assert not drafts["ambiguous"] and not drafts["unregistered"] and not drafts["unclassified"]


def test_claim6_defect_p01a_drafts_leave_a_filename_template_as_an_unregistered_blocker(extracted) -> None:
    """The note expects exactly the four ambiguous names. A fifth blocker remains: the f-string output name in
    compute_table1_effects.py:205 is a bare name with a result extension that no registered result has. No
    registration, disambiguation entry or new status can clear a template; only a draft edit or an extractor change."""
    drafts = extracted["papers/P01-A-JRSSA/"]["blocking"]
    assert drafts["ambiguous"] == AMBIGUOUS_P01A
    assert drafts["unregistered"] == {"table1_effects_{date_suffix}.json"}
    assert len(drafts["cited"]) == 23
    assert drafts["not_a_file"] == {
        "results/trajectory_tda_bhps/post_audit/",
        "results/trajectory_tda_bhps/stratified_markov/",
        "results/trajectory_tda_integration/post_audit/",
        "results/trajectory_tda_integration/stratified_markov/",
    }
    line = _source("papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py")[204]
    assert 'f"table1_effects_{date_suffix}.json"' in line


def test_claim6_defect_outside_drafts_templates_and_a_bare_extension_are_unregistered_too(extracted) -> None:
    """Reported, not blocking, under drafts-only scope; but they show the class: a template or a lone '.json' token
    is 'unregistered', so whole-root scope (I's alternative) would block on tokens that name no file."""
    a = extracted["papers/P01-A-JRSSA/"]["reported"]["unregistered"]
    b = extracted["papers/P01-B-JRSSB/"]["reported"]["unregistered"]
    assert {".json", "8000}.json", "regime_labels.npy"} <= a
    assert {".json", "ladder_{survey}_L{landmarks}_B{B}_{date}.json", "level1_comparison_YYYYMMDD.json"} <= b


def test_claim6_holds_no_candidate_falls_in_no_class_and_no_file_is_not_text(extracted) -> None:
    for root in ROOTS:
        for scope in ("blocking", "reported"):
            assert not extracted[root][scope]["unclassified"]
        assert extracted[root]["not_text"] == []
    string_suffix = Extractor(suffix="string")
    for root in ROOTS:
        result = string_suffix.run(root)
        assert not result["blocking"]["unclassified"] and not result["reported"]["unclassified"]


def test_claim6_whole_root_and_drafts_cited_counts(extracted) -> None:
    """§11.1 says whole-root scope 'added 19 and 4 cited files'. Under the rule as written it adds 24 and 8."""
    added = {}
    for root in ROOTS:
        drafts, rest = extracted[root]["blocking"]["cited"], extracted[root]["reported"]["cited"]
        added[root] = len(rest - drafts)
        assert len(drafts | rest) == {"papers/P01-A-JRSSA/": 47, "papers/P01-B-JRSSB/": 10}[root]
    assert added == {"papers/P01-A-JRSSA/": 24, "papers/P01-B-JRSSB/": 8}
    assert "added 19 and 4 cited files" in _note()


def test_claim6_defect_one_citing_file_means_two_results_by_one_basename() -> None:
    """The disambiguation file has one row per (citing file, basename) naming one registered path. In
    compute_table1_effects.py each ambiguous basename is composed twice, once under each results tree."""
    lines = _source("papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py")
    block = "\n".join(lines[21:54])
    for base in sorted(AMBIGUOUS_P01A - {"05_analysis.json"}):
        assert block.count(f'"{base}"') == 2, base
    assert '"results/trajectory_tda_integration/post_audit/" "04_nulls_wasserstein_w2_20260407.json"' in block
    assert '"results/trajectory_tda_bhps/post_audit/" "04_nulls_wasserstein_w2_20260407.json"' in block
    assert "one row per `(citing file path,\nbasename)` giving the registered path it means" in _note()


# --- Claim 7 (R-M7): K's option 1 and its readings ---------------------------------------------------------------------------

ROOT = "obj_root"
GITKEEP = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def _members(monkeypatch: pytest.MonkeyPatch, blobs: tuple[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    state = reducers.new_legacy_state()
    members = [
        _observation("obj_m1", ROOT, "papers/P01-A-JRSSA/drafts/.gitkeep", blobs[0], WHOLE),
        _observation("obj_m2", ROOT, "papers/P01-A-JRSSA/figures/.gitkeep", blobs[1], WHOLE),
    ]
    for member in members:
        _observe(monkeypatch, state, member)
    return state, members


def test_claim7_defect_the_latest_for_source_and_selector_rule_refuses_an_earlier_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fourth WP9.3 check option 1 must read: _batch_rules (:555-559) keys 'the latest for its source and selector'
    by registration and selector. Two members observed whole under the root's registration have the same key, so the
    earlier member can never be accepted closed_reference, which §10.3 requires of every inventory row. The two real
    .gitkeep members share one blob, so the stale rule does not hide this."""
    state, members = _members(monkeypatch, (GITKEEP, GITKEEP))
    assert state["stale_observations"] == []
    with pytest.raises(IntegrityError, match="not the latest for its source and selector"):
        reducers._batch_rules(state, {"items": [{"observation_ref": _ref(members[0])}]})
    reducers._batch_rules(state, {"items": [{"observation_ref": _ref(members[1])}]})  # the later one passes
    tree = dict(line.split("\t")[::-1] for line in _git("ls-tree", REVIEWED, *members_paths()).decode().splitlines())
    assert {entry.split()[2] for entry in tree.values()} == {GITKEEP}
    note = _note()
    assert "That needs three readings of WP9.3's row checks" in note and "_batch_rules" not in note


def members_paths() -> list[str]:
    return ["papers/P01-A-JRSSA/drafts/.gitkeep", "papers/P01-A-JRSSA/figures/.gitkeep"]


def test_claim7_reading_two_is_real_whole_file_is_true_for_a_member_and_a_batch_refuses_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unread, _whole_file is true for a member's whole_file selector, so LR-020 would close the root, and
    check_acceptance (:614-616) refuses a batch holding two members. Reading 2 must change _whole_file itself."""
    state, members = _members(monkeypatch, (GITKEEP, GITKEEP))
    assert reducers._whole_file(state, members[0]) is True
    source = _source("research_system/legacy/replay/reducers.py")
    assert 'whole = [str(o["registration_ref"]["id"]) for o in observations if _whole_file(state, o)]' in source[613]
    assert "two whole-file items of one registration" in source[615]


def test_claim7_holds_members_with_different_blobs_mark_each_other_stale_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """The third reading is needed: per-registration fingerprints make member 1 stale when member 2 is observed."""
    state, _ = _members(monkeypatch, ("a" * 40, "b" * 40))
    assert state["stale_observations"] == ["obj_m1"]


def test_claim7_holds_a_per_path_stale_rule_equals_the_current_rule_for_every_one_path_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A model of §10.2's per-path comparison. For a registration whose observations share one path (every role but
    the root, by LR-015's path rule), grouping by path changes nothing."""
    state = reducers.new_legacy_state()
    history = [("obj_o1", "a" * 40), ("obj_o2", "a" * 40), ("obj_o3", "b" * 40), ("obj_o4", "b" * 40)]
    for record_id, blob in history:
        _observe(monkeypatch, state, _observation(record_id, "obj_reg", "results/x.json", blob, FAMILY))
    per_path: list[str] = []
    seen: list[tuple[str, str]] = []
    for record_id, blob in history:
        per_path += [other for other, other_blob in seen if other_blob != blob and other not in per_path]
        seen.append((record_id, blob))
    assert per_path == state["stale_observations"] == ["obj_o1", "obj_o2"]


# --- Claim 8 (R-M8): the derived citation-status ID --------------------------------------------------------------------------


def _status_id(root: str, supersedes: str | None, cited: str, extractor: str, reviewer: str) -> str:
    domain = f"w9-citation-status:{root}:{supersedes or 'none'}:{cited}:{extractor}:{reviewer}"
    return derived_id("obj", domain, 1_763_546_400_000)


def test_claim8_holds_the_derived_status_id_binds_all_three_hashes() -> None:
    base = ("obj_root", None, "1" * 64, "2" * 64, "3" * 64)
    ids = {_status_id(*base)}
    for index in (2, 3, 4):
        changed = list(base)
        changed[index] = "f" * 64
        ids.add(_status_id(*changed))
    ids.add(_status_id("obj_root", "obj_prev", *base[2:]))
    assert len(ids) == 5


def test_claim8_every_wp9_4_row_has_a_subject_in_section_5_6() -> None:
    covered = {23, 30, 40, 45, 50, 26, 31, 41, 46, 51, 27, 32, 42, 47, 52, 28, 33, 43, 48, 53, 29, 34, 44, 49, 54, 55}
    covered |= {24, 25, 35, 39}
    package = {23, *range(26, 36), 39, *range(40, 56)}
    assert package | {24, 25} == covered


# --- Claim 9 (R-M9): the use-key carrier --------------------------------------------------------------------------------------


def test_claim9_holds_an_alias_can_carry_the_key() -> None:
    schema = json.loads((SCHEMAS / "core/commands/create_task.schema.json").read_text(encoding="utf-8"))
    alias = schema["$defs"]["alias"]
    assert set(alias["required"]) == {"namespace", "value", "scope_id"}
    assert alias["properties"]["namespace"] == {"type": "string", "minLength": 1, "x-source-citation": "W2 §24.1"}


def test_claim9_defect_amend_task_can_change_the_alias_and_the_refs_after_create_task() -> None:
    """J's guard is named for CreateTask. AmendTask carries the same task_definition, aliases and source_import_refs
    included, so a guard on CreateTask alone can be passed and then amended around."""
    schema = json.loads((SCHEMAS / "core/commands/amend_task.schema.json").read_text(encoding="utf-8"))
    properties = schema["$defs"]["task_definition"]["properties"]
    assert {"aliases", "source_import_refs"} <= set(properties)
    note = _note()
    assert "AmendTask" not in note


# --- Claim 11: first-round closures still hold ---------------------------------------------------------------------------------


def test_claim11_the_ten_gate_sites_and_the_review_field_reads_are_unchanged() -> None:
    source = _source("research_system/legacy/replay/reducers.py")
    assert [n for n, line in enumerate(source, 1) if "row_id in WP9_3_ROWS" in line] == [
        703,
        719,
        737,
        847,
        908,
        991,
        1025,
        1138,
        1179,
        1387,
    ]
    hits = set()
    for path in ("research_system/legacy/replay/reducers.py", "research_system/legacy/preparers.py"):
        for number, line in enumerate(_source(path), 1):
            if re.search(r"_(REQUEST|FAMILY)_REVIEW_FIELD\b", line) and not re.match(
                r"^_(REQUEST|FAMILY)_REVIEW", line
            ):
                hits.add((path.rsplit("/", 1)[-1], number))
    assert hits == {
        ("reducers.py", 797),
        ("reducers.py", 965),
        ("reducers.py", 1092),
        ("preparers.py", 389),
        ("preparers.py", 512),
    }


def test_claim11_the_import_seam_the_note_allowlists_is_complete() -> None:
    importers = set()
    for path in (REPO_ROOT / "research_system").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative.startswith(("research_system/legacy/", "research_system/cli.py")):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.search(r"from research_system\.legacy(\.[\w.]+)? import", line)
            if match:
                importers.add((relative, number, match.group(1)))
    assert importers == {
        ("research_system/command/service.py", 640, ".identities"),
        ("research_system/command/t2.py", 1197, ".identities"),
        ("research_system/discovery/routes.py", 313, ".identities"),
        ("research_system/discovery/routes.py", 332, ".commands"),
        ("research_system/projection/replay.py", 1215, ".commands"),
        ("research_system/projection/replay.py", 1393, ".replay.driver"),
    }
