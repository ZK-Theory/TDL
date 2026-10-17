# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (follow-up, 2026-10-17)
# Purpose: Give every tests/tools control the hosted runner's environment, so a workstation-only variable cannot
# hide a defect that CI will see.
"""Shared fixtures for the tools controls.

Obs 2026-10-16-workstation-env-masked-a-ci-only-runner-defect: the dev shell exports
``PYTHONDONTWRITEBYTECODE=1``, the hosted runner does not. A certify_packet control passed on every workstation
run and failed on every hosted run, because the runner wrote ``__pycache__`` into the tree it certifies and only
the workstation's variable stopped it. Controls that spawn tools now run without such variables everywhere.
"""

from __future__ import annotations

import pytest

# Variables a workstation sets and the hosted runner does not, which change what a spawned tool writes or reads.
WORKSTATION_ONLY = ("PYTHONDONTWRITEBYTECODE",)


@pytest.fixture(autouse=True)
def _hosted_runner_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in WORKSTATION_ONLY:
        monkeypatch.delenv(name, raising=False)
