# Research context: 2026-10-02 research_system suite triage (obs 2026-10-03-shared-seam-change-merged-without-its-dependents)
# Purpose: Controls for the research_system CI lanes: affected-test selection, duration
# sharding, the shrink-only known-failures baseline, and the workflow that wires them.
"""Controls for the research_system CI lane tools.

A lane that silently selects, shards or judges nothing passes green while the suite rots,
which is how 195 failures reached main unseen. Each tool therefore has a positive case and a
negative control here, and the selector is checked against the real seams whose changes
broke main on 2026-10-02.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "research-system-suite.yml"
KNOWN_FAILURES = TOOLS / "research_system_known_failures.txt"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


affected = _load("affected_research_tests")
shards = _load("research_system_shards")
baseline = _load("research_system_baseline")


# --- affected-test selection -------------------------------------------------------------

PACKAGE = {
    "research_system/store/ledger.py": "import json\n",
    "research_system/store/__init__.py": "from research_system.store.ledger import EventLedger\n",
    "research_system/command/service.py": "from research_system.store import EventLedger\n",
    "research_system/command/lifecycle.py": "from .service import submit\n",
    "research_system/config.py": "import pathlib\n",
    # A facade package that re-exports with a relative import, like research_system/methods.
    "research_system/methods/__init__.py": "from .pack import MethodsPack\n",
    "research_system/methods/pack.py": "import json\n",
}
TESTS = {
    "tests/research_system/integration/test_service.py": "from research_system.command.service import submit\n",
    "tests/research_system/integration/test_lifecycle.py": "from research_system.command import lifecycle\n",
    "tests/research_system/unit/test_config.py": "from research_system.config import load\n",
    "tests/research_system/contracts/helper.py": "from research_system.config import load\n",
    "tests/research_system/contracts/test_uses_helper.py": "from tests.research_system.contracts.helper import x\n",
    "tests/research_system/contracts/test_pack.py": "PACKS = '.research-system/packs'\n",
    "tests/research_system/contracts/test_methods.py": "from research_system.methods import MethodsPack\n",
}


def _select(*changed: str, pinned: str = "") -> list[str]:
    return affected.select(list(changed), TESTS, PACKAGE, pinned)


def test_a_seam_change_selects_its_transitive_dependents_through_a_facade() -> None:
    picked = _select("research_system/store/ledger.py")
    assert "tests/research_system/integration/test_service.py" in picked
    assert "tests/research_system/integration/test_lifecycle.py" in picked  # via a relative import
    assert "tests/research_system/unit/test_config.py" not in picked  # negative control


def test_a_test_tree_helper_change_selects_its_importers() -> None:
    assert _select("tests/research_system/contracts/helper.py") == [
        "tests/research_system/contracts/test_uses_helper.py"
    ]


def test_a_relative_reexport_in_a_package_init_reaches_the_package_importers() -> None:
    # In a package's __init__.py, "from .pack import X" names research_system.methods.pack,
    # not research_system.pack. CodeRabbit review on #329.
    picked = _select("research_system/methods/pack.py")
    assert picked == ["tests/research_system/contracts/test_methods.py"]


def test_a_package_change_reaches_tests_through_a_helper() -> None:
    picked = _select("research_system/config.py")
    assert picked == [
        "tests/research_system/contracts/test_uses_helper.py",
        "tests/research_system/unit/test_config.py",
    ]


def test_a_changed_test_selects_itself_and_a_helper_selects_no_non_test_file() -> None:
    assert _select("tests/research_system/unit/test_config.py") == ["tests/research_system/unit/test_config.py"]
    assert all(Path(path).name.startswith("test_") for path in _select("research_system/config.py"))


@pytest.mark.parametrize("conftest", ["tests/conftest.py", "conftest.py", "tests/research_system/unit/conftest.py"])
def test_a_governing_conftest_selects_every_test(conftest: str) -> None:
    assert _select(conftest) == sorted(path for path in TESTS if Path(path).name.startswith("test_"))


@pytest.mark.parametrize("conftest", ["tests/research/conftest.py", "tests/financial/conftest.py"])
def test_an_unrelated_conftest_selects_nothing(conftest: str) -> None:
    assert _select(conftest) == []


def test_a_pinned_non_python_path_selects_contracts_and_pack_loaders() -> None:
    picked = _select(".gitattributes", pinned="path: .gitattributes\n")
    assert "tests/research_system/contracts/test_pack.py" in picked
    assert "tests/research_system/contracts/test_uses_helper.py" in picked  # every contract test
    assert "tests/research_system/integration/test_service.py" not in picked


def test_an_unpinned_document_selects_nothing() -> None:
    assert _select("docs/README.md", pinned="path: .gitattributes\n") == []


REAL_SEAMS = {
    "research_system/command/service.py": "tests/research_system/integration/test_authority_grant_source.py",
    "research_system/store/writer.py": "tests/research_system/integration/test_scoped_authority_grant_activation.py",
    "research_system/assurance/external_records.py": (
        "tests/research_system/contracts/test_external_record_envelope_and_resolver.py"
    ),
    "research_system/discovery/replay/driver.py": "tests/research_system/integration/test_wp6_6_discovery_runtime.py",
    ".agents/skills/research-assurance-triage/SKILL.md": (
        "tests/research_system/integration/test_assurance_pack_runner.py"
    ),
    ".gitattributes": "tests/research_system/contracts/test_wp6_2_live_issue_contract.py",
    "research_system/store/ledger.py": "tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py",
    "research_system/config.py": "tests/research_system/integration/test_authority_grant_source.py",
    # Reached only through research_system/methods/__init__.py's relative re-export.
    "research_system/methods/pack.py": "tests/research_system/contracts/test_methods_pack_contract.py",
    "tests/research_system/contracts/wp6_2_t2_expectations.py": (
        "tests/research_system/contracts/test_wp6_2_t2_authority_contract.py"
    ),
}


@pytest.fixture(scope="module")
def real_tree() -> tuple[dict[str, str], dict[str, str], str]:
    tests = {
        path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / affected.TEST_ROOT).rglob("*.py")
    }
    return tests, affected._package_sources(), affected._pinned_text()


@pytest.mark.parametrize("changed, dependent", sorted(REAL_SEAMS.items()), ids=sorted(REAL_SEAMS))
def test_each_2026_10_02_culprit_seam_selects_the_test_it_broke(
    real_tree: tuple[dict[str, str], dict[str, str], str], changed: str, dependent: str
) -> None:
    """Each pair is a change that broke the named test on main while CI ran nothing."""
    tests, package, pinned = real_tree
    assert (REPO_ROOT / changed).is_file() and (REPO_ROOT / dependent).is_file()
    assert dependent in affected.select([changed], tests, package, pinned)


def test_a_real_documentation_change_selects_nothing(real_tree: tuple[dict[str, str], dict[str, str], str]) -> None:
    tests, package, pinned = real_tree
    document = "docs/plans/strategy/Meta-Research-Plan-23-03-2026.md"
    assert (REPO_ROOT / document).is_file()
    assert affected.select([document], tests, package, pinned) == []


# --- sharding ----------------------------------------------------------------------------


def test_every_real_test_file_lands_in_exactly_one_shard() -> None:
    files = shards.discover()
    buckets = shards.assign(files, shards.load_weights(), 8)
    placed = [name for bucket in buckets for name in bucket]
    assert len(files) > 100
    assert sorted(placed) == files and len(placed) == len(set(placed))
    assert all(buckets)


def test_assignment_is_heaviest_first_on_the_lightest_shard() -> None:
    weights = {"a": 10, "b": 7, "c": 5, "d": 4, "e": 1}
    # a->1 (10), b->2 (7), c->2 (12), d->1 (14), e->2 (13)
    assert shards.assign(list(weights), weights, 2) == [["a", "d"], ["b", "c", "e"]]
    assert shards.assign(list(weights), weights, 2) == shards.assign(sorted(weights, reverse=True), weights, 2)


def test_recorded_durations_are_positive_and_cover_most_files() -> None:
    weights = shards.load_weights()
    files = shards.discover()
    assert all(seconds > 0 for seconds in weights.values())
    assert sum(name in weights for name in files) >= 0.9 * len(files)


def _shards_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / "research_system_shards.py"), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )


def test_a_selection_is_sharded_and_its_empty_shards_are_not_errors(tmp_path: Path) -> None:
    chosen = shards.discover()[:3]
    selection = tmp_path / "selection.txt"
    selection.write_text("\n".join(chosen) + "\n", encoding="utf-8")
    outputs = [_shards_cli("--of", "8", "--shard", str(k), "--files", str(selection)) for k in range(1, 9)]
    assert all(run.returncode == 0 for run in outputs)
    assert sorted(line for run in outputs for line in run.stdout.splitlines()) == sorted(chosen)


def test_a_selection_naming_an_unknown_file_is_refused(tmp_path: Path) -> None:
    selection = tmp_path / "selection.txt"
    selection.write_text("tests/research_system/unit/test_does_not_exist.py\n", encoding="utf-8")
    run = _shards_cli("--of", "8", "--shard", "1", "--files", str(selection))
    assert run.returncode != 0 and "not research_system tests" in run.stderr


def test_an_empty_shard_of_the_whole_suite_is_an_error() -> None:
    run = _shards_cli("--of", "100000", "--shard", "100000")
    assert run.returncode == 1 and "is empty" in run.stderr


# --- known-failures baseline --------------------------------------------------------------

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest">
<testcase classname="tests.research_system.unit.test_a" name="test_pass"/>
<testcase classname="tests.research_system.unit.test_a.TestGroup" name="test_param[x-1]"/>
<testcase classname="tests.research_system.unit.test_a" name="test_known"><failure message="m"/></testcase>
<testcase classname="tests.research_system.unit.test_a" name="test_skip"><skipped message="s"/></testcase>
{extra}
</testsuite></testsuites>
"""
KNOWN = "tests/research_system/unit/test_a.py::test_known"


