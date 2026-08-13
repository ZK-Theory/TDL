"""Configuration controls for the ARS currency workflows."""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENCY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ars-artefact-currency.yml"
WATCHDOG_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ars-artefact-currency-watchdog.yml"


def _workflow(path: Path) -> dict[str, object]:
    """Load a GitHub Actions workflow without YAML 1.1 coercing ``on``."""
    document = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(document, dict)
    return document


def test_currency_controls_run_on_main_pull_requests() -> None:
    """Both current-candidate controls must be present on the PR they protect."""
    for path in (CURRENCY_WORKFLOW, WATCHDOG_WORKFLOW):
        document = _workflow(path)

        triggers = document["on"]
        assert isinstance(triggers, dict)
        assert triggers["pull_request"] == {"branches": ["main"]}


def _recorded_subject_script(document: dict[str, object], *, job_name: str) -> str:
    jobs = document["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[job_name]
    assert isinstance(job, dict)
    steps = job["steps"]
    assert isinstance(steps, list)
    for step in steps:
        if isinstance(step, dict) and step.get("name") == "Record resolved workflow subject":
            script = step.get("run")
            assert isinstance(script, str)
            return script
    raise AssertionError(f"{job_name} does not record its resolved workflow subject")


def test_currency_controls_record_their_exact_checked_out_subject() -> None:
    """Each PR control must leave its event, ref, and resolved SHA visible."""
    controls = (
        (CURRENCY_WORKFLOW, "contract-and-session-currency"),
        (WATCHDOG_WORKFLOW, "require-active-currency-workflow"),
    )

    for path, job_name in controls:
        script = _recorded_subject_script(_workflow(path), job_name=job_name)

        assert "git rev-parse HEAD" in script
        assert "GITHUB_EVENT_NAME" in script
        assert "GITHUB_REF" in script
        assert "GITHUB_STEP_SUMMARY" in script
