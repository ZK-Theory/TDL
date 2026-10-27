"""The project supports Windows only, so no CI job may run on Linux.

Decided by Stephen on 2026-09-11 (PR #278). These controls keep that decision
from eroding one workflow at a time, and guard the two ways a move to Windows
runners fails silently: a bash script left under the Windows default shell, and
a platform gate still pointed at a job that no longer exists or runs elsewhere.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
ADMISSION_CONFIG = REPO_ROOT / ".github" / "merge-admission.yml"

# Syntax that only a POSIX shell accepts. Windows runners default to pwsh.
BASH_MARKERS = ("set -euo pipefail", "$(", "source ", "printf ", "git init", "[ -")


def _load(path: Path) -> dict[str, Any]:
    """Load a workflow without YAML 1.1 coercing ``on`` or version strings."""
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(document, dict), f"{path.name} is not a mapping"
    return document


def _shell(block: object) -> str | None:
    """Return ``defaults.run.shell`` from a workflow or job mapping, if declared."""
    if not isinstance(block, dict):
        return None
    run = block.get("defaults", {}).get("run", {})
    return run.get("shell") if isinstance(run, dict) else None


def test_workflow_discovery_is_not_vacuous() -> None:
    """A glob that matched nothing would make every control below pass."""
    names = {path.name for path in WORKFLOWS}
    assert {"ci.yml", "merge-admission.yml", "ars-artefact-currency.yml"} <= names


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_no_job_runs_on_linux(path: Path) -> None:
    """Every job's runner label is a Windows label."""
    for name, job in _load(path)["jobs"].items():
        runs_on = job.get("runs-on")
        labels = runs_on if isinstance(runs_on, list) else [runs_on]
        assert labels and all(isinstance(label, str) and label.startswith("windows") for label in labels), (
            f"{path.name}:{name} runs on {runs_on!r}; the project supports Windows only"
        )


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_bash_scripts_declare_bash(path: Path) -> None:
    """A POSIX script under pwsh fails at runtime, not at review."""
    document = _load(path)
    workflow_shell = _shell(document)
    for name, job in document["jobs"].items():
        job_shell = _shell(job) or workflow_shell
        for step in job.get("steps", []):
            script = step.get("run")
            if not isinstance(script, str) or not any(marker in script for marker in BASH_MARKERS):
                continue
            shell = step.get("shell", job_shell)
            assert shell == "bash", (
                f"{path.name}:{name} step {step.get('name')!r} uses bash syntax but runs under "
                f"{shell or 'the Windows default shell (pwsh)'}"
            )


# research_system contract tests read pinned historical commits. On a depth-1 checkout they
# fail for the environment, not the code: six of eight suite shards on PR #342 (obs
# 2026-10-07-suite-lane-shallow-checkout-fails-history-tests).
SHALLOW_FETCH_FLAGS = ("--depth", "--shallow", "--deepen")
RESEARCH_SYSTEM_TEST_JOBS = {
    ("ci.yml", "windows-store-lock"),
    ("ars-artefact-currency.yml", "contract-and-session-currency"),
    ("research-system-suite.yml", "suite"),
}


def _runs_research_system_tests(job: dict[str, Any]) -> bool:
    """A job runs research_system tests if it invokes pytest on them or on a suite shard."""
    script = "\n".join(step.get("run", "") for step in job.get("steps", []))
    return "pytest" in script and ("tests/research_system" in script or "tools/research_system_shards.py" in script)


def _checks_out_full_history(job: dict[str, Any]) -> bool:
    """Judge the job's first checkout: ``actions/checkout`` or a hand-rolled ``git fetch``."""
    for step in job.get("steps", []):
        if step.get("uses", "").startswith("actions/checkout@"):
            return step.get("with", {}).get("fetch-depth") == "0"
        script = step.get("run", "")
        if "git fetch" in script or "git clone" in script:
            return not any(flag in script for flag in SHALLOW_FETCH_FLAGS)
    return False


def _shallow_research_system_jobs(document: dict[str, Any]) -> list[str]:
    return [
        name
        for name, job in document["jobs"].items()
        if _runs_research_system_tests(job) and not _checks_out_full_history(job)
    ]


def test_research_system_job_discovery_is_not_vacuous() -> None:
    """A detector that matched no job would make the full-history control pass on anything."""
    found = {
        (path.name, name)
        for path in WORKFLOWS
        for name, job in _load(path)["jobs"].items()
        if _runs_research_system_tests(job)
    }
    assert RESEARCH_SYSTEM_TEST_JOBS <= found


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_research_system_test_jobs_check_out_full_history(path: Path) -> None:
    """Every job that runs research_system tests has the history those tests read."""
    assert _shallow_research_system_jobs(_load(path)) == [], (
        f"{path.name}: these jobs run research_system tests on a shallow checkout"
    )


