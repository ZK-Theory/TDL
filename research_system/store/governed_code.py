"""Canonical Git-subject identities for the Gate 6 SPEC control store.

The manifest deliberately identifies committed Git *blob* bytes, rather than
working-tree bytes.  That keeps the identity stable across checkout EOL
normalisation and makes a dirty or redirected candidate fail before it can be
bound to a control store.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError

GOVERNED_CODE_MANIFEST_SCHEMA_ID = "ars://store/governed-code-manifest"
GOVERNED_CODE_MANIFEST_SCHEMA_VERSION = "1.0.0"
GIT_INSPECTION_TIMEOUT_SECONDS = 10

_COMMIT_OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_SCP_REMOTE = re.compile(r"^[^/@:\s]+@(?P<host>[^/:\s]+):(?P<path>.+)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTEGRATED_MAIN_REF = "refs/heads/main"
_CATEGORIES = frozenset(
    {
        "executable_python",
        "operational_config",
        "schema",
        "contract",
        "dependency_input",
    }
)
_REQUIRED_CATEGORIES = _CATEGORIES
_DEPENDENCY_INPUTS = frozenset({".python-version", "pyproject.toml", "uv.lock"})
_RUNTIME_AUTHORITY_DATA_PREFIX = "research_system/projection/data/"
_RUNTIME_AUTHORITY_DATA_SUFFIXES = frozenset({".json", ".yaml", ".yml"})
_REDIRECT_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _canonical_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise IntegrityError(f"{label} path is not canonical")
    if any(ord(character) < 32 for character in value):
        raise IntegrityError(f"{label} path is not canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise IntegrityError(f"{label} path is not canonical")
    canonical = path.as_posix()
    if canonical != value:
        raise IntegrityError(f"{label} path is not canonical")
    return canonical


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise IntegrityError(f"{label} is not a SHA-256 digest")
    return value


def _require_commit_oid(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_OID.fullmatch(value) is None:
        raise IntegrityError(f"{label} is not an exact Git commit")
    return value


def _category_for_path(path: str) -> str | None:
    if path.startswith("research_system/") and path.endswith(".py"):
        return "executable_python"
    if (
        path.startswith(_RUNTIME_AUTHORITY_DATA_PREFIX)
        and PurePosixPath(path).suffix in _RUNTIME_AUTHORITY_DATA_SUFFIXES
    ):
        # `projection.grandfather` reads these serialized authority records at
        # runtime.  The constrained package-data rule deliberately excludes
        # prose and interpreter caches from the governed code subject.
        return "operational_config"
    if path.startswith(".research-system/schemas/"):
        return "schema"
    if path.startswith(".research-system/contracts/"):
        return "contract"
    if path.startswith(".research-system/"):
        return "operational_config"
    if path in _DEPENDENCY_INPUTS:
        return "dependency_input"
    return None


def _is_governed_prefix(path: str) -> bool:
    return (
        path.startswith(
            (
                "research_system/",
                ".research-system/",
            )
        )
        or path in _DEPENDENCY_INPUTS
    )


def _is_documentation_path(path: str) -> bool:
    return path == "README.md" or path.startswith("docs/")


def _physical_directory(path: Path, *, label: str) -> Path:
    """Return an existing directory only when every component is physical.

    ``Path.resolve`` is intentionally not used as the authority check: it would
    erase the evidence that an operator supplied a symlink, junction, or other
    Windows reparse point.
    """

    absolute = Path(os.path.abspath(path))
    if not absolute.is_absolute():  # pragma: no cover - defensive for exotic paths
        raise IntegrityError(f"{label} is not absolute")
    current = Path(absolute.anchor)
    parts = absolute.parts[1:]
    for part in parts:
        current /= part
        try:
            details = os.lstat(current)
        except OSError as exc:
            raise IntegrityError(f"{label} is unavailable") from exc
        attributes = getattr(details, "st_file_attributes", 0)
        if stat.S_ISLNK(details.st_mode) or attributes & _REDIRECT_ATTRIBUTE:
            raise IntegrityError(f"{label} is redirected")
    if not current.is_dir():
        raise IntegrityError(f"{label} is not a directory")
    return current


def _assert_physical_file(root: Path, relative_path: str) -> None:
    path = root.joinpath(*PurePosixPath(relative_path).parts)
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            details = os.lstat(current)
        except OSError as exc:
            raise IntegrityError("governed file is unavailable") from exc
        attributes = getattr(details, "st_file_attributes", 0)
        if stat.S_ISLNK(details.st_mode) or attributes & _REDIRECT_ATTRIBUTE:
            raise IntegrityError("governed file is redirected")
    if not current.is_file():
        raise IntegrityError("governed file is not a regular file")


def _run_git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            input=input_bytes,
            check=False,
            capture_output=True,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IntegrityError("governed repository Git inspection is unavailable") from exc
    if completed.returncode != 0:
        raise IntegrityError(f"governed repository Git inspection failed with exit status {completed.returncode}")
    return completed.stdout


def _git_text(root: Path, *arguments: str) -> str:
    try:
        return _run_git(root, *arguments).decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise IntegrityError("governed repository Git inspection is not UTF-8") from exc


def _git_commit(root: Path, value: object, *, label: str) -> str:
    requested = _require_commit_oid(value, label=label)
    resolved = _git_text(root, "rev-parse", "--verify", f"{requested}^{{commit}}")
    if _COMMIT_OID.fullmatch(resolved) is None:
        raise IntegrityError(f"{label} did not resolve to an exact Git commit")
    return resolved


def _assert_clean_subject(root: Path) -> str:
    top_level = _physical_directory(
        Path(_git_text(root, "rev-parse", "--show-toplevel")),
        label="governed candidate root",
    )
    if top_level != root:
        raise IntegrityError("governed candidate root is not the Git worktree root")
    if _git_text(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise IntegrityError("governed candidate Git subject is not clean")
    return _git_commit(root, _git_text(root, "rev-parse", "HEAD"), label="Git head")


def _credential_free_repository_identity(value: str) -> str:
    if "://" in value:
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise IntegrityError("governed repository identity is invalid") from exc
        if parsed.netloc:
            if not parsed.scheme or not hostname:
                raise IntegrityError("governed repository identity is invalid")
            host = f"[{hostname}]" if ":" in hostname else hostname
            authority = f"{host}:{port}" if port is not None else host
            return urlunsplit((parsed.scheme, authority, parsed.path, "", ""))
        return value
    scp_remote = _SCP_REMOTE.fullmatch(value)
    if scp_remote is not None:
        return f"{scp_remote.group('host')}:{scp_remote.group('path')}"
    return value


def _canonical_repository_identity(root: Path) -> str:
    """Return Git's canonical configured identity for this repository.

    A worktree's absolute path is not durable provenance: the same repository
    can be inspected from a second clean linked worktree.  The configured
    origin is shared by those worktrees and is available without a network
    request.  Authentication userinfo is not repository identity and must
    never enter the persisted manifest.  Resolving SSH/HTTPS aliases would
    require an external authority that this local admission boundary does not
    possess.
    """

    try:
        identity = _git_text(root, "remote", "get-url", "origin")
    except IntegrityError as exc:
        raise IntegrityError("governed repository identity is unavailable") from exc
    if not identity or any(ord(character) < 32 for character in identity):
        raise IntegrityError("governed repository identity is invalid")
    return _credential_free_repository_identity(identity)


def _tree_entries(root: Path, commit: str) -> tuple[tuple[str, str, str, str], ...]:
    raw = _run_git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries: list[tuple[str, str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, encoded_path = record.split(b"\t", maxsplit=1)
            mode, kind, oid = metadata.decode("ascii", errors="strict").split(" ")
            path = encoded_path.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise IntegrityError("governed Git tree has an invalid entry") from exc
        canonical = _canonical_path(path, label="Git tree")
        if _is_governed_prefix(canonical) and (kind != "blob" or mode not in {"100644", "100755"}):
            raise IntegrityError("governed Git tree contains a redirected or non-regular file")
        entries.append((canonical, mode, kind, oid))
    return tuple(entries)


def _blob_contents(root: Path, blob_oids: tuple[str, ...]) -> Mapping[str, bytes]:
    unique = tuple(dict.fromkeys(blob_oids))
    if not unique:
        return {}
    output = _run_git(root, "cat-file", "--batch", input_bytes=("\n".join(unique) + "\n").encode("ascii"))
    contents: dict[str, bytes] = {}
    offset = 0
    for expected_oid in unique:
        try:
            header_end = output.index(b"\n", offset)
            header = output[offset:header_end].decode("ascii", errors="strict").split(" ")
            oid, kind, length_text = header
            length = int(length_text)
            content_start = header_end + 1
            content_end = content_start + length
            content = output[content_start:content_end]
            if len(content) != length or output[content_end : content_end + 1] != b"\n":
                raise ValueError("invalid batch payload")
        except (UnicodeDecodeError, ValueError, IndexError) as exc:
            raise IntegrityError("governed Git blob inspection failed") from exc
        if oid != expected_oid or kind != "blob" or _COMMIT_OID.fullmatch(oid) is None:
            raise IntegrityError("governed Git blob inspection returned an unexpected object")
        contents[oid] = content
        offset = content_end + 1
    if offset != len(output):
        raise IntegrityError("governed Git blob inspection returned trailing data")
    return contents


def _canonical_lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _assert_working_bytes_match_committed(root: Path, expected: Mapping[str, bytes]) -> None:
    """Compare bytes without trusting configurable Git content filters.

    A clean ``git status`` is not an immutable-byte proof: assume-unchanged and
    skip-worktree flags or a custom clean filter can hide a divergent runtime
    file.  Only line-ending normalization is permitted between committed text
    blobs and the bytes the runtime will actually read.
    """

    paths = tuple(expected)
    tagged = _run_git(root, "ls-files", "-v", "-z")
    flags: dict[str, str] = {}
    for record in tagged.split(b"\0"):
        if not record:
            continue
        try:
            flag = record[:1].decode("ascii", errors="strict")
            if record[1:2] != b" ":
                raise ValueError("missing tag separator")
            path = _canonical_path(record[2:].decode("utf-8", errors="strict"), label="Git index")
        except (UnicodeDecodeError, ValueError) as exc:
            raise IntegrityError("governed Git index entry is invalid") from exc
        flags[path] = flag
    if set(paths) - set(flags):
        raise IntegrityError("governed file is absent from the Git index")
    if any(flags[path] != "H" for path in paths):
        raise IntegrityError("governed file has assume-unchanged or skip-worktree index state")
    for path in paths:
        try:
            working = root.joinpath(*PurePosixPath(path).parts).read_bytes()
        except OSError as exc:
            raise IntegrityError("governed working file is unavailable") from exc
        if _canonical_lf(working) != _canonical_lf(expected[path]):
            raise IntegrityError("governed working file differs from its exact Git blob")


@dataclass(frozen=True, slots=True)
class GovernedCodeFile:
    """One category-labelled immutable Git blob in a governed subject."""

    category: str
    path: str
    git_blob_oid: str
    canonical_sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> "GovernedCodeFile":
        if not isinstance(value, Mapping) or set(value) != {
            "category",
            "path",
            "git_blob_oid",
            "canonical_sha256",
        }:
            raise IntegrityError("governed file record fields are not exact")
        category = value.get("category")
        if not isinstance(category, str) or category not in _CATEGORIES:
            raise IntegrityError("governed file category is unsupported")
        path = _canonical_path(value.get("path"), label="governed file")
        if _category_for_path(path) != category:
            raise IntegrityError("governed file category does not own its path")
        oid = _require_commit_oid(value.get("git_blob_oid"), label="governed file blob")
        digest = _require_sha256(value.get("canonical_sha256"), label="governed file canonical hash")
        return cls(category=category, path=path, git_blob_oid=oid, canonical_sha256=digest)

    def to_mapping(self) -> dict[str, str]:
        return {
            "category": self.category,
            "path": self.path,
            "git_blob_oid": self.git_blob_oid,
            "canonical_sha256": self.canonical_sha256,
        }


def _schema_catalogue_sha256(files: tuple[GovernedCodeFile, ...]) -> str:
    return sha256_hex(canonical_bytes([item.to_mapping() for item in files if item.category == "schema"]))


@dataclass(frozen=True, slots=True)
class GovernedCodeManifest:
    """A versioned, immutable inventory of the executable governed subject."""

    repository_identity: str
    git_commit: str
    governed_files: tuple[GovernedCodeFile, ...]
    schema_catalogue_sha256: str
    manifest_sha256: str
    schema_id: str = GOVERNED_CODE_MANIFEST_SCHEMA_ID
    schema_version: str = GOVERNED_CODE_MANIFEST_SCHEMA_VERSION

    def _body_mapping(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "repository_identity": self.repository_identity,
            "git_commit": self.git_commit,
            "governed_files": [item.to_mapping() for item in self.governed_files],
            "schema_catalogue_sha256": self.schema_catalogue_sha256,
        }

    def to_mapping(self) -> dict[str, Any]:
        return {**self._body_mapping(), "manifest_sha256": self.manifest_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> "GovernedCodeManifest":
        if not isinstance(value, Mapping) or set(value) != {
            "schema_id",
            "schema_version",
            "repository_identity",
            "git_commit",
            "governed_files",
            "schema_catalogue_sha256",
            "manifest_sha256",
        }:
            raise IntegrityError("governed code manifest fields are not exact")
        if (
            value.get("schema_id") != GOVERNED_CODE_MANIFEST_SCHEMA_ID
            or value.get("schema_version") != GOVERNED_CODE_MANIFEST_SCHEMA_VERSION
        ):
            raise IntegrityError("governed code manifest schema is unsupported")
        repository_identity = value.get("repository_identity")
        if (
            not isinstance(repository_identity, str)
            or not repository_identity
            or any(ord(character) < 32 for character in repository_identity)
        ):
            raise IntegrityError("governed code manifest repository identity is invalid")
        if _credential_free_repository_identity(repository_identity) != repository_identity:
            raise IntegrityError("governed code manifest repository identity is invalid")
        git_commit = _require_commit_oid(value.get("git_commit"), label="governed manifest Git commit")
        raw_files = value.get("governed_files")
        if not isinstance(raw_files, list):
            raise IntegrityError("governed code manifest files are invalid")
        files = tuple(GovernedCodeFile.from_mapping(item) for item in raw_files)
        if not files or tuple(sorted(files, key=lambda item: (item.category, item.path))) != files:
            raise IntegrityError("governed code manifest files are not canonically ordered")
        paths = tuple(item.path for item in files)
        if len(set(paths)) != len(paths):
            raise IntegrityError("governed code manifest files are duplicated")
        if {item.category for item in files} != _REQUIRED_CATEGORIES:
            raise IntegrityError("governed code manifest category inventory is incomplete")
        catalogue_sha256 = _require_sha256(value.get("schema_catalogue_sha256"), label="governed schema catalogue hash")
        if catalogue_sha256 != _schema_catalogue_sha256(files):
            raise IntegrityError("governed schema catalogue hash does not match its exact files")
        manifest_sha256 = _require_sha256(value.get("manifest_sha256"), label="governed manifest hash")
        candidate = cls(
            repository_identity=repository_identity,
            git_commit=git_commit,
            governed_files=files,
            schema_catalogue_sha256=catalogue_sha256,
            manifest_sha256=manifest_sha256,
        )
        if candidate.manifest_sha256 != sha256_hex(canonical_bytes(candidate._body_mapping())):
            raise IntegrityError("governed code manifest hash does not match exact contents")
        return candidate


def _validated_manifest(value: GovernedCodeManifest | Mapping[str, Any]) -> GovernedCodeManifest:
    """Run the exact mapping validator even for an already typed value."""

    return GovernedCodeManifest.from_mapping(value.to_mapping() if isinstance(value, GovernedCodeManifest) else value)


def _assert_manifest_repository_identity(manifest: GovernedCodeManifest, root: Path) -> None:
    if manifest.repository_identity != _canonical_repository_identity(root):
        raise IntegrityError("governed code manifest repository identity differs from the candidate repository")


def _inventory_for_commit(
    root: Path,
    commit: str,
    *,
    verify_working_files: bool,
) -> tuple[GovernedCodeFile, ...]:
    selected: list[tuple[str, str, str]] = []
    for path, _mode, _kind, oid in _tree_entries(root, commit):
        category = _category_for_path(path)
        if category is not None:
            selected.append((category, path, oid))
    if not selected:
        raise IntegrityError("governed code manifest has no governed files")
    if {category for category, _path, _oid in selected} != _REQUIRED_CATEGORIES:
        raise IntegrityError("governed code manifest category inventory is incomplete")
    if len({path for _category, path, _oid in selected}) != len(selected):
        raise IntegrityError("governed code manifest path inventory is duplicated")
    blob_contents = _blob_contents(root, tuple(oid for _category, _path, oid in selected))
    if verify_working_files:
        for _category, path, _oid in selected:
            _assert_physical_file(root, path)
        _assert_working_bytes_match_committed(
            root,
            {path: blob_contents[oid] for _category, path, oid in selected},
        )
    return tuple(
        GovernedCodeFile(
            category=category,
            path=path,
            git_blob_oid=oid,
            canonical_sha256=hashlib.sha256(blob_contents[oid]).hexdigest(),
        )
        for category, path, oid in sorted(selected)
    )


def build_governed_code_manifest(
    repository_root: str | Path,
    *,
    subject: str | None = None,
) -> GovernedCodeManifest:
    """Build a manifest from exactly the clean committed subject at ``HEAD``.

    ``subject`` is optional only to make a caller's expected exact commit
    explicit.  It must resolve to the same commit as the clean worktree HEAD;
    symbolic branch names are intentionally not accepted.
    """

    root = _physical_directory(Path(repository_root), label="governed candidate root")
    head = _assert_clean_subject(root)
    if subject is not None and _git_commit(root, subject, label="governed manifest subject") != head:
        raise IntegrityError("governed manifest subject is not the clean Git head")
    files = _inventory_for_commit(root, head, verify_working_files=True)
    catalogue_sha256 = _schema_catalogue_sha256(files)
    body = {
        "schema_id": GOVERNED_CODE_MANIFEST_SCHEMA_ID,
        "schema_version": GOVERNED_CODE_MANIFEST_SCHEMA_VERSION,
        "repository_identity": _canonical_repository_identity(root),
        "git_commit": head,
        "governed_files": [item.to_mapping() for item in files],
        "schema_catalogue_sha256": catalogue_sha256,
    }
    return GovernedCodeManifest.from_mapping({**body, "manifest_sha256": sha256_hex(canonical_bytes(body))})


def validate_governed_code_manifest(
    manifest: GovernedCodeManifest | Mapping[str, Any],
    repository_root: str | Path,
) -> GovernedCodeManifest:
    """Fail closed unless one clean worktree exactly recreates ``manifest``."""

    parsed = _validated_manifest(manifest)
    root = _physical_directory(Path(repository_root), label="governed candidate root")
    _assert_manifest_repository_identity(parsed, root)
    if _assert_clean_subject(root) != parsed.git_commit:
        raise IntegrityError("governed code manifest Git subject differs from the candidate head")
    rebuilt = build_governed_code_manifest(root, subject=parsed.git_commit)
    if rebuilt != parsed:
        raise IntegrityError("governed code manifest differs from exact canonical Git bytes")
    return parsed


def _assert_manifest_base_subject(
    manifest: GovernedCodeManifest,
    root: Path,
    base_commit: str,
) -> None:
    base_files = _inventory_for_commit(root, base_commit, verify_working_files=False)
    if (
        _schema_catalogue_sha256(base_files) != manifest.schema_catalogue_sha256
        or base_files != manifest.governed_files
    ):
        raise IntegrityError("governed code manifest does not match its exact base Git subject")


class GovernedSubjectRelation(str, Enum):
    """Git-history relation between a persisted manifest and a clean subject."""

    SAME = "same"
    STRICT_DESCENDANT = "strict_descendant"
    STRICT_ANCESTOR = "strict_ancestor"
    DIVERGENT = "divergent"


@dataclass(frozen=True, slots=True)
class GovernedSubjectRelationship:
    """Read-only classification; it grants no binding transition authority."""

    manifest_commit: str
    inspected_commit: str
    relation: GovernedSubjectRelation


def classify_governed_subject_relationship(
    manifest: GovernedCodeManifest | Mapping[str, Any],
    repository_root: str | Path,
) -> GovernedSubjectRelationship:
    """Classify a clean local subject against a portable manifest identity.

    In particular, ``DIVERGENT`` is evidence for a separately governed
    retired-subject transition; this helper does not construct or authorize
    that transition.
    """

    parsed = _validated_manifest(manifest)
    root = _physical_directory(Path(repository_root), label="governed candidate root")
    _assert_manifest_repository_identity(parsed, root)
    current_head = _assert_clean_subject(root)
    base = _git_commit(root, parsed.git_commit, label="governed manifest Git commit")
    _assert_manifest_base_subject(parsed, root, base)
    _inventory_for_commit(root, current_head, verify_working_files=True)
    if current_head == base:
        relation = GovernedSubjectRelation.SAME
    elif _is_ancestor(root, base, current_head):
        relation = GovernedSubjectRelation.STRICT_DESCENDANT
    elif _is_ancestor(root, current_head, base):
        relation = GovernedSubjectRelation.STRICT_ANCESTOR
    else:
        relation = GovernedSubjectRelation.DIVERGENT
    return GovernedSubjectRelationship(
        manifest_commit=base,
        inspected_commit=current_head,
        relation=relation,
    )


@dataclass(frozen=True, slots=True)
class ReviewedPostDivergenceSuccessor:
    """One reviewed code successor after a separately governed divergence repair."""

    predecessor_commit: str
    successor_manifest: GovernedCodeManifest
    reviewed_commit: str
    refreshed_main_commit: str


def validate_reviewed_post_divergence_successor(
    predecessor_manifest: GovernedCodeManifest | Mapping[str, Any],
    repository_root: str | Path,
    *,
    reviewed_commit: str,
    refreshed_main_commit: str,
) -> ReviewedPostDivergenceSuccessor:
    """Validate an ordinary later reviewed code successor on clean live main.

    This is intentionally *not* the retired-binding divergence transition.
    That transition needs its own governed transaction.  The caller refreshes
    and independently verifies live main before passing it here; this local
    boundary requires that value, the reviewed subject, and the physical clean
    worktree all identify one strict code-changing descendant.
    """

    predecessor = _validated_manifest(predecessor_manifest)
    root = _physical_directory(Path(repository_root), label="governed candidate root")
    current_head = _assert_clean_subject(root)
    _assert_manifest_repository_identity(predecessor, root)
    base = _git_commit(root, predecessor.git_commit, label="governed predecessor manifest Git commit")
    _assert_manifest_base_subject(predecessor, root, base)
    reviewed = _git_commit(root, reviewed_commit, label="reviewed commit")
    refreshed_main = _git_commit(root, refreshed_main_commit, label="refreshed main commit")
    if current_head != reviewed:
        raise IntegrityError("reviewed commit is not the exact current Git head")
    if current_head != refreshed_main:
        raise IntegrityError("refreshed main commit is not the exact current Git head")
    if base == current_head or not _is_ancestor(root, base, current_head):
        raise IntegrityError("reviewed successor is not a code-bearing descendant of the predecessor manifest")
    successor_manifest = build_governed_code_manifest(root, subject=current_head)
    if successor_manifest.governed_files == predecessor.governed_files:
        raise IntegrityError("reviewed successor does not change the governed code subject")
    return ReviewedPostDivergenceSuccessor(
        predecessor_commit=base,
        successor_manifest=successor_manifest,
        reviewed_commit=reviewed,
        refreshed_main_commit=refreshed_main,
    )


@dataclass(frozen=True, slots=True)
class ReviewedDocumentationSuccessor:
    """Proof that a reviewed integrated descendant changes documentation only."""

    base_commit: str
    successor_commit: str
    integrated_main_commit: str
    documentation_only: bool = True
    executable_equivalence_claimed: bool = False


def _is_ancestor(root: Path, older: str, newer: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
            check=False,
            capture_output=True,
            timeout=GIT_INSPECTION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IntegrityError("governed repository ancestry inspection is unavailable") from exc
    if completed.returncode in {0, 1}:
        return completed.returncode == 0
    raise IntegrityError("governed repository ancestry inspection failed")


def _changed_paths(root: Path, base: str, successor: str) -> tuple[str, ...]:
    raw = _run_git(root, "diff", "--no-renames", "--name-only", "-z", base, successor)
    try:
        paths = tuple(
            _canonical_path(item.decode("utf-8", errors="strict"), label="Git diff")
            for item in raw.split(b"\0")
            if item
        )
    except UnicodeDecodeError as exc:
        raise IntegrityError("governed Git diff is not UTF-8") from exc
    if not paths:
        raise IntegrityError("reviewed documentation successor does not advance the governed subject")
    return paths


def _assert_documentation_entries_are_regular(
    root: Path,
    base: str,
    successor: str,
    changed_paths: tuple[str, ...],
) -> None:
    base_entries = {path: (mode, kind, oid) for path, mode, kind, oid in _tree_entries(root, base)}
    successor_entries = {path: (mode, kind, oid) for path, mode, kind, oid in _tree_entries(root, successor)}
    current_documentation_paths: list[str] = []
    for path in changed_paths:
        for entries in (base_entries, successor_entries):
            entry = entries.get(path)
            if entry is not None and entry[:2] not in {("100644", "blob"), ("100755", "blob")}:
                raise IntegrityError("reviewed successor changed documentation entry is not a regular file")
        if path in successor_entries:
            _assert_physical_file(root, path)
            current_documentation_paths.append(path)
    if current_documentation_paths:
        documentation_blobs = _blob_contents(
            root,
            tuple(successor_entries[path][2] for path in current_documentation_paths),
        )
        _assert_working_bytes_match_committed(
            root,
            {path: documentation_blobs[successor_entries[path][2]] for path in current_documentation_paths},
        )


def validate_reviewed_documentation_successor(
    manifest: GovernedCodeManifest | Mapping[str, Any],
    repository_root: str | Path,
    *,
    successor_commit: str,
    reviewed_commit: str,
) -> ReviewedDocumentationSuccessor:
    """Admit only an exactly reviewed, integrated documentation-only descendant.

    This return value is deliberately not an executable-equivalence attestation:
    it proves that the configured governed inventory and schema catalogue did
    not change, while permitting a separately reviewed documentation revision.
    The integration ref is fixed locally; the binding service separately owns
    the fresh live-remote equality check before an authoritative store write.
    """

    parsed = _validated_manifest(manifest)
    root = _physical_directory(Path(repository_root), label="governed candidate root")
    current_head = _assert_clean_subject(root)
    _assert_manifest_repository_identity(parsed, root)
    base = _git_commit(root, parsed.git_commit, label="governed manifest Git commit")
    _assert_manifest_base_subject(parsed, root, base)
    successor = _git_commit(root, successor_commit, label="reviewed successor")
    reviewed = _git_commit(root, reviewed_commit, label="reviewed commit")
    if current_head != successor:
        raise IntegrityError("reviewed successor is not the exact current Git head")
    if reviewed != successor:
        raise IntegrityError("reviewed commit is not the exact successor commit")
    try:
        integrated_main = _git_text(root, "rev-parse", "--verify", f"{_INTEGRATED_MAIN_REF}^{{commit}}")
    except IntegrityError as exc:
        raise IntegrityError("reviewed successor main integration is unavailable") from exc
    integrated_main = _git_commit(root, integrated_main, label="integrated main commit")
    if not _is_ancestor(root, base, successor):
        raise IntegrityError("reviewed successor is not a descendant of the governed manifest")
    if integrated_main != successor:
        raise IntegrityError("reviewed successor is not the exact integrated main commit")
    successor_files = _inventory_for_commit(root, successor, verify_working_files=True)
    if _schema_catalogue_sha256(successor_files) != parsed.schema_catalogue_sha256:
        raise IntegrityError("reviewed successor changes the governed schema catalogue")
    if successor_files != parsed.governed_files:
        raise IntegrityError("reviewed successor changes governed code, configuration, contracts, or locks")
    changed_paths = _changed_paths(root, base, successor)
    if any(not _is_documentation_path(path) for path in changed_paths):
        raise IntegrityError("reviewed successor contains non-document changes")
    _assert_documentation_entries_are_regular(root, base, successor, changed_paths)
    return ReviewedDocumentationSuccessor(
        base_commit=base,
        successor_commit=successor,
        integrated_main_commit=integrated_main,
    )
