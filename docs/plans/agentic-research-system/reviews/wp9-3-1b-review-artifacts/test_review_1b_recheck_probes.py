# Research context: docs/plans/agentic-research-system/reviews/wp9-3-1b-review-649d0698-2026-11-10.md (addendum)
# Purpose: the WP9.3-1b reviewer's re-check probes at 6836b846, after the fixes for the review's M-1, m-1, m-3, i-1
# and i-2. Each runs on scratch stores and repositories under tmp_path, or on pure functions.
"""Re-check probes for WP9.3-1b at ``6836b846``: the controls that replace the first round's confirming probes, the
census's negative control, the six writers' refusals, and what the fixes leave open."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system import cli  # noqa: E402
from research_system.errors import ConfigurationError, IntegrityError  # noqa: E402
from research_system.legacy.inventory import refuse_tool_output  # noqa: E402
from research_system.store.current_binding import CURRENT_BINDING_RELATIVE_PATH  # noqa: E402

UNLOADABLE = "refused: the store has a current binding this checkout cannot load"


def _named(tmp_path: Path, monkeypatch) -> tuple[SimpleNamespace, Path]:
    """A scratch control root and a scratch foundation naming it. No committed foundation is read."""
    import yaml

    control = tmp_path / "control"
    (control / "runtime").mkdir(parents=True)
    foundation = tmp_path / "repository" / ".research-system" / "config" / "foundation.yaml"
    foundation.parent.mkdir(parents=True)
    foundation.write_text(
        yaml.safe_dump({"project_id": "tdl", "store_identity": "a" * 64, "control_root": str(control)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: foundation)
    return SimpleNamespace(project_id="tdl", store_identity="a" * 64, control_root=control), control


def _pointer(control: Path, data: bytes | None) -> Path:
    path = control / CURRENT_BINDING_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.unlink(missing_ok=True)
    else:
        path.write_bytes(data)
    return path


# --- m-1: the in-lock decision ------------------------------------------------------------------------------------------


def test_m1_control_a_check_taken_mid_replace_is_a_check_and_refuses_once_the_new_pointer_is_published(
    tmp_path: Path, monkeypatch
) -> None:
    """The first round's probe, inverted: mid-replace the pointer is still absent, but the check returned is callable,
    and called after the publish (as it would be under the submit's lock) it loads the new pointer and refuses."""
    from research_system.store.anchor import DirectoryTransaction
    from research_system.store.writer import CompositeWriterLock

    binding, control = _named(tmp_path, monkeypatch)
    pointer = _pointer(control, b"not a binding")
    taken: list[tuple[bool, Any]] = []
    original = DirectoryTransaction.adopt_or_publish

    def observed(self, stage, final_name):  # noqa: ANN001
        if final_name == pointer.name:
            taken.append((os.path.lexists(pointer), cli._foundation_binding_check(binding)))
        return original(self, stage, final_name)

    monkeypatch.setattr(DirectoryTransaction, "adopt_or_publish", observed)
    with CompositeWriterLock((control,), {"writer_id": "review-probe"}) as lock:
        lock.locked_root(control).replace_exact_file(
            CURRENT_BINDING_RELATIVE_PATH.as_posix(), b"not a binding", b"still not a binding"
        )
    [(present, check)] = taken
    assert present is False and callable(check)
    with pytest.raises(ConfigurationError, match=UNLOADABLE):
        check()


def test_m1_the_in_lock_decision_refuses_a_pointer_that_appears_and_fails_to_load(tmp_path: Path, monkeypatch) -> None:
    """Absent before binding, present and unloadable under the lock: refused there, by the real loader."""
    binding, control = _named(tmp_path, monkeypatch)
    check = cli._foundation_binding_check(binding)
    assert callable(check)
    assert check() is None  # still absent: the store has no current binding
    _pointer(control, b"{}")
    with pytest.raises(ConfigurationError, match=f"ars submit {UNLOADABLE}"):
        check()


def test_m1_the_in_lock_decision_revalidates_the_pre_bind_binding_and_propagates_its_refusal(
    tmp_path: Path, monkeypatch
) -> None:
    import research_system.store.current_binding as current_binding

    binding, control = _named(tmp_path, monkeypatch)
    _pointer(control, b"{}")
    calls: list[str] = []

    def refuse() -> None:
        calls.append("revalidate")
        raise IntegrityError("current store binding identity is invalid")

    monkeypatch.setattr(current_binding, "load_current_binding", lambda **kwargs: SimpleNamespace(revalidate=refuse))
    check = cli._foundation_binding_check(binding)
    with pytest.raises(IntegrityError, match="identity is invalid"):
        check()
    assert calls == ["revalidate"]


def test_m1_residual_a_binding_loaded_before_binding_whose_pointer_is_gone_under_the_lock_is_not_rechecked(
    tmp_path: Path, monkeypatch
) -> None:
    """Finding n-1 of the addendum. The pre-bind load found a binding; under the lock the pointer is absent, which is
    the state an "absent-final" crash of an advance leaves (``store/anchor.py:2713-2720``). The check returns without
    revalidating: the store reads as never bound, though this very check saw it bound."""
    import research_system.store.current_binding as current_binding

    binding, control = _named(tmp_path, monkeypatch)
    _pointer(control, b"{}")
    calls: list[str] = []
    monkeypatch.setattr(
        current_binding,
        "load_current_binding",
        lambda **kwargs: SimpleNamespace(revalidate=lambda: calls.append("revalidate")),
    )
    check = cli._foundation_binding_check(binding)
    _pointer(control, None)
    assert check() is None
    assert calls == []


# --- M-1: the six writers and the census --------------------------------------------------------------------------------


def _never(*args: Any, **kwargs: Any) -> None:
    raise AssertionError("built or read after the refusal")


@pytest.mark.parametrize(
    ("handler", "command", "args"),
    [
        ("_store_backup", "ars store backup", {"config": "c", "request": "r"}),
        ("_store_verify_restore", "ars store verify-restore", {"config": "c", "command": "x", "receipt": "r"}),
        ("_brief_runtime", "ars brief", {"config": "c"}),
        ("_authority_activate_grant", "ars authority activate-grant", {"config": "c", "request": "r"}),
        ("_eval_publish_release", "ars eval publish-release", {"config": "c", "evaluation_runs": "e"}),
    ],
)
def test_m1_each_cli_writer_refuses_an_unloadable_named_binding_before_it_reads_or_builds(
    tmp_path: Path, monkeypatch, handler: str, command: str, args: dict
) -> None:
    """Through each handler, with the real loader on a scratch named store whose pointer cannot load."""
    binding, control = _named(tmp_path, monkeypatch)
    _pointer(control, b"{}")
    monkeypatch.setattr(cli.ControlBinding, "load", lambda path: binding)
    for name in ("_read_json", "_read_canonical_json", "runtime_schema_registry", "EventLedger", "CommandService"):
        monkeypatch.setattr(cli, name, _never)
    with pytest.raises(ConfigurationError, match=f"{command} {UNLOADABLE}"):
        getattr(cli, handler)(SimpleNamespace(operator_config=None, **args))


def test_m1_each_cli_writer_on_a_never_bound_named_store_gets_a_no_op_check(tmp_path: Path, monkeypatch) -> None:
    """No regression for a store with no current binding: the check returns under the lock and loads nothing."""
    import research_system.store.current_binding as current_binding

    binding, _ = _named(tmp_path, monkeypatch)
    monkeypatch.setattr(current_binding, "load_current_binding", _never)
    for command in ("ars store backup", "ars brief", "ars authority activate-grant", "ars eval publish-release"):
        check = cli._writer_binding_check(binding, command)
        assert callable(check) and check() is None


def _census():
    from tests.research_system.contracts import test_w9_wp9_3_censuses as census

    return census


@pytest.mark.parametrize("mutation", ["removed", "none"])
def test_m1_the_service_census_fails_on_a_production_construction_with_no_binding_check(
    monkeypatch, mutation: str
) -> None:
    """The census's negative control on the real tree: ``_brief_runtime``'s ``binding_check=`` removed, or set to
    ``None``, in an otherwise unchanged ``cli.py``, fails the census naming that site."""
    census = _census()
    cli_source = (REPO_ROOT / "research_system" / "cli.py").read_text(encoding="utf-8")
    start = cli_source.index("def _brief_runtime(")
    end = cli_source.index("\ndef ", start + 1)
    body = cli_source[start:end]
    assert body.count("binding_check=binding_check,") == 1
    replaced = body.replace("binding_check=binding_check,", "" if mutation == "removed" else "binding_check=None,")
    mutated = cli_source[:start] + replaced + cli_source[end:]
    real = list(census._tracked_python())
    monkeypatch.setattr(
        census,
        "_tracked_python",
        lambda: iter([(path, mutated if path == "research_system/cli.py" else text) for path, text in real]),
    )
    unchecked = [site for site in census._service_constructions("research_system/cli.py", mutated) if not site[3]]
    assert [site[1] for site in unchecked] == ["_brief_runtime"]
    with pytest.raises(AssertionError):
        census.test_every_production_command_service_construction_passes_a_binding_check()
    monkeypatch.setattr(census, "_tracked_python", lambda: iter(real))
    census.test_every_production_command_service_construction_passes_a_binding_check()  # control: the real tree passes


def test_m1_census_blind_spot_a_construction_through_partial_is_not_seen() -> None:
    """Info: the census sees calls of the class (or of names, subclasses and attributes bound to it). A construction
    through ``functools.partial`` or a lookup by string is not a call of the class, so it is not seen. None exists in
    production code today."""
    census = _census()
    source = (
        "import functools\n"
        "def f():\n"
        "    make = functools.partial(CommandService, 1)\n"
        "    return make()\n"
        "def g(module):\n"
        "    return getattr(module, 'Command' + 'Service')(1)\n"
    )
    assert census._service_constructions("fixture.py", source) == []


# --- m-3, i-1, i-2: the tools ---------------------------------------------------------------------------------------


def test_m3_control_reproduce_refuses_an_output_under_the_vault_it_is_given(tmp_path: Path, capsys) -> None:
    vault = tmp_path / "TDA-Research"
    (vault / "05-Daily").mkdir(parents=True)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "inventory.json").write_text(json.dumps({"source_identity": {}}), encoding="utf-8")
    (inputs / "copy.md").write_bytes(b"x\n")
    out = vault / "05-Daily" / "report.json"
    args = ["legacy", "inventory", "reproduce", "--inventory", str(inputs / "inventory.json")]
    args += ["--frozen-copy", str(inputs / "copy.md"), "--vault-root", str(vault), "--output", str(out)]
    assert cli.main(args) == 1
    assert "W9 tool output is under the vault" in capsys.readouterr().err
    assert not out.exists()


