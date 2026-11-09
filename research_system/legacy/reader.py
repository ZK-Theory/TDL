"""The W9 observation reader (WP9.3 note §7).

It reads a registered legacy source by its kind, handle-bound, and returns the exact bytes with the identity the
observation records. Read modes (§7.1):

- ``git_tracked``: a handle-bound working-tree read and a Git object read of ``<git_head>:<path>``, which must be
  byte-identical, as W11 requires;
- a ``conventions_lock`` registration (``CONVENTIONS.md``): a Git object read of blob ``4620c716`` only (W9 §7.3 item 3);
- a Computational-Log entry (role ``legacy_decision_log_entry``): the accepted export's retained copy, read from Git at
  its pinned commit; the live vault page is refused (owner point C). None is pinned in WP9.3, so it is refused;
- ``untracked_file`` and ``restricted_untracked_file``: a handle-bound read under the repository root;
- ``vault_file``: a handle-bound read through the real vault path, never the repository's ``vault/`` junction, which
  must resolve to the registration's ``canonical_target``. The vault's ``CONVENTIONS.md`` is a symlink to the repository
  file, so a source whose resolved target is the repository's ``CONVENTIONS.md`` is refused, by path and by identity.

**The handle-bound protocol** is W11 §7.3's (open, hash, re-check identity, close), on the repository's primitives: the
registered root anchor and per-directory member anchors (``research_system.store.lock``), as Discovery's dossier read
uses them. It refuses a symlink or junction leaf or parent, a file with more than one link, and any change of file
identity before, during or after the read, with every parent anchor unchanged. A registration's ``physical_identity``
is computed from the same identity calls.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.store.lock import open_registered_member_directory_anchor, open_registered_root_anchor

READER_VERSION = "1.0.0"
TOOL_ID = "research_system.legacy.reader"
# The modules whose blobs at the binding's git_head identify the importer (§7.5).
IMPORTER_MODULES = ("research_system/legacy/reader.py", "research_system/legacy/segmentation.py")
CONVENTIONS_LOCK = {
    "repository_path": "CONVENTIONS.md",
    "git_commit": "4b143c9225035cc29e37351445f1c3a4ab09ceb1",
    "git_blob": "4620c71607ca3a06c6df3b8e96a6bddffc783960",
    "byte_length": 33645,
    "sha256": "d04fe97e4a318f4a3c3dae00650419c13d6e7077ac54acda0b738c1608698589",
}
CL_ROLE = "legacy_decision_log_entry"
_GIT_TIMEOUT_SECONDS = 30
# §7.4: fixed per identity kind, so every observer writes the same ones.
NON_INFERENCES = {
    "git_tracked": ("no authority from file presence (W0 §4)",),
    "untracked_file": ("no authority from file presence (W0 §4)", "no Git identity"),
    "vault_file": ("no authority from file presence (W0 §4)", "no Git identity"),
    "restricted_untracked_file": (
        "no authority from file presence (W0 §4)",
        "no Git identity",
        "no frozen copy in the ARS store",
    ),
}


class ReadRefused(IntegrityError):
    """The source cannot be read as its registration requires; nothing is observed."""


def utc_micros(value: datetime) -> str:
    """Contract §5.1: UTC, ISO 8601, ``Z`` and microseconds."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def git_blob_id(raw: bytes) -> str:
    """The Git blob ID of exact bytes."""
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False).hexdigest()


def _git(repository: Path, *args: str, text: bool = True) -> Any:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *args],
            check=True,
            capture_output=True,
            text=text,
            timeout=_GIT_TIMEOUT_SECONDS,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise ReadRefused(f"git {args[0]} failed") from exc


@dataclass(frozen=True)
class SourceRead:
    """One read: the exact bytes, the source identity the record carries, and the read's own facts."""

    raw: bytes
    source_identity: dict[str, Any]
    physical_identity: dict[str, Any] | None
    path_form: dict[str, Any]
    read_started_at: str
    read_ended_at: str
    non_inferences: tuple[str, ...] = field(default=())


def _relative(path: str) -> PurePosixPath:
    # The raw segments are checked: PurePosixPath drops "." segments silently.
    if not path or path.startswith("/") or "\\" in path or ":" in path:
        raise ReadRefused("registered path is not a canonical relative path")
    if any(segment in {"", ".", ".."} for segment in path.split("/")):
        raise ReadRefused("registered path is not a canonical relative path")
    return PurePosixPath(path)


def canonical_target(path: Path | str) -> str:
    """A physical target in one form: no Windows ``\\\\?\\`` prefix, forward slashes."""
    text = str(path)
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[len("\\\\?\\UNC\\") :]
    elif text.startswith("\\\\?\\"):
        text = text[len("\\\\?\\") :]
    return Path(text).as_posix()


