# Research context: docs/plans/agentic-research-system/reviews/wp9-3-2-review-b98515c6-2026-11-11.md (P-080; P-083)
# Purpose: the WP9.3-2 reviewer's asserting probes. Each runs on scratch stores and repositories under tmp_path, on
# forged scratch ledgers, or on pure functions, and asserts what the code does at b98515c6. A passing probe confirms
# the claim or the finding it names.
"""Reviewer probes for WP9.3-2 at ``b98515c6``: n-1 on a real crashed advance, the n-3 census, LR-016 to LR-020 at
replay, the builder's batch mode, the anchors, the export recheck, the ``.apm/`` tools and D-4."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import random
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system import cli  # noqa: E402
from research_system.errors import ConfigurationError, IntegrityError  # noqa: E402
from research_system.legacy import acceptance, evidence  # noqa: E402
from research_system.legacy.export_recheck import recheck_cl_export  # noqa: E402
from research_system.legacy.inventory import build_acceptance_batch  # noqa: E402
from research_system.legacy.replay import reducers  # noqa: E402
from research_system.legacy.replay.driver import replay_legacy  # noqa: E402
from research_system.store.current_binding import CURRENT_BINDING_RELATIVE_PATH  # noqa: E402
from tests.research_system.contracts.test_w9_wp9_3_censuses import (  # noqa: E402
    _service_constructions,
    _service_name_strings,
)
from tests.research_system.integration import w9_flows as flows  # noqa: E402
from tests.research_system.integration.test_w9_wp9_3_replay import PIN, _full_flow  # noqa: E402
from tests.research_system.integration.test_w9_wp9_3_replay import base as base  # noqa: E402, F401
from tests.research_system.integration.w9_flows import Actors, at  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

BASE = "b6ecfdfc2e54c687378163ff1c74531a6b053917"
HEAD = "b98515c6f946307b4e3e71dc9c062ab7a2c325d8"
UNLOADABLE = "ars submit refused: the store has a current binding this checkout cannot load"
POINTER_ABSENT = f"{UNLOADABLE}: its binding pointer is absent"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


# --- n-1: a real advance crashed between the unlink and the publish ----------------------------------------------------


class _Crash(Exception):
    pass


def _crash_the_pointer_publish(monkeypatch, control_root: Path) -> None:
    """Make the real advance die in the absent-final state: the old pointer unlinked, the new one never published."""
    import research_system.store.binding_service as binding_service

    original = binding_service._replace_or_verify
    pointer = CURRENT_BINDING_RELATIVE_PATH.as_posix()

    def crashing(locked: Any, path: str, before: bytes, intended: bytes) -> None:
        if path == pointer:
            (control_root / CURRENT_BINDING_RELATIVE_PATH).unlink()
            raise _Crash("simulated crash after the unlink")
        original(locked, path, before, intended)

    monkeypatch.setattr(binding_service, "_replace_or_verify", crashing)


def test_n1_a_real_crashed_advance_refuses_a_preloaded_and_a_fresh_writer_under_the_lock(
    tmp_path: Path, monkeypatch
) -> None:
    """P-083 item 5: on the real v1.2 advance fixture, crash the advance with the pointer unlinked and unpublished.
    A writer whose check loaded the binding before the crash, and a fresh one built after it, both refuse in the lock."""
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_w9_wp9_3_binding_head import _pin_intent

    service, intent, predecessor_root, _, _ = _pin_intent(tmp_path)
    monkeypatch.setattr(
        cli, "canonical_foundation_path", lambda: predecessor_root / ".research-system" / "config" / "foundation.yaml"
    )
    binding = SimpleNamespace(
        project_id=PROJECT_ID, store_identity=service.store_identity, control_root=service.control_root
    )
    preloaded = cli._foundation_binding_check(binding)
    assert callable(preloaded)
    preloaded()  # healthy before the crash: the real binding revalidates
    _crash_the_pointer_publish(monkeypatch, service.control_root)
    with pytest.raises(_Crash):
        service.advance(intent)
    assert not (service.control_root / CURRENT_BINDING_RELATIVE_PATH).exists()
    objects = sorted((service.control_root / "objects" / "binding-repair").iterdir())
    assert objects, "the advance wrote its binding object before it touched the pointer"
    with pytest.raises(ConfigurationError, match=POINTER_ABSENT):
        preloaded()
    fresh = cli._foundation_binding_check(binding)  # no pointer now: nothing is loaded before binding
    assert callable(fresh)
    with pytest.raises(ConfigurationError, match=POINTER_ABSENT):
        fresh()


def test_n1_an_absent_final_crash_inside_the_real_anchor_transaction_is_refused(tmp_path: Path, monkeypatch) -> None:
    """The record's §8 ask: R1 against an absent-final crash on a real anchor transaction. The crash is injected in
    ``DirectoryTransaction.adopt_or_publish`` for the pointer, so the real ``replace_or_recover`` has made its desired
    stage durable and run its real ``remove_exact_final`` on the old pointer (``store/anchor.py:2729-2733``)."""
    from research_system.store.anchor import DirectoryTransaction
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_w9_wp9_3_binding_head import _pin_intent

    service, intent, predecessor_root, _, _ = _pin_intent(tmp_path)
    monkeypatch.setattr(
        cli, "canonical_foundation_path", lambda: predecessor_root / ".research-system" / "config" / "foundation.yaml"
    )
    binding = SimpleNamespace(
        project_id=PROJECT_ID, store_identity=service.store_identity, control_root=service.control_root
    )
    preloaded = cli._foundation_binding_check(binding)
    original = DirectoryTransaction.adopt_or_publish

    def crashing(self: Any, stage: Any, final_name: str) -> Any:
        if final_name == CURRENT_BINDING_RELATIVE_PATH.name:
            raise _Crash("simulated crash between the unlink and the publish")
        return original(self, stage, final_name)

    monkeypatch.setattr(DirectoryTransaction, "adopt_or_publish", crashing)
    with pytest.raises(_Crash):
        service.advance(intent)
    monkeypatch.setattr(DirectoryTransaction, "adopt_or_publish", original)
    assert not (service.control_root / CURRENT_BINDING_RELATIVE_PATH).exists()
    assert any((service.control_root / "objects" / "binding-repair").iterdir())
    with pytest.raises(ConfigurationError, match=POINTER_ABSENT):
        preloaded()
    with pytest.raises(ConfigurationError, match=POINTER_ABSENT):
        cli._foundation_binding_check(binding)()


def test_n1_a_fresh_writer_in_a_new_process_refuses_the_crashed_advance(tmp_path: Path, monkeypatch) -> None:
    """The fresh-process limb, in a separate interpreter: no in-process state can carry the earlier load."""
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_w9_wp9_3_binding_head import _pin_intent

    service, intent, predecessor_root, _, _ = _pin_intent(tmp_path)
    _crash_the_pointer_publish(monkeypatch, service.control_root)
    with pytest.raises(_Crash):
        service.advance(intent)
    foundation = predecessor_root / ".research-system" / "config" / "foundation.yaml"
    script = tmp_path / "fresh_writer.py"
    script.write_text(
        "\n".join(
            [
                "import sys",
                "from pathlib import Path",
                "from types import SimpleNamespace",
                f"sys.path.insert(0, {str(REPO_ROOT)!r})",
                "from research_system import cli",
                "from research_system.errors import ConfigurationError",
                f"cli.canonical_foundation_path = lambda: Path({str(foundation)!r})",
                "binding = SimpleNamespace(",
                f"    project_id={PROJECT_ID!r}, store_identity={service.store_identity!r},",
                f"    control_root=Path({str(service.control_root)!r}),",
                ")",
                "check = cli._foundation_binding_check(binding)",
                "try:",
                "    check()",
                "except ConfigurationError as exc:",
                "    print('REFUSED', exc)",
                "else:",
                "    print('ADMITTED')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(f"REFUSED {POINTER_ABSENT}")


def test_n1_a_really_initialized_never_bound_store_still_skips(tmp_path: Path, monkeypatch) -> None:
    """Preservation, on a real store init (not a bare directory): no pointer and no ``objects/binding-repair/``, so the
    in-lock check is a no-op and the store is byte-identical."""
    import yaml

    from tests.research_system.factories import control_plane
    from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes

    (tmp_path / "store").mkdir()
    harness = control_plane(tmp_path / "store")
    control_root = harness.ledger.control_root
    assert not (control_root / CURRENT_BINDING_RELATIVE_PATH).exists()
    assert not (control_root / "objects" / "binding-repair").exists()
    foundation = tmp_path / "repo" / ".research-system" / "config" / "foundation.yaml"
    foundation.parent.mkdir(parents=True)
    foundation.write_text(
        yaml.safe_dump({"project_id": "tdl", "store_identity": "a" * 64, "control_root": str(control_root)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: foundation)
    binding = SimpleNamespace(project_id="tdl", store_identity="a" * 64, control_root=control_root)
    before = _tree_bytes(control_root)
    check = cli._foundation_binding_check(binding)
    assert callable(check) and check() is None
    assert _tree_bytes(control_root) == before


# --- n-3: the CommandService census --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "import functools\n\ndef f():\n    return functools.partial(CommandService, 1)()\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from operator import attrgetter\n\ndef f(m):\n    return attrgetter('CommandService')(m)(1)\n",
            [("fixture.py", "f", 4, False)],
        ),
        ("def f():\n    make = lambda: CommandService(1)\n    return make()\n", [("fixture.py", "f", 2, False)]),
        (
            "Alias = CommandService\n\nclass Sub(Alias):\n    pass\n\ndef f():\n    return Sub(1)\n",
            [("fixture.py", "f", 7, False)],
        ),
    ],
    ids=["functools-partial", "attrgetter-from-import", "lambda", "alias-subclass"],
)
def test_n3_each_named_evasion_is_seen(source: str, expected: list) -> None:
    assert _service_constructions("fixture.py", source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "from research_system.command.service import CommandService as Svc\n\ndef f():\n    return Svc(1)\n",
        "from functools import partial as p\n\ndef f():\n    return p(CommandService, 1)()\n",
        "from typing import Any\nfrom functools import partial\n\nfactory: Any = partial(CommandService, 1)\n\n"
        "def f():\n    return factory()\n",
        "def f():\n    if (made := CommandService):\n        return made(1)\n",
    ],
    ids=["import-alias", "partial-import-alias", "annotated-partial", "walrus"],
)
def test_n3_finding_constructions_the_census_does_not_see(source: str) -> None:
    """Finding m-3: four spellings that construct ``CommandService`` without a check and that the census reports as no
    construction at all. The string backstop does not see them either: none holds the class name as a string."""
    assert _service_constructions("fixture.py", source) == []
    assert _service_name_strings(source) == []


# --- LR-016 to LR-020 at replay -----------------------------------------------------------------------------------


@pytest.fixture
def actors() -> Actors:
    from tests.research_system.factories import ACTORS

    return Actors(owner=ACTORS["actor-a"])


@pytest.fixture
def flow(base, actors):  # noqa: F811
    forger, records = _full_flow(base[0], actors)
    return forger, records, base[1]


def _replay(forger, schemas) -> dict[str, Any]:
    return replay_legacy(forger.events, schemas=schemas, pinned_signatures=(PIN,))


def _lr020(forger, actors, record, transitions, when: float):
    """LR-020's transaction, as ``w9_flows.acceptance_recorded`` builds it, appended at ``when``."""
    review_id = record["independent_review_ref"]["id"]
    decision_id = record["decision_ref"]["id"]
    proposal = flows.decision_proposal("LR-019", record, decision_id, at(63))
    grant = flows.new_id("authority_grant")
    resolved = flows.resolution("LR-020", proposal, record, actors.owner, grant, at(when), [review_id])
    members = [
        ("DecisionResolved", decision_id, resolved),
        ("LegacyClosedReferenceAcceptanceRecorded", record["record_id"], deepcopy(record)),
        *(("LegacyOwnershipTransitionedRecorded", t["record_id"], deepcopy(t)) for t in transitions),
    ]
    return forger.append("ResolveW9AuthorityDecision", members, actor=actors.owner, when=at(when), grant=grant)


