from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from research_system.discovery.git_reference import (
    AdvertisedGitReference,
    GitCliReferenceTransport,
    GitReferenceCandidate,
    GitReferenceResolution,
    GitTransportFailure,
    resolve_github_reference,
)
from research_system.errors import ConfigurationError
from research_system.schema_registry import cached_schema_registry


LIGHTWEIGHT_OID = "145efcde673f1a1897eff250b77221d26c34c479"
ANNOTATED_OBJECT_OID = "7c8804c93df4ce114a7285f6be0b4f0f32f84609"
ANNOTATED_COMMIT_OID = "8a2bb4be4e7c8b5ba9e21632814b2fb55126ab52"
BRANCH_OID = "cf97c9296111f8c193150d5cd475748ef242cdc7"
DIRECT_OID = "8d1a040f4d83fcaa605f3c0f95d256192428c6de"
SCHEMA_ROOT = Path(__file__).resolve().parents[3] / ".research-system" / "schemas"


@dataclass
class FakeTransport:
    advertised: tuple[AdvertisedGitReference, ...] = ()
    resolved: dict[str, str | None] | None = None
    advertise_failure: GitTransportFailure | None = None
    resolve_failure: GitTransportFailure | None = None

    def __post_init__(self) -> None:
        if self.resolved is None:
            self.resolved = {}
        self.advertise_calls: list[str] = []
        self.resolve_calls: list[tuple[str, str]] = []

    def advertise(self, repository_url: str) -> tuple[AdvertisedGitReference, ...]:
        self.advertise_calls.append(repository_url)
        if self.advertise_failure is not None:
            raise self.advertise_failure
        return self.advertised

    def resolve_commit(self, repository_url: str, revision: str) -> str | None:
        self.resolve_calls.append((repository_url, revision))
        if self.resolve_failure is not None:
            raise self.resolve_failure
        return self.resolved.get(revision)


def _head(name: str, oid: str = BRANCH_OID) -> AdvertisedGitReference:
    return AdvertisedGitReference(canonical_ref=f"refs/heads/{name}", object_oid=oid)


def _tag(
    name: str,
    oid: str = LIGHTWEIGHT_OID,
    *,
    peeled_oid: str | None = None,
) -> AdvertisedGitReference:
    return AdvertisedGitReference(
        canonical_ref=f"refs/tags/{name}",
        object_oid=oid,
        peeled_oid=peeled_oid,
    )


def test_neurips2024_lightweight_tag_regression_resolves_exact_commit() -> None:
    transport = FakeTransport(
        advertised=(_tag("neurips2024"),),
        resolved={"refs/tags/neurips2024": LIGHTWEIGHT_OID},
    )

    result = resolve_github_reference(
        "https://github.com/berenslab/eff-ph/tree/neurips2024",
        transport=transport,
    )

    assert result.to_dict() == {
        "repository_url": "https://github.com/berenslab/eff-ph.git",
        "requested_locator": "https://github.com/berenslab/eff-ph/tree/neurips2024",
        "status": "resolved",
        "resolution_trace": [
            "parsed GitHub tree locator",
            "advertised 0 heads and 1 tag",
            "matched locator prefix 'neurips2024'",
            f"validated refs/tags/neurips2024 at commit {LIGHTWEIGHT_OID}",
        ],
        "canonical_ref": "refs/tags/neurips2024",
        "resolved_kind": "lightweight_tag",
        "commit_oid": LIGHTWEIGHT_OID,
    }


def test_annotated_tag_uses_the_peeled_commit() -> None:
    transport = FakeTransport(
        advertised=(
            _tag(
                "release/v1",
                ANNOTATED_OBJECT_OID,
                peeled_oid=ANNOTATED_COMMIT_OID,
            ),
        ),
        resolved={"refs/tags/release/v1": ANNOTATED_COMMIT_OID},
    )

    result = resolve_github_reference(
        "https://github.com/acme/project/tree/release/v1/src/model.py",
        transport=transport,
    )

    assert result.to_dict()["resolved_kind"] == "annotated_tag"
    assert result.to_dict()["commit_oid"] == ANNOTATED_COMMIT_OID
    assert result.to_dict()["subpath"] == "src/model.py"


