# Research context: docs/plans/agentic-research-system/reviews/wp9-3-1b-review-649d0698-2026-11-10.md (P-082 item 5)
# Purpose: the WP9.3-1b reviewer's asserting probes. Each runs on scratch stores and repositories under tmp_path, or on
# pure functions, and asserts what the code does at 649d0698. A passing probe confirms the claim or finding it names.
"""Reviewer probes for WP9.3-1b at ``649d0698``: M-1's closure and soundness, the other CLI writers, M-2's edges, the
tools' output guards, the builder's schema gap, and the D-4 census."""

from __future__ import annotations

import ast
import hashlib
import os
import random
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
from research_system.legacy.inventory import refuse_tool_output, reproduce_light_inventory  # noqa: E402
from research_system.legacy.preparers import check_resegmentation, inventory_rows  # noqa: E402
from research_system.legacy.segmentation import SegmentationError, resolve_first_anchor_after, segment  # noqa: E402
from research_system.store.current_binding import CURRENT_BINDING_RELATIVE_PATH  # noqa: E402

UNLOADABLE = "ars submit refused: the store has a current binding this checkout cannot load"
RESOLUTION = "W9 inventory region resolution differs from the first anchor after its after_line"
UNRESOLVABLE = "W9 inventory region cannot be resolved"


# --- M-1 ----------------------------------------------------------------------------------------------------------------


