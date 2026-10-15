# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group C)
# Purpose: One control per record contract of tools/certify_packet.py, each run against a scratch repository
# with a tiny test suite, so the runner is shown refusing what each session-local copy once accepted.
"""Controls for ``tools/certify_packet.py``."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from tools import certify_packet as cp

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "certify_packet.py"

PASSING = "def test_one():\n    assert True\n\n\ndef test_two():\n    assert 1 + 1 == 2\n"
GUARDED = "def guard(x):\n    if x < 0:\n        raise ValueError('negative refused')\n    return x\n"
GUARD_TEST = (
    "import pytest\nfrom pkg import guard\n\n\n"
    "def test_guard_refuses_negative():\n    with pytest.raises(ValueError, match='negative refused'):\n"
    "        guard.guard(-1)\n"
)


def _git(repo: Path, *args: str) -> str:
    base = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null"]
    return subprocess.run([*base, *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with a guarded package and passing tests, committed on main. It has no ``.gitignore``, so
    anything the runner writes into it shows as dirt."""
    path = tmp_path / "subject"
    (path / "pkg").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "pkg" / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    (path / "pkg" / "guard.py").write_text(GUARDED, encoding="utf-8", newline="\n")
    (path / "tests" / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    (path / "tests" / "test_a.py").write_text(PASSING, encoding="utf-8", newline="\n")
    (path / "tests" / "test_guard.py").write_text(GUARD_TEST, encoding="utf-8", newline="\n")
    (path / "conftest.py").write_text("", encoding="utf-8", newline="\n")
    _git(path, "init", "-q", "-b", "main")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "seed")
    return path


def _collect(tmp_path: Path, nodes: list[str]) -> Path:
    path = tmp_path / "collect.txt"
    path.write_text("\n".join(nodes) + "\n", encoding="utf-8")
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    # A hosted runner leaves PYTHONDONTWRITEBYTECODE unset; a workstation that exports it hid the runner writing
    # bytecode into its subject, so the runner gets the hosted runner's environment here.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, check=False, env=env)


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD")


# --- contract 1 ---------------------------------------------------------------------------------------------


def test_a_selection_missing_a_node_of_a_touched_test_file_is_refused(repo: Path, tmp_path: Path) -> None:
    """Obs 2026-10-07-certification-selection-narrower-than-ci-missed-pr-regressions."""
    base = _head(repo)
    (repo / "tests" / "test_b.py").write_text(PASSING, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "touch test_b")
    sha = _head(repo)
    narrow = _collect(tmp_path, ["tests/test_a.py::test_one", "tests/test_b.py::test_one"])
    args = ["run", "--sha", sha, "--worktree", str(repo), "--collect", str(narrow), "--out", str(tmp_path / "o")]
    refused = _run(*args, "--base", base, "--dry-run")
    assert refused.returncode != 0
    assert "omits 1 node(s)" in refused.stderr and "tests/test_b.py::test_two" in refused.stderr

    admitted = _run(*args, "--base", base, "--dry-run", "--partial-reason", "test_two is covered by CI")
    assert admitted.returncode == 0, admitted.stderr
    full = _collect(tmp_path, ["tests/test_b.py::test_one", "tests/test_b.py::test_two"])
    args[args.index(str(narrow))] = str(full)
    assert _run(*args, "--base", base, "--dry-run").returncode == 0


# --- contract 5 ---------------------------------------------------------------------------------------------


def test_a_dirty_tree_is_refused_at_launch(repo: Path, tmp_path: Path) -> None:
    (repo / "notes.md").write_text("a brief committed later\n", encoding="utf-8")
    collect = _collect(tmp_path, ["tests/test_a.py::test_one"])
    result = _run("run", "--sha", _head(repo), "--worktree", str(repo), "--collect", str(collect),
                  "--out", str(tmp_path / "o"), "--dry-run")  # fmt: skip
    assert result.returncode != 0 and "not the clean SHA (at launch)" in result.stderr


