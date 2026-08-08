import uuid

import pytest

from research_system import canonical as canonical_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConfigurationError
from research_system.ids import IdRegistry, new_id, validate_id


def test_canonical_bytes_are_order_independent():
    left = canonical_bytes({"b": 2, "a": 1})
    right = canonical_bytes({"a": 1, "b": 2})
    assert left == b'{"a":1,"b":2}'
    assert left == right
    assert sha256_hex(left) == sha256_hex(right)


def test_jsonable_recursively_normalizes_tuples_for_canonical_bytes():
    value = {"outer": ({"inner": (1, 2)},)}
    normalized = canonical_module.jsonable(value)
    assert normalized == {"outer": [{"inner": [1, 2]}]}
    assert canonical_bytes(normalized) == b'{"outer":[{"inner":[1,2]}]}'


@pytest.mark.parametrize(
    "value, message",
    [
        ({"value": 1.5}, "floating-point"),
        ({"cafÃ©": "value"}, "ASCII object keys"),
        ({"value": 2**53}, "safe integer range"),
    ],
)
def test_p0_canonical_subset_rejects_non_interoperable_values(value, message):
    with pytest.raises(ValueError, match=message):
        canonical_bytes(value)


def test_ids_use_registered_owner_prefix_and_uuid7_body():
    command_id = new_id("command")
    assert command_id.startswith("cmd_")
    assert uuid.UUID(command_id.removeprefix("cmd_")).version == 7
    assert validate_id(command_id, "command") == command_id


def test_wrong_or_unknown_kind_is_rejected():
    assurance_id = new_id("assurance_requirement")
    assert assurance_id.startswith("asr_")
    with pytest.raises(ValueError, match="expected command ID"):
        validate_id(assurance_id, "command")
    with pytest.raises(ValueError, match="unknown ID kind"):
        new_id("arbitrary_prefix")


def test_accepted_w2_artefact_kind_uses_owner_prefix():
    artefact_id = new_id("artefact")
    assert artefact_id.startswith("art_")
    assert validate_id(artefact_id, "artefact") == artefact_id


def test_scope_definition_uses_w2_object_prefix():
    scope_id = new_id("scope_definition")
    assert scope_id.startswith("obj_")
    assert validate_id(scope_id, "scope_definition") == scope_id


def test_registry_rejects_duplicate_kind_prefixes():
    with pytest.raises(ConfigurationError, match="duplicate ID kind prefixes"):
        IdRegistry({"route_request": "rrq", "resource_request": "rrq"})


def test_resource_request_uses_distinct_w8_owner_prefix():
    resource_request_id = new_id("resource_request")
    assert resource_request_id.startswith("rsq_")
    assert validate_id(resource_request_id, "resource_request") == resource_request_id


def test_backup_receipt_uses_w8_owner_prefix():
    receipt_id = new_id("backup_receipt")
    assert receipt_id.startswith("bkr_")
    assert validate_id(receipt_id, "backup_receipt") == receipt_id
