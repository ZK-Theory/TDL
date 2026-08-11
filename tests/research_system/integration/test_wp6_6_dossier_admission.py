from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

import research_system.discovery.dossier as dossier_module
import research_system.discovery.runtime as runtime_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.discovery import DiscoveryRuntime, replay_discovery
from research_system.discovery.authority import subject_sha256
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierAdmissionRejected,
    DossierMember,
    PreparedDossierAdmission,
    RegisteredRoot,
    accepted_expected_set_hash,
    admission_profile_hash,
    prepare_dossier_admission as _prepare_dossier_admission,
    registered_root_identity_hash,
)
from research_system.errors import IntegrityError
from tests.research_system.integration.test_wp6_6_discovery_runtime import (
    ACTOR_ID,
    _command,
    _genesis,
    _runtime,
)


REPO = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = REPO / ".research-system/contracts/wp6-4"
PACKAGE = ".research-system/contracts/wp6-4/tda-scale-v1.0.3/package-index.json"
SCOPE = ".research-system/contracts/wp6-4/tda-scale-v1.0.1/scale01-scope-definition-blueprint.json"
PREFLIGHT = ".research-system/contracts/wp6-4/tda-scale-v1.0.3/scale01-gate6-preflight.json"
FIXTURE_PREFLIGHT = ".research-system/contracts/wp6-4/tda-scale-v1.0.1/scale01-fixture-preflight-evidence.json"
V1_INDEX = REPO / ".research-system/contracts/wp6-4/tda-scale-v1.0.1/package-index.json"
DOSSIER_AUTHORITY = ".research-system/contracts/wp6-6/tda-scale-dossier-expected-set-authority.json"
PATH_AUTHORITY = ".research-system/contracts/wp6-6/tda-scale-path-registration-authority.json"
TDA_RUNTIME_ROOT = Path(os.environ.get("TDL_REPOSITORY_ROOT", Path.home() / "TDL"))
VAULT = Path(os.environ.get("TDA_VAULT_ROOT", TDA_RUNTIME_ROOT / "vault"))
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not VAULT.exists() or not CONTRACT_ROOT.exists(),
        reason="real TDA dossier roots are not configured in this environment",
    ),
]


def _member(key: str, kind: str, relative_path: str, *, root_id: str = "repo") -> DossierMember:
    if root_id == "repo":
        root = CONTRACT_ROOT
        relative_path = PurePosixPath(relative_path).relative_to(".research-system/contracts/wp6-4").as_posix()
    else:
        root = VAULT
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
        admission_profile_hash("profile:wp6.6:dossier-admission", 1),
        members,
    )
    expected = replace(expected, content_hash=accepted_expected_set_hash(expected))
    roots = {
        "repo": RegisteredRoot("repo", CONTRACT_ROOT, 1, registered_root_identity_hash(CONTRACT_ROOT)),
        "vault": RegisteredRoot("vault", VAULT, 1, registered_root_identity_hash(VAULT)),
    }
    return expected, roots


