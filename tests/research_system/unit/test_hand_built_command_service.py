"""Controls for tests.research_system.factories.hand_built_command_service.

Obs 2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red: two tests built CommandService with
object.__new__ and copied __init__'s defaults by hand, and #420 broke both by adding binding_check. The helper takes
the defaults from a real instance, and the census below keeps new hand copies out of the suite.
"""

from __future__ import annotations

import re
from pathlib import Path

from research_system.command.service import CommandService
from tests.research_system.factories import REPO_ROOT, hand_built_command_service

_HAND_COPY = re.compile(r"object\.__new__\(\s*CommandService\s*\)|CommandService\.__new__\(")
_ALLOWED = {Path("tests/research_system/factories.py")}


def _hand_copies(sources: dict[Path, str]) -> list[str]:
    """Return ``path:line`` for every hand-built CommandService outside the shared factory."""
    found: list[str] = []
    for path, text in sorted(sources.items()):
        if path in _ALLOWED:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if _HAND_COPY.search(line):
                found.append(f"{path.as_posix()}:{number}")
    return found


def test_hand_built_service_carries_every_init_attribute(tmp_path: Path) -> None:
    real = CommandService(tmp_path / "real", None, None, None, None)  # type: ignore[arg-type]
    built = hand_built_command_service(tmp_path / "built")

    assert set(vars(built)) == set(vars(real))
    assert built.binding_check is None
    assert built.control_root == tmp_path / "built"


def test_an_attribute_added_to_init_reaches_the_hand_built_service(tmp_path: Path, monkeypatch) -> None:
    """Negative control: the failure #420 caused, an attribute added to __init__ only, cannot recur."""
    original = CommandService.__init__

    def init_with_a_new_default(self, *args, **kwargs) -> None:
        original(self, *args, **kwargs)
        self.added_after_the_copy = "default"

    monkeypatch.setattr(CommandService, "__init__", init_with_a_new_default)

    assert hand_built_command_service(tmp_path).added_after_the_copy == "default"


def test_attributes_override_the_defaults(tmp_path: Path) -> None:
    def marker() -> None:
        return None

    built = hand_built_command_service(tmp_path, binding_check=marker, release_lock_timeout_seconds=1.0)

    assert built.binding_check is marker
    assert built.release_lock_timeout_seconds == 1.0


def test_no_test_hand_builds_a_command_service_outside_the_factory() -> None:
    sources = {
        path.relative_to(REPO_ROOT): path.read_text(encoding="utf-8") for path in (REPO_ROOT / "tests").rglob("*.py")
    }

    assert _hand_copies(sources) == []


def test_the_census_reports_a_hand_copy() -> None:
    """Negative control for the census: a hand copy outside the factory is reported with its line."""
    hand_copy = "service = object.__new__(" + "CommandService)\n"  # split so the census does not read this file
    sources = {
        Path("tests/research_system/unit/test_example.py"): "x = 1\n" + hand_copy,
        Path("tests/research_system/factories.py"): hand_copy,
    }

    assert _hand_copies(sources) == ["tests/research_system/unit/test_example.py:2"]