def test_the_lr020_helper_reproduces_the_positive_flow(flow, actors) -> None:
    """Positive control for the next probe: the hand-built LR-020 replays when nothing lands in between."""
    forger, records, schemas = flow
    record = flows.acceptance(forger.project_id, actors.analyst, at(60), [records["whole"]])
    expected = [flows.ownership_transition(record, records["registration"])]
    forger = flows.acceptance_recorded(forger, actors, record, expected, stop_after="LR-019")
    state = _replay(_lr020(forger, actors, record, expected, 64), schemas)
    assert state["ownership"] == {records["registration"]["record_id"]: "closed_reference"}


def test_an_item_made_stale_between_lr016_and_lr020_is_refused_at_lr020_by_replay(flow, actors) -> None:
    """§7.2 and §10.1: LR-020 refuses an item that is stale in the projection, re-checked at replay, not only by the
    preparer's re-read. A new observation of the registration lands after LR-019."""
    forger, records, schemas = flow
    record = flows.acceptance(forger.project_id, actors.analyst, at(60), [records["whole"]])
    expected = [flows.ownership_transition(record, records["registration"])]
    forger = flows.acceptance_recorded(forger, actors, record, expected, stop_after="LR-019")
    later = flows.observation(
        forger.project_id,
        actors.observer,
        at(63.5),
        records["registration"],
        PIN,
        count=2,
        source=flows.tracked(sha256="b" * 64, blob="2" * 40),
    )
    forger = forger.row("LR-015", later["record_id"], later, actor=actors.observer, when=at(63.5))
    with pytest.raises(IntegrityError, match="W9 acceptance item's observation is stale"):
        _replay(_lr020(forger, actors, record, expected, 64), schemas)