def _named(tmp_path: Path, monkeypatch) -> tuple[SimpleNamespace, Path]:
    """A scratch control root and a scratch foundation naming it. No committed foundation is read."""
    import yaml

    control = tmp_path / "control"
    control.mkdir(parents=True)
    foundation = tmp_path / "repository" / ".research-system" / "config" / "foundation.yaml"
    foundation.parent.mkdir(parents=True)
    foundation.write_text(
        yaml.safe_dump({"project_id": "tdl", "store_identity": "a" * 64, "control_root": str(control)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: foundation)
    return SimpleNamespace(project_id="tdl", store_identity="a" * 64, control_root=control), control


@pytest.mark.parametrize("pointer", ["empty-object", "garbage", "directory"])
def test_m1_unstubbed_load_failures_refuse(tmp_path: Path, monkeypatch, pointer: str) -> None:
    """The real ``load_current_binding`` (not a stub): any failure on a named store with a pointer refuses."""
    binding, control = _named(tmp_path, monkeypatch)
    path = control / CURRENT_BINDING_RELATIVE_PATH
    path.parent.mkdir(parents=True)
    if pointer == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"{}" if pointer == "empty-object" else b"\x00not json")
    with pytest.raises(ConfigurationError, match=UNLOADABLE):
        cli._foundation_binding_check(binding)


def test_m1_a_non_ars_exception_from_the_load_propagates_and_never_skips(tmp_path: Path, monkeypatch) -> None:
    """Only the two ``return None`` branches skip; an unexpected exception type is not caught into a skip."""
    import research_system.store.current_binding as current_binding

    binding, control = _named(tmp_path, monkeypatch)
    (control / CURRENT_BINDING_RELATIVE_PATH).parent.mkdir(parents=True)
    (control / CURRENT_BINDING_RELATIVE_PATH).write_bytes(b"{}")

    def boom(**kwargs: Any) -> None:
        raise KeyError("unexpected")

    monkeypatch.setattr(current_binding, "load_current_binding", boom)
    with pytest.raises(KeyError):
        cli._foundation_binding_check(binding)


def test_m1_the_skip_decision_is_taken_outside_the_lock_and_the_pointer_is_absent_mid_replace(
    tmp_path: Path, monkeypatch
) -> None:
    """Finding m-1 (this review). The binding service replaces the pointer by unlinking it and then publishing the new
    one (``anchor.py`` ``replace_or_recover``). Inside that window, under the advance's own writer lock,
    ``_foundation_binding_check`` reads "no current binding" and returns ``None``: an ``ars submit`` that looks then
    builds ``CommandService(binding_check=None)`` and never rechecks once it takes the lock after the advance."""
    from research_system.store.anchor import DirectoryTransaction
    from research_system.store.writer import CompositeWriterLock

    binding, control = _named(tmp_path, monkeypatch)
    pointer = control / CURRENT_BINDING_RELATIVE_PATH
    pointer.parent.mkdir(parents=True)
    pointer.write_bytes(b'{"binding":"old"}')
    (control / "runtime").mkdir()
    seen: list[tuple[bool, Any]] = []
    original = DirectoryTransaction.adopt_or_publish

    def observed(self, stage, final_name):  # noqa: ANN001
        if final_name == pointer.name:
            seen.append((os.path.lexists(pointer), cli._foundation_binding_check(binding)))
        return original(self, stage, final_name)

    monkeypatch.setattr(DirectoryTransaction, "adopt_or_publish", observed)
    with CompositeWriterLock((control,), {"writer_id": "review-probe"}) as lock:
        lock.locked_root(control).replace_exact_file(
            CURRENT_BINDING_RELATIVE_PATH.as_posix(), b'{"binding":"old"}', b'{"binding":"new"}'
        )
    assert seen == [(False, None)]  # absent mid-replace, and the check reads it as "never bound"
    assert pointer.read_bytes() == b'{"binding":"new"}'


@pytest.mark.slow
def test_m1_closed_ars_submit_from_the_old_checkout_after_the_advance_refuses_through_main(
    tmp_path: Path, monkeypatch
) -> None:
    """The earlier review's M-1 probe, inverted, on the real v1.2 advance fixture, and through ``cli.main``: after the
    advance the old checkout's ``ars submit`` refuses before any ledger or service is built, and the control root is
    byte-identical."""
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_w9_wp9_3_binding_head import _admit, _pin_intent

    service, intent, predecessor_root, _, _ = _pin_intent(tmp_path)
    monkeypatch.setattr(
        cli, "canonical_foundation_path", lambda: predecessor_root / ".research-system" / "config" / "foundation.yaml"
    )
    binding = SimpleNamespace(
        project_id=PROJECT_ID, store_identity=service.store_identity, control_root=service.control_root
    )
    assert callable(cli._foundation_binding_check(binding))
    assert service.advance(intent)["status"] == "advanced"
    with pytest.raises(IntegrityError):
        _admit(service, predecessor_root)

    def tree() -> dict[str, bytes | None]:
        root = service.control_root
        return {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None for p in sorted(root.rglob("*"))}

    def never(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("built after the refusal")

    before = tree()
    monkeypatch.setattr(cli.ControlBinding, "load", lambda path: binding)
    monkeypatch.setattr(cli, "EventLedger", never)
    monkeypatch.setattr(cli, "CommandService", never)
    with pytest.raises(ConfigurationError, match=UNLOADABLE) as refused:
        cli.main(["command", "submit", "--config", str(tmp_path / "c.yaml"), "--command", str(tmp_path / "x.json")])
    assert "current store binding identity is invalid" in str(refused.value)  # the code-root mismatch
    assert tree() == before


# --- N-1 / M-4 (this review): the other production CLI writers ----------------------------------------------------------


def test_only_ars_submit_hands_command_service_a_binding_check() -> None:
    """Finding M-1 of this review. Six production CLI paths build ``CommandService`` with no ``binding_check``, so
    ``_recheck_binding`` (``command/service.py:1890``) is a no-op for them on any store, named and bound or not."""
    tree = ast.parse((REPO_ROOT / "research_system" / "cli.py").read_text(encoding="utf-8"))
    sites: dict[str, bool] = {}
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        for call in [node for node in ast.walk(function) if isinstance(node, ast.Call)]:
            if isinstance(call.func, ast.Name) and call.func.id == "CommandService":
                sites[function.name] = any(keyword.arg == "binding_check" for keyword in call.keywords)
    assert sites == {
        "_store_backup": False,
        "_store_verify_restore": False,
        "_command_submit": True,
        "_brief_runtime": False,
        "_authority_activate_grant": False,
        "_publication_evidence": False,
        "_eval_publish_release": False,
    }


# --- M-2 ----------------------------------------------------------------------------------------------------------------

SOURCE = b"# Title\n\n## a\nlegacy text a\n\n## b\nlegacy text b\n\n## c\nlegacy text c\n"


def _hash_line(data: bytes, number: int) -> str:
    lines = data.split(b"\n")
    return hashlib.sha256(lines[number - 1] + (b"\n" if number < len(lines) else b"")).hexdigest()


def _record(data: bytes, after: Any, first: int, last: int, selector: str = "heading_section", **kw: Any) -> dict:
    """Rows true to the *declared* range, as a hand-builder makes them; only the resolution can be wrong."""
    level = kw.get("level", 2 if selector == "heading_section" else None)
    structural = kw.get("structural", [])
    args: dict[str, Any] = {"region": (first, last), "structural": structural}
    if level is not None:
        args["level"] = level
    segmented = segment(data, selector, **args)
    return {
        "selector_kind": selector,
        "heading_level": level,
        "covered_region": {
            "form": "first_anchor_after",
            "after_line": after,
            "after_line_sha256": (
                _hash_line(data, after) if type(after) is int and 1 <= after <= len(data.split(b"\n")) else None
            ),
            "resolved_first_line": first,
            "resolved_last_line": last,
        },
        "structural_ranges": [{"first_line": a, "last_line": b} for a, b in structural],
        "rows": inventory_rows(segmented, selector),
        "suppressed_anchors": segmented["suppressed_anchors"],
        "file_facts": segmented["file_facts"],
    }


@pytest.mark.parametrize(("first", "last"), [(6, 10), (3, 5), (6, 8)], ids=["skip-first", "stop-early", "both"])
def test_m2_the_three_wrong_resolutions_are_refused(first: int, last: int) -> None:
    check_resegmentation(SOURCE, _record(SOURCE, 1, 3, 10))  # control: the true resolution is admitted
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(SOURCE, _record(SOURCE, 1, first, last))


def test_m2_edges_last_line_no_anchor_and_crlf_bom() -> None:
    with pytest.raises(IntegrityError, match=f"{UNRESOLVABLE}: no anchor follows line 10"):
        check_resegmentation(SOURCE, _record(SOURCE, 10, 10, 10))
    with pytest.raises(IntegrityError, match=f"{UNRESOLVABLE}: no anchor follows line 9"):
        check_resegmentation(SOURCE, _record(SOURCE, 9, 10, 10))
    crlf = b"\xef\xbb\xbf" + SOURCE.replace(b"\n", b"\r\n")
    assert resolve_first_anchor_after(crlf, "heading_section", 1, level=2) == (3, 10)
    check_resegmentation(crlf, _record(crlf, 1, 3, 10))
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(crlf, _record(crlf, 1, 6, 10))
    # No final terminator: the last line is still line 10.
    bare = SOURCE.rstrip(b"\n")
    assert resolve_first_anchor_after(bare, "heading_section", 4, level=2) == (6, 10)


@pytest.mark.parametrize("after", [True, False, "1", 1.0, None, 2**70])
def test_m2_a_non_integer_or_huge_after_line_is_refused(after: Any) -> None:
    with pytest.raises(IntegrityError):
        check_resegmentation(SOURCE, _record(SOURCE, after, 3, 10))


def test_m2_suppression_and_level_3_sections() -> None:
    assert resolve_first_anchor_after(SOURCE, "heading_section", 1, level=2, structural=[(3, 7)]) == (9, 10)
    check_resegmentation(SOURCE, _record(SOURCE, 1, 9, 10, structural=[(3, 7)]))
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(SOURCE, _record(SOURCE, 1, 6, 10, structural=[(3, 7)]))
    nested = b"# T\n## a\n### a1\nx\n### a2\ny\n## b\n### b1\nz\n"
    assert resolve_first_anchor_after(nested, "heading_section", 3, level=3) == (5, 9)


@pytest.mark.parametrize("selector", ["tracker_task_row", "working_note_entry", "log_frontmatter", "conventions_unit"])
def test_m2_a_fixed_region_selector_cannot_carry_a_first_anchor_after_form(selector: str) -> None:
    with pytest.raises(SegmentationError, match="takes no declared region"):
        resolve_first_anchor_after(SOURCE, selector, 1)


def test_m2_the_digit_heading_reading_departs_from_the_contracts_anchor_word() -> None:
    """Finding m-2 (this review). Contract §3 calls only a dated level-2/3 heading an anchor; a digit heading that fails
    the grammar is a "non-anchor heading" that opens a blocker block. The resolver counts it as the first anchor."""
    data = b"# Log\n\n## 2026/01 x\ntext\n\n## 2026-01-02 y\ntext\n"
    assert resolve_first_anchor_after(data, "computational_log_entry", 1) == (3, 7)  # the literal word gives (6, 7)
    with pytest.raises(IntegrityError, match=RESOLUTION):
        check_resegmentation(data, _record(data, 1, 6, 7, "computational_log_entry"))


def test_m2_heading_section_prose_between_the_named_line_and_the_first_anchor_is_outside_the_region() -> None:
    """Info i-3 (this review): an unaddressed-region blocker between ``after_line`` and the first anchor is not in the
    resolved region, by the form's definition, as with a line range; only anchors are protected from dropping."""
    data = b"# T\n\nloose prose\n\n## a\nx\n"
    whole = segment(data, "heading_section", level=2, region=(1, 6))["rows"]
    assert [(r["start_line"], r["blocker_reason"]) for r in whole if r["row_kind"] == "blocker"] == [
        (1, "unaddressed_region"),
        (3, "unaddressed_region"),
    ]
    first, last = resolve_first_anchor_after(data, "heading_section", 1, level=2)
    assert (first, last) == (5, 6)
    region = segment(data, "heading_section", level=2, region=(first, last))["rows"]
    assert not [r for r in region if r["row_kind"] == "blocker"]


def _generated(rng: random.Random) -> bytes:
    pieces = [
        b"# T\n",
        b"## a\n",
        b"## a\n",
        b"### s\n",
        b"### 3 things\n",
        b"## 2026-01-02 x\n",
        b"## 2026-01-02 x\n",
        b"### 2026-02 y\n",
        b"## 2026/01 z\n",
        b"### 9z\n",
        b"#### 2026-03-01 deep\n",
        b"text\n",
        b"\n",
        b"---\n",
        b"\xff\xfe bad\n",
        b"## \xff bad\n",
    ]
    ending = rng.choice([b"", b"\r"])
    body = b"".join(rng.choice(pieces).replace(b"\n", ending + b"\n") for _ in range(rng.randint(1, 18)))
    if rng.random() < 0.2:
        body = body.rstrip(b"\r\n")
    return (b"\xef\xbb\xbf" + body) if rng.random() < 0.1 else body


def test_m2_independent_property_no_anchor_row_of_the_whole_file_after_the_named_line_drops_out() -> None:
    """Independent of the PR's property test: segment the whole file, then require every item or anchor blocker
    (``unparseable_anchor``/``duplicate_anchor``) starting after ``after_line`` to start a row of the resolved region,
    with the same bytes; and LR-011 to admit exactly the resolution and refuse first-1/first+1/last-1. Seed 20261111."""
    rng = random.Random(20261111)
    checked = 0
    for _ in range(3000):
        data = _generated(rng)
        count = len(data.split(b"\n")) - (1 if data.endswith(b"\n") else 0)
        if count < 2:
            continue
        after = rng.randint(1, count)
        for selector, extra in (("heading_section", {"level": rng.choice([2, 3])}), ("computational_log_entry", {})):
            structural: list[tuple[int, int]] = []
            if selector == "heading_section" and rng.random() < 0.3:
                a = rng.randint(1, count)
                structural = [(a, rng.randint(a, count))]
            try:
                first, last = resolve_first_anchor_after(data, selector, after, structural=structural, **extra)
            except SegmentationError as exc:
                assert str(exc) == f"no anchor follows line {after}"
                continue
            kw = {**extra, "structural": structural}
            whole = segment(data, selector, region=(1, count), **kw)["rows"]
            region = {r["start_line"]: r for r in segment(data, selector, region=(first, last), **kw)["rows"]}
            for row in whole:
                anchor_row = row["row_kind"] == "item" or row["blocker_reason"] in (
                    "unparseable_anchor",
                    "duplicate_anchor",
                )
                if anchor_row and row["start_line"] > after:
                    kept = region.get(row["start_line"])
                    assert kept is not None, (data, selector, after, row)
                    assert kept["raw_row_sha256"] == row["raw_row_sha256"], (data, selector, after, row)
            record = _record(data, after, first, last, selector, structural=structural, level=extra.get("level"))
            check_resegmentation(data, record)
            for bad_first, bad_last in ((first - 1, last), (first + 1, last), (first, last - 1)):
                if after < bad_first <= bad_last <= count and (bad_first, bad_last) != (first, last):
                    with pytest.raises(IntegrityError, match=RESOLUTION):
                        check_resegmentation(
                            data,
                            _record(
                                data,
                                after,
                                bad_first,
                                bad_last,
                                selector,
                                structural=structural,
                                level=extra.get("level"),
                            ),
                        )
            checked += 1
    assert checked > 1000


# --- M-3: the tools' output guards --------------------------------------------------------------------------------------


def test_m3_reproduce_writes_into_a_vault_it_is_never_told_about(tmp_path: Path, capsys) -> None:
    """Finding m-3 (this review). Note §12: every tool refuses an output under the vault. ``reproduce`` passes
    ``vault_root=None`` and has no ``--vault-root``, so it never refuses one; ``build`` refuses only when given one."""
    data = b"---\na: 1\n---\nbody\n"
    segmented = segment(data, "log_frontmatter")
    record = {
        "selector_kind": "log_frontmatter",
        "heading_level": None,
        "covered_region": {"form": "fixed_by_selector"},
        "structural_ranges": [],
        "source_identity": {
            "identity_kind": "untracked_file",
            "sha256": hashlib.sha256(data).hexdigest(),
            "byte_length": len(data),
        },
        "rows": inventory_rows(segmented, "log_frontmatter"),
        "suppressed_anchors": [],
        "file_facts": segmented["file_facts"],
    }
    assert reproduce_light_inventory(record, data)["reproduced"] is True
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "copy.md").write_bytes(data)
    (inputs / "inventory.json").write_text(__import__("json").dumps(record), encoding="utf-8")
    vault = tmp_path / "TDA-Research" / "05-Daily"
    vault.mkdir(parents=True)
    out = vault / "report.json"
    args = ["legacy", "inventory", "reproduce", "--inventory", str(inputs / "inventory.json")]
    assert cli.main([*args, "--frozen-copy", str(inputs / "copy.md"), "--output", str(out)]) == 0
    assert out.exists()
    capsys.readouterr()


@pytest.mark.skipif(os.name != "nt", reason="directory junctions are Windows-only")
def test_m3_an_output_through_the_repositorys_vault_junction_passes_both_guards(tmp_path: Path) -> None:
    """The repository's ``vault/`` junction (CLAUDE.md) resolves out of the repository, so without ``--vault-root`` an
    output named under it is neither "inside the repository it reads" nor "under the vault"."""
    repository = tmp_path / "repo"
    repository.mkdir()
    real_vault = tmp_path / "real-vault"
    real_vault.mkdir()
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(repository / "vault"), str(real_vault)], check=True, capture_output=True
    )
    resolved = refuse_tool_output(repository / "vault" / "x.json", repository_root=repository, vault_root=None)
    assert resolved == (real_vault / "x.json").resolve()
    with pytest.raises(IntegrityError, match="under the vault"):
        refuse_tool_output(repository / "vault" / "x.json", repository_root=repository, vault_root=real_vault)


