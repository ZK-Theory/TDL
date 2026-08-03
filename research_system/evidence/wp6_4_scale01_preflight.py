"""Verify the bounded WP6.4 SCALE-01 machine-package candidate.

The module is intentionally independent of the ARS runtime.  It reads raw
working-tree bytes, derives SHA-256 and Git blob identities, validates the
candidate schemas, and enforces the pending/non-dispatchable boundary.  No
function in this module publishes an event, object, ScopeDefinition, dispatch,
result, claim, or owner-acceptance record.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


BASE_COMMIT = "cbe24f86b65c2c49bd58eecf4b6786e8879c4704"
BASE_TREE = "a16afef0f29ad1d1c52d0f91b9ab00fa4d343b6c"
PACKAGE_RELATIVE_ROOT = ".research-system/contracts/wp6-4/tda-scale-v1.0.1"
SCHEMA_RELATIVE_ROOT = ".research-system/schemas/contracts/wp6-4"

INDEX_SCHEMA = {
    "path": f"{SCHEMA_RELATIVE_ROOT}/tda-scale-package-index.schema.json",
    "schema_id": "ars://contracts/wp6-4/tda-scale-package-index",
    "schema_version": "1.0.1",
}
BLUEPRINT_SCHEMA = {
    "path": f"{SCHEMA_RELATIVE_ROOT}/scale-01-scope-definition-blueprint.schema.json",
    "schema_id": "ars://contracts/wp6-4/scale-01-scope-definition-blueprint",
    "schema_version": "1.0.1",
}
FIXTURE_SCHEMA = {
    "path": f"{SCHEMA_RELATIVE_ROOT}/scale-01-fixture-observation.schema.json",
    "schema_id": "ars://contracts/wp6-4/scale-01-fixture-observation",
    "schema_version": "1.0.1",
}
NO_WRITE_SCHEMA = {
    "path": f"{SCHEMA_RELATIVE_ROOT}/scale-01-no-write-evidence.schema.json",
    "schema_id": "ars://contracts/wp6-4/scale-01-no-write-evidence",
    "schema_version": "1.0.1",
}
PREFLIGHT_SCHEMA = {
    "path": f"{SCHEMA_RELATIVE_ROOT}/scale-01-gate6-preflight.schema.json",
    "schema_id": "ars://contracts/wp6-4/scale-01-gate6-preflight",
    "schema_version": "1.0.1",
}
PREFLIGHT_ARTIFACT = {
    "path": f"{PACKAGE_RELATIVE_ROOT}/gate6-preflight.json",
    "schema_id": PREFLIGHT_SCHEMA["schema_id"],
    "schema_version": "1.0.1",
    "binding_id": "scale_01_gate6_preflight",
}

SOURCE_SCHEMAS = (
    {
        "path": ".research-system/schemas/core/commands/create_scope_definition.schema.json",
        "schema_id": "ars://core/command/CreateScopeDefinition",
        "schema_version": "1.0.0",
        "byte_length": 16949,
        "raw_sha256": "0e1e3f8f9242a69559749b491048d7ce3983fada083cdc65475cc8ac9feb2856",
        "git_blob": "a8ffbd7c607bbeb523074a2a96d63ab87bf67af1",
    },
    {
        "path": ".research-system/schemas/contracts/w11/research-dossier-manifest.schema.json",
        "schema_id": "ars://portfolio/research-dossier-manifest",
        "schema_version": "1.0.0",
        "byte_length": 8118,
        "raw_sha256": "ebba2bae34833237a5bb1dde06bcb598258b52f325635237378e7b8fdcf7e987",
        "git_blob": "5cc93fe457c3f540bc2bea8d19e5c92d9c801675",
    },
    {
        "path": ".research-system/schemas/contracts/w11/dossier-expected-set-content.schema.json",
        "schema_id": "ars://portfolio/dossier-expected-set-content",
        "schema_version": "1.0.0",
        "byte_length": 10518,
        "raw_sha256": "543002112c8d9ace692f15d2d0e6a3a3f2747a01e405ced717c94c1b3f3bcc0d",
        "git_blob": "caa26760e10f2ff04078940ef63ebe0c84944b95",
    },
)

CANDIDATE_SCHEMAS = (INDEX_SCHEMA, BLUEPRINT_SCHEMA, FIXTURE_SCHEMA, NO_WRITE_SCHEMA, PREFLIGHT_SCHEMA)

ARTIFACTS = (
    {
        "path": f"{PACKAGE_RELATIVE_ROOT}/scope-definition-blueprint.json",
        "schema_id": BLUEPRINT_SCHEMA["schema_id"],
        "schema_version": "1.0.1",
        "binding_id": "scale_01_scope_definition_blueprint",
    },
    {
        "path": f"{PACKAGE_RELATIVE_ROOT}/fixture-observation.json",
        "schema_id": FIXTURE_SCHEMA["schema_id"],
        "schema_version": "1.0.1",
        "binding_id": "scale_01_fixture_observation",
    },
    {
        "path": f"{PACKAGE_RELATIVE_ROOT}/no-write-evidence.json",
        "schema_id": NO_WRITE_SCHEMA["schema_id"],
        "schema_version": "1.0.1",
        "binding_id": "scale_01_no_write_evidence",
    },
)

PACKAGE_INDEX_ARTIFACT = {
    "path": f"{PACKAGE_RELATIVE_ROOT}/package-index.json",
    "schema_id": INDEX_SCHEMA["schema_id"],
    "schema_version": "1.0.1",
    "binding_id": "tda_scale_package_index",
}

FIXED_FIXTURES = (
    (
        "F-USOC-EMBED",
        "results/trajectory_tda_integration/embeddings.npy",
        "C:/Users/steph/TDL/results/trajectory_tda_integration/embeddings.npy",
        4364928,
        "69b2ba55902565960e8009004d2c21332d3786e2af3e83edc4ac0a2d3a5f5540",
    ),
    (
        "F-USOC-TRAJ",
        "results/trajectory_tda_integration/01_trajectories.json",
        "C:/Users/steph/TDL/results/trajectory_tda_integration/01_trajectories.json",
        5584666,
        "d356874922685ac7052124b8a7897f6a52e5cde2a124a1ec4816bc30e6748c39",
    ),
    (
        "F-BHPS-EMBED",
        "results/trajectory_tda_bhps/embeddings.npy",
        "C:/Users/steph/TDL/results/trajectory_tda_bhps/embeddings.npy",
        1361568,
        "349fd443529a1212f03e8a1b8b189c02bdce6afffe82ea17c5ca8895e041b3c0",
    ),
    (
        "F-BHPS-TRAJ",
        "results/trajectory_tda_bhps/01_trajectories.json",
        "C:/Users/steph/TDL/results/trajectory_tda_bhps/01_trajectories.json",
        1898001,
        "a872606a435478515daa8edd91ac58172c173d61c8a8c2e2f12e305dc1b07b47",
    ),
    (
        "F-G-MEDIAN-CHECKPOINT",
        "results/panel_methodology/fdr/subgroup_checkpoints/bhps_nssec_Routine-Manual_B1000_seed42.json",
        "C:/Users/steph/TDL/results/panel_methodology/fdr/subgroup_checkpoints/bhps_nssec_Routine-Manual_B1000_seed42.json",
        579,
        "9a0feef58c77d8e5d2b798db2936fc6c14f1f56518177b9d31ee71f2360bd8a7",
    ),
    (
        "F-G-SLOW-L5000-CHECKPOINT",
        "results/panel_methodology/fdr/subgroup_checkpoints/usoc_nssec_Routine-Manual_B1000_seed42.json",
        "C:/Users/steph/TDL/results/panel_methodology/fdr/subgroup_checkpoints/usoc_nssec_Routine-Manual_B1000_seed42.json",
        583,
        "3c4dc1e29f2817b0f8c51a2b1892375053cb82b7f7223940f16797b207f06541",
    ),
)

FIXTURE_IDS = tuple(item[0] for item in FIXED_FIXTURES)
FIXTURE_SET_SHA256 = "9828d1891e17fd378b6fcdbc66090481b10484c6b5fb3e7fcd9d074c8886fd4f"

PREDECESSOR_COMPONENTS = (
    (
        "MASTER_PROGRAMME",
        "00-Meta/Research Direction Reports/Evidence-Led TDA Scale and Research Programme for ARS - v1.0.0 - 2026-07-16.md",
        28244,
        "277f57f938af78f9dd0f270e97bc94919dc55e15b468246844a778a560d241ea",
    ),
    (
        "BENCHMARK_FIXTURE_MANIFEST",
        "00-Meta/Discovery/ars-scale-benchmark-fixture-manifest-v1.0.0-2026-07-16.md",
        10114,
        "fc05bff665917f88349767213a39a6bf1be2e2238d8d08493a8882fb00275341",
    ),
    (
        "SCALE_01_BRIEF",
        "00-Meta/Discovery/ars-scale-01-stage-telemetry-markov-hoist-brief-v1.0.0-2026-07-16.md",
        15326,
        "bbe18f432f2cdeabb99bec4d6dcf82ba7848222b88d54411815593f7ae0918c3",
    ),
    (
        "SCALE_02_TEMPLATE",
        "00-Meta/Discovery/ars-scale-02-distribution-preserving-vectorisation-template-v1.0.0-2026-07-16.md",
        5978,
        "0370c414cd34f451b76b28fcd70d0ce0bffb270f94fcfe33800d10dc11b220b9",
    ),
    (
        "SCALE_03_BRIEF",
        "00-Meta/Discovery/ars-scale-03-certified-w2-acceleration-brief-v1.0.0-2026-07-16.md",
        15219,
        "18c9b3b27eb441a20d8375f2d06f4d113da38a900794c4ef01d10c2d1bfa0232",
    ),
    (
        "SCALE_04_BRIEF",
        "00-Meta/Discovery/ars-scale-04-giotto-execution-architecture-brief-v1.0.0-2026-07-16.md",
        13459,
        "1866e771cf744d64bd69f17219473cb309b147042e9d9f47821cc65c7fa48fbf",
    ),
    (
        "SCALE_05_TEMPLATE",
        "00-Meta/Discovery/ars-scale-05-complex-reduction-template-v1.0.0-2026-07-16.md",
        6941,
        "b9080a30c063d4107ce76236999062015cab626df75b2c7901934864fa99571f",
    ),
    (
        "SPEC_01_ASSAY_BRIEF",
        "00-Meta/Discovery/ars-spec-01-spectral-distance-ph-assay-brief-v1.0.0-2026-07-16.md",
        14660,
        "39ee3e5a44ec9dbe25766e7ecf89b98fbae8eedcace2ae40f9d5a0fb32f43b84",
    ),
    (
        "SPEC_02_MICRO_SPIKE_TEMPLATE",
        "00-Meta/Discovery/ars-spec-02-spectral-distance-ph-micro-spike-template-v1.0.0-2026-07-16.md",
        12535,
        "f9316c33844d77c9bde9506decb942354a28441e372a06c7abc2d9ed03d5bec5",
    ),
    (
        "DIR_01_MULTIPARAMETER_TEMPLATE",
        "00-Meta/Discovery/ars-dir-01-multiparameter-consolidation-template-v1.0.0-2026-07-16.md",
        2934,
        "1641ee199b4b463b2924cd89729f54a13f0eb67796d12403390baf03d2554f2f",
    ),
    (
        "DIR_02_REGIONAL_MAPPER_TEMPLATE",
        "00-Meta/Discovery/ars-dir-02-regional-mapper-extension-template-v1.0.0-2026-07-16.md",
        3313,
        "a4d3a3615796d6cc5e75cef8c4df93cfd8c7ff8e2adbbdd2b65203fc710380ee",
    ),
    (
        "DIR_03_ZIGZAG_TEMPLATE",
        "00-Meta/Discovery/ars-dir-03-zigzag-new-event-template-v1.0.0-2026-07-16.md",
        2869,
        "8bed90be64e2fb9eeba54505d9267c4f5b06a14a9c88721dd0e1e28098684d74",
    ),
    (
        "DIR_04_DIRECTED_PERSISTENCE_TEMPLATE",
        "00-Meta/Discovery/ars-dir-04-directed-persistence-assay-template-v1.0.0-2026-07-16.md",
        3558,
        "46e790a5de1c7b44c3f00c6e644cd118a3ffbc616f99c0cb43f806a26ffd5e82",
    ),
    (
        "DIR_05_TRAJECTORY_PL_SHEAF_TEMPLATE",
        "00-Meta/Discovery/ars-dir-05-trajectory-pl-sheaf-template-v1.0.0-2026-07-16.md",
        3924,
        "3640180168f9f57a3d09cad17804f3f63cb0fb29e9b2002c7994ee13b39273d8",
    ),
    (
        "DIR_07_PERSISTENT_CUP_LENGTH_TEMPLATE",
        "00-Meta/Discovery/ars-dir-07-persistent-cup-length-literature-template-v1.0.0-2026-07-16.md",
        3613,
        "9d7288ca27424bf4189f8982d89daafae9fab28a7e3eee6730748e249caa087c",
    ),
    (
        "DIR_08_DIFFUSION_NON_REDUNDANCY_TEMPLATE",
        "00-Meta/Discovery/ars-dir-08-diffusion-nonredundancy-template-v1.0.0-2026-07-16.md",
        2870,
        "5d4078e9640c29b93160c2f9694388b437f331a96777f1c885d70b4e934e4526",
    ),
    (
        "DIR_09_TOPOLOGICAL_CAUSAL_EFFECTS_TEMPLATE",
        "00-Meta/Discovery/ars-dir-09-topological-causal-effects-template-v1.0.0-2026-07-16.md",
        3392,
        "a79cb0cb7884e4e9c0b6cc116417b665307ec4c35bc86f0fc823fa2794017583",
    ),
)

DEPENDENCY_IDS = (
    "foundation_binding",
    "kan68_a7",
    "operator_session",
    "wp6_6_admission_profile",
    "wp6_6_expected_set",
    "wp6_6_blueprint_locator",
    "wp6_6_atomic_admission",
)


class VerificationError(ValueError):
    """Raised when the candidate is not an exact, closed preflight."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fixture_set_sha256(member_ids: list[str] | tuple[str, ...]) -> str:
    """Return the independent multiset digest used by no-write evidence."""

    return hashlib.sha256(_canonical_json(sorted(member_ids))).hexdigest()