def test_the_ownership_id_is_a_pure_function_of_its_inputs_and_differs_by_each(flow, actors) -> None:
    """§10.5: the ID depends on the acceptance ID, the registration ID and the proposal's created_at, and on nothing
    the projection holds; changing any one input changes it."""
    from research_system.legacy.records import ownership_record_id

    one = ownership_record_id("obj_a", "obj_r", "2026-11-11T00:00:00.000Z")
    assert one == ownership_record_id("obj_a", "obj_r", "2026-11-11T00:00:00.000Z")
    assert (
        len(
            {
                one,
                ownership_record_id("obj_b", "obj_r", "2026-11-11T00:00:00.000Z"),
                ownership_record_id("obj_a", "obj_s", "2026-11-11T00:00:00.000Z"),
                ownership_record_id("obj_a", "obj_r", "2026-11-11T00:00:00.001Z"),
            }
        )
        == 4
    )


def _complete_family_set(forger, actors, records, when: float, count: int) -> dict[str, Any]:
    table = forger_table(forger, records)
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
            "family_names": [family["name"] for family in table["families"]],
        },
        families=[flows.signed_family(family["name"], PIN) for family in table["families"]],
    )


def forger_table(forger, records) -> dict[str, Any]:
    state = replay_legacy(forger.events, schemas=None, pinned_signatures=(PIN,))
    tables = state["records"]["legacy_field_family_membership"]
    assert len(tables) == 1
    return next(iter(tables.values()))