def test_m3_a_git_head_starting_with_a_dash_reaches_git_as_an_option(tmp_path: Path) -> None:
    """Info i-2 (this review). ``inventory build`` hands ``--git-head`` to the reader unchecked, and the reader passes
    it to ``git show <head>:<path>``. A value starting with ``-`` is parsed by Git as an option, here ``--output``,
    which makes Git write a file inside the repository the tool reads. PR #428 checks the inventory's ``git_blob`` the
    same way; ``--git-head`` gets no such check."""
    from research_system.legacy.reader import LegacyReader, ReadRefused

    repository = tmp_path / "repo"
    repository.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True)

    git("init", "-q")
    (repository / "a.md").write_bytes(b"# a\n")
    git("add", "a.md")
    git("-c", "user.name=r", "-c", "user.email=r@example.invalid", "commit", "-q", "-m", "a")
    reader = LegacyReader(repository_root=repository, git_head="--output=written-by-git")
    with pytest.raises(ReadRefused, match="git show failed"):
        reader._git_object(reader.git_head, "a.md")
    # The same argument, as the reader builds it: Git parses it as its --output option and tries to open the file. On
    # Windows a ':' is not allowed in that name, so Git fails here; on POSIX it writes "written-by-git:a.md".
    shown = subprocess.run(
        ["git", "-C", str(repository), "show", f"{reader.git_head}:a.md"], capture_output=True, text=True
    )
    assert (
        "could not open 'written-by-git:a.md' for writing" in shown.stderr
        or (repository / "written-by-git:a.md").exists()
    )


