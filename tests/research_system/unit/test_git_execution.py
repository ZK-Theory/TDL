"""Controls for ``run_git`` naming the cause of its fail-closed refusal.

``run_git`` refuses through three separate paths (the executable is missing, the
launch raises ``OSError``, the call times out) and used to raise one message for
all of them.  On 2026-09-26 eleven certification groups failed in the same second
with that one message and nothing could say whether it was a timeout or an OS
error (observation 2026-09-26-git-unavailable-error-hides-its-cause).  Each
refusal now appends its own cause to the caller's ``unavailable_message``.

Each branch has its own control, and each control also asserts that the other two
causes are absent, so an implementation that merges any two causes fails.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from research_system import git_execution
from research_system.discovery import spec_source_git
from research_system.errors import ConfigurationError
from research_system.git_execution import run_git

CALLER_MESSAGE = "caller-specific Git inspection is unavailable"

_NOT_FOUND = "executable not found"
_OS_ERROR = "OSError"
_TIMED_OUT = "timed out after"
_ALL_CAUSES = (_NOT_FOUND, _OS_ERROR, _TIMED_OUT)


def _fake_git(tmp_path: Path) -> Path:
    """Return a physical file that passes the executable check without being Git."""

    fake = tmp_path / "fake-git"
    fake.write_bytes(b"")
    return fake


def _refusal(tmp_path: Path, **keywords: object) -> ConfigurationError:
    with pytest.raises(ConfigurationError) as raised:
        run_git(tmp_path, "status", unavailable_message=CALLER_MESSAGE, **keywords)
    return raised.value


def _assert_names_only(error: ConfigurationError, cause: str) -> None:
    message = str(error)
    assert message.startswith(CALLER_MESSAGE + " (") and message.endswith(")"), message
    assert cause in message, message
    assert not any(other in message for other in _ALL_CAUSES if other != cause), message


def test_missing_executable_names_its_cause(monkeypatch, tmp_path):
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", None)

    error = _refusal(tmp_path)

    _assert_names_only(error, _NOT_FOUND)
    assert error.__cause__ is None


def test_launch_oserror_names_its_cause(monkeypatch, tmp_path):
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", _fake_git(tmp_path))
    failure = OSError("simulated launch failure")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(git_execution.subprocess, "run", fail)

    error = _refusal(tmp_path)

    _assert_names_only(error, _OS_ERROR)
    assert "simulated launch failure" in str(error)
    assert error.__cause__ is failure


@pytest.mark.parametrize("executable", ["directory", "absent"])
def test_unusable_executable_is_an_oserror_not_a_missing_one(monkeypatch, tmp_path, executable):
    # ``None`` means Git was never found on PATH; a path that exists as a directory or
    # has vanished is a different refusal and must say so.
    path = tmp_path if executable == "directory" else tmp_path / "vanished-git"
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", path)

    error = _refusal(tmp_path)

    _assert_names_only(error, _OS_ERROR)
    assert isinstance(error.__cause__, OSError)


@pytest.mark.parametrize(("timeout", "rendered"), [(10, "10s"), (60, "60s"), (0.5, "0.5s")])
def test_timeout_names_its_cause(monkeypatch, tmp_path, timeout, rendered):
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", _fake_git(tmp_path))
    failure = subprocess.TimeoutExpired("git", timeout)

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(git_execution.subprocess, "run", fail)

    error = _refusal(tmp_path, timeout=timeout)

    _assert_names_only(error, _TIMED_OUT)
    assert f"{_TIMED_OUT} {rendered}" in str(error)
    assert error.__cause__ is failure


def test_default_timeout_is_named(monkeypatch, tmp_path):
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", _fake_git(tmp_path))

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", kwargs["timeout"])

    monkeypatch.setattr(git_execution.subprocess, "run", fail)

    assert f"{_TIMED_OUT} 10s" in str(_refusal(tmp_path))


def test_long_or_multiline_oserror_text_stays_short_and_on_one_line(monkeypatch, tmp_path):
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", _fake_git(tmp_path))

    def fail(*args, **kwargs):
        raise OSError("first line\nsecond line " + "x" * 500)

    monkeypatch.setattr(git_execution.subprocess, "run", fail)

    message = str(_refusal(tmp_path))

    assert "\n" not in message
    assert "first line second line" in message
    assert len(message) < len(CALLER_MESSAGE) + 200


def test_default_caller_message_is_the_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", None)

    with pytest.raises(ConfigurationError) as raised:
        run_git(tmp_path, "status")

    assert str(raised.value).startswith("Git validation is unavailable")


@pytest.mark.parametrize(
    ("failure", "failure_kind"),
    [
        (subprocess.TimeoutExpired("git", 60), "timeout"),
        (OSError("simulated launch failure"), "transport"),
    ],
)
def test_source_resolution_still_classifies_the_chained_cause(monkeypatch, tmp_path, failure, failure_kind):
    """The consumer that reads ``__cause__`` is unaffected by the longer message."""

    monkeypatch.setattr(git_execution, "_GIT_EXECUTABLE", _fake_git(tmp_path))

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(git_execution.subprocess, "run", fail)

    result, raw = spec_source_git.resolve_source(str(tmp_path), "main")

    assert raw is None
    assert result["status"] == "unavailable"
    assert result["failure_kind"] == failure_kind
