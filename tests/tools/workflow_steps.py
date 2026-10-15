# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group E)
# Purpose: Run CI glue the way the runner runs it. One Git Bash resolver for every hook and workflow control,
# and a harness that executes a workflow step's real script under GitHub's bash flags with tools stubbed.
"""Shared helpers for controls that execute shell: hooks and GitHub workflow steps.

Obs 2026-10-06-workflow-step-tested-by-string-not-by-running: the research-system lane's controls asserted that
strings were present, while the step itself had two real bugs (errexit ended the step before the baseline ran;
``mapfile -t`` kept CRLF). Only running the step under GitHub's flags showed them. The same ``_bash()`` resolver
had been copied into ten test files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

# GitHub runs ``shell: bash`` steps as ``bash --noprofile --norc -eo pipefail {0}``.
GITHUB_BASH_FLAGS = ("--noprofile", "--norc", "-eo", "pipefail")


def git_bash(context: str) -> str:
    """Resolve Git's bash rather than Windows' WSL launcher stub, failing (never skipping) if none exists.

    ``shutil.which("bash")`` finds ``C:\\Windows\\System32\\bash.exe`` first on Windows, the WSL shim, which
    exits nonzero when no distribution is installed. ``context`` says what cannot run without it, for example
    "the notation guard's controls cannot run".
    """
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail(f"no usable bash: {context}, and must not silently skip")
    return found


def step_script(workflow: dict[str, Any], job: str, step_name: str) -> str:
    """Return the ``run:`` script of the named step, failing if the step is absent or not a script."""
    steps = workflow["jobs"][job]["steps"]
    matches = [step for step in steps if step.get("name") == step_name]
    assert len(matches) == 1, f"{job} has {len(matches)} step(s) named {step_name!r}"
    script = matches[0].get("run")
    assert isinstance(script, str) and script.strip(), f"{job}/{step_name} has no run script"
    return script


def run_step(
    workflow: dict[str, Any],
    job: str,
    step_name: str,
    cwd: Path,
    *,
    replace: dict[str, str] | None = None,
    prelude: str = "",
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a workflow step's real script under GitHub's bash flags.

    ``replace`` swaps exact substrings of the script (each must occur exactly once, so a renamed command
    cannot leave the stub unused); ``prelude`` defines stub functions ahead of the script.
    """
    script = step_script(workflow, job, step_name)
    for old, new in (replace or {}).items():
        assert script.count(old) == 1, f"{old!r} occurs {script.count(old)} times in {job}/{step_name}"
        script = script.replace(old, new)
    (cwd / "step.sh").write_bytes((prelude + script).encode("utf-8"))
    return subprocess.run(
        [git_bash(f"the {job}/{step_name} step control cannot run"), *GITHUB_BASH_FLAGS, "step.sh"],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )
