"""Direct controls for the independent C-1 workflow-state watchdog."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check_workflow_liveness.py"
TARGET = ".github/workflows/ars-artefact-currency.yml"


def _run(payload: dict[str, object], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    response = tmp_path / "workflows.json"
    response.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--workflows-json", str(response), "--target-path", TARGET],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_active_target_workflow_passes(tmp_path: Path) -> None:
    result = _run({"workflows": [{"path": TARGET, "state": "active"}]}, tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"active: {TARGET}" in result.stdout


def test_manually_disabled_target_workflow_fails_closed(tmp_path: Path) -> None:
    result = _run({"workflows": [{"path": TARGET, "state": "disabled_manually"}]}, tmp_path)

    assert result.returncode == 1
    assert "disabled_manually" in result.stderr