def test_m3_control_both_tools_require_the_vault_root(capsys) -> None:
    for tool in ("build", "reproduce"):
        with pytest.raises(SystemExit):
            cli.main(["legacy", "inventory", tool, "--output", "x.json"])
        assert "--vault-root" in capsys.readouterr().err
    with pytest.raises(IntegrityError, match="W9 tool output guard needs the vault root"):
        refuse_tool_output(Path("x.json"), repository_root=None, vault_root=None)  # type: ignore[arg-type]


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are Windows-only")
@pytest.mark.parametrize("named_as", ["real-path", "junction-path"])
def test_m3_control_an_output_through_the_repositorys_vault_junction_is_refused(tmp_path: Path, named_as: str) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    real_vault = tmp_path / "real-vault"
    real_vault.mkdir()
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(repository / "vault"), str(real_vault)], check=True, capture_output=True
    )
    vault_root = real_vault if named_as == "real-path" else repository / "vault"
    with pytest.raises(IntegrityError, match="under the vault"):
        refuse_tool_output(repository / "vault" / "x.json", repository_root=repository, vault_root=vault_root)


@pytest.mark.parametrize(
    ("selector", "kwargs", "message"),
    [
        ("computational_log_entry", {"heading_level": 2}, "takes no heading level and no structural ranges"),
        ("computational_log_entry", {"structural_ranges": [(1, 1)]}, "takes no heading level and no structural"),
        ("tracker_task_row", {"heading_level": 1}, "takes no heading level and no structural ranges"),
        ("heading_section", {}, "W9 heading_section inventory declares its heading level"),
    ],
)
def test_i1_control_the_builder_refuses_the_schema_rule_before_any_read(selector: str, kwargs: dict, message: str):
    from research_system.legacy.inventory import build_light_inventory

    reader = SimpleNamespace(read=_never)
    with pytest.raises(IntegrityError, match=message):
        build_light_inventory(
            {}, reader=reader, selector_kind=selector, observer_actor_id="a", project_id="p", **kwargs
        )


