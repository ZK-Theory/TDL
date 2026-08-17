from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import research_system.assurance.runner as assurance_runner
import research_system.evidence.wp64_real_a8 as wp64_real_a8
import research_system.git_execution as git_execution_module
import research_system.methods.registration as registration_module
import tools.verify_w11_materialization as w11_materialization
from research_system.canonical import sha256_hex
from research_system.errors import ConfigurationError
from research_system.git_execution import git_blob_sha1, run_git, scrubbed_git_environment
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    RawContentPublication,
    prepare_registered_raw_content,
)


ARTEFACT_ID = "art_019ffe2b-fd4b-7000-8000-000000000111"
SPEC_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md")
ASSET_PATH = Path(".research-system/methods/assets/example.md")


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    for relative in (SPEC_PATH, ASSET_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"# {relative.name}\n".encode())
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Tests")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "fixture")
    return root


def _registration(document_type: str) -> CandidateRegistration:
    return CandidateRegistration(
        artefact_id=ARTEFACT_ID,
        project_id="prj_01978abc-1000-7000-8000-000000001000",
        actor_id="act_01978abc-1001-7000-8000-000000001001",
        authority_grant_id="agr_019fe47a-3001-7000-8000-000000003001",
        submitted_at="2026-08-14T12:00:00Z",
        correlation_id="git-registration-hardening",
        reason="bind one exact committed source",
        manifest={
            "artefact_id": ARTEFACT_ID,
            "artefact_type": document_type,
            "authority": {"use_authority": "candidate"},
        },
    )


def _publication(root: Path, source: Path, document_type: str) -> RawContentPublication:
    raw = (root / source).read_bytes()
    return RawContentPublication(
        source_relative_path=source.as_posix(),
        source_git_blob=_git(root, "rev-parse", f"HEAD:{source.as_posix()}"),
        content_sha256=sha256_hex(raw),
        size_bytes=len(raw),
        media_type="text/markdown; charset=utf-8",
        document_type=document_type,
        destination_relative_path=f"methods/content/spec-flow/{ARTEFACT_ID}.md",
    )


