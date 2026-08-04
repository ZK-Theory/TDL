from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from research_system import wp64_scale01 as scale01


REPO_ROOT = Path(__file__).resolve().parents[3]
_SHA_FIELDS = (
    "event_tail_sha256",
    "object_set_sha256",
    "scope_definition_set_sha256",
    "dispatch_set_sha256",
    "result_set_sha256",
    "claim_set_sha256",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_bytes())


def _documents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        _load_json(REPO_ROOT / scale01.PACKAGE_INDEX_PATH),
        _load_json(REPO_ROOT / scale01.BLUEPRINT_PATH),
        _load_json(REPO_ROOT / scale01.PREFLIGHT_PATH),
    )


def _refresh_observation(observation: dict[str, Any]) -> None:
    observation["fixture_count"] = len(observation["fixtures"])
    observation["fixture_set_sha256"] = scale01.derive_fixture_set_sha256(observation["fixtures"])
    observation["alignment_count"] = len(observation["alignments"])
    observation["observation_id"] = scale01.derive_fixture_observation_id(observation)


def _refresh_evidence(evidence: dict[str, Any]) -> None:
    evidence["evidence_id"] = scale01.derive_no_write_evidence_id(evidence)


def _tree_snapshot(root: Path) -> tuple[tuple[str, int, str], ...]:
    rows = []
    for path in sorted((candidate for candidate in root.rglob("*") if candidate.is_file())):
        raw = path.read_bytes()
        rows.append((path.relative_to(root).as_posix(), len(raw), hashlib.sha256(raw).hexdigest()))
    return tuple(rows)


def _valid_w11_manifest() -> dict[str, Any]:
    record_ref = {
        "id": "obj_00000000-0000-7000-8000-000000000001",
        "record_revision": 1,
        "content_hash": "0" * 64,
    }
    return {
        "schema_id": "ars://portfolio/research-dossier-manifest",
        "schema_version": "1.0.0",
        "dossier_logical_id": "scale01-synthetic-dossier",
        "dossier_revision": 1,
        "package_version": "1.0.0",
        "purpose": "Synthetic schema control only",
        "author": "synthetic-actor",
        "created_at": "2026-08-03T00:00:00Z",
        "governing_decisions": [],
        "component_count": 0,
        "components": [],
        "source_dependency_count": 0,
        "source_dependencies": [],
        "object_blueprints": [],
        "scope_definition_blueprints": [],
        "dependency_edges": [],
        "relationships": [],
        "object_count": 0,
        "scope_count": 0,
        "edge_count": 0,
        "relationship_count": 0,
        "admission_profile_ref": record_ref,
        "ownership_declarations": ["synthetic control only"],
        "prohibited_adoption_claims": ["not admission authority"],
        "closure_hash": "0" * 64,
    }


