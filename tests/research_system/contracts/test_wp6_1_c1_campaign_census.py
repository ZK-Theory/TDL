"""Campaign census checks for WP6.1 C1 row ownership."""

from __future__ import annotations

from pathlib import Path

import yaml

from research_system.schema_registry import runtime_schema_registry

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-owner-source-catalogue.yaml"


# Copied verbatim from plan section 5.
C1_ROWS = {
    "task.request_readiness",
    "task.approve_readiness",
    "task.claim_start",
    "dispatch.issue",
    "dispatch.deliver",
    "dispatch.acknowledge",
    "dispatch.claim",
    "dispatch.expire_issued",
    "dispatch.expire_delivered",
    "dispatch.expire_acknowledged",
    "dispatch.withdraw_issued",
    "lease.activate",
    "lease.renew",
    "lease.release",
    "lease.expire",
    "lease.revoke",
    "attempt.create",
    "attempt.claim",
    "attempt.start",
    "operator.request_resource_grant",
    "operator.claim_execution_lease",
    "operator.record_heartbeat",
    "operator.release_resources",
}

C2_ROWS = {
    "task.block",
    "task.request_input",
    "task.pause",
    "task.submit_review",
    "task.resume",
    "task.cancel",
    "dispatch.fulfil",
    "dispatch.withdraw_claimed",
    "attempt.complete",
    "attempt.fail",
    "attempt.partial",
    "attempt.pause",
    "attempt.resume",
    "attempt.request_stop",
    "attempt.abandon",
    "attempt.supersede",
    "attempt.retry",
    "checkpoint.record",
    "blocker.record",
    "blocker.resolve",
    "artefact.register",
    "review.request",
    "operator.request_pause",
    "operator.confirm_pause",
    "operator.request_stop",
    "operator.confirm_stop",
    "operator.request_resume",
    "operator.quarantine_orphan",
}

C3_ROWS = {
    "scope.complete",
    "task.accept",
    "task.reject",
    "task.close_partial",
    "task.reopen_partial",
    "task.reopen_rejected",
    "task.reopen_cancelled",
    "artefact.availability",
    "artefact.regenerability",
    "artefact.integrity",
    "artefact.structural_validation",
    "artefact.scientific_review",
    "artefact.use_authority",
    "artefact.supersede",
    "operator.adopt_late_artefact",
    "review.assign",
    "review.start",
    "review.record_verdict",
    "review.request_changes",
    "review.satisfy",
    "review.satisfy_after_changes",
    "review.withdraw",
    "review.supersede",
    "decision.propose",
    "decision.request_review",
    "decision.resolve",
    "decision.reject",
    "decision.expire",
    "decision.supersede",
    "rule.evaluate",
    "decision.amend",
    "correction.record",
}

R1_ROWS = {
    "operator.create_backup",
    "operator.verify_restore",
}


def _catalogue_keys() -> list[str]:
    return [row["key"] for row in yaml.safe_load(CATALOGUE_PATH.read_text(encoding="utf-8"))["rows"]]


def test_wp6_1_c1_campaign_census_matches_normative_plan_allocation() -> None:
    row_keys = _catalogue_keys()
    all_rows = set(row_keys)

    # Catalogue geometry
    assert len(row_keys) == 104
    assert len(all_rows) == 104

    # Campaign literal sets
    assert len(C1_ROWS) == 23
    assert len(C2_ROWS) == 28
    assert len(C3_ROWS) == 32
    assert len(R1_ROWS) == 2

    assert C1_ROWS.isdisjoint(C2_ROWS)
    assert C1_ROWS.isdisjoint(C3_ROWS)
    assert C1_ROWS.isdisjoint(R1_ROWS)
    assert C2_ROWS.isdisjoint(C3_ROWS)
    assert C2_ROWS.isdisjoint(R1_ROWS)
    assert C3_ROWS.isdisjoint(R1_ROWS)

    campaign_rows = C1_ROWS | C2_ROWS | C3_ROWS | R1_ROWS
    assert len(campaign_rows) == 85

    # Baseline-active is the catalogue complement.
    active_rows = all_rows - campaign_rows
    assert len(active_rows) == 19

    # Campaign keys must match catalogue minus active rows and not introduce unknown keys.
    assert all_rows == (campaign_rows | active_rows)
    assert campaign_rows <= all_rows
    assert active_rows.isdisjoint(campaign_rows)
    assert len(active_rows | campaign_rows) == 104


def test_wp6_1_current_runtime_census_is_104_active_zero_remaining() -> None:
    rows = yaml.safe_load(CATALOGUE_PATH.read_text(encoding="utf-8"))["rows"]
    registry = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    active = [row["key"] for row in rows if registry.command_binding(row["command_type"]) is not None]
    remaining = [row["key"] for row in rows if registry.command_binding(row["command_type"]) is None]

    assert len(active) == 104
    assert remaining == []