def _git_blob_sha1(repo_root: Path, data: bytes) -> str:
    completed = subprocess.run(
        ["git", "hash-object", "--no-filters", "--stdin"],
        cwd=repo_root,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise VerificationError(f"Git blob derivation failed: {completed.stderr.decode(errors='replace').strip()}")
    return completed.stdout.decode("ascii").strip()


def _git_head(repo_root: Path) -> tuple[str, str]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root, text=True).strip()
    return commit, tree


def _raw_json(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise VerificationError(f"{path} is not BOM-free UTF-8/LF")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{path} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{path} must contain a JSON object")
    return value, data


def _validate(instance: Any, schema: dict[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "$"
        raise VerificationError(f"{label} schema validation failed at {location}: {error.message}")


def _read_git_source(repo_root: Path, source: dict[str, Any]) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{BASE_COMMIT}:{source['path']}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise VerificationError(f"protected source is unavailable: {source['path']}")
    data = completed.stdout
    observed = {
        "byte_length": len(data),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": _git_blob_sha1(repo_root, data),
    }
    expected = {key: source[key] for key in observed}
    if observed != expected:
        raise VerificationError(f"protected source identity mismatch: {source['path']}: {observed} != {expected}")
    return data


def build_artifact_identity(
    repo_root: Path,
    relative_path: str,
    schema_id: str,
    schema_version: str,
    *,
    subject_commit: str = BASE_COMMIT,
    subject_tree: str = BASE_TREE,
) -> dict[str, Any]:
    """Derive an exact identity from on-disk bytes, never from a JSON claim."""

    path = repo_root / Path(relative_path.replace("/", "/"))
    data = path.read_bytes()
    return {
        "path": relative_path,
        "schema_id": schema_id,
        "schema_version": schema_version,
        "subject_commit": subject_commit,
        "subject_tree": subject_tree,
        "byte_length": len(data),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": _git_blob_sha1(repo_root, data),
    }


def _assert_identity(declared: dict[str, Any], observed: dict[str, Any], label: str) -> None:
    keys = (
        "path",
        "schema_id",
        "schema_version",
        "subject_commit",
        "subject_tree",
        "byte_length",
        "raw_sha256",
        "git_blob",
    )
    for key in keys:
        if declared.get(key) != observed.get(key):
            raise VerificationError(
                f"{label} identity mismatch for {key}: {declared.get(key)!r} != {observed.get(key)!r}"
            )


def _package_path(package_root: Path, relative_path: str) -> Path:
    if not relative_path.startswith(f"{PACKAGE_RELATIVE_ROOT}/"):
        raise VerificationError(f"candidate path is outside the package root: {relative_path}")
    suffix = relative_path[len(PACKAGE_RELATIVE_ROOT) + 1 :]
    if "/" in suffix or ".." in PurePosixPath(suffix).parts:
        raise VerificationError(f"candidate path is not a direct package file: {relative_path}")
    path = package_root / suffix
    if path.resolve().parent != package_root.resolve():
        raise VerificationError(f"candidate path escapes package root: {relative_path}")
    return path


def _candidate_identity(repo_root: Path, package_root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    path = _package_path(package_root, expected["path"])
    data = path.read_bytes()
    return {
        "path": expected["path"],
        "schema_id": expected["schema_id"],
        "schema_version": expected["schema_version"],
        "subject_commit": BASE_COMMIT,
        "subject_tree": BASE_TREE,
        "byte_length": len(data),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": _git_blob_sha1(repo_root, data),
    }


def _identity_for_candidate(
    repo_root: Path, package_root: Path, entry: dict[str, Any], expected: dict[str, Any]
) -> None:
    if entry.get("path") != expected["path"]:
        raise VerificationError(f"candidate identity path mismatch: {entry.get('path')!r}")
    if "binding_kind" in entry and entry.get("binding_kind") != "machine_artifact":
        raise VerificationError(f"candidate binding kind is not machine_artifact: {expected['path']}")
    observed = _candidate_identity(repo_root, package_root, expected)
    _assert_identity(entry, observed, expected["path"])
    if not _package_path(package_root, expected["path"]).exists():
        raise VerificationError(f"candidate artifact is absent: {expected['path']}")


def _assert_source_bindings(repo_root: Path, index: dict[str, Any]) -> None:
    declared = {entry["path"]: entry for entry in index["schema_bindings"]}
    expected_paths = {source["path"] for source in SOURCE_SCHEMAS} | {item["path"] for item in CANDIDATE_SCHEMAS}
    if set(declared) != expected_paths:
        raise VerificationError("schema binding set is not the fixed independent schema tuple")
    for source in SOURCE_SCHEMAS:
        entry = declared[source["path"]]
        if entry.get("binding_kind") != "governing_schema":
            raise VerificationError(f"protected source binding kind changed: {source['path']}")
        expected = {
            "path": source["path"],
            "schema_id": source["schema_id"],
            "schema_version": source["schema_version"],
            "subject_commit": BASE_COMMIT,
            "subject_tree": BASE_TREE,
            "byte_length": source["byte_length"],
            "raw_sha256": source["raw_sha256"],
            "git_blob": source["git_blob"],
        }
        source_bytes = _read_git_source(repo_root, source)
        observed = _raw_identity(repo_root, source_bytes, source["path"], source["schema_id"], source["schema_version"])
        if observed != expected:
            raise VerificationError(f"source identity mismatch: {source['path']}")
        _assert_identity(entry, observed, source["path"])
        parsed = json.loads(source_bytes.decode("utf-8"))
        if parsed.get("$id") != source["schema_id"]:
            raise VerificationError(f"source schema ID mismatch: {source['path']}")
    for schema in CANDIDATE_SCHEMAS:
        entry = declared[schema["path"]]
        if entry.get("binding_kind") != "candidate_schema":
            raise VerificationError(f"candidate schema binding kind changed: {schema['path']}")
        observed = build_artifact_identity(repo_root, schema["path"], schema["schema_id"], schema["schema_version"])
        _assert_identity(entry, observed, schema["path"])
        parsed, _ = _raw_json(repo_root / Path(schema["path"]))
        if parsed.get("$id") != schema["schema_id"]:
            raise VerificationError(f"candidate schema ID mismatch: {schema['path']}")


def _raw_identity(repo_root: Path, data: bytes, path: str, schema_id: str, schema_version: str) -> dict[str, Any]:
    return {
        "path": path,
        "schema_id": schema_id,
        "schema_version": schema_version,
        "subject_commit": BASE_COMMIT,
        "subject_tree": BASE_TREE,
        "byte_length": len(data),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": _git_blob_sha1(repo_root, data),
    }


def _assert_predecessor(index: dict[str, Any]) -> None:
    manifest = index["predecessor_manifest"]
    if manifest != {
        "manifest_path": "00-Meta/Research Direction Reports/Evidence-Led TDA Scale and Research Programme for ARS - package manifest - v1.0.0 - 2026-07-16.md",
        "package_id": "TDA-ARS-SCALE-RESEARCH",
        "package_version": "1.0.0",
        "schema_id": "external://tda-scale/package-manifest",
        "schema_version": "1.0.0",
        "byte_length": 5843,
        "raw_sha256": "e20d173b1787c7adf141d08eadecb320ee534a075ad764e542b9fd495df61cbf",
        "git_blob": None,
        "subject_commit": None,
        "subject_tree": None,
        "identity_source": "external_vault_read_only",
    }:
        raise VerificationError("predecessor package-manifest identity changed")
    observed = {
        (entry["component_id"], entry["source_relative_path"], entry["byte_length"], entry["raw_sha256"])
        for entry in index["predecessor_components"]
    }
    expected = set(PREDECESSOR_COMPONENTS)
    if observed != expected:
        raise VerificationError("predecessor component identity set changed")
    if any(
        entry["reuse_in_place"] is not True
        or entry["changed_path"] is not None
        or entry["git_blob"] is not None
        or entry["subject_commit"] is not None
        or entry["subject_tree"] is not None
        for entry in index["predecessor_components"]
    ):
        raise VerificationError("v1.0.0 component is not an unchanged external read-only reuse")


def _assert_dependencies(dependencies: list[dict[str, Any]]) -> None:
    if {item["dependency_id"] for item in dependencies} != set(DEPENDENCY_IDS):
        raise VerificationError("dependency set is not the fixed WP6.6/foundation/A7 pending set")
    if any(item["status"] != "pending" or item["exact_reference"] is not None for item in dependencies):
        raise VerificationError("an unresolved dependency was asserted as resolved")


def _normalised_path(path: str) -> str:
    if "\x00" in path or "\\" in path:
        raise VerificationError(f"path uses an unsafe separator: {path!r}")
    if any(part in {"", ".", ".."} for part in PurePosixPath(path).parts):
        raise VerificationError(f"path contains traversal or empty segments: {path!r}")
    return unicodedata.normalize("NFC", path)


def _assert_fixture_observation(observation: dict[str, Any]) -> None:
    root = observation["registered_root"]
    if root["canonical_relative_root"] != root["diagnostic_physical_path"]:
        raise VerificationError("registered root identity and diagnostic path diverge")
    if root["read_only_required"] is not True or root["path_is_diagnostic_only"] is not True:
        raise VerificationError("registered root is not read-only diagnostic input")
    expected = {item[0]: item for item in FIXED_FIXTURES}
    observed_ids = {item["fixture_id"] for item in observation["fixtures"]}
    if observed_ids != set(expected):
        raise VerificationError("fixture observation set is not the independent registered tuple")
    normalised_paths: set[str] = set()
    for fixture in observation["fixtures"]:
        fixture_expected = expected[fixture["fixture_id"]]
        _, rel, physical, size, digest = fixture_expected
        if (fixture["relative_path"], fixture["physical_path"], fixture["size_bytes"], fixture["raw_sha256"]) != (
            rel,
            physical,
            size,
            digest,
        ):
            raise VerificationError(f"fixture identity mismatch: {fixture['fixture_id']}")
        _normalised_path(fixture["relative_path"])
        _normalised_path(fixture["physical_path"])
        if not fixture["physical_path"].startswith(root["diagnostic_physical_path"] + "/"):
            raise VerificationError(f"fixture physical path escapes registered root: {fixture['fixture_id']}")
        normalised_paths.add(fixture["relative_path"].casefold())
        safety = fixture["path_safety"]
        if any(
            safety[key] is not True
            for key in (
                "no_path_escape",
                "no_reparse_point",
                "no_symlink",
                "no_case_fold_ambiguity",
                "no_unicode_normalization_ambiguity",
            )
        ):
            raise VerificationError(f"fixture path safety is not closed: {fixture['fixture_id']}")
        alignment = fixture["row_membership_alignment"]
        if alignment["status"] != "pending_wp6_6" or any(
            alignment[key] is not None
            for key in ("row_index_relative_path", "row_index_sha256", "positional_alignment", "evidence_ref")
        ):
            raise VerificationError(f"fixture row alignment is not pending/null: {fixture['fixture_id']}")
    if len(normalised_paths) != len(observed_ids):
        raise VerificationError("fixture paths contain a case-fold collision")


def _assert_no_write_evidence(evidence: dict[str, Any]) -> None:
    comparison = evidence["fixture_set_comparison"]
    if comparison["before_member_ids"] != list(FIXTURE_IDS) or comparison["after_member_ids"] != list(FIXTURE_IDS):
        raise VerificationError("no-write fixture sets do not equal the independent fixed tuple")
    if (
        comparison["before_multiset_sha256"] != FIXTURE_SET_SHA256
        or comparison["after_multiset_sha256"] != FIXTURE_SET_SHA256
    ):
        raise VerificationError("no-write fixture multiset hash is not independently derived")
    if comparison["sets_match"] is not True or comparison["duplicate_free"] is not True:
        raise VerificationError("no-write fixture comparison is not closed")
    scratch = evidence["attempt_scratch"]
    _normalised_path(scratch["relative_path"])
    _normalised_path(scratch["physical_path"])
    if scratch["path_disjoint"] is not True or scratch["attempt_write_count"] != 0:
        raise VerificationError("attempt scratch is not disjoint and empty")
    for legacy in evidence["legacy_root_write_checks"]:
        if legacy["write_observed"] is not False or legacy["pre_hash"] is not None or legacy["post_hash"] is not None:
            raise VerificationError("legacy root write evidence is not no-write/pending")
    unchanged = evidence["authoritative_state_unchanged"]
    if any(
        cell["unchanged"] is not True or cell["before_ref"] is not None or cell["after_ref"] is not None
        for cell in unchanged.values()
    ):
        raise VerificationError("authoritative state was not held unchanged with null references")
    publication = evidence["publication"]
    if publication["authoritative_publication"] is not False or any(
        publication[key] != 0 for key in ("object_count_delta", "scope_count_delta", "event_count_delta")
    ):
        raise VerificationError("no-write evidence permits authoritative publication")
    if any(publication[key] is not None for key in ("dispatch_ref", "result_ref", "claim_ref")):
        raise VerificationError("no-write evidence contains a publication reference")
    failure = evidence["failure_injection"]
    if failure["failure_injected"] is not True or failure["expected_authoritative_publication"] is not False:
        raise VerificationError("failure injection is not fail-closed")


def verify_failure_injection(
    *, failure_injected: bool, authoritative_publication: bool, deltas: tuple[int, int, int]
) -> None:
    """Enforce zero authoritative publication when a pre-publication failure fires."""

    if failure_injected and (authoritative_publication or deltas != (0, 0, 0)):
        raise VerificationError("failure injection crossed the zero-publication boundary")


def _assert_preflight(repo_root: Path, package_root: Path, preflight: dict[str, Any]) -> None:
    if (
        preflight["admission_status"] != "pending_wp6_6"
        or preflight["dispatchable"] is not False
        or preflight["execution_authorized"] is not False
    ):
        raise VerificationError("preflight is not pending and non-dispatchable")
    if any(
        preflight[key] is not None
        for key in (
            "admission_event_ref",
            "dispatch_ref",
            "result_ref",
            "claim_ref",
            "owner_acceptance_ref",
            "research_claim",
            "pilot_claim",
            "result_claim",
        )
    ):
        raise VerificationError("preflight contains an admission, dispatch, result, claim, or acceptance reference")
    _assert_dependencies(preflight["dependencies"])
    if any(
        preflight["cardinality"][key] is not None
        for key in ("object_count", "scope_count", "edge_count", "relationship_count")
    ):
        raise VerificationError("object/scope/edge cardinality was guessed before WP6.6")
    if (
        preflight["supersession"]["mutation_prohibited"] is not True
        or preflight["supersession"]["superseded_by_ref"] is not None
    ):
        raise VerificationError("preflight supersession boundary is not immutable")
    if preflight["preflight_self_binding"] != {
        "path": PREFLIGHT_ARTIFACT["path"],
        "schema_id": PREFLIGHT_ARTIFACT["schema_id"],
        "schema_version": PREFLIGHT_ARTIFACT["schema_version"],
        "self_hashing": "prohibited_due_to_self_reference",
        "external_verifier_required": True,
    }:
        raise VerificationError("preflight self-binding boundary changed")
    if preflight["package_index_ref"]["path"] != PACKAGE_INDEX_ARTIFACT["path"]:
        raise VerificationError("preflight package-index path is not fixed")
    _identity_for_candidate(repo_root, package_root, preflight["package_index_ref"], PACKAGE_INDEX_ARTIFACT)
    if {item["path"] for item in preflight["component_refs"]} != {item["path"] for item in ARTIFACTS}:
        raise VerificationError("preflight component tuple was coordinated with a missing artifact")
    for entry, expected in zip(
        sorted(preflight["component_refs"], key=lambda item: item["path"]),
        sorted(ARTIFACTS, key=lambda item: item["path"]),
        strict=True,
    ):
        _identity_for_candidate(repo_root, package_root, entry, expected)
    if preflight["schema_binding"]["path"] != PREFLIGHT_SCHEMA["path"]:
        raise VerificationError("preflight schema binding path is not fixed")
    observed_schema = build_artifact_identity(
        repo_root, PREFLIGHT_SCHEMA["path"], PREFLIGHT_SCHEMA["schema_id"], PREFLIGHT_SCHEMA["schema_version"]
    )
    _assert_identity(preflight["schema_binding"], observed_schema, PREFLIGHT_SCHEMA["path"])


def verify_candidate_package(repo_root: Path, *, package_root: Path | None = None) -> dict[str, Any]:
    """Verify the complete machine candidate and return exact observed identities."""

    repo_root = repo_root.resolve()
    package_root = (repo_root / Path(PACKAGE_RELATIVE_ROOT)) if package_root is None else package_root.resolve()
    if not package_root.is_dir():
        raise VerificationError(f"candidate package directory is absent: {package_root}")

    schema_values: dict[str, dict[str, Any]] = {}
    for schema in CANDIDATE_SCHEMAS:
        parsed, _ = _raw_json(repo_root / Path(schema["path"]))
        schema_values[schema["schema_id"]] = parsed

    package_index, _ = _raw_json(package_root / "package-index.json")
    blueprint, _ = _raw_json(package_root / "scope-definition-blueprint.json")
    fixture_observation, _ = _raw_json(package_root / "fixture-observation.json")
    no_write, _ = _raw_json(package_root / "no-write-evidence.json")
    preflight, _ = _raw_json(package_root / "gate6-preflight.json")

    _validate(package_index, schema_values[INDEX_SCHEMA["schema_id"]], "package index")
    _validate(blueprint, schema_values[BLUEPRINT_SCHEMA["schema_id"]], "scope blueprint")
    _validate(fixture_observation, schema_values[FIXTURE_SCHEMA["schema_id"]], "fixture observation")
    _validate(no_write, schema_values[NO_WRITE_SCHEMA["schema_id"]], "no-write evidence")
    _validate(preflight, schema_values[PREFLIGHT_SCHEMA["schema_id"]], "Gate 6 preflight")

    scope_command = json.loads(_read_git_source(repo_root, SOURCE_SCHEMAS[0]).decode("utf-8"))
    _validate(blueprint, scope_command["$defs"]["payload"], "CreateScopeDefinition payload")
    if set(blueprint) != {
        "new_scope_definition_id",
        "revision",
        "members",
        "ordering_rules",
        "effective_at",
        "dependency_rules",
        "completion_predicate",
        "amendment_authority",
    }:
        raise VerificationError("scope blueprint contains a command envelope or non-payload field")
    if any(blueprint[key] for key in ("members", "ordering_rules", "dependency_rules")):
        raise VerificationError("scope blueprint guesses WP6.6 object/scope/edge content")

    _assert_source_bindings(repo_root, package_index)
    _assert_predecessor(package_index)
    if {item["path"] for item in package_index["artifact_bindings"]} != {item["path"] for item in ARTIFACTS}:
        raise VerificationError("package artifact binding set is not independently closed")
    for entry, expected in zip(
        sorted(package_index["artifact_bindings"], key=lambda item: item["path"]),
        sorted(ARTIFACTS, key=lambda item: item["path"]),
        strict=True,
    ):
        _identity_for_candidate(repo_root, package_root, entry, expected)
    changed = {item["path"]: (item["component_id"], item["schema_id"]) for item in package_index["changed_components"]}
    expected_changed = {item["path"]: (item["binding_id"], item["schema_id"]) for item in ARTIFACTS}
    if changed != expected_changed:
        raise VerificationError("changed component set is not the fixed additive tuple")
    _assert_dependencies(package_index["dependency_boundary"])
    _assert_fixture_observation(fixture_observation)
    _assert_no_write_evidence(no_write)
    _assert_preflight(repo_root, package_root, preflight)
    verify_failure_injection(
        failure_injected=True,
        authoritative_publication=no_write["publication"]["authoritative_publication"],
        deltas=(0, 0, 0),
    )

    subject_commit, subject_tree = _git_head(repo_root)
    observed = [
        _candidate_identity(repo_root, package_root, item)
        for item in (PACKAGE_INDEX_ARTIFACT, *ARTIFACTS, PREFLIGHT_ARTIFACT)
    ]
    return {
        "package_version": package_index["package_version"],
        "preflight": preflight,
        "subject": {"commit": subject_commit, "tree": subject_tree, "namespace": "working_tree_or_HEAD_bytes"},
        "bindings": observed,
    }


__all__ = [
    "VerificationError",
    "build_artifact_identity",
    "fixture_set_sha256",
    "verify_candidate_package",
    "verify_failure_injection",
]
