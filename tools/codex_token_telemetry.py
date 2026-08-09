"""Audit Codex JSONL token telemetry from monotone cumulative counters.

``last_token_usage`` is diagnostic only: records can repeat it without advancing
``total_token_usage``. Usage is therefore derived from cumulative deltas. An
explicit sequence boundary can exclude inherited fork history while retaining
the last pre-boundary cumulative snapshot as the local baseline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
COMPONENT_FIELDS = FIELDS[:-1]


def _usage(value: Any) -> dict[str, int | None] | None:
    if not isinstance(value, dict) or not any(field in value for field in FIELDS):
        return None
    result = {field: int(value.get(field, 0) or 0) if field in value else None for field in FIELDS}
    if int(result.get("total_tokens") or 0) > 0 and all(int(result.get(field) or 0) == 0 for field in COMPONENT_FIELDS):
        for field in COMPONENT_FIELDS:
            result[field] = None
    return result


def token_snapshot(record: dict[str, Any]) -> tuple[dict[str, int | None], dict[str, int | None] | None] | None:
    payload = record.get("payload") or {}
    if record.get("type") != "event_msg" or payload.get("type") != "token_count":
        return None
    info = payload.get("info") or {}
    total = _usage(info.get("total_token_usage"))
    if total is None:
        return None
    return total, _usage(info.get("last_token_usage"))


def _delta(
    current: dict[str, int | None],
    previous: dict[str, int | None],
) -> tuple[dict[str, int | None], bool]:
    comparable = [field for field in FIELDS if current.get(field) is not None and previous.get(field) is not None]
    reset = any(int(current[field] or 0) < int(previous[field] or 0) for field in comparable)
    delta: dict[str, int | None] = {}
    for field in FIELDS:
        value = current.get(field)
        if value is None:
            delta[field] = None
        elif reset or previous.get(field) is None:
            delta[field] = int(value)
        else:
            delta[field] = int(value) - int(previous[field] or 0)
    return delta, reset


def _positive(delta: dict[str, int | None]) -> bool:
    return any(int(delta.get(field) or 0) > 0 for field in ("input_tokens", "output_tokens", "total_tokens"))


def audit_records(records: Iterable[dict[str, Any]], *, boundary_seq: int = 0) -> dict[str, Any]:
    """Return child-local additive usage and telemetry-consistency warnings."""
    if boundary_seq < 0:
        raise ValueError("boundary_seq must be non-negative")
    usage = {field: 0 for field in FIELDS}
    previous: dict[str, int | None] | None = {field: 0 for field in FIELDS} if boundary_seq == 0 else None
    warnings: list[dict[str, Any]] = []
    token_records = 0
    local_token_records = 0
    repeated_last_records = 0
    reset_records = 0

    for seq, record in enumerate(records):
        snapshot = token_snapshot(record)
        if snapshot is None:
            continue
        token_records += 1
        current, last = snapshot
        if seq < boundary_seq:
            previous = current
            continue
        local_token_records += 1
        if previous is None:
            warnings.append(
                {
                    "seq": seq,
                    "code": "missing_pre_boundary_baseline",
                    "detail": "first local cumulative snapshot was retained as a baseline, not counted",
                }
            )
            previous = current
            continue

        delta, reset = _delta(current, previous)
        if reset:
            reset_records += 1
            warnings.append({"seq": seq, "code": "cumulative_counter_reset"})
        if _positive(delta):
            for field in FIELDS:
                if delta[field] is not None:
                    usage[field] += max(0, int(delta[field] or 0))
            if last is not None:
                mismatches = [
                    field
                    for field in FIELDS
                    if delta.get(field) is not None
                    and last.get(field) is not None
                    and int(delta[field] or 0) != int(last[field] or 0)
                ]
                if mismatches:
                    warnings.append(
                        {
                            "seq": seq,
                            "code": "last_usage_differs_from_cumulative_delta",
                            "fields": mismatches,
                        }
                    )
        elif last is not None and any(int(last.get(field) or 0) > 0 for field in FIELDS):
            repeated_last_records += 1
            component_total = sum(int(last.get(field) or 0) for field in COMPONENT_FIELDS)
            warnings.append(
                {
                    "seq": seq,
                    "code": (
                        "bookkeeping_last_total_without_cumulative_advance"
                        if component_total == 0 and int(last.get("total_tokens") or 0) > 0
                        else "repeated_last_usage_without_cumulative_advance"
                    ),
                }
            )
        previous = current

    return {
        "usage": usage,
        "token_records": token_records,
        "local_token_records": local_token_records,
        "repeated_last_records": repeated_last_records,
        "counter_reset_records": reset_records,
        "boundary_seq": boundary_seq,
        "warnings": warnings,
        "semantics": {
            "additive_source": "positive deltas of total_token_usage",
            "last_token_usage": "diagnostic only; never summed",
            "cache_write": "reported from raw cumulative cache_write_input_tokens deltas",
        },
    }


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    malformed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(value, dict):
            records.append(value)
        else:
            malformed += 1
    return records, malformed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--boundary-seq", type=int, default=0)
    args = parser.parse_args(argv)
    records, malformed = load_jsonl(args.jsonl)
    result = audit_records(records, boundary_seq=args.boundary_seq)
    result["malformed_records"] = malformed
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if malformed else 0


if __name__ == "__main__":
    raise SystemExit(main())