def _physical_identity(final: Path, opened: os.stat_result) -> dict[str, Any]:
    return {
        "canonical_target": canonical_target(final),
        "reparse_chain": [],
        "volume_serial_number": str(opened.st_dev),
        "stable_file_id": str(opened.st_ino),
        "link_count": int(opened.st_nlink),
        "case_aliases": [],
        "unicode_aliases": [],
        "short_name_aliases": [],
    }


def handle_bound_read(root: Path, path: str) -> tuple[bytes, dict[str, Any], tuple[int, int]]:
    """Read one file under a registered root by W11 §7.3's protocol (WP9.3 note §7.1).

    Returns:
        The bytes, the physical identity, and the file's ``(st_dev, st_ino)``.

    Raises:
        ReadRefused: For a symlink or junction leaf or parent, a file with more than one link, a missing file, or any
            identity change before, during or after the read.
    """

    relative = _relative(path)
    anchor = open_registered_root_anchor(root, delete_protect=True)
    try:
        directory_anchors = []
        try:
            parent = anchor.final_path
            for part in relative.parts[:-1]:
                child = parent / part
                try:
                    child_anchor = open_registered_member_directory_anchor(child)
                except Exception as exc:
                    raise ReadRefused("a parent of the registered path is unavailable") from exc
                directory_anchors.append(child_anchor)
                if os.path.normcase(str(child_anchor.final_path)) != os.path.normcase(str(child)):
                    raise ReadRefused("a parent of the registered path is a link or junction")
                parent = child_anchor.final_path
            candidate = parent / relative.parts[-1]
            if candidate.is_symlink() or candidate.is_junction():
                raise ReadRefused("the registered path is a symlink or junction")
            before = candidate.stat(follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise ReadRefused("the registered path is not a regular file")
            if before.st_nlink != 1:
                raise ReadRefused("the registered file has more than one link")
            with candidate.open("rb") as handle:
                opened = os.fstat(handle.fileno())
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or opened.st_nlink != 1:
                    raise ReadRefused("the registered file's identity changed during the read")
                raw = handle.read()
                after = os.fstat(handle.fileno())
            linked = candidate.stat(follow_symlinks=False)
            stable = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
            if any(getattr(after, name) != getattr(opened, name) for name in stable) or (
                linked.st_dev,
                linked.st_ino,
                linked.st_nlink,
            ) != (opened.st_dev, opened.st_ino, 1):
                raise ReadRefused("the registered file's identity changed during the read")
            for directory_anchor in directory_anchors:
                if directory_anchor.refresh() != (directory_anchor.identity, directory_anchor.final_path):
                    raise ReadRefused("a parent anchor changed during the read")
            final = candidate.resolve(strict=True)
        except ReadRefused:
            raise
        except FileNotFoundError as exc:
            raise ReadRefused("the registered file is missing") from exc
        except OSError as exc:
            raise ReadRefused("the registered file cannot be read handle-bound") from exc
        finally:
            for directory_anchor in reversed(directory_anchors):
                directory_anchor.close()
        if anchor.refresh() != (anchor.identity, anchor.final_path):
            raise ReadRefused("the registered root changed during the read")
    finally:
        anchor.close()
    return raw, _physical_identity(final, opened), (opened.st_dev, opened.st_ino)


class LegacyReader:
    """Reads registered legacy sources for the W9 preparers and ``ars legacy observation-id`` (WP9.3 note §7)."""

    def __init__(
        self,
        *,
        repository_root: Path,
        git_head: str | None,
        vault_root: Path | None = None,
        accepted_cl_export: Collection[Mapping[str, Any]] = (),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        code_root: Path | None = None,
        code_head: str | None = None,
    ) -> None:
        """Bind the reader to the binding's repository and ``git_head`` (§11.2).

        Args:
            repository_root: The bound repository root (the source repository).
            git_head: The binding's ``git_head``; required for any Git read.
            vault_root: The real vault path, never the repository's ``vault/`` junction.
            accepted_cl_export: The pinned Computational-Log export (§11.3).
            clock: The read-time clock.
            code_root: The repository the importer's modules are read from; the source repository by default.
            code_head: The commit the importer's modules are read at; ``git_head`` by default.
        """
        self.repository_root = repository_root.resolve(strict=True)
        self.git_head = git_head
        self.vault_root = vault_root
        self.accepted_cl_export = tuple(accepted_cl_export)
        self.clock = clock
        self.code_root = (code_root or repository_root).resolve(strict=True)
        self.code_head = code_head or git_head
        if vault_root is not None:
            given = Path(os.path.abspath(vault_root))
            try:
                given.relative_to(self.repository_root)
            except ValueError:
                pass
            else:
                raise ReadRefused("the vault is read through its real path, never through the repository")

    def importer_identity(self, actor_id: str) -> dict[str, Any]:
        """§7.5: the tool, its version, and the SHA-256 over its modules' blobs at the binding's ``git_head``."""
        if not self.code_head:
            raise ReadRefused("the importer identity needs the binding's git_head")
        blobs = {
            path: _git(self.code_root, "rev-parse", f"{self.code_head}:{path}").strip() for path in IMPORTER_MODULES
        }
        return {
            "actor_id": actor_id,
            "tool_id": TOOL_ID,
            "tool_version": READER_VERSION,
            "tool_sha256": sha256_hex(canonical_bytes(blobs)),
        }

    def _git_object(self, commit: str, path: str) -> tuple[bytes, str]:
        raw = _git(self.repository_root, "show", f"{commit}:{path}", text=False)
        blob = _git(self.repository_root, "rev-parse", f"{commit}:{path}").strip()
        if git_blob_id(raw) != blob:
            raise ReadRefused("the Git object read does not hash to its blob")
        return raw, blob

    def _repository_conventions_identity(self) -> tuple[int, int] | None:
        try:
            observed = (self.repository_root / "CONVENTIONS.md").stat()
        except OSError:
            return None
        return observed.st_dev, observed.st_ino

    def read(self, registration: Mapping[str, Any]) -> SourceRead:
        """Read the source a registration names, by its kind and role (§7.1).

        Raises:
            ReadRefused: If the source cannot be read as the registration requires.
        """

        started = self.clock()
        role = registration.get("role")
        kind = registration.get("source_identity_kind")
        path = str(registration.get("normalized_path"))
        physical: dict[str, Any] | None = None
        path_form = {"path_as_given": path, "resolved_through_link": False, "resolved_target": None}
        if role == CL_ROLE:
            if not self.accepted_cl_export:
                raise ReadRefused("no accepted Computational-Log export")
            copy = self.accepted_cl_export[-1]["retained_copy"]
            raw, blob = self._git_object(copy["git_commit"], copy["repository_path"])
            identity = {
                "identity_kind": "git_tracked",
                "repository_path": copy["repository_path"],
                "git_commit": copy["git_commit"],
                "git_blob": blob,
            }
            kind = "git_tracked"
        elif role == "conventions_lock":
            raw, blob = self._git_object(CONVENTIONS_LOCK["git_commit"], CONVENTIONS_LOCK["repository_path"])
            if blob != CONVENTIONS_LOCK["git_blob"]:
                raise ReadRefused("CONVENTIONS.md is read only from blob 4620c716")
            identity = {
                "identity_kind": "git_tracked",
                "repository_path": "CONVENTIONS.md",
                "git_commit": CONVENTIONS_LOCK["git_commit"],
                "git_blob": blob,
            }
        elif kind == "git_tracked":
            if not self.git_head:
                raise ReadRefused("a git_tracked read needs the binding's git_head")
            raw, physical, _ = handle_bound_read(self.repository_root, path)
            committed, blob = self._git_object(self.git_head, path)
            if committed != raw:
                raise ReadRefused("the working tree differs from the bytes at the binding's git_head")
            identity = {
                "identity_kind": "git_tracked",
                "repository_path": path,
                "git_commit": self.git_head,
                "git_blob": blob,
            }
        elif kind in {"untracked_file", "restricted_untracked_file"}:
            raw, physical, _ = handle_bound_read(self.repository_root, path)
            identity = {"identity_kind": kind, "path": path}
        elif kind == "vault_file":
            if self.vault_root is None:
                raise ReadRefused("no vault root is configured")
            raw, physical, file_key = handle_bound_read(self.vault_root, path)
            target = registration.get("physical_identity", {}).get("canonical_target")
            conventions = self._repository_conventions_identity()
            if (
                PurePosixPath(physical["canonical_target"]).name.casefold() == "conventions.md"
                or file_key == conventions
            ):
                raise ReadRefused("the vault source resolves to the repository's CONVENTIONS.md")
            if os.path.normcase(physical["canonical_target"]) != os.path.normcase(str(target)):
                raise ReadRefused("the vault source does not resolve to the registration's canonical target")
            identity = {"identity_kind": "vault_file", "vault_path": path}
        else:
            raise ReadRefused(f"unknown source kind: {kind}")
        identity["sha256"] = sha256_hex(raw)
        identity["byte_length"] = len(raw)
        return SourceRead(
            raw=raw,
            source_identity=identity,
            physical_identity=physical,
            path_form=path_form,
            read_started_at=utc_micros(started),
            read_ended_at=utc_micros(self.clock()),
            non_inferences=NON_INFERENCES[kind],
        )