@pytest.mark.parametrize(
    ("workflow", "full", "shallow", "job"),
    [
        ("research-system-suite.yml", "          fetch-depth: 0\n", "", "suite"),
        ("ci.yml", "          fetch-depth: 0\n", "", "windows-store-lock"),
        (
            "ars-artefact-currency.yml",
            'git fetch --no-tags origin "${GITHUB_REF}"',
            'git fetch --no-tags --depth=1 origin "${GITHUB_REF}"',
            "contract-and-session-currency",
        ),
    ],
)
def test_the_full_history_control_fails_on_a_shallow_copy(
    tmp_path: Path, workflow: str, full: str, shallow: str, job: str
) -> None:
    """Negative control: the same workflow with its depth made shallow is refused."""
    text = (WORKFLOW_DIR / workflow).read_text(encoding="utf-8")
    assert full in text, f"{workflow} no longer contains {full!r}; the control would edit nothing"
    copy = tmp_path / workflow
    copy.write_text(text.replace(full, shallow), encoding="utf-8")
    assert job in _shallow_research_system_jobs(_load(copy))


def test_removed_linux_lanes_stay_removed() -> None:
    """The two Linux-only lanes removed on 2026-09-11 are not quietly restored."""
    jobs = _load(WORKFLOW_DIR / "ci.yml")["jobs"]
    assert "test" not in jobs
    assert "petls-backend" not in jobs


def test_platform_gate_reads_a_windows_job_from_its_trusted_workflow() -> None:
    """The admission gate's platform job exists, runs on Windows, and lives where the gate trusts it."""
    section = yaml.safe_load(ADMISSION_CONFIG.read_text(encoding="utf-8"))["platform_order"]
    workflow_path = REPO_ROOT / section["workflow_path"]
    assert workflow_path.is_file(), f"platform_order.workflow_path {section['workflow_path']} does not exist"
    jobs = _load(workflow_path)["jobs"]
    assert section["check_run"] in jobs, f"{section['check_run']} is not a job in {section['workflow_path']}"
    assert jobs[section["check_run"]]["runs-on"].startswith("windows")
    assert "continue-on-error" not in jobs[section["check_run"]], "advisory evidence cannot gate admission"


ADMISSION_CONTROL_MODULES = (
    "tests/tools/test_merge_admission.py",
    "tests/tools/test_ci_platform_policy.py",
    "tests/tools/test_admin_bypass_guard_hook.py",
    # The workflow-step harness the hook and lane controls share (2026-10-15 system review, Group E).
    "tests/tools/test_workflow_steps.py",
    # Hook and gate controls (2026-09-23 system review, Campaign D). The two git-hook suites
    # went stale outside every automatic path (obs 2026-09-17-hook-test-outside-ci-rotted-
    # after-a-gate-was-added); the two harness-hook suites replace a manual selftest and no test.
    "tests/tools/test_pre_commit_hook.py",
    "tests/tools/test_post_commit_repowise_hook.py",
    "tests/tools/test_notation_guard_hook.py",
    "tests/tools/test_dispatch_readiness_guard_hook.py",
    "tests/tools/test_no_dot_git_hooks_writers.py",
    "tests/tools/test_mutation_check.py",
    "tests/tools/test_certify_packet.py",
    "tests/tools/test_assert_no_skips.py",
    "tests/tools/test_ci_parity.py",
    "tests/tools/test_commit_state_guard_hook.py",
    "tests/tools/test_crlf_byte_surface.py",
    "tests/tools/test_system_review_hook_gates.py",
    "tests/tools/test_sync_agent_skills.py",
    "tests/tools/test_results_no_overwrite_hook.py",
    "tests/tools/test_hook_currency.py",
    "tests/tools/test_review_staleness.py",
    # System review tools (2026-10-06, PR #332): the review ledger and stranded-commit lint, and
    # the retired-plan gate that pre-commit Gate 2 runs.
    "tests/tools/test_observation_log_lint.py",
    "tests/tools/test_retired_imperatives.py",
    "tests/tools/test_check_pinned_commits.py",
    # Hook controls no lane ran until the 2026-10-27 system review (Group H1); the glob test below
    # now finds any such file instead of relying on this list.
    "tests/tools/test_pre_push_hook.py",
    "tests/tools/test_commit_msg_hooks.py",
    "tests/tools/test_handoff_surface_hook.py",
    "tests/tools/test_hook_script_lf_bytes.py",
)

# A hook-control module that deliberately does not run in admission-controls, with the reason. Empty: every one runs.
HOOK_CONTROL_EXEMPTIONS: dict[str, str] = {}


def test_admission_controls_run_in_a_blocking_windows_job() -> None:
    """Codex review 3990242343: these controls must execute in CI, or a PR can weaken them unseen."""
    job = _load(WORKFLOW_DIR / "ci.yml")["jobs"].get("admission-controls")
    assert job is not None, "ci.yml has no admission-controls job"
    assert job["runs-on"].startswith("windows")
    assert "continue-on-error" not in job and "if" not in job
    scripts = " ".join(step.get("run", "") for step in job["steps"])
    for module in ADMISSION_CONTROL_MODULES:
        assert module in scripts, f"admission-controls does not run {module}"


