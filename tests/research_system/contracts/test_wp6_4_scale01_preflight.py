import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from research_system.evidence.wp6_4_scale01_preflight import verify_candidate_package
from research_system.evidence.wp6_4_scale01_preflight import verify_failure_injection


REPO_ROOT = Path(__file__).parents[3]
PACKAGE_ROOT = REPO_ROOT / ".research-system/contracts/wp6-4/tda-scale-v1.0.1"


def _copy_package(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    copied = tmp_path / "candidate"
    shutil.copytree(PACKAGE_ROOT, copied)
    return copied


def _load(package_root: Path, name: str) -> dict:
    return json.loads((package_root / name).read_text(encoding="utf-8"))


def _dump(package_root: Path, name: str, value: dict) -> None:
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    (package_root / name).write_bytes(data.encode("utf-8"))


def _assert_rejected(tmp_path: Path, name: str, value: dict) -> None:
    package_root = _copy_package(tmp_path)
    _dump(package_root, name, value)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


def test_scale01_candidate_verifies_only_as_pending_and_non_dispatchable():
    result = verify_candidate_package(REPO_ROOT)

    assert result["package_version"] == "1.0.1"
    assert result["preflight"]["admission_status"] == "pending_wp6_6"
    assert result["preflight"]["dispatchable"] is False
    assert result["preflight"]["execution_authorized"] is False


@pytest.mark.parametrize(
    "field",
    ["schema_id", "schema_version", "path", "subject_commit", "subject_tree", "byte_length", "raw_sha256", "git_blob"],
)
def test_candidate_identity_substitution_is_rejected(tmp_path, field):
    package_root = _copy_package(tmp_path)
    package_index = _load(package_root, "package-index.json")
    entry = package_index["artifact_bindings"][0]
    if field == "schema_id":
        entry[field] = "ars://contracts/wp6-4/foreign"
    elif field == "schema_version":
        entry[field] = "1.0.0"
    elif field == "path":
        entry[field] = package_index["artifact_bindings"][1]["path"]
    elif field == "byte_length":
        entry[field] = entry[field] + 1
    elif field == "subject_commit":
        entry[field] = "1" * 40
    elif field == "subject_tree":
        entry[field] = "2" * 40
    elif field == "raw_sha256":
        entry[field] = "1" * 64
    else:
        entry[field] = "1" * 40
    _dump(package_root, "package-index.json", package_index)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


def test_governing_scope_schema_identity_mutation_is_rejected(tmp_path):
    package_root = _copy_package(tmp_path)
    package_index = _load(package_root, "package-index.json")
    entry = next(
        item
        for item in package_index["schema_bindings"]
        if item["schema_id"] == "ars://core/command/CreateScopeDefinition"
    )
    entry["raw_sha256"] = "1" * 64
    _dump(package_root, "package-index.json", package_index)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("admission_status", "admitted"),
        ("dispatchable", True),
        ("execution_authorized", True),
        ("admission_event_ref", "evt_1"),
        ("dispatch_ref", "dispatch_1"),
        ("result_ref", "result_1"),
        ("claim_ref", "claim_1"),
        ("owner_acceptance_ref", "acceptance_1"),
        ("research_claim", "claim"),
        ("pilot_claim", "claim"),
        ("result_claim", "claim"),
    ],
)
def test_preflight_cannot_become_admitted_dispatchable_or_claim_bearing(tmp_path, field, value):
    preflight = _load(_copy_package(tmp_path), "gate6-preflight.json")
    preflight[field] = value
    _assert_rejected(tmp_path / field.replace("_", "-"), "gate6-preflight.json", preflight)


def test_w11_manifest_admission_status_is_not_a_preflight_input(tmp_path):
    preflight = _load(_copy_package(tmp_path), "gate6-preflight.json")
    preflight["w11_manifest"] = {"admission_status": "admitted"}
    _assert_rejected(tmp_path / "w11-manifest", "gate6-preflight.json", preflight)


