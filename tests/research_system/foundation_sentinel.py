# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (outcome, open items)
# Purpose: Refuse, by default, any research_system test that reads the committed canonical foundation, so a test
# can no longer pass or fail because of the machine it runs on.
"""Foundation isolation for the research_system tests.

Obs 2026-10-17-cli-tests-read-the-committed-foundation-unpinned: tests that built their own store still let
``ControlBinding.load`` read ``.research-system/config/foundation.yaml``, which names the operator's live roots. The
asserted refusal then depended on the host: "path is unavailable" on the hosted runner, "code roots do not include"
in a linked worktree. Two such tests passed for months only because the live store failed to load (obs
2026-10-17-tests-passed-on-the-live-stores-breakage). ``factories.approved_foundation`` existed for exactly this,
but nothing made a test use it.

Every test now starts with ``canonical_foundation_path`` replaced by a sentinel in each module that binds the name.
A test that pins its own foundation (``approved_foundation``, or its own ``monkeypatch.setattr``) replaces the
sentinel and proceeds. A test that deliberately reads the operator's live store is marked ``live_store`` and keeps
the real function. The sentinel raises a ``BaseException`` subclass: the CLI turns ordinary errors into exit codes,
so an ``Exception`` would let a test asserting ``== 1`` pass silently, which is the failure this guard exists to stop.
"""

from __future__ import annotations

import importlib

import pytest

# Every module that binds the name: a ``from research_system.config import canonical_foundation_path`` keeps its
# own reference, so each binding is replaced. A new binding the list misses is caught by
# test_every_binding_of_canonical_foundation_path_is_guarded.
FOUNDATION_BINDINGS = ("research_system.config", "research_system.cli", "research_system.evidence.wp64_real_a8")
SENTINEL_MESSAGE = "this test read the committed canonical foundation without pinning its own"


class UnpinnedCanonicalFoundation(BaseException):  # noqa: N818 - BaseException on purpose, see the module docstring
    """Raised when a research_system test reaches the committed foundation without pinning one."""


def _sentinel():  # noqa: ANN202 - stands in for ``canonical_foundation_path() -> Path``
    raise UnpinnedCanonicalFoundation(
        f"{SENTINEL_MESSAGE}: pin one with tests.research_system.factories.approved_foundation, or mark the test "
        "live_store if it must read the operator's live store (obs 2026-10-17-cli-tests-read-the-committed-"
        "foundation-unpinned)"
    )


def install(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace every binding with the sentinel, unless the test is marked ``live_store``.

    Wired as an autouse fixture by ``tests/research_system/conftest.py``.
    """
    if request.node.get_closest_marker("live_store"):
        return
    for name in FOUNDATION_BINDINGS:
        monkeypatch.setattr(importlib.import_module(name), "canonical_foundation_path", _sentinel)
