#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group C)
# Purpose: The Gate 6 certification runner as committed infrastructure, with the five record contracts each
# session-local copy learned by failing: a diff-derived selection, records keyed by what makes them true, no
# result for an interrupted group, a control that holds only on its own failure, and cleanliness at launch.
"""Run a frozen pytest selection as a resumable certification packet, or run mutation controls.

Every Gate 6 sub-phase rebuilt or hunted down this runner from a dead session's scratchpad (obs
2026-10-06-certification-runner-lives-in-a-dead-session-scratchpad), and each copy learned a lesson the next
did not inherit:

1. **Selection is derived from the diff** (obs 2026-10-07-certification-selection-narrower-than-ci-missed-pr-
   regressions). With ``--base``, the collect file must hold every node of every test file the diff touches
   and every node of every test file ``tools/affected_research_tests.py`` selects (the import closure and its
   conftest/pin rules). A partial selection needs ``--partial-reason``, recorded in the run.
2. **Records are keyed by what makes them true** (obs 2026-10-07-resumable-control-records-keyed-without-the-
   sha). Results live under ``<out>/<sha8>-<selection8>/``; each record stores the SHA, the selection hash and
   its own nodes' hash, and resume refuses a record whose stored inputs differ from the invocation.
3. **An interrupted group leaves no result** (obs 2026-10-15-runner-recorded-interrupted-groups-as-results).
   Ctrl-C stops the children and writes nothing for the groups in flight; on resume, a record with pytest exit
   2 or a log ending in ``KeyboardInterrupt`` is moved aside and re-run.
4. **A control holds only on its own failure** (obs 2026-10-08-mutation-control-held-on-an-environment-failure,
   2026-10-07-mutation-control-exposed-a-clause-no-admissible-input-reaches). ``controls`` applies each
   mutation, runs its tests, and records ``held`` only when they fail with the control's expected text. An
   environment failure is ``inconclusive``; a control that does not fire is ``not_fired`` and fails the run
   unless the spec gives a disposition (``redundant: <domain argument>`` or ``missing-test: <the test added>``).
5. **Cleanliness is checked at launch and at window start** (obs 2026-10-15-handoff-one-worktree-conflicts-
   with-clean-sha-runner): a dirty tree fails while someone is watching, not unattended at 02:00.

An environment failure (``Git inspection is unavailable``, ``TimeoutExpired``) is retried once with both
attempts kept. A run that executed no test has no exit code worth reading. ``status`` reports exit codes per
group, never a count of files.

Usage:
    certify_packet.py run --sha SHA --worktree W --collect FILE --out DIR [--base REF] [--now] [--dry-run]
    certify_packet.py status --out DIR --sha SHA --collect FILE
    certify_packet.py controls --sha SHA --worktree W --spec CONTROLS.json --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ENVIRONMENT_SIGNATURES = ("Git inspection is unavailable", "TimeoutExpired")
INTERRUPTED_SIGNATURES = ("KeyboardInterrupt", "!!!!!!! Interrupted")
PYTEST_INTERRUPTED = 2
TEST_FILE = re.compile(r"(^|/)test_[^/]*\.py$")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(worktree: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=worktree, check=True, capture_output=True, text=True).stdout


def worktree_python(worktree: Path) -> Path:
    for candidate in (worktree / ".venv" / "Scripts" / "python.exe", worktree / ".venv" / "bin" / "python"):
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def read_selection(collect: Path) -> list[str]:
    nodes = [line.strip() for line in collect.read_text(encoding="utf-8").splitlines() if "::" in line]
    duplicates = sorted({node for node in nodes if nodes.count(node) > 1})
    if duplicates:
        raise SystemExit(f"duplicate nodes in {collect}: {duplicates[:5]}")
    if not nodes:
        raise SystemExit(f"{collect} holds no pytest node ids")
    return nodes


# --- contract 5: the subject is the clean SHA, at launch and at window start ---------------------------------


def assert_clean_subject(worktree: Path, sha: str, when: str) -> None:
    head = git(worktree, "rev-parse", "HEAD").strip()
    dirty = git(worktree, "status", "--porcelain").strip()
    problems = []
    if head != sha:
        problems.append(f"HEAD is {head[:12]}, not {sha[:12]}")
    if dirty:
        problems.append(f"the tree is dirty:\n{dirty}")
    if problems:
        raise SystemExit(f"not the clean SHA ({when}): " + "; ".join(problems))


# --- contract 1: the selection covers what the diff can affect -----------------------------------------------


def no_bytecode() -> dict[str, str]:
    """The environment for every Python the runner starts in the subject: it must not write into the tree it
    certifies. Collection once wrote ``__pycache__/`` there, and the next launch refused its own droppings
    wherever git did not ignore them (a hosted runner, which leaves ``PYTHONDONTWRITEBYTECODE`` unset)."""
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def collect_nodes(worktree: Path, files: list[str]) -> list[str]:
    if not files:
        return []
    done = subprocess.run(
        [str(worktree_python(worktree)), "-B", "-m", "pytest", "--collect-only", "-q", "-o", "addopts=",
         "-p", "no:cacheprovider", "-p", "no:cov", *files],
        cwd=worktree, capture_output=True, text=True, check=False, env=no_bytecode(),
    )  # fmt: skip
    return [line.strip() for line in done.stdout.splitlines() if "::" in line and not line.startswith(" ")]


def required_selection(worktree: Path, base: str) -> tuple[list[str], list[str]]:
    """(test files the diff touches, test files the affected selector chooses), both repository-relative."""
    changed = [p for p in git(worktree, "diff", "--name-only", f"{base}...HEAD").splitlines() if p.strip()]
    touched = sorted(p for p in changed if TEST_FILE.search(p) and (worktree / p).exists())
    selector = worktree / "tools" / "affected_research_tests.py"
    affected: list[str] = []
    if selector.exists():
        done = subprocess.run(
            [str(worktree_python(worktree)), "-B", str(selector), "--base", base],
            cwd=worktree, capture_output=True, text=True, check=True, env=no_bytecode(),
        )  # fmt: skip
        affected = sorted(line.strip() for line in done.stdout.splitlines() if line.strip())
    return touched, affected


def selection_gaps(selection: list[str], required: list[str]) -> list[str]:
    chosen = set(selection)
    return sorted(node for node in required if node not in chosen)


# --- contracts 2 and 3: records keyed by their inputs; interrupted groups leave none -------------------------


@dataclass(frozen=True)
class RunKey:
    sha: str
    selection_hash: str

    @property
    def folder(self) -> str:
        return f"{self.sha[:8]}-{self.selection_hash[:8]}"


def junit_executed(junit: Path) -> int:
    if not junit.exists():
        return 0
    try:
        root = ET.parse(junit).getroot()
    except ET.ParseError:
        return 0
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return sum(int(s.get("tests", 0)) - int(s.get("skipped", 0)) for s in suites)


def was_interrupted(record: dict, log: Path) -> bool:
    if record.get("exit") == PYTEST_INTERRUPTED:
        return True
    tail = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.exists() else ""
    return any(signature in tail for signature in INTERRUPTED_SIGNATURES)


class Packet:
    """Run groups into ``out``; ``stop_event`` set by the caller (Ctrl-C) stops children and records nothing."""

    def __init__(self, worktree: Path, out: Path, key: RunKey, stop_at: datetime | None, group_budget: int) -> None:
        self.worktree, self.out, self.key, self.stop_at, self.group_budget = worktree, out, key, stop_at, group_budget
        self.stopping = threading.Event()

    def run(self, label: str, nodes: list[str]) -> dict | None:
        recorded, log = self.out / f"{label}.result.json", self.out / f"{label}.log"
        nodes_hash = sha256("\n".join(nodes))
        if recorded.exists():
            record = json.loads(recorded.read_text(encoding="utf-8"))
            stored = (record.get("sha"), record.get("selection_hash"), record.get("nodes_hash"))
            if stored != (self.key.sha, self.key.selection_hash, nodes_hash):
                raise SystemExit(f"{recorded} was recorded for other inputs {stored}; refusing to reuse it")
            if not was_interrupted(record, log):
                return {**record, "resumed": True}
            stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            for suffix in (".result.json", ".log", ".xml"):
                source = self.out / f"{label}{suffix}"
                if source.exists():
                    source.replace(self.out / f"{label}.interrupted-{stamp}{suffix}")
        attempts = []
        for attempt in (1, 2):
            result = self._attempt(label, nodes)
            if result is None:  # stopped by the runner's own shutdown: no record
                return None
            attempts.append(result)
            if not result["environment"] or attempt == 2:
                break
            for suffix in (".log", ".xml"):
                source = self.out / f"{label}{suffix}"
                if source.exists():
                    shutil.copyfile(source, self.out / f"{label}.environment-1{suffix}")
        final = {**attempts[-1], "sha": self.key.sha, "selection_hash": self.key.selection_hash,
                 "nodes_hash": nodes_hash, "nodes": len(nodes), "attempts": len(attempts)}  # fmt: skip
        recorded.write_text(json.dumps(final, indent=1), encoding="utf-8")
        return final

    def _attempt(self, label: str, nodes: list[str]) -> dict | None:
        log, junit = self.out / f"{label}.log", self.out / f"{label}.xml"
        args = [str(worktree_python(self.worktree)), "-B", "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider",
                "-p", "no:cov", "-v", "--tb=short", f"--basetemp={self.out / 'b' / label}", f"--junitxml={junit}",
                *nodes]  # fmt: skip
        started = time.time()
        cut_off = False
        with log.open("w", encoding="utf-8") as handle:
            process = subprocess.Popen(args, cwd=self.worktree, stdout=handle, stderr=subprocess.STDOUT,
                                       env=no_bytecode())  # fmt: skip
            (self.out / f"{label}.started.json").write_text(json.dumps({"pid": process.pid, "started": started}))
            while process.poll() is None:
                if self.stopping.is_set():
                    _kill(process)
                    process.wait()
                    return None
                if self.stop_at and datetime.now() >= self.stop_at:
                    _kill(process)
                    cut_off = True
                    break
                time.sleep(1)
            code = process.wait()
        if self.stopping.is_set():
            return None
        text = log.read_text(encoding="utf-8", errors="replace")
        seconds = round(time.time() - started)
        return {
            "label": label,
            "exit": code,
            "seconds": seconds,
            "over_budget": seconds > self.group_budget,
            "cut_off": cut_off,
            "executed": junit_executed(junit),
            "environment": code != 0 and any(s in text for s in ENVIRONMENT_SIGNATURES),
            "summary": text.strip().splitlines()[-1:],
        }


def _kill(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        process.kill()


def group_by_file(nodes: list[str], per_group: int) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    by_file: dict[str, list[str]] = {}
    for node in nodes:
        by_file.setdefault(node.partition("::")[0], []).append(node)
    for path, file_nodes in by_file.items():
        stem = Path(path).stem.removeprefix("test_")
        for index in range(0, len(file_nodes), per_group):
            groups[f"{stem}-{index // per_group}"] = file_nodes[index : index + per_group]
    return groups


def wait_for_window(start: tuple[int, int], latest: tuple[int, int], out: Path) -> datetime:
    now = datetime.now()
    begin = now.replace(hour=start[0], minute=start[1], second=0, microsecond=0)
    if (now.hour, now.minute) >= latest:
        begin += timedelta(days=1)
    while datetime.now() < begin:
        (out / "waiting.json").write_text(json.dumps({"now": datetime.now().isoformat(timespec="seconds"),
                                                      "starts": begin.isoformat()}))  # fmt: skip
        time.sleep(min(300, max(1, (begin - datetime.now()).total_seconds())))
    return begin


def _clock(text: str) -> tuple[int, int]:
    hours, _, minutes = text.partition(":")
    return int(hours), int(minutes or 0)


def command_run(args: argparse.Namespace) -> int:
    worktree = args.worktree.resolve()
    selection = read_selection(args.collect)
    key = RunKey(args.sha, sha256("\n".join(selection)))
    assert_clean_subject(worktree, args.sha, "at launch")  # contract 5, while someone is watching
    coverage: dict = {}
    if args.base:
        touched, affected = required_selection(worktree, args.base)
        required = collect_nodes(worktree, sorted(set(touched) | set(affected)))
        gaps = selection_gaps(selection, required)
        coverage = {"base": args.base, "touched": touched, "affected": affected, "required_nodes": len(required),
                    "missing_nodes": len(gaps), "partial_reason": args.partial_reason}  # fmt: skip
        if gaps and not args.partial_reason:
            shown = "\n  ".join(gaps[:20])
            raise SystemExit(f"the selection omits {len(gaps)} node(s) the diff can affect:\n  {shown}\n"
                             "add them, or give --partial-reason (recorded in the run)")  # fmt: skip
    groups = group_by_file(selection, args.per_group)
    if args.dry_run:
        print(json.dumps({"key": key.folder, "groups": len(groups), "tests": len(selection), "coverage": coverage},
                         indent=1))  # fmt: skip
        return 0
    out = args.out / key.folder
    (out / "b").mkdir(parents=True, exist_ok=True)
    began = datetime.now() if args.now else wait_for_window(_clock(args.window_start), _clock(args.latest_start), out)
    assert_clean_subject(worktree, args.sha, "at window start")
    stop_at = began.replace(hour=_clock(args.stop)[0], minute=_clock(args.stop)[1], second=0, microsecond=0)
    if stop_at <= began:
        stop_at += timedelta(days=1)
    (out / "started.json").write_text(json.dumps({"began": began.isoformat(timespec="seconds"), "sha": args.sha,
                                                   "selection_hash": key.selection_hash, "coverage": coverage}))  # fmt: skip
    packet = Packet(worktree, out, key, None if args.now else stop_at, args.group_budget_minutes * 60)
    pool = ThreadPoolExecutor(max_workers=args.workers)
    futures = {label: pool.submit(packet.run, label, nodes) for label, nodes in groups.items()}
    try:
        while not all(f.done() for f in futures.values()):
            time.sleep(1)
    except KeyboardInterrupt:
        packet.stopping.set()  # contract 3: children stopped, nothing recorded for groups in flight
        pool.shutdown(wait=True, cancel_futures=True)
        print("interrupted: groups in flight were stopped and left without a result; resume re-runs them")
        return 130
    pool.shutdown(wait=True)
    results = [f.result() for f in futures.values() if f.result() is not None]
    wall = round((datetime.now() - began).total_seconds())
    summary = {
        "sha": args.sha, "selection_hash": key.selection_hash, "began": began.isoformat(timespec="seconds"),
        "wall_seconds": wall, "packet_over_budget": wall > args.packet_budget_minutes * 60,
        "tree_clean_after": not git(worktree, "status", "--porcelain").strip(),
        "failed_groups": sorted(r["label"] for r in results if r["exit"] != 0),
        "not_executed": sorted(r["label"] for r in results if r["executed"] < 1),
        "cut_off": sorted(r["label"] for r in results if r["cut_off"]),
        "groups_over_budget": sorted(r["label"] for r in results if r["over_budget"]),
        "coverage": coverage, "results": results,
    }  # fmt: skip
    (out / "results.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return command_status(argparse.Namespace(out=args.out, sha=args.sha, collect=args.collect))


def command_status(args: argparse.Namespace) -> int:
    """Exit code per group, read from the records; a count of files is not a status (obs 2026-10-15-...)."""
    selection = read_selection(args.collect)
    out = args.out / RunKey(args.sha, sha256("\n".join(selection))).folder
    if not out.exists():
        print(f"no run recorded for this SHA and selection under {out}")
        return 1
    labels = sorted(
        p.name.removesuffix(".result.json") for p in out.glob("*.result.json") if ".interrupted-" not in p.name
    )
    bad = 0
    for label in labels:
        record = json.loads((out / f"{label}.result.json").read_text(encoding="utf-8"))
        state = "INTERRUPTED" if was_interrupted(record, out / f"{label}.log") else f"exit {record['exit']}"
        if record.get("executed", 0) < 1:
            state += " (no test executed)"
        bad += state != "exit 0"
        print(f"{label:48s} {state}")
    print(f"{len(labels)} group record(s) under {out}; {bad} not clean")
    return 1 if bad or not labels else 0


# --- contract 4: a control holds only on its own failure -----------------------------------------------------


def run_control(worktree: Path, control: dict, out: Path) -> dict:
    path = worktree / control["file"]
    original = path.read_bytes()
    text = original.decode("utf-8")
    if text.count(control["find"]) != 1:
        raise SystemExit(f"control {control['id']}: 'find' must occur exactly once in {control['file']}")
    log = out / f"{control['id']}.log"
    try:
        path.write_bytes(text.replace(control["find"], control["replace"]).encode("utf-8"))
        done = subprocess.run(
            [str(worktree_python(worktree)), "-B", "-m", "pytest", "-o", "addopts=", "-p", "no:cacheprovider",
             "-p", "no:cov", "--tb=short", *control["tests"]],
            cwd=worktree, capture_output=True, text=True, check=False, env=no_bytecode(),
        )  # fmt: skip
    finally:
        path.write_bytes(original)
    output = done.stdout + done.stderr
    log.write_text(output, encoding="utf-8")
    if any(s in output for s in ENVIRONMENT_SIGNATURES):
        verdict = "inconclusive"
    elif done.returncode == 0:
        verdict = "not_fired"
    elif done.returncode == 1 and re.search(control["expected"], output):
        verdict = "held"
    else:
        verdict = "failed_otherwise"  # red, but not with the guard's own failure
    return {"id": control["id"], "verdict": verdict, "exit": done.returncode,
            "mutation_hash": sha256(json.dumps(control, sort_keys=True)),
            "disposition": control.get("disposition")}  # fmt: skip


def command_controls(args: argparse.Namespace) -> int:
    worktree = args.worktree.resolve()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    assert_clean_subject(worktree, args.sha, "before controls")
    out = args.out / f"{args.sha[:8]}-controls"
    out.mkdir(parents=True, exist_ok=True)
    failures = []
    for control in spec["controls"]:
        record_path = out / f"{control['id']}.json"
        mutation_hash = sha256(json.dumps(control, sort_keys=True))
        if record_path.exists():
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if (record.get("sha"), record.get("mutation_hash")) != (args.sha, mutation_hash):
                raise SystemExit(f"{record_path} was recorded for other inputs; refusing to reuse it")
        else:
            record = {**run_control(worktree, control, out), "sha": args.sha}
            record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
        disposition = control.get("disposition") or ""
        accepted = record["verdict"] == "held" or (
            record["verdict"] == "not_fired" and re.match(r"(redundant|missing-test): \S", disposition)
        )
        print(f"{control['id']:24s} {record['verdict']}" + (f"  [{disposition}]" if disposition else ""))
        if not accepted:
            failures.append(control["id"])
    assert_clean_subject(worktree, args.sha, "after controls")
    if failures:
        print(f"controls not accepted: {failures} (inconclusive re-runs; not_fired needs a disposition)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--sha", required=True)
    run.add_argument("--worktree", type=Path, required=True)
    run.add_argument("--collect", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--base", help="Require the selection to cover what the diff from this ref can affect.")
    run.add_argument("--partial-reason", help="Admit a selection that omits affected nodes; recorded in the run.")
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--per-group", type=int, default=5)
    run.add_argument("--window-start", default="02:00")
    run.add_argument("--latest-start", default="08:00")
    run.add_argument("--stop", default="11:00")
    run.add_argument("--group-budget-minutes", type=int, default=60)
    run.add_argument("--packet-budget-minutes", type=int, default=300)
    run.add_argument("--now", action="store_true", help="Start now and run past the window's stop time.")
    run.add_argument("--dry-run", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("--out", type=Path, required=True)
    status.add_argument("--sha", required=True)
    status.add_argument("--collect", type=Path, required=True)
    controls = sub.add_parser("controls")
    controls.add_argument("--sha", required=True)
    controls.add_argument("--worktree", type=Path, required=True)
    controls.add_argument("--spec", type=Path, required=True)
    controls.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return {"run": command_run, "status": command_status, "controls": command_controls}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