@pytest.mark.parametrize("head", ["--output=x", "-p", "HEAD", "a" * 39, "A" * 40, "g" * 40])
def test_i2_control_build_refuses_a_git_head_that_is_not_a_hex_commit_id(
    tmp_path: Path, monkeypatch, capsys, head: str
) -> None:
    import research_system.legacy.reader as reader_module

    monkeypatch.setattr(reader_module, "_git", _never)
    monkeypatch.setattr(reader_module.LegacyReader, "__init__", _never)
    repository = tmp_path / "repo"
    repository.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    (tmp_path / "registration.json").write_text("{}", encoding="utf-8")
    args = ["legacy", "inventory", "build", "--registration", str(tmp_path / "registration.json")]
    args += ["--selector-kind", "tracker_task_row", "--repository-root", str(repository), f"--git-head={head}"]
    args += ["--vault-root", str(vault), "--observer", "a", "--project-id", "p", "--output", str(tmp_path / "o.json")]
    assert cli.main(args) == 1
    assert "W9 inventory build needs --git-head as a lowercase hex commit ID" in capsys.readouterr().err


# --- The real v1.2 advance fixture ---------------------------------------------------------------------------------------


@pytest.mark.slow
def test_m1_after_the_advance_the_old_checkouts_brief_writer_refuses_on_the_real_fixture(
    tmp_path: Path, monkeypatch
) -> None:
    """One of the six writers on the real advance: before it, the old checkout's ``ars brief`` gets a check that
    passes under the lock; after it, the same writer refuses before binding, with the code-root mismatch."""
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_w9_wp9_3_binding_head import _pin_intent

    service, intent, predecessor_root, _, _ = _pin_intent(tmp_path)
    monkeypatch.setattr(
        cli, "canonical_foundation_path", lambda: predecessor_root / ".research-system" / "config" / "foundation.yaml"
    )
    binding = SimpleNamespace(
        project_id=PROJECT_ID, store_identity=service.store_identity, control_root=service.control_root
    )
    before = cli._writer_binding_check(binding, "ars brief")
    before()  # admitted before the advance
    assert service.advance(intent)["status"] == "advanced"
    with pytest.raises(Exception, match="changed during the operation|identity is invalid"):
        before()  # a check taken before the advance refuses under a later lock
    monkeypatch.setattr(cli.ControlBinding, "load", lambda path: binding)
    for name in ("runtime_schema_registry", "EventLedger", "CommandService"):
        monkeypatch.setattr(cli, name, _never)
    with pytest.raises(ConfigurationError, match=f"ars brief {UNLOADABLE}: current store binding identity is invalid"):
        cli._brief_runtime(SimpleNamespace(config=tmp_path / "c.yaml"))


