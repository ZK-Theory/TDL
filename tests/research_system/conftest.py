# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (outcome, open items)
# Purpose: Wire the foundation sentinel into every research_system test (see foundation_sentinel.py).
"""Autouse wiring for the research_system foundation sentinel."""

from __future__ import annotations

import pytest

from tests.research_system import foundation_sentinel


@pytest.fixture(autouse=True)
def _no_unpinned_canonical_foundation(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    foundation_sentinel.install(request, monkeypatch)