def _report(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "report.xml"
    path.write_text(JUNIT.format(extra=extra), encoding="utf-8")
    return path


def _check(tmp_path: Path, report: Path, *entries: str) -> subprocess.CompletedProcess[str]:
    listed = tmp_path / "known.txt"
    listed.write_text("# comment\n\n" + "\n".join(entries) + "\n", encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(TOOLS / "research_system_baseline.py"), "--baseline", str(listed), str(report)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_node_ids_are_rebuilt_from_pytest_classnames(tmp_path: Path) -> None:
    results = baseline.outcomes([_report(tmp_path)])
    assert results == {
        "tests/research_system/unit/test_a.py::test_pass": "passed",
        "tests/research_system/unit/test_a.py::TestGroup::test_param[x-1]": "passed",
        KNOWN: "failed",
        "tests/research_system/unit/test_a.py::test_skip": "skipped",
    }


def test_a_listed_failure_passes_the_baseline(tmp_path: Path) -> None:
    assert _check(tmp_path, _report(tmp_path), KNOWN).returncode == 0


@pytest.mark.parametrize(
    "extra",
    [
        '<testcase classname="tests.research_system.unit.test_b" name="test_new"><failure message="m"/></testcase>',
        '<testcase classname="tests.research_system.unit.test_b" name="test_new"><error message="m"/></testcase>',
    ],
    ids=["failure", "error"],
)
def test_an_unlisted_failure_or_error_fails_the_baseline(tmp_path: Path, extra: str) -> None:
    run = _check(tmp_path, _report(tmp_path, extra), KNOWN)
    assert (
        run.returncode == 1
        and "new failure (not in baseline): tests/research_system/unit/test_b.py::test_new" in run.stderr
    )


def test_a_listed_entry_that_now_passes_fails_the_baseline(tmp_path: Path) -> None:
    run = _check(tmp_path, _report(tmp_path), KNOWN, "tests/research_system/unit/test_a.py::test_pass")
    assert run.returncode == 1 and "baseline entry now passes; remove it" in run.stderr


def test_a_report_with_no_tests_fails_the_baseline(tmp_path: Path) -> None:
    empty = tmp_path / "empty.xml"
    empty.write_text('<testsuites><testsuite name="pytest"/></testsuites>', encoding="utf-8")
    run = _check(tmp_path, empty)
    assert run.returncode == 1 and "no executed tests" in run.stderr


def test_listed_entries_absent_from_a_shard_and_skipped_entries_are_ignored(tmp_path: Path) -> None:
    entries = (
        KNOWN,
        "tests/research_system/unit/test_other.py::test_x",
        "tests/research_system/unit/test_a.py::test_skip",
    )
    assert _check(tmp_path, _report(tmp_path), *entries).returncode == 0


def test_every_known_failure_names_a_real_test() -> None:
    """A typo or stale entry would tolerate nothing while looking like a recorded decision."""
    entries = baseline.load_baseline(KNOWN_FAILURES)
    assert entries
    for entry in entries:
        path, *_, name = entry.split("::")
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert f"def {name.split('[', 1)[0]}(" in source, entry


# --- workflow wiring ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _script(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_the_workflow_runs_nightly_on_demand_and_on_pull_requests(workflow: dict) -> None:
    triggers = workflow["on"]
    assert triggers["schedule"] and "workflow_dispatch" in triggers and "pull_request" in triggers
    assert "paths" not in triggers["pull_request"], "a path filter leaves a required check pending"


def test_every_shard_is_in_the_matrix_and_judged_by_the_baseline(workflow: dict) -> None:
    suite = workflow["jobs"]["suite"]
    assert [int(k) for k in suite["strategy"]["matrix"]["shard"]] == list(range(1, int(workflow["env"]["SHARDS"]) + 1))
    script = _script(suite)
    assert "--files selection.txt" in script
    assert '-m "not live_store"' in script
    assert "tools/research_system_baseline.py" in script and "tools/research_system_known_failures.txt" in script
    assert "continue-on-error" not in suite
    assert all("continue-on-error" not in step for step in suite["steps"])


def test_selection_uses_the_affected_selector_on_pull_requests_and_everything_otherwise(workflow: dict) -> None:
    script = _script(workflow["jobs"]["select"])
    assert "tools/affected_research_tests.py --base" in script
    assert "tools/research_system_shards.py --of 1 --shard 1" in script


def test_the_lane_runs_these_controls_and_refuses_skips(workflow: dict) -> None:
    script = _script(workflow["jobs"]["ci-tools"])
    assert "tests/tools/test_research_system_ci_tools.py" in script
    assert "tools/assert_no_skips.py ci-tools.xml" in script


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the shard step's controls cannot run, and must not silently skip")
    return found


def _run_shard_step(workflow: dict, tmp_path: Path, pytest_status: int) -> tuple[int, list[str]]:
    """Run the workflow's real shard script as GitHub runs it, with pytest replaced by a stub.

    GitHub runs ``shell: bash`` as ``bash --noprofile --norc -eo pipefail {0}``. The stub records
    the arguments it received and exits with ``pytest_status``. The shard file is written the way
    Windows Python writes it, with CRLF line endings.
    """
    step = next(step for step in workflow["jobs"]["suite"]["steps"] if step.get("name") == "Run this shard")
    invocation = ".venv/Scripts/python.exe -m pytest"
    assert step["run"].count(invocation) == 1, "the stub must replace exactly the pytest invocation"
    stub = 'fake_pytest() { printf "%s\\n" "$@" > args.txt; return "$FAKE_STATUS"; }\n'
    (tmp_path / "step.sh").write_bytes((stub + step["run"].replace(invocation, "fake_pytest")).encode("utf-8"))
    (tmp_path / "shard.txt").write_bytes(
        b"tests/research_system/unit/test_a.py\r\ntests/research_system/unit/test_b.py\r\n"
    )
    run = subprocess.run(
        [_bash(), "--noprofile", "--norc", "-eo", "pipefail", "step.sh"],
        cwd=tmp_path,
        env={**os.environ, "FAKE_STATUS": str(pytest_status), "RUNNER_TEMP": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    args = (tmp_path / "args.txt").read_bytes().decode("utf-8").split("\n") if (tmp_path / "args.txt").exists() else []
    return run.returncode, args


@pytest.mark.parametrize("pytest_status", [0, 1])
def test_a_test_outcome_reaches_the_baseline_step(workflow: dict, tmp_path: Path, pytest_status: int) -> None:
    # Exit 1 (tests failed) must not end the step under errexit, or the baseline step that
    # judges known failures never runs. CodeRabbit review on #329.
    returncode, _ = _run_shard_step(workflow, tmp_path, pytest_status)
    assert returncode == 0


@pytest.mark.parametrize("pytest_status", [2, 4, 5])
def test_a_non_test_pytest_exit_fails_the_step(workflow: dict, tmp_path: Path, pytest_status: int) -> None:
    returncode, _ = _run_shard_step(workflow, tmp_path, pytest_status)
    assert returncode == pytest_status


def test_shard_paths_reach_pytest_without_carriage_returns(workflow: dict, tmp_path: Path) -> None:
    # Windows Python writes shard.txt with CRLF, and mapfile -t keeps the \r. CodeRabbit review on #329.
    _, args = _run_shard_step(workflow, tmp_path, 0)
    assert "tests/research_system/unit/test_a.py" in args and "tests/research_system/unit/test_b.py" in args
    assert not any("\r" in arg for arg in args)
