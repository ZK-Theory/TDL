import uuid

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id, validate_id


def test_canonical_bytes_are_order_independent():
    left = canonical_bytes({'b': 2, 'a': 1})
    right = canonical_bytes({'a': 1, 'b': 2})
    assert left == b'{"a":1,"b":2}'
    assert left == right
    assert sha256_hex(left) == sha256_hex(right)


@pytest.mark.parametrize(
    'value, message',
    [
        ({'value': 1.5}, 'floating-point'),
        ({'café': 'value'}, 'ASCII object keys'),
        ({'value': 2**53}, 'safe integer range'),
    ],
)
def test_p0_canonical_subset_rejects_non_interoperable_values(value, message):
    with pytest.raises(ValueError, match=message):
        canonical_bytes(value)


def test_ids_use_registered_owner_prefix_and_uuid7_body():
    command_id = new_id('command')
    assert command_id.startswith('cmd_')
    assert uuid.UUID(command_id.removeprefix('cmd_')).version == 7
    assert validate_id(command_id, 'command') == command_id


def test_wrong_or_unknown_kind_is_rejected():
    assurance_id = new_id('assurance_requirement')
    assert assurance_id.startswith('asr_')
    with pytest.raises(ValueError, match='expected command ID'):
        validate_id(assurance_id, 'command')
    with pytest.raises(ValueError, match='unknown ID kind'):
        new_id('arbitrary_prefix')

def test_accepted_w2_artefact_kind_uses_owner_prefix():
    artefact_id = new_id('artefact')
    assert artefact_id.startswith('art_')
    assert validate_id(artefact_id, 'artefact') == artefact_id
