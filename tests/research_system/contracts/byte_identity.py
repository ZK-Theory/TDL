"""One shared shape for the controls of a byte-identity guard.

When Stephen accepts an artefact by content address, the test that pins it must compare bytes, and its negative
controls must run through that comparison. The WP9.2-1 envelope test wrote three controls that compared a tampered
envelope with the expected bytes directly, beside the guard instead of through it. Weakening the guard to an object
comparison, or deleting it, left all three green, although ``contract-first-tdd`` already said to delete the guard in
memory and confirm the control fails (observation 2026-10-28-byte-identity-controls-bypass-their-guard-despite-
checklist). The prose rule had failed once, so the shape lives here.

``assert_byte_identity`` builds three refusals that parse to the same JSON value as the committed bytes: a
pretty-printed copy, and the committed bytes followed by ``\\n`` and by ``\\r\\n``. Only a byte comparison can refuse
them, so a guard that compares parsed objects fails here, and so does a guard that accepts everything. The caller adds
the schema-valid tampers that only its own guard knows how to make.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable


def object_equal_refusals(committed: bytes) -> list[bytes]:
    """Return byte strings that differ from ``committed`` but parse to the same JSON value."""
    parsed = json.loads(committed)
    return [
        json.dumps(parsed, indent=2, sort_keys=True).encode(),
        committed + b"\n",
        committed + b"\r\n",
    ]


def assert_byte_identity(accepts: Callable[[bytes], bool], committed: bytes, tampers: Iterable[bytes] = ()) -> None:
    """Assert that the guard ``accepts`` admits the committed bytes and refuses every other byte string given.

    Args:
        accepts: The guard under test: the one predicate the positive test also calls.
        committed: The byte string the owner accepted.
        tampers: Byte strings whose parsed value differs from ``committed``, such as a schema-valid tamper.
    """
    assert accepts(committed), "the guard refuses the committed bytes"
    parsed = json.loads(committed)
    for data in object_equal_refusals(committed):
        assert data != committed and json.loads(data) == parsed
        assert not accepts(data), f"the guard admits an object-equal re-encoding: {data[:60]!r}"
    for data in tampers:
        assert json.loads(data) != parsed, "a tamper must change the parsed value; re-encodings are built here"
        assert not accepts(data), f"the guard admits a tamper: {data[:60]!r}"
