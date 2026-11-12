# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-2 §12.3, §12.4)
# Purpose: the .apm/bus/ inventory (O-19) and the .apm/ file-level inventory (O-36; W9-T18), on synthetic trees only.
"""``.apm/`` inventory controls (WP9.3 note §12.3, §12.4, §17 "W9-T18" and "Tools write nothing").

Every ``.apm/`` tree here is synthetic, in a scratch Git repository under ``tmp_path``. The live ``.apm/`` is never read.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from research_system import cli
from research_system.errors import IntegrityError
from research_system.legacy.apm_inventory import (
    BUS_FORMAT,
    CLOSURE_MAP_FORMAT,
    apm_universe,
    build_apm_file_inventory,
    build_bus_inventory,
)
from tests.research_system.contracts.test_w9_contract_materialization import _load_tool
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes
from tests.research_system.unit.test_w9_evidence_acceptance import git

TRACKER = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.2 | b |\n"
DUPLICATE_TRACKER = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.1 | b |\n"
PIN = flows.signature()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    (root / ".apm" / "memory" / "stage-01").mkdir(parents=True)
    (root / ".apm" / "bus").mkdir()
    (root / ".apm" / "plan.md").write_bytes(b"# plan\n")
    (root / ".apm" / "tracker.md").write_bytes(TRACKER)
    (root / ".apm" / "memory" / "index.md").write_bytes(b"# memory index\n")
    (root / ".apm" / "memory" / "stage-01" / "task-log.md").write_bytes(b"untracked worker log\n")
    (root / ".apm" / "bus" / "message-1.json").write_bytes(b'{"to": "manager"}\n')
    (root / ".gitignore").write_text(".apm/memory/stage-*/\n.apm/bus/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "synthetic .apm")
    return root


def _closure(tracker_bytes: bytes = TRACKER) -> dict[str, Any]:
    segmented = _load_tool("w9_segmentation").segment(tracker_bytes, "tracker_task_row")
    actors = flows.Actors(owner="actor-owner")
    registration = flows.registration("tdl", actors.analyst, flows.at(0), path=".apm/tracker.md")
    inventory = flows.inventory(
        "tdl", actors.observer, flows.at(1), registration, segmented, source=flows.tracked(".apm/tracker.md")
    )
    observations = [
        flows.observation(
            "tdl",
            actors.observer,
            flows.at(2 + index),
            registration,
            PIN,
            count=index,
            selector={
                "selector_kind": "inventory_item",
                "inventory_ref": flows.record_ref(inventory),
                "row_ordinal": row["row_ordinal"],
                "anchor_text": row["anchor_text"],
                "raw_row_sha256": row["raw_row_sha256"],
            },
            families=[flows.signed_family("item", PIN)],
        )
        for index, row in enumerate(inventory["rows"])
        if row["row_kind"] == "item"
    ]
    return {"file": ".apm/tracker.md", "inventory": inventory, "observations": observations}


def _closure_map(**changes: Any) -> dict[str, Any]:
    body = {
        "format": CLOSURE_MAP_FORMAT,
        "closures": [_closure()],
        "non_import": [
            {
                "files": [
                    ".apm/plan.md",
                    ".apm/memory/index.md",
                    ".apm/memory/stage-01/task-log.md",
                    ".apm/bus/message-1.json",
                ],
                "record": {"kind": "w9-apm-non-import", "sha256": "f" * 64},
            }
        ],
    }
    body.update(changes)
    return body


# --- The universe and the bijection (W9-T18) --------------------------------------------------------------------------


def test_the_universe_is_tracked_files_at_the_commit_the_stage_logs_and_the_bus(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    assert apm_universe(repository, commit) == [
        ".apm/bus/message-1.json",
        ".apm/memory/index.md",
        ".apm/memory/stage-01/task-log.md",
        ".apm/plan.md",
        ".apm/tracker.md",
    ]


def test_an_exact_bijection_does_not_block(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    report = build_apm_file_inventory(repository, commit, _closure_map())
    assert report["blocked"] is False
    assert report["files"] == 5
    assert all(report[key] == [] for key in ("missing", "extra", "in_two_places", "items_missing", "items_extra"))


def _non_import(files: list[str]) -> list[dict[str, Any]]:
    return [{"files": files, "record": {"kind": "w9-apm-non-import", "sha256": "f" * 64}}]


def test_a_missing_file_blocks(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    files = [".apm/memory/index.md", ".apm/memory/stage-01/task-log.md", ".apm/bus/message-1.json"]
    report = build_apm_file_inventory(repository, commit, _closure_map(non_import=_non_import(files)))
    assert report["blocked"] is True and report["missing"] == [".apm/plan.md"]


def test_an_extra_file_blocks(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    body = _closure_map()
    body["non_import"][0]["files"].append(".apm/ghost.md")
    report = build_apm_file_inventory(repository, commit, body)
    assert report["blocked"] is True and report["extra"] == [".apm/ghost.md"]


def test_a_file_in_two_places_blocks(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    body = _closure_map()
    body["non_import"].append(deepcopy(body["non_import"][0]))
    report = build_apm_file_inventory(repository, commit, body)
    assert report["blocked"] is True and ".apm/plan.md" in report["in_two_places"]


def test_a_closure_item_with_no_accepted_observation_blocks(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    closure = _closure()
    closure["observations"].pop()
    report = build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))
    assert report["blocked"] is True and report["items_missing"] == [{"file": ".apm/tracker.md", "row_ordinal": 2}]


def test_an_observation_of_no_item_of_its_inventory_blocks(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    closure = _closure()
    other = _closure()["observations"][0]  # an item of another inventory record
    closure["observations"].append(other)
    report = build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))
    assert report["blocked"] is True and report["items_extra"] == [{"file": ".apm/tracker.md", "row_ordinal": 1}]


def test_a_blocker_row_left_in_a_closure_blocks(repository: Path) -> None:
    """W9-T22's duplicate anchors: both rows are blockers, so the closure cannot close."""
    commit = git(repository, "rev-parse", "HEAD")
    closure = _closure(DUPLICATE_TRACKER)
    assert closure["observations"] == []
    report = build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))
    assert report["blocked"] is True
    assert [row["blocker_reason"] for row in report["blockers_left"]] == ["duplicate_anchor", "duplicate_anchor"]


