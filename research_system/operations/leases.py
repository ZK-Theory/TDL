"""Lease heartbeat, runtime, artefact, and stop predicates."""

from datetime import datetime


def heartbeat_disposition(profile: str, heartbeat_policy: dict) -> dict:
    if profile == "trivial":
        expected = {
            "status": "not_applicable",
            "reason": "terminal_receipt_closes_lease",
        }
        if heartbeat_policy != expected:
            raise ValueError("invalid trivial heartbeat disposition")
        return heartbeat_policy
    if not heartbeat_policy.get("cadence_s") or not heartbeat_policy.get("grace_s"):
        raise ValueError("periodic heartbeat policy required")
    return heartbeat_policy


def runtime_disposition(*, elapsed_s: int, hard_limit_s: int) -> dict:
    if elapsed_s > hard_limit_s:
        return {"status": "stop_required", "reason": "hard_runtime_limit"}
    return {"status": "within_limit", "reason": None}


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def artifact_disposition(*, observed_at: str, lease_expires_at: str) -> dict:
    if _instant(observed_at) > _instant(lease_expires_at):
        return {
            "status": "late_artifact",
            "preserve": True,
            "acceptance_allowed": False,
        }
    return {
        "status": "within_lease",
        "preserve": True,
        "acceptance_allowed": True,
    }


def stop_confirmation(
    *, provider: str, process_children: str, output_writer: str, checkpoint_writer: str
) -> str:
    terminal = {"terminal", "not_applicable"}
    dispositions = {provider, process_children, output_writer, checkpoint_writer}
    return "confirmed" if dispositions <= terminal else "stop_uncertain"
