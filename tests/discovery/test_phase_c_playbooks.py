"""Discovery Harness Phase-C portability artifacts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS_DIR = REPO_ROOT / "playbooks" / "discovery-harness"


def test_agent_neutral_task_contract_documents_bus_schema() -> None:
    contract = (PLAYBOOKS_DIR / "agent-neutral-task-contract.md").read_text(encoding="utf-8")
    for required in [
        "schema_version: discovery-agent-task/v1",
        ".apm/bus/<agent-slug>/task.md",
        ".apm/bus/<agent-slug>/report.md",
        "task_id",
        "objective",
        "inputs",
        "outputs",
        "acceptance_criteria",
        "research_assurance",
        "report_contract",
    ]:
        assert required in contract


def test_discovery_playbooks_cover_scout_assay_and_spike() -> None:
    playbooks = {
        "scout-review.md": ["Scout Review", "_inbox/YYYY-Www.md", "_backlog.md"],
        "assay.md": ["Assay", "assay_scorecard", "validate_assay_scorecard"],
        "spike.md": ["Spike", "spike_preregistration", "validate_spike_preregistration"],
    }
    for filename, required_strings in playbooks.items():
        text = (PLAYBOOKS_DIR / filename).read_text(encoding="utf-8")
        assert "Use this when no skill wrapper is available" in text
        assert "Inputs" in text
        assert "Outputs" in text
        assert "Validation" in text
        for required in required_strings:
            assert required in text
