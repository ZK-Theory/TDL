"""Liveness controls for tools/invoke_checked.ps1 (obs 142).

Why: PowerShell reports only the LAST native process's exit code, so
`commandA; commandB` where A fails and B succeeds returns B's (zero) exit
code — a later success silently erases an earlier failure. A validation
bundle chained this way can report green while one of its checks actually
failed. invoke_checked.ps1 checks the exit code after each step and stops at
the first failure, so its own exit code always reflects the earliest failing
step, not the last command run.

Invocation note: tests call the runner via `-File` on a small generated
wrapper script, not `-Command "& '...ps1' ..."`. Windows PowerShell 5.1's
`-Command` does not propagate an inner script's `exit N` as the outer
process's exit code when the script is invoked via `&` from within the
command string — it collapses any failing exit to a generic 1. That is still
nonzero (so it would not resurrect the original silent-success defect), but
it loses which step failed and its exact code, so `-File` is the correct
invocation for both real use and for these fidelity-checking tests.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "tools" / "invoke_checked.ps1"


def _powershell() -> str:
    discovered = shutil.which("powershell.exe") or shutil.which("powershell")
    if discovered is None:
        pytest.skip("powershell.exe is not available")
    return discovered


def _run(commands_ps: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    wrapper = tmp_path / "wrapper.ps1"
    wrapper.write_text(
        f"& '{RUNNER}' -Commands @({commands_ps})\nexit $LASTEXITCODE\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [_powershell(), "-NoProfile", "-NonInteractive", "-File", str(wrapper)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_first_failure_is_not_masked_by_a_later_success(tmp_path: Path) -> None:
    """The exact obs 142 defect: a later success must not erase an earlier failure."""
    result = _run('{ cmd /c "exit 7" }, { cmd /c "exit 0" }', tmp_path)
    assert result.returncode == 7, result.stderr


def test_all_commands_succeeding_exits_zero(tmp_path: Path) -> None:
    result = _run('{ cmd /c "exit 0" }, { cmd /c "exit 0" }', tmp_path)
    assert result.returncode == 0, result.stderr


def test_a_later_step_failure_is_still_caught(tmp_path: Path) -> None:
    result = _run('{ cmd /c "exit 0" }, { cmd /c "exit 3" }', tmp_path)
    assert result.returncode == 3, result.stderr
