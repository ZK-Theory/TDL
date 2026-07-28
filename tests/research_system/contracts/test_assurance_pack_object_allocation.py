import hashlib
import json
import re
import subprocess
import uuid
from pathlib import Path

import pytest
import yaml

from research_system.ids import new_id, validate_id

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
PACK_SCHEMA_PATH = ROOT / ".research-system" / "schemas" / "assurance" / "assurance-pack.schema.json"
REGISTRY_PATH = ROOT / ".research-system" / "config" / "id-kind-registry.yaml"
ALLOCATIONS_PATH = ROOT / ".research-system" / "config" / "assurance-pack-object-allocations.yaml"

# The accepted upstream contract subject. The allocation file pins this too; the tests below
# assert the two agree rather than trusting either in isolation.
ACCEPTED_CONTRACT_SUBJECT = "449b0d002edea3013dcc32a115f1870c4a082974"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _assurance_pack_allocations() -> list[dict]:
    return [row for row in _load_yaml(ALLOCATIONS_PATH)["allocations"] if row["id_kind"] == "assurance_pack"]


def _current_allocation() -> dict:
    # Allocations are append-only: superseding one adds a row rather than editing it, so historical
    # revisions are expected to accumulate. The current allocation is the highest revision, and only
    # that revision has to be unique.
    allocations = _assurance_pack_allocations()
    assert allocations, "no assurance_pack allocation"
    current_revision = max(row["assurance_pack_revision"] for row in allocations)
    current = [row for row in allocations if row["assurance_pack_revision"] == current_revision]
    assert len(current) == 1, f"expected one allocation at revision {current_revision}, found {len(current)}"
    return current[0]


def _contract_pack_object() -> dict:
    return _load_yaml(CONTRACT_PATH)["proposed_pack_identity"]["assurance_pack_object"]


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, cwd=ROOT, text=True)


def _git_blob(path: Path) -> str:
    repo_relative = path.relative_to(ROOT).as_posix()
    completed = _git("hash-object", "--path", repo_relative, str(path))
    assert completed.returncode == 0, f"git hash-object failed: {completed.stderr.strip()}"
    return completed.stdout.strip()


def _blob_at_commit(commit: str, repo_relative: str) -> str | None:
    """Return the blob id recorded for a path at a commit, or None if the commit is unreachable.

    Args:
        commit: Commit-ish to resolve the path against.
        repo_relative: Repository-relative POSIX path.

    Returns:
        The blob id, or None when history for that commit is not present locally.
    """
    completed = _git("rev-parse", f"{commit}:{repo_relative}")
    return completed.stdout.strip() if completed.returncode == 0 else None


def _repository_is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true"


def test_assurance_pack_kind_uses_the_contract_declared_owner_prefix():
    # The prefix is not a local choice: the owner-accepted contract declares it and the accepted
    # contract schema pins it as a const. Read it from the contract so registry drift fails here.
    declared_prefix = _contract_pack_object()["id_prefix"]
    assert _load_yaml(REGISTRY_PATH)["kinds"]["assurance_pack"] == declared_prefix

    minted = new_id("assurance_pack")
    assert minted.startswith(f"{declared_prefix}_")
    assert uuid.UUID(minted.removeprefix(f"{declared_prefix}_")).version == 7
    assert validate_id(minted, "assurance_pack") == minted


def test_assurance_pack_prefix_does_not_collide_with_assurance_requirement():
    kinds = _load_yaml(REGISTRY_PATH)["kinds"]
    assert kinds["assurance_pack"] != kinds["assurance_requirement"]

    requirement_id = new_id("assurance_requirement")
    with pytest.raises(ValueError, match="expected assurance_pack ID"):
        validate_id(requirement_id, "assurance_pack")


