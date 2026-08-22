from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from research_system.config import SpecOperatorConfig
from research_system.errors import ConfigurationError, SchemaError
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ID = "ars://operations/spec-operator-config"
SCHEMA_VERSION = "1.0.0"
ROUTE_ID = "SPEC-GATE6-RUN-V1"
PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"
ACTOR_ID = "act_01978abc-0001-7000-8000-000000000002"
GRANT_ID = "agr_01978abc-0001-7000-8000-000000000003"


def _document(tmp_path: Path) -> dict[str, object]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "control_root": str((tmp_path / "control-store").resolve()),
        "project_id": PROJECT_ID,
        "store_identity": "a" * 64,
        "route_id": ROUTE_ID,
        "operator_actor_id": ACTOR_ID,
        "actor_session_id": "ses_gate6_operator_01",
        "authority_grant_id": GRANT_ID,
    }


def _raw(document: dict[str, object]) -> bytes:
    return json.dumps(document, sort_keys=True).encode("utf-8")


def _schema_validator() -> Draft202012Validator:
    schema = json.loads(
        (ROOT / ".research-system" / "schemas" / "operations" / "spec-operator-config.schema.json").read_bytes()
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_spec_operator_config_loads_exact_authority_neutral_locator(tmp_path: Path) -> None:
    document = _document(tmp_path)
    config_path = tmp_path / "operator-config.json"
    config_path.write_bytes(_raw(document))

    config = SpecOperatorConfig.load(config_path)

    assert config.schema_id == SCHEMA_ID
    assert config.schema_version == SCHEMA_VERSION
    assert config.control_root == Path(document["control_root"])
    assert config.project_id == PROJECT_ID
    assert config.store_identity == "a" * 64
    assert config.route_id == ROUTE_ID
    assert config.operator_actor_id == ACTOR_ID
    assert config.actor_session_id == "ses_gate6_operator_01"
    assert config.authority_grant_id == GRANT_ID
    assert {field.name for field in fields(SpecOperatorConfig)} == {
        "schema_id",
        "schema_version",
        "control_root",
        "project_id",
        "store_identity",
        "route_id",
        "operator_actor_id",
        "actor_session_id",
        "authority_grant_id",
    }
    assert not any(hasattr(config, name) for name in ("authorize", "admin", "semantic_authority"))


@pytest.mark.parametrize("missing", sorted(_document(Path("C:/unused")).keys()))
def test_spec_operator_config_requires_every_field(tmp_path: Path, missing: str) -> None:
    document = _document(tmp_path)
    document.pop(missing)

    with pytest.raises(ConfigurationError, match="fields are not exact"):
        SpecOperatorConfig.from_raw(_raw(document))


def test_spec_operator_config_rejects_unknown_field_and_wrong_route(tmp_path: Path) -> None:
    document = _document(tmp_path)
    document["unexpected"] = "must not become authority"
    with pytest.raises(ConfigurationError, match="fields are not exact"):
        SpecOperatorConfig.from_raw(_raw(document))

    document = _document(tmp_path)
    document["route_id"] = "OTHER-ROUTE"
    with pytest.raises(ConfigurationError, match="route_id"):
        SpecOperatorConfig.from_raw(_raw(document))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("control_root", "relative/control"),
        ("project_id", "prj_not-a-uuid"),
        ("operator_actor_id", "act_not-a-uuid"),
        ("authority_grant_id", "agr_not-a-uuid"),
        ("store_identity", "A" * 64),
        ("actor_session_id", "   "),
    ],
)
def test_spec_operator_config_rejects_malformed_locator_fields(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    document = _document(tmp_path)
    document[field] = value

    with pytest.raises(ConfigurationError):
        SpecOperatorConfig.from_raw(_raw(document))


def test_spec_operator_config_does_not_require_store_existence_or_authorize_root(tmp_path: Path) -> None:
    document = _document(tmp_path)
    absent_root = tmp_path / "not-yet-materialized" / "store"
    document["control_root"] = str(absent_root)

    config = SpecOperatorConfig.from_raw(_raw(document))

    assert config.control_root == absent_root
    assert not absent_root.exists()
    # Wrong-root, redirection, and project/store admission belong to the
    # shared verified-binding loader, not to this authority-neutral locator.


def test_spec_operator_config_schema_and_loader_agree(tmp_path: Path) -> None:
    document = _document(tmp_path)
    validator = _schema_validator()

    validator.validate(document)
    loaded = SpecOperatorConfig.from_raw(_raw(document))
    assert loaded.route_id == document["route_id"]

    for field, value in {
        "control_root": "relative",
        "project_id": "prj_not-a-uuid",
        "operator_actor_id": "act_not-a-uuid",
        "authority_grant_id": "agr_not-a-uuid",
        "actor_session_id": "   ",
    }.items():
        invalid = dict(document)
        invalid[field] = value
        assert list(validator.iter_errors(invalid)), field
        with pytest.raises(ConfigurationError):
            SpecOperatorConfig.from_raw(_raw(invalid))


def test_spec_operator_config_is_registered_and_unknown_fields_are_schema_errors(tmp_path: Path) -> None:
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    document = _document(tmp_path)

    registry.validate(SCHEMA_ID, document, schema_version=SCHEMA_VERSION)
    document["unexpected"] = "forbidden"
    with pytest.raises(SchemaError, match="Additional properties"):
        registry.validate(SCHEMA_ID, document, schema_version=SCHEMA_VERSION)
