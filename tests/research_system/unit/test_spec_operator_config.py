from __future__ import annotations

from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes
from research_system.config import SpecOperatorConfig
from research_system.errors import ConfigurationError


PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"
ACTOR_ID = "act_01978abc-0001-7000-8000-000000000002"
SESSION_ID = "ses_01978abc-0001-7000-8000-000000000003"
GRANT_ID = "agr_01978abc-0001-7000-8000-000000000004"


def _operator_config(control_root: Path) -> dict[str, str]:
    return {
        "schema_id": "ars://operations/spec-operator-config",
        "schema_version": "1.0.0",
        "control_root": str(control_root),
        "project_id": PROJECT_ID,
        "store_identity": "a" * 64,
        "route_id": "SPEC-GATE6-RUN-V1",
        "operator_actor_id": ACTOR_ID,
        "actor_session_id": SESSION_ID,
        "authority_grant_id": GRANT_ID,
    }


def test_spec_operator_config_loads_exact_authority_neutral_evidence(tmp_path: Path) -> None:
    """Remediation-red: selection evidence is strict but grants no authority."""

    control_root = tmp_path / "physical-control"
    control_root.mkdir()
    path = tmp_path / "operator-config.json"
    path.write_bytes(canonical_bytes(_operator_config(control_root)))

    config = SpecOperatorConfig.load(path)

    assert config.control_root == control_root.resolve(strict=True)
    assert config.project_id == PROJECT_ID
    assert config.store_identity == "a" * 64
    assert config.route_id == "SPEC-GATE6-RUN-V1"
    assert config.operator_actor_id == ACTOR_ID
    assert config.actor_session_id == SESSION_ID
    assert config.authority_grant_id == GRANT_ID


@pytest.mark.parametrize(
    "mutation",
    (
        "extra",
        "missing",
        "schema_id",
        "schema_version",
        "route_id",
        "relative_control_root",
        "missing_control_root",
        "project_id",
        "store_identity",
        "operator_actor_id",
        "actor_session_id",
        "authority_grant_id",
    ),
)
def test_spec_operator_config_rejects_noncanonical_or_unusable_evidence(
    tmp_path: Path,
    mutation: str,
) -> None:
    """Remediation-red: malformed selection inputs fail before binding admission."""

    control_root = tmp_path / "physical-control"
    control_root.mkdir()
    value = _operator_config(control_root)
    if mutation == "extra":
        value["authority"] = "invented"
    elif mutation == "missing":
        value.pop("route_id")
    elif mutation == "schema_id":
        value["schema_id"] = "ars://operations/other"
    elif mutation == "schema_version":
        value["schema_version"] = "1.0"
    elif mutation == "route_id":
        value["route_id"] = "LOCAL-ADMIN"
    elif mutation == "relative_control_root":
        value["control_root"] = "physical-control"
    elif mutation == "missing_control_root":
        value["control_root"] = str(tmp_path / "missing")
    elif mutation == "project_id":
        value["project_id"] = "project-1"
    elif mutation == "store_identity":
        value["store_identity"] = "A" * 64
    elif mutation == "operator_actor_id":
        value["operator_actor_id"] = "act_not-a-uuid"
    elif mutation == "actor_session_id":
        value["actor_session_id"] = "ses_not-a-uuid"
    elif mutation == "authority_grant_id":
        value["authority_grant_id"] = "agr_not-a-uuid"
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")

    with pytest.raises(ConfigurationError):
        SpecOperatorConfig.from_raw(canonical_bytes(value))
