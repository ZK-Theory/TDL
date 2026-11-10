# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §8.1; owner point I)
# Purpose: run the segmentation contract's vectors against both implementations, and compare them differentially.
"""The runtime segmenter against the reference implementation (WP9.3 note §8.1; P-081 item 9).

- **The vectors.** Every test in ``tests/tools/test_w9_segmentation.py`` (the contract's vectors, contract §7) runs
  twice: against ``tools/w9_segmentation.py`` and against ``research_system.legacy.segmentation``. The vectors file is
  not edited; each test function is called with its module's ``seg`` replaced by the implementation under test.
- **The differential test.** Inputs are generated from a fixed seed over the line forms the contract distinguishes
  (headings of every level, dates in every form, stage and other tables, bullets and continuations, frontmatter, the
  footer, rule and blank lines, a BOM, CRLF, a missing final terminator and invalid UTF-8). For every input and
  selector both implementations must return identical output, or refuse alike.
"""

from __future__ import annotations

import inspect
import itertools
import random
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from research_system.legacy import segmentation as runtime
from tests.tools import test_w9_segmentation as vectors

REFERENCE = vectors.seg
IMPLEMENTATIONS = {"reference": REFERENCE, "runtime": runtime}
# The differential seed and case count, recorded here (CONVENTIONS: seeds are specified and recorded).
DIFFERENTIAL_SEED = 20261109
DIFFERENTIAL_CASES = 1500


def _vector_cases() -> Iterator[tuple[str, Callable[..., None], dict[str, Any]]]:
    for name, function in inspect.getmembers(vectors, inspect.isfunction):
        if not name.startswith("test_") or function.__module__ != vectors.__name__:
            continue
        marks = [mark for mark in getattr(function, "pytestmark", []) if mark.name == "parametrize"]
        if not marks:
            yield name, function, {}
            continue
        axes = []
        for mark in marks:
            names = (
                [part.strip() for part in mark.args[0].split(",")] if isinstance(mark.args[0], str) else mark.args[0]
            )
            values = mark.args[1]
            ids = mark.kwargs.get("ids") or [str(index) for index in range(len(values))]
            axes.append(
                [
                    (identifier, dict(zip(names, value if len(names) > 1 else (value,), strict=True)))
                    for identifier, value in zip(ids, values, strict=True)
                ]
            )
        for combination in itertools.product(*axes):
            kwargs: dict[str, Any] = {}
            for _, values in combination:
                kwargs.update(values)
            yield f"{name}[{'-'.join(identifier for identifier, _ in combination)}]", function, kwargs


VECTOR_CASES = list(_vector_cases())


def test_every_vector_is_collected() -> None:
    names = {name.split("[")[0] for name, _, _ in VECTOR_CASES}
    assert names == {name for name in dir(vectors) if name.startswith("test_")}
    assert len(VECTOR_CASES) >= 35


@pytest.mark.parametrize("implementation", sorted(IMPLEMENTATIONS))
@pytest.mark.parametrize(("name", "function", "kwargs"), VECTOR_CASES, ids=[case[0] for case in VECTOR_CASES])
def test_contract_vector(
    monkeypatch: pytest.MonkeyPatch, implementation: str, name: str, function: Callable[..., None], kwargs: dict
) -> None:
    monkeypatch.setattr(vectors, "seg", IMPLEMENTATIONS[implementation])
    function(**kwargs)


# --- The differential test -------------------------------------------------------------------------------------------

_LINE_FORMS = [
    b"",
    b"   ",
    b"\t",
    b"---",
    b"---  ",
    b"# Title",
    b"## a",
    b"## a",
    b"## b ##",
    b"### sub",
    b"#### deep",
    b"####### seven",
    b" ## leading",
    b"##nospace",
    b"## 2026-01-02 entry",
    b"### 2026-03 month",
    b"### 2026-06-03b suffixed",
    b"### 2026-06-01/02 range",
    b"### ~2026-05-01 approx",
    b"### 2026-06-05(later)",
    b"### 2026-13x bad",
    b"## 2026 not a date",
    b"### Results",
    b"## Task Tracking",
    b"## Working Notes",
    b"## Notes",
    b"| Task | Status |",
    b"|------|--------|",
    b"| :--- | ---: |",
    b"| 1.37 | done |",
    b"| 1.2g | open |",
    b"| 1.15a-redo | x |",
    b"| bad\\|cell | y |",
    b"| Thread | Note |",
    b"| \xff | z |",
    b"- **2026-10-21: a**",
    b"- undated note",
    b"* star bullet",
    b"  continuation",
    b"\tcontinuation",
    b"paragraph text",
    b"*Last updated: 2026-07-16*",
    b"title: x",
    b"## \xff bad",
    b"```",
    b"===",
]
_SELECTOR_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("heading_section", {"level": 2}),
    ("heading_section", {"level": 3}),
    ("computational_log_entry", {}),
    ("tracker_task_row", {}),
    ("working_note_entry", {}),
    ("log_frontmatter", {}),
    ("conventions_unit", {}),
]