def test_a_record_not_at_its_recomputed_hash_is_refused(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    closure = _closure()
    closure["inventory"] = {**closure["inventory"], "observer_actor_id": "someone-else"}
    with pytest.raises(IntegrityError, match="W9 .apm closure map inventory is not at its recomputed content hash"):
        build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))


def test_a_closure_whose_inventory_names_another_file_is_refused(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    closure = {**_closure(), "file": ".apm/plan.md"}
    with pytest.raises(IntegrityError, match="W9 .apm closure's inventory names another file: .apm/plan.md"):
        build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))


@pytest.mark.parametrize(
    "change",
    [
        lambda selector: selector.update(raw_row_sha256="0" * 64),
        lambda selector: selector.update(anchor_text="9.9"),
        lambda selector: selector["inventory_ref"].update(record_revision=2),
        lambda selector: selector["inventory_ref"].update(content_hash="0" * 64),
        lambda selector: selector.update(selector_kind="whole_file"),
    ],
    ids=["raw-row-hash", "anchor", "ref-revision", "ref-hash", "selector-kind"],
)
def test_an_observation_whose_selector_differs_from_its_item_row_blocks(repository: Path, change) -> None:
    """The selector as replay checks it (§8.2), not its inventory ID and ordinal alone (CodeRabbit, #432).

    Only the one selector field changes: the inventory ID and the ordinal still name the item row, and the
    observation is re-hashed so it verifies."""
    from research_system.legacy.records import record_content_hash

    commit = git(repository, "rev-parse", "HEAD")
    closure = _closure()
    observation = deepcopy(closure["observations"][0])
    change(observation["selector"])
    assert observation["selector"]["inventory_ref"]["id"] == closure["inventory"]["record_id"]
    assert observation["selector"]["row_ordinal"] == 1
    observation["content_hash"] = record_content_hash(observation)
    closure["observations"][0] = observation
    report = build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))
    assert report["blocked"] is True
    assert report["items_extra"] == [{"file": ".apm/tracker.md", "row_ordinal": 1}]
    assert report["items_missing"] == [{"file": ".apm/tracker.md", "row_ordinal": 1}]


def test_an_observation_of_another_registration_blocks(repository: Path) -> None:
    """Replay refuses an inventory item whose inventory belongs to another registration (§8.2); so does the file tool,
    though the selector still names the item row exactly (CodeRabbit, #432)."""
    from research_system.legacy.records import record_content_hash

    commit = git(repository, "rev-parse", "HEAD")
    closure = _closure()
    other = flows.registration("tdl", "actor-analyst", flows.at(0), path=".apm/plan.md", file_id="9")
    observation = deepcopy(closure["observations"][0])
    observation["registration_ref"] = flows.record_ref(other)
    observation["content_hash"] = record_content_hash(observation)
    assert observation["selector"]["inventory_ref"]["id"] == closure["inventory"]["record_id"]
    closure["observations"][0] = observation
    report = build_apm_file_inventory(repository, commit, _closure_map(closures=[closure]))
    assert report["blocked"] is True
    assert report["items_extra"] == [{"file": ".apm/tracker.md", "row_ordinal": 1}]
    assert report["items_missing"] == [{"file": ".apm/tracker.md", "row_ordinal": 1}]


