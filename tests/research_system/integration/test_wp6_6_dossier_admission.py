from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from research_system.discovery import DiscoveryRuntime, replay_discovery
from research_system.discovery.authority import subject_sha256
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierAdmissionRejected,
    DossierMember,
    RegisteredRoot,
    accepted_expected_set_hash,
    prepare_dossier_admission,
)
from research_system.errors import IntegrityError
from tests.research_system.integration.test_wp6_6_discovery_runtime import (
    ACTOR_ID,
    _command,
    _genesis,
    _runtime,
)


REPO = Path(__file__).resolve().parents[3]
PACKAGE = ".research-system/contracts/wp6-4/tda-scale-v1.0.3/package-index.json"
SCOPE = ".research-system/contracts/wp6-4/tda-scale-v1.0.1/scale01-scope-definition-blueprint.json"
PREFLIGHT = ".research-system/contracts/wp6-4/tda-scale-v1.0.3/scale01-gate6-preflight.json"
FIXTURE_PREFLIGHT = ".research-system/contracts/wp6-4/tda-scale-v1.0.1/scale01-fixture-preflight-evidence.json"
V1_INDEX = REPO / ".research-system/contracts/wp6-4/tda-scale-v1.0.1/package-index.json"
DOSSIER_AUTHORITY = ".research-system/contracts/wp6-6/tda-scale-dossier-expected-set-authority.json"
PATH_AUTHORITY = ".research-system/contracts/wp6-6/tda-scale-path-registration-authority.json"
VAULT = Path("C:/Users/steph/TDL/vault")


def _member(key: str, kind: str, relative_path: str, *, root_id: str = "repo") -> DossierMember:
    root = REPO if root_id == "repo" else VAULT
    raw = (root / relative_path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    return DossierMember(key, kind, root_id, relative_path, len(raw), digest, f"prov:{key}", 1, digest)


def _subject() -> tuple[AcceptedExpectedSet, dict[str, RegisteredRoot]]:
    inherited = json.loads(V1_INDEX.read_bytes())
    vault_components = tuple(
        _member(row["component_id"], "component", row["relative_path"], root_id="vault")
        for row in inherited["reused_components"]
    )
    members = (
        _member("package-index", "package_index", PACKAGE),
        _member("scope", "scope_definition", SCOPE),
        _member("fixture-preflight", "evidence", FIXTURE_PREFLIGHT),
        _member("gate6-preflight", "evidence", PREFLIGHT),
        *vault_components,
    )
    expected = AcceptedExpectedSet(
        "expected:tda-scale:1.0.3",
        3,
        "1" * 64,
        "obj_019fed25-b33e-7740-b280-000000000913",
        "TDA-ARS-SCALE-RESEARCH",
        "1.0.3",
        "prj_01978abc-1000-7000-8000-000000001000",
        "profile:wp6.6:dossier-admission",
        1,
        "2" * 64,
        members,
    )
    expected = replace(expected, content_hash=accepted_expected_set_hash(expected))
    roots = {
        "repo": RegisteredRoot("repo", REPO, 1, "3" * 64),
        "vault": RegisteredRoot("vault", VAULT, 1, "4" * 64),
    }
    return expected, roots


def _rehash(expected: AcceptedExpectedSet) -> AcceptedExpectedSet:
    return replace(expected, content_hash=accepted_expected_set_hash(replace(expected, content_hash="0" * 64)))


def test_real_tda_scale_dossier_prepares_deterministic_provider_free_atomic_batch() -> None:
    expected, roots = _subject()

    first = prepare_dossier_admission(
        expected_set=expected,
        current_expected_set_revision=3,
        candidate_members=tuple(expected.members),
        registered_roots=roots,
    )
    second = prepare_dossier_admission(
        expected_set=expected,
        current_expected_set_revision=3,
        candidate_members=tuple(expected.members),
        registered_roots=roots,
    )

    assert first == second
    assert first.events[0]["event_type"] == "ResearchDossierAdmitted"
    assert first.events[0]["payload"]["provider_execution"] == "forbidden"
    assert [event["event_type"] for event in first.events].count("PortfolioObjectRegistered") == 20
    assert [event["event_type"] for event in first.events].count("ScopeDefinitionRegistered") == 1
    assert len(first.observed_members) == 21


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda expected: tuple(expected.members[:-1]), "candidate_member_set_mismatch"),
        (
            lambda expected: (
                *expected.members,
                replace(
                    expected.members[0],
                    member_key="foreign-package",
                    relative_path="foreign-package.json",
                ),
            ),
            "candidate_member_set_mismatch",
        ),
        (lambda expected: (*expected.members, expected.members[0]), "duplicate_candidate_member_key"),
        (
            lambda expected: (replace(expected.members[0], sha256="0" * 64), *expected.members[1:]),
            "candidate_member_identity_mismatch",
        ),
    ],
)
def test_candidate_missing_extra_duplicate_tamper_or_traversal_rejects_without_output(mutation, reason) -> None:
    expected, roots = _subject()
    with pytest.raises(DossierAdmissionRejected, match=reason):
        prepare_dossier_admission(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=mutation(expected),
            registered_roots=roots,
        )


