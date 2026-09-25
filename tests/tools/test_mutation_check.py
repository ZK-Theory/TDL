# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Controls for the committed mutation-check harness that replaces per-session scratch
# scripts, including the stale-bytecode failure that corrupted a real run.
"""Controls for ``tools/mutation_check.py``.

Obs 2026-09-11-mutation-harness-stale-bytecode: a same-size mutant written and restored within
one second left CPython executing cached bytecode, so the restored baseline failed on the
wrong grounds and a mutant could be reported CAUGHT by the previous mutant's code. These tests
drive the tool as a subprocess over a throwaway package.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "mutation_check.py"


@pytest.fixture
def toy(tmp_path: Path) -> Path:
    root = tmp_path / "toy"
    root.mkdir()
    (root / "calc.py").write_text(
        "def gt(a, b):\n    return a > b\n\n\ndef add(a, b):\n    return a + b\n", newline="\n"
    )
    (root / "test_calc.py").write_text(
        "from calc import add, gt\n\n\ndef test_gt():\n    assert gt(3, 2) is True\n    assert gt(2, 3) is False\n\n\n"
        "def test_add():\n    assert add(2, 3) == 5\n",
        newline="\n",
    )
    return root


def _run(root: Path, *mutants: tuple[str, str, str]) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(TOOL), "--target", "calc.py", "--cwd", str(root)]
    for name, old, new in mutants:
        args += ["--mutant", name, old, new]
    args += ["--", "test_calc.py"]
    return subprocess.run(args, capture_output=True, text=True, timeout=300)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_caught_mutant_passes_and_the_file_is_restored_byte_for_byte(toy: Path) -> None:
    before = _sha(toy / "calc.py")

    result = _run(toy, ("add-to-sub", "return a + b", "return a - b"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CAUGHT    add-to-sub" in result.stdout
    assert _sha(toy / "calc.py") == before


def test_a_surviving_mutant_fails_the_check(toy: Path) -> None:
    result = _run(toy, ("equivalent", "return a + b", "return b + a"))

    assert result.returncode == 1
    assert "SURVIVED  equivalent" in result.stdout


@pytest.mark.parametrize(
    ("old", "reason"),
    [("return a * b", "anchor not found"), ("return a", "anchor occurs 2 times")],
)
def test_a_missing_or_ambiguous_anchor_is_a_failure_not_a_skip(toy: Path, old: str, reason: str) -> None:
    result = _run(toy, ("bad-anchor", old, "return 0"))

    assert result.returncode == 1
    assert reason in result.stdout


def test_a_red_baseline_aborts_before_any_mutant(toy: Path) -> None:
    (toy / "test_calc.py").write_text("def test_red():\n    assert False\n", newline="\n")
    before = _sha(toy / "calc.py")

    result = _run(toy, ("add-to-sub", "return a + b", "return a - b"))

    assert result.returncode == 2
    assert "baseline is not green" in result.stderr
    assert _sha(toy / "calc.py") == before


def test_same_size_mutants_in_quick_succession_do_not_run_stale_bytecode(toy: Path) -> None:
    """The incident: `>` to `<` keeps the file size, so an mtime/size-keyed .pyc can be reused.

    Two same-size mutants back to back, then the restored baseline. With stale bytecode the
    baseline after restore goes red (it runs the last mutant) and the harness fails loudly.
    """
    before = _sha(toy / "calc.py")

    result = _run(toy, ("gt-to-lt", "return a > b", "return a < b"), ("swap", "return a > b", "return b > a"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CAUGHT    gt-to-lt" in result.stdout
    assert "CAUGHT    swap" in result.stdout
    assert "restored baseline green" in result.stdout
    assert _sha(toy / "calc.py") == before
    assert not list(toy.rglob("*.pyc")), "the harness must not leave bytecode that a later run could trust"


def test_a_stale_pyc_matching_the_sources_size_and_mtime_is_not_trusted(toy: Path) -> None:
    """The discriminating control: bytecode compiled from a same-size mutant, stamped with the
    original's mtime, is exactly what CPython reuses. `-B` alone still READS it, so the harness
    must delete it; otherwise the baseline runs mutant code and goes red for the wrong reason."""
    import importlib.util
    import os
    import py_compile

    source = toy / "calc.py"
    original = source.read_bytes()
    stamp = source.stat().st_mtime
    source.write_bytes(original.replace(b"return a > b", b"return a < b"))
    os.utime(source, (stamp, stamp))
    py_compile.compile(str(source), cfile=importlib.util.cache_from_source(str(source)), doraise=True)
    source.write_bytes(original)
    os.utime(source, (stamp, stamp))
    assert Path(importlib.util.cache_from_source(str(source))).exists(), "fixture must plant the stale bytecode"

    result = _run(toy, ("add-to-sub", "return a + b", "return a - b"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CAUGHT    add-to-sub" in result.stdout