def test_every_hook_control_module_runs_in_admission_controls() -> None:
    """Obs 2026-10-27-hook-control-tests-run-by-no-lane: four hook controls sat outside every lane.

    The list above is hand-written, so a hook test nobody added to it was never missed. This derives the set from
    the files: every ``tests/tools/test_*hook*.py`` runs in admission-controls or is exempted with a reason.
    """
    job = _load(WORKFLOW_DIR / "ci.yml")["jobs"]["admission-controls"]
    scripts = " ".join(step.get("run", "") for step in job["steps"])
    modules = sorted(
        path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / "tests/tools").glob("test_*hook*.py")
    )
    assert modules, "no hook-control modules found; the glob or the tree moved"
    missing = [m for m in modules if m not in scripts and m not in HOOK_CONTROL_EXEMPTIONS]
    assert not missing, f"admission-controls does not run these hook controls: {missing}"
    stale = [m for m in HOOK_CONTROL_EXEMPTIONS if m not in modules]
    assert not stale, f"exemptions name files that no longer exist: {stale}"


def test_admission_controls_check_out_full_history_for_the_pin_check() -> None:
    """The pinned-commit control reads every pinned commit and the remote's tags; a shallow clone hides both.

    Obs 2026-10-15-accepted-contracts-pin-commits-on-local-only-branches.
    """
    job = _load(WORKFLOW_DIR / "ci.yml")["jobs"]["admission-controls"]
    assert _checks_out_full_history(job)
    shallow = copy.deepcopy(job)
    checkout = next(step for step in shallow["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    del checkout["with"]["fetch-depth"]
    assert not _checks_out_full_history(shallow), "negative control: the same job without fetch-depth must fail"


def test_admission_controls_refuse_skipped_or_absent_controls() -> None:
    """The hook suites skip without Git Bash, and a lane of skips exits green; the job must check."""
    job = _load(WORKFLOW_DIR / "ci.yml")["jobs"]["admission-controls"]
    scripts = " ".join(step.get("run", "") for step in job["steps"])
    assert "--junitxml=admission-controls.xml" in scripts
    assert "tools/assert_no_skips.py admission-controls.xml" in scripts


# Every file the gate's behaviour depends on. If a new gate file appears, it must
# be added here AND to CODEOWNERS, or edits to it would bypass code-owner review.
GATE_FILES = (
    ".github/CODEOWNERS",
    ".github/merge-admission.yml",
    ".github/workflows/merge-admission.yml",
    ".github/workflows/merge-admission-sweep.yml",
    ".github/workflows/ci.yml",
    "tools/check_merge_admission.py",
    ".claude/hooks/admin-bypass-guard.sh",
    ".claude/settings.json",
)


def _codeowners_rules() -> dict[str, list[str]]:
    """Return CODEOWNERS path patterns mapped to their owners."""
    rules: dict[str, list[str]] = {}
    for line in (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            pattern, *owners = stripped.split()
            rules[pattern] = owners
    return rules


def test_every_gate_file_exists_and_has_a_code_owner() -> None:
    """Edits to the gate need code-owner review; a file missing from CODEOWNERS silently escapes it."""
    rules = _codeowners_rules()
    for path in GATE_FILES:
        assert (REPO_ROOT / path).is_file(), f"gate file {path} does not exist"
        assert rules.get(f"/{path}"), f"{path} has no code owner in .github/CODEOWNERS"


def test_codeowners_names_no_file_outside_the_gate() -> None:
    """Positive control on scope: code-owner review must not spread to ordinary PRs unannounced."""
    assert set(_codeowners_rules()) == {f"/{path}" for path in GATE_FILES}


GIT_GUIDANCE = REPO_ROOT / ".claude" / "instructions" / "git.instructions.md"
_PRODUCERS_BY_NAME = {"codex": "chatgpt-codex-connector", "coderabbit": "coderabbitai"}


def _guidance_contradictions(guidance: str, producers: list[str]) -> list[str]:
    """Return each reviewer the guidance says merge admission needs that ``review_producers`` does not list.

    Obs 2026-10-20-git-guidance-still-requires-codex-after-producer-removal: #376 emptied ``review_producers``
    and updated CONVENTIONS, but the git instructions agents load still said admission needs Codex.
    """
    named = re.findall(r"(?i)merge admission (?:needs|requires|waits (?:on|for)) (codex|coderabbit)\b", guidance)
    return sorted({name.lower() for name in named if _PRODUCERS_BY_NAME[name.lower()] not in producers})


def test_git_guidance_names_no_reviewer_admission_does_not_require() -> None:
    config = yaml.safe_load(ADMISSION_CONFIG.read_text(encoding="utf-8"))
    producers = config["thread_finality"]["review_producers"]
    assert _guidance_contradictions(GIT_GUIDANCE.read_text(encoding="utf-8"), producers) == []


def test_the_guidance_control_fails_on_the_pre_fix_wording() -> None:
    stale = "- Merge admission needs Codex to reach a terminal state on the exact head."
    assert _guidance_contradictions(stale, []) == ["codex"]
    assert _guidance_contradictions(stale, ["chatgpt-codex-connector"]) == []