# --- D-4 at the re-checked head ------------------------------------------------------------------------------------------


def test_d4_unchanged_at_6836b846() -> None:
    import hashlib

    from research_system.schema_registry import runtime_schema_registry

    fields = (
        "schema_id",
        "schema_version",
        "command_type",
        "event_type",
        "producer_command_type",
        "policy_action_type",
    )
    bindings = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas").active_bindings()
    encoded = b"".join(b"|".join(str(getattr(b, f) or "").encode() for f in fields) + b"\n" for b in bindings)
    assert len(bindings) == 273
    assert hashlib.sha256(encoded).hexdigest() == "0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712"

    def blob(rev: str, path: str) -> str:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", f"{rev}:{path}"], check=True, capture_output=True, text=True
        ).stdout.strip()

    head = "6836b8467ef855a9f5fa200cf7823c9714885f49"
    assert blob(head, "tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml").startswith("4c895042")
    assert blob(head, "tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py").startswith("559d684a")
    assert blob(head, "tools/w9_segmentation.py").startswith("43e1454d")
    for path in (
        ".research-system",
        "research_system/schema_registry.py",
        "research_system/authority.py",
        "research_system/command",
        "research_system/store",
        "research_system/discovery",
        "research_system/projection",
        "research_system/legacy/segmentation.py",
        "research_system/legacy/preparers.py",
        "research_system/legacy/replay",
        "tests/research_system/unit/test_schema_registry.py",
    ):
        expected = "0ea4e489" if not path.startswith("research_system/legacy") else "649d0698"
        assert blob(head, path) == blob(expected, path), path
    changed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "649d0698", head, "--", "research_system"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert changed == ["research_system/cli.py", "research_system/legacy/inventory.py"]
