# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §8.2)
# Purpose: vectors for template §3 rule 1 parsing and rules 2 to 5 (patterns, exhaustiveness, exclusivity).
"""JSON family vectors (WP9.3 note §8.2; membership template §3; W9-T3). Each refusal asserts its own message."""

from __future__ import annotations

import pytest

from research_system.legacy.json_families import JsonBlocked, assign, expand, observed_pointers, parse_strict


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b'\xef\xbb\xbf{"a": 1}', "JSON bytes start with a BOM"),
        ('{"a": 1}'.encode("utf-16"), "JSON bytes are not UTF-8"),
        ('{"a": 1}'.encode("utf-16-le"), "JSON departs from RFC 8259"),
        (b'{"a": 1, "a": 2}', "duplicate JSON key: 'a'"),
        (b'{"x": {"a": 1, "a": 2}}', "duplicate JSON key: 'a'"),
        (b'{"a": 1e400}', "JSON number overflows to infinity: 1e400"),
        (b'{"a": -1e400}', "JSON number overflows to infinity: -1e400"),
        (b'{"a": "\\ud800"}', "JSON string holds a lone surrogate"),
        (b'{"\\udfff": 1}', "JSON key holds a lone surrogate"),
        (b"{'a': 1}", "JSON departs from RFC 8259"),
        (b'{"a": 1,}', "JSON departs from RFC 8259"),
        (b'{"a": "x\ny"}', "JSON departs from RFC 8259"),
        (b"\xff", "JSON bytes are not UTF-8"),
    ],
    ids=[
        "bom",
        "utf-16",
        "utf-16-no-bom",
        "duplicate-key",
        "nested-duplicate-key",
        "overflow",
        "negative-overflow",
        "lone-surrogate-value",
        "lone-surrogate-key",
        "single-quotes",
        "trailing-comma",
        "control-character",
        "invalid-utf-8",
    ],
)
def test_template_rule_1_blockers(data: bytes, message: str) -> None:
    with pytest.raises(JsonBlocked, match=message):
        parse_strict(data)


def test_non_finite_tokens_are_numbers_and_recorded() -> None:
    parsed = parse_strict(b'{"a": NaN, "b": [Infinity, -Infinity, 1.5], "c": "NaN"}')
    assert parsed.non_finite_tokens is True
    assert parsed.non_finite_pointers == ("/a", "/b/0", "/b/1")
    assert parse_strict(b'{"a": 1.0, "s": "Infinity"}').non_finite_tokens is False


def test_a_valid_pair_of_surrogates_is_accepted() -> None:
    assert parse_strict(b'{"a": "\\ud83d\\ude00"}').value == {"a": "\U0001f600"}


VALUE = parse_strict(
    b'{"result": {"h0": {"w2": 1.0}, "h1": {"w2": 2.0}}, "cells": [{"x": 1}, {"x": 2}], "empty": [], "a/b": {"~k": 3}}'
).value


def test_observed_pointers_list_every_leaf_and_container_with_the_root() -> None:
    assert observed_pointers(VALUE) == (
        "",
        "/result",
        "/result/h0",
        "/result/h0/w2",
        "/result/h1",
        "/result/h1/w2",
        "/cells",
        "/cells/0",
        "/cells/0/x",
        "/cells/1",
        "/cells/1/x",
        "/empty",
        "/a~1b",
        "/a~1b/~0k",
    )


def test_deep_nesting_is_walked_without_a_recursion_error() -> None:
    """PR #420 review: the walk is iterative, so nesting past Python's frame limit cannot escape as RecursionError."""
    depth = 5000
    value: list = []
    for _ in range(depth):
        value = [value]
    pointers = observed_pointers(value)
    assert len(pointers) == depth + 1 and pointers[-1] == "/0" * depth
    data = b"[" * (depth + 1) + b"]" * (depth + 1)  # the same depth + 1 nested lists as ``value``
    try:
        parsed = parse_strict(data)
    except JsonBlocked:
        return  # the C scanner's own depth limit is a clean refusal too
    assert len(observed_pointers(parsed.value)) == depth + 1


def test_patterns_expand_against_the_observed_value() -> None:
    assert expand("/cells/[*]/x", VALUE) == ("/cells/0/x", "/cells/1/x")
    assert expand("/empty/[*]", VALUE) == ()
    assert expand("/a~1b/~0k", VALUE) == ("/a~1b/~0k",)
    with pytest.raises(JsonBlocked, match=r"table pointer '/missing/\[\*\]' is absent from the observed bytes"):
        expand("/missing/[*]", VALUE)
    with pytest.raises(JsonBlocked, match=r"\[\*\] does not name an array"):
        expand("/result/[*]", VALUE)


FAMILIES = [
    {"name": "meta", "pointers": ["", "/result", "/result/h0", "/result/h1", "/cells", "/cells/[*]", "/empty"]},
    {"name": "h0_w2", "pointers": ["/result/h0/w2"]},
    {"name": "h1_w2", "pointers": ["/result/h1/w2"]},
    {"name": "cells", "pointers": ["/cells/[*]/x", "/a~1b", "/a~1b/~0k"]},
]


def test_a_complete_table_assigns_every_pointer_once() -> None:
    owner = assign(FAMILIES, [], VALUE)
    assert set(owner) == set(observed_pointers(VALUE))
    assert owner["/result/h1/w2"] == "h1_w2" and owner["/result/h1"] == "meta"


@pytest.mark.parametrize(
    ("families", "unassigned", "message"),
    [
        (FAMILIES, ["/loose"], "the membership table has unassigned pointers"),
        (FAMILIES[:-1], [], "observed pointers no family covers"),
        ([*FAMILIES, {"name": "extra", "pointers": ["/result/h0/w2"]}], [], "is in two families"),
        ([*FAMILIES, {"name": "extra", "pointers": ["/result/h2"]}], [], "is absent from the observed bytes"),
    ],
    ids=["unassigned", "uncovered", "two-families", "absent-table-pointer"],
)
def test_template_rules_2_to_5_blockers(families, unassigned, message: str) -> None:
    with pytest.raises(JsonBlocked, match=message):
        assign(families, unassigned, VALUE)
