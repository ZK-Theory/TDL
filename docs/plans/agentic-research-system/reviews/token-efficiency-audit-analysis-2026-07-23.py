#!/usr/bin/env python3
"""Lineage-aware all-history Codex token-efficiency census.

The primary unit is every retained JSONL byte prefix beneath the live and
archived Codex session stores. Spawned child files can embed their parent's
history, so token usage is derived only from the child-local boundary. The
script emits a complete session manifest plus a compact aggregate summary.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import pathlib
import re
from datetime import UTC, datetime
from typing import Any

ROOTS = (
    ("live", pathlib.Path(r"C:\Users\steph\.codex\sessions")),
    ("archived", pathlib.Path(r"C:\Users\steph\.codex\archived_sessions")),
)
FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
COMPONENT_FIELDS = FIELDS[:-1]
POLL_TOOLS = {"wait", "wait_agent", "list_agents", "wait_threads", "read_thread"}
TEAM_MARKER = "You are an agent in a team of agents collaborating"
WP63_REVIEW_SESSION = "019f765a-6903-7401-b103-e7a51aa2ee14"
OBSERVER_SKILL_RE = re.compile(r"(?i)(research-observer|task-observer)[\\/]+SKILL\.md")
OBSERVER_LOG_RE = re.compile(r"(?i)skill-observations.*(log\.md|cross-cutting-principles)")
SKILL_RE = re.compile(r"(?i)skills?[\\/]+[^\\/]+[\\/]+SKILL\.md")
WRAPPER_PREFIXES = (
    "# AGENTS.md instructions",
    "<environment_context>",
    "<permissions instructions>",
    "<recommended_plugins>",
)
ACTIVITY_PATTERNS = {
    "review": re.compile(
        r"(?i)\b(review|audit|assess|verify|validation|validate|gate|finding|adversarial|"
        r"assurance|inspect|triage|coderabbit|acceptance)\w*"
    ),
    "planning": re.compile(
        r"(?i)\b(plan|dispatch|handoff|handback|manager|brief|roadmap|strategy|work package|" r"coordinate|initiate)\w*"
    ),
    "implementation": re.compile(
        r"(?i)\b(implement|fix|repair|patch|remediat|refactor|change|update|edit|create|" r"build|migrat)\w*"
    ),
    "empirical": re.compile(
        r"(?i)\b(analy[sz]|experiment|battery|compute|benchmark|statistic|estimand|"
        r"wasserstein|topolog|markov|null|bhps|usoc|trajectory|simulation)\w*"
    ),
    "writing": re.compile(
        r"(?i)\b(write|draft|paper|manuscript|prose|document|readme|latex|copyedit|" r"lesson|report)\w*"
    ),
    "tooling": re.compile(
        r"(?i)\b(setup|install|config|plugin|skill|memory|vault|worktree|branch|commit|git|"
        r"github|pull request|sync|cleanup|repository|ci)\w*"
    ),
    "web_design": re.compile(
        r"(?i)\b(website|web app|css|html|figma|design|storybook|visuali[sz]|diagram|" r"frontend|react|next\.js)\w*"
    ),
    "learning": re.compile(
        r"(?i)\b(mathuni|learn|study|exercise|proof|theorem|algebra|category theory|" r"geometry)\w*"
    ),
    "control": re.compile(r"(?i)\b(turn_aborted|heartbeat|poll|wait|status check|continue|monitor|proceed)\w*"),
}


def zero() -> dict[str, int]:
    return {field: 0 for field in FIELDS}


def content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(item.get("text", "")) for item in value if isinstance(item, dict) and item.get("text"))
    return ""


def output_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def percentile(values: list[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def project_from_cwd(cwd: str) -> str:
    lowered = cwd.lower()
    if re.search(r"(?i)(?:\\|/)tdl(?:\\|/|$)", cwd):
        return "TDL"
    if "zktheoryweb" in lowered or "vibecoded-design-tells" in lowered:
        return "web_design"
    if "cosmo diary" in lowered:
        return "Cosmo_Diary"
    if "mathuni" in lowered:
        return "MathUni"
    if ".codex" in lowered or ".agents" in lowered:
        return "agent_configuration"
    return "other"


def source_kind(meta: dict[str, Any]) -> str:
    source = meta.get("source")
    if isinstance(source, dict):
        subagent = source.get("subagent") or {}
        if subagent.get("other") == "guardian":
            return "guardian"
        if isinstance(subagent.get("thread_spawn"), dict):
            return "spawned_subagent"
    if meta.get("thread_source") == "subagent":
        return "delegated_task"
    if source == "exec" or meta.get("thread_source") == "automation":
        return "automation"
    return "root"


def parent_and_agent(meta: dict[str, Any]) -> tuple[str, str]:
    source = meta.get("source")
    if isinstance(source, dict):
        spawn = (source.get("subagent") or {}).get("thread_spawn")
        if isinstance(spawn, dict):
            return str(spawn.get("parent_thread_id", "")), str(spawn.get("agent_path", ""))
    return str(meta.get("parent_thread_id", "")), str(meta.get("agent_path", ""))


def read_prefix(path: pathlib.Path, size: int | None = None) -> bytes:
    with path.open("rb") as handle:
        snapshot = handle.read() if size is None else handle.read(size)
    if snapshot and not snapshot.endswith(b"\n"):
        newline = snapshot.rfind(b"\n")
        snapshot = snapshot[: newline + 1] if newline >= 0 else b""
    return snapshot


def records_from_snapshot(snapshot: bytes) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    errors = 0
    for raw in snapshot.splitlines():
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            errors += 1
    return records, errors


def local_boundary(records: list[dict[str, Any]], meta: dict[str, Any], inherited: bool) -> tuple[int, str]:
    if source_kind(meta) != "spawned_subagent":
        return 0, "file_start"
    team_markers: list[int] = []
    task_starts: list[int] = []
    for seq, record in enumerate(records):
        payload = record.get("payload") or {}
        ptype = payload.get("type")
        if (
            record.get("type") == "response_item"
            and ptype == "message"
            and payload.get("role") == "developer"
            and TEAM_MARKER in content_text(payload.get("content"))
        ):
            team_markers.append(seq)
        if record.get("type") == "event_msg" and ptype == "task_started":
            task_starts.append(seq)
    if team_markers and task_starts:
        marker = team_markers[0]
        boundary = min(task_starts, key=lambda seq: abs(seq - marker))
        if abs(boundary - marker) <= 4:
            return boundary, "team_marker_adjacent_task_start"
    if inherited:
        return 0, "ambiguous_inherited_history"
    return 0, "no_inherited_history"


def current_total(payload: dict[str, Any]) -> tuple[dict[str, int | None], set[str]]:
    info = payload.get("info") or {}
    raw = info.get("total_token_usage") or {}
    present = {field for field in FIELDS if field in raw}
    values: dict[str, int | None] = {
        field: int(raw.get(field, 0) or 0) if field in present else None for field in FIELDS
    }
    # Older summary records preserve total_tokens while setting every component
    # to zero. Zero here means "not recorded", not a measured zero.
    if (
        int(values.get("total_tokens") or 0) > 0
        and int(values.get("input_tokens") or 0) == 0
        and int(values.get("output_tokens") or 0) == 0
        and all(int(values.get(field) or 0) == 0 for field in COMPONENT_FIELDS)
    ):
        for field in COMPONENT_FIELDS:
            values[field] = None
            present.discard(field)
    return values, present


def cumulative_delta(
    current: dict[str, int | None],
    previous: dict[str, int | None],
    present: set[str],
) -> tuple[dict[str, int | None], bool]:
    comparable = [field for field in present if current.get(field) is not None and previous.get(field) is not None]
    reset = any(int(current[field] or 0) < int(previous[field] or 0) for field in comparable)
    result: dict[str, int | None] = {}
    for field in FIELDS:
        value = current.get(field)
        if value is None:
            result[field] = None
        elif reset or previous.get(field) is None:
            result[field] = int(value)
        else:
            result[field] = int(value) - int(previous[field] or 0)
    return result, reset


def positive_usage(delta: dict[str, int | None]) -> bool:
    return (
        int(delta.get("input_tokens") or 0) > 0
        or int(delta.get("output_tokens") or 0) > 0
        or (delta.get("total_tokens") is not None and int(delta.get("total_tokens") or 0) > 0)
    )


def add_usage(target: dict[str, int], delta: dict[str, int | None]) -> None:
    for field in FIELDS:
        if delta.get(field) is not None:
            target[field] += max(0, int(delta[field] or 0))


def classify_activity(value: str) -> list[str]:
    labels = [name for name, pattern in ACTIVITY_PATTERNS.items() if pattern.search(value)]
    return labels or ["unclassified"]


def first_visible_text(records: list[dict[str, Any]], start: int, end: int) -> str:
    event_fallback = ""
    for record in records[start:end]:
        payload = record.get("payload") or {}
        ptype = payload.get("type")
        if record.get("type") == "event_msg" and ptype == "user_message":
            value = str(payload.get("message", "")).strip()
            if value:
                return value
        if record.get("type") == "response_item" and ptype == "message" and payload.get("role") == "user":
            value = content_text(payload.get("content")).strip()
            if value and not value.startswith(WRAPPER_PREFIXES):
                return value
            event_fallback = event_fallback or value
    return event_fallback


def task_labels(records: list[dict[str, Any]], boundary: int, agent_path: str) -> tuple[int, collections.Counter[str]]:
    starts = [
        seq
        for seq, record in enumerate(records)
        if seq >= boundary
        and record.get("type") == "event_msg"
        and (record.get("payload") or {}).get("type") == "task_started"
    ]
    labels: collections.Counter[str] = collections.Counter()
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(records)
        value = first_visible_text(records, start, end) or agent_path
        labels.update(classify_activity(value))
    return len(starts), labels


def parse_guardian_decisions(records: list[dict[str, Any]], boundary: int) -> collections.Counter[str]:
    decisions: collections.Counter[str] = collections.Counter()
    for record in records[boundary:]:
        payload = record.get("payload") or {}
        if (
            record.get("type") == "response_item"
            and payload.get("type") == "message"
            and payload.get("role") == "assistant"
        ):
            value = content_text(payload.get("content"))
            match = re.search(r'"outcome"\s*:\s*"([^"]+)', value)
            if match:
                decisions[match.group(1)] += 1
    return decisions


def wait_counterfactual(wait_events: list[dict[str, Any]]) -> dict[str, int]:
    runs: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_key = ""
    previous_round = -2
    for event in wait_events:
        key = event["cell_id"]
        if current and (key != current_key or event["round"] != previous_round + 1):
            runs.append(current)
            current = []
        current.append(event)
        current_key = key
        previous_round = event["round"]
    if current:
        runs.append(current)

    eliminated = 0
    lower = zero()
    for run in runs:
        requested = sum(event["yield_ms"] for event in run)
        keep = max(1, math.ceil(requested / 60_000))
        remove = max(0, len(run) - keep)
        eliminated += remove
        if remove:
            smallest = sorted(run, key=lambda event: int(event["usage"].get("total_tokens") or 0))[:remove]
            for event in smallest:
                add_usage(lower, event["usage"])
    return {
        "sequences": len(runs),
        "observed_rounds": len(wait_events),
        "eliminated_rounds": eliminated,
        "eliminated_processed_lower_bound": lower["total_tokens"],
        "eliminated_input_lower_bound": lower["input_tokens"],
        "eliminated_cached_input_lower_bound": lower["cached_input_tokens"],
        "eliminated_uncached_input_lower_bound": (lower["input_tokens"] - lower["cached_input_tokens"]),
        "eliminated_output_lower_bound": lower["output_tokens"],
    }


def parse_session(
    store: str,
    root: pathlib.Path,
    source: pathlib.Path,
    snapshot: bytes,
) -> dict[str, Any]:
    records, parse_errors = records_from_snapshot(snapshot)
    metas = [record.get("payload") or {} for record in records if record.get("type") == "session_meta"]
    if not metas:
        raise ValueError(f"no session_meta in {source}")
    meta = metas[0]
    session_id = str(meta.get("id", ""))
    embedded_ids = {str(item.get("id", "")) for item in metas if item.get("id")}
    inherited = any(item != session_id for item in embedded_ids)
    boundary, boundary_rule = local_boundary(records, meta, inherited)
    parent_id, agent_path = parent_and_agent(meta)

    first_timestamp = str(records[0].get("timestamp", "")) if records else ""
    last_timestamp = str(records[-1].get("timestamp", "")) if records else ""
    actor = source_kind(meta)
    project = project_from_cwd(str(meta.get("cwd", "")))
    usage = zero()
    previous: dict[str, int | None] = {field: 0 for field in FIELDS}
    token_records = local_token_records = reset_events = unchanged_records = 0
    component_records = total_only_records = null_usage_records = 0
    first_call = zero()
    call_events: list[dict[str, Any]] = []
    pending_tools: list[dict[str, Any]] = []
    round_number = 0
    pure_poll = zero()
    pure_poll_rounds = 0
    pure_poll_names: collections.Counter[str] = collections.Counter()
    wait_events: list[dict[str, Any]] = []
    wait_usage = zero()

    calls: dict[str, dict[str, Any]] = {}
    tool_output_events: list[tuple[int, int]] = []
    tool_calls = tool_outputs = tool_output_chars = large_outputs = 0
    observer_skill_reads = observer_skill_chars = 0
    observer_log_reads = observer_log_chars = 0
    other_skill_reads = other_skill_chars = 0
    compaction_sequences: list[int] = []
    task_complete = turn_aborted = patch_events = 0
    active_turns: list[dict[str, str]] = []

    for seq, record in enumerate(records):
        payload = record.get("payload") or {}
        ptype = payload.get("type")
        rtype = record.get("type")

        if rtype == "event_msg" and ptype == "token_count":
            token_records += 1
            current, present = current_total(payload)
            if not present:
                null_usage_records += int(seq >= boundary)
                continue
            delta, reset = cumulative_delta(current, previous, present)
            if seq >= boundary:
                local_token_records += 1
                reset_events += int(reset)
                if COMPONENT_FIELDS[0] in present:
                    component_records += 1
                elif "total_tokens" in present:
                    total_only_records += 1
                if positive_usage(delta):
                    add_usage(usage, delta)
                    if not any(first_call.values()):
                        add_usage(first_call, delta)
                    call_events.append({"seq": seq, "usage": delta})
                    names = [item["name"] for item in pending_tools]
                    if names and all(name in POLL_TOOLS for name in names):
                        pure_poll_rounds += 1
                        pure_poll_names.update(names)
                        add_usage(pure_poll, delta)
                    if len(pending_tools) == 1 and pending_tools[0]["name"] == "wait":
                        item = pending_tools[0]
                        event = {
                            "round": round_number,
                            "cell_id": str(item["arguments"].get("cell_id", "")),
                            "yield_ms": int(item["arguments"].get("yield_time_ms", 10_000) or 10_000),
                            "usage": delta,
                        }
                        wait_events.append(event)
                        add_usage(wait_usage, delta)
                    pending_tools = []
                    round_number += 1
                else:
                    unchanged_records += 1
            previous = current
            continue

        if seq < boundary:
            if rtype == "event_msg" and ptype == "token_count":
                current, present = current_total(payload)
                if present:
                    previous = current
            continue

        if rtype == "turn_context":
            active_turns.append(
                {
                    "model": str(payload.get("model", "")),
                    "effort": str(payload.get("effort", "")),
                }
            )
        elif rtype == "compacted":
            compaction_sequences.append(seq)
        elif rtype == "event_msg" and ptype == "task_complete":
            task_complete += 1
        elif rtype == "event_msg" and ptype == "turn_aborted":
            turn_aborted += 1
        elif rtype == "event_msg" and ptype == "patch_apply_end":
            patch_events += 1

        if rtype != "response_item":
            continue
        if ptype in ("custom_tool_call", "function_call"):
            call_id = str(payload.get("call_id", ""))
            name = str(payload.get("name", ""))
            raw_arguments = payload.get("input") or payload.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            item = {
                "seq": seq,
                "name": name,
                "input": str(raw_arguments),
                "arguments": arguments if isinstance(arguments, dict) else {},
            }
            calls[call_id] = item
            pending_tools.append(item)
            tool_calls += 1
        elif ptype in ("custom_tool_call_output", "function_call_output"):
            call_id = str(payload.get("call_id", ""))
            value = output_text(payload.get("output"))
            size = len(value)
            tool_outputs += 1
            tool_output_chars += size
            tool_output_events.append((seq, size))
            large_outputs += int(size >= 20_000)
            call = calls.get(call_id)
            if not call:
                continue
            call_input = call["input"]
            if OBSERVER_SKILL_RE.search(call_input):
                observer_skill_reads += 1
                observer_skill_chars += size
            elif OBSERVER_LOG_RE.search(call_input):
                observer_log_reads += 1
                observer_log_chars += size
            elif SKILL_RE.search(call_input):
                other_skill_reads += 1
                other_skill_chars += size

    task_starts, activity_labels = task_labels(records, boundary, agent_path)
    guardian = parse_guardian_decisions(records, boundary) if actor == "guardian" else collections.Counter()
    task_start_sequences = [
        seq
        for seq, record in enumerate(records)
        if seq >= boundary
        and record.get("type") == "event_msg"
        and (record.get("payload") or {}).get("type") == "task_started"
    ]
    annotated_segments: list[dict[str, Any]] = []
    if session_id == WP63_REVIEW_SESSION:
        for index, start in enumerate(task_start_sequences[:6]):
            end = task_start_sequences[index + 1] if index + 1 < len(task_start_sequences) else len(records)
            segment_usage = zero()
            selected_calls = [event for event in call_events if start <= event["seq"] < end]
            for event in selected_calls:
                add_usage(segment_usage, event["usage"])
            annotated_segments.append(
                {
                    "review": f"R{index + 5}",
                    "start_seq": start,
                    "end_seq": end,
                    "inference_rounds": len(selected_calls),
                    "input_including_cache": segment_usage["input_tokens"],
                    "cache_read": segment_usage["cached_input_tokens"],
                    "uncached_input": (segment_usage["input_tokens"] - segment_usage["cached_input_tokens"]),
                    "output": segment_usage["output_tokens"],
                    "processed": segment_usage["total_tokens"],
                    "tool_output_chars": sum(size for seq, size in tool_output_events if start <= seq < end),
                }
            )

    compaction_pairs: list[dict[str, int]] = []
    terminal_compactions = 0
    for compact in compaction_sequences:
        before = [event for event in call_events if event["seq"] < compact]
        after = [event for event in call_events if event["seq"] > compact]
        if not before or not after:
            terminal_compactions += 1
            continue
        pre = before[-1]["usage"]
        post = after[0]["usage"]
        if pre.get("input_tokens") is None or post.get("input_tokens") is None:
            continue
        compaction_pairs.append(
            {
                "pre_input": int(pre["input_tokens"] or 0),
                "post_input": int(post["input_tokens"] or 0),
            }
        )

    if component_records and total_only_records:
        telemetry_tier = "mixed"
    elif component_records:
        telemetry_tier = "full_components"
    elif total_only_records:
        telemetry_tier = "total_only"
    else:
        telemetry_tier = "no_usage"

    context_mode = "not_spawned"
    if actor == "spawned_subagent":
        context_mode = "inherited_history" if inherited else "no_parent_history"

    return {
        "session_id": session_id,
        "store": store,
        "relative_path": str(source.relative_to(root)),
        "absolute_path": str(source),
        "snapshot_bytes": len(snapshot),
        "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "records": len(records),
        "parse_errors": parse_errors,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "cwd": str(meta.get("cwd", "")),
        "project": project,
        "actor": actor,
        "parent_id": parent_id,
        "agent_path": agent_path,
        "embedded_session_ids": sorted(embedded_ids),
        "inherited_history": inherited,
        "local_boundary_seq": boundary,
        "boundary_rule": boundary_rule,
        "context_mode": context_mode,
        "telemetry_tier": telemetry_tier,
        "token_records": token_records,
        "local_token_records": local_token_records,
        "unchanged_token_records": unchanged_records,
        "counter_reset_events": reset_events,
        "usage": usage,
        "first_call": first_call,
        "inference_rounds": len(call_events),
        "turns": len(active_turns),
        "models": sorted({item["model"] for item in active_turns if item["model"]}),
        "efforts": sorted({item["effort"] for item in active_turns if item["effort"]}),
        "model_counts": dict(sorted(collections.Counter(item["model"] for item in active_turns).items())),
        "effort_counts": dict(sorted(collections.Counter(item["effort"] for item in active_turns).items())),
        "task_starts": task_starts,
        "task_complete_events": task_complete,
        "turn_aborted_events": turn_aborted,
        "activity_labels": dict(sorted(activity_labels.items())),
        "compactions": len(compaction_sequences),
        "compaction_pairs": compaction_pairs,
        "terminal_compactions": terminal_compactions,
        "patch_events": patch_events,
        "tool_calls": tool_calls,
        "tool_outputs": tool_outputs,
        "tool_output_chars": tool_output_chars,
        "tool_outputs_ge_20000_chars": large_outputs,
        "pure_poll_rounds": pure_poll_rounds,
        "pure_poll_names": dict(sorted(pure_poll_names.items())),
        "pure_poll_usage": pure_poll,
        "wait_usage": wait_usage,
        "wait_counterfactual": wait_counterfactual(wait_events),
        "observer_skill_reads": observer_skill_reads,
        "observer_skill_output_chars": observer_skill_chars,
        "observer_log_reads": observer_log_reads,
        "observer_log_output_chars": observer_log_chars,
        "other_skill_reads": other_skill_reads,
        "other_skill_output_chars": other_skill_chars,
        "guardian_decisions": dict(sorted(guardian.items())),
        "annotated_segments": annotated_segments,
    }


def usage_sum(rows: list[dict[str, Any]], key: str = "usage") -> dict[str, int]:
    result = zero()
    for row in rows:
        for field in FIELDS:
            result[field] += int(row[key].get(field, 0) or 0)
    return result


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usage = usage_sum(rows)
    return {
        "sessions": len(rows),
        "processed": usage["total_tokens"],
        "input_including_cache": usage["input_tokens"],
        "cache_read": usage["cached_input_tokens"],
        "uncached_input": usage["input_tokens"] - usage["cached_input_tokens"],
        "cache_write_input_recorded": usage["cache_write_input_tokens"],
        "output": usage["output_tokens"],
        "reasoning_output_subset": usage["reasoning_output_tokens"],
        "turns": sum(row["turns"] for row in rows),
        "inference_rounds": sum(row["inference_rounds"] for row in rows),
        "task_starts": sum(row["task_starts"] for row in rows),
        "compactions": sum(row["compactions"] for row in rows),
        "tool_calls": sum(row["tool_calls"] for row in rows),
        "tool_output_chars": sum(row["tool_output_chars"] for row in rows),
        "pure_poll_rounds": sum(row["pure_poll_rounds"] for row in rows),
        "turn_aborted_events": sum(row["turn_aborted_events"] for row in rows),
    }


def grouped(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = sorted({str(row[key]) for row in rows})
    return {value: aggregate([row for row in rows if str(row[key]) == value]) for value in values}


def poll_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pure = usage_sum(rows, "pure_poll_usage")
    waits = usage_sum(rows, "wait_usage")
    counter = collections.Counter()
    sequence_count = observed_rounds = eliminated_rounds = 0
    eliminated = zero()
    for row in rows:
        counter.update(row["pure_poll_names"])
        item = row["wait_counterfactual"]
        sequence_count += item["sequences"]
        observed_rounds += item["observed_rounds"]
        eliminated_rounds += item["eliminated_rounds"]
        eliminated["total_tokens"] += item["eliminated_processed_lower_bound"]
        eliminated["input_tokens"] += item["eliminated_input_lower_bound"]
        eliminated["cached_input_tokens"] += item["eliminated_cached_input_lower_bound"]
        eliminated["output_tokens"] += item["eliminated_output_lower_bound"]
    return {
        "pure_poll_rounds": sum(row["pure_poll_rounds"] for row in rows),
        "pure_poll_tool_names": dict(sorted(counter.items())),
        "pure_poll_usage": {
            "processed": pure["total_tokens"],
            "input_including_cache": pure["input_tokens"],
            "cache_read": pure["cached_input_tokens"],
            "uncached_input": pure["input_tokens"] - pure["cached_input_tokens"],
            "output": pure["output_tokens"],
        },
        "long_process_wait": {
            "sequences": sequence_count,
            "observed_rounds": observed_rounds,
            "observed_processed": waits["total_tokens"],
            "counterfactual": "replace observed short waits by at most 60-second waits; keep ceil(sum(requested_ms)/60000) rounds per consecutive cell-id run",
            "eliminated_rounds": eliminated_rounds,
            "eliminated_processed_lower_bound": eliminated["total_tokens"],
            "eliminated_uncached_input_lower_bound": (eliminated["input_tokens"] - eliminated["cached_input_tokens"]),
            "eliminated_cache_read_lower_bound": eliminated["cached_input_tokens"],
            "eliminated_output_lower_bound": eliminated["output_tokens"],
        },
    }


def context_comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for mode in ("inherited_history", "no_parent_history"):
        selected = [row for row in rows if row["context_mode"] == mode]
        first_inputs = [
            int(row["first_call"]["input_tokens"])
            for row in selected
            if row["telemetry_tier"] in {"full_components", "mixed"}
        ]
        result[mode] = {
            **aggregate(selected),
            "first_call_input_median": percentile(first_inputs, 0.5),
            "first_call_input_p90": percentile(first_inputs, 0.9),
        }
    return result


def compaction_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = [pair for row in rows for pair in row["compaction_pairs"]]
    pre = [pair["pre_input"] for pair in pairs]
    post = [pair["post_input"] for pair in pairs]
    return {
        "events": sum(row["compactions"] for row in rows),
        "paired_events": len(pairs),
        "terminal_or_unpaired": sum(row["terminal_compactions"] for row in rows),
        "pre_input_median": percentile(pre, 0.5),
        "pre_input_p10": percentile(pre, 0.1),
        "pre_input_p90": percentile(pre, 0.9),
        "post_input_median": percentile(post, 0.5),
        "post_input_p10": percentile(post, 0.1),
        "post_input_p90": percentile(post, 0.9),
    }


def observer_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "observer_skill_reads": sum(row["observer_skill_reads"] for row in rows),
        "observer_skill_output_chars": sum(row["observer_skill_output_chars"] for row in rows),
        "observer_log_reads": sum(row["observer_log_reads"] for row in rows),
        "observer_log_output_chars": sum(row["observer_log_output_chars"] for row in rows),
        "other_skill_reads": sum(row["other_skill_reads"] for row in rows),
        "other_skill_output_chars": sum(row["other_skill_output_chars"] for row in rows),
    }


def activity_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: collections.Counter[str] = collections.Counter()
    for row in rows:
        result.update(row["activity_labels"])
    return dict(sorted(result.items()))


def nested_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: collections.Counter[str] = collections.Counter()
    for row in rows:
        result.update(row[key])
    return dict(sorted(result.items()))


def guardian_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if row["actor"] == "guardian"]
    decisions: collections.Counter[str] = collections.Counter()
    for row in selected:
        decisions.update(row["guardian_decisions"])
    return {"aggregate": aggregate(selected), "decisions": dict(sorted(decisions.items()))}


def manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    usage = row["usage"]
    first = row["first_call"]
    return {
        "session_id": row["session_id"],
        "store": row["store"],
        "relative_path": row["relative_path"],
        "absolute_path": row["absolute_path"],
        "snapshot_bytes": row["snapshot_bytes"],
        "snapshot_sha256": row["snapshot_sha256"],
        "records": row["records"],
        "parse_errors": row["parse_errors"],
        "first_timestamp": row["first_timestamp"],
        "last_timestamp": row["last_timestamp"],
        "cwd": row["cwd"],
        "project": row["project"],
        "actor": row["actor"],
        "parent_id": row["parent_id"],
        "agent_path": row["agent_path"],
        "inherited_history": row["inherited_history"],
        "local_boundary_seq": row["local_boundary_seq"],
        "boundary_rule": row["boundary_rule"],
        "context_mode": row["context_mode"],
        "telemetry_tier": row["telemetry_tier"],
        "processed": usage["total_tokens"],
        "input_including_cache": usage["input_tokens"],
        "cache_read": usage["cached_input_tokens"],
        "uncached_input": usage["input_tokens"] - usage["cached_input_tokens"],
        "cache_write_input_recorded": usage["cache_write_input_tokens"],
        "output": usage["output_tokens"],
        "reasoning_output_subset": usage["reasoning_output_tokens"],
        "first_call_input": first["input_tokens"],
        "inference_rounds": row["inference_rounds"],
        "turns": row["turns"],
        "task_starts": row["task_starts"],
        "task_complete_events": row["task_complete_events"],
        "turn_aborted_events": row["turn_aborted_events"],
        "models": ";".join(row["models"]),
        "efforts": ";".join(row["efforts"]),
        "activity_labels": json.dumps(row["activity_labels"], sort_keys=True),
        "compactions": row["compactions"],
        "tool_calls": row["tool_calls"],
        "tool_outputs": row["tool_outputs"],
        "tool_output_chars": row["tool_output_chars"],
        "pure_poll_rounds": row["pure_poll_rounds"],
        "pure_poll_processed": row["pure_poll_usage"]["total_tokens"],
        "wait_rounds": row["wait_counterfactual"]["observed_rounds"],
        "wait_eliminated_rounds_60s": row["wait_counterfactual"]["eliminated_rounds"],
        "wait_eliminated_processed_lower_bound": row["wait_counterfactual"]["eliminated_processed_lower_bound"],
        "observer_skill_reads": row["observer_skill_reads"],
        "observer_skill_output_chars": row["observer_skill_output_chars"],
        "observer_log_reads": row["observer_log_reads"],
        "observer_log_output_chars": row["observer_log_output_chars"],
    }


def write_manifest(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    flattened = [manifest_row(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flattened[0]))
        writer.writeheader()
        writer.writerows(flattened)


def load_cut_manifest(path: pathlib.Path) -> list[tuple[str, pathlib.Path, int, str]]:
    result: list[tuple[str, pathlib.Path, int, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            result.append(
                (
                    row["store"],
                    pathlib.Path(row["absolute_path"]),
                    int(row["snapshot_bytes"]),
                    row["snapshot_sha256"],
                )
            )
    return result


def discover() -> list[tuple[str, pathlib.Path, int, str]]:
    result: list[tuple[str, pathlib.Path, int, str]] = []
    for store, root in ROOTS:
        for source in root.rglob("*.jsonl"):
            result.append((store, source, source.stat().st_size, ""))
    return sorted(result, key=lambda item: str(item[1]).lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-out", type=pathlib.Path)
    parser.add_argument("--summary-out", type=pathlib.Path)
    parser.add_argument("--cut-manifest", type=pathlib.Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    sources = load_cut_manifest(args.cut_manifest) if args.cut_manifest else discover()
    rows: list[dict[str, Any]] = []
    hash_failures: list[str] = []
    for store, source, size, expected_hash in sources:
        root = dict(ROOTS)[store]
        snapshot = read_prefix(source, size)
        actual_hash = hashlib.sha256(snapshot).hexdigest()
        if expected_hash and actual_hash != expected_hash:
            hash_failures.append(str(source))
        rows.append(parse_session(store, root, source, snapshot))

    session_ids = [row["session_id"] for row in rows]
    manifest_hash = hashlib.sha256(
        "\n".join(f"{row['session_id']}|{row['snapshot_bytes']}|{row['snapshot_sha256']}" for row in rows).encode()
    ).hexdigest()
    full_component_rows = [row for row in rows if row["telemetry_tier"] in {"full_components", "mixed"}]
    processed_identity_failures = sum(
        row["usage"]["total_tokens"] != row["usage"]["input_tokens"] + row["usage"]["output_tokens"]
        for row in full_component_rows
    )
    ambiguous_boundaries = [row["session_id"] for row in rows if row["boundary_rule"] == "ambiguous_inherited_history"]
    summary = {
        "schema": "token-efficiency-audit-all-history/v2",
        "evidence_cut_created_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "description": "every retained complete-line JSONL byte prefix beneath both configured Codex session stores",
            "roots": [str(root) for _, root in ROOTS],
            "files": len(rows),
            "snapshot_bytes": sum(row["snapshot_bytes"] for row in rows),
            "manifest_sha256": manifest_hash,
            "first_record_timestamp": min(row["first_timestamp"] for row in rows),
            "last_record_timestamp": max(row["last_timestamp"] for row in rows),
        },
        "semantics": {
            "processed": "child-local cumulative total_tokens; for full-component records this equals input including cache plus output",
            "lineage": "spawned child history before the adjacent team-marker/task-start boundary is excluded",
            "counter_resets": "usage is partitioned into monotone epochs and positive deltas are summed",
            "cache": "cache-read is part of input and must not be added again; cache-write is reported only where telemetry records it",
            "reasoning": "reasoning output is a subset of output and must not be added again",
            "cost": "the JSONL does not establish billed currency cost",
            "task_unit": "physical session and child-local task-start/turn proxies; durable accepted-artifact outcomes are not universally recorded",
        },
        "checks": {
            "unique_primary_session_ids": len(set(session_ids)),
            "duplicate_primary_session_ids": len(session_ids) - len(set(session_ids)),
            "parse_errors": sum(row["parse_errors"] for row in rows),
            "hash_failures_against_cut_manifest": hash_failures,
            "ambiguous_inherited_boundaries": ambiguous_boundaries,
            "counter_reset_events": sum(row["counter_reset_events"] for row in rows),
            "processed_identity_failures_full_component_sessions": processed_identity_failures,
            "tool_call_output_gap": sum(row["tool_calls"] - row["tool_outputs"] for row in rows),
        },
        "all_history": aggregate(rows),
        "by_store": grouped(rows, "store"),
        "by_project": grouped(rows, "project"),
        "by_actor": grouped(rows, "actor"),
        "by_context_mode": grouped(rows, "context_mode"),
        "by_telemetry_tier": grouped(rows, "telemetry_tier"),
        "activity_labels_overlapping": activity_summary(rows),
        "turn_models": nested_counts(rows, "model_counts"),
        "turn_efforts": nested_counts(rows, "effort_counts"),
        "spawn_context_comparison": context_comparison(rows),
        "polling": poll_summary(rows),
        "compactions": compaction_summary(rows),
        "observer_and_skill_reads": observer_summary(rows),
        "guardian": guardian_summary(rows),
        "natural_comparisons": {
            "wp63_same_reviewer_exact_head_r5_r10": next(
                (row["annotated_segments"] for row in rows if row["session_id"] == WP63_REVIEW_SESSION),
                [],
            )
        },
        "top_sessions_by_child_local_processed": [
            {
                "session_id": row["session_id"],
                "project": row["project"],
                "actor": row["actor"],
                "agent_path": row["agent_path"],
                "processed": row["usage"]["total_tokens"],
                "turns": row["turns"],
                "compactions": row["compactions"],
                "pure_poll_processed": row["pure_poll_usage"]["total_tokens"],
            }
            for row in sorted(rows, key=lambda item: item["usage"]["total_tokens"], reverse=True)[:25]
        ],
    }

    if args.manifest_out:
        write_manifest(args.manifest_out, rows)
    rendered = json.dumps(summary, indent=2 if args.pretty else None, sort_keys=True)
    if args.summary_out:
        args.summary_out.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