def _rehash(expected: AcceptedExpectedSet) -> AcceptedExpectedSet:
    return replace(expected, content_hash=accepted_expected_set_hash(expected))


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _rehash_ledger(events: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    previous_hash = "0" * 64
    for position, event in enumerate(events, start=1):
        event["global_position"] = position
        event["previous_event_hash"] = previous_hash
        unsigned = dict(event)
        unsigned.pop("event_hash", None)
        event["event_hash"] = sha256_hex(canonical_bytes(unsigned))
        previous_hash = event["event_hash"]
    return tuple(events)


def _candidate_manifest(members: tuple[DossierMember, ...]) -> dict[str, object]:
    component_members = [member for member in members if member.member_kind == "component"]
    source_members = [member for member in members if member.member_kind in {"package_index", "evidence"}]
    components = [
        {
            "component_key": member.member_key,
            "component_kind": "immutable_programme_source",
            "schema_id": "ars://portfolio/source-component",
            "schema_version": "1.0.0",
            "root_id": member.root_id,
            "relative_path_or_object_ref": member.relative_path,
            "size_bytes": member.size_bytes,
            "sha256": member.sha256,
            "required": True,
            "dependency_keys": [],
            "permitted_consumers": ["portfolio-admission"],
            "confidentiality_class": "internal",
        }
        for member in component_members
    ]
    sources = [
        {
            "source_key": member.member_key,
            "source_kind": member.member_kind,
            "schema_or_media_type": "application/json",
            "root_id": member.root_id,
            "relative_path_or_locator": member.relative_path,
            "size_bytes": member.size_bytes,
            "sha256": member.sha256,
            "source_authority_class": "independently_observed",
            "required": True,
            "permitted_consumers": ["portfolio-admission"],
            "confidentiality_class": "internal",
            "independent_resolution_policy_id": "policy:wp6.6:registered-path-read",
            "independent_resolution_policy_hash": "7" * 64,
        }
        for member in source_members
    ]
    objects: list[dict[str, object]] = []
    object_refs: dict[str, dict[str, object]] = {}
    for index, member in enumerate(component_members, start=1):
        row: dict[str, object] = {
            "object_key": member.member_key,
            "portfolio_kind": "programme" if member.member_key == "MASTER-PROGRAMME" else "candidate_definition",
            "schema_id": "ars://portfolio/object",
            "schema_version": "1.0.0",
            "proposed_record_id": f"obj_019fed25-b33e-7740-b280-{1000 + index:012d}",
            "proposed_revision": 1,
            "source_keys": [member.member_key],
            "permitted_consumers": ["portfolio-catalogue"],
        }
        digest = _canonical_hash(row)
        row.update(blueprint_hash=digest, expected_content_hash=digest)
        objects.append(row)
        object_refs[member.member_key] = {"key": member.member_key, "revision": 1, "content_hash": digest}
    scope_row: dict[str, object] = {
        "scope_key": "tda-scale-programme",
        "scope_schema_id": "ars://portfolio/scope-definition",
        "scope_schema_version": "1.0.0",
        "proposed_scope_id": "obj_019fed25-b33e-7740-b280-000000001999",
        "proposed_revision": 1,
        "governing_object_keys": [member.member_key for member in component_members],
        "permitted_consumers": ["portfolio-catalogue"],
    }
    scope_digest = _canonical_hash(scope_row)
    scope_row.update(blueprint_hash=scope_digest, expected_content_hash=scope_digest)
    scope_ref = {"key": "tda-scale-programme", "revision": 1, "content_hash": scope_digest}
    edges: list[dict[str, object]] = []
    master = component_members[0]
    for index, member in enumerate(component_members[1:], start=1):
        edge: dict[str, object] = {
            "edge_key": f"{master.member_key}-contains-{member.member_key}",
            "edge_type": "contains",
            "proposed_edge_id": f"obj_019fed25-b33e-7740-b280-{2000 + index:012d}",
            "proposed_revision": 1,
            "from_key": object_refs[master.member_key],
            "to_key": object_refs[member.member_key],
            "required": True,
            "satisfaction_predicate_ref_or_null": None,
            "effective_scope_key": "tda-scale-programme",
        }
        edge["expected_content_hash"] = _canonical_hash(edge)
        edges.append(edge)
    relationship_members = deepcopy([*object_refs.values(), scope_ref])
    relationships = [
        {
            "relationship_key": "tda-scale-programme-closure",
            "relationship_kind": "contains",
            "ordered_member_keys_with_revisions_hashes": relationship_members,
            "relation_schema_id": "ars://portfolio/relation/dossier-six-family-closure",
            "relation_schema_version": "1.0.0",
            "relation_hash": _canonical_hash(relationship_members),
        }
    ]
    manifest: dict[str, object] = {
        "schema_id": "ars://portfolio/research-dossier-manifest",
        "schema_version": "1.0.0",
        "dossier_logical_id": "obj_019fed25-b33e-7740-b280-000000000913",
        "dossier_revision": 1,
        "package_version": "1.0.3",
        "purpose": "Provider-free admission of the exact TDA-scale programme dossier.",
        "author": "WP6.6 Portfolio Steward",
        "created_at": "2026-08-01T00:00:00Z",
        "governing_decisions": [],
        "component_count": len(components),
        "components": components,
        "source_dependency_count": len(sources),
        "source_dependencies": sources,
        "object_blueprints": objects,
        "scope_definition_blueprints": [scope_row],
        "dependency_edges": edges,
        "relationships": relationships,
        "object_count": len(objects),
        "scope_count": 1,
        "edge_count": len(edges),
        "relationship_count": 1,
        "admission_profile_ref": {
            "id": "profile:wp6.6:dossier-admission",
            "record_revision": 1,
            "content_hash": admission_profile_hash("profile:wp6.6:dossier-admission", 1),
        },
        "ownership_declarations": ["Successor owns only newly materialized semantic records."],
        "prohibited_adoption_claims": ["No source component is itself a portfolio object."],
    }
    manifest["closure_hash"] = _canonical_hash(manifest)
    return manifest


def _admit_with_default_manifest(**kwargs: Any) -> PreparedDossierAdmission:
    kwargs.setdefault("candidate_manifest", _candidate_manifest(kwargs["candidate_members"]))
    return _prepare_dossier_admission(**kwargs)


def test_real_tda_scale_dossier_prepares_deterministic_provider_free_atomic_batch() -> None:
    expected, roots = _subject()

    first = _admit_with_default_manifest(
        expected_set=expected,
        current_expected_set_revision=3,
        candidate_members=tuple(expected.members),
        registered_roots=roots,
    )
    second = _admit_with_default_manifest(
        expected_set=expected,
        current_expected_set_revision=3,
        candidate_members=tuple(expected.members),
        registered_roots=roots,
    )

    assert first == second
    assert first.events[0]["event_type"] == "ResearchDossierAdmitted"
    assert first.events[0]["payload"]["provider_execution"] == "forbidden"
    object_events = [event for event in first.events if event["event_type"] == "PortfolioObjectRegistered"]
    assert len(object_events) == 33
    assert [event["event_type"] for event in first.events].count("ScopeDefinitionRegistered") == 1
    assert len(first.observed_members) == 21
    assert all(event["payload"]["record_id"].startswith("obj_") for event in object_events)
    assert not {member.member_key for member in expected.members} & {
        event["payload"]["record_id"] for event in object_events
    }


def test_package_manifest_must_describe_the_exact_admitted_member_closure() -> None:
    expected, roots = _subject()
    manifest = _candidate_manifest(expected.members)
    manifest["components"] = manifest["components"][:-1]
    manifest["component_count"] = len(manifest["components"])
    manifest["closure_hash"] = _canonical_hash({key: value for key, value in manifest.items() if key != "closure_hash"})

    with pytest.raises(DossierAdmissionRejected, match="package_manifest_closure_mismatch"):
        _admit_with_default_manifest(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=expected.members,
            candidate_manifest=manifest,
            registered_roots=roots,
        )


@pytest.mark.parametrize(
    ("family", "mutation", "reason"),
    [
        (
            "object_blueprints",
            lambda row: row.__setitem__("proposed_record_id", "obj_019fed25-b33e-7740-b280-ffffffffffff"),
            "invalid_object_blueprint",
        ),
        (
            "dependency_edges",
            lambda row: row.__setitem__("to_key", deepcopy(row["from_key"])),
            "invalid_dependency_edge",
        ),
        (
            "relationships",
            lambda row: row["ordered_member_keys_with_revisions_hashes"][0].__setitem__("content_hash", "f" * 64),
            "invalid_relationship",
        ),
    ],
)
def test_semantic_blueprint_substitution_rejects_before_publication(
    family: str,
    mutation: Callable[[dict[str, Any]], None],
    reason: str,
) -> None:
    expected, roots = _subject()
    manifest = _candidate_manifest(expected.members)
    mutation(manifest[family][0])
    manifest["closure_hash"] = _canonical_hash({key: value for key, value in manifest.items() if key != "closure_hash"})
    with pytest.raises(DossierAdmissionRejected, match=reason):
        _admit_with_default_manifest(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=expected.members,
            candidate_manifest=manifest,
            registered_roots=roots,
        )


def test_materialized_identity_cannot_collide_with_dossier_identity() -> None:
    expected, roots = _subject()
    manifest = _candidate_manifest(expected.members)
    edge_row = manifest["dependency_edges"][0]
    edge_row["proposed_edge_id"] = expected.dossier_id
    edge_preimage = {key: value for key, value in edge_row.items() if key != "expected_content_hash"}
    edge_row["expected_content_hash"] = _canonical_hash(edge_preimage)
    manifest["closure_hash"] = _canonical_hash({key: value for key, value in manifest.items() if key != "closure_hash"})
    with pytest.raises(DossierAdmissionRejected, match="immutable_identity_collision"):
        _admit_with_default_manifest(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=expected.members,
            candidate_manifest=manifest,
            registered_roots=roots,
        )


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
def test_candidate_missing_extra_duplicate_tamper_or_traversal_rejects_without_output(
    mutation: Callable[[AcceptedExpectedSet], tuple[DossierMember, ...]],
    reason: str,
) -> None:
    expected, roots = _subject()
    with pytest.raises(DossierAdmissionRejected, match=reason):
        _admit_with_default_manifest(
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
        (
            {
                "registered_roots": {
                    "repo": RegisteredRoot("repo", tmp_path, 1, registered_root_identity_hash(tmp_path))
                }
            },
            "incomplete_package",
        ),
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
            _admit_with_default_manifest(**arguments)


def test_unregistered_and_traversing_expected_paths_are_rejected() -> None:
    expected, roots = _subject()
    attacks = (
        (replace(expected.members[0], root_id="foreign"), "unregistered_root"),
        (replace(expected.members[0], relative_path="../package-index.json"), "path_traversal"),
    )
    for attacked_member, reason in attacks:
        attacked = _rehash(replace(expected, members=(attacked_member, *expected.members[1:])))
        with pytest.raises(DossierAdmissionRejected, match=reason):
            _admit_with_default_manifest(
                expected_set=attacked,
                current_expected_set_revision=3,
                candidate_members=attacked.members,
                registered_roots=roots,
            )


def test_registered_root_physical_identity_mismatch_rejects_before_publication() -> None:
    expected, roots = _subject()
    replaced = {**roots, "repo": replace(roots["repo"], registration_hash="0" * 64)}
    with pytest.raises(DossierAdmissionRejected, match="path_registration_identity_mismatch"):
        _admit_with_default_manifest(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=expected.members,
            registered_roots=replaced,
        )


def test_root_replacement_between_identity_check_and_read_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "registered"
    displaced = tmp_path / "displaced"
    root.mkdir()
    (root / "member.json").write_text("original", encoding="utf-8")
    registered = RegisteredRoot("repo", root, 1, registered_root_identity_hash(root))
    member = DossierMember("member", "evidence", "repo", "member.json", 8, "0" * 64, "prov", 1, "0" * 64)
    replaced = False

    def replace_root(_path: Path) -> None:
        nonlocal replaced
        if replaced:
            return
        replaced = True
        root.rename(displaced)
        root.mkdir()
        (root / "member.json").write_text("original", encoding="utf-8")

    monkeypatch.setattr(dossier_module, "_after_root_identity_check", replace_root)
    with pytest.raises(DossierAdmissionRejected, match="path_registration_identity_changed"):
        dossier_module._open_registered_member(member, {"repo": registered})


def test_alias_probe_oserror_is_mapped_to_incomplete_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "registered"
    root.mkdir()
    (root / "member.json").write_text("content", encoding="utf-8")
    registered = RegisteredRoot("repo", root, 1, registered_root_identity_hash(root))
    member = DossierMember("member", "evidence", "repo", "member.json", 7, "0" * 64, "prov", 1, "0" * 64)
    original = Path.is_symlink

    def fail_probe(path: Path) -> bool:
        if path.name == "member.json":
            raise OSError("injected alias probe failure")
        return original(path)

    monkeypatch.setattr(Path, "is_symlink", fail_probe)
    with pytest.raises(DossierAdmissionRejected, match="incomplete_package"):
        dossier_module._open_registered_member(member, {"repo": registered})


def test_hardlinked_member_is_rejected_as_unproven_identity(tmp_path: Path) -> None:
    root = tmp_path / "registered"
    root.mkdir()
    source = root / "source.json"
    source.write_text("exact", encoding="utf-8")
    os.link(source, root / "member.json")
    registered = RegisteredRoot("repo", root, 1, registered_root_identity_hash(root))
    member = DossierMember("member", "evidence", "repo", "member.json", 5, "0" * 64, "prov", 1, "0" * 64)

    with pytest.raises(DossierAdmissionRejected, match="path_identity_unproven"):
        dossier_module._open_registered_member(member, {"repo": registered})


def test_member_swap_after_identity_capture_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "registered"
    root.mkdir()
    candidate = root / "member.json"
    candidate.write_text("exact", encoding="utf-8")
    registered = RegisteredRoot("repo", root, 1, registered_root_identity_hash(root))
    member = DossierMember("member", "evidence", "repo", "member.json", 5, "0" * 64, "prov", 1, "0" * 64)

    def swap_member(path: Path) -> None:
        path.rename(root / "displaced.json")
        path.write_text("exact", encoding="utf-8")

    monkeypatch.setattr(dossier_module, "_after_member_identity_check", swap_member)
    with pytest.raises(DossierAdmissionRejected, match="path_identity_unproven"):
        dossier_module._open_registered_member(member, {"repo": registered})


def test_observed_content_tamper_is_rejected_without_an_event_batch(tmp_path: Path) -> None:
    expected, _ = _subject()
    for member in expected.members:
        target = tmp_path / member.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        source_root = CONTRACT_ROOT if member.root_id == "repo" else VAULT
        target.write_bytes((source_root / member.relative_path).read_bytes())
    (tmp_path / expected.members[-1].relative_path).write_text("tampered", encoding="utf-8")

    with pytest.raises(DossierAdmissionRejected, match="member_content_tampered"):
        _admit_with_default_manifest(
            expected_set=expected,
            current_expected_set_revision=3,
            candidate_members=tuple(expected.members),
            registered_roots={
                "repo": RegisteredRoot("repo", tmp_path, 1, registered_root_identity_hash(tmp_path)),
                "vault": RegisteredRoot("vault", tmp_path, 1, registered_root_identity_hash(tmp_path)),
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
    accepted_type = "DossierExpectedSetAccepted" if kind == "dossier_expected_set" else "PathRegistrationAccepted"
    accepted_event = next(
        event
        for event in reversed(tuple(runtime.ledger.iter_events()))
        if event["payload"].get("authority_event_type") == accepted_type
    )
    authority = replay_discovery(runtime.ledger.iter_events())["authorities"][kind]
    assert authority["transaction_id"] == accepted_event["transaction_id"]


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
            "admission_profile_decision": {
                "dispatchable": False,
                "profile_id": expected.admission_profile_id,
                "profile_revision": expected.admission_profile_revision,
                "provider_execution": "forbidden",
            },
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
            "environment_scope": "owner-accepted-stephen-windows-tda-runtime",
            "identity_scheme": "windows-file-id-v1",
            "registered_roots": json.loads((REPO / PATH_AUTHORITY).read_bytes())["registered_roots"],
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
            "candidate_manifest": _candidate_manifest(expected.members),
        },
    )

    incomplete_manifest = deepcopy(command)
    manifest = incomplete_manifest["payload"]["candidate_manifest"]
    manifest["components"] = manifest["components"][:-1]
    manifest["component_count"] -= 1
    manifest["closure_hash"] = _canonical_hash({key: value for key, value in manifest.items() if key != "closure_hash"})
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(DossierAdmissionRejected, match="package_manifest_closure_mismatch"):
        runtime.submit(incomplete_manifest)
    assert tuple(runtime.ledger.iter_events()) == before

    receipt = runtime.submit(command)
    replayed = replay_discovery(runtime.ledger.iter_events())

    assert receipt.status == "accepted"
    assert replayed["authorities"]["dossier_expected_set"]["status"] == "accepted"
    assert replayed["authorities"]["path_registration"]["status"] == "accepted"
    assert replayed["dossiers"][expected.dossier_id]["member_count"] == 21

    omitted = [deepcopy(event) for event in runtime.ledger.iter_events()]
    omitted.remove(next(event for event in omitted if event["event_type"] == "PortfolioObjectRegistered"))
    with pytest.raises(IntegrityError, match="materialization closure mismatch"):
        replay_discovery(_rehash_ledger(omitted))

    relationship_omitted = [deepcopy(event) for event in runtime.ledger.iter_events()]
    admission = next(event for event in relationship_omitted if event["event_type"] == "ResearchDossierAdmitted")
    admission["payload"]["relationships"] = []
    admission["payload"]["relationship_count"] = 0
    with pytest.raises(IntegrityError, match="materialization closure mismatch"):
        replay_discovery(_rehash_ledger(relationship_omitted))

    cross_namespace = [deepcopy(event) for event in runtime.ledger.iter_events()]
    object_event = next(
        event
        for event in cross_namespace
        if event["event_type"] == "PortfolioObjectRegistered"
        and event["payload"]["portfolio_kind"] == "dependency_edge"
    )
    blueprint = object_event["payload"]["blueprint"]
    object_event["stream_id"] = expected.dossier_id
    object_event["payload"]["record_id"] = expected.dossier_id
    blueprint["proposed_edge_id"] = expected.dossier_id
    blueprint_preimage = {key: value for key, value in blueprint.items() if key != "expected_content_hash"}
    blueprint_hash = _canonical_hash(blueprint_preimage)
    blueprint["expected_content_hash"] = blueprint_hash
    object_event["payload"]["content_sha256"] = blueprint_hash
    with pytest.raises(IntegrityError, match="Portfolio object identity collision"):
        replay_discovery(_rehash_ledger(cross_namespace))


@pytest.mark.parametrize("attack", ["unrelated_tracked_file", "altered_expected_set", "git_timeout"])
@pytest.mark.integration
def test_public_observation_rejects_authority_content_not_serialized_by_git_bytes(
    tmp_path: Path,
    attack: str,
    monkeypatch: pytest.MonkeyPatch,
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
    elif attack == "altered_expected_set":
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
    expected_error = "content does not match registered subject"
    if attack == "git_timeout":
        monkeypatch.setattr(
            runtime_module.subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(args[0], 10)),
        )
        expected_error = "authority file lacks current Git identity"
    with pytest.raises(IntegrityError, match=expected_error):
        runtime.submit(observe)
    assert tuple(runtime.ledger.iter_events()) == before


@pytest.mark.parametrize(
    "invalid_root",
    [
        None,
        {},
        {"path": "$TDA_VAULT_ROOT"},
        {"path": "$TDA_VAULT_ROOT", "root_id": "vault", "registration_revision": 1, "registration_hash": "0" * 64},
    ],
)
def test_dossier_runtime_rejects_malformed_registered_root_before_field_access(
    tmp_path: Path, invalid_root: object
) -> None:
    expected, _ = _subject()
    runtime = _runtime(tmp_path)
    projection = {
        "authorities": {
            "dossier_expected_set": {
                "status": "accepted",
                "subject": {"expected_set": json.loads(json.dumps(asdict(expected)))},
            },
            "path_registration": {
                "status": "accepted",
                "subject": {"registered_roots": [invalid_root]},
            },
        }
    }
    command = Command(
        _command(
            "AdmitResearchDossier",
            expected.dossier_id,
            0,
            {
                "row_id": "OR-028",
                "dossier_id": expected.dossier_id,
                "expected_set_id": expected.expected_set_id,
                "candidate_members": [asdict(member) for member in expected.members],
                "candidate_manifest": _candidate_manifest(expected.members),
            },
        )
    )

    with pytest.raises(IntegrityError, match="invalid registered root"):
        runtime._prepare_dossier(command, projection)