def test_builder_finding_a_complete_family_set_with_no_membership_record_previews_no_transition(flow, actors) -> None:
    """Finding m-2: batch mode admits ``"membership": null`` for a ``json_family_set`` observation and previews that
    the item transitions nothing, where replay derives a transition for the same batch."""
    forger, records, schemas = flow
    complete = _complete_family_set(forger, actors, records, 55, 2)
    forger = forger.row("LR-015", complete["record_id"], complete, actor=actors.observer, when=at(55))
    state = _replay(forger, schemas)
    record = flows.acceptance(forger.project_id, actors.analyst, at(60), [complete])
    assert len(reducers.derive_ownership(state, record)) == 1  # replay: the item covers the whole file
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
    _, preview = build_acceptance_batch(batch)
    assert preview[0]["transitions"] is False  # the builder: no transition, and no refusal
    batch["items"][0]["membership"] = forger_table(forger, records)
    _, preview = build_acceptance_batch(batch)
    assert preview[0]["transitions"] is True


# --- §10.2: pilot_promotion, through the guard's own predicate ---------------------------------------------------


def _entries(*fixtures: str, disposition: str = "evidence", prefix: str = "review") -> list[dict[str, Any]]:
    return [{"fixture_id": f, "disposition": disposition, "ref": flows.evidence_ref(prefix)} for f in fixtures]


