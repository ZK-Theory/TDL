"""The project supports Windows only, so no CI job may run on Linux.

Decided by Stephen on 2026-09-11 (PR #278). These controls keep that decision
from eroding one workflow at a time, and guard the two ways a move to Windows
runners fails silently: a bash script left under the Windows default shell, and
a platform gate still pointed at a job that no longer exists or runs elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
ADMISSION_CONFIG = REPO_ROOT / ".github" / "merge-admission.yml"

# Syntax that only a POSIX shell accepts. Windows runners default to pwsh.
BASH_MARKERS = ("set -euo pipefail", "$(", "source ", "printf ", "git init", "[ -")


def _load(path: Path) -> dict[str, Any]:
    """Load a workflow without YAML 1.1 coercing ``on`` or version strings."""
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(document, dict), f"{path.name} is not a mapping"
    return document


def _shell(block: object) -> str | None:
    """Return ``defaults.run.shell`` from a workflow or job mapping, if declared."""
    if not isinstance(block, dict):
        return None
    run = block.get("defaults", {}).get("run", {})
    return run.get("shell") if isinstance(run, dict) else None


def test_workflow_discovery_is_not_vacuous() -> None:
    """A glob that matched nothing would make every control below pass."""
    names = {path.name for path in WORKFLOWS}
    assert {"ci.yml", "merge-admission.yml", "ars-artefact-currency.yml"} <= names


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_no_job_runs_on_linux(path: Path) -> None:
    """Every job's runner label is a Windows label."""
    for name, job in _load(path)["jobs"].items():
        runs_on = job.get("runs-on")
        labels = runs_on if isinstance(runs_on, list) else [runs_on]
        assert labels and all(
            isinstance(label, str) and label.startswith("windows") for label in labels
        ), f"{path.name}:{name} runs on {runs_on!r}; the project supports Windows only"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_bash_scripts_declare_bash(path: Path) -> None:
    """A POSIX script under pwsh fails at runtime, not at review."""
    document = _load(path)
    workflow_shell = _shell(document)
    for name, job in document["jobs"].items():
        job_shell = _shell(job) or workflow_shell
        for step in job.get("steps", []):
            script = step.get("run")
            if not isinstance(script, str) or not any(marker in script for marker in BASH_MARKERS):
                continue
            shell = step.get("shell", job_shell)
            assert shell == "bash", (
                f"{path.name}:{name} step {step.get('name')!r} uses bash syntax but runs under "
                f"{shell or 'the Windows default shell (pwsh)'}"
            )


def test_removed_linux_lanes_stay_removed() -> None:
    """The two Linux-only lanes removed on 2026-09-11 are not quietly restored."""
    jobs = _load(WORKFLOW_DIR / "ci.yml")["jobs"]
    assert "test" not in jobs
    assert "petls-backend" not in jobs


def test_platform_gate_reads_a_windows_job_from_its_trusted_workflow() -> None:
    """The admission gate's platform job exists, runs on Windows, and lives where the gate trusts it."""
    section = yaml.safe_load(ADMISSION_CONFIG.read_text(encoding="utf-8"))["platform_order"]
    workflow_path = REPO_ROOT / section["workflow_path"]
    assert workflow_path.is_file(), f"platform_order.workflow_path {section['workflow_path']} does not exist"
    jobs = _load(workflow_path)["jobs"]
    assert section["check_run"] in jobs, f"{section['check_run']} is not a job in {section['workflow_path']}"
    assert jobs[section["check_run"]]["runs-on"].startswith("windows")
    assert "continue-on-error" not in jobs[section["check_run"]], "advisory evidence cannot gate admission"