@pytest.fixture
def synthetic_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    fixture_root = tmp_path / "legacy-fixtures"
    scratch_root = tmp_path / "attempt-scratch"
    protected_root = tmp_path / "protected-surfaces"
    fixture_root.mkdir()
    scratch_root.mkdir()
    protected_root.mkdir()

    protected_surface_paths = {}
    for field in _SHA_FIELDS:
        path = protected_root / f"{field.removesuffix('_sha256')}.json"
        path.write_bytes(f"synthetic:{field}\n".encode())
        protected_surface_paths[field] = path

    expected_rows = []
    observation_rows = []
    fixture_paths = []
    for template in scale01.EXPECTED_FIXTURE_TUPLE:
        path = fixture_root / template["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = f"synthetic:{template['fixture_alias']}\n".encode()
        path.write_bytes(raw)
        metadata = path.stat()
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        expected = dict(template)
        expected["raw_sha256"] = raw_sha256
        expected_rows.append(expected)
        observation_rows.append(
            {
                **expected,
                "physical_path": path.resolve(strict=True).as_posix(),
                "byte_size": len(raw),
                "volume_id": str(metadata.st_dev),
                "stable_file_id": f"dev:{metadata.st_dev}:ino:{metadata.st_ino}",
                "file_write_capable": False,
            }
        )
        fixture_paths.append(path)

    monkeypatch.setattr(scale01, "EXPECTED_FIXTURE_TUPLE", tuple(expected_rows))
    for path in fixture_paths:
        path.chmod(0o444)

    alignments = []
    for geometry_alias, binding in scale01.EXPECTED_ALIGNMENT_BINDINGS.items():
        pairs = [
            {
                "row_index": index,
                "membership_id_sha256": hashlib.sha256(f"{geometry_alias}:{index}".encode()).hexdigest(),
            }
            for index in range(2)
        ]
        alignments.append(
            {
                "geometry_alias": geometry_alias,
                "embedding_fixture_alias": binding[0],
                "trajectory_fixture_alias": binding[1],
                "checkpoint_fixture_alias": binding[2],
                "scratch_row_index_relative_path": (f"scale-01/row-indices/{geometry_alias.casefold()}.json"),
                "row_count": len(pairs),
                "membership_count": len(pairs),
                "pair_count": len(pairs),
                **scale01.derive_alignment_hashes(pairs),
                "aligned": True,
                "pairs": pairs,
            }
        )

    observation = {
        "schema_id": "ars://contracts/wp6-4/scale01-fixture-observation",
        "schema_version": "1.0.1",
        "lifecycle_status": "produced_unreviewed",
        "observation_id": "fobs_" + "0" * 64,
        "fixture_root": {
            "root_id": "synthetic-scale01-fixture-root",
            **scale01.path_identity(fixture_root),
            "reparse_chain": [],
            "symlink_free": True,
            "casefold_unique": True,
            "unicode_nfc_unique": True,
            "root_write_capable": False,
            "read_only_enforcement": "synthetic_read_only_contract",
            "mutation_probe_performed": False,
        },
        "fixture_count": len(observation_rows),
        "fixture_set_sha256": scale01.derive_fixture_set_sha256(observation_rows),
        "fixtures": observation_rows,
        "alignment_count": len(alignments),
        "alignments": alignments,
    }
    _refresh_observation(observation)

    pre_snapshot = scale01.snapshot_protected_state(
        fixture_root,
        protected_surface_paths=protected_surface_paths,
    )
    state = pre_snapshot.evidence_state()
    evidence = {
        "schema_id": "ars://contracts/wp6-4/scale01-no-write-evidence",
        "schema_version": "1.0.1",
        "lifecycle_status": "produced_unreviewed",
        "evidence_id": "nw_" + "0" * 64,
        "fixture_root": scale01.path_identity(fixture_root),
        "scratch_root": scale01.path_identity(scratch_root),
        "scratch_disjoint": True,
        "failure_injected": False,
        "pre_state": deepcopy(state),
        "post_state": deepcopy(state),
        "comparison": {
            "legacy_entry_sets_equal": True,
            "legacy_bytes_equal": True,
            "event_tail_unchanged": True,
            "object_set_unchanged": True,
            "scope_definition_set_unchanged": True,
            "dispatch_set_unchanged": True,
            "result_set_unchanged": True,
            "claim_set_unchanged": True,
        },
        "legacy_write_paths": [],
        "publication_paths": [],
        "rollback_status": "not_required_zero_publication",
    }
    _refresh_evidence(evidence)

    try:
        yield {
            "fixture_root": fixture_root,
            "scratch_root": scratch_root,
            "fixture_paths": fixture_paths,
            "protected_surface_paths": protected_surface_paths,
            "pre_snapshot": pre_snapshot,
            "observation": observation,
            "evidence": evidence,
        }
    finally:
        for path in fixture_paths:
            if path.exists():
                path.chmod(0o666)


def test_static_candidate_is_valid_pending_and_non_dispatchable() -> None:
    assert scale01.verify_static_scale01_candidate(REPO_ROOT) == {
        "admission_status": "pending_wp6_6",
        "dispatchable": False,
        "execution_authorized": False,
        "lifecycle_status": "produced_unreviewed",
    }


@pytest.mark.parametrize("dependency_index", range(3))
def test_each_current_dependency_rejects_a_coordinated_identity_substitution(dependency_index: int) -> None:
    package_index, blueprint, preflight = _documents()
    replacement = package_index["source_dependencies"][(dependency_index + 1) % 3]
    row = package_index["source_dependencies"][dependency_index]
    for field in ("repository_path", "raw_bytes", "raw_sha256", "git_blob_id"):
        row[field] = replacement[field]

    with pytest.raises(scale01.Scale01VerificationError, match="source dependency tuple"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


@pytest.mark.parametrize("dependency_index", range(5))
@pytest.mark.parametrize(("field", "value"), (("exact_ref", "obj_fabricated"), ("status", "accepted")))
def test_each_pending_dependency_rejects_a_mismatched_state(dependency_index: int, field: str, value: str) -> None:
    package_index, blueprint, preflight = _documents()
    preflight["dependencies"][dependency_index][field] = value

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("admission_status", "admitted"),
        ("dispatchable", True),
        ("execution_authorized", True),
    ),
)
def test_preflight_status_cannot_be_promoted(field: str, value: Any) -> None:
    package_index, blueprint, preflight = _documents()
    preflight[field] = value

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("lifecycle_status", "accepted"),
        ("dispatchable", True),
        ("execution_authorized", True),
    ),
)
def test_package_candidate_status_cannot_be_promoted(field: str, value: Any) -> None:
    package_index, blueprint, preflight = _documents()
    package_index[field] = value

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