@pytest.mark.parametrize("mutation", ["invalid_id", "missing", "extra", "envelope"])
def test_scope_blueprint_is_payload_only_and_cardinality_free(tmp_path, mutation):
    blueprint = _load(_copy_package(tmp_path), "scope-definition-blueprint.json")
    if mutation == "invalid_id":
        blueprint["new_scope_definition_id"] = "scope-not-ars-object"
    elif mutation == "missing":
        blueprint.pop("completion_predicate")
    elif mutation == "extra":
        blueprint["object_count"] = 1
    else:
        blueprint["actor_id"] = "act_1"
    _assert_rejected(tmp_path / f"scope-{mutation}", "scope-definition-blueprint.json", blueprint)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item.update({"relative_path": "../results/foreign.json"}),
        lambda item: item.update({"physical_path": "C:/foreign/valid-fixture.bin"}),
        lambda item: item.update({"size_bytes": item["size_bytes"] + 1}),
        lambda item: item.update({"raw_sha256": "69b2ba55902565960e8009004d2c21332d3786e2af3e83edc4ac0a2d3a5f5540"}),
        lambda item: item["path_safety"].update({"no_reparse_point": False}),
        lambda item: item["path_safety"].update({"no_symlink": False}),
        lambda item: item["path_safety"].update({"no_case_fold_ambiguity": False}),
        lambda item: item["path_safety"].update({"no_unicode_normalization_ambiguity": False}),
        lambda item: item["row_membership_alignment"].update({"row_index_relative_path": "results/index.json"}),
    ],
)
def test_fixture_observation_rejects_path_identity_and_alignment_mutations(tmp_path, mutation):
    package_root = _copy_package(tmp_path)
    observation = _load(package_root, "fixture-observation.json")
    mutation(observation["fixtures"][0])
    _dump(package_root, "fixture-observation.json", observation)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


def test_case_fold_and_unicode_path_ambiguity_are_rejected(tmp_path):
    package_root = _copy_package(tmp_path)
    observation = _load(package_root, "fixture-observation.json")
    observation["fixtures"][0]["relative_path"] = "results/trajectory_tda_integration/EMBEDDINGS.npy"
    _dump(package_root, "fixture-observation.json", observation)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)

    package_root = _copy_package(tmp_path / "unicode")
    observation = _load(package_root, "fixture-observation.json")
    observation["fixtures"][0]["relative_path"] = "results/trajectory_tda_integration/embeddings.npy\u0301"
    _dump(package_root, "fixture-observation.json", observation)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


def test_write_capable_legacy_root_and_nonzero_publication_are_rejected(tmp_path):
    package_root = _copy_package(tmp_path)
    evidence = _load(package_root, "no-write-evidence.json")
    evidence["legacy_root_write_checks"][0]["write_observed"] = True
    _dump(package_root, "no-write-evidence.json", evidence)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)

    package_root = _copy_package(tmp_path / "publication")
    evidence = _load(package_root, "no-write-evidence.json")
    evidence["publication"]["object_count_delta"] = 1
    _dump(package_root, "no-write-evidence.json", evidence)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


@pytest.mark.parametrize("dependency_id", ["foundation_binding", "kan68_a7", "operator_session"])
def test_foundation_a7_and_operator_session_dependencies_remain_pending(tmp_path, dependency_id):
    preflight = _load(_copy_package(tmp_path), "gate6-preflight.json")
    dependency = next(item for item in preflight["dependencies"] if item["dependency_id"] == dependency_id)
    dependency["status"] = "resolved"
    dependency["exact_reference"] = "record_1"
    _assert_rejected(tmp_path / dependency_id, "gate6-preflight.json", preflight)


def test_predecessor_v1_0_0_mutation_is_rejected(tmp_path):
    package_index = _load(_copy_package(tmp_path), "package-index.json")
    package_index["predecessor_components"][0]["raw_sha256"] = "1" * 64
    _assert_rejected(tmp_path / "predecessor", "package-index.json", package_index)


def test_coordinated_candidate_omission_cannot_remove_a_fixed_component(tmp_path):
    package_root = _copy_package(tmp_path)
    package_index = _load(package_root, "package-index.json")
    package_index["artifact_bindings"][0] = deepcopy(package_index["artifact_bindings"][1])
    package_index["changed_components"][0]["path"] = package_index["changed_components"][1]["path"]
    _dump(package_root, "package-index.json", package_index)
    preflight = _load(package_root, "gate6-preflight.json")
    preflight["component_refs"][0] = deepcopy(preflight["component_refs"][1])
    _dump(package_root, "gate6-preflight.json", preflight)
    with pytest.raises(ValueError):
        verify_candidate_package(REPO_ROOT, package_root=package_root)


def test_failure_injection_preserves_zero_authoritative_publication():
    verify_failure_injection(failure_injected=True, authoritative_publication=False, deltas=(0, 0, 0))
    with pytest.raises(ValueError):
        verify_failure_injection(failure_injected=True, authoritative_publication=True, deltas=(0, 0, 0))
    with pytest.raises(ValueError):
        verify_failure_injection(failure_injected=True, authoritative_publication=False, deltas=(1, 0, 0))
