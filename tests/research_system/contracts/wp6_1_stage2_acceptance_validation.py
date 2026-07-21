"""External, exact-byte owner acceptance validation for WP6.1 Stage-2."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_system.schema_registry import SchemaRegistry


ACCEPTANCE_SCHEMA_ID = "ars://contracts/wp6-1-stage2-owner-acceptance-record"
SUBJECT_COMMIT = "c7e32755e9adb2f39f6a40056ef6058986c9263d"
R10_COMMIT = "b1863e33106e02edaf3ccf0a18aa9385005b25bd"
RECORD_PATH = ".research-system/contracts/wp6-1-stage2-owner-acceptance-record.yaml"
IDENTITY_MANIFEST_PATH = ".research-system/contracts/wp6-1-schema-identities.yaml"
CATALOGUE_PATH = ".research-system/contracts/wp6-1-owner-source-catalogue.yaml"
IDENTITY_CONTRACT_PATH = ".research-system/schemas/contracts/wp6-1-schema-identities.schema.json"
CATALOGUE_CONTRACT_PATH = ".research-system/schemas/contracts/wp6-1-owner-source-catalogue.schema.json"
STAGE1_RECORD_PATH = ".research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml"
STAGE1_CONTRACT_PATH = ".research-system/schemas/contracts/wp6-1-stage1-owner-acceptance-record.schema.json"
R10_REPORT_PATH = (
    "docs/plans/agentic-research-system/reviews/adversarial-wp6-1-stage2-schema-overlay-r10-review-2026-07-21.md"
)
COMMAND_TREE_PATH = ".research-system/schemas/core/commands"
EVENT_TREE_PATH = ".research-system/schemas/core/events"
CORE_TREE_PATH = ".research-system/schemas/core"
OWNER_STATEMENT = (
    "“I explicitly accept the Stage-2 WP6.1 generated-output tuple reviewed at "
    "c7e32755e9adb2f39f6a40056ef6058986c9263d: exactly 173 schemas—87 command schemas under tree "
    "9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea and 86 event schemas under tree "
    "154ffc4bdde82fe903718734687e7a62797b1f69, forming core tree "
    "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46—plus the associated manifests and strict validation contracts. "
    "I accept the R10 verdict of 0 Critical, 0 Major, and 0 Minor and record D-G6-3 as accepted for these "
    "exact bytes only. This does not authorize runtime registration, dispatch, reduction, projection, migration, "
    "hooks, PR merge, or any further Gate 6 transition.”"
)


@dataclass(frozen=True)
class ArtifactBinding:
    repository_path: str
    schema_id: str
    schema_version: str
    git_blob_id: str
    canonical_utf8_lf_sha256: str

    def as_record(self) -> dict[str, str]:
        return {
            "repository_path": self.repository_path,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "git_blob_id": self.git_blob_id,
            "canonical_utf8_lf_sha256": self.canonical_utf8_lf_sha256,
        }


@dataclass(frozen=True)
class Stage2Acceptance:
    accepted_exact_bytes_only: bool
    subject_commit: str
    core_tree: str


ARTIFACTS = {
    "schema_identities": ArtifactBinding(
        IDENTITY_MANIFEST_PATH,
        "ars://contracts/wp6-1-schema-identities",
        "1.0.0",
        "54a2938d34cea9c4a88d23585ce012a86bc3209d",
        "d6d537088f41179b993b94991d5bf5790499cce80bf419c098ca899e794b37e7",
    ),
    "owner_source_catalogue": ArtifactBinding(
        CATALOGUE_PATH,
        "ars://contracts/wp6-1-owner-source-catalogue",
        "1.0.0",
        "1adc66921ee9c90d8786ff173748150922f1035e",
        "bddc6882b969d322cab88af99f15a214edec9ef90c5f563dc9a9fbd082a632ab",
    ),
    "schema_identities_contract": ArtifactBinding(
        IDENTITY_CONTRACT_PATH,
        "ars://contracts/wp6-1-schema-identities",
        "1.0.0",
        "5857d1dbf80ca86d711641b1206267fa2fa44202",
        "43e20dd7307381c22237daf92bc53b405aaf88fe526dec38dcaffd8be0159e91",
    ),
    "owner_source_catalogue_contract": ArtifactBinding(
        CATALOGUE_CONTRACT_PATH,
        "ars://contracts/wp6-1-owner-source-catalogue",
        "1.0.0",
        "8e7ae9079304e20de6d70f74f581d479391f8a31",
        "537ffab03f21c3ca8c8ec040ae65babf4c371d06f582dc56d82fd14c0d0736e5",
    ),
    "stage1_owner_acceptance_record": ArtifactBinding(
        STAGE1_RECORD_PATH,
        "ars://contracts/wp6-1-stage1-owner-acceptance-record",
        "1.0.0",
        "42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83",
        "70a37499528b7d5fdb2fb4627723ae726156c33229aeba5400fd382c752aa648",
    ),
    "stage1_owner_acceptance_contract": ArtifactBinding(
        STAGE1_CONTRACT_PATH,
        "ars://contracts/wp6-1-stage1-owner-acceptance-record",
        "1.0.0",
        "63762c1555515ae9a2db071663d7fe9e2e86a96a",
        "ba0b1ebfa070c04b52923acd09810677c46936027b1197d01621fc941d2f4fe3",
    ),
}
EXPECTED_HARD_STOPS = {
    "runtime_registration_authorized": False,
    "dispatch_authorized": False,
    "reduction_authorized": False,
    "projection_authorized": False,
    "migration_authorized": False,
    "hooks_authorized": False,
    "pr_merge_authorized": False,
    "further_gate_6_transition_authorized": False,
    "implementation_start_authorized": False,
    "separate_owner_authorization_required": True,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _git_bytes(repo_root: Path, revision: str, repository_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{revision}:{repository_path}"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise ValueError(f"immutable Git object unavailable: {revision}:{repository_path}")
    data = result.stdout
    _require(not data.startswith(b"\xef\xbb\xbf") and b"\r" not in data, "immutable Git bytes are not UTF-8/LF")
    return data


def _git_blob_id(repo_root: Path, data: bytes) -> str:
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", "--stdin"],
        cwd=repo_root,
        input=data,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise ValueError("immutable Git blob calculation failed")
    return result.stdout.decode("ascii").strip()


def _git_tree(repo_root: Path, repository_path: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{SUBJECT_COMMIT}:{repository_path}"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise ValueError(f"immutable Git tree unavailable: {repository_path}")
    return result.stdout.decode("ascii").strip()


def _schema_count(repo_root: Path, repository_path: str) -> int:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", f"{SUBJECT_COMMIT}:{repository_path}"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise ValueError(f"immutable Git tree listing failed: {repository_path}")
    return sum(name.endswith(".schema.json") for name in result.stdout.decode("utf-8").splitlines())


def _verified_artifact(repo_root: Path, binding: ArtifactBinding) -> bytes:
    data = _git_bytes(repo_root, SUBJECT_COMMIT, binding.repository_path)
    _require(_git_blob_id(repo_root, data) == binding.git_blob_id, "immutable Git blob mismatch")
    _require(
        hashlib.sha256(data).hexdigest() == binding.canonical_utf8_lf_sha256,
        "immutable Git SHA-256 mismatch",
    )
    return data


def core_schema_tree(repo_root: Path) -> str:
    tree = _git_tree(repo_root, CORE_TREE_PATH)
    _require(tree == "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46", "immutable core tree mismatch")
    return tree


def candidate_snapshot_statuses(repo_root: Path) -> dict[str, str]:
    identity_manifest = yaml.safe_load(_verified_artifact(repo_root, ARTIFACTS["schema_identities"]))
    governance = identity_manifest["governance"]
    snapshot = {
        "review_status": governance["review_status"],
        "acceptance_status": governance["acceptance_status"],
    }
    expected = {
        "review_status": "pending_independent_review",
        "acceptance_status": "pending_d_g6_3_owner_acceptance",
    }
    _require(snapshot == expected, "candidate snapshot statuses changed")
    return snapshot


def _verify_immutable_candidate(repo_root: Path) -> None:
    _require(
        _git_tree(repo_root, COMMAND_TREE_PATH) == "9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea",
        "immutable command tree mismatch",
    )
    _require(_schema_count(repo_root, COMMAND_TREE_PATH) == 87, "immutable command schema count mismatch")
    _require(
        _git_tree(repo_root, EVENT_TREE_PATH) == "154ffc4bdde82fe903718734687e7a62797b1f69",
        "immutable event tree mismatch",
    )
    _require(_schema_count(repo_root, EVENT_TREE_PATH) == 86, "immutable event schema count mismatch")
    _require(core_schema_tree(repo_root) == "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46", "immutable core tree mismatch")
    _require(
        _schema_count(repo_root, COMMAND_TREE_PATH) + _schema_count(repo_root, EVENT_TREE_PATH) == 173,
        "immutable Stage-2 schema count mismatch",
    )
    for binding in ARTIFACTS.values():
        _verified_artifact(repo_root, binding)
    candidate_snapshot_statuses(repo_root)


def _verify_r10_review(repo_root: Path) -> None:
    data = _git_bytes(repo_root, R10_COMMIT, R10_REPORT_PATH)
    _require(_git_blob_id(repo_root, data) == "64e5f18a1b851f991689fdcc9db11bec0143539c", "R10 Git blob mismatch")
    _require(
        hashlib.sha256(data).hexdigest() == "383b4680ad2812941cad6b1c1907277f3f00c0fa43ab4aa8775f5bc9541088d8",
        "R10 SHA-256 mismatch",
    )
    _require(b"**accept** \xe2\x80\x94 **0 Critical, 0 Major, 0 Minor**" in data, "R10 verdict is not accept")


@lru_cache(maxsize=1)
def _registry(schema_root: Path) -> SchemaRegistry:
    return SchemaRegistry(schema_root)


def _expected_candidate() -> dict[str, Any]:
    return {
        "subject_commit": SUBJECT_COMMIT,
        "command_schemas": {"tree_id": "9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea", "schema_count": 87},
        "event_schemas": {"tree_id": "154ffc4bdde82fe903718734687e7a62797b1f69", "schema_count": 86},
        "core_schemas": {"tree_id": "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46", "schema_count": 173},
        "contract_artifacts": {name: binding.as_record() for name, binding in ARTIFACTS.items()},
    }


def _expected_review() -> dict[str, Any]:
    return {
        "review_commit": R10_COMMIT,
        "report": {
            "repository_path": R10_REPORT_PATH,
            "git_blob_id": "64e5f18a1b851f991689fdcc9db11bec0143539c",
            "canonical_utf8_lf_sha256": "383b4680ad2812941cad6b1c1907277f3f00c0fa43ab4aa8775f5bc9541088d8",
        },
        "verdict": {"disposition": "accept", "critical_findings": 0, "major_findings": 0, "minor_findings": 0},
    }


def derive_stage2_accepted_exact_bytes_only(repo_root: Path, record: Mapping[str, Any]) -> Stage2Acceptance:
    """Derive acceptance only after immutable candidate and review validation."""
    _verify_immutable_candidate(repo_root)
    _verify_r10_review(repo_root)
    _registry(repo_root / ".research-system" / "schemas").validate(ACCEPTANCE_SCHEMA_ID, dict(record))
    _require(record["acceptance_statement"] == OWNER_STATEMENT, "owner statement mismatch")
    _require(record["accepted_candidate"] == _expected_candidate(), "accepted candidate binding mismatch")
    _require(record["r10_review"] == _expected_review(), "R10 review binding mismatch")
    _require(
        record["decision"] == {"decision_id": "D-G6-3", "outcome": "accepted", "effective_scope": "exact_bytes_only"},
        "decision binding mismatch",
    )
    _require(record["hard_stops"] == EXPECTED_HARD_STOPS, "hard-stop binding mismatch")
    return Stage2Acceptance(True, SUBJECT_COMMIT, core_schema_tree(repo_root))


def load_stage2_owner_acceptance(repo_root: Path) -> Stage2Acceptance:
    """Load the external record; immutable candidate evidence is never read from checkout bytes."""
    record_bytes = (repo_root / RECORD_PATH).read_bytes()
    if record_bytes.startswith(b"\xef\xbb\xbf") or b"\r" in record_bytes:
        raise ValueError("owner acceptance record is not UTF-8/LF canonical")
    return derive_stage2_accepted_exact_bytes_only(repo_root, yaml.safe_load(record_bytes))
