#!/usr/bin/env python3
"""Reproduce the 2026-07-23 Codex token-efficiency evidence cut.

Reads local JSONL, hashes each byte snapshot, derives usage from monotone
cumulative deltas, and emits structural counts without payload text.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import re
import shutil
import subprocess
from typing import Any

ROOTS = (
    pathlib.Path(r"C:\Users\steph\.codex\sessions"),
    pathlib.Path(r"C:\Users\steph\.codex\archived_sessions"),
)
FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
COMPONENTS = FIELDS[:-1]
UUID_RE = re.compile(r"(019f[0-9a-f-]{32})")
READ_RE = re.compile(r"(?i)(Get-Content|\bgit\s+(show|cat-file|diff)|\brg\b|read_mcp_resource|view_image)")
VALID_RE = re.compile(r"(?i)(pytest|ruff\s+check|pre-commit|validate|check_[\w-]+\.py|diff\s+--check)")
PATH_RE = re.compile(
    r"(?i)(?:(?:docs|research_system|tests|tools|contracts|\.research-system)[\\/][\w.\\/-]+\.(?:md|py|json|ya?ml|txt))"
)
SKILL_RE = re.compile(r"(?i)skills?[\\/]+[\w.-]+[\\/]+SKILL\.md")
OBSERVER_RE = re.compile(r"(?i)research-observer[\\/]+SKILL\.md")

# id | group | role | outcome
SESSION_ROWS = """
019f8954-d0cc-7d12-ae83-e8ccb8b61165|coordinator|coordinator|mixed_multi_subject
019f89d0-7cdb-7163-8f1b-20a8c2e813f6|manager_trial|initial_manager_trial|handback
019f89d3-02e5-7af3-a02c-2f81d742c2bc|manager_trial|initial_trial_acceptance_explorer|analysis_returned
019f89d3-3f90-7af2-9fad-d7500a768562|manager_trial|initial_trial_t2_explorer|analysis_returned
019f89ef-d36c-7720-b416-0823d02326ae|manager_trial|standalone_manager_trial|handback
019f89f2-23d0-7971-baa6-8ce6f8cb12dc|manager_trial|standalone_trial_scope_explorer|analysis_returned
019f89f2-b5fa-7cc3-8c70-1a22b636de94|manager_trial|standalone_trial_seam_explorer|no_substantive_return
019f8a1b-c117-7d22-988b-88e06c0c53b2|stopped_launch|wrong_source_launch_1|stopped_no_deliverable
019f8a29-196a-7a80-ac03-ecc5572fdb5d|stopped_launch|wrong_source_launch_2|stopped_no_deliverable
019f8a2e-61a5-7b40-8b07-adb0d8243dad|wp6_core|t2_author_and_first_remediation|candidate_and_remediation
019f8a30-8444-77a3-af51-3558ab7577b9|wp6_delegated_subtask|author_authority_explorer|analysis_returned
019f8a80-2e64-7633-acbd-f6fb7f12ef9b|wp6_core|first_independent_review|review_report
019f8aa5-af01-7801-95f4-35a1b9959e2b|wp6_delegated_subtask|review_remediation_explorer|analysis_returned
019f8b0f-6fca-72f2-a551-304ff0d5d811|wp6_core|cyber_boundary_review|stopped_no_report
019f8b3e-5a2d-7552-9bd8-dfe7562c93b3|wp6_core|static_second_review|review_report
019f8bb8-b7e5-73b1-bb10-ca30a679cd73|wp6_core|final_remediation_author|candidate
019f8beb-f6f7-7900-b14c-3c7da567ba25|wp6_core|final_independent_review|review_report
019f8c3e-769d-77a3-9b7a-9d2fa1c24d25|efficiency_review|efficiency_plan_review_r1|review_report
019f8c51-a665-7581-ba15-9f00a1496707|efficiency_review|historical_efficiency_review|review_report
019f8c70-ba2f-7a61-9a14-f85d4d00fa0d|efficiency_review|efficiency_plan_v2_review|review_report
019f8c84-6d2a-7782-a8de-352b06e6f382|efficiency_review|efficiency_plan_v2_1_review|review_report
019f8c99-a392-73d0-8138-733d24cbe9ad|audit_current|current_token_evidence_audit|live_lower_bound
""".strip().splitlines()
SESSIONS = {row.split("|")[0]: dict(zip(("group", "role", "outcome"), row.split("|")[1:])) for row in SESSION_ROWS}


def zero() -> dict[str, int]:
    return {field: 0 for field in FIELDS}


def add(target: dict[str, int], source: dict[str, Any]) -> None:
    for field in FIELDS:
        target[field] += int(source.get(field, 0) or 0)


def delta(total: dict[str, Any], previous: dict[str, int]) -> dict[str, int]:
    return {field: int(total.get(field, 0) or 0) - previous[field] for field in FIELDS}


def text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(item.get("text", "") for item in value if isinstance(item, dict))
    return ""


def meaningful(value: str) -> bool:
    value = value.strip()
    return bool(value) and not (
        ("<environment_context>" in value and "<codex_delegation>" not in value)
        or (value.startswith("<recommended_plugins>") and "<codex_delegation>" not in value)
        or value.startswith("# AGENTS.md instructions")
    )


def pct(values: list[int], q: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    return values[max(0, math.ceil(q * len(values)) - 1)]


def serialised_chars(value: Any) -> int:
    return len(value) if isinstance(value, str) else len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def tool_category(call_input: str) -> str:
    if OBSERVER_RE.search(call_input):
        return "research_observer_skill"
    if re.search(r"(?i)skill-observations.*(?:log|principles)", call_input):
        return "observation_records"
    if VALID_RE.search(call_input):
        return "validation"
    if re.search(r"(?i)\bgit\s+(?:show|diff|log|status|ls-tree|cat-file)", call_input):
        return "git_inspection"
    if re.search(r"(?i)Get-Content|read_mcp_resource", call_input):
        return "file_read"
    if re.search(r"(?i)\brg\b|Select-String", call_input):
        return "search"
    return "other"


def dispatch_chars(messages: list[tuple[str, str]]) -> int:
    for _, value in messages:
        if "<codex_delegation>" in value:
            match = re.search(r"<input>(.*)</input>", value, re.DOTALL)
            return len(match.group(1)) if match else len(value)
    return len(messages[0][1]) if messages else 0


def locate() -> tuple[dict[str, pathlib.Path], list[str]]:
    found: dict[str, pathlib.Path] = {}
    duplicates: list[str] = []
    for root in ROOTS:
        for source in root.rglob("rollout-*.jsonl"):
            match = UUID_RE.search(source.name)
            if match and match.group(1) in SESSIONS:
                if match.group(1) in found:
                    duplicates.append(match.group(1))
                found[match.group(1)] = source
    return found, sorted(set(duplicates))


def parse_session(session_id: str, source: pathlib.Path) -> dict[str, Any]:
    snapshot = source.read_bytes()
    records, parse_errors = [], 0
    for line in snapshot.splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            parse_errors += 1

    previous, final, summed_last = zero(), zero(), zero()
    token_records = calls = unchanged = mismatch = negative = 0
    call_events, compact_seq, user_messages, tools = [], [], [], []
    tool_outputs: dict[str, int] = {}
    turn_contexts, patch_seq = [], []
    first_ts = last_ts = ""
    context_compacted = session_meta = base_chars = injected_chars = first_injected = 0

    for seq, record in enumerate(records):
        timestamp = str(record.get("timestamp", ""))
        first_ts, last_ts = first_ts or timestamp, timestamp or last_ts
        kind, payload = record.get("type"), record.get("payload") or {}
        ptype = payload.get("type")
        if kind == "session_meta":
            session_meta += 1
            if not base_chars:
                base_chars = len(str((payload.get("base_instructions") or {}).get("text", "")))
        elif kind == "turn_context":
            turn_contexts.append(payload)
        elif kind == "compacted":
            compact_seq.append(seq)
        elif kind == "event_msg" and ptype == "context_compacted":
            context_compacted += 1
        elif kind == "event_msg" and ptype == "patch_apply_end":
            patch_seq.append(seq)

        if kind == "event_msg" and ptype == "token_count":
            token_records += 1
            info = payload.get("info") or {}
            total, last = info.get("total_token_usage") or {}, info.get("last_token_usage") or {}
            current_delta = delta(total, previous)
            negative += int(any(value < 0 for value in current_delta.values()))
            mismatch += int(any(current_delta[field] != int(last.get(field, 0) or 0) for field in COMPONENTS))
            add(summed_last, last)
            final = {field: int(total.get(field, 0) or 0) for field in FIELDS}
            if any(current_delta[field] > 0 for field in COMPONENTS):
                calls += 1
                call_events.append(
                    {
                        "seq": seq,
                        "timestamp": timestamp,
                        "usage": current_delta,
                        "window": int(info.get("model_context_window", 0) or 0),
                    }
                )
            else:
                unchanged += 1
            previous = final.copy()

        if kind == "response_item" and ptype == "message" and payload.get("role") == "user":
            value = text(payload.get("content"))
            if meaningful(value):
                user_messages.append((timestamp, value))
            else:
                injected_chars += len(value)
                first_injected = first_injected or len(value)

        if kind != "response_item":
            continue
        if ptype == "custom_tool_call":
            tools.append(
                (seq, str(payload.get("call_id", "")), str(payload.get("name", "")), str(payload.get("input", "")))
            )
        elif ptype == "function_call":
            namespace, name = str(payload.get("namespace", "")), str(payload.get("name", ""))
            tools.append(
                (
                    seq,
                    str(payload.get("call_id", "")),
                    f"{namespace}.{name}" if namespace else name,
                    str(payload.get("arguments", "")),
                )
            )
        elif ptype in ("custom_tool_call_output", "function_call_output"):
            tool_outputs[str(payload.get("call_id", ""))] = serialised_chars(payload.get("output"))

    call_keys, read_keys, validation_seqs = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    category_calls, category_chars, path_reads = collections.Counter(), collections.Counter(), collections.Counter()
    sizes, read_calls = [], 0
    skill_reads = skill_chars = observer_reads = observer_chars = validation_calls = 0
    for seq, call_id, name, call_input in tools:
        key, size = (name, " ".join(call_input.split())), int(tool_outputs.get(call_id, 0))
        call_keys[key] += 1
        sizes.append(size)
        category = tool_category(call_input)
        category_calls[category] += 1
        category_chars[category] += size
        if READ_RE.search(call_input):
            read_calls += 1
            read_keys[key] += 1
            normalised = call_input.replace("\\\\", "/").replace("\\", "/")
            for read_path in {match.group(0).lower() for match in PATH_RE.finditer(normalised)}:
                path_reads[read_path] += 1
        if VALID_RE.search(call_input):
            validation_calls += 1
            validation_seqs[key].append(seq)
        if SKILL_RE.search(call_input):
            skill_reads += 1
            skill_chars += size
        if OBSERVER_RE.search(call_input):
            observer_reads += 1
            observer_chars += size

    pairs = []
    for compact in compact_seq:
        before = [event for event in call_events if event["seq"] < compact]
        after = [event for event in call_events if event["seq"] > compact]
        if before and after:
            pre, post = before[-1]["usage"], after[0]["usage"]
            pairs.append(
                {
                    "pre_input": pre["input_tokens"],
                    "post_input": post["input_tokens"],
                    "pre_cached": pre["cached_input_tokens"],
                    "post_cached": post["cached_input_tokens"],
                    "input_drop": pre["input_tokens"] - post["input_tokens"],
                }
            )

    inputs = [event["usage"]["input_tokens"] for event in call_events]
    total_input, cached = final["input_tokens"], final["cached_input_tokens"]
    repeated_paths = [
        {"path": path, "count": count}
        for path, count in sorted(path_reads.items(), key=lambda item: (-item[1], item[0]))
        if count > 1
    ]
    tooling = {
        "calls": len(tools),
        "tool_output_chars": sum(sizes),
        "outputs_ge_20000_chars": sum(size >= 20_000 for size in sizes),
        "outputs_ge_100000_chars": sum(size >= 100_000 for size in sizes),
        "max_output_chars": max(sizes, default=0),
        "exact_duplicate_calls": sum(count - 1 for count in call_keys.values()),
        "read_calls": read_calls,
        "exact_duplicate_reads": sum(count - 1 for count in read_keys.values()),
        "validation_calls": validation_calls,
        "exact_duplicate_validations": sum(max(0, len(seqs) - 1) for seqs in validation_seqs.values()),
        "duplicate_validations_without_patch": sum(
            not any(left < patch < right for patch in patch_seq)
            for seqs in validation_seqs.values()
            for left, right in zip(seqs, seqs[1:])
        ),
        "skill_file_reads": skill_reads,
        "skill_output_chars": skill_chars,
        "research_observer_skill_reads": observer_reads,
        "research_observer_output_chars": observer_chars,
        "distinct_read_paths": len(path_reads),
        "repeated_read_path_accesses": sum(count - 1 for count in path_reads.values()),
        "top_repeated_read_paths": repeated_paths[:10],
        "output_category_calls": dict(sorted(category_calls.items())),
        "output_category_chars": dict(sorted(category_chars.items())),
        "patch_events": len(patch_seq),
    }
    usage = {
        "input_including_cache": total_input,
        "cache_read": cached,
        "uncached_input": total_input - cached,
        "cache_write_input": final["cache_write_input_tokens"],
        "output": final["output_tokens"],
        "reasoning_output_subset": final["reasoning_output_tokens"],
        "processed": final["total_tokens"],
        "cache_share_of_input": cached / total_input if total_input else 0.0,
    }
    return {
        "session_id": session_id,
        **SESSIONS[session_id],
        "path": str(source),
        "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "snapshot_bytes": len(snapshot),
        "first_timestamp": first_ts,
        "cut_timestamp": last_ts,
        "records": len(records),
        "parse_errors": parse_errors,
        "session_meta_records": session_meta,
        "turns": len(turn_contexts),
        "models_efforts": sorted({f"{ctx.get('model', '')}/{ctx.get('effort', '')}" for ctx in turn_contexts}),
        "context_windows": sorted({event["window"] for event in call_events if event["window"]}),
        "token_count_records": token_records,
        "unchanged_token_count_records": unchanged,
        "last_usage_mismatch_records": mismatch,
        "negative_cumulative_deltas": negative,
        "calls": calls,
        "usage": usage,
        "sum_last_minus_final": {field: summed_last[field] - final[field] for field in FIELDS},
        "call_input": {
            "first": inputs[0] if inputs else 0,
            "median": pct(inputs, 0.5),
            "p90": pct(inputs, 0.9),
            "max": max(inputs, default=0),
            "last": inputs[-1] if inputs else 0,
            "calls_ge_80000": sum(value >= 80_000 for value in inputs),
            "calls_ge_200000": sum(value >= 200_000 for value in inputs),
        },
        "compactions": len(compact_seq),
        "context_compacted_events": context_compacted,
        "compaction_pairs": pairs,
        "meaningful_user_messages": len(user_messages),
        "dispatch_chars": dispatch_chars(user_messages),
        "first_base_instruction_chars": base_chars,
        "first_injected_context_chars": first_injected,
        "injected_context_chars": injected_chars,
        "tooling": tooling,
        "_calls": call_events,
        "_messages": user_messages,
    }


def aggregate(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    usage_keys = (
        "input_including_cache",
        "cache_read",
        "uncached_input",
        "cache_write_input",
        "output",
        "reasoning_output_subset",
        "processed",
    )
    tool_keys = (
        "calls",
        "tool_output_chars",
        "outputs_ge_20000_chars",
        "outputs_ge_100000_chars",
        "exact_duplicate_calls",
        "read_calls",
        "exact_duplicate_reads",
        "validation_calls",
        "exact_duplicate_validations",
        "duplicate_validations_without_patch",
        "skill_file_reads",
        "skill_output_chars",
        "research_observer_skill_reads",
        "research_observer_output_chars",
        "distinct_read_paths",
        "repeated_read_path_accesses",
        "patch_events",
    )
    return {
        "group": name,
        "sessions": len(rows),
        "session_ids": [row["session_id"] for row in rows],
        "calls": sum(row["calls"] for row in rows),
        "turns": sum(row["turns"] for row in rows),
        "compactions": sum(row["compactions"] for row in rows),
        "usage": {key: sum(row["usage"][key] for row in rows) for key in usage_keys},
        "tooling": {key: sum(row["tooling"][key] for row in rows) for key in tool_keys},
        "first_call_input_sum": sum(row["call_input"]["first"] for row in rows),
        "dispatch_chars_sum": sum(row["dispatch_chars"] for row in rows),
        "first_base_instruction_chars_sum": sum(row["first_base_instruction_chars"] for row in rows),
        "first_injected_context_chars_sum": sum(row["first_injected_context_chars"] for row in rows),
        "injected_context_chars_sum": sum(row["injected_context_chars"] for row in rows),
    }


def phase_rows(coordinator: dict[str, Any]) -> list[dict[str, Any]]:
    messages, calls = coordinator["_messages"], coordinator["_calls"]
    wp = next(ts for ts, value in messages if "The handback is here:" in value)
    audit = next(ts for ts, value in messages if "If you give me the session ids" in value)
    phases = (
        ("initial_efficiency_design", "", wp),
        ("wp6_coordination", wp, audit),
        ("token_efficiency_audit", audit, "~"),
    )
    result = []
    for name, start, end in phases:
        usage, selected = zero(), [event for event in calls if start <= event["timestamp"] < end]
        for event in selected:
            add(usage, event["usage"])
        result.append(
            {
                "phase": name,
                "start": start or coordinator["first_timestamp"],
                "end": coordinator["cut_timestamp"] if end == "~" else end,
                "calls": len(selected),
                "cache_read": usage["cached_input_tokens"],
                "uncached_input": usage["input_tokens"] - usage["cached_input_tokens"],
                "output": usage["output_tokens"],
                "reasoning_output_subset": usage["reasoning_output_tokens"],
                "processed": usage["total_tokens"],
            }
        )
    return result


def ccusage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    executable = shutil.which("ccusage")
    if not executable:
        return {"available": False}
    args = ["codex", "session", "--json", "--since", "2026-07-18", "--until", "2026-07-23", "--no-cost", "--offline"]
    command = [executable, *args]
    if pathlib.Path(executable).suffix.lower() == ".ps1":
        powershell = shutil.which("powershell")
        if not powershell:
            return {"available": False, "reason": "PowerShell shim cannot be launched"}
        command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", executable, *args]
    payload = json.loads(subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8").stdout)
    indexed = {}
    for entry in payload.get("sessions", []):
        match = UUID_RE.search(str(entry.get("sessionId", "")))
        if match:
            indexed[match.group(1)] = entry
    comparisons = []
    for row in rows:
        entry, raw = indexed.get(row["session_id"]), row["usage"]
        if not entry:
            comparisons.append({"session_id": row["session_id"], "present": False})
            continue
        comparisons.append(
            {
                "session_id": row["session_id"],
                "present": True,
                "cache_read_delta": int(entry.get("cacheReadTokens", 0)) - raw["cache_read"],
                "uncached_input_delta": int(entry.get("inputTokens", 0)) - raw["uncached_input"],
                "output_delta": int(entry.get("outputTokens", 0)) - raw["output"],
                "reasoning_delta": int(entry.get("reasoningOutputTokens", 0)) - raw["reasoning_output_subset"],
                "processed_delta": int(entry.get("totalTokens", 0)) - raw["processed"],
                "ccusage_cache_creation": int(entry.get("cacheCreationTokens", 0)),
                "raw_cache_write": raw["cache_write_input"],
            }
        )
    return {"available": True, "command": "ccusage " + " ".join(args), "comparisons": comparisons}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ccusage", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    located, duplicates = locate()
    missing = sorted(set(SESSIONS) - set(located))
    if missing:
        raise SystemExit("missing session JSONL: " + ", ".join(missing))
    rows = [parse_session(session_id, located[session_id]) for session_id in SESSIONS]
    coordinator = next(row for row in rows if row["group"] == "coordinator")
    phases = phase_rows(coordinator)
    for row in rows:
        row.pop("_calls")
        row.pop("_messages")
    groups = [
        aggregate(group, [row for row in rows if row["group"] == group])
        for group in sorted({row["group"] for row in rows})
    ]
    fresh_groups = {"manager_trial", "stopped_launch", "wp6_core", "wp6_delegated_subtask"}
    selected = [
        aggregate("wp6_all_fresh_tasks", [row for row in rows if row["group"] in fresh_groups]),
        aggregate(
            "no_deliverable_or_no_substantive_return",
            [
                row
                for row in rows
                if row["outcome"] in {"no_substantive_return", "stopped_no_deliverable", "stopped_no_report"}
            ],
        ),
        aggregate(
            "completed_wp6_core_excluding_stopped_review",
            [row for row in rows if row["group"] == "wp6_core" and not row["outcome"].startswith("stopped")],
        ),
    ]
    crosscheck = {"available": False, "skipped": True} if args.skip_ccusage else ccusage(rows)
    checks = {
        "session_count": len(rows),
        "duplicate_ids": duplicates,
        "parse_errors": sum(row["parse_errors"] for row in rows),
        "negative_deltas": sum(row["negative_cumulative_deltas"] for row in rows),
        "processed_identity_failures": sum(
            row["usage"]["processed"] != row["usage"]["input_including_cache"] + row["usage"]["output"] for row in rows
        ),
        "compaction_pair_mismatches": sum(row["compactions"] != len(row["compaction_pairs"]) for row in rows),
        "context_compacted_mismatches": sum(row["compactions"] != row["context_compacted_events"] for row in rows),
    }
    output = {
        "schema": "token-efficiency-audit-evidence-cut/v1",
        "semantics": {
            "processed": "final cumulative input including cache + output",
            "uncached_input": "input_tokens - cached_input_tokens",
            "reasoning_output_subset": "subset of output; never add again",
            "cumulative_rule": "session baselines use final cumulative totals; calls/phases use positive cumulative deltas",
            "cost": "no actual bill in JSONL",
        },
        "checks": checks,
        "sessions": rows,
        "groups": groups,
        "selected_aggregates": selected,
        "coordinator_phases": phases,
        "ccusage": crosscheck,
    }
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
