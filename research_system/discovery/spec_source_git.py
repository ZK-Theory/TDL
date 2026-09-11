"""Exact SOURCE resolution, using credential-free Git and closed outcome records."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from research_system.errors import ConfigurationError, IntegrityError
from research_system.git_execution import run_git


def parse_locator(locator: str) -> tuple[str, str | None]:
    """Accept one literal ref or full commit OID, optionally followed by :subpath."""
    if not isinstance(locator, str) or not locator or len(locator) > 2048:
        raise ConfigurationError("SOURCE requires one nonempty Git locator")
    ref, separator, subpath = locator.partition(":")
    if (
        not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", ref)
        or ".." in ref
        or "//" in ref
        or ref.endswith(("/", ".", ".lock"))
        or any(part.startswith(".") for part in ref.split("/"))
    ):
        raise ConfigurationError("malformed SOURCE Git reference")
    if separator and (
        not subpath
        or subpath.startswith(("/", "-"))
        or "\\" in subpath
        or ":" in subpath
        or any(part in {"", ".", ".."} for part in subpath.split("/"))
        or any(ord(char) < 32 for char in subpath)
    ):
        raise ConfigurationError("malformed SOURCE Git subpath")
    return ref, subpath if separator else None


def _physical_repository(path: Path) -> Path:
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise IntegrityError("SOURCE repository path is redirected")
    return path.resolve(strict=True)


def resolve_source(repository_url: str, requested_locator: str) -> tuple[dict, bytes | None]:
    """Resolve heads/tags independently, peel commits, and return their exact Git bytes.

    A whole-tree selection returns Git's deterministic tar archive; a blob
    subpath returns the blob bytes. No checkout, filters or source execution runs.
    """
    ref, subpath = parse_locator(requested_locator)
    if not isinstance(repository_url, str) or not repository_url:
        raise ConfigurationError("SOURCE repository is required")
    remote = repository_url.startswith("https://")
    if remote:
        url = urlsplit(repository_url)
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ConfigurationError("SOURCE repository must be a credential-free HTTPS URL")
    elif not Path(repository_url).is_absolute():
        raise ConfigurationError("SOURCE repository must be HTTPS or an absolute physical path")
    trace: list[str] = []
    result = {"repository_url": repository_url, "requested_locator": requested_locator, "resolution_trace": trace}
    if subpath is not None:
        result["subpath"] = subpath

    def unavailable(kind: str) -> tuple[dict, None]:
        trace.append(f"unavailable: {kind}")
        return {**result, "status": "unavailable", "failure_kind": kind}, None

    def checked(root: Path, *args: str, input: bytes | None = None):
        operation = run_git(root, *args, text=False, timeout=60, input=input)
        if operation.returncode:
            detail = operation.stderr.decode("utf-8", errors="replace").lower()
            kind = (
                "auth"
                if any(word in detail for word in ("authentication", "could not read username", "403", "401"))
                else "transport"
            )
            raise _Unavailable(kind)
        return operation.stdout

    try:
        with TemporaryDirectory(prefix="ars-source-") as temporary:
            if remote:
                root = Path(temporary)
                checked(root, "init", "--quiet")
                checked(
                    root,
                    "fetch",
                    "--quiet",
                    "--no-recurse-submodules",
                    "--no-tags",
                    repository_url,
                    "+refs/heads/*:refs/heads/*",
                    "+refs/tags/*:refs/tags/*",
                )
                trace.append("fetch: all advertised heads and tags succeeded")
            else:
                root = _physical_repository(Path(repository_url))
            refs = checked(root, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags").decode().splitlines()
            trace.append("enumerate: heads and tags succeeded")
            requested_refs = (
                {ref} if ref.startswith(("refs/heads/", "refs/tags/")) else {f"refs/heads/{ref}", f"refs/tags/{ref}"}
            )
            selections = [
                (name, "head" if name.startswith("refs/heads/") else "tag") for name in refs if name in requested_refs
            ]
            if re.fullmatch(r"[0-9a-f]{40}", ref):
                exists = checked(root, "cat-file", "--batch-check", input=f"{ref}^{{commit}}\n".encode())
                present = not exists.rstrip().endswith(b" missing")
                trace.append(f"direct commit: {'present' if present else 'absent'}")
                if present:
                    selections.append((ref, "commit"))
            candidates = []
            for name, kind in selections:
                oid = checked(root, "rev-parse", "--verify", f"{name}^{{commit}}").decode().strip()
                candidates.append({"canonical_ref": name, "resolved_kind": kind, "commit_oid": oid})
                trace.append(f"peel: {name} -> {oid}")
            if not candidates:
                trace.append("exhaustive: heads, tags and direct commit checked")
                return {**result, "status": "absent"}, None
            if len(candidates) > 1:
                return {**result, "status": "ambiguous", "candidates": candidates}, None
            selected = candidates[0]
            oid = selected["commit_oid"]
            if subpath:
                path_type = checked(root, "cat-file", "--batch-check", input=f"{oid}:{subpath}\n".encode())
                if path_type.rstrip().endswith(b" missing"):
                    trace.append("exhaustive: resolved commit has no selected subpath")
                    return {**result, "status": "absent"}, None
                if path_type.split()[1] == b"blob":
                    raw = checked(root, "cat-file", "blob", f"{oid}:{subpath}")
                elif path_type.split()[1] == b"tree":
                    raw = checked(root, "archive", "--format=tar", oid, "--", subpath)
                else:
                    raise ConfigurationError("SOURCE subpath must select a Git blob or tree")
            else:
                raw = checked(root, "archive", "--format=tar", oid)
            trace.append("read: exact committed source bytes")
            return {**result, "status": "resolved", **selected}, raw
    except _Unavailable as exc:
        return unavailable(exc.kind)
    except ConfigurationError as exc:
        if isinstance(exc.__cause__, subprocess.TimeoutExpired):
            return unavailable("timeout")
        if isinstance(exc.__cause__, OSError):
            return unavailable("transport")
        raise
    except OSError:
        return unavailable("transport")


class _Unavailable(Exception):
    def __init__(self, kind: str):
        self.kind = kind