def test_the_runner_leaves_no_bytecode_in_its_subject(repo: Path, tmp_path: Path) -> None:
    """Coverage collection wrote ``__pycache__/`` into the subject, so the next launch refused the runner's own
    droppings (admission-controls, red on main after #362). Bytecode git does not ignore is still dirt."""
    base = _head(repo)
    (repo / "tests" / "test_b.py").write_text(PASSING, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "touch test_b")
    collect = _collect(tmp_path, ["tests/test_b.py::test_one", "tests/test_b.py::test_two"])
    args = ["run", "--sha", _head(repo), "--worktree", str(repo), "--collect", str(collect), "--out",
            str(tmp_path / "o"), "--base", base, "--dry-run"]  # fmt: skip
    first = _run(*args)
    assert first.returncode == 0, first.stderr
    assert '"required_nodes": 2' in first.stdout, "the collection ran, so it had the chance to write bytecode"
    assert _git(repo, "status", "--porcelain", "--ignored") == "", "the runner left nothing, not even ignored files"
    again = _run(*args)
    assert again.returncode == 0, again.stderr

    (repo / "tests" / "__pycache__").mkdir()
    (repo / "tests" / "__pycache__" / "test_b.cpython-313.pyc").write_bytes(b"stale")
    refused = _run(*args)
    assert refused.returncode != 0 and "not the clean SHA (at launch)" in refused.stderr
    assert "tests/__pycache__/" in refused.stderr


def test_another_sha_is_refused_at_launch(repo: Path, tmp_path: Path) -> None:
    collect = _collect(tmp_path, ["tests/test_a.py::test_one"])
    result = _run("run", "--sha", "0" * 40, "--worktree", str(repo), "--collect", str(collect),
                  "--out", str(tmp_path / "o"), "--dry-run")  # fmt: skip
    assert result.returncode != 0 and "HEAD is" in result.stderr


# --- contracts 2 and 3 --------------------------------------------------------------------------------------


