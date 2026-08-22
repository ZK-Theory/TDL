"""Resolve GitHub source locators without confusing absence with unavailability."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol, Sequence, cast
from urllib.parse import unquote, urlsplit

from research_system.errors import ConfigurationError


_OID = re.compile(r"[0-9a-f]{40}")
_REPOSITORY_COMPONENT = re.compile(r"[A-Za-z0-9_.-]+")
_FAILURE_KINDS = frozenset({"auth", "timeout", "transport"})
_RESOLVED_KINDS = frozenset({"head", "lightweight_tag", "annotated_tag", "commit"})

FailureKind = Literal["auth", "timeout", "transport"]
ResolvedKind = Literal["head", "lightweight_tag", "annotated_tag", "commit"]
ResolutionStatus = Literal["resolved", "absent", "ambiguous", "unavailable"]


class GitTransportFailure(Exception):
    """A classified failure to inspect the remote Git repository."""

    def __init__(self, failure_kind: FailureKind | str, detail: str = "") -> None:
        if failure_kind not in _FAILURE_KINDS:
            raise ValueError(f"unsupported Git transport failure kind: {failure_kind}")
        super().__init__(detail or failure_kind)
        self.failure_kind = cast(FailureKind, failure_kind)


@dataclass(frozen=True)
class AdvertisedGitReference:
    """One head or tag returned by the remote advertisement."""

    canonical_ref: str
    object_oid: str
    peeled_oid: str | None = None

    def __post_init__(self) -> None:
        if not self.canonical_ref.startswith(("refs/heads/", "refs/tags/")):
            raise ValueError("advertised reference must be a canonical head or tag")
        if _OID.fullmatch(self.object_oid) is None:
            raise ValueError("advertised reference object must be an exact commit-sized OID")
        if self.peeled_oid is not None and _OID.fullmatch(self.peeled_oid) is None:
            raise ValueError("peeled reference object must be an exact commit-sized OID")


@dataclass(frozen=True)
class GitReferenceCandidate:
    """One exact commit interpretation of a requested locator."""

    canonical_ref: str
    resolved_kind: ResolvedKind
    commit_oid: str

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_ref, str) or not self.canonical_ref:
            raise ConfigurationError("Git reference candidate requires canonical_ref")
        if not isinstance(self.resolved_kind, str) or self.resolved_kind not in _RESOLVED_KINDS:
            raise ConfigurationError("Git reference candidate has invalid resolved_kind")
        if not isinstance(self.commit_oid, str) or _OID.fullmatch(self.commit_oid) is None:
            raise ConfigurationError("Git reference candidate requires an exact lowercase commit OID")
        if self.resolved_kind == "head" and (
            not self.canonical_ref.startswith("refs/heads/") or not self.canonical_ref.removeprefix("refs/heads/")
        ):
            raise ConfigurationError("Git head candidate requires a canonical head ref")
        if self.resolved_kind in {"lightweight_tag", "annotated_tag"} and (
            not self.canonical_ref.startswith("refs/tags/") or not self.canonical_ref.removeprefix("refs/tags/")
        ):
            raise ConfigurationError("Git tag candidate requires a canonical tag ref")
        if self.resolved_kind == "commit" and self.canonical_ref != self.commit_oid:
            raise ConfigurationError("Git commit candidate requires its exact commit OID as canonical_ref")

    def to_dict(self) -> dict[str, str]:
        return {
            "canonical_ref": self.canonical_ref,
            "resolved_kind": self.resolved_kind,
            "commit_oid": self.commit_oid,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GitReferenceCandidate:
        expected = {"canonical_ref", "resolved_kind", "commit_oid"}
        if set(value) != expected:
            raise ConfigurationError("Git reference candidate must be a closed object")
        if not all(isinstance(value[key], str) for key in expected):
            raise ConfigurationError("Git reference candidate fields must be strings")
        return cls(
            canonical_ref=value["canonical_ref"],
            resolved_kind=cast(ResolvedKind, value["resolved_kind"]),
            commit_oid=value["commit_oid"],
        )


@dataclass(frozen=True)
class GitReferenceResolution:
    """Closed public result for one GitHub source locator."""

    repository_url: str
    requested_locator: str
    status: ResolutionStatus
    resolution_trace: tuple[str, ...]
    subpath: str | None = None
    canonical_ref: str | None = None
    resolved_kind: ResolvedKind | None = None
    commit_oid: str | None = None
    candidates: tuple[GitReferenceCandidate, ...] = ()
    failure_kind: FailureKind | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.repository_url, str)
            or not self.repository_url
            or not isinstance(self.requested_locator, str)
            or not self.requested_locator
        ):
            raise ConfigurationError("Git reference resolution requires repository and locator")
        if not isinstance(self.status, str) or self.status not in {"resolved", "absent", "ambiguous", "unavailable"}:
            raise ConfigurationError("Git reference resolution has invalid status")
        if not self.resolution_trace or any(not isinstance(item, str) or not item for item in self.resolution_trace):
            raise ConfigurationError("Git reference resolution requires a non-empty trace")
        if self.subpath is not None:
            if (
                not isinstance(self.subpath, str)
                or not self.subpath
                or self.subpath.startswith("/")
                or "\\" in self.subpath
                or "\x00" in self.subpath
                or any(part in {"", ".", ".."} for part in self.subpath.split("/"))
            ):
                raise ConfigurationError("Git reference resolution has invalid subpath")

        singular = (self.canonical_ref, self.resolved_kind, self.commit_oid)
        if self.status == "resolved":
            if any(value is None for value in singular) or self.candidates or self.failure_kind is not None:
                raise ConfigurationError("resolved Git reference has invalid variant fields")
            GitReferenceCandidate(
                canonical_ref=cast(str, self.canonical_ref),
                resolved_kind=cast(ResolvedKind, self.resolved_kind),
                commit_oid=cast(str, self.commit_oid),
            )
            return
        if any(value is not None for value in singular):
            raise ConfigurationError("non-resolved Git reference cannot contain singular provenance")
        if self.status == "ambiguous":
            if len(self.candidates) < 2 or self.failure_kind is not None:
                raise ConfigurationError("ambiguous Git reference requires at least two candidates")
            return
        if self.candidates:
            raise ConfigurationError("non-ambiguous Git reference cannot contain candidates")
        if self.status == "unavailable":
            if not isinstance(self.failure_kind, str) or self.failure_kind not in _FAILURE_KINDS:
                raise ConfigurationError("unavailable Git reference requires a classified failure")
            return
        if self.failure_kind is not None:
            raise ConfigurationError("absent Git reference cannot contain a failure kind")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "repository_url": self.repository_url,
            "requested_locator": self.requested_locator,
            "status": self.status,
            "resolution_trace": list(self.resolution_trace),
        }
        if self.subpath is not None:
            value["subpath"] = self.subpath
        if self.status == "resolved":
            value.update(
                {
                    "canonical_ref": self.canonical_ref,
                    "resolved_kind": self.resolved_kind,
                    "commit_oid": self.commit_oid,
                }
            )
        elif self.status == "ambiguous":
            value["candidates"] = [candidate.to_dict() for candidate in self.candidates]
        elif self.status == "unavailable":
            value["failure_kind"] = self.failure_kind
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GitReferenceResolution:
        if not isinstance(value, Mapping):
            raise ConfigurationError("Git reference resolution must be an object")
        status = value.get("status")
        if not isinstance(status, str):
            raise ConfigurationError("Git reference resolution status must be a string")
        common = {"repository_url", "requested_locator", "status", "resolution_trace"}
        if "subpath" in value:
            common.add("subpath")
        variant = {
            "resolved": {"canonical_ref", "resolved_kind", "commit_oid"},
            "absent": set(),
            "ambiguous": {"candidates"},
            "unavailable": {"failure_kind"},
        }.get(status)
        if variant is None or set(value) != common | variant:
            raise ConfigurationError("Git reference resolution variant must be a closed object")
        trace = value["resolution_trace"]
        if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
            raise ConfigurationError("Git reference resolution trace must be an array")
        candidates: tuple[GitReferenceCandidate, ...] = ()
        if status == "ambiguous":
            raw_candidates = value["candidates"]
            if not isinstance(raw_candidates, Sequence) or isinstance(raw_candidates, (str, bytes)):
                raise ConfigurationError("Git reference candidates must be an array")
            if not all(isinstance(item, Mapping) for item in raw_candidates):
                raise ConfigurationError("Git reference candidates must be objects")
            candidates = tuple(GitReferenceCandidate.from_dict(item) for item in raw_candidates)
        string_fields = ("repository_url", "requested_locator")
        if not all(isinstance(value[field], str) for field in string_fields):
            raise ConfigurationError("Git reference resolution identity fields must be strings")
        if "subpath" in value and not isinstance(value["subpath"], str):
            raise ConfigurationError("Git reference resolution subpath must be a string")
        if status == "resolved" and not all(
            isinstance(value[field], str) for field in ("canonical_ref", "resolved_kind", "commit_oid")
        ):
            raise ConfigurationError("resolved Git reference provenance fields must be strings")
        if status == "unavailable" and not isinstance(value["failure_kind"], str):
            raise ConfigurationError("unavailable Git reference failure kind must be a string")
        return cls(
            repository_url=value["repository_url"],
            requested_locator=value["requested_locator"],
            status=cast(ResolutionStatus, status),
            resolution_trace=tuple(trace),
            subpath=value.get("subpath"),
            canonical_ref=value.get("canonical_ref"),
            resolved_kind=cast(ResolvedKind | None, value.get("resolved_kind")),
            commit_oid=value.get("commit_oid"),
            candidates=candidates,
            failure_kind=cast(FailureKind | None, value.get("failure_kind")),
        )


class GitReferenceTransport(Protocol):
    """Remote operations required by the semantic resolver."""

    def advertise(self, repository_url: str) -> tuple[AdvertisedGitReference, ...]: ...

    def resolve_commit(self, repository_url: str, revision: str) -> str | None: ...


class GitSourceTransport(GitReferenceTransport, Protocol):
    """Resolver transport that can also return exact blobs from one commit."""

    def read_paths(
        self,
        repository_url: str,
        commit_oid: str,
        paths: tuple[str, ...],
    ) -> dict[str, bytes]: ...


class GitCliReferenceTransport:
    """Inspect a remote with fixed-argument Git commands and no credential prompts."""

    def __init__(self, *, git_executable: str = "git", timeout_seconds: float = 30.0) -> None:
        if (
            not isinstance(git_executable, str)
            or not git_executable
            or "\x00" in git_executable
            or timeout_seconds <= 0
        ):
            raise ValueError("Git transport requires an executable and positive timeout")
        self.git_executable = git_executable
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _require_operand(value: str, label: str) -> str:
        """Reject values Git could reinterpret as options at a transport seam."""

        if not isinstance(value, str) or not value or "\x00" in value or value.startswith("-"):
            raise ValueError(f"{label} must be a non-option Git operand")
        return value

    @staticmethod
    def _classify_failure(stderr: str) -> FailureKind:
        lowered = stderr.lower()
        auth_markers = (
            "authentication failed",
            "could not read username",
            "permission denied",
            "terminal prompts disabled",
            "access denied",
        )
        if any(marker in lowered for marker in auth_markers):
            return "auth"
        return "transport"

    def _invoke(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None,
        text: bool,
    ) -> subprocess.CompletedProcess[Any]:
        """Run Git once with the transport's shared non-interactive policy."""

        environment = os.environ.copy()
        environment["GIT_TERMINAL_PROMPT"] = "0"
        environment["GCM_INTERACTIVE"] = "Never"
        options: dict[str, Any] = {
            "cwd": cwd,
            "env": environment,
            "capture_output": True,
            "text": text,
            "timeout": self.timeout_seconds,
            "check": False,
        }
        if text:
            options.update({"encoding": "utf-8", "errors": "replace"})
        try:
            return subprocess.run(
                [self.git_executable, *arguments],
                **options,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitTransportFailure("timeout", "Git command timed out") from exc
        except OSError as exc:
            raise GitTransportFailure("transport", "Git executable is unavailable") from exc

    def _run(self, arguments: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return cast(subprocess.CompletedProcess[str], self._invoke(arguments, cwd=cwd, text=True))

    def _run_bytes(self, arguments: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[bytes]:
        return cast(subprocess.CompletedProcess[bytes], self._invoke(arguments, cwd=cwd, text=False))

    def advertise(self, repository_url: str) -> tuple[AdvertisedGitReference, ...]:
        self._require_operand(repository_url, "repository URL")
        completed = self._run(("ls-remote", "--heads", "--tags", repository_url))
        if completed.returncode != 0:
            raise GitTransportFailure(self._classify_failure(completed.stderr), "Git advertisement failed")
        direct: dict[str, str] = {}
        peeled: dict[str, str] = {}
        for raw_line in completed.stdout.splitlines():
            fields = raw_line.split("\t")
            if len(fields) != 2 or _OID.fullmatch(fields[0]) is None:
                raise GitTransportFailure("transport", "Git returned malformed advertisement")
            oid, reference = fields
            is_peeled = reference.endswith("^{}")
            canonical_ref = reference[:-3] if is_peeled else reference
            if not canonical_ref.startswith(("refs/heads/", "refs/tags/")):
                raise GitTransportFailure("transport", "Git returned an unexpected reference")
            target = peeled if is_peeled else direct
            previous = target.setdefault(canonical_ref, oid)
            if previous != oid:
                raise GitTransportFailure("transport", "Git returned conflicting reference objects")
        if not set(peeled).issubset(direct):
            raise GitTransportFailure("transport", "Git returned a peeled tag without its tag object")
        return tuple(
            AdvertisedGitReference(reference, oid, peeled.get(reference)) for reference, oid in sorted(direct.items())
        )

    @staticmethod
    def _is_absent_fetch(stderr: str) -> bool:
        lowered = stderr.lower()
        return any(
            marker in lowered
            for marker in (
                "couldn't find remote ref",
                "not our ref",
                "unadvertised object",
                "no such remote ref",
            )
        )

    def resolve_commit(self, repository_url: str, revision: str) -> str | None:
        self._require_operand(repository_url, "repository URL")
        self._require_operand(revision, "revision")
        with tempfile.TemporaryDirectory(prefix="ars-git-reference-") as temporary:
            root = Path(temporary)
            initialized = self._run(("init", "--bare", "."), cwd=root)
            if initialized.returncode != 0:
                raise GitTransportFailure("transport", "temporary Git repository initialization failed")
            fetched = self._run(
                ("fetch", "--quiet", "--depth=1", "--no-tags", repository_url, revision),
                cwd=root,
            )
            if fetched.returncode != 0:
                failure_kind = self._classify_failure(fetched.stderr)
                if failure_kind != "auth" and self._is_absent_fetch(fetched.stderr):
                    return None
                raise GitTransportFailure(failure_kind, "Git object fetch failed")
            resolved = self._run(("rev-parse", "--verify", "FETCH_HEAD^{commit}"), cwd=root)
            if resolved.returncode != 0:
                return None
            oid = resolved.stdout.strip()
            if _OID.fullmatch(oid) is None:
                raise GitTransportFailure("transport", "Git returned a malformed commit OID")
            return oid

    def read_paths(
        self,
        repository_url: str,
        commit_oid: str,
        paths: tuple[str, ...],
    ) -> dict[str, bytes]:
        """Fetch one exact commit and read requested repository-relative blobs."""

        self._require_operand(repository_url, "repository URL")
        self._require_operand(commit_oid, "commit OID")
        if _OID.fullmatch(commit_oid) is None:
            raise ValueError("source read requires an exact commit OID")
        for path in paths:
            if not isinstance(path, str):
                raise ValueError("source read path must be canonical and repository-relative")
            parts = Path(path).parts
            if (
                not path
                or "\x00" in path
                or Path(path).is_absolute()
                or Path(path).as_posix() != path
                or any(part in {"", ".", ".."} for part in parts)
                or ":" in path
            ):
                raise ValueError("source read path must be canonical and repository-relative")
        with tempfile.TemporaryDirectory(prefix="ars-git-source-") as temporary:
            root = Path(temporary)
            initialized = self._run(("init", "--bare", "."), cwd=root)
            if initialized.returncode != 0:
                raise GitTransportFailure("transport", "temporary Git repository initialization failed")
            fetched = self._run(
                ("fetch", "--quiet", "--depth=1", "--no-tags", repository_url, commit_oid),
                cwd=root,
            )
            if fetched.returncode != 0:
                failure_kind = self._classify_failure(fetched.stderr)
                raise GitTransportFailure(failure_kind, "Git source fetch failed")
            resolved = self._run(("rev-parse", "--verify", "FETCH_HEAD^{commit}"), cwd=root)
            if resolved.returncode != 0 or resolved.stdout.strip() != commit_oid:
                raise GitTransportFailure("transport", "Git source fetch returned a different commit")
            content: dict[str, bytes] = {}
            for path in paths:
                listing = self._run_bytes(("ls-tree", "-z", "--full-tree", commit_oid, "--", path), cwd=root)
                if listing.returncode != 0:
                    raise GitTransportFailure("transport", "Git tree inspection failed")
                entries = tuple(entry for entry in listing.stdout.split(b"\x00") if entry)
                if not entries:
                    continue
                if len(entries) != 1:
                    raise GitTransportFailure("transport", "Git returned an ambiguous tree entry")
                metadata, separator, returned_path = entries[0].partition(b"\t")
                fields = metadata.split(b" ")
                try:
                    expected_path = path.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValueError("source read path must be UTF-8") from exc
                if separator != b"\t" or len(fields) != 3 or returned_path != expected_path:
                    raise GitTransportFailure("transport", "Git returned a malformed tree entry")
                _mode, object_type, object_oid = fields
                if object_type != b"blob":
                    continue
                if _OID.fullmatch(object_oid.decode("ascii", errors="ignore")) is None:
                    raise GitTransportFailure("transport", "Git returned a malformed blob OID")
                read = self._run_bytes(("cat-file", "blob", object_oid.decode("ascii")), cwd=root)
                if read.returncode != 0:
                    raise GitTransportFailure("transport", "Git blob read failed")
                content[path] = read.stdout
            return content


@dataclass(frozen=True)
class _ParsedLocator:
    repository_url: str
    requested_locator: str
    route: Literal["tree", "commit"]
    remainder: tuple[str, ...]


def _parse_github_locator(locator: str) -> _ParsedLocator:
    try:
        parsed = urlsplit(locator)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("invalid GitHub locator") from exc
    if (
        not isinstance(locator, str)
        or parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.hostname.lower() != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError("invalid GitHub locator")
    raw_parts = parsed.path.split("/")
    if len(raw_parts) < 5 or raw_parts[0] != "":
        raise ConfigurationError("invalid GitHub locator")
    parts = tuple(unquote(part) for part in raw_parts[1:])
    if any(not part or part in {".", ".."} or "/" in part or "\\" in part or "\x00" in part for part in parts):
        raise ConfigurationError("invalid GitHub locator")
    owner, repository, route, *remainder = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if (
        _REPOSITORY_COMPONENT.fullmatch(owner) is None
        or _REPOSITORY_COMPONENT.fullmatch(repository) is None
        or owner in {".", ".."}
        or repository in {".", ".."}
        or route not in {"tree", "commit"}
        or not remainder
    ):
        raise ConfigurationError("invalid GitHub locator")
    if route == "commit" and (len(remainder) != 1 or _OID.fullmatch(remainder[0]) is None):
        raise ConfigurationError("invalid GitHub locator")
    return _ParsedLocator(
        repository_url=f"https://github.com/{owner}/{repository}.git",
        requested_locator=locator,
        route=cast(Literal["tree", "commit"], route),
        remainder=tuple(remainder),
    )


def _count_advertised(references: Sequence[AdvertisedGitReference]) -> str:
    heads = sum(reference.canonical_ref.startswith("refs/heads/") for reference in references)
    tags = sum(reference.canonical_ref.startswith("refs/tags/") for reference in references)
    head_word = "head" if heads == 1 else "heads"
    tag_word = "tag" if tags == 1 else "tags"
    return f"advertised {heads} {head_word} and {tags} {tag_word}"


def _unavailable(parsed: _ParsedLocator, trace: list[str], failure: GitTransportFailure) -> GitReferenceResolution:
    trace.append(f"Git reference operation failed: {failure.failure_kind}")
    return GitReferenceResolution(
        repository_url=parsed.repository_url,
        requested_locator=parsed.requested_locator,
        status="unavailable",
        resolution_trace=tuple(trace),
        failure_kind=failure.failure_kind,
    )


def _candidate_from_advertisement(reference: AdvertisedGitReference, commit_oid: str) -> GitReferenceCandidate:
    if reference.canonical_ref.startswith("refs/heads/"):
        kind: ResolvedKind = "head"
    elif reference.peeled_oid is None:
        kind = "lightweight_tag"
    else:
        kind = "annotated_tag"
    return GitReferenceCandidate(reference.canonical_ref, kind, commit_oid)


def resolve_github_reference(
    locator: str,
    *,
    transport: GitReferenceTransport | None = None,
) -> GitReferenceResolution:
    """Resolve one GitHub tree or commit locator to an exact commit.

    Malformed locators raise :class:`ConfigurationError`. Remote inspection
    failures are returned as ``unavailable`` and can never be downgraded to
    ``absent``.
    """

    parsed = _parse_github_locator(locator)
    transport = transport or GitCliReferenceTransport()
    trace = [f"parsed GitHub {parsed.route} locator"]

    if parsed.route == "commit":
        oid = parsed.remainder[0]
        try:
            resolved_oid = transport.resolve_commit(parsed.repository_url, oid)
        except GitTransportFailure as failure:
            return _unavailable(parsed, trace, failure)
        if resolved_oid is None:
            trace.append(f"direct commit {oid} was absent after successful lookup")
            return GitReferenceResolution(
                parsed.repository_url,
                parsed.requested_locator,
                "absent",
                tuple(trace),
            )
        if resolved_oid != oid:
            return _unavailable(
                parsed,
                trace,
                GitTransportFailure("transport", "direct commit lookup returned a different object"),
            )
        trace.append(f"validated direct commit {resolved_oid}")
        return GitReferenceResolution(
            parsed.repository_url,
            parsed.requested_locator,
            "resolved",
            tuple(trace),
            canonical_ref=resolved_oid,
            resolved_kind="commit",
            commit_oid=resolved_oid,
        )

    try:
        advertised = transport.advertise(parsed.repository_url)
    except GitTransportFailure as failure:
        trace.append(f"Git reference advertisement failed: {failure.failure_kind}")
        return GitReferenceResolution(
            parsed.repository_url,
            parsed.requested_locator,
            "unavailable",
            tuple(trace),
            failure_kind=failure.failure_kind,
        )
    trace.append(_count_advertised(advertised))

    remainder = "/".join(parsed.remainder)
    named_matches: list[tuple[str, AdvertisedGitReference]] = []
    for reference in advertised:
        prefix = "refs/heads/" if reference.canonical_ref.startswith("refs/heads/") else "refs/tags/"
        name = reference.canonical_ref[len(prefix) :]
        if remainder == name or remainder.startswith(f"{name}/"):
            named_matches.append((name, reference))
    longest_name = max((name for name, _ in named_matches), key=len, default=None)
    selected = [reference for name, reference in named_matches if name == longest_name]

    direct_oid = parsed.remainder[0] if _OID.fullmatch(parsed.remainder[0]) is not None else None
    if longest_name is not None:
        trace.append(f"matched locator prefix '{longest_name}'")
    candidates: list[GitReferenceCandidate] = []
    subpath: str | None = None
    if longest_name is not None:
        subpath = remainder[len(longest_name) + 1 :] or None
        for reference in sorted(selected, key=lambda item: item.canonical_ref):
            try:
                resolved_oid = transport.resolve_commit(parsed.repository_url, reference.canonical_ref)
            except GitTransportFailure as failure:
                return _unavailable(parsed, trace, failure)
            if resolved_oid is None:
                trace.append(f"discarded {reference.canonical_ref}: target is not a commit")
                continue
            expected_oid = reference.peeled_oid or reference.object_oid
            if resolved_oid != expected_oid:
                return _unavailable(
                    parsed,
                    trace,
                    GitTransportFailure("transport", "remote reference changed during resolution"),
                )
            candidate = _candidate_from_advertisement(reference, resolved_oid)
            candidates.append(candidate)
            trace.append(f"validated {reference.canonical_ref} at commit {resolved_oid}")

    if direct_oid is not None and (longest_name is None or longest_name == direct_oid):
        direct_subpath = "/".join(parsed.remainder[1:]) or None
        if subpath is None:
            subpath = direct_subpath
        try:
            resolved_oid = transport.resolve_commit(parsed.repository_url, direct_oid)
        except GitTransportFailure as failure:
            return _unavailable(parsed, trace, failure)
        if resolved_oid is not None and resolved_oid != direct_oid:
            return _unavailable(
                parsed,
                trace,
                GitTransportFailure("transport", "direct commit lookup returned a different object"),
            )
        if resolved_oid is not None:
            candidates.append(GitReferenceCandidate(resolved_oid, "commit", resolved_oid))
            trace.append(f"validated direct commit {resolved_oid}")

    unique = {
        (candidate.canonical_ref, candidate.resolved_kind, candidate.commit_oid): candidate for candidate in candidates
    }
    candidates = [unique[key] for key in sorted(unique)]
    if not candidates:
        trace.append(f"no head, tag, or direct commit matched locator '{remainder}'")
        return GitReferenceResolution(
            parsed.repository_url,
            parsed.requested_locator,
            "absent",
            tuple(trace),
            subpath=subpath,
        )
    if len(candidates) > 1:
        return GitReferenceResolution(
            parsed.repository_url,
            parsed.requested_locator,
            "ambiguous",
            tuple(trace),
            subpath=subpath,
            candidates=tuple(candidates),
        )
    candidate = candidates[0]
    return GitReferenceResolution(
        parsed.repository_url,
        parsed.requested_locator,
        "resolved",
        tuple(trace),
        subpath=subpath,
        canonical_ref=candidate.canonical_ref,
        resolved_kind=candidate.resolved_kind,
        commit_oid=candidate.commit_oid,
    )


__all__ = [
    "AdvertisedGitReference",
    "GitCliReferenceTransport",
    "GitReferenceCandidate",
    "GitReferenceResolution",
    "GitReferenceTransport",
    "GitSourceTransport",
    "GitTransportFailure",
    "resolve_github_reference",
]
