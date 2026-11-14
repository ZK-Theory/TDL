# Research context: docs/plans/agentic-research-system/reviews/wp9-3-2-review-b98515c6-2026-11-11.md (P-080; P-083)
# Purpose: the reviewer's own probes of the CodeRabbit comments on PR #432 that bear on an assurance claim. Each
# asserts what the code does at b98515c6; a passing probe confirms the defect it names. Scratch trees under tmp_path.
"""Cross-check probes for WP9.3-2 at ``b98515c6``: the anchor's root-commit fallback, the ``.apm/`` file inventory's
closure checks, and the "latest for its selector" comparison."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system.errors import IntegrityError  # noqa: E402
from research_system.legacy import acceptance  # noqa: E402
from research_system.legacy.apm_inventory import CLOSURE_MAP_FORMAT, build_apm_file_inventory  # noqa: E402
from research_system.legacy.replay.driver import replay_legacy  # noqa: E402
from tests.research_system.integration import w9_flows as flows  # noqa: E402
from tests.research_system.integration.test_w9_wp9_3_replay import PIN, _full_flow  # noqa: E402
from tests.research_system.integration.test_w9_wp9_3_replay import base as base  # noqa: E402, F401
from tests.research_system.integration.w9_flows import Actors, at  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# --- n-3: the two census cases CodeRabbit names ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "reported"),
    [
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, binding_check=c)\n"
            "    alias = factory\n    return alias()\n",
            False,
        ),
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, binding_check=c)\n"
            "    return factory(binding_check=None)\n",
            True,
        ),
    ],
    ids=["checked-partial-through-an-alias-reported-unchecked", "call-time-None-override-reported-checked"],
)
def test_finding_m1_coderabbits_two_partial_cases(source: str, reported: bool) -> None:
    """Finding m-1, CodeRabbit's census comments (confirmed): a checked partial reached through an alias is reported
    unchecked (a false failure), and ``binding_check=None`` passed at the call is reported checked (a false pass)."""
    from tests.research_system.contracts.test_w9_wp9_3_censuses import _service_constructions

    assert [site[3] for site in _service_constructions("fixture.py", source)] == [reported]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def _init(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "r@example.invalid")
    _git(repo, "config", "user.name", "R")


def _commit(repo: Path, name: str, data: bytes) -> str:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)
    return _git(repo, "rev-parse", "HEAD")


# --- §10.3: a failed parent lookup is read as a root commit -------------------------------------------------------


def test_finding_m4_a_shallow_boundary_commit_passes_an_anchor_it_does_not_introduce(tmp_path: Path) -> None:
    """Finding m-4 (CodeRabbit acceptance.py:84, confirmed): ``_introduced_blobs`` treats any failed ``<commit>^1``
    lookup as a root commit and scans the whole tree. In a shallow clone the boundary commit's parent is absent, so an
    anchor naming a commit that only touched an unrelated file passes W9-T16's second control. In the full clone the
    same anchor is refused."""
    full = tmp_path / "full"
    _init(full)
    threshold, governing = b"threshold\n", b"governing\n"
    _commit(full, "t.txt", threshold)
    _commit(full, "g.txt", governing)
    unrelated = _commit(full, "unrelated.txt", b"x\n")
    record = {
        "threshold_preregistration_sha256": hashlib.sha256(threshold).hexdigest(),
        "governing_record_set_sha256": hashlib.sha256(governing).hexdigest(),
        "anchors": [
            {"anchored": "threshold_preregistration", "anchor_kind": "git_commit", "value": unrelated},
            {"anchored": "governing_record_set", "anchor_kind": "git_commit", "value": unrelated},
        ],
    }
    with pytest.raises(IntegrityError, match="does not introduce the anchored bytes"):
        acceptance.check_anchors(full, unrelated, record)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", full.resolve().as_uri(), str(shallow)], check=True, capture_output=True
    )
    assert _git(shallow, "rev-parse", "HEAD") == unrelated
    acceptance.check_anchors(shallow, unrelated, record)  # admitted: the defect


# --- §12.4: the file inventory's closure checks -------------------------------------------------------------------


def _apm_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    _init(repo)
    head = _commit(repo, ".apm/plan.md", b"plan\n")
    return repo, head


def test_finding_m5_a_non_import_entry_with_a_null_record_places_files_and_unblocks(tmp_path: Path) -> None:
    """Finding m-5 (CodeRabbit apm_inventory.py:152, confirmed): a non-import entry is checked for its outer keys only.
    ``"record": null`` places every listed file, and the report does not block, so W9-T18's "one non-import record"
    is not checked."""
    repo, head = _apm_repo(tmp_path)
    closure_map = {
        "format": CLOSURE_MAP_FORMAT,
        "closures": [],
        "non_import": [{"files": [".apm/plan.md"], "record": None}],
    }
    report = build_apm_file_inventory(repo, head, closure_map)
    assert report["blocked"] is False and report["missing"] == []


def test_finding_m5_a_linked_stage_directory_is_walked_outside_the_repository(tmp_path: Path) -> None:
    """Finding m-5 (CodeRabbit apm_inventory.py:93, confirmed where the OS allows a directory link): a ``stage-NN``
    that is a link to a directory outside the repository is walked, and its files are counted as ``.apm/`` files."""
    repo, head = _apm_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "foreign.md").write_bytes(b"not apm\n")
    (repo / ".apm" / "memory").mkdir(parents=True)
    try:
        os.symlink(outside, repo / ".apm" / "memory" / "stage-01", target_is_directory=True)
    except OSError:
        pytest.skip("this machine cannot create a directory symlink")
    closure_map = {
        "format": CLOSURE_MAP_FORMAT,
        "closures": [],
        "non_import": [
            {"files": [".apm/plan.md", ".apm/memory/stage-01/foreign.md"], "record": {"kind": "k", "sha256": "0" * 64}}
        ],
    }
    report = build_apm_file_inventory(repo, head, closure_map)
    assert ".apm/memory/stage-01/foreign.md" not in report["extra"]
    assert report["blocked"] is False


# --- §10.1: "the latest for its source and selector" ---------------------------------------------------------------


@pytest.fixture
def actors() -> Actors:
    from tests.research_system.factories import ACTORS

    return Actors(owner=ACTORS["actor-a"])


def test_finding_i_reordered_family_names_leave_the_earlier_observation_latest(base, actors) -> None:  # noqa: F811
    """Info (CodeRabbit reducers.py:558, confirmed): two complete family-set observations of one registration, with the
    names in the other order, are distinct selectors to the "latest" check, so a batch of the earlier one passes
    LR-016's replay. The bytes are the same, so nothing stale is accepted; the literal §10.1 rule is not met."""
    forger, records = _full_flow(base[0], actors)
    schemas = base[1]
    state = replay_legacy(forger.events, schemas=schemas, pinned_signatures=(PIN,))
    table = next(iter(state["records"]["legacy_field_family_membership"].values()))
    names = [family["name"] for family in table["families"]]
    assert len(names) >= 2

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
    replay_legacy(forger.events, schemas=schemas, pinned_signatures=(PIN,))  # admitted
