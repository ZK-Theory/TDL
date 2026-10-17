# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (follow-up, 2026-10-17)
# Purpose: Prove the tests/tools conftest strips the workstation-only variables before a control spawns a tool.
"""Controls for ``tests/tools/conftest.py``.

Obs 2026-10-16-workstation-env-masked-a-ci-only-runner-defect.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.tools.conftest import WORKSTATION_ONLY


def test_no_workstation_only_variable_reaches_a_control() -> None:
    assert not [name for name in WORKSTATION_ONLY if name in os.environ]


def test_a_spawned_python_writes_bytecode_as_it_does_on_the_hosted_runner(tmp_path: Path) -> None:
    """Negative control: with the variable stripped, an import writes __pycache__, which the runner must not do."""
    (tmp_path / "probe_module.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run([sys.executable, "-c", "import probe_module"], cwd=tmp_path, check=True)
    assert list((tmp_path / "__pycache__").glob("probe_module*.pyc")), "the spawned interpreter wrote no bytecode"