def _generated(rng: random.Random) -> bytes:
    lines = [rng.choice(_LINE_FORMS) for _ in range(rng.randint(0, 24))]
    if rng.random() < 0.3:
        lines.insert(0, b"---")
        lines.insert(rng.randint(1, len(lines)), b"---")
    terminator = rng.choice([b"\n", b"\r\n", None])
    if terminator is None:
        data = b"".join(line + rng.choice([b"\n", b"\r\n"]) for line in lines)
    else:
        data = b"".join(line + terminator for line in lines)
    if lines and rng.random() < 0.2:
        data = data.rstrip(b"\r\n")
    if rng.random() < 0.1:
        data = b"\xef\xbb\xbf" + data
    return data


def _outcome(module: Any, data: bytes, selector: str, kwargs: dict[str, Any]) -> tuple[str, Any]:
    try:
        return "rows", module.segment(data, selector, **kwargs)
    except ValueError as exc:  # the reference tool's refusal
        return "refused", str(exc)


def test_runtime_segmenter_equals_the_reference_on_generated_inputs() -> None:
    rng = random.Random(DIFFERENTIAL_SEED)
    compared = refused = 0
    for _ in range(DIFFERENTIAL_CASES):
        data = _generated(rng)
        for selector, kwargs in _SELECTOR_CALLS:
            line_count = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
            if selector == "heading_section" and line_count and rng.random() < 0.3:
                first = rng.randint(1, line_count)
                kwargs = {**kwargs, "region": (first, rng.randint(first, line_count))}
                if rng.random() < 0.5:
                    kwargs["structural"] = [(first, first)]
            reference = _outcome(REFERENCE, data, selector, kwargs)
            try:
                observed: tuple[str, Any] = ("rows", runtime.segment(data, selector, **kwargs))
            except runtime.SegmentationError as exc:
                observed = ("refused", str(exc))
            assert observed[0] == reference[0], (data, selector, kwargs)
            if observed[0] == "rows":
                assert observed[1] == reference[1], (data, selector, kwargs)
                compared += 1
            else:
                refused += 1
    # The generator reaches both outcomes, so the comparison is not vacuous.
    assert compared > DIFFERENTIAL_CASES * 4 and refused > 100


def test_the_runtime_segmenter_refuses_with_its_own_error() -> None:
    for call in (
        lambda: runtime.segment(b"x\n", "nonexistent"),
        lambda: runtime.segment(b"x\n", "heading_section"),
        lambda: runtime.segment(b"x\n", "tracker_task_row"),
        lambda: runtime.segment(b"x\n", "heading_section", level=2, structural=[(1, 3)]),
        lambda: runtime.segment("text", "log_frontmatter"),  # type: ignore[arg-type]
    ):
        with pytest.raises(runtime.SegmentationError):
            call()


@pytest.mark.parametrize("selector", ["heading_section", "computational_log_entry"])
@pytest.mark.parametrize("region", [(1, 4), (0, 2), (3, 2)])
def test_a_covered_region_outside_the_file_is_refused_not_indexed(selector: str, region: tuple[int, int]) -> None:
    """PR #420 review: a declared region past the file refuses cleanly; the reference tool would index past it."""
    with pytest.raises(runtime.SegmentationError, match=rf"covered region {region[0]}:{region[1]} is outside the file"):
        runtime.segment(b"## a\nb\nc\n", selector, level=2, region=region)


def test_the_reference_tool_is_untouched_and_not_imported_by_the_runtime() -> None:
    """Owner point I: the reference stays non-runtime, accepted at blob 43e1454d (P-067 item 2, P-068)."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    blob = subprocess.run(
        ["git", "-C", str(root), "hash-object", "tools/w9_segmentation.py"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert blob.startswith("43e1454d")
    import ast

    for path in (root / "research_system").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert not any("w9_segmentation" in name for name in names), path