def _packet_run(repo: Path, tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    collect = _collect(tmp_path, ["tests/test_a.py::test_one", "tests/test_a.py::test_two"])
    result = _run("run", "--sha", _head(repo), "--worktree", str(repo), "--collect", str(collect),
                  "--out", str(tmp_path / "o"), "--now", "--workers", "2")  # fmt: skip
    folder = cp.RunKey(_head(repo), cp.sha256("\n".join(cp.read_selection(collect)))).folder
    return result, tmp_path / "o" / folder


def test_a_packet_records_results_under_its_sha_and_selection(repo: Path, tmp_path: Path) -> None:
    result, out = _packet_run(repo, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads((out / "a-0.result.json").read_text(encoding="utf-8"))
    assert record["exit"] == 0 and record["executed"] == 2 and record["sha"] == _head(repo)
    assert "a-0" in result.stdout and "exit 0" in result.stdout, "status reports exit codes per group"


def test_a_record_for_other_inputs_is_refused_not_reused(repo: Path, tmp_path: Path) -> None:
    """Obs 2026-10-07-resumable-control-records-keyed-without-the-sha."""
    _, out = _packet_run(repo, tmp_path)
    record_path = out / "a-0.result.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["sha"] = "f" * 40
    record_path.write_text(json.dumps(record), encoding="utf-8")
    again, _ = _packet_run(repo, tmp_path)
    assert again.returncode != 0 and "recorded for other inputs" in again.stderr


def test_an_interrupted_record_is_re_run_on_resume(repo: Path, tmp_path: Path) -> None:
    """Obs 2026-10-15-runner-recorded-interrupted-groups-as-results: exit 2 is pytest's interrupted code."""
    _, out = _packet_run(repo, tmp_path)
    record_path = out / "a-0.result.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["exit"] = 2
    record_path.write_text(json.dumps(record), encoding="utf-8")
    again, _ = _packet_run(repo, tmp_path)
    assert again.returncode == 0, again.stdout + again.stderr
    assert json.loads(record_path.read_text(encoding="utf-8"))["exit"] == 0
    assert list(out.glob("a-0.interrupted-*.result.json")), "the interrupted record is kept aside, not deleted"


def test_a_group_stopped_by_shutdown_leaves_no_result(repo: Path, tmp_path: Path) -> None:
    (repo / "tests" / "test_slow.py").write_text(
        "import time\n\n\ndef test_slow():\n    time.sleep(30)\n", encoding="utf-8", newline="\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "slow")
    out = tmp_path / "o"
    (out / "b").mkdir(parents=True)
    packet = cp.Packet(repo, out, cp.RunKey(_head(repo), "s" * 64), None, 3600)
    outcome: list = []
    worker = threading.Thread(target=lambda: outcome.append(packet.run("slow-0", ["tests/test_slow.py::test_slow"])))
    worker.start()
    time.sleep(3)
    packet.stopping.set()
    worker.join(timeout=60)
    assert outcome == [None]
    assert not (out / "slow-0.result.json").exists(), "an interrupted group must not leave a result to resume from"


# --- contract 4 ---------------------------------------------------------------------------------------------


def _controls(repo: Path, tmp_path: Path, controls: list[dict]) -> subprocess.CompletedProcess[str]:
    spec = tmp_path / "controls.json"
    spec.write_text(json.dumps({"controls": controls}), encoding="utf-8")
    return _run("controls", "--sha", _head(repo), "--worktree", str(repo), "--spec", str(spec),
                "--out", str(tmp_path / "c"))  # fmt: skip


GUARD_NODE = "tests/test_guard.py::test_guard_refuses_negative"


def test_a_control_holds_only_on_its_own_failure(repo: Path, tmp_path: Path) -> None:
    deleted_guard = {"id": "c1", "file": "pkg/guard.py", "find": "    if x < 0:\n        raise ValueError('negative refused')\n",
                     "replace": "", "tests": [GUARD_NODE], "expected": "DID NOT RAISE"}  # fmt: skip
    result = _controls(repo, tmp_path, [deleted_guard])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "c1" in result.stdout and "held" in result.stdout
    assert _git(repo, "status", "--porcelain") == "", "the mutation was restored"


def test_an_environment_failure_is_inconclusive_never_held(repo: Path, tmp_path: Path) -> None:
    """Obs 2026-10-08-mutation-control-held-on-an-environment-failure."""
    env_failure = {"id": "c2", "file": "pkg/guard.py", "find": "    return x\n",
                   "replace": "    raise RuntimeError('current binding Git inspection is unavailable')\n",
                   "tests": [GUARD_NODE], "expected": "."}  # fmt: skip
    result = _controls(repo, tmp_path, [env_failure])
    assert result.returncode == 1
    assert "inconclusive" in result.stdout


def test_a_red_run_without_the_expected_failure_does_not_hold(repo: Path, tmp_path: Path) -> None:
    wrong_reason = {"id": "c3", "file": "pkg/guard.py", "find": "'negative refused'", "replace": "'other'",
                    "tests": [GUARD_NODE], "expected": "DID NOT RAISE"}  # fmt: skip
    result = _controls(repo, tmp_path, [wrong_reason])
    assert result.returncode == 1 and "failed_otherwise" in result.stdout


def test_a_control_that_does_not_fire_needs_a_disposition(repo: Path, tmp_path: Path) -> None:
    """Obs 2026-10-07-mutation-control-exposed-a-clause-no-admissible-input-reaches."""
    no_effect = {"id": "c4", "file": "pkg/guard.py", "find": "    return x\n", "replace": "    return x  # same\n",
                 "tests": [GUARD_NODE], "expected": "."}  # fmt: skip
    refused = _controls(repo, tmp_path, [no_effect])
    assert refused.returncode == 1 and "not_fired" in refused.stdout
    disposed = {**no_effect, "id": "c5", "disposition": "redundant: the comment changes no behaviour"}
    accepted = _controls(repo, tmp_path, [disposed])
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
