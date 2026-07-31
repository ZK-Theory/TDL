from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from research_system.authority import (
    GrantedCommandIdentity,
    GrantedPolicyActionIdentity,
    ScopedAuthorityGrant,
)
from research_system.errors import SchemaError
from research_system.schema_registry import bundled_runtime_schema_registry


PROJECT_ID = "prj_01978abc-6100-7000-8000-000000006100"
GRANT_ID = "agr_01978abc-6101-7000-8000-000000006101"
ACTOR_ID = "act_01978abc-6102-7000-8000-000000006102"
REQUIREMENT_ID = "asr_01978abc-6103-7000-8000-000000006103"
TASK_ID = "tsk_01978abc-6104-7000-8000-000000006104"
SUBJECT_IDS = {
    "scope_definition": "obj_01978abc-6110-7000-8000-000000006110",
    "task": "tsk_01978abc-6111-7000-8000-000000006111",
    "dispatch": "dsp_01978abc-6112-7000-8000-000000006112",
    "lease": "els_01978abc-6113-7000-8000-000000006113",
    "attempt": "att_01978abc-6114-7000-8000-000000006114",
    "message": "msg_01978abc-6115-7000-8000-000000006115",
    "blocker": "blk_01978abc-6116-7000-8000-000000006116",
    "artefact": "art_01978abc-6117-7000-8000-000000006117",
    "review": "rev_01978abc-6118-7000-8000-000000006118",
    "decision": "dec_01978abc-6119-7000-8000-000000006119",
    "rule_evaluation": "val_01978abc-6120-7000-8000-000000006120",
    "corrected_record": "msg_01978abc-6121-7000-8000-000000006121",
    "resource": "rgr_01978abc-6122-7000-8000-000000006122",
    "project_store": PROJECT_ID,
    "assurance_requirement": REQUIREMENT_ID,
    "assurance_pack": "asp_01978abc-6123-7000-8000-000000006123",
}
CORRECTED_RECORD_IDS = (
    "cpm_01978abc-6130-7000-8000-000000006130",
    "hbt_01978abc-6131-7000-8000-000000006131",
    "pid_01978abc-6132-7000-8000-000000006132",
    "stp_01978abc-6133-7000-8000-000000006133",
    "rsd_01978abc-6134-7000-8000-000000006134",
    "rcv_01978abc-6135-7000-8000-000000006135",
    "opc_01978abc-6136-7000-8000-000000006136",
    "opr_01978abc-6137-7000-8000-000000006137",
    "bkr_01978abc-6138-7000-8000-000000006138",
)


def _grant_value() -> dict[str, object]:
    return {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.0.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_actor_classes": ["human"],
        "allowed_commands": [
            {
                "command_type": "AcceptAssuranceRequirement",
                "schema_id": "ars://core/command/AcceptAssuranceRequirement",
                "schema_version": "1.0.0",
                "schema_sha256": "1" * 64,
            }
        ],
        "allowed_policy_actions": [
            {
                "policy_action_type": "accept_r3_assurance_requirement",
                "schema_id": "ars://core/policy-action/AcceptR3AssuranceRequirement",
                "schema_version": "1.0.0",
                "schema_sha256": "2" * 64,
            }
        ],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {
                "kind": "assurance_requirement",
                "id": REQUIREMENT_ID,
            },
        },
        "risk_ceiling": "R3",
        "effective_at": "2026-07-31T09:00:00Z",
        "expires_at": "2026-08-01T09:00:00Z",
        "delegable": False,
        "revoked": False,
    }