def test_pilot_promotion_the_three_fixture_reading_is_refused_and_each_conditional_is_optional() -> None:
    with pytest.raises(IntegrityError, match="lacks the unconditional fixture F-037"):
        reducers._check_pilot_promotion({"pilot_promotion": _entries("F-017", "F-018", "F-023")})
    reducers._check_pilot_promotion({"pilot_promotion": _entries("F-018", "F-023", "F-037", "S-014")})
    for conditional in ("F-017", "S-005", "F-038"):
        reducers._check_pilot_promotion({"pilot_promotion": _entries("F-018", "F-023", "F-037", "S-014", conditional)})


@pytest.mark.parametrize("outside", ["S-007", "F-015", "F-006", "S-015", "F-999"])
def test_q2_a_fixture_outside_lr020s_seven_is_refused(outside: str) -> None:
    with pytest.raises(IntegrityError, match=f"lists a fixture LR-020 does not name: {outside}"):
        reducers._check_pilot_promotion({"pilot_promotion": _entries("F-018", "F-023", "F-037", "S-014", outside)})


@pytest.mark.parametrize(
    ("disposition", "prefix", "message"),
    [
        ("evidence", "decision", "evidence ref must be a review or an artefact"),
        ("evidence", "task", "evidence ref must be a review or an artefact"),
        ("evidence", "scope_definition", "evidence ref must be a review or an artefact"),
        ("waiver", "review", "waiver ref must be a Decision"),
    ],
)
def test_pilot_promotion_ref_kinds_are_refused_by_the_predicate(disposition: str, prefix: str, message: str) -> None:
    entries = _entries("F-018", "F-023", "F-037") + _entries("S-014", disposition=disposition, prefix=prefix)
    with pytest.raises(IntegrityError, match=message):
        reducers._check_pilot_promotion({"pilot_promotion": entries})


# --- §10.3: anchors on a scratch repository --------------------------------------------------------------------------


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "anchors"
    repo.mkdir()
    for args in (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "r@example.invalid"),
        ("config", "user.name", "R"),
    ):
        _git(repo, *args)
    return repo


def _commit(repo: Path, name: str, data: bytes, message: str) -> str:
    (repo / name).write_bytes(data)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _anchored(commit_t: str, commit_g: str, t: bytes, g: bytes) -> dict[str, Any]:
    return {
        "threshold_preregistration_sha256": hashlib.sha256(t).hexdigest(),
        "governing_record_set_sha256": hashlib.sha256(g).hexdigest(),
        "anchors": [
            {"anchored": "threshold_preregistration", "anchor_kind": "git_commit", "value": commit_t},
            {"anchored": "governing_record_set", "anchor_kind": "git_commit", "value": commit_g},
        ],
    }


def test_anchors_the_merge_commit_reading_and_the_root_commit(tmp_path: Path) -> None:
    """The record's reading (against the first parent): a merge commit introduces what its side branch added, a root
    commit introduces its whole tree, and an ancestor that did not touch the bytes is refused (W9-T16)."""
    repo = _repo(tmp_path)
    t, g = b"threshold\n", b"governing\n"
    root = _commit(repo, "t.txt", t, "root")
    _git(repo, "checkout", "-q", "-b", "side")
    side = _commit(repo, "g.txt", g, "side adds g")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "other.txt", b"x\n", "main moves")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge side", "side")
    merge = _git(repo, "rev-parse", "HEAD")
    acceptance.check_anchors(repo, merge, _anchored(root, merge, t, g))
    acceptance.check_anchors(repo, merge, _anchored(root, side, t, g))
    with pytest.raises(IntegrityError, match="does not introduce the anchored bytes"):
        acceptance.check_anchors(repo, merge, _anchored(merge, merge, t, g))  # the merge did not add t.txt
    with pytest.raises(IntegrityError, match="not an ancestor of git_head"):
        acceptance.check_anchors(repo, root, _anchored(root, side, t, g))


