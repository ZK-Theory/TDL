"""Exact remote Git proof for governed Discovery source corrections."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConfigurationError, IntegrityError
from research_system.git_execution import run_git


@dataclass(frozen=True)
class SourceCorrectionRemoteProof:
    """Ephemeral proof that one exact correction document matches its remote ref."""

    document_sha256: str
    repository_url: str
    resolved_ref: str
    commit_oid: str
    required_paths_sha256: str


def resolve_remote_tag(repository_url: str, resolved_ref: str) -> str:
    """Resolve one exact remote tag without treating heads as exhaustive."""

    if (
        not isinstance(repository_url, str)
        or not repository_url
        or not isinstance(resolved_ref, str)
        or not resolved_ref
    ):
        raise IntegrityError("SPEC-01 correction remote identity is invalid")

    try:
        with tempfile.TemporaryDirectory(prefix="ars-spec-ls-remote-") as directory:
            result = run_git(
                Path(directory),
                "ls-remote",
                "--tags",
                repository_url,
                resolved_ref,
                timeout=30,
                unavailable_message="SPEC-01 correction remote reference could not be resolved",
            )
    except ConfigurationError as exc:
        raise IntegrityError("SPEC-01 correction remote reference could not be resolved") from exc
    lines = [line.split() for line in result.stdout.splitlines() if line.strip()]
    direct: list[str] = []
    peeled: list[str] = []
    for line in lines:
        if len(line) != 2 or len(line[0]) != 40 or any(character not in "0123456789abcdef" for character in line[0]):
            raise IntegrityError("SPEC-01 correction remote tag resolution is not exact")
        if line[1] == resolved_ref:
            direct.append(line[0])
        elif line[1] == f"{resolved_ref}^{{}}":
            peeled.append(line[0])
        else:
            raise IntegrityError("SPEC-01 correction remote tag resolution is not exact")
    if result.returncode != 0 or len(direct) != 1 or len(peeled) > 1 or len(lines) != len(direct) + len(peeled):
        raise IntegrityError("SPEC-01 correction remote tag resolution is not exact")
    return peeled[0] if peeled else direct[0]


def verify_remote_commit_paths(
    repository_url: str,
    resolved_ref: str,
    commit_oid: str,
    required_paths: Sequence[Mapping[str, Any]],
) -> None:
    """Verify every correction path against bytes fetched from the pinned ref."""

    if not isinstance(repository_url, str) or not isinstance(resolved_ref, str):
        raise IntegrityError("SPEC-01 correction remote identity is invalid")
    if not isinstance(commit_oid, str) or len(commit_oid) != 40:
        raise IntegrityError("SPEC-01 correction commit identity is invalid")
    if not required_paths:
        raise IntegrityError("SPEC-01 correction required paths are empty")
    expected: dict[str, str] = {}
    for item in required_paths:
        path = item.get("path") if isinstance(item, Mapping) else None
        digest = item.get("sha256") if isinstance(item, Mapping) else None
        relative = Path(path) if isinstance(path, str) else None
        if (
            relative is None
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != path
            or not isinstance(digest, str)
            or len(digest) != 64
            or path in expected
        ):
            raise IntegrityError("SPEC-01 correction required path binding is invalid")
        expected[path] = digest
    try:
        with tempfile.TemporaryDirectory(prefix="ars-spec-correction-") as directory:
            checkout = Path(directory)
            commands = (("init", "--quiet"), ("remote", "add", "origin", repository_url))
            for arguments in commands:
                result = run_git(
                    checkout,
                    *arguments,
                    timeout=30,
                    text=False,
                    unavailable_message="SPEC-01 correction remote content could not be fetched",
                )
                if result.returncode != 0:
                    raise IntegrityError("SPEC-01 correction remote content could not be fetched")
            fetched = run_git(
                checkout,
                "fetch",
                "--quiet",
                "--depth=1",
                "origin",
                resolved_ref,
                timeout=30,
                unavailable_message="SPEC-01 correction remote content could not be fetched",
            )
            if fetched.returncode != 0:
                raise IntegrityError("SPEC-01 correction remote content could not be fetched")
            resolved = run_git(
                checkout,
                "rev-parse",
                "FETCH_HEAD^{commit}",
                timeout=30,
                unavailable_message="SPEC-01 correction fetched ref could not be resolved",
            )
            if resolved.returncode != 0 or resolved.stdout.strip() != commit_oid:
                raise IntegrityError("SPEC-01 correction fetched ref differs from its pinned commit")
            for path, digest in expected.items():
                content = run_git(
                    checkout,
                    "show",
                    f"{commit_oid}:{path}",
                    text=False,
                    timeout=30,
                    unavailable_message="SPEC-01 correction remote path could not be read",
                )
                if content.returncode != 0 or sha256_hex(content.stdout) != digest:
                    raise IntegrityError("SPEC-01 correction required path differs from the pinned commit")
    except ConfigurationError as exc:
        raise IntegrityError("SPEC-01 correction remote content could not be verified") from exc


def verify_source_correction_remote(
    document: Mapping[str, Any],
    *,
    resolve_tag: Callable[[str, str], str] | None = None,
    verify_paths: Callable[[str, str, str, Sequence[Mapping[str, Any]]], None] | None = None,
) -> SourceCorrectionRemoteProof:
    """Verify a correction's exact remote tag, fetched commit, and required path bytes."""

    git_ref = document.get("corrected_git_reference")
    if not isinstance(git_ref, Mapping):
        raise IntegrityError("SPEC-01 correction remote identity is invalid")
    repository_url = git_ref.get("repository_url")
    resolved_ref = git_ref.get("resolved_ref")
    commit_oid = git_ref.get("commit_oid")
    required_paths = git_ref.get("required_paths")
    if (
        not isinstance(repository_url, str)
        or not repository_url
        or not isinstance(resolved_ref, str)
        or not resolved_ref
        or not isinstance(commit_oid, str)
        or len(commit_oid) != 40
        or not isinstance(required_paths, Sequence)
        or isinstance(required_paths, (str, bytes, bytearray))
    ):
        raise IntegrityError("SPEC-01 correction remote identity is invalid")
    resolver = resolve_remote_tag if resolve_tag is None else resolve_tag
    path_verifier = verify_remote_commit_paths if verify_paths is None else verify_paths
    resolved_commit = resolver(repository_url, resolved_ref)
    if resolved_commit != commit_oid:
        raise IntegrityError("SPEC-01 correction commit differs from the live remote tag")
    path_verifier(
        repository_url,
        resolved_ref,
        commit_oid,
        required_paths,
    )
    return SourceCorrectionRemoteProof(
        document_sha256=sha256_hex(canonical_bytes(document)),
        repository_url=repository_url,
        resolved_ref=resolved_ref,
        commit_oid=commit_oid,
        required_paths_sha256=sha256_hex(canonical_bytes(required_paths)),
    )


__all__ = [
    "SourceCorrectionRemoteProof",
    "resolve_remote_tag",
    "verify_remote_commit_paths",
    "verify_source_correction_remote",
]
