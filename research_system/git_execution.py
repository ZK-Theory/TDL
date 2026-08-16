"""Dependency-free, non-interactive Git execution for repository assurance.

The caller supplies every repository root and argument.  This module removes
ambient repository/configuration redirection and disables fsmonitor before Git
is allowed to inspect security-sensitive repository state.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from research_system.errors import ConfigurationError


_DISCOVERED_GIT_EXECUTABLE = shutil.which("git")
_GIT_EXECUTABLE = (
    Path(_DISCOVERED_GIT_EXECUTABLE).resolve(strict=False) if _DISCOVERED_GIT_EXECUTABLE is not None else None
)


_REPOSITORY_ENVIRONMENT = frozenset(
    {
        "git_alternate_object_directories",
        "git_ceiling_directories",
        "git_common_dir",
        "git_dir",
        "git_discovery_across_filesystem",
        "git_graft_file",
        "git_index_file",
        "git_namespace",
        "git_object_directory",
        "git_prefix",
        "git_quarantine_path",
        "git_replace_ref_base",
        "git_shallow_file",
        "git_work_tree",
    }
)

_PROCESS_AND_TRANSPORT_ENVIRONMENT = frozenset(
    {
        "git_askpass",
        "git_editor",
        "git_exec_path",
        "git_external_diff",
        "git_pager",
        "git_proxy_command",
        "git_sequence_editor",
        "git_ssh",
        "git_ssh_command",
        "ssh_askpass",
        "git_allow_protocol",
        "git_protocol_from_user",
    }
)


def scrubbed_git_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment without case-variant Git repository/config injection."""

    environment = dict(os.environ if source is None else source)
    for variable in tuple(environment):
        normalized = variable.casefold()
        if (
            normalized in _REPOSITORY_ENVIRONMENT
            or normalized in _PROCESS_AND_TRANSPORT_ENVIRONMENT
            or normalized == "git_config"
            or normalized.startswith("git_config_")
        ):
            environment.pop(variable)
    # Ignore repository-local as well as ambient system/global configuration.
    # Safety-critical callers must not inherit URL rewrites, credential helpers,
    # filters, or process hooks from the candidate they are inspecting.
    environment["GIT_CONFIG"] = os.devnull
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_SYSTEM"] = os.devnull
    # Validation must neither consult system configuration nor refresh an index.
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    # Never allow a validation probe to wait for credentials or a terminal.
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def run_git(
    repository_root: Path,
    *arguments: str,
    text: bool = True,
    input: str | bytes | None = None,
    timeout: int | float = 10,
    unavailable_message: str = "Git validation is unavailable",
) -> subprocess.CompletedProcess[Any]:
    """Run one fixed Git command with portable output and failure semantics."""

    if _GIT_EXECUTABLE is None:
        raise ConfigurationError(unavailable_message)
    try:
        if not _GIT_EXECUTABLE.resolve(strict=True).is_file():
            raise OSError("Git executable is not a physical file")
    except OSError as exc:
        error = ConfigurationError(unavailable_message)
        error.__cause__ = exc
        raise error
    try:
        return subprocess.run(  # nosec B603 B607 - fixed executable and argument vector
            [
                str(_GIT_EXECUTABLE),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                "-c",
                "core.askPass=",
                "-c",
                "credential.helper=",
                "-C",
                str(repository_root),
                *arguments,
            ],
            capture_output=True,
            check=False,
            env=scrubbed_git_environment(),
            input=input,
            text=text,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = ConfigurationError(unavailable_message)
        error.__cause__ = exc
        raise error


__all__ = ["run_git", "scrubbed_git_environment"]