# --- §12.2: the export and its recheck ------------------------------------------------------------------------------


def _reference_tool():
    spec = importlib.util.spec_from_file_location(
        "w9_segmentation_reference", REPO_ROOT / "tools" / "w9_segmentation.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_the_export_and_its_recheck_are_two_implementations() -> None:
    """§12.2 (review M-4): different files and blobs, neither imports the other, and the recheck calls the runtime's."""
    runtime = REPO_ROOT / "research_system" / "legacy" / "segmentation.py"
    reference = REPO_ROOT / "tools" / "w9_segmentation.py"
    assert _git(REPO_ROOT, "rev-parse", f"{HEAD}:tools/w9_segmentation.py").startswith("43e1454d")
    assert _git(REPO_ROOT, "rev-parse", f"{HEAD}:research_system/legacy/segmentation.py") != _git(
        REPO_ROOT, "rev-parse", f"{HEAD}:tools/w9_segmentation.py"
    )
    assert not any("w9_segmentation" in name for name in _imports(runtime))
    assert not any(name.startswith("research_system") for name in _imports(reference))
    recheck = _imports(REPO_ROOT / "research_system" / "legacy" / "export_recheck.py")
    assert "research_system.legacy.segmentation" in recheck
    assert not any("w9_segmentation" in name for name in recheck)


def _synthetic_log(rng: random.Random) -> bytes:
    lines = ["---", "title: synthetic", "---", "", "# Computational log", ""]
    for _ in range(rng.randint(1, 8)):
        level = rng.choice(["##", "###"])
        date = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        head = rng.choice([f"{level} {date} entry", f"{level} {date}", f"{level} 7 not a date", f"{level} notes"])
        lines.append(head)
        for _ in range(rng.randint(0, 3)):
            lines.append(rng.choice(["Body line.", "- bullet", "#### deeper", "", "  indented", "| a | b |"]))
    eol = rng.choice(["\n", "\r\n"])
    return (eol.join(lines) + rng.choice(["", eol])).encode()


def _export(tool, raw: bytes, region: tuple[int, int]) -> dict[str, Any]:
    segmentation = tool.segment(raw, "computational_log_entry", region=region)
    return {
        "format": evidence.CL_EXPORT_FORMAT,
        "selector": {
            "selector_kind": "computational_log_entry",
            "region": {"first_line": region[0], "last_line": region[1]},
        },
        "segmentation": segmentation,
        "read": {
            "started_at": "2026-11-11T00:00:00Z",
            "ended_at": "2026-11-11T00:00:01Z",
            "path_form": {},
            "limits": [],
        },
        "retained_copy": {
            "repository_path": ".research-system/evidence/w9/cl-copy.md",
            "git_blob": hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw),
        },
        "classifications": [{"ordinal": row["row_ordinal"], "class": None} for row in segmentation["rows"]],
        "producer": dict(evidence.CL_EXPORT_PRODUCER),
    }


def test_the_reference_tools_segment_output_is_exactly_the_exports_segmentation_member_and_reproduces() -> None:
    """The ``w9-cl-export/1`` reading: ``segmentation`` is the reference tool's ``segment()`` output verbatim. Over 400
    seeded synthetic logs (seed 20261111), the export is admitted and the runtime segmenter reproduces it."""
    tool = _reference_tool()
    rng = random.Random(20261111)
    for _ in range(400):
        raw = _synthetic_log(rng)
        count = raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)
        first = rng.randint(5, max(5, count))
        region = (first, rng.randint(first, max(first, count)))
        export = _export(tool, raw, region)
        report = recheck_cl_export(export, raw)
        assert report["void"] is False, (raw, region, report)


