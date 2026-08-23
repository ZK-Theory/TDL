"""Direct contract controls for the SPEC governed-code manifest."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import research_system.store.governed_code as governed_code
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.store.governed_code import (
    GOVERNED_CODE_MANIFEST_SCHEMA_ID,
    GOVERNED_CODE_MANIFEST_SCHEMA_VERSION,
    GovernedCodeManifest,
    GovernedSubjectRelation,
    ReviewedPostDivergenceSuccessor,
    build_governed_code_manifest,
    classify_governed_subject_relationship,
    validate_governed_code_manifest,
    validate_reviewed_documentation_successor,
    validate_reviewed_post_divergence_successor,
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _write(repository: Path, relative_path: str, text: str) -> None:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "--all")
    _git(repository, "commit", "-m", message)
    return _git(repository, "rev-parse", "HEAD")


def _recompute_manifest_hashes(mapping: dict[str, object]) -> None:
    files = mapping["governed_files"]
    assert isinstance(files, list)
    mapping["schema_catalogue_sha256"] = sha256_hex(
        canonical_bytes([item for item in files if item["category"] == "schema"])
    )
    body = {key: value for key, value in mapping.items() if key != "manifest_sha256"}
    mapping["manifest_sha256"] = sha256_hex(canonical_bytes(body))


@pytest.fixture
def governed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "governed-repository"
    origin = tmp_path / "governed-origin.git"
    repository.mkdir()
    origin.mkdir()
    _git(repository, "init", "-q", "-b", "main")
    _git(repository, "config", "user.email", "governed-code@example.test")
    _git(repository, "config", "user.name", "Governed code test")
    _git(repository, "remote", "add", "origin", origin.as_uri())
    empty_hooks = repository / "empty-hooks"
    empty_hooks.mkdir()
    _git(repository, "config", "commit.gpgSign", "false")
    _git(repository, "config", "core.hooksPath", str(empty_hooks))
    _git(repository, "config", "core.autocrlf", "false")
    _write(repository, "research_system/runtime.py", "VALUE = 'base'\n")
    _write(
        repository,
        "research_system/projection/data/wp6_1_06h_grandfather_authority.yaml",
        "schema_id: ars://tests/grandfather-authority\n",
    )
    _write(
        repository,
        "research_system/projection/data/06h-g-rm-8-grandfather-decision.json",
        '{"decision":"GRANDFATHER"}\n',
    )
    _write(repository, "research_system/projection/data/README.md", "# Package notes\n")
    _write(repository, "research_system/projection/__pycache__/grandfather.pyc", "not runtime authority\n")
    _write(repository, ".research-system/config/operator.yaml", "route: SPEC-GATE6-RUN-V1\n")
    _write(repository, ".research-system/adapters/operator.yaml", "provider: operator\n")
    _write(repository, ".research-system/schemas/operations/example.schema.json", '{"type":"object"}\n')
    _write(repository, ".research-system/contracts/example.yaml", "contract: exact\n")
    _write(repository, "pyproject.toml", '[project]\nname = "governed-code-test"\nversion = "0"\n')
    _write(repository, "uv.lock", "version = 1\n")
    _write(repository, ".python-version", "3.13\n")
    _write(repository, "docs/README.md", "# Base documentation\n")
    _commit(repository, "base governed subject")
    return repository


def test_manifest_binds_complete_category_inventory_to_committed_git_bytes(
    governed_repository: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)

    assert isinstance(manifest, GovernedCodeManifest)
    assert manifest.git_commit == _git(governed_repository, "rev-parse", "HEAD")
    assert manifest.repository_identity == _git(governed_repository, "remote", "get-url", "origin")
    assert {item.category for item in manifest.governed_files} == {
        "dependency_input",
        "executable_python",
        "operational_config",
        "schema",
        "contract",
    }
    assert {item.path for item in manifest.governed_files if item.category == "dependency_input"} == {
        ".python-version",
        "pyproject.toml",
        "uv.lock",
    }
    runtime = next(item for item in manifest.governed_files if item.path == "research_system/runtime.py")
    runtime_authority_paths = {
        "research_system/projection/data/wp6_1_06h_grandfather_authority.yaml",
        "research_system/projection/data/06h-g-rm-8-grandfather-decision.json",
    }
    assert {
        item.path for item in manifest.governed_files if item.category == "operational_config"
    } >= runtime_authority_paths
    assert "research_system/projection/data/README.md" not in {item.path for item in manifest.governed_files}
    assert "research_system/projection/__pycache__/grandfather.pyc" not in {
        item.path for item in manifest.governed_files
    }
    committed_runtime = subprocess.run(
        ["git", "-C", str(governed_repository), "show", f"HEAD:{runtime.path}"],
        check=True,
        capture_output=True,
    ).stdout
    assert runtime.canonical_sha256 == hashlib.sha256(committed_runtime).hexdigest()

    assert validate_governed_code_manifest(manifest, governed_repository) == manifest


def test_manifest_schema_is_versioned_and_validates_the_typed_public_mapping(
    governed_repository: Path,
) -> None:
    schema_path = Path(__file__).parents[3] / ".research-system/schemas/operations/governed-code-manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$id"] == GOVERNED_CODE_MANIFEST_SCHEMA_ID
    assert schema["properties"]["schema_version"]["const"] == GOVERNED_CODE_MANIFEST_SCHEMA_VERSION
    assert "repository_identity" in schema["required"]
    validator = Draft202012Validator(schema)
    mapping = build_governed_code_manifest(governed_repository).to_mapping()
    assert list(validator.iter_errors(mapping)) == []

    mapping["governed_files"][0]["canonical_sha256"] = "not-a-digest"
    assert list(validator.iter_errors(mapping))


def test_manifest_rejects_dirty_subject_and_self_consistent_hash_drift(
    governed_repository: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    _write(governed_repository, "untracked.txt", "not governed but not clean\n")

    with pytest.raises(IntegrityError, match="not clean"):
        build_governed_code_manifest(governed_repository)
    with pytest.raises(IntegrityError, match="not clean"):
        validate_governed_code_manifest(manifest, governed_repository)

    _git(governed_repository, "clean", "-f")
    forged = manifest.to_mapping()
    forged["governed_files"][0]["canonical_sha256"] = "0" * 64
    _recompute_manifest_hashes(forged)
    parsed = GovernedCodeManifest.from_mapping(forged)
    with pytest.raises(IntegrityError, match="canonical Git bytes"):
        validate_governed_code_manifest(parsed, governed_repository)


def test_manifest_rejects_missing_category_and_redirected_repository_directory(
    governed_repository: Path,
    tmp_path: Path,
) -> None:
    (governed_repository / ".research-system/contracts/example.yaml").unlink()
    _commit(governed_repository, "remove contracts")
    with pytest.raises(IntegrityError, match="category inventory"):
        build_governed_code_manifest(governed_repository)

    redirected = tmp_path / "redirected-repository"
    redirected.symlink_to(governed_repository, target_is_directory=True)
    with pytest.raises(IntegrityError, match="redirected"):
        build_governed_code_manifest(redirected)


@pytest.mark.parametrize("index_flag", ["--assume-unchanged", "--skip-worktree"])
def test_manifest_rejects_hidden_index_state_even_when_status_reports_clean(
    governed_repository: Path,
    index_flag: str,
) -> None:
    governed_path = "research_system/runtime.py"
    _git(governed_repository, "update-index", index_flag, governed_path)
    _write(governed_repository, governed_path, "VALUE = 'hidden runtime drift'\n")
    assert _git(governed_repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    with pytest.raises(IntegrityError, match="assume-unchanged or skip-worktree"):
        build_governed_code_manifest(governed_repository)


@pytest.mark.parametrize("index_flag", ["--assume-unchanged", "--skip-worktree"])
def test_manifest_rejects_hidden_runtime_authority_data_bytes(
    governed_repository: Path,
    index_flag: str,
) -> None:
    governed_path = "research_system/projection/data/wp6_1_06h_grandfather_authority.yaml"
    _git(governed_repository, "update-index", index_flag, governed_path)
    _write(governed_repository, governed_path, "schema_id: ars://tests/hidden-authority-drift\n")
    assert _git(governed_repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    with pytest.raises(IntegrityError, match="assume-unchanged or skip-worktree"):
        build_governed_code_manifest(governed_repository)


def test_git_inspection_failure_reports_exit_status_without_command_output(
    governed_repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_git(*arguments, **_kwargs):
        return subprocess.CompletedProcess(arguments, 17, stdout=b"", stderr=b"credential=secret")

    monkeypatch.setattr(governed_code.subprocess, "run", failed_git)

    with pytest.raises(IntegrityError, match="exit status 17") as error:
        build_governed_code_manifest(governed_repository)

    assert "credential=secret" not in str(error.value)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda mapping: mapping["governed_files"].append(mapping["governed_files"][0].copy()),
        lambda mapping: mapping["governed_files"][0].__setitem__("path", "research_system//runtime.py"),
        lambda mapping: mapping["governed_files"][0].__setitem__("category", "schema"),
    ],
    ids=["duplicate", "noncanonical", "wrong-category"],
)
def test_manifest_mapping_rejects_duplicate_or_noncanonical_file_records(
    governed_repository: Path,
    mutator,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    mapping = manifest.to_mapping()
    mutator(mapping)

    with pytest.raises(IntegrityError):
        GovernedCodeManifest.from_mapping(mapping)


def test_manifest_validation_rejects_a_self_consistent_extra_member(
    governed_repository: Path,
) -> None:
    mapping = build_governed_code_manifest(governed_repository).to_mapping()
    extra = mapping["governed_files"][0].copy()
    extra["path"] = ".research-system/contracts/untracked-by-subject.yaml"
    mapping["governed_files"].append(extra)
    mapping["governed_files"].sort(key=lambda item: (item["category"], item["path"]))
    _recompute_manifest_hashes(mapping)

    parsed = GovernedCodeManifest.from_mapping(mapping)
    with pytest.raises(IntegrityError, match="canonical Git bytes"):
        validate_governed_code_manifest(parsed, governed_repository)


def test_manifest_is_portable_across_clean_worktrees_of_the_same_repository(
    governed_repository: Path,
    tmp_path: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    second_worktree = tmp_path / "second-worktree"
    _git(governed_repository, "worktree", "add", "--detach", str(second_worktree), manifest.git_commit)

    try:
        assert validate_governed_code_manifest(manifest, second_worktree) == manifest
    finally:
        _git(governed_repository, "worktree", "remove", "--force", str(second_worktree))


def test_manifest_rejects_a_different_repository_identity(
    governed_repository: Path,
    tmp_path: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    different_repository = tmp_path / "different-repository"
    different_origin = tmp_path / "different-origin.git"
    different_repository.mkdir()
    different_origin.mkdir()
    _git(different_repository, "init", "-q", "-b", "main")
    _git(different_repository, "remote", "add", "origin", different_origin.as_uri())

    with pytest.raises(IntegrityError, match="repository identity differs"):
        validate_governed_code_manifest(manifest, different_repository)


def test_classify_governed_subject_relationship_reports_a_divergent_retired_subject(
    governed_repository: Path,
) -> None:
    base = _git(governed_repository, "rev-parse", "HEAD")
    _git(governed_repository, "checkout", "-q", "-b", "retired-subject", base)
    _write(governed_repository, "research_system/runtime.py", "VALUE = 'retired subject'\n")
    _commit(governed_repository, "retired governed subject")
    retired_manifest = build_governed_code_manifest(governed_repository)
    _git(governed_repository, "checkout", "-q", "-B", "main", base)
    _write(governed_repository, "research_system/runtime.py", "VALUE = 'assembled main'\n")
    _commit(governed_repository, "assembled main")

    relationship = classify_governed_subject_relationship(retired_manifest, governed_repository)

    assert relationship.relation is GovernedSubjectRelation.DIVERGENT
    assert relationship.manifest_commit == retired_manifest.git_commit
    assert relationship.inspected_commit == _git(governed_repository, "rev-parse", "HEAD")


def test_reviewed_post_divergence_successor_accepts_one_exact_clean_code_descendant(
    governed_repository: Path,
) -> None:
    predecessor = build_governed_code_manifest(governed_repository)
    _write(governed_repository, "research_system/runtime.py", "VALUE = 'reviewed successor'\n")
    successor_commit = _commit(governed_repository, "reviewed code successor")

    relationship = classify_governed_subject_relationship(predecessor, governed_repository)
    transition = validate_reviewed_post_divergence_successor(
        predecessor,
        governed_repository,
        reviewed_commit=successor_commit,
        refreshed_main_commit=successor_commit,
    )

    assert relationship.relation is GovernedSubjectRelation.STRICT_DESCENDANT
    assert isinstance(transition, ReviewedPostDivergenceSuccessor)
    assert transition.predecessor_commit == predecessor.git_commit
    assert transition.reviewed_commit == successor_commit
    assert transition.refreshed_main_commit == successor_commit
    assert transition.successor_manifest.git_commit == successor_commit
    assert transition.successor_manifest != predecessor


def test_reviewed_post_divergence_successor_rejects_stale_review_main_non_descendant_and_dirty_subject(
    governed_repository: Path,
) -> None:
    predecessor = build_governed_code_manifest(governed_repository)
    _write(governed_repository, "research_system/runtime.py", "VALUE = 'reviewed successor'\n")
    successor_commit = _commit(governed_repository, "reviewed code successor")

    with pytest.raises(IntegrityError, match="reviewed commit"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit=predecessor.git_commit,
            refreshed_main_commit=successor_commit,
        )
    with pytest.raises(IntegrityError, match="refreshed main"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit=successor_commit,
            refreshed_main_commit=predecessor.git_commit,
        )

    unrelated_commit = _git(governed_repository, "commit-tree", f"{successor_commit}^{{tree}}", "-m", "unrelated")
    _git(governed_repository, "checkout", "-q", "--detach", unrelated_commit)
    with pytest.raises(IntegrityError, match="descendant"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit=unrelated_commit,
            refreshed_main_commit=unrelated_commit,
        )

    _git(governed_repository, "checkout", "-q", "main")
    _write(governed_repository, "untracked.txt", "dirty\n")
    with pytest.raises(IntegrityError, match="not clean"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit=successor_commit,
            refreshed_main_commit=successor_commit,
        )


def test_reviewed_post_divergence_successor_rejects_malformed_reviewed_or_main_subject(
    governed_repository: Path,
) -> None:
    predecessor = build_governed_code_manifest(governed_repository)
    with pytest.raises(IntegrityError, match="reviewed commit"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit="main",
            refreshed_main_commit=predecessor.git_commit,
        )
    with pytest.raises(IntegrityError, match="refreshed main"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit=predecessor.git_commit,
            refreshed_main_commit="main",
        )


def test_reviewed_post_divergence_successor_rejects_document_only_and_redirected_subjects(
    governed_repository: Path,
    tmp_path: Path,
) -> None:
    predecessor = build_governed_code_manifest(governed_repository)
    _write(governed_repository, "docs/README.md", "# Documentation only\n")
    documentation_commit = _commit(governed_repository, "documentation successor")
    with pytest.raises(IntegrityError, match="does not change the governed code subject"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            governed_repository,
            reviewed_commit=documentation_commit,
            refreshed_main_commit=documentation_commit,
        )

    _write(governed_repository, "research_system/runtime.py", "VALUE = 'reviewed successor'\n")
    successor_commit = _commit(governed_repository, "reviewed code successor")
    redirected = tmp_path / "redirected-repository"
    redirected.symlink_to(governed_repository, target_is_directory=True)
    with pytest.raises(IntegrityError, match="redirected"):
        validate_reviewed_post_divergence_successor(
            predecessor,
            redirected,
            reviewed_commit=successor_commit,
            refreshed_main_commit=successor_commit,
        )


def test_reviewed_documentation_successor_requires_exact_review_main_and_governed_equality(
    governed_repository: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    _write(governed_repository, "docs/README.md", "# Reviewed documentation\n")
    documentation_commit = _commit(governed_repository, "documentation only")

    successor = validate_reviewed_documentation_successor(
        manifest,
        governed_repository,
        successor_commit=documentation_commit,
        reviewed_commit=documentation_commit,
    )
    assert successor.successor_commit == documentation_commit
    assert successor.documentation_only is True
    assert successor.executable_equivalence_claimed is False

    with pytest.raises(IntegrityError, match="review"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=documentation_commit,
            reviewed_commit=manifest.git_commit,
        )

    _write(governed_repository, "research_system/runtime.py", "VALUE = 'changed'\n")
    code_commit = _commit(governed_repository, "code change")
    _git(governed_repository, "checkout", "-q", "--detach", documentation_commit)
    with pytest.raises(IntegrityError, match="exact integrated main"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=documentation_commit,
            reviewed_commit=documentation_commit,
        )

    _git(governed_repository, "checkout", "-q", "main")
    with pytest.raises(IntegrityError, match="governed"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=code_commit,
            reviewed_commit=code_commit,
        )


def test_reviewed_documentation_successor_rejects_a_symlinked_documentation_entry(
    governed_repository: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    (governed_repository / "docs/linked.md").symlink_to("README.md")
    documentation_commit = _commit(governed_repository, "symlinked documentation")

    with pytest.raises(IntegrityError, match="documentation entry is not a regular file"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=documentation_commit,
            reviewed_commit=documentation_commit,
        )


@pytest.mark.parametrize("index_flag", ["--assume-unchanged", "--skip-worktree"])
def test_reviewed_documentation_successor_rejects_hidden_documentation_bytes(
    governed_repository: Path,
    index_flag: str,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    _write(governed_repository, "docs/README.md", "# Reviewed documentation\n")
    documentation_commit = _commit(governed_repository, "documentation only")
    _git(governed_repository, "update-index", index_flag, "docs/README.md")
    _write(governed_repository, "docs/README.md", "# Hidden runtime documentation drift\n")
    assert _git(governed_repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    with pytest.raises(IntegrityError, match="assume-unchanged or skip-worktree"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=documentation_commit,
            reviewed_commit=documentation_commit,
        )


def test_reviewed_documentation_successor_rejects_non_descendant_and_schema_catalogue_drift(
    governed_repository: Path,
) -> None:
    manifest = build_governed_code_manifest(governed_repository)
    base = manifest.git_commit
    _git(governed_repository, "checkout", "-q", "-b", "side", base)
    _write(governed_repository, "docs/side.md", "# Side history\n")
    side_commit = _commit(governed_repository, "side documentation")
    _git(governed_repository, "checkout", "-q", "-B", "other", base)
    _write(governed_repository, "docs/other.md", "# Other history\n")
    other_commit = _commit(governed_repository, "other documentation")
    _git(governed_repository, "branch", "-f", "main", other_commit)

    with pytest.raises(IntegrityError, match="current Git head"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=side_commit,
            reviewed_commit=side_commit,
        )

    _git(governed_repository, "checkout", "-q", "-B", "schema-change", base)
    _write(
        governed_repository,
        ".research-system/schemas/operations/example.schema.json",
        '{"type":"array"}\n',
    )
    schema_commit = _commit(governed_repository, "schema change")
    _git(governed_repository, "branch", "-f", "main", schema_commit)
    with pytest.raises(IntegrityError, match="schema catalogue"):
        validate_reviewed_documentation_successor(
            manifest,
            governed_repository,
            successor_commit=schema_commit,
            reviewed_commit=schema_commit,
        )
