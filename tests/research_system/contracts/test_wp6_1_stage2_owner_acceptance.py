from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess

import pytest
import yaml

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts import wp6_1_stage2_acceptance_validation as validation
from tests.research_system.contracts.wp6_1_stage2_acceptance_validation import (
    derive_stage2_accepted_exact_bytes_only,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
RECORD_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-stage2-owner-acceptance-record.yaml"
SCHEMA_ID = "ars://contracts/wp6-1-stage2-owner-acceptance-record"


def _record() -> dict:
    return yaml.safe_load(RECORD_PATH.read_bytes())


def _set(record: dict, path: tuple[str, ...], value: object) -> None:
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def test_wp6_1_stage2_owner_acceptance_is_external_and_exact() -> None:
    record = _record()
    registry = SchemaRegistry(SCHEMA_ROOT)

    assert registry.contains(SCHEMA_ID)
    registry.validate(SCHEMA_ID, record)
    derived = derive_stage2_accepted_exact_bytes_only(REPO_ROOT, record)

    assert derived.accepted_exact_bytes_only is True
    assert derived.subject_commit == "c7e32755e9adb2f39f6a40056ef6058986c9263d"
    assert derived.core_tree == "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("accepted_candidate", "subject_commit"), "0000000000000000000000000000000000000000"),
        (("accepted_candidate", "command_schemas", "tree_id"), "0000000000000000000000000000000000000000"),
        (
            ("accepted_candidate", "contract_artifacts", "schema_identities", "git_blob_id"),
            "0000000000000000000000000000000000000000",
        ),
        (("r10_review", "review_commit"), "0000000000000000000000000000000000000000"),
        (("acceptance_statement",), "altered owner statement"),
        (("decision", "outcome"), "rejected"),
        (("hard_stops", "hooks_authorized"), True),
    ],
)
def test_wp6_1_stage2_owner_acceptance_rejects_bound_identity_mutations(path: tuple[str, ...], value: object) -> None:
    record = deepcopy(_record())
    _set(record, path, value)

    with pytest.raises(SchemaError):
        derive_stage2_accepted_exact_bytes_only(REPO_ROOT, record)


def test_wp6_1_stage2_owner_acceptance_rejects_extra_and_live_status_fields() -> None:
    record = deepcopy(_record())
    record["acceptance_status"] = "accepted"

    with pytest.raises(SchemaError):
        derive_stage2_accepted_exact_bytes_only(REPO_ROOT, record)


def test_wp6_1_stage2_candidate_pending_snapshot_does_not_override_external_acceptance() -> None:
    snapshot = validation.candidate_snapshot_statuses(REPO_ROOT)

    assert snapshot == {
        "review_status": "pending_independent_review",
        "acceptance_status": "pending_d_g6_3_owner_acceptance",
    }
    assert derive_stage2_accepted_exact_bytes_only(REPO_ROOT, _record()).accepted_exact_bytes_only is True


def test_wp6_1_stage2_owner_acceptance_rejects_immutable_git_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_run = validation.subprocess.run
    target = f"{validation.SUBJECT_COMMIT}:{validation.IDENTITY_MANIFEST_PATH}"

    def substituted_run(args: list[str], *args_: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        result = real_run(args, *args_, **kwargs)
        if args == ["git", "show", target]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=result.stdout.replace(b"wp6-1-schema-identities", b"wp6-1-schema-alias", 1),
                stderr=b"",
            )
        return result

    monkeypatch.setattr(validation.subprocess, "run", substituted_run)

    with pytest.raises(ValueError, match="immutable Git (blob|SHA-256) mismatch"):
        derive_stage2_accepted_exact_bytes_only(REPO_ROOT, _record())


def test_wp6_1_stage2_owner_acceptance_preserves_the_accepted_core_tree() -> None:
    assert validation.core_schema_tree(REPO_ROOT) == "b88ac9c83705d36b3c19f5c5172e0fa4aa7ebb46"