def test_finding_i_the_recheck_cannot_see_a_narrowed_region() -> None:
    """Info i-3: the recheck re-segments the region the export declares. An export cut to a narrower region, with its
    rows produced for that region, reproduces; that the region is the legacy region is L-0b's and Stephen's."""
    tool = _reference_tool()
    raw = b"---\nt: x\n---\n\n## 2026-01-01 a\nbody\n## 2026-01-02 b\nbody\n## 7 broken\nbody\n"
    full = _export(tool, raw, (5, 10))
    narrow = _export(tool, raw, (5, 8))
    assert len(full["segmentation"]["rows"]) > len(narrow["segmentation"]["rows"])
    assert recheck_cl_export(narrow, raw)["void"] is False


WP9_3_2_TESTS = (
    "tests/research_system/integration/test_w9_wp9_3_2_batch_build.py",
    "tests/research_system/integration/test_w9_wp9_3_2_replay.py",
    "tests/research_system/integration/test_w9_wp9_3_2_runtime.py",
    "tests/research_system/unit/test_w9_apm_inventory.py",
    "tests/research_system/unit/test_w9_evidence_acceptance.py",
    "tests/research_system/unit/test_w9_export_recheck.py",
)


def test_the_recheck_never_runs_on_the_live_log() -> None:
    """§12.2: no WP9.3 production module and no WP9.3-2 test names the live Computational-Log page or the vault.
    (Three older W9 tests name the page as a refused path: the reader's refusal controls, not reads.)"""
    hits = []
    for path in [
        *(REPO_ROOT / "research_system" / "legacy").glob("*.py"),
        *(REPO_ROOT / name for name in WP9_3_2_TESTS),
    ]:
        text = path.read_text(encoding="utf-8")
        if "Computational-Log.md" in text or "TDA-Research" in text:
            hits.append(path.relative_to(REPO_ROOT).as_posix())
    assert hits == []


# --- §12.3, §12.4: the .apm/ tools read only ----------------------------------------------------------------------


def test_the_apm_tools_open_no_store_and_write_nothing_under_apm(tmp_path: Path) -> None:
    from research_system.legacy.apm_inventory import apm_universe, build_bus_inventory
    from research_system.legacy.inventory import refuse_tool_output
    from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes

    repo = tmp_path / "repo"
    (repo / ".apm" / "bus" / "agent").mkdir(parents=True)
    (repo / ".apm" / "memory" / "stage-01").mkdir(parents=True)
    (repo / ".apm" / "bus" / "agent" / "msg.json").write_text("{}", encoding="utf-8")
    (repo / ".apm" / "memory" / "stage-01" / "log.md").write_text("x", encoding="utf-8")
    (repo / ".apm" / "plan.md").write_text("plan", encoding="utf-8")
    _git(tmp_path, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "r@example.invalid")
    _git(repo, "config", "user.name", "R")
    _git(repo, "add", ".apm/plan.md")
    _git(repo, "commit", "-q", "-m", "plan")
    before = _tree_bytes(repo / ".apm")
    inventory = build_bus_inventory(repo / ".apm")
    assert [entry["path"] for entry in inventory["files"]] == ["agent/msg.json"]
    assert apm_universe(repo, _git(repo, "rev-parse", "HEAD")) == [
        ".apm/bus/agent/msg.json",
        ".apm/memory/stage-01/log.md",
        ".apm/plan.md",
    ]
    assert _tree_bytes(repo / ".apm") == before
    for forbidden in (repo / ".apm" / "out.json", repo / "out.json"):
        with pytest.raises(IntegrityError):
            refuse_tool_output(forbidden, repository_root=repo, vault_root=tmp_path / "vault")
    source = (REPO_ROOT / "research_system" / "legacy" / "apm_inventory.py").read_text(encoding="utf-8")
    for opener in ("EventLedger", "ControlBinding", "load_current_binding", "open(", "write_"):
        assert opener not in source


# --- D-4 and the boundary ----------------------------------------------------------------------------------------


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
    for path, prefix in (
        ("tests/research_system/smoke/wp6_1_06h_current_append_manifest.yaml", "4c895042"),
        ("tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py", "559d684a"),
        ("tools/w9_segmentation.py", "43e1454d"),
    ):
        assert _git(REPO_ROOT, "rev-parse", f"{HEAD}:{path}").startswith(prefix)