@pytest.mark.parametrize(
    "named",
    [None, {}, {"kind": "", "sha256": "f" * 64}, {"kind": "w9-apm-non-import", "sha256": "F" * 64}, "f" * 64],
    ids=["null", "empty", "no-kind", "bad-hash", "not-an-object"],
)
def test_a_non_import_entry_without_its_record_is_refused(repository: Path, named: Any) -> None:
    """A null or malformed ``record`` must not place its files (CodeRabbit, #432)."""
    commit = git(repository, "rev-parse", "HEAD")
    body = _closure_map()
    body["non_import"][0]["record"] = named
    with pytest.raises(IntegrityError, match="W9 .apm non-import record does not name its record by kind and SHA-256"):
        build_apm_file_inventory(repository, commit, body)


def _link_directory(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")


@pytest.mark.parametrize("linked", ["stage", "bus", "memory"])
def test_a_linked_stage_bus_or_memory_root_is_refused_before_it_is_listed(
    repository: Path, tmp_path: Path, linked: str
) -> None:
    """``os.walk`` follows a link given as its start even with ``followlinks=False`` (CodeRabbit, #432)."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "foreign.md").write_bytes(b"not an .apm file\n")
    apm = repository / ".apm"
    if linked == "stage":
        _link_directory(apm / "memory" / "stage-02", outside)
        where = ".apm/memory/stage-02"
    elif linked == "bus":
        os.rename(apm / "bus", tmp_path / "old-bus")
        _link_directory(apm / "bus", outside)
        where = ".apm/bus"
    else:
        os.rename(apm / "memory", tmp_path / "old-memory")
        _link_directory(apm / "memory", outside)
        where = ".apm/memory"
    commit = git(repository, "rev-parse", "HEAD")
    with pytest.raises(IntegrityError, match="W9 .apm inventory meets a linked directory: " + re.escape(where)):
        apm_universe(repository, commit)
    if linked == "bus":
        with pytest.raises(IntegrityError, match="W9 .apm inventory needs a real bus directory"):
            build_bus_inventory(apm)


@pytest.mark.parametrize("where", ["memory/stage-01", "bus"])
def test_a_linked_file_in_a_stage_log_or_the_bus_is_refused(repository: Path, tmp_path: Path, where: str) -> None:
    """``followlinks=False`` keeps os.walk out of linked directories but still lists a linked file, whose bytes live
    outside ``.apm/`` (CodeRabbit, #432)."""
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"not an .apm file\n")
    link = repository / ".apm" / where / "linked.md"
    try:
        os.symlink(outside, link)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")
    commit = git(repository, "rev-parse", "HEAD")
    message = "W9 .apm inventory meets a linked file: " + re.escape(f".apm/{where}/linked.md")
    with pytest.raises(IntegrityError, match=message):
        apm_universe(repository, commit)


@pytest.mark.parametrize("tool", ["universe", "bus"])
def test_a_directory_that_cannot_be_listed_is_refused(
    repository: Path, monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    """``os.walk`` skips an unlistable directory by default, which would leave a partial inventory (CodeRabbit, #432)."""
    nested = repository / ".apm" / "bus" / "nested"
    nested.mkdir()
    (nested / "message-2.json").write_bytes(b"{}\n")
    real = os.scandir

    def unlistable(path: Any = ".") -> Any:
        if Path(path).name == "nested":
            raise PermissionError(13, "Access is denied", str(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", unlistable)
    with pytest.raises(IntegrityError, match="W9 .apm inventory cannot list a directory: .*Access is denied"):
        if tool == "universe":
            apm_universe(repository, git(repository, "rev-parse", "HEAD"))
        else:
            build_bus_inventory(repository / ".apm")


def test_a_malformed_closure_map_is_refused(repository: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    with pytest.raises(IntegrityError, match="W9 .apm closure map does not have the fixed format"):
        build_apm_file_inventory(repository, commit, {**_closure_map(), "format": "other/1"})


# --- The bus inventory (O-19) ----------------------------------------------------------------------------------------


def test_the_bus_inventory_is_a_dated_list_of_paths_sizes_and_hashes(repository: Path) -> None:
    import hashlib

    moment = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    inventory = build_bus_inventory(repository / ".apm", recorded_at=moment)
    raw = (repository / ".apm" / "bus" / "message-1.json").read_bytes()
    assert inventory == {
        "format": BUS_FORMAT,
        "recorded_at": "2026-11-11T12:00:00Z",
        "root": ".apm/bus",
        "files": [{"path": "message-1.json", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}],
    }


def test_the_bus_inventory_refuses_a_file_with_a_second_link(repository: Path) -> None:
    target = repository / ".apm" / "bus" / "message-1.json"
    os.link(target, repository / "elsewhere.json")
    with pytest.raises(IntegrityError, match="W9 .apm bus file cannot be read handle-bound: message-1.json"):
        build_bus_inventory(repository / ".apm")


# --- The tools (note §12, §13; "Tools write nothing") ----------------------------------------------------------------


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir(exist_ok=True)
    return vault


def test_the_bus_tool_writes_only_its_output_and_leaves_apm_byte_identical(repository: Path, tmp_path: Path) -> None:
    before = _tree_bytes(repository)
    output = tmp_path / "bus.json"
    argv = ["legacy", "apm-inventory", "bus", "--apm-root", str(repository / ".apm"), "--vault-root"]
    assert cli.main([*argv, str(_vault(tmp_path)), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["format"] == BUS_FORMAT
    assert _tree_bytes(repository) == before


def test_the_files_tool_exits_0_on_a_bijection_and_1_when_it_blocks(repository: Path, tmp_path: Path) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    before = _tree_bytes(repository)
    for name, body, code in (("good", _closure_map(), 0), ("bad", _closure_map(non_import=[]), 1)):
        closure_map = tmp_path / f"{name}-map.json"
        closure_map.write_text(json.dumps(body), encoding="utf-8")
        output = tmp_path / f"{name}.json"
        argv = ["legacy", "apm-inventory", "files", "--repository-root", str(repository), "--git-commit", commit]
        argv += ["--closure-map", str(closure_map), "--vault-root", str(_vault(tmp_path)), "--output", str(output)]
        assert cli.main(argv) == code
        assert json.loads(output.read_text(encoding="utf-8"))["blocked"] is bool(code)
    assert _tree_bytes(repository) == before


@pytest.mark.parametrize(
    ("where", "message"),
    [
        ("apm", "W9 tool output is under .apm/"),
        ("vault", "W9 tool output is under the vault"),
        ("store", "W9 tool output is inside a store"),
        ("repository", "W9 tool output is inside the repository it reads"),
    ],
)
@pytest.mark.parametrize("tool", ["bus", "files"])
def test_each_apm_tool_refuses_a_forbidden_output_before_reading(
    repository: Path, tmp_path: Path, capsys, tool: str, where: str, message: str
) -> None:
    vault = _vault(tmp_path)
    store = tmp_path / "store"
    (store / "manifests").mkdir(parents=True)
    (store / "manifests" / "store-identity.json").write_text("{}", encoding="utf-8")
    outputs = {
        "apm": repository / ".apm" / "out.json",
        "vault": vault / "out.json",
        "store": store / "out.json",
        "repository": repository / "out.json",
    }
    closure_map = tmp_path / "map.json"
    closure_map.write_text(json.dumps(_closure_map()), encoding="utf-8")
    before = _tree_bytes(tmp_path)
    if tool == "bus":
        argv = ["legacy", "apm-inventory", "bus", "--apm-root", str(repository / ".apm")]
    else:
        commit = git(repository, "rev-parse", "HEAD")
        argv = ["legacy", "apm-inventory", "files", "--repository-root", str(repository), "--git-commit", commit]
        argv += ["--closure-map", str(closure_map)]
    assert cli.main([*argv, "--vault-root", str(vault), "--output", str(outputs[where])]) == 1
    assert message in capsys.readouterr().err
    assert _tree_bytes(tmp_path) == before


def test_the_bus_tool_needs_the_apm_directory_itself(repository: Path, tmp_path: Path, capsys) -> None:
    argv = ["legacy", "apm-inventory", "bus", "--apm-root", str(repository), "--vault-root", str(_vault(tmp_path))]
    assert cli.main([*argv, "--output", str(tmp_path / "x.json")]) == 1
    assert "W9 .apm inventory needs --apm-root to name the .apm directory" in capsys.readouterr().err