def test_scoped_authority_grant_v2_binds_exact_command_policy_actor_and_scope() -> None:
    grant = ScopedAuthorityGrant.from_dict(_grant_value())

    assert grant.allowed_actor_classes == ("human",)
    assert grant.allowed_commands == (
        GrantedCommandIdentity(
            command_type="AcceptAssuranceRequirement",
            schema_id="ars://core/command/AcceptAssuranceRequirement",
            schema_version="1.0.0",
            schema_sha256="1" * 64,
        ),
    )
    assert grant.allowed_policy_actions == (
        GrantedPolicyActionIdentity(
            policy_action_type="accept_r3_assurance_requirement",
            schema_id="ars://core/policy-action/AcceptR3AssuranceRequirement",
            schema_version="1.0.0",
            schema_sha256="2" * 64,
        ),
    )
    assert grant.subject_scope.subject_id == REQUIREMENT_ID
    with pytest.raises(FrozenInstanceError):
        grant.actor_id = ACTOR_ID  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("schema_version", "1.1.0"),
        ("allowed_actor_classes", ["importer"]),
        ("allowed_actor_classes", ["human", "human"]),
        ("expires_at", "2026-07-31T09:00:00Z"),
        ("delegable", True),
        ("revoked", True),
    ],
)
def test_scoped_authority_grant_rejects_incompatible_or_unsafe_values(
    field: str,
    replacement: object,
) -> None:
    value = _grant_value()
    value[field] = replacement

    with pytest.raises(ValueError):
        ScopedAuthorityGrant.from_dict(value)


def test_scoped_authority_grant_rejects_wildcards_and_duplicate_identities() -> None:
    wildcard = _grant_value()
    commands = wildcard["allowed_commands"]
    assert isinstance(commands, list)
    command = commands[0]
    assert isinstance(command, dict)
    command["command_type"] = "*"
    with pytest.raises(ValueError):
        ScopedAuthorityGrant.from_dict(wildcard)

    duplicate = _grant_value()
    duplicate_commands = duplicate["allowed_commands"]
    assert isinstance(duplicate_commands, list)
    duplicate_commands.append(dict(duplicate_commands[0]))
    with pytest.raises(ValueError):
        ScopedAuthorityGrant.from_dict(duplicate)


@pytest.mark.parametrize(("subject_kind", "subject_id"), SUBJECT_IDS.items())
def test_scoped_authority_grant_accepts_closed_exact_subject_vocabulary(
    subject_kind: str,
    subject_id: str,
) -> None:
    value = _grant_value()
    value["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": subject_kind, "id": subject_id},
    }
    assert ScopedAuthorityGrant.from_dict(value).subject_scope.subject_id == subject_id


def test_scoped_authority_grant_rejects_wildcard_and_kind_id_mismatch() -> None:
    wildcard = _grant_value()
    wildcard["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": "assurance_requirement", "id": "*"},
    }
    with pytest.raises(ValueError):
        ScopedAuthorityGrant.from_dict(wildcard)

    mismatch = _grant_value()
    mismatch["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": "message", "id": TASK_ID},
    }
    with pytest.raises(ValueError, match="kind and ID mismatch"):
        ScopedAuthorityGrant.from_dict(mismatch)

    project_is_not_correctable = _grant_value()
    project_is_not_correctable["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": "corrected_record", "id": PROJECT_ID},
    }
    with pytest.raises(ValueError, match="kind and ID mismatch"):
        ScopedAuthorityGrant.from_dict(project_is_not_correctable)


@pytest.mark.parametrize("subject_id", CORRECTED_RECORD_IDS)
def test_corrected_record_scope_accepts_complete_closed_selector_prefixes(
    subject_id: str,
) -> None:
    value = _grant_value()
    value["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": "corrected_record", "id": subject_id},
    }
    assert ScopedAuthorityGrant.from_dict(value).subject_scope.subject_id == subject_id


def test_v2_schema_enforces_the_same_closed_subject_vocabulary_as_the_model() -> None:
    schemas = bundled_runtime_schema_registry()
    for subject_kind, subject_id in SUBJECT_IDS.items():
        value = _grant_value()
        value["subject_scope"] = {
            "project_id": PROJECT_ID,
            "subject": {"kind": subject_kind, "id": subject_id},
        }
        schemas.validate_active(
            "ars://core/scoped-authority-grant",
            value,
            schema_version="2.0.0",
        )

    mismatch = _grant_value()
    mismatch["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": "message", "id": TASK_ID},
    }
    with pytest.raises(SchemaError):
        schemas.validate_active(
            "ars://core/scoped-authority-grant",
            mismatch,
            schema_version="2.0.0",
        )