def test_the_diff_stays_inside_the_boundary() -> None:
    """P-080's boundary as P-081 item 10 extends it: production code only under ``research_system/legacy/`` and
    ``research_system/cli.py``; no protected tree changes."""
    changed = _git(REPO_ROOT, "diff", "--name-only", BASE, HEAD).splitlines()
    production = [p for p in changed if p.startswith("research_system/")]
    assert production and all(
        p.startswith("research_system/legacy/") or p == "research_system/cli.py" for p in production
    )
    protected = (
        ".research-system/",
        "contracts/",
        "research_system/command/",
        "research_system/store/",
        "research_system/discovery/",
        "research_system/projection/",
        "research_system/schema_registry.py",
        "research_system/authority.py",
        "research_system/legacy/accepted_w9.py",
        "research_system/legacy/segmentation.py",
        "tools/w9_segmentation.py",
        "tests/research_system/smoke/",
    )
    assert [p for p in changed if p.startswith(protected)] == []
    assert [p for p in changed if p.startswith("tools/")] == ["tools/research_system_durations.json"]


# --- Genesis and guard 8 (owner point F; P-081 item 6) ----------------------------------------------------------


def _accepted_catalogue() -> dict[str, Any]:
    import json

    return json.loads(
        (REPO_ROOT / ".research-system/evals/expected/w9-legacy-integration-v1.json").read_text(encoding="utf-8")
    )


def test_genesis_guard_8_holds_the_19_42_partition_and_refuses_a_broken_one(monkeypatch) -> None:
    from research_system.legacy import routes

    routes.validate_legacy_route_registry(_accepted_catalogue())
    assert len(routes.LEGACY_ROUTED_ROWS) == 19 and len(routes.LEGACY_DEFERRED_ROWS) == 42
    assert routes.LEGACY_ROUTED_ROWS == {"LR-001", *(f"LR-{n:03d}" for n in range(3, 21))}
    assert "WP9.3" not in set(routes.LEGACY_DEFERRED_ROWS.values())
    for routed, deferred, label in (
        (routes.LEGACY_ROUTED_ROWS - {"LR-020"}, routes.LEGACY_DEFERRED_ROWS, "missing"),
        (routes.LEGACY_ROUTED_ROWS, {**routes.LEGACY_DEFERRED_ROWS, "LR-020": "WP9.3"}, "overlap"),
        (routes.LEGACY_ROUTED_ROWS - {"LR-020"}, {**routes.LEGACY_DEFERRED_ROWS, "LR-020": "WP9.9"}, "bad tag"),
    ):
        monkeypatch.setattr(routes, "LEGACY_ROUTED_ROWS", frozenset(routed))
        monkeypatch.setattr(routes, "LEGACY_DEFERRED_ROWS", deferred)
        with pytest.raises(IntegrityError, match="does not partition the accepted W9 catalogue"):
            routes.validate_legacy_route_registry(_accepted_catalogue())
        monkeypatch.undo()


def test_a_real_w9_genesis_on_a_scratch_store_replays_at_this_head(tmp_path: Path, monkeypatch) -> None:
    """The genesis path at ``b98515c6``: W11 genesis, then W9 genesis through ``LegacyRuntime.submit`` on a scratch
    store, then every public replay over the ledger."""
    from research_system.discovery.runtime import replay_discovery
    from research_system.projection.replay import replay as replay_projection
    from tests.research_system.integration.w9_runtime_harness import w9_store

    store = w9_store(tmp_path, monkeypatch)
    events = store.events()
    assert [event.get("event_type") for event in events].count("W9CatalogueGenesisImported") == 1
    replay_projection(events, schema_registry=store.harness.schemas)
    replay_discovery(events, schemas=store.harness.schemas)
    state = replay_legacy(events, schemas=store.harness.schemas, pinned_signatures=(store.pin,))
    assert state["catalogue"] is not None
    assert state["row_counts"].get("LR-001") == 1