def test_git_environment_scrubs_case_variant_repository_and_config_injection() -> None:
    environment = scrubbed_git_environment(
        {
            "Path": "git-bin",
            "gIt_DiR": "foreign.git",
            "GIT_CEILING_DIRECTORIES": "foreign-root",
            "Git_Config_Global": "foreign-config",
            "git_config_count": "1",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "git_config_value_0": "malicious-hook",
        }
    )

    assert environment["Path"] == "git-bin"
    assert not any(
        key.casefold() == "git_dir"
        or key.casefold() == "git_ceiling_directories"
        or (
            key.casefold().startswith("git_config_")
            and key not in {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM"}
        )
        for key in environment
    )
    assert environment["GIT_CONFIG"] == os.devnull
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_GRAFT_FILE"] == os.devnull
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_git_environment_scrubs_process_transport_and_prompt_injection_case_insensitively() -> None:
    environment = scrubbed_git_environment(
        {
            "Path": "git-bin",
            "gIt_ExEc_PaTh": "hostile-exec",
            "Git_Ssh_Command": "hostile-ssh",
            "GIT_ASKPASS": "hostile-askpass",
            "ssh_askpass": "hostile-ssh-askpass",
            "git_proxy_command": "hostile-proxy",
            "GIT_ALLOW_PROTOCOL": "file",
            "git_protocol_from_user": "1",
        }
    )

    assert environment["Path"] == "git-bin"
    assert not {
        "git_exec_path",
        "git_ssh_command",
        "git_askpass",
        "ssh_askpass",
        "git_proxy_command",
        "git_allow_protocol",
        "git_protocol_from_user",
    } & {key.casefold() for key in environment}
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_security_sensitive_git_callers_use_the_shared_execution_boundary() -> None:
    def direct_execution_calls(tree: ast.AST) -> list[tuple[int, str]]:
        subprocess_execution = {
            "Popen",
            "call",
            "check_call",
            "check_output",
            "getoutput",
            "getstatusoutput",
            "run",
        }
        subprocess_aliases = {"subprocess"}
        os_aliases = {"os"}
        imported_calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "subprocess":
                        subprocess_aliases.add(alias.asname or alias.name)
                    elif alias.name == "os":
                        os_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                imported_calls.update(
                    alias.asname or alias.name for alias in node.names if alias.name in subprocess_execution
                )
            elif isinstance(node, ast.ImportFrom) and node.module == "os":
                imported_calls.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in {"system", "popen"}
                    or alias.name.startswith("exec")
                    or alias.name.startswith("spawn")
                )

        calls: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in imported_calls:
                calls.append((node.lineno, node.func.id))
                continue
            if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
                continue
            owner = node.func.value.id
            name = node.func.attr
            if (owner in subprocess_aliases and name in subprocess_execution) or (
                owner in os_aliases
                and (name in {"system", "popen"} or name.startswith("exec") or name.startswith("spawn"))
            ):
                calls.append((node.lineno, f"{owner}.{name}"))
        return calls

    repository_root = Path(__file__).resolve().parents[3]
    for relative in (
        "research_system/owner_authority.py",
        "research_system/store/binding_repair.py",
        "research_system/methods/pack.py",
        "research_system/assurance/runner.py",
        "tools/verify_w11_materialization.py",
    ):
        tree = ast.parse((repository_root / relative).read_text(encoding="utf-8"), filename=relative)
        direct_calls = direct_execution_calls(tree)
        assert direct_calls == [], f"{relative} bypasses run_git: {direct_calls}"

    evidence_relative = "research_system/evidence/wp64_real_a8.py"
    evidence_tree = ast.parse(
        (repository_root / evidence_relative).read_text(encoding="utf-8"),
        filename=evidence_relative,
    )
    subprocess_calls = direct_execution_calls(evidence_tree)
    assert len(subprocess_calls) == 1
    assert subprocess_calls[0][1] == "subprocess.run"
    enclosing = next(
        node
        for node in ast.walk(evidence_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_fresh_process_binding_load"
    )
    assert any(isinstance(node, ast.Call) and node.lineno == subprocess_calls[0][0] for node in ast.walk(enclosing))


def test_shared_git_runner_captures_timeout_and_explicit_local_config_neutralization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def capture_run(arguments, **kwargs):
        captured["arguments"] = arguments
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(git_execution_module.subprocess, "run", capture_run)
    completed = run_git(tmp_path, "-c", "core.hooksPath=hostile", "rev-parse", "HEAD", timeout=37)

    arguments = captured["arguments"]
    assert isinstance(arguments, list)
    config_values = [arguments[index + 1] for index, value in enumerate(arguments[:-1]) if value == "-c"]
    assert {
        "core.fsmonitor=false",
        "core.untrackedCache=false",
        f"core.worktree={tmp_path}",
        "core.bare=false",
        f"core.attributesFile={os.devnull}",
        f"core.hooksPath={os.devnull}",
        "core.pager=",
        "diff.external=",
        "core.askPass=",
        "credential.helper=",
        "credential.interactive=never",
        "core.sshCommand=",
        "core.gitProxy=",
        "protocol.ext.allow=never",
        "protocol.file.allow=never",
    } <= set(config_values)
    assert arguments.index("core.hooksPath=hostile") < arguments.index(f"core.hooksPath={os.devnull}")
    assert captured["timeout"] == 37
    assert captured["shell"] is False
    assert completed.stdout == "ok\n"


def test_shared_git_blob_identity_matches_git_object_format() -> None:
    assert git_blob_sha1(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert git_blob_sha1(b"test content\n") == "d670460b4b4aece5915caf5c68d12f560a9fe3e4"


def test_shared_git_runner_disables_repository_local_clean_filters(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    sentinel = tmp_path / "filter-invoked"
    filter_script = tmp_path / "hostile_filter.py"
    filter_script.write_text(
        "import pathlib, sys\n"
        f"pathlib.Path({str(sentinel)!r}).write_text('invoked', encoding='utf-8')\n"
        "sys.stdout.buffer.write(sys.stdin.buffer.read())\n",
        encoding="utf-8",
    )
    (root / ".gitattributes").write_text(f"{SPEC_PATH.as_posix()} filter=hostile\n", encoding="utf-8")
    python = str(Path(sys.executable).resolve()).replace("\\", "/")
    script = str(filter_script.resolve()).replace("\\", "/")
    _git(root, "config", "filter.hostile.clean", f'"{python}" "{script}"')
    raw = (root / SPEC_PATH).read_bytes()

    completed = run_git(
        root,
        "hash-object",
        "--path",
        SPEC_PATH.as_posix(),
        "--stdin",
        input=raw,
        text=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.decode("ascii").strip() == git_blob_sha1(raw)
    assert not sentinel.exists()


def test_assurance_git_reader_passes_extended_blob_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def capture_run_git(repository_root, *arguments, **kwargs):
        captured["repository_root"] = repository_root
        captured["arguments"] = arguments
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout=b"blob", stderr=b"")

    monkeypatch.setattr(assurance_runner, "run_git", capture_run_git)
    reader = assurance_runner._GitObjectReader(tmp_path)

    assert reader._run("cat-file", "blob", "a" * 40) == b"blob"
    assert captured["timeout"] == 30


def test_wp64_git_failure_preserves_bounded_stderr_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        wp64_real_a8,
        "run_git",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=128,
            stdout=b"",
            stderr=b"fatal: exact candidate object is unavailable\n",
        ),
    )

    with pytest.raises(wp64_real_a8.EvidenceHarnessError, match="exact candidate object is unavailable"):
        wp64_real_a8._git_bytes(tmp_path, "rev-parse", "HEAD")


def test_shared_git_runner_ignores_hostile_repository_config_and_process_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    expected = _git(root, "rev-parse", "HEAD")
    hostile_config = tmp_path / "hostile.gitconfig"
    hostile_config.write_text("[alias]\nrev-parse = !exit 19\n", encoding="utf-8")
    for key, value in {
        "gIt_DiR": str(tmp_path / "foreign.git"),
        "Git_Config": str(hostile_config),
        "GIT_EXEC_PATH": str(tmp_path / "hostile-exec"),
        "Git_Ssh_Command": "exit 23",
        "GIT_ASKPASS": str(tmp_path / "hostile-askpass"),
        "GIT_PROXY_COMMAND": "exit 29",
    }.items():
        monkeypatch.setenv(key, value)

    completed = run_git(root, "rev-parse", "HEAD")

    assert completed.returncode == 0
    assert completed.stdout.strip() == expected


def test_evidence_and_w11_git_paths_share_hostile_environment_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    expected = _git(root, "rev-parse", "HEAD")
    hostile_config = tmp_path / "hostile.gitconfig"
    hostile_config.write_text("[alias]\nrev-parse = !exit 31\n", encoding="utf-8")
    monkeypatch.setenv("PaTh", str(tmp_path / "hostile-bin"))
    monkeypatch.setenv("gIt_DiR", str(tmp_path / "foreign.git"))
    monkeypatch.setenv("Git_Config", str(hostile_config))
    monkeypatch.setenv("GIT_EXEC_PATH", str(tmp_path / "hostile-exec"))

    assert wp64_real_a8._git(root, "rev-parse", "HEAD") == expected
    assert w11_materialization._git(root, "rev-parse", "HEAD") == expected


def test_raw_registration_hostile_git_environment_cannot_publish_wrong_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    control = tmp_path / "control"
    control.mkdir()
    publication = _publication(root, SPEC_PATH, "spec_operator_source")
    publication = replace(publication, source_git_blob="0" * 40)
    monkeypatch.setenv("gIt_DiR", str(tmp_path / "foreign.git"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "hostile")

    with pytest.raises(ConfigurationError, match="exact committed Git blob"):
        prepare_registered_raw_content(
            repository_root=root,
            publication=publication,
            registration=_registration("spec_operator_source"),
            control_root=control,
        )

    assert not (control / publication.destination_relative_path).exists()


@pytest.mark.parametrize(
    ("source", "document_type"),
    ((SPEC_PATH, "methods_asset"), (ASSET_PATH, "spec_operator_source")),
)
def test_raw_registration_rejects_document_type_that_does_not_match_source_path(
    tmp_path: Path,
    source: Path,
    document_type: str,
) -> None:
    root = _repository(tmp_path)
    control = tmp_path / "control"
    control.mkdir()

    with pytest.raises(ConfigurationError, match="does not match its source path"):
        prepare_registered_raw_content(
            repository_root=root,
            publication=_publication(root, source, document_type),
            registration=_registration(document_type),
            control_root=control,
        )


def test_raw_registration_hashes_the_captured_bytes_not_a_second_path_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    control = tmp_path / "control"
    control.mkdir()
    publication = _publication(root, SPEC_PATH, "spec_operator_source")
    derived_artefact_id = registration_module.spec_brief_input_artefact_id(
        publication.source_relative_path,
        publication.content_sha256,
    )
    publication = replace(
        publication,
        destination_relative_path=f"methods/content/spec-flow/{derived_artefact_id}.md",
    )
    registration = _registration("spec_operator_source")
    registration = replace(
        registration,
        artefact_id=derived_artefact_id,
        manifest={**registration.manifest, "artefact_id": derived_artefact_id},
    )
    original_run_git = registration_module.run_git
    replaced: list[tuple[str, ...]] = []

    def replace_after_capture(repository_root, *arguments, **kwargs):
        if arguments[:1] == ("hash-object",):
            (root / SPEC_PATH).write_bytes(b"changed after capture\n")
            replaced.append(arguments)
        return original_run_git(repository_root, *arguments, **kwargs)

    monkeypatch.setattr(registration_module, "run_git", replace_after_capture)
    prepared = prepare_registered_raw_content(
        repository_root=root,
        publication=publication,
        registration=registration,
        control_root=control,
    )

    assert replaced, "the hash-object capture hook was not exercised"
    assert prepared.raw_bytes == b"# spec-01-assay-brief-v1.1.0.md\n"
    assert (root / SPEC_PATH).read_bytes() == b"changed after capture\n"


def test_candidate_document_write_failure_removes_the_partial_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = CandidateDocumentStore(tmp_path)

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(registration_module.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        store.write(ARTEFACT_ID, b"partial")

    assert not (tmp_path / store.relative_path(ARTEFACT_ID)).exists()
