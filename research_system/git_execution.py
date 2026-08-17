"""Dependency-free, non-interactive Git execution for repository assurance.

The caller supplies every repository root and argument.  This module removes
ambient repository/configuration redirection and disables fsmonitor before Git
is allowed to inspect security-sensitive repository state.
"""

from __future__ import annotations

import hashlib
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


def git_blob_sha1(raw: bytes) -> str:
    """Return Git's SHA-1 object identity for exact blob bytes.

    SHA-1 is required by the Git object format here, not used as a security
    digest.  ``usedforsecurity=False`` keeps this identity operation available
    in FIPS-restricted Python/OpenSSL environments.
    """

    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()  # nosec B324


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
    # GIT_CONFIG_GLOBAL/SYSTEM suppress ambient global and system configuration.
    # GIT_CONFIG affects `git config` only; it does not suppress repository-local
    # configuration for general Git commands.  Safety-critical scalar settings
    # are therefore overridden explicitly in the command argv below.
    environment["GIT_CONFIG"] = os.devnull
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_CONFIG_SYSTEM"] = os.devnull
    # Validation must neither consult system configuration nor refresh an index.
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    # Never allow a validation probe to wait for credentials or a terminal.
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _harden_git_arguments(arguments: tuple[str, ...]) -> tuple[str, ...]:
    """Add command-specific guards where scalar config overrides are insufficient."""

    index = 0
    while index + 1 < len(arguments) and arguments[index] in {"-c", "--config-env"}:
        index += 2
    if index >= len(arguments):
        return arguments
    command = arguments[index]
    if command == "hash-object" and "--no-filters" not in arguments[index + 1 :]:
        command_arguments = list(arguments[index + 1 :])
        while "--path" in command_arguments:
            path_index = command_arguments.index("--path")
            del command_arguments[path_index : path_index + 2]
        command_arguments = [argument for argument in command_arguments if not argument.startswith("--path=")]
        return (*arguments[: index + 1], "--no-filters", *command_arguments)
    if command in {"diff", "show"} and "--no-ext-diff" not in arguments[index + 1 :]:
        return (*arguments[: index + 1], "--no-ext-diff", *arguments[index + 1 :])
    return arguments


def _split_leading_config(arguments: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    index = 0
    while index + 1 < len(arguments) and arguments[index] in {"-c", "--config-env"}:
        index += 2
    return arguments[:index], arguments[index:]


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
        resolved_repository_root = repository_root.resolve(strict=False)
        hardened_arguments = _harden_git_arguments(arguments)
        caller_config, command_arguments = _split_leading_config(hardened_arguments)
        return subprocess.run(  # nosec B603 B607 - fixed executable and argument vector
            [
                str(_GIT_EXECUTABLE),
                "-C",
                str(resolved_repository_root),
                *caller_config,
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                "-c",
                f"core.worktree={resolved_repository_root}",
                "-c",
                "core.bare=false",
                "-c",
                f"core.attributesFile={os.devnull}",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "core.pager=",
                "-c",
                "diff.external=",
                "-c",
                "core.askPass=",
                "-c",
                "credential.helper=",
                "-c",
                "credential.interactive=never",
                "-c",
                "core.sshCommand=",
                "-c",
                "core.gitProxy=",
                "-c",
                "protocol.ext.allow=never",
                "-c",
                "protocol.file.allow=never",
                *command_arguments,
            ],
            capture_output=True,
            check=False,
            shell=False,
            env=scrubbed_git_environment(),
            input=input,
            text=text,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = ConfigurationError(unavailable_message)
        error.__cause__ = exc
        raise error


__all__ = ["git_blob_sha1", "run_git", "scrubbed_git_environment"]
