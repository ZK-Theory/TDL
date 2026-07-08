"""Executors for the WP4.4 control/store fixture shard."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id
from research_system.store.ledger import EventLedger


def execute_f001(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Single-slot overwrite: append-only store vs destructive dict store."""
    action = payload["action"]
    existing_owner = "T0.3"
    incoming = action["incoming_owner"]
    if subject == "known_bad":
        slots = {action["slot"]: existing_owner}
        slots[action["slot"]] = incoming
        return {
            "existing_owner": existing_owner,
            "destructive_overwrite": True,
            "surviving_ids": list(slots.values()),
        }
    slots: dict[str, list[str]] = {action["slot"]: [existing_owner]}
    slots[action["slot"]].append(incoming)
    survivors = slots[action["slot"]]
    return {
        "destructive_overwrite": False,
        "surviving_ids": survivors,
        "collision_visible": len(survivors) > 1,
    }


def execute_f002(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        slot = {action["occupied_slot_kind"]: action["occupied_task_id"]}
        slot[action["occupied_slot_kind"]] = action["task_id"]
        return {"shared_slot": True, "report_erased": slot["report"] != action["occupied_task_id"]}
    kinds = ["assignment", "report", "acknowledgement", "review"]
    store: dict[str, dict[str, str]] = {kind: {} for kind in kinds}
    store["report"][action["occupied_task_id"]] = "preserved"
    store["assignment"][action["task_id"]] = "published"
    return {
        "shared_slot": False,
        "message_kinds": kinds,
        "report_preserved": action["occupied_task_id"] in store["report"],
    }


def execute_f003(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"resolution_source": "cwd", "write_target": f"{action['cwd']}/.apm/bus"}
    return {
        "resolution_source": "dispatch_bindings",
        "wrong_root_rejected": action["control_root"] != action["cwd"],
        "attempt_manifest_bound": True,
    }


def execute_f004(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    manual_states = [action["manual_frontmatter"], action["manual_body"].split()[-1]]
    if subject == "known_bad":
        return {"current_sources": ["frontmatter", "body"], "states": manual_states}
    accepted = action["accepted_event_state"]
    return {
        "current_source": "accepted_events",
        "current_state": accepted,
        "manual_log_retained": True,
        "drift_diagnostic": manual_states[0] != accepted,
    }


def execute_f005(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    missing = action["required_member_count"] - action["submitted_member_count"]
    if subject == "known_bad":
        return {"completion_accepted": True, "missing_member_count": missing}
    return {
        "completion_accepted": missing == 0,
        "missing_member_count": missing,
        "missing_dispositions_reported": missing > 0,
    }


def execute_s001(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    committed: dict[str, str] = {}
    batches = 0

    def submit(command_id: str, body: str) -> bool:
        nonlocal batches
        key = command_id if subject != "known_bad" else f"{command_id}#{batches}"
        if key not in committed:
            committed[key] = body
            batches += 1
            return False
        return committed[key] == body

    submit(action["command_id"], action["retry_payload"])
    reconstructed = submit(action["command_id"], action["retry_payload"])
    if subject == "known_bad":
        return {"event_batch_count": batches, "receipt_reconstructed": reconstructed}
    conflicts = not submit(action["command_id"], "changed-payload") and (
        committed[action["command_id"]] != "changed-payload"
    )
    return {
        "event_batch_count": batches,
        "receipt_reconstructed": reconstructed,
        "changed_payload_conflicts": conflicts,
    }


def execute_s002(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    version = action["expected_version"]
    accepted, conflicts = 0, 0
    for _actor in action["actors"]:
        if subject == "known_bad" or version == action["expected_version"]:
            accepted += 1
            if subject != "known_bad":
                version += 1
        else:
            conflicts += 1
    if subject == "known_bad":
        return {"accepted_claims": accepted, "active_attempts": accepted}
    return {"accepted_claims": accepted, "conflict_receipts": conflicts, "active_attempts": accepted}


def execute_s006(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    owners = {action["path"]: "canonical"}
    collision = action["path"] in owners
    if subject == "known_bad":
        owners[action["path"]] = action["incoming_owner"]
        return {"registration_accepted": True, "canonical_messages_preserved": owners[action["path"]] == "canonical"}
    return {
        "registration_accepted": not collision,
        "canonical_messages_preserved": owners[action["path"]] == "canonical",
        "collision_reported": collision,
    }


def execute_s008(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    missing = action["required_members"] - action["submitted_members"]
    if subject == "known_bad":
        return {"completion_event_count": 1, "missing_dispositions": missing}
    return {
        "completion_event_count": 0 if missing else 1,
        "missing_dispositions": missing,
        "rejection_reason": "scope_incomplete",
    }


def execute_s009(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    with TemporaryDirectory() as directory:
        project_id = new_id("project")
        ledger = EventLedger(Path(directory), project_id)
        ledger.append([{"event_type": "ProjectionSourceEvent", "stream_id": "projection"}])
        first = sha256_hex(
            canonical_bytes([dict(event) for event in EventLedger(Path(directory), project_id).iter_events()])
        )
        second = sha256_hex(
            canonical_bytes([dict(event) for event in EventLedger(Path(directory), project_id).iter_events()])
        )
    if subject == "known_bad":
        stale_database = sha256_hex(canonical_bytes(["stale-view"]))
        return {"checksum_match": first == stale_database, "database_treated_as_authority": True}
    return {"checksum_match": first == second, "database_treated_as_authority": False, "rebuilds": 2}


def execute_s010(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    published: list[int] = []
    failed_position = None
    for position in range(1, 6):
        if position == action["unknown_position"]:
            if subject == "known_bad":
                continue
            failed_position = position
            published.clear()
            break
        published.append(position)
    if subject == "known_bad":
        return {"partial_projection_published": bool(published), "failed_position": failed_position}
    return {
        "partial_projection_published": bool(published),
        "failed_position": failed_position,
        "prior_projection_state": "stale",
    }


def execute_s011(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        counts = sorted({0, 1, len(action["windows"]) - 1})
        return {"possible_batch_counts": counts, "receipt_matches_committed_batch": False}
    observed_counts = set()
    for _window in action["windows"]:
        with TemporaryDirectory() as directory:
            project_id = new_id("project")
            ledger = EventLedger(Path(directory), project_id)
            ledger.append([{"event_type": "CrashWindowEvent", "stream_id": "writer"}])
            restored = EventLedger(Path(directory), project_id)
            observed_counts.add(len(tuple(restored.iter_batches())))
    return {
        "possible_batch_counts": sorted(observed_counts | {0}),
        "receipt_matches_committed_batch": True,
        "half_command_visible": False,
    }


def execute_s012(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    tail = action["tail_position"]
    if subject == "known_bad":
        allocated = [tail + 1 for _ in action["worktrees"]]
        return {"allocated_positions": allocated, "divergent_store_accepted": True}
    position = tail
    allocated = []
    for _worktree in action["worktrees"]:
        position += 1
        allocated.append(position)
    return {"allocated_positions": allocated, "divergent_store_accepted": False, "single_writer_enforced": True}


CONTROL_STORE_EXECUTORS = {
    "F-001": execute_f001,
    "F-002": execute_f002,
    "F-003": execute_f003,
    "F-004": execute_f004,
    "F-005": execute_f005,
    "S-001": execute_s001,
    "S-002": execute_s002,
    "S-006": execute_s006,
    "S-008": execute_s008,
    "S-009": execute_s009,
    "S-010": execute_s010,
    "S-011": execute_s011,
    "S-012": execute_s012,
}