def test_stale_collision_unauthorized_and_incomplete_inputs_reject_before_publication(tmp_path: Path) -> None:
    expected, roots = _subject()
    cases = (
        ({"current_expected_set_revision": 2}, "stale_expected_set_revision"),
        ({"existing_identities": frozenset({expected.dossier_id})}, "immutable_identity_collision"),
        ({"registered_roots": {"repo": replace(roots["repo"], authorized=False)}}, "unauthorized_path"),
        ({"registered_roots": {"repo": RegisteredRoot("repo", tmp_path, 1, "3" * 64)}}, "incomplete_package"),
    )
    for overrides, reason in cases:
        arguments = {
            "expected_set": expected,
            "current_expected_set_revision": 3,
            "candidate_members": tuple(expected.members),
            "registered_roots": roots,
        }
        arguments.update(overrides)
        with pytest.raises(DossierAdmissionRejected, match=reason):
            prepare_dossier_admission(**arguments)


def test_unregistered_and_traversing_expected_paths_are_rejected() -> None:
    expected, roots = _subject()
    attacks = (
        (replace(expected.members[0], root_id="foreign"), "unregistered_root"),
        (replace(expected.members[0], relative_path="../package-index.json"), "path_traversal"),
    )
    for attacked_member, reason in attacks:
        attacked = _rehash(replace(expected, members=(attacked_member, *expected.members[1:])))
        with pytest.raises(DossierAdmissionRejected, match=reason):
            prepare_dossier_admission(
                expected_set=attacked,
                current_expected_set_revision=3,
                candidate_members=attacked.members,
                registered_roots=roots,
            )


def test_observed_content_tamper_is_rejected_without_an_event_batch(tmp_path: Path) -> None:
    expected, _ = _subject()
    for member in expected.members:
        target = tmp_path / member.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        source_root = REPO if member.root_id == "repo" else VAULT
        target.write_bytes((source_root / member.relative_path).read_bytes())
    (tmp_path / expected.members[-1].relative_path).write_text("tampered", encoding="utf-8")

    with pytest.raises(DossierAdmissionRejected, match="member_content_tampered"):
        prepare_dossier_admission(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=tuple(expected.members),
            registered_roots={
                "repo": RegisteredRoot("repo", tmp_path, 1, "3" * 64),
                "vault": RegisteredRoot("vault", tmp_path, 1, "4" * 64),
            },
        )


def test_real_package_retains_non_dispatchable_provider_free_identity() -> None:
    package = json.loads((REPO / PACKAGE).read_bytes())
    assert package["package_id"] == "TDA-ARS-SCALE-RESEARCH"
    assert package["admission_status"] == "pending_wp6_6"
    assert package["dispatchable"] is False
    assert package["execution_authorized"] is False


def _accept_authority(runtime: DiscoveryRuntime, kind: str, subject: dict[str, object], offset: int) -> None:
    actors = [f"act_019fed25-b33e-7740-b280-{offset + number:012d}" for number in range(5)]
    actors[4] = ACTOR_ID
    stream_id = f"obj_019fed25-b33e-7740-b280-{offset:012d}"
    review_id = f"rev_019fed25-b33e-7740-b280-{offset:012d}"
    decision_id = f"dec_019fed25-b33e-7740-b280-{offset:012d}"
    first_row = 110 if kind == "dossier_expected_set" else 116
    authority_file_path = DOSSIER_AUTHORITY if kind == "dossier_expected_set" else PATH_AUTHORITY
    authority_raw = (REPO / authority_file_path).read_bytes()
    subject.update(
        authority_file_path=authority_file_path,
        authority_file_size=len(authority_raw),
        authority_file_sha256=hashlib.sha256(authority_raw).hexdigest(),
        authority_file_git_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
        ).strip(),
        authority_file_git_blob=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", f"HEAD:{authority_file_path}"], text=True
        ).strip(),
    )
    subject["subject_sha256"] = subject_sha256(subject)
    steps = (
        (
            "RegisterDossierExpectedSetContent"
            if kind == "dossier_expected_set"
            else "RegisterPathRegistrationContent",
            actors[0],
            {"subject": subject},
        ),
        (
            "ObserveW11AuthorityFile",
            actors[1],
            {
                "subject_sha256": subject["subject_sha256"],
            },
        ),
        ("RequestW11AuthorityReview", actors[2], {"reviewer_actor_id": actors[3]}),
        (
            "RecordW11AuthorityReview",
            actors[3],
            {
                "verdict": "approve",
                "unchanged_subject_sha256": subject["subject_sha256"],
                "unchanged_file_sha256": subject["authority_file_sha256"],
                "reconstruction_sha256": "5" * 64,
            },
        ),
        ("ProposeW11AuthorityDecision", actors[2], {"decision_id": decision_id, "proposed_decision": "accept"}),
        (
            "ResolveDecision",
            actors[4],
            {"decision_id": decision_id, "decision": "accept", "transaction_id": f"txn:{kind}"},
        ),
    )
    for index, (command_type, actor_id, value) in enumerate(steps):
        target_stream_id, expected_version = (
            (stream_id, index) if index < 2 else ((review_id, index - 2) if index < 4 else (decision_id, index - 4))
        )
        command = _command(
            command_type,
            target_stream_id,
            expected_version,
            {"row_id": f"OR-{first_row + index}", "authority_kind": kind, **value},
        )
        command["actor_id"] = actor_id
        assert runtime.submit(command).status == "accepted"


