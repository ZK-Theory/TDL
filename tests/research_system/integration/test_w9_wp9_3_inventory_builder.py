# Research context: docs/plans/agentic-research-system/03-decisions-and-open-questions.md (P-082 item 5; review M-3)
# Purpose: the light-inventory builder, its reproduction mode and the `ars legacy inventory` tools (WP9.3 note §12, §13).
"""WP9.3-1b: the builder and reproduction mode end to end, and the tools' write-nothing rules (note §12.1, §13, §17)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from research_system import cli
from research_system.errors import IntegrityError
from research_system.legacy.inventory import build_light_inventory, refuse_tool_output, reproduce_light_inventory
from research_system.legacy.preparers import check_resegmentation, inventory_rows
from research_system.legacy.segmentation import segment
from tests.research_system.integration.w9_runtime_harness import SECTIONS, TRACKER, W9Store, w9_store

RESOLUTION = "W9 inventory region resolution differs from the first anchor after its after_line"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> W9Store:
    return w9_store(tmp_path, monkeypatch)


def _build(store: W9Store, registration: dict[str, Any], selector: str, **kwargs: Any) -> dict[str, Any]:
    return build_light_inventory(
        registration,
        reader=store.runtime.reader,
        selector_kind=selector,
        observer_actor_id=store.actors.observer,
        project_id=store.harness.ledger.project_id,
        **kwargs,
    )


def _propose(store: W9Store, record: dict[str, Any]) -> Any:
    return store.submit("ProposeLegacyRecord", store.actors.observer, record["record_id"], 0, record)


def _worktree_bytes(root: Path) -> dict[str, bytes | None]:
    """Every file and directory under ``root`` except ``.git``, whose index Git itself may refresh."""
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
        if ".git" not in path.relative_to(root).parts
    }


# --- Build mode (note §8.3, §12.1) -------------------------------------------------------------------------------------


def test_a_built_first_anchor_after_inventory_is_admitted_at_lr_011(store: W9Store) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    record = _build(store, sections, "heading_section", heading_level=2, region=("first_anchor_after", 1))
    assert record["covered_region"]["resolved_first_line"] == 3
    assert record["covered_region"]["resolved_last_line"] == 10
    assert [row["anchor_text"] for row in record["rows"] if row["row_kind"] == "item"] == ["a", "b", "c"]
    assert not {"created_by_actor_id", "created_at", "content_hash"} & set(record)
    assert _propose(store, record).status == "accepted"


def test_a_built_line_range_inventory_records_its_anchor_line_hashes_and_is_admitted(store: W9Store) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    record = _build(store, sections, "heading_section", heading_level=2, region=("line_range", 6, 10))
    assert record["covered_region"]["anchor_line_sha256s"] == [row["anchor_line_sha256"] for row in record["rows"]]
    assert [row["anchor_text"] for row in record["rows"] if row["row_kind"] == "item"] == ["b", "c"]
    assert _propose(store, record).status == "accepted"


def test_a_built_fixed_region_inventory_matches_the_hand_built_one_and_is_admitted(store: W9Store) -> None:
    tracker = store.register("tracker.md", role="legacy_coordination")
    record = _build(store, tracker, "tracker_task_row")
    hand = store.inventory_payload(tracker, TRACKER)
    ignored = {"record_id", "independent_reproduction_ref", "read_started_at", "read_ended_at"}
    assert {k: v for k, v in record.items() if k not in ignored} == {k: v for k, v in hand.items() if k not in ignored}
    assert _propose(store, record).status == "accepted"


def test_a_wrong_resolution_is_refused_through_submit_and_appends_nothing(store: W9Store) -> None:
    """Review M-2 through the runtime: rows true to the declared range, the after_line hash right, items dropped."""
    sections = store.register("sections.md", role="legacy_coordination")
    record = _build(store, sections, "heading_section", heading_level=2, region=("first_anchor_after", 1))
    segmented = segment(SECTIONS, "heading_section", level=2, region=(6, 10))
    record["covered_region"]["resolved_first_line"] = 6
    record["rows"] = inventory_rows(segmented, "heading_section")
    record["suppressed_anchors"] = segmented["suppressed_anchors"]
    before = store.events()
    with pytest.raises(IntegrityError, match=RESOLUTION):
        _propose(store, record)
    assert store.events() == before


@pytest.mark.parametrize(
    ("selector", "kwargs", "message"),
    [
        ("heading_section", {"heading_level": 2}, "W9 heading_section inventory declares its covered region"),
        ("tracker_task_row", {"region": ("line_range", 1, 3)}, "W9 tracker_task_row inventory has a fixed region"),
        ("heading_section", {"heading_level": 2, "region": ("first_anchor_after", 9)}, "no anchor follows line 9"),
        ("heading_section", {"heading_level": 2, "region": ("diagonal", 1)}, "W9 inventory region is not a known form"),
    ],
)
def test_the_builder_refuses_a_region_the_selector_cannot_take(
    store: W9Store, selector: str, kwargs: dict[str, Any], message: str
) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    with pytest.raises(IntegrityError, match=message):
        _build(store, sections, selector, **kwargs)


def test_the_builder_requires_a_frozen_copy_ref_exactly_for_untracked_and_vault_sources(store: W9Store) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    with pytest.raises(IntegrityError, match="W9 source of this kind carries no frozen copy"):
        _build(store, sections, "heading_section", heading_level=2, region=("line_range", 1, 10), frozen_copy_ref={})
    path = store.repo / "notes" / "untracked.md"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(SECTIONS)
    untracked = store.register("notes/untracked.md", kind="untracked_file", role="legacy_coordination")
    with pytest.raises(IntegrityError, match="W9 untracked or vault source needs its frozen copy ref"):
        _build(store, untracked, "heading_section", heading_level=2, region=("line_range", 1, 10))
    ref = store.frozen_copy(SECTIONS, "sections.md")
    record = _build(
        store, untracked, "heading_section", heading_level=2, region=("line_range", 1, 10), frozen_copy_ref=ref
    )
    assert record["source_identity"]["frozen_copy_ref"] == ref
    assert _propose(store, record).status == "accepted"


def test_the_builder_computes_no_observation_id_and_no_ownership_list() -> None:
    """Note §12.1: the observation ID needs the store's projection; the ownership list is a batch's (WP9.3-2)."""
    import ast
    import inspect

    import research_system.legacy.inventory as inventory

    names = {node.id for node in ast.walk(ast.parse(inspect.getsource(inventory))) if isinstance(node, ast.Name)}
    assert not {"observation_record_id", "observation_id", "EventLedger", "LegacyRuntime"} & names


# --- Reproduction mode (note §12.1; LR-013) -----------------------------------------------------------------------------


def test_reproduction_reports_equality_differences_and_a_wrong_resolution(store: W9Store) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    record = _build(store, sections, "heading_section", heading_level=2, region=("first_anchor_after", 1))
    assert reproduce_light_inventory(record, SECTIONS)["reproduced"] is True
    changed = deepcopy(record)
    changed["rows"][1]["anchor_text"] = "not b"
    report = reproduce_light_inventory(changed, SECTIONS)
    assert report["reproduced"] is False and report["rows"]["differing_ordinals"] == [changed["rows"][1]["row_ordinal"]]
    wrong = deepcopy(record)
    wrong["covered_region"]["resolved_first_line"] = 6
    report = reproduce_light_inventory(wrong, SECTIONS)
    assert report["reproduced"] is False and report["region"]["resolution_equal"] is False
    # PR #428 review: a boolean after_line with a null hash would have hashed "equal" and resolved as line 1.
    boolean = deepcopy(record)
    boolean["covered_region"].update(after_line=True, after_line_sha256=None)
    report = reproduce_light_inventory(boolean, SECTIONS)
    assert report["reproduced"] is False and report["region"]["resolution_equal"] is False
    with pytest.raises(IntegrityError, match="W9 reproduction bytes are not the inventory's source"):
        reproduce_light_inventory(record, SECTIONS + b"x")


# --- The tools (note §12, §13; §17 "Tools write nothing") ---------------------------------------------------------------


def _write_json(path: Path, value: Any) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _build_args(store: W9Store, registration: Path, output: Path) -> list[str]:
    return [
        "legacy",
        "inventory",
        "build",
        "--registration",
        str(registration),
        "--selector-kind",
        "heading_section",
        "--heading-level",
        "2",
        "--after-line",
        "1",
        "--repository-root",
        str(store.repo),
        "--git-head",
        store.head,
        "--observer",
        store.actors.observer,
        "--project-id",
        store.harness.ledger.project_id,
        "--output",
        str(output),
    ]


def test_build_then_reproduce_through_the_cli_writes_only_its_outputs(store: W9Store, tmp_path: Path, capsys) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    registration = _write_json(inputs / "registration.json", sections)
    out = tmp_path / "out"
    out.mkdir()
    repository = _worktree_bytes(store.repo)
    control = _worktree_bytes(store.harness.ledger.control_root)
    assert cli.main(_build_args(store, registration, out / "inventory.json")) == 0
    record = json.loads((out / "inventory.json").read_text(encoding="utf-8"))
    check_resegmentation(SECTIONS, record)
    reproduce = ["legacy", "inventory", "reproduce", "--inventory", str(out / "inventory.json")]
    assert cli.main([*reproduce, "--repository-root", str(store.repo), "--output", str(out / "report.json")]) == 0
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))["reproduced"] is True
    (inputs / "copy.md").write_bytes(SECTIONS)
    assert cli.main([*reproduce, "--frozen-copy", str(inputs / "copy.md"), "--output", str(out / "report-2.json")]) == 0
    assert _worktree_bytes(store.repo) == repository
    assert _worktree_bytes(store.harness.ledger.control_root) == control
    assert sorted(path.name for path in out.iterdir()) == ["inventory.json", "report-2.json", "report.json"]
    capsys.readouterr()


def test_reproduce_exits_1_when_the_report_shows_a_difference(store: W9Store, tmp_path: Path) -> None:
    sections = store.register("sections.md", role="legacy_coordination")
    record = _build(store, sections, "heading_section", heading_level=2, region=("first_anchor_after", 1))
    record["covered_region"]["resolved_first_line"] = 6
    inventory = _write_json(tmp_path / "inventory.json", record)
    report = tmp_path / "report.json"
    args = ["legacy", "inventory", "reproduce", "--inventory", str(inventory), "--repository-root", str(store.repo)]
    assert cli.main([*args, "--output", str(report)]) == 1
    assert json.loads(report.read_text(encoding="utf-8"))["region"]["resolution_equal"] is False


@pytest.mark.parametrize("blob", ["--output=x", "-p", "abc", "G" * 40, None])
def test_reproduce_refuses_a_git_blob_that_is_not_a_hex_object_id(
    store: W9Store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, blob: Any
) -> None:
    """PR #428 review: the inventory's ``git_blob`` never reaches ``git cat-file`` as an option or a stray word."""
    import research_system.legacy.reader as reader_module

    def no_git(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("git ran on an unchecked blob ID")

    monkeypatch.setattr(reader_module, "_git", no_git)
    inventory = _write_json(
        tmp_path / "inventory.json", {"source_identity": {"identity_kind": "git_tracked", "git_blob": blob}}
    )
    args = ["legacy", "inventory", "reproduce", "--inventory", str(inventory), "--repository-root", str(store.repo)]
    assert cli.main([*args, "--output", str(tmp_path / "report.json")]) == 1
    assert "W9 reproduction needs the inventory's git_blob as a lowercase hex object ID" in capsys.readouterr().err
    assert not (tmp_path / "report.json").exists()


@pytest.mark.parametrize(
    ("where", "message"),
    [
        ("apm", "W9 tool output is under .apm/"),
        ("vault", "W9 tool output is under the vault"),
        ("store", "W9 tool output is inside a store"),
        ("repository", "W9 tool output is inside the repository it reads"),
        ("existing", "W9 tool output already exists"),
    ],
)
def test_each_tool_refuses_a_forbidden_output_before_it_reads(
    store: W9Store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, where: str, message: str
) -> None:
    """Note §12: never under .apm/, the vault or a store; never in the input tree; never over an existing file."""
    sections = store.register("sections.md", role="legacy_coordination")
    registration = _write_json(tmp_path / "registration.json", sections)
    vault = tmp_path / "vault"
    vault.mkdir()
    targets = {
        "apm": tmp_path / "work" / ".apm" / "inventory.json",
        "vault": vault / "inventory.json",
        "store": store.harness.ledger.control_root / "inventory.json",
        "repository": store.repo / "inventory.json",
        "existing": registration,
    }
    output = targets[where]
    repository = _worktree_bytes(store.repo)
    control = _worktree_bytes(store.harness.ledger.control_root)
    import research_system.legacy.reader as reader_module

    def no_read(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("an input was read before the output guard")

    monkeypatch.setattr(reader_module.LegacyReader, "__init__", no_read)
    monkeypatch.setattr(reader_module, "_git", no_read)
    monkeypatch.setattr(cli, "_read_json", no_read)
    build = _build_args(store, registration, output)
    # The legacy group turns a refusal into exit 1 and an ``error:`` line; a read before the guard would raise instead.
    assert cli.main([*build, "--vault-root", str(vault)]) == 1
    assert message in capsys.readouterr().err
    inventory = _write_json(tmp_path / "inventory.json", {"source_identity": {}})
    reproduce = [
        "legacy",
        "inventory",
        "reproduce",
        "--inventory",
        str(inventory),
        "--repository-root",
        str(store.repo),
    ]
    if where != "vault":  # reproduce reads no vault, so names none
        assert cli.main([*reproduce, "--output", str(output)]) == 1
        assert message in capsys.readouterr().err
    assert _worktree_bytes(store.repo) == repository
    assert _worktree_bytes(store.harness.ledger.control_root) == control
    if where != "existing":
        assert not output.exists()


def test_the_output_guard_reads_a_store_marker_that_is_a_directory_or_a_dangling_link(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    (store_root / "manifests" / "store-identity.json").mkdir(parents=True)
    with pytest.raises(IntegrityError, match="W9 tool output is inside a store"):
        refuse_tool_output(store_root / "deep" / "out.json", repository_root=None, vault_root=None)
    assert (
        refuse_tool_output(tmp_path / "elsewhere.json", repository_root=None, vault_root=None)
        == (tmp_path / "elsewhere.json").resolve()
    )
