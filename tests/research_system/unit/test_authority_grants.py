from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from research_system.authority import AuthorityGrant, AuthorityScope
from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry
from tests.research_system.factories import REPO_ROOT


PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
ACTOR_ID = "act_01978abc-1002-7000-8000-000000001002"
GRANT_ID = "agr_01978abc-1001-7000-8000-000000001001"
DECISION_ID = "rgd_01978abc-1003-7000-8000-000000001003"


def test_authority_grant_110_contract_is_frozen_and_strict() -> None:
    grant = AuthorityGrant.from_dict(
        {
            "schema_id": "ars://core/authority-grant",
            "schema_version": "1.1.0",
            "authority_grant_id": GRANT_ID,
            "actor_id": ACTOR_ID,
            "allowed_command_types": ["PublishReleaseGateDecision"],
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": "release_gate_decision", "id": DECISION_ID},
            },
            "risk_ceiling": "R2",
            "effective_at": "2026-07-12T00:00:00Z",
            "expires_at": "2026-07-13T00:00:00Z",
            "delegable": False,
            "revoked": False,
        }
    )

    assert grant.subject_scope == AuthorityScope(
        project_id=PROJECT_ID,
        subject_kind="release_gate_decision",
        subject_id=DECISION_ID,
    )
    assert grant.allowed_command_types == ("PublishReleaseGateDecision",)
    with pytest.raises(FrozenInstanceError):
        grant.actor_id = ACTOR_ID  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "1.0.0"),
        ("allowed_command_types", ["*"]),
        ("delegable", True),
        ("revoked", True),
        ("risk_ceiling", 2.0),
    ],
)
def test_authority_grant_110_rejects_noncanonical_contract_values(
    field: str, value: object
) -> None:
    payload = {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_command_types": ["PublishReleaseGateDecision"],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "release_gate_decision", "id": DECISION_ID},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    payload[field] = value
    with pytest.raises(ValueError):
        AuthorityGrant.from_dict(payload)


def test_authority_grant_rejects_unhashable_command_elements_as_value_error() -> None:
    payload = {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_command_types": [["nested-command"]],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "release_gate_decision", "id": DECISION_ID},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    with pytest.raises(ValueError, match="allowed command types"):
        AuthorityGrant.from_dict(payload)


@pytest.mark.parametrize(
    "expires_at",
    ["2026-07-12T00:00:00Z", "2026-07-11T23:59:59Z"],
)
def test_authority_grant_rejects_equal_or_inverted_time_range(
    expires_at: str,
) -> None:
    payload = {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_command_types": ["PublishReleaseGateDecision"],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "release_gate_decision", "id": DECISION_ID},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": expires_at,
        "delegable": False,
        "revoked": False,
    }

    with pytest.raises(ValueError, match="strictly after"):
        AuthorityGrant.from_dict(payload)


def test_registered_authority_grant_110_schema_rejects_extra_scope() -> None:
    registry = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    payload = {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_command_types": ["PublishReleaseGateDecision"],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "release_gate_decision", "id": DECISION_ID},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    registry.validate("ars://core/authority-grant", payload)
    payload["subject_scope"]["candidate"] = "p0"
    with pytest.raises(SchemaError, match="candidate"):
        registry.validate("ars://core/authority-grant", payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("delegable", True),
        ("revoked", True),
        ("allowed_command_types", ["*"]),
        ("allowed_command_types", ["bad/path"]),
        ("allowed_command_types", ["bad\\path"]),
    ],
)
def test_registered_authority_grant_110_schema_matches_model_constraints(
    field: str, value: object
) -> None:
    payload = {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_command_types": ["PublishReleaseGateDecision"],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "release_gate_decision", "id": DECISION_ID},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    payload[field] = value
    with pytest.raises(SchemaError):
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas").validate(
            "ars://core/authority-grant", payload
        )


@pytest.mark.parametrize(
    ("kind", "subject_id"),
    [
        ("authority_grant", DECISION_ID),
        ("release_gate_decision", GRANT_ID),
    ],
)
def test_registered_scope_schema_binds_subject_kind_to_id_prefix(
    kind: str, subject_id: str
) -> None:
    payload = {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": GRANT_ID,
        "actor_id": ACTOR_ID,
        "allowed_command_types": ["PublishReleaseGateDecision"],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": kind, "id": subject_id},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": "2026-07-13T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    with pytest.raises(SchemaError, match="subject"):
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas").validate(
            "ars://core/authority-grant", payload
        )