def test_authority_chains_activate_dossier_admission_without_constructor_inputs(tmp_path: Path) -> None:
    expected, roots = _subject()
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    _accept_authority(
        runtime,
        "dossier_expected_set",
        {
            "authority_kind": "dossier_expected_set",
            "record_id": expected.expected_set_id,
            "record_revision": expected.revision,
            "project_id": expected.project_id,
            "scope_id": expected.dossier_id,
            "owner_requirement_refs": ["W11:OR-110-115"],
            "content_sha256": expected.content_hash,
            "expected_set": json.loads(json.dumps(asdict(expected))),
        },
        710,
    )
    _accept_authority(
        runtime,
        "path_registration",
        {
            "authority_kind": "path_registration",
            "record_id": "path-registration:tda-scale",
            "record_revision": 1,
            "project_id": expected.project_id,
            "scope_id": expected.dossier_id,
            "owner_requirement_refs": ["W11:OR-116-121"],
            "content_sha256": "8" * 64,
            "collision_status": "no_collision",
            "registered_roots": [
                {
                    **asdict(root),
                    "path": "$REPOSITORY_ROOT" if root.root_id == "repo" else "$TDA_VAULT_ROOT",
                }
                for root in roots.values()
            ],
        },
        720,
    )
    command = _command(
        "AdmitResearchDossier",
        expected.dossier_id,
        0,
        {
            "row_id": "OR-028",
            "dossier_id": expected.dossier_id,
            "expected_set_id": expected.expected_set_id,
            "candidate_members": [asdict(member) for member in expected.members],
        },
    )

    receipt = runtime.submit(command)
    replayed = replay_discovery(runtime.ledger.iter_events())

    assert receipt.status == "accepted"
    assert replayed["authorities"]["dossier_expected_set"]["status"] == "accepted"
    assert replayed["authorities"]["path_registration"]["status"] == "accepted"
    assert replayed["dossiers"][expected.dossier_id]["member_count"] == 21


@pytest.mark.parametrize("attack", ["unrelated_tracked_file", "altered_expected_set"])
def test_public_observation_rejects_authority_content_not_serialized_by_git_bytes(
    tmp_path: Path,
    attack: str,
) -> None:
    expected, _ = _subject()
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    subject = {
        "authority_kind": "dossier_expected_set",
        "record_id": expected.expected_set_id,
        "record_revision": expected.revision,
        "project_id": expected.project_id,
        "scope_id": expected.dossier_id,
        "owner_requirement_refs": ["W11:OR-110-115"],
        "content_sha256": expected.content_hash,
        "expected_set": json.loads(json.dumps(asdict(expected))),
    }
    authority_path = DOSSIER_AUTHORITY
    if attack == "unrelated_tracked_file":
        authority_path = PACKAGE
    else:
        subject["expected_set"]["package_version"] = "fabricated"  # type: ignore[index]
    raw = (REPO / authority_path).read_bytes()
    subject.update(
        authority_file_path=authority_path,
        authority_file_size=len(raw),
        authority_file_sha256=hashlib.sha256(raw).hexdigest(),
        authority_file_git_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
        ).strip(),
        authority_file_git_blob=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", f"HEAD:{authority_path}"], text=True
        ).strip(),
    )
    subject["subject_sha256"] = subject_sha256(subject)
    stream_id = "obj_019fed25-b33e-7740-b280-000000000730"
    register = _command(
        "RegisterDossierExpectedSetContent",
        stream_id,
        0,
        {"row_id": "OR-110", "authority_kind": "dossier_expected_set", "subject": subject},
    )
    assert runtime.submit(register).status == "accepted"
    observe = _command(
        "ObserveW11AuthorityFile",
        stream_id,
        1,
        {
            "row_id": "OR-111",
            "authority_kind": "dossier_expected_set",
            "subject_sha256": subject["subject_sha256"],
        },
    )
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="content does not match registered subject"):
        runtime.submit(observe)
    assert tuple(runtime.ledger.iter_events()) == before
