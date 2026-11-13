# Research context: docs/plans/agentic-research-system/reviews/wp9-3-2-review-b98515c6-2026-11-11.md (addendum)
# Purpose: the reviewer's re-check probes at 26f9af91: the inverses of the first round's finding probes, the i-2 fixes,
# the second pass's three fixes, D-4 and the boundary. Scratch stores and repositories under tmp_path only.
"""Re-check probes for WP9.3-2 at ``26f9af91`` (PR #432 after CodeRabbit's two passes and the review's fixes)."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system.errors import IntegrityError  # noqa: E402
from research_system.legacy import acceptance, evidence  # noqa: E402
from research_system.legacy.apm_inventory import apm_universe, build_apm_file_inventory  # noqa: E402
from research_system.legacy.evidence import EvidenceRefused, require_cl_export  # noqa: E402
from research_system.legacy.inventory import build_acceptance_batch  # noqa: E402
from research_system.legacy.records import record_content_hash  # noqa: E402
from research_system.legacy.replay.driver import replay_legacy  # noqa: E402
from tests.research_system.contracts.test_w9_wp9_3_censuses import _service_constructions  # noqa: E402
from tests.research_system.integration import w9_flows as flows  # noqa: E402
from tests.research_system.integration.test_w9_wp9_3_replay import PIN, _full_flow  # noqa: E402
from tests.research_system.integration.test_w9_wp9_3_replay import base as base  # noqa: E402, F401
from tests.research_system.integration.w9_flows import Actors, at  # noqa: E402
from tests.research_system.unit.test_w9_apm_inventory import _closure_map  # noqa: E402
from tests.research_system.unit.test_w9_apm_inventory import repository as repository  # noqa: E402, F401
from tests.research_system.unit.test_w9_evidence_acceptance import reference_export  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

FIRST = "b98515c6f946307b4e3e71dc9c062ab7a2c325d8"
HEAD = "26f9af91a250718a76aeddb9f85b5117201b8139"
BASE = "b6ecfdfc2e54c687378163ff1c74531a6b053917"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


# --- m-1: the census -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from research_system.command.service import CommandService as Svc\n\ndef f():\n    return Svc(1)\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from functools import partial as p\n\ndef f():\n    return p(CommandService, 1)()\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from typing import Any\nfrom functools import partial\n\nfactory: Any = partial(CommandService, 1)\n\n"
            "def f():\n    return factory()\n",
            [("fixture.py", "f", 7, False)],
        ),
        ("def f():\n    if (made := CommandService):\n        return made(1)\n", [("fixture.py", "f", 3, False)]),
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, binding_check=c)\n"
            "    alias = factory\n    return alias()\n",
            [("fixture.py", "f", 6, True)],
        ),
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, binding_check=c)\n"
            "    return factory(binding_check=None)\n",
            [("fixture.py", "f", 5, False)],
        ),
        # The reviewer's own extra forms, not among the implementer's fixtures.
        (
            "import functools as ft\n\ndef f(c):\n    return ft.partial(CommandService, binding_check=c)(binding_check=False)\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from research_system.command.service import CommandService as Svc\n\nAlias = Svc\n\ndef f():\n"
            "    return Alias(1)\n",
            [("fixture.py", "f", 6, False)],
        ),
        (
            "from functools import partial as p\n\ndef f(c):\n    factory = p(CommandService, binding_check=c)\n"
            "    other: object = factory\n    return other(1)\n",
            [("fixture.py", "f", 6, True)],
        ),
    ],
    ids=[
        "import-alias",
        "partial-import-alias",
        "annotated-partial",
        "walrus",
        "checked-partial-alias",
        "call-time-none",
        "module-alias-partial-false-override",
        "import-alias-then-assign",
        "aliased-partial-through-annassign",
    ],
)
def test_m1_closed_every_form_is_a_construction_with_the_right_check(source: str, expected: list) -> None:
    assert _service_constructions("fixture.py", source) == expected


# --- m-1 at bc47fea8: partial bindings keyed by lexical scope (CodeRabbit's third pass) ---------------------------

_CHECKED = "partial(CommandService, binding_check=check)"
_UNCHECKED = "partial(CommandService, 1)"


def _src(*lines: str) -> str:
    return "from functools import partial\n" + "\n".join(lines) + "\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # A module-level partial used inside a function resolves from the module.
        (_src(f"factory = {_CHECKED}", "def f():", "    return factory()"), [("fixture.py", "f", 4, True)]),
        (_src(f"factory = {_UNCHECKED}", "def f():", "    return factory()"), [("fixture.py", "f", 4, False)]),
        # A nested function resolves from its enclosing function.
        (
            _src("def outer(check):", f"    factory = {_CHECKED}", "    def inner():", "        return factory()"),
            [("fixture.py", "outer.inner", 5, True)],
        ),
        (
            _src(
                f"factory = {_CHECKED}",
                "def outer():",
                f"    factory = {_UNCHECKED}",
                "    def inner():",
                "        return factory()",
            ),
            [("fixture.py", "outer.inner", 6, False)],
        ),
        # A call in a class body resolves from the class body.
        (
            _src("def make(check):", "    class C:", f"        factory = {_CHECKED}", "        made = factory()"),
            [("fixture.py", "make.C", 5, True)],
        ),
        (
            _src(f"factory = {_CHECKED}", "class C:", f"    factory = {_UNCHECKED}", "    made = factory()"),
            [("fixture.py", "C", 5, False)],
        ),
    ],
    ids=[
        "module-checked-in-function",
        "module-unchecked-in-function",
        "enclosing-checked-in-nested",
        "enclosing-unchecked-shadows-module-checked",
        "class-body-checked",
        "class-body-unchecked-shadows-module-checked",
    ],
)
def test_m1_scope_keying_resolves_module_enclosing_and_class_body_names(source: str, expected: list) -> None:
    assert _service_constructions("fixture.py", source) == expected


def test_finding_m5_the_census_lets_a_class_body_enclose_its_methods() -> None:
    """Finding m-5 (addendum, at bc47fea8): Python resolves a free name in a method from the enclosing function or
    module, never from the class body, so the method's ``factory()`` below calls the module's unchecked partial. The
    census resolves it from the class body instead and reports it checked: a false pass. The correct answer is
    ``False``; this probe asserts what the census does."""
    source = _src(
        f"factory = {_UNCHECKED}",
        "def make(check):",
        "    class C:",
        f"        factory = {_CHECKED}",
        "        def build(self):",
        "            return factory()",
        "    return C",
    )
    assert _service_constructions("fixture.py", source) == [("fixture.py", "make.C.build", 7, True)]
    calls: list[Any] = []

    def recorder(*args: Any, **kwargs: Any) -> None:
        calls.append(kwargs.get("binding_check", "unchecked"))

    namespace: dict[str, Any] = {"CommandService": recorder, "__name__": "fixture"}
    exec(compile(source, "fixture.py", "exec"), namespace)
    namespace["make"]("the check")().build()
    assert calls == ["unchecked"]  # Python's own answer: the module's unchecked partial ran


# --- m-2: batch mode --------------------------------------------------------------------------------------------


@pytest.fixture
def actors() -> Actors:
    from tests.research_system.factories import ACTORS

    return Actors(owner=ACTORS["actor-a"])


def _complete_family_set_batch(base, actors) -> tuple[dict[str, Any], dict[str, Any]]:  # noqa: F811
    forger, records = _full_flow(base[0], actors)
    state = replay_legacy(forger.events, schemas=base[1], pinned_signatures=(PIN,))
    table = next(iter(state["records"]["legacy_field_family_membership"].values()))
    names = [family["name"] for family in table["families"]]
    complete = flows.observation(
        forger.project_id,
        actors.observer,
        at(55),
        records["registration"],
        PIN,
        count=2,
        selector={"selector_kind": "json_family_set", "membership_ref": flows.record_ref(table), "family_names": names},
        families=[flows.signed_family(name, PIN) for name in names],
    )
    record = flows.acceptance(forger.project_id, actors.analyst, at(60), [complete])
    batch = {
        "project_id": forger.project_id,
        "items": [
            {
                "observation": complete,
                "registration": records["registration"],
                "membership": None,
                "pilot_promotion": flows.pilot_promotion(),
            }
        ],
        "threshold_preregistration_sha256": "3" * 64,
        "governing_record_set_sha256": "4" * 64,
        "anchors": record["anchors"],
        "enforcement_change_list": record["enforcement_change_list"],
    }
    return batch, table


def test_m2_closed_a_family_set_item_with_no_membership_record_is_refused(base, actors) -> None:  # noqa: F811
    batch, table = _complete_family_set_batch(base, actors)
    with pytest.raises(IntegrityError, match="json_family_set observation needs the membership record it names"):
        build_acceptance_batch(batch)
    batch["items"][0]["membership"] = table
    _, preview = build_acceptance_batch(batch)
    assert preview[0]["transitions"] is True


def test_m2_closed_a_membership_or_registration_at_another_hash_is_refused(base, actors) -> None:  # noqa: F811
    batch, table = _complete_family_set_batch(base, actors)
    edited = deepcopy(table)
    edited["families"] = edited["families"][:1]
    edited["content_hash"] = record_content_hash(edited)  # same ID, valid hash, other content
    batch["items"][0]["membership"] = edited
    with pytest.raises(IntegrityError, match="membership record is not the one the observation names"):
        build_acceptance_batch(batch)
    batch["items"][0]["membership"] = table
    registration = deepcopy(batch["items"][0]["registration"])
    registration["normalized_path"] = "results/other.json"
    registration["content_hash"] = record_content_hash(registration)
    batch["items"][0]["registration"] = registration
    with pytest.raises(IntegrityError, match="observation names another registration"):
        build_acceptance_batch(batch)


# --- m-3: anchors -----------------------------------------------------------------------------------------------


def _init(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "r@example.invalid")
    _git(repo, "config", "user.name", "R")


def _commit(repo: Path, name: str, data: bytes) -> str:
    (repo / name).write_bytes(data)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)
    return _git(repo, "rev-parse", "HEAD")


def test_m3_closed_a_shallow_repository_is_refused_and_the_full_clone_still_decides(tmp_path: Path) -> None:
    full = tmp_path / "full"
    _init(full)
    threshold, governing = b"threshold\n", b"governing\n"
    root = _commit(full, "t.txt", threshold)
    governed = _commit(full, "g.txt", governing)
    unrelated = _commit(full, "unrelated.txt", b"x\n")

    def record(t: str, g: str) -> dict[str, Any]:
        return {
            "threshold_preregistration_sha256": hashlib.sha256(threshold).hexdigest(),
            "governing_record_set_sha256": hashlib.sha256(governing).hexdigest(),
            "anchors": [
                {"anchored": "threshold_preregistration", "anchor_kind": "git_commit", "value": t},
                {"anchored": "governing_record_set", "anchor_kind": "git_commit", "value": g},
            ],
        }

    acceptance.check_anchors(full, unrelated, record(root, governed))  # positive control: a root commit, a child
    with pytest.raises(IntegrityError, match="does not introduce the anchored bytes"):
        acceptance.check_anchors(full, unrelated, record(unrelated, unrelated))
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", full.resolve().as_uri(), str(shallow)], check=True, capture_output=True
    )
    with pytest.raises(IntegrityError, match="cannot be checked in a shallow repository"):
        acceptance.check_anchors(shallow, unrelated, record(unrelated, unrelated))


# --- m-4: the .apm/ file inventory ------------------------------------------------------------------------------


def _head(repository: Path) -> str:  # noqa: F811
    return _git(repository, "rev-parse", "HEAD")


def test_m4_positive_control_the_fixture_map_is_an_exact_bijection(repository: Path) -> None:  # noqa: F811
    assert build_apm_file_inventory(repository, _head(repository), _closure_map())["blocked"] is False


@pytest.mark.parametrize("record", [None, {}, {"kind": "", "sha256": "f" * 64}, {"kind": "k", "sha256": "F" * 64}])
def test_m4_closed_a_non_import_entry_without_a_valid_record_is_refused(repository: Path, record: Any) -> None:  # noqa: F811
    closure_map = _closure_map()
    closure_map["non_import"][0]["record"] = record
    with pytest.raises(IntegrityError, match="does not name its record by kind and SHA-256"):
        build_apm_file_inventory(repository, _head(repository), closure_map)


def _link_dir(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        pytest.skip("this machine cannot create a directory symlink")


def test_m4_closed_a_linked_stage_directory_is_refused(repository: Path, tmp_path: Path) -> None:  # noqa: F811
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "foreign.md").write_bytes(b"x\n")
    _link_dir(repository / ".apm" / "memory" / "stage-02", outside)
    with pytest.raises(IntegrityError, match="meets a linked directory: .apm/memory/stage-02"):
        apm_universe(repository, _head(repository))


def test_m4_closed_a_linked_memory_root_is_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init(repo)
    _commit(repo, "README", b"r\n")
    (repo / ".apm").mkdir()
    outside = tmp_path / "memory-elsewhere"
    (outside / "stage-01").mkdir(parents=True)
    _link_dir(repo / ".apm" / "memory", outside)
    with pytest.raises(IntegrityError, match="meets a linked directory: .apm/memory"):
        apm_universe(repo, _head(repo))


@pytest.mark.parametrize("where", ["bus", "memory/stage-01"])
def test_m4_second_pass_a_linked_file_in_the_bus_or_a_stage_log_is_refused(
    repository: Path,  # noqa: F811
    tmp_path: Path,
    where: str,
) -> None:
    outside = tmp_path / "elsewhere.json"
    outside.write_bytes(b"{}\n")
    try:
        os.symlink(outside, repository / ".apm" / where / "linked.json")
    except OSError:
        pytest.skip("this machine cannot create a file symlink")
    with pytest.raises(IntegrityError, match=f"meets a linked file: .apm/{where}/linked.json"):
        apm_universe(repository, _head(repository))


def test_m4_closed_an_unlistable_directory_refuses_instead_of_being_skipped(
    repository: Path,  # noqa: F811
    monkeypatch,
) -> None:
    real = os.scandir
    stage = repository / ".apm" / "memory" / "stage-01"

    def failing(path: Any = ".") -> Any:
        if Path(path) == stage:
            raise PermissionError(13, "simulated", str(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", failing)
    with pytest.raises(IntegrityError, match="cannot list a directory"):
        apm_universe(repository, _head(repository))


def _first_observation_changed(**changes: Any) -> dict[str, Any]:
    closure_map = _closure_map()
    observation = closure_map["closures"][0]["observations"][0]
    for key, value in changes.items():
        if key == "registration_id":
            observation["registration_ref"] = {**observation["registration_ref"], "id": value}
        else:
            observation["selector"][key] = value
    observation["content_hash"] = record_content_hash(observation)
    return closure_map


@pytest.mark.parametrize(
    "changes",
    [
        {"raw_row_sha256": "0" * 64},
        {"anchor_text": "not the row's anchor"},
        {"inventory_ref": {"id": "obj_x", "record_revision": 1, "content_hash": "0" * 64}},
        {"registration_id": flows.new_id("scope_definition")},
    ],
    ids=["raw-row-hash", "anchor-text", "inventory-ref", "second-pass-registration"],
)
def test_m4_closed_an_observation_whose_selector_or_registration_differs_blocks(
    repository: Path,  # noqa: F811
    changes: dict[str, Any],
) -> None:
    report = build_apm_file_inventory(repository, _head(repository), _first_observation_changed(**changes))
    assert report["blocked"] is True and report["items_extra"] and report["items_missing"]


# --- i-1: selector order ----------------------------------------------------------------------------------------


def test_i1_closed_reordered_family_names_make_the_earlier_observation_not_the_latest(base, actors) -> None:  # noqa: F811
    forger, records = _full_flow(base[0], actors)
    schemas = base[1]
    state = replay_legacy(forger.events, schemas=schemas, pinned_signatures=(PIN,))
    table = next(iter(state["records"]["legacy_field_family_membership"].values()))
    names = [family["name"] for family in table["families"]]

    def observed(order: list[str], count: int, when: float) -> dict[str, Any]:
        return flows.observation(
            forger.project_id,
            actors.observer,
            at(when),
            records["registration"],
            PIN,
            count=count,
            selector={
                "selector_kind": "json_family_set",
                "membership_ref": flows.record_ref(table),
                "family_names": order,
            },
            families=[flows.signed_family(name, PIN) for name in order],
        )

    earlier = observed(names, 2, 55)
    forger = forger.row("LR-015", earlier["record_id"], earlier, actor=actors.observer, when=at(55))
    later = observed(list(reversed(names)), 3, 56)
    forger = forger.row("LR-015", later["record_id"], later, actor=actors.observer, when=at(56))
    record = flows.acceptance(forger.project_id, actors.analyst, at(60), [earlier])
    forger = flows.acceptance_recorded(forger, actors, record, [], stop_after="LR-016")
    with pytest.raises(IntegrityError, match="not the latest for its source and selector"):
        replay_legacy(forger.events, schemas=schemas, pinned_signatures=(PIN,))


# --- i-2: the export format --------------------------------------------------------------------------------------


def test_i2_closed_a_calendar_invalid_read_time_is_refused_as_evidence() -> None:
    export = reference_export()
    export["read"]["started_at"] = "2026-02-30T00:00:00Z"
    with pytest.raises(EvidenceRefused, match="read does not have the fixed format"):
        require_cl_export(export)


@pytest.mark.parametrize(
    "path",
    [
        "results/cl-copy.md",
        ".research-system/evidence/w9",
        ".research-system/evidence/w9/../w9/cl.md",
        ".research-system/evidence/w9//cl.md",
        "/.research-system/evidence/w9/cl.md",
        ".research-system/evidence/w10/cl.md",
    ],
)
def test_i2_closed_a_retained_copy_outside_the_evidence_area_is_refused(path: str) -> None:
    export = reference_export()
    export["retained_copy"]["repository_path"] = path
    with pytest.raises(EvidenceRefused, match="copy is not in the evidence area"):
        require_cl_export(export)


def test_i2_positive_control_a_nested_copy_in_the_evidence_area_is_admitted() -> None:
    export = reference_export()
    export["retained_copy"]["repository_path"] = ".research-system/evidence/w9/cl/2026-11-11/copy.md"
    assert require_cl_export(export) == export


# --- D-4 and the boundary at 26f9af91 ------------------------------------------------------------------------


def test_d4_unchanged_at_the_new_head() -> None:
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
    for path, prefix in (
        ("tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml", "4c895042"),
        ("tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py", "559d684a"),
        ("tools/w9_segmentation.py", "43e1454d"),
    ):
        assert _git(REPO_ROOT, "rev-parse", f"{HEAD}:{path}").startswith(prefix)


def test_the_fix_commits_touch_only_the_eleven_files() -> None:
    changed = sorted(_git(REPO_ROOT, "diff", "--name-only", FIRST, HEAD).splitlines())
    assert changed == sorted(
        [
            "docs/plans/agentic-research-system/transition/w9/wp9-3-2-record.md",
            "research_system/legacy/acceptance.py",
            "research_system/legacy/apm_inventory.py",
            "research_system/legacy/evidence.py",
            "research_system/legacy/inventory.py",
            "research_system/legacy/replay/reducers.py",
            "tests/research_system/contracts/test_w9_wp9_3_censuses.py",
            "tests/research_system/integration/test_w9_wp9_3_2_batch_build.py",
            "tests/research_system/integration/test_w9_wp9_3_2_replay.py",
            "tests/research_system/unit/test_w9_apm_inventory.py",
            "tests/research_system/unit/test_w9_evidence_acceptance.py",
        ]
    )
    second = sorted(
        _git(REPO_ROOT, "diff", "--name-only", "4636bc4c596009c4e83324a1eccec7cd6d5dfef4", HEAD).splitlines()
    )
    assert set(second) <= set(changed) and len(second) == 4
    protected = (
        ".research-system/",
        "contracts/",
        "research_system/command/",
        "research_system/store/",
        "research_system/discovery/",
        "research_system/projection/",
        "research_system/schema_registry.py",
        "research_system/authority.py",
        "research_system/cli.py",
        "research_system/legacy/accepted_w9.py",
        "research_system/legacy/segmentation.py",
        "tools/",
        "tests/research_system/smoke/",
    )
    whole = _git(REPO_ROOT, "diff", "--name-only", BASE, HEAD).splitlines()
    assert [
        p
        for p in whole
        if p.startswith(protected) and p not in {"research_system/cli.py", "tools/research_system_durations.json"}
    ] == []
    assert evidence.CL_EXPORT_PRODUCER["git_blob"].startswith("43e1454d")


MERGED_HEAD = "bc47fea828908522abb118bd27ee7ec250af8627"
MERGE_COMMIT = "baea2c13a4a28f30cf38f2a5c51fdd6a063db510"


def test_the_merged_tree_is_bc47fea8_and_differs_from_26f9af91_only_in_the_census_test_and_the_record() -> None:
    """The equalities that carry D-4 and genesis from 26f9af91 to the merge: the merge commit's tree is
    ``bc47fea8``'s, and ``bc47fea8`` changes only the census test and the record, so ``research_system/``,
    ``.research-system/``, the smoke tree and ``tools/`` are 26f9af91's byte for byte."""
    assert _git(REPO_ROOT, "rev-parse", f"{MERGE_COMMIT}^{{tree}}") == _git(
        REPO_ROOT, "rev-parse", f"{MERGED_HEAD}^{{tree}}"
    )
    assert sorted(_git(REPO_ROOT, "diff", "--name-only", HEAD, MERGED_HEAD).splitlines()) == [
        "docs/plans/agentic-research-system/transition/w9/wp9-3-2-record.md",
        "tests/research_system/contracts/test_w9_wp9_3_censuses.py",
    ]
    for tree in ("research_system", ".research-system", "tests/research_system/smoke", "tools"):
        assert _git(REPO_ROOT, "rev-parse", f"{HEAD}:{tree}") == _git(REPO_ROOT, "rev-parse", f"{MERGE_COMMIT}:{tree}")
    assert _git(REPO_ROOT, "diff", "--name-only", MERGED_HEAD, "HEAD", "--", "research_system", "tests") == ""
