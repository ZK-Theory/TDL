"""JSON field families for W9 membership tables (WP9.3 note §8.2; membership template §3; W9-T2, W9-T3).

Parsing follows template §3 rule 1, which Python's ``json`` does not meet by default (review m-5):

- the bytes are decoded strictly as UTF-8; a BOM or any other encoding blocks (``json.loads`` on bytes accepts both);
- a duplicate key anywhere blocks (``json.loads`` silently keeps the last one);
- the bare tokens ``NaN``, ``Infinity`` and ``-Infinity`` are accepted as numbers, and their pointers are recorded;
- a finite literal that overflows to infinity, such as ``1e400``, blocks: the template does not say how to record it;
- a lone-surrogate escape blocks;
- any other departure from RFC 8259 blocks, as ``json.loads`` with ``strict=True`` refuses it.

Pattern expansion and the both-directions exhaustiveness and exclusivity checks are template §3 rules 2 to 5.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from research_system.errors import IntegrityError

_BOM = b"\xef\xbb\xbf"
_WILDCARD = "[*]"


class JsonBlocked(IntegrityError):
    """The bytes are not JSON under template §3 rule 1, or a table does not cover them (rules 2 to 5)."""


class _NonFinite(float):
    """A float that remembers it came from a bare non-finite token."""

    token: str

    def __new__(cls, token: str) -> _NonFinite:
        value = super().__new__(cls, {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}[token])
        value.token = token
        return value


@dataclass(frozen=True)
class ParsedJson:
    """A parsed result file: the value, and the pointers of its non-finite number leaves (template §3 rule 1)."""

    value: Any
    non_finite_pointers: tuple[str, ...]

    @property
    def non_finite_tokens(self) -> bool:
        """Whether the file holds ``NaN``, ``Infinity`` or ``-Infinity``, which the observation records."""
        return bool(self.non_finite_pointers)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JsonBlocked(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def _float(text: str) -> float:
    value = float(text)
    if math.isinf(value):
        raise JsonBlocked(f"JSON number overflows to infinity: {text}")
    return value


def escape(segment: str) -> str:
    """RFC 6901: ``~`` is written ``~0`` and ``/`` is written ``~1`` (template §3 rule 7)."""
    return segment.replace("~", "~0").replace("/", "~1")


def _walk(value: Any, pointer: str = "") -> Iterator[tuple[str, Any]]:
    yield pointer, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{pointer}/{escape(key)}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{pointer}/{index}")


def _has_lone_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(char) <= 0xDFFF for char in text)


def parse_strict(data: bytes) -> ParsedJson:
    """Parse result-file bytes under template §3 rule 1.

    Raises:
        JsonBlocked: On a BOM, non-UTF-8 bytes, a duplicate key, an overflowing number, a lone surrogate, or any other
            departure from RFC 8259.
    """

    if not isinstance(data, bytes):
        raise JsonBlocked("JSON parsing reads bytes")
    if data.startswith(_BOM):
        raise JsonBlocked("JSON bytes start with a BOM")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise JsonBlocked("JSON bytes are not UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_NonFinite, parse_float=_float, strict=True)
    except JsonBlocked:
        raise
    except (ValueError, RecursionError) as exc:
        raise JsonBlocked(f"JSON departs from RFC 8259: {exc}") from exc
    non_finite = []
    for pointer, node in _walk(value):
        if isinstance(node, str) and _has_lone_surrogate(node):
            raise JsonBlocked("JSON string holds a lone surrogate")
        if isinstance(node, dict) and any(_has_lone_surrogate(key) for key in node):
            raise JsonBlocked("JSON key holds a lone surrogate")
        if isinstance(node, _NonFinite):
            non_finite.append(pointer)
    return ParsedJson(value, tuple(non_finite))


def observed_pointers(value: Any) -> tuple[str, ...]:
    """Every leaf and container pointer present, the root ``""`` included (template §3 rule 2)."""
    return tuple(pointer for pointer, _ in _walk(value))


def _segments(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise JsonBlocked(f"not an RFC 6901 pointer: {pointer!r}")
    return pointer[1:].split("/")


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def expand(pattern: str, value: Any) -> tuple[str, ...]:
    """Expand one table entry against the observed value (template §3 rules 2 and 5).

    A ``[*]`` segment means every index of an array, never an object key. A concrete pointer, or a pattern whose
    array is absent, that the value does not hold blocks; a ``[*]`` over a present empty array expands to nothing.

    Raises:
        JsonBlocked: If the entry names a pointer the bytes do not hold.
    """

    nodes: list[tuple[str, Any]] = [("", value)]
    for segment in _segments(pattern):
        expanded: list[tuple[str, Any]] = []
        for pointer, node in nodes:
            if segment == _WILDCARD:
                if not isinstance(node, list):
                    raise JsonBlocked(f"table pattern {pattern!r}: [*] does not name an array")
                expanded.extend((f"{pointer}/{index}", child) for index, child in enumerate(node))
                continue
            key = _unescape(segment)
            if isinstance(node, dict) and key in node:
                expanded.append((f"{pointer}/{segment}", node[key]))
            elif isinstance(node, list) and key.isdigit() and str(int(key)) == key and int(key) < len(node):
                expanded.append((f"{pointer}/{segment}", node[int(key)]))
            else:
                raise JsonBlocked(f"table pointer {pattern!r} is absent from the observed bytes")
        nodes = expanded
    return tuple(pointer for pointer, _ in nodes)


def assign(families: Sequence[Mapping[str, Any]], unassigned: Iterable[str], value: Any) -> dict[str, str]:
    """Check a membership table against observed bytes and return each pointer's one family (template §3).

    Args:
        families: The table's families, each with ``name`` and ``pointers`` (patterns allowed).
        unassigned: The table's ``unassigned`` list, which must be empty for import (W9-T3).
        value: The parsed observed value.

    Returns:
        Every observed pointer mapped to its one family.

    Raises:
        JsonBlocked: If ``unassigned`` is not empty, a table pointer is absent, a pointer is in two families, or an
            observed pointer is in none.
    """

    if list(unassigned):
        raise JsonBlocked("the membership table has unassigned pointers")
    owner: dict[str, str] = {}
    for family in families:
        for pattern in family["pointers"]:
            for pointer in expand(pattern, value):
                if pointer in owner and owner[pointer] != family["name"]:
                    raise JsonBlocked(f"pointer {pointer!r} is in two families")
                owner[pointer] = family["name"]
    missing = [pointer for pointer in observed_pointers(value) if pointer not in owner]
    if missing:
        raise JsonBlocked(f"observed pointers no family covers: {missing[:5]}")
    return owner