def test_allocated_object_id_is_a_valid_registered_identity():
    allocated = _current_allocation()["assurance_pack_id"]
    assert validate_id(allocated, "assurance_pack") == allocated

    # Independently of the registry, the pack schema constrains the field the future candidate
    # will carry. The allocated id has to satisfy that pattern or the candidate cannot be valid.
    pattern = json.loads(PACK_SCHEMA_PATH.read_text(encoding="utf-8"))["$defs"]["assurancePackId"]["pattern"]
    assert re.fullmatch(pattern, allocated)


def test_allocation_agrees_with_the_contract_and_the_pack_schema():
    allocation = _current_allocation()
    contract = _load_yaml(CONTRACT_PATH)
    pack_identity = contract["proposed_pack_identity"]
    pack_schema_properties = json.loads(PACK_SCHEMA_PATH.read_text(encoding="utf-8"))["properties"]

    assert allocation["assurance_pack_revision"] == pack_identity["assurance_pack_object"]["revision"]
    assert allocation["assurance_pack_revision"] == pack_schema_properties["assurance_pack_revision"]["const"]
    assert allocation["canonical_repository_path"] == pack_identity["repository_path"]
    assert allocation["canonical_repository_path"] == pack_schema_properties["canonical_repository_path"]["const"]
    assert allocation["distribution_scope"] == pack_identity["distribution_scope"]
    assert allocation["distribution_scope"] == pack_schema_properties["distribution_scope"]["const"]


def test_allocation_binds_the_unmodified_accepted_contract_subject():
    # The allocation derives its authority from an owner-accepted contract at exact bytes. If the
    # contract is edited, the allocation is no longer authorized by what it claims to be authorized
    # by, and this fails rather than letting the drift pass silently.
    allocation = _current_allocation()
    repo_relative = CONTRACT_PATH.relative_to(ROOT).as_posix()
    assert allocation["authorizing_subject_commit"] == ACCEPTED_CONTRACT_SUBJECT
    assert allocation["authorizing_contract_path"] == repo_relative

    contract_bytes = CONTRACT_PATH.read_bytes()
    assert b"\r\n" not in contract_bytes, "contract must be LF in the working tree (canonical byte surface)"
    assert hashlib.sha256(contract_bytes).hexdigest() == allocation["authorizing_contract_canonical_sha256"]
    assert _git_blob(CONTRACT_PATH) == allocation["authorizing_contract_git_blob"]

    # The checks above prove the contract has not drifted from what the allocation pins. They do not
    # prove those pins belong to the commit the allocation names as its authority: updating the pins
    # to match an edited contract while leaving authorizing_subject_commit stale would pass them.
    # Resolve the blob at the named commit to close that. Shallow checkouts (CI uses
    # actions/checkout@v4, which defaults to depth 1) do not carry the object, so the assertion is
    # conditional on the history being present rather than silently absent.
    blob_at_subject = _blob_at_commit(ACCEPTED_CONTRACT_SUBJECT, repo_relative)
    if blob_at_subject is None:
        assert _repository_is_shallow(), (
            f"{ACCEPTED_CONTRACT_SUBJECT}:{repo_relative} is unreachable in a full checkout; "
            "the allocation names a commit this repository does not contain"
        )
    else:
        assert blob_at_subject == allocation["authorizing_contract_git_blob"]


def test_allocations_are_unique_per_object_and_per_revision():
    rows = _load_yaml(ALLOCATIONS_PATH)["allocations"]
    ids = [row["assurance_pack_id"] for row in rows]
    revisions = [(row["id_kind"], row["assurance_pack_revision"]) for row in rows]

    assert len(set(ids)) == len(ids), "duplicate allocated object id"
    assert len(set(revisions)) == len(revisions), "duplicate (id_kind, revision) allocation"


def test_every_allocated_kind_is_registered():
    kinds = _load_yaml(REGISTRY_PATH)["kinds"]
    for row in _load_yaml(ALLOCATIONS_PATH)["allocations"]:
        assert row["id_kind"] in kinds, f"allocation names an unregistered kind: {row['id_kind']}"
        assert row["assurance_pack_id"].startswith(f"{kinds[row['id_kind']]}_")