def test_m3_the_tool_handlers_reference_no_store_binding() -> None:
    """F-4 holds vacuously for the tools: neither handler names a ledger, a binding loader or a Gate 6 refusal."""
    tree = ast.parse((REPO_ROOT / "research_system" / "cli.py").read_text(encoding="utf-8"))
    handlers = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for name in ("_legacy_inventory_build", "_legacy_inventory_reproduce"):
        names = {n.id for n in ast.walk(handlers[name]) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(handlers[name]) if isinstance(n, ast.Attribute)}
        assert not names & {
            "EventLedger",
            "ControlBinding",
            "load_current_binding",
            "_legacy_current_binding",
            "_verified_ledger",
            "LegacyRuntime",
            "CommandService",
            "refuse_gate6_store",
        }, name


@pytest.mark.parametrize(
    ("selector", "kwargs"),
    [
        ("computational_log_entry", {"heading_level": 2}),
        ("computational_log_entry", {"structural_ranges": [(1, 1)]}),
    ],
    ids=["log-with-level", "log-with-structural"],
)
def test_m3_the_builder_hands_out_a_proposal_lr_011_refuses_at_its_schema(
    tmp_path: Path, monkeypatch, selector: str, kwargs: dict
) -> None:
    """Info i-1 (this review). The builder checks its output with ``check_resegmentation`` only, not the record schema,
    so its docstring's "a proposal it cannot admit is never handed out" does not hold for a schema refusal."""
    from research_system.legacy.inventory import build_light_inventory
    from tests.research_system.integration.w9_runtime_harness import w9_store

    store = w9_store(tmp_path, monkeypatch)
    sections = store.register("sections.md", role="legacy_coordination")

    def build(**extra: Any) -> dict:
        return build_light_inventory(
            sections,
            reader=store.runtime.reader,
            selector_kind=selector,
            observer_actor_id=store.actors.observer,
            project_id=store.harness.ledger.project_id,
            **extra,
        )

    control = build()
    assert store.submit("ProposeLegacyRecord", store.actors.observer, control["record_id"], 0, control).status == (
        "accepted"
    )
    record = build(**kwargs)  # handed out
    before = store.events()
    with pytest.raises(IntegrityError, match="does not validate against its record schema"):
        store.submit("ProposeLegacyRecord", store.actors.observer, record["record_id"], 0, record)
    assert store.events() == before


# --- D-4 ----------------------------------------------------------------------------------------------------------------


def test_d4_census_and_protected_blobs_are_unchanged() -> None:
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

    head = "649d06986907218662a14562e5e2e617ae2f5c6c"
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
        "tests/research_system/unit/test_schema_registry.py",
    ):
        assert blob(head, path) == blob("0ea4e489", path), path
