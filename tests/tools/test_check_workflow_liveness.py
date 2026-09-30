"""Direct controls for the independent C-1 workflow-state watchdog."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check_workflow_liveness.py"
TARGET = ".github/workflows/ars-artefact-currency.yml"


def _run(payload: dict[str, object], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    response = tmp_path / "workflows.json"
    response.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--workflows-json", str(response), "--target-path", TARGET],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_active_target_workflow_passes(tmp_path: Path) -> None:
    result = _run({"workflows": [{"path": TARGET, "state": "active"}]}, tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"active: {TARGET}" in result.stdout


def test_manually_disabled_target_workflow_fails_closed(tmp_path: Path) -> None:
    result = _run({"workflows": [{"path": TARGET, "state": "disabled_manually"}]}, tmp_path)

    assert result.returncode == 1
    assert "disabled_manually" in result.stderr


# All-tracked mode (obs 2026-09-08-workflow-disabled-state-is-invisible-to-the-repo): the
# watchdog named two workflows, so any other tracked workflow, including one added later,
# could sit disabled with nothing noticing. The governed set is derived from the tree.
TRACKED = [".github/workflows/a.yml", ".github/workflows/b.yml"]


def _run_all(pages: object, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    response = tmp_path / "workflows.json"
    response.write_text(json.dumps(pages), encoding="utf-8")
    args = [sys.executable, str(SCRIPT), "--workflows-json", str(response), "--all-tracked"]
    for path in TRACKED:
        args += ["--tracked-path", path]
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def _page(*rows: tuple[str, str]) -> dict[str, object]:
    return {"workflows": [{"path": path, "state": state} for path, state in rows]}


def test_all_tracked_passes_when_every_tracked_workflow_is_active(tmp_path: Path) -> None:
    """Paginated `--slurp` output (a list of pages) is merged; untracked dynamic rows are ignored."""
    pages = [
        _page((TRACKED[0], "active"), ("dynamic/dependabot/dependabot-updates", "disabled_manually")),
        _page((TRACKED[1], "active")),
    ]

    result = _run_all(pages, tmp_path)

    assert result.returncode == 0, result.stderr
    assert "2 tracked workflow(s) active" in result.stdout


def test_all_tracked_names_every_inactive_tracked_workflow(tmp_path: Path) -> None:
    result = _run_all(_page((TRACKED[0], "disabled_manually"), (TRACKED[1], "disabled_inactivity")), tmp_path)

    assert result.returncode == 1
    assert f"{TRACKED[0]} is 'disabled_manually'" in result.stderr
    assert f"{TRACKED[1]} is 'disabled_inactivity'" in result.stderr


def test_all_tracked_fails_when_a_tracked_workflow_is_missing_from_github(tmp_path: Path) -> None:
    """A workflow file GitHub never registered has not run either; absence is not activity."""
    result = _run_all(_page((TRACKED[0], "active")), tmp_path)

    assert result.returncode == 1
    assert f"{TRACKED[1]}: not registered with GitHub Actions" in result.stderr


def test_all_tracked_defaults_to_the_workflow_files_git_tracks() -> None:
    """Without --tracked-path the set comes from git, so a new workflow file is covered on arrival."""
    spec = __import__("importlib.util").util.spec_from_file_location("cwl", SCRIPT)
    module = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tracked = module.tracked_workflow_paths(REPO_ROOT)

    assert ".github/workflows/ci.yml" in tracked
    assert ".github/workflows/merge-admission.yml" in tracked
    assert all(path.startswith(".github/workflows/") for path in tracked)


def test_the_watchdog_checks_every_tracked_workflow() -> None:
    watchdog = (REPO_ROOT / ".github" / "workflows" / "ars-artefact-currency-watchdog.yml").read_text(encoding="utf-8")
    assert "--all-tracked" in watchdog
    assert "--paginate" in watchdog and "--slurp" in watchdog
    assert "--tracked-ref FETCH_HEAD" in watchdog and "github.base_ref" in watchdog


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def test_a_pull_request_run_checks_the_base_branch_workflow_set(tmp_path: Path) -> None:
    """A workflow the PR adds cannot be registered until merge, so a PR run must not demand it."""
    repo = tmp_path / "repo"
    (repo / ".github" / "workflows").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / TRACKED[0]).write_text("on: push\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / TRACKED[1]).write_text("on: push\n", encoding="utf-8")
    _git(repo, "add", "-A")
    response = tmp_path / "workflows.json"
    response.write_text(json.dumps(_page((TRACKED[0], "active"))), encoding="utf-8")
    command = [
        sys.executable,
        str(SCRIPT),
        "--workflows-json",
        str(response),
        "--all-tracked",
        "--repo-root",
        str(repo),
    ]

    head_run = subprocess.run(command, capture_output=True, text=True, check=False)
    base_run = subprocess.run([*command, "--tracked-ref", base], capture_output=True, text=True, check=False)

    assert head_run.returncode == 1 and f"{TRACKED[1]}: not registered" in head_run.stderr
    assert base_run.returncode == 0, base_run.stderr
