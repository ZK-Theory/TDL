# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (outcome, open items)
# Purpose: Controls for the foundation sentinel in tests/research_system/conftest.py.
"""Controls for the research_system foundation sentinel.

Obs 2026-10-17-cli-tests-read-the-committed-foundation-unpinned.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from research_system import config
from research_system.cli import main
from tests.research_system.foundation_sentinel import FOUNDATION_BINDINGS, SENTINEL_MESSAGE, UnpinnedCanonicalFoundation

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_an_unpinned_cli_call_fails_with_the_sentinel_message(tmp_path: Path) -> None:
    """The observation's negative control: ``main([...])`` reaching the committed foundation must not pass."""
    config_path = tmp_path / "control-binding.json"
    config_path.write_text("{}", encoding="utf-8")
    with pytest.raises(UnpinnedCanonicalFoundation, match=SENTINEL_MESSAGE):
        main(
            [
                "eval",
                "publish-release",
                "--config",
                str(config_path),
                "--actor-id",
                "act_01978abc-1002-7000-8000-000000001002",
                "--authority-grant-id",
                "grt_01978abc-1003-7000-8000-000000001003",
                "--evaluation-runs",
                str(tmp_path / "runs.json"),
                "--output",
                str(tmp_path / "receipt.json"),
            ]
        )


def test_the_sentinel_is_not_an_exception_a_cli_could_swallow() -> None:
    assert not issubclass(UnpinnedCanonicalFoundation, Exception)


def test_a_test_that_pins_its_own_foundation_proceeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pinned = tmp_path / "foundation.yaml"
    monkeypatch.setattr(config, "canonical_foundation_path", lambda: pinned)
    assert config.canonical_foundation_path() == pinned


@pytest.mark.live_store
def test_a_live_store_test_keeps_the_real_foundation() -> None:
    assert config.canonical_foundation_path() == REPO_ROOT / ".research-system" / "config" / "foundation.yaml"


def test_every_binding_of_canonical_foundation_path_is_guarded() -> None:
    """A new ``from research_system.config import canonical_foundation_path`` must join FOUNDATION_BINDINGS."""
    bound = {"research_system.config"}
    for path in (REPO_ROOT / "research_system").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(a.name == "canonical_foundation_path" for a in node.names):
                bound.add(".".join(path.relative_to(REPO_ROOT).with_suffix("").parts))
    assert bound == set(FOUNDATION_BINDINGS)
