"""Provider-neutral immutable context-template accounting validation."""

from research_system.errors import ArsError

_ALLOWED_SEGMENT_BUCKETS = frozenset({"managed", "reserved"})


def validate_wrapper_accounting(accounting: dict) -> None:
    required = {
        "method",
        "raw_capacity",
        "fixed_overhead",
        "managed_tokens",
        "reserved_variable_tokens",
        "segments",
    }
    if set(accounting) != required:
        raise ArsError("wrapper_accounting_incomplete")
    segments = accounting["segments"]
    if (
        not isinstance(segments, dict)
        or not segments
        or any(bucket not in _ALLOWED_SEGMENT_BUCKETS for bucket in segments.values())
    ):
        raise ArsError("wrapper_accounting_incomplete")
    numeric = (
        accounting["raw_capacity"],
        accounting["fixed_overhead"],
        accounting["managed_tokens"],
        accounting["reserved_variable_tokens"],
    )
    if any(not isinstance(value, int) or value < 0 for value in numeric):
        raise ArsError("wrapper_accounting_incomplete")
    if sum(numeric[1:]) > numeric[0]:
        raise ArsError("wrapper_capacity_exceeded")