def test_longest_slash_ref_wins_over_a_shorter_ref_prefix() -> None:
    transport = FakeTransport(
        advertised=(_head("feature"), _head("feature/source", DIRECT_OID)),
        resolved={"refs/heads/feature/source": DIRECT_OID},
    )

    result = resolve_github_reference(
        "https://github.com/acme/project/tree/feature/source/pkg/file.py",
        transport=transport,
    )

    assert result.to_dict()["canonical_ref"] == "refs/heads/feature/source"
    assert result.to_dict()["subpath"] == "pkg/file.py"
    assert transport.resolve_calls == [("https://github.com/acme/project.git", "refs/heads/feature/source")]


def test_same_name_head_and_tag_are_ambiguous_without_singular_provenance() -> None:
    transport = FakeTransport(
        advertised=(_head("release"), _tag("release")),
        resolved={
            "refs/heads/release": BRANCH_OID,
            "refs/tags/release": LIGHTWEIGHT_OID,
        },
    )

    result = resolve_github_reference(
        "https://github.com/acme/project/tree/release",
        transport=transport,
    )

    assert result.to_dict() == {
        "repository_url": "https://github.com/acme/project.git",
        "requested_locator": "https://github.com/acme/project/tree/release",
        "status": "ambiguous",
        "resolution_trace": [
            "parsed GitHub tree locator",
            "advertised 1 head and 1 tag",
            "matched locator prefix 'release'",
            f"validated refs/heads/release at commit {BRANCH_OID}",
            f"validated refs/tags/release at commit {LIGHTWEIGHT_OID}",
        ],
        "candidates": [
            {
                "canonical_ref": "refs/heads/release",
                "resolved_kind": "head",
                "commit_oid": BRANCH_OID,
            },
            {
                "canonical_ref": "refs/tags/release",
                "resolved_kind": "lightweight_tag",
                "commit_oid": LIGHTWEIGHT_OID,
            },
        ],
    }


@pytest.mark.parametrize("route", ["tree", "commit"])
def test_direct_commit_locator_resolves_an_exact_oid(route: str) -> None:
    transport = FakeTransport(resolved={DIRECT_OID: DIRECT_OID})

    result = resolve_github_reference(
        f"https://github.com/acme/project/{route}/{DIRECT_OID}",
        transport=transport,
    )

    assert result.to_dict()["canonical_ref"] == DIRECT_OID
    assert result.to_dict()["resolved_kind"] == "commit"
    assert result.to_dict()["commit_oid"] == DIRECT_OID
    if route == "tree":
        assert transport.advertise_calls == ["https://github.com/acme/project.git"]
    else:
        assert transport.advertise_calls == []


def test_tree_direct_commit_locator_preserves_the_optional_subpath() -> None:
    transport = FakeTransport(resolved={DIRECT_OID: DIRECT_OID})

    result = resolve_github_reference(
        f"https://github.com/acme/project/tree/{DIRECT_OID}/src/model.py",
        transport=transport,
    )

    assert result.to_dict()["subpath"] == "src/model.py"
    assert result.to_dict()["canonical_ref"] == DIRECT_OID
    assert result.to_dict()["commit_oid"] == DIRECT_OID


def test_direct_commit_lookup_cannot_substitute_a_different_commit() -> None:
    result = resolve_github_reference(
        f"https://github.com/acme/project/commit/{DIRECT_OID}",
        transport=FakeTransport(resolved={DIRECT_OID: BRANCH_OID}),
    )

    assert result.status == "unavailable"
    assert result.failure_kind == "transport"


def test_absent_requires_successful_exhaustive_advertisement() -> None:
    result = resolve_github_reference(
        "https://github.com/acme/project/tree/missing",
        transport=FakeTransport(advertised=(_head("main"), _tag("v1"))),
    )

    assert result.to_dict() == {
        "repository_url": "https://github.com/acme/project.git",
        "requested_locator": "https://github.com/acme/project/tree/missing",
        "status": "absent",
        "resolution_trace": [
            "parsed GitHub tree locator",
            "advertised 1 head and 1 tag",
            "no head, tag, or direct commit matched locator 'missing'",
        ],
    }