@pytest.mark.parametrize("document_index", (0, 2))
def test_candidate_requires_immutable_supersession(document_index: int) -> None:
    documents = list(_documents())
    documents[document_index]["supersession_policy"] = "mutate_in_place"

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, *documents)


@pytest.mark.parametrize(
    "field",
    ("admission_event_ref", "dispatch_ref", "result_ref", "claim_ref", "owner_acceptance_ref"),
)
def test_pending_preflight_rejects_non_null_authority_references(field: str) -> None:
    package_index, blueprint, preflight = _documents()
    preflight[field] = "obj_fabricated"

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


@pytest.mark.parametrize("field", ("research_claim", "pilot_claim", "result_claim"))
def test_pending_preflight_rejects_research_pilot_and_result_claims(field: str) -> None:
    package_index, blueprint, preflight = _documents()
    preflight[field] = "fabricated claim"

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


def test_scope_definition_payload_uses_behavioral_datetime_format_checking() -> None:
    package_index, blueprint, preflight = _documents()
    blueprint["effective_at"] = "2026-13-40T25:61:00Z"

    with pytest.raises(scale01.Scale01VerificationError, match="date-time"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


def test_scope_definition_payload_is_closed() -> None:
    package_index, blueprint, preflight = _documents()
    blueprint["final_object_count"] = 1

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


def test_w11_manifest_cannot_self_declare_scale01_admission() -> None:
    manifest = _valid_w11_manifest()
    scale01.verify_w11_dossier_manifest(REPO_ROOT, manifest)
    manifest["admission_status"] = "admitted"

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_w11_dossier_manifest(REPO_ROOT, manifest)


@pytest.mark.parametrize("target", ("predecessor", "component"))
def test_v100_byte_identity_cannot_be_mutated_in_the_candidate(target: str) -> None:
    package_index, blueprint, preflight = _documents()
    if target == "predecessor":
        package_index["predecessor_manifest"]["raw_sha256"] = "f" * 64
    else:
        package_index["reused_components"][0]["raw_sha256"] = "f" * 64

    with pytest.raises(scale01.Scale01VerificationError, match="v1.0.0"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


def test_candidate_local_changed_component_hash_is_recomputed() -> None:
    package_index, blueprint, preflight = _documents()
    package_index["changed_components"][0]["raw_sha256"] = "f" * 64

    with pytest.raises(scale01.Scale01VerificationError, match="changed component"):
        scale01.verify_scale01_documents(REPO_ROOT, package_index, blueprint, preflight)


def test_public_preflight_rejects_caller_selected_protected_surface_mapping(
    synthetic_bundle: dict[str, Any],
) -> None:
    alternate_root = synthetic_bundle["scratch_root"] / "coordinated-alternate"
    alternate_root.mkdir()
    alternate_paths = {}
    for field in _SHA_FIELDS:
        path = alternate_root / f"{field}.json"
        path.write_bytes(f"alternate:{field}\n".encode())
        alternate_paths[field] = path

    alternate_snapshot = scale01.snapshot_protected_state(
        synthetic_bundle["fixture_root"],
        protected_surface_paths=alternate_paths,
    )
    alternate_state = alternate_snapshot.evidence_state()
    evidence = deepcopy(synthetic_bundle["evidence"])
    evidence["pre_state"] = deepcopy(alternate_state)
    evidence["post_state"] = deepcopy(alternate_state)
    _refresh_evidence(evidence)

    with pytest.raises(TypeError, match="protected_surface_paths"):
        scale01.verify_scale01_preflight_candidate(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            synthetic_bundle["observation"],
            evidence,
            protected_surface_paths=alternate_paths,
        )


def test_public_preflight_fails_closed_while_canonical_foundation_is_pending(
    synthetic_bundle: dict[str, Any],
) -> None:
    with pytest.raises(
        scale01.Scale01VerificationError,
        match="canonical foundation dependency is pending",
    ):
        scale01.verify_scale01_preflight_candidate(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            synthetic_bundle["observation"],
            synthetic_bundle["evidence"],
        )


def test_fixture_tuple_rejects_coordinated_omission(synthetic_bundle: dict[str, Any]) -> None:
    observation = deepcopy(synthetic_bundle["observation"])
    observation["fixtures"].pop()
    _refresh_observation(observation)

    with pytest.raises(scale01.Scale01VerificationError, match="independent fixed fixture tuple"):
        scale01.verify_fixture_observation(REPO_ROOT, synthetic_bundle["fixture_root"], observation)


def test_fixture_path_rejects_traversal(synthetic_bundle: dict[str, Any]) -> None:
    observation = deepcopy(synthetic_bundle["observation"])
    observation["fixtures"][0]["relative_path"] = "../escape.json"
    _refresh_observation(observation)

    with pytest.raises(scale01.Scale01VerificationError, match="traversal"):
        scale01.verify_fixture_observation(REPO_ROOT, synthetic_bundle["fixture_root"], observation)


def test_fixture_paths_reject_casefold_aliases(synthetic_bundle: dict[str, Any]) -> None:
    observation = deepcopy(synthetic_bundle["observation"])
    alias = deepcopy(observation["fixtures"][0])
    alias["fixture_alias"] = "CASE-ALIAS"
    alias["relative_path"] = alias["relative_path"].upper()
    observation["fixtures"].append(alias)
    _refresh_observation(observation)

    with pytest.raises(scale01.Scale01VerificationError, match="case-fold"):
        scale01.verify_fixture_observation(REPO_ROOT, synthetic_bundle["fixture_root"], observation)


def test_fixture_path_rejects_non_nfc_unicode(synthetic_bundle: dict[str, Any]) -> None:
    observation = deepcopy(synthetic_bundle["observation"])
    observation["fixtures"][0]["relative_path"] = "re\u0301sults/non-nfc.json"
    _refresh_observation(observation)

    with pytest.raises(scale01.Scale01VerificationError, match="Unicode NFC"):
        scale01.verify_fixture_observation(REPO_ROOT, synthetic_bundle["fixture_root"], observation)


def test_fixture_root_rejects_reparse_or_symlink_state(
    synthetic_bundle: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_root = synthetic_bundle["fixture_root"].resolve(strict=True)
    original = scale01._is_reparse

    def injected_reparse(path: Path) -> bool:
        return path.resolve(strict=True) == fixture_root or original(path)

    monkeypatch.setattr(scale01, "_is_reparse", injected_reparse)
    with pytest.raises(scale01.Scale01VerificationError, match="symlink or reparse"):
        scale01.verify_fixture_observation(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["observation"],
        )


def test_foreign_but_byte_valid_fixture_root_is_rejected(synthetic_bundle: dict[str, Any], tmp_path: Path) -> None:
    foreign_root = tmp_path / "foreign-valid-root"
    foreign_paths = []
    for row in scale01.EXPECTED_FIXTURE_TUPLE:
        path = foreign_root / row["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic:{row['fixture_alias']}\n".encode())
        path.chmod(0o444)
        foreign_paths.append(path)
    try:
        with pytest.raises(scale01.Scale01VerificationError, match="fixture root"):
            scale01.verify_fixture_observation(REPO_ROOT, foreign_root, synthetic_bundle["observation"])
    finally:
        for path in foreign_paths:
            path.chmod(0o666)


def test_write_capable_root_claim_is_rejected(synthetic_bundle: dict[str, Any]) -> None:
    observation = deepcopy(synthetic_bundle["observation"])
    observation["fixture_root"]["root_write_capable"] = True
    _refresh_observation(observation)

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_fixture_observation(REPO_ROOT, synthetic_bundle["fixture_root"], observation)


def test_actual_write_capable_fixture_file_is_rejected(synthetic_bundle: dict[str, Any]) -> None:
    path = synthetic_bundle["fixture_paths"][0]
    path.chmod(0o666)
    try:
        with pytest.raises(scale01.Scale01VerificationError, match="write-capable"):
            scale01.verify_fixture_observation(
                REPO_ROOT,
                synthetic_bundle["fixture_root"],
                synthetic_bundle["observation"],
            )
    finally:
        path.chmod(0o444)


def test_row_index_membership_alignment_is_recomputed(synthetic_bundle: dict[str, Any]) -> None:
    observation = deepcopy(synthetic_bundle["observation"])
    observation["alignments"][0]["membership_count"] += 1
    _refresh_observation(observation)

    with pytest.raises(scale01.Scale01VerificationError, match="membership count"):
        scale01.verify_fixture_observation(REPO_ROOT, synthetic_bundle["fixture_root"], observation)


@pytest.mark.parametrize("field", _SHA_FIELDS)
def test_no_write_evidence_rejects_each_changed_protected_surface(synthetic_bundle: dict[str, Any], field: str) -> None:
    synthetic_bundle["protected_surface_paths"][field].write_bytes(b"mutated protected bytes\n")

    with pytest.raises(scale01.Scale01VerificationError, match="pre/post protected state"):
        scale01.verify_no_write_evidence(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            synthetic_bundle["evidence"],
            pre_snapshot=synthetic_bundle["pre_snapshot"],
        )


def test_no_write_evidence_rejects_coordinated_caller_hash_substitution(
    synthetic_bundle: dict[str, Any],
) -> None:
    evidence = deepcopy(synthetic_bundle["evidence"])
    original_paths = dict(synthetic_bundle["protected_surface_paths"])
    original_bytes = {field: path.read_bytes() for field, path in original_paths.items()}
    substitute_root = synthetic_bundle["scratch_root"] / "coordinated-substitute"
    substitute_root.mkdir()
    for field in _SHA_FIELDS:
        raw = f"substitute:{field}\n".encode()
        substitute_path = substitute_root / f"{field}.json"
        substitute_path.write_bytes(raw)
        fabricated_hash = hashlib.sha256(raw).hexdigest()
        evidence["pre_state"][field] = fabricated_hash
        evidence["post_state"][field] = fabricated_hash
        synthetic_bundle["protected_surface_paths"][field] = substitute_path
    _refresh_evidence(evidence)

    with pytest.raises(scale01.Scale01VerificationError, match="pre/post protected state"):
        scale01.verify_no_write_evidence(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            evidence,
            pre_snapshot=synthetic_bundle["pre_snapshot"],
        )
    assert {field: path.read_bytes() for field, path in original_paths.items()} == original_bytes


def test_no_write_evidence_rejects_same_path_surface_replacement(
    synthetic_bundle: dict[str, Any],
) -> None:
    path = synthetic_bundle["protected_surface_paths"]["object_set_sha256"]
    raw = path.read_bytes()
    path.rename(path.with_suffix(".original"))
    path.write_bytes(raw)

    with pytest.raises(scale01.Scale01VerificationError, match="protected-path binding"):
        scale01.verify_no_write_evidence(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            synthetic_bundle["evidence"],
            pre_snapshot=synthetic_bundle["pre_snapshot"],
        )


def test_no_write_evidence_rejects_changed_legacy_set(synthetic_bundle: dict[str, Any]) -> None:
    evidence = deepcopy(synthetic_bundle["evidence"])
    evidence["post_state"]["legacy_entries"][0]["byte_size"] += 1
    ordered = sorted(
        evidence["post_state"]["legacy_entries"],
        key=lambda row: row["relative_path"],
    )
    evidence["post_state"]["legacy_entry_set_sha256"] = scale01.canonical_sha256(ordered)
    _refresh_evidence(evidence)

    with pytest.raises(scale01.Scale01VerificationError, match="pre/post protected state"):
        scale01.verify_no_write_evidence(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            evidence,
            pre_snapshot=synthetic_bundle["pre_snapshot"],
        )


def test_no_write_evidence_requires_disjoint_scratch(synthetic_bundle: dict[str, Any]) -> None:
    evidence = deepcopy(synthetic_bundle["evidence"])
    evidence["scratch_root"] = scale01.path_identity(synthetic_bundle["fixture_root"])
    _refresh_evidence(evidence)

    with pytest.raises(scale01.Scale01VerificationError, match="not disjoint"):
        scale01.verify_no_write_evidence(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["fixture_root"],
            evidence,
            pre_snapshot=synthetic_bundle["pre_snapshot"],
        )


def test_no_write_evidence_rejects_a_legacy_write_record(synthetic_bundle: dict[str, Any]) -> None:
    evidence = deepcopy(synthetic_bundle["evidence"])
    evidence["legacy_write_paths"] = ["results/forbidden.json"]
    _refresh_evidence(evidence)

    with pytest.raises(scale01.Scale01VerificationError, match="schema violation"):
        scale01.verify_no_write_evidence(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            evidence,
            pre_snapshot=synthetic_bundle["pre_snapshot"],
        )


def test_public_preflight_rejects_before_failure_injection_and_has_zero_publication(
    synthetic_bundle: dict[str, Any],
) -> None:
    observed_roots = (
        synthetic_bundle["fixture_root"],
        synthetic_bundle["scratch_root"],
        REPO_ROOT / scale01.PACKAGE_DIR,
    )
    before = tuple(_tree_snapshot(root) for root in observed_roots)
    injection_called = False

    def fail_before_publication() -> None:
        nonlocal injection_called
        injection_called = True
        raise RuntimeError("synthetic failure")

    with pytest.raises(
        scale01.Scale01VerificationError,
        match="canonical foundation dependency is pending",
    ):
        scale01.verify_scale01_preflight_candidate(
            REPO_ROOT,
            synthetic_bundle["fixture_root"],
            synthetic_bundle["scratch_root"],
            synthetic_bundle["observation"],
            synthetic_bundle["evidence"],
            failure_injector=fail_before_publication,
        )

    assert not injection_called
    assert tuple(_tree_snapshot(root) for root in observed_roots) == before