@pytest.mark.parametrize("failure_kind", ["auth", "timeout", "transport"])
def test_transport_failure_is_unavailable_never_absent(failure_kind: str) -> None:
    result = resolve_github_reference(
        "https://github.com/acme/project/tree/release",
        transport=FakeTransport(
            advertise_failure=GitTransportFailure(failure_kind, "untrusted detail"),
        ),
    )

    assert result.to_dict() == {
        "repository_url": "https://github.com/acme/project.git",
        "requested_locator": "https://github.com/acme/project/tree/release",
        "status": "unavailable",
        "resolution_trace": [
            "parsed GitHub tree locator",
            f"Git reference advertisement failed: {failure_kind}",
        ],
        "failure_kind": failure_kind,
    }


@pytest.mark.parametrize(
    "locator",
    [
        "http://github.com/acme/project/tree/main",
        "https://gitlab.com/acme/project/tree/main",
        "https://github.com/acme/project/blob/main/file.py",
        "https://github.com/acme/project/commit/not-an-oid",
        "https://github.com/acme/project/tree/../main",
        "https://github.com/acme/project/tree/feature%2Fsource",
        "https://github.com/acme/project/tree/main?tab=readme",
    ],
)
def test_malformed_locator_is_an_input_error(locator: str) -> None:
    transport = FakeTransport()

    with pytest.raises(ConfigurationError, match="GitHub locator"):
        resolve_github_reference(locator, transport=transport)

    assert transport.advertise_calls == []
    assert transport.resolve_calls == []


def test_result_parser_rejects_fields_from_another_status_variant() -> None:
    with pytest.raises(ConfigurationError, match="closed object"):
        GitReferenceResolution.from_dict(
            {
                "repository_url": "https://github.com/acme/project.git",
                "requested_locator": "https://github.com/acme/project/tree/missing",
                "status": "absent",
                "resolution_trace": ["exhaustive successful resolution"],
                "failure_kind": "transport",
            }
        )


@pytest.mark.parametrize(
    ("status", "invalid_fields"),
    [
        ([], {}),
        ({"status": "resolved"}, {}),
        ("resolved", {"canonical_ref": []}),
        ("resolved", {"resolved_kind": {"head"}}),
        ("resolved", {"commit_oid": 1}),
        ("unavailable", {"failure_kind": []}),
    ],
)
def test_result_parser_rejects_malformed_variant_values_without_type_leaks(
    status: object,
    invalid_fields: dict[str, object],
) -> None:
    value: dict[str, object] = {
        "repository_url": "https://github.com/acme/project.git",
        "requested_locator": "https://github.com/acme/project/tree/main",
        "status": status,
        "resolution_trace": ["parsed source"],
    }
    if status == "resolved":
        value.update(
            {
                "canonical_ref": "refs/heads/main",
                "resolved_kind": "head",
                "commit_oid": BRANCH_OID,
            }
        )
    elif status == "unavailable":
        value["failure_kind"] = "transport"
    value.update(invalid_fields)

    with pytest.raises(ConfigurationError):
        GitReferenceResolution.from_dict(value)


@pytest.mark.parametrize(
    ("canonical_ref", "resolved_kind", "commit_oid"),
    [
        ("refs/tags/main", "head", BRANCH_OID),
        ("refs/heads/main", "lightweight_tag", BRANCH_OID),
        (BRANCH_OID, "commit", DIRECT_OID),
    ],
)
def test_git_reference_candidates_reject_mismatched_canonical_provenance(
    canonical_ref: str,
    resolved_kind: str,
    commit_oid: str,
) -> None:
    with pytest.raises(ConfigurationError, match="canonical"):
        GitReferenceCandidate(canonical_ref, resolved_kind, commit_oid)  # type: ignore[arg-type]


@pytest.mark.parametrize("subpath", ["/source", "source/../other", "source\\other"])
def test_result_parser_rejects_noncanonical_subpaths(subpath: str) -> None:
    with pytest.raises(ConfigurationError, match="subpath"):
        GitReferenceResolution(
            repository_url="https://github.com/acme/project.git",
            requested_locator="https://github.com/acme/project/tree/main/source",
            status="resolved",
            resolution_trace=("validated source",),
            subpath=subpath,
            canonical_ref="refs/heads/main",
            resolved_kind="head",
            commit_oid=BRANCH_OID,
        )


def test_cli_fetch_does_not_misclassify_auth_failure_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = GitCliReferenceTransport()

    def fake_run(arguments: tuple[str, ...], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if arguments[0] == "init":
            return subprocess.CompletedProcess(arguments, 0, "", "")
        assert arguments[0] == "fetch"
        return subprocess.CompletedProcess(
            arguments,
            128,
            "",
            "fatal: Authentication failed\nfatal: couldn't find remote ref protected",
        )

    monkeypatch.setattr(transport, "_run", fake_run)

    with pytest.raises(GitTransportFailure, match="Git object fetch failed") as error:
        transport.resolve_commit("https://github.com/acme/project.git", "refs/heads/protected")

    assert error.value.failure_kind == "auth"


def test_cli_source_fetch_does_not_misclassify_auth_failure_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = GitCliReferenceTransport()

    def fake_run(arguments: tuple[str, ...], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if arguments[0] == "init":
            return subprocess.CompletedProcess(arguments, 0, "", "")
        assert arguments[0] == "fetch"
        return subprocess.CompletedProcess(
            arguments,
            128,
            "",
            "fatal: Authentication failed\nfatal: couldn't find remote ref protected",
        )

    monkeypatch.setattr(transport, "_run", fake_run)

    with pytest.raises(GitTransportFailure, match="Git source fetch failed") as error:
        transport.read_paths(
            "https://github.com/acme/project.git",
            DIRECT_OID,
            ("source.py",),
        )

    assert error.value.failure_kind == "auth"


def test_registered_schema_accepts_each_closed_result_variant() -> None:
    registry = cached_schema_registry(SCHEMA_ROOT)
    values = [
        resolve_github_reference(
            "https://github.com/acme/project/tree/main",
            transport=FakeTransport(
                advertised=(_head("main"),),
                resolved={"refs/heads/main": BRANCH_OID},
            ),
        ).to_dict(),
        resolve_github_reference(
            "https://github.com/acme/project/tree/missing",
            transport=FakeTransport(),
        ).to_dict(),
        resolve_github_reference(
            "https://github.com/acme/project/tree/release",
            transport=FakeTransport(
                advertised=(_head("release"), _tag("release")),
                resolved={
                    "refs/heads/release": BRANCH_OID,
                    "refs/tags/release": LIGHTWEIGHT_OID,
                },
            ),
        ).to_dict(),
        resolve_github_reference(
            "https://github.com/acme/project/tree/main",
            transport=FakeTransport(advertise_failure=GitTransportFailure("timeout")),
        ).to_dict(),
    ]

    for value in values:
        registry.validate("ars://portfolio/git-reference-resolution", value)


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def test_git_cli_transport_handles_real_heads_and_both_tag_forms(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    remote.mkdir()
    work.mkdir()
    _git(remote, "init", "--bare", ".")
    _git(work, "init", ".")
    _git(work, "config", "user.name", "ARS Test")
    _git(work, "config", "user.email", "ars-test@example.invalid")
    (work / "source.txt").write_text("exact source\n", encoding="utf-8")
    _git(work, "add", "source.txt")
    _git(work, "commit", "-m", "source")
    commit_oid = _git(work, "rev-parse", "HEAD")
    _git(work, "branch", "feature/source")
    _git(work, "tag", "lightweight")
    _git(work, "tag", "-a", "annotated", "-m", "annotated tag")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "--all", "origin")
    _git(work, "push", "--tags", "origin")

    transport = GitCliReferenceTransport(timeout_seconds=10)
    advertised = {item.canonical_ref: item for item in transport.advertise(str(remote))}

    assert advertised["refs/heads/feature/source"].object_oid == commit_oid
    assert advertised["refs/tags/lightweight"].peeled_oid is None
    assert advertised["refs/tags/annotated"].peeled_oid == commit_oid
    assert transport.resolve_commit(str(remote), "refs/heads/feature/source") == commit_oid
    assert transport.resolve_commit(str(remote), "refs/tags/lightweight") == commit_oid
    assert transport.resolve_commit(str(remote), "refs/tags/annotated") == commit_oid
    assert transport.resolve_commit(str(remote), commit_oid) == commit_oid
