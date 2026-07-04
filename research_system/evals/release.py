"""Exact required-grader closure and non-compensable release logic."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from research_system.evals.errors import UnableToGrade
from research_system.evals.graders import validate_grader_result
from research_system.evals.models import GraderResult, ResultKey

BLOCKING = frozenset({"fail", "unable_to_grade", "fixture_error"})


def _expected(
    coverage: object,
    attribute: str,
    key: ResultKey,
) -> Any:
    return getattr(coverage, attribute)[key]


def _incompatibility(
    coverage: object,
    result: GraderResult,
) -> str | None:
    key = result.result_key
    mapping_bindings = (
        "expected_subject_hashes",
        "expected_trace_hashes",
        "expected_oracle_hashes",
        "expected_policy_hashes",
        "expected_threshold_policy_hashes",
        "required_independence",
        "required_criticality",
    )
    missing_bindings = [
        attribute
        for attribute in mapping_bindings
        if key not in getattr(coverage, attribute, {})
    ]
    if missing_bindings:
        return "coverage bindings missing: " + ",".join(missing_bindings)
    if result.critical != _expected(coverage, "required_criticality", key):
        return "criticality mismatch"
    if not result.required:
        return "required result not marked required"
    try:
        validate_grader_result(
            result,
            expected_subject_hash=_expected(
                coverage,
                "expected_subject_hashes",
                key,
            ),
            expected_trace_hash=_expected(
                coverage,
                "expected_trace_hashes",
                key,
            ),
            expected_oracle_hash=_expected(
                coverage,
                "expected_oracle_hashes",
                key,
            ),
            expected_policy_hash=_expected(
                coverage,
                "expected_policy_hashes",
                key,
            ),
            expected_threshold_policy_hash=_expected(
                coverage,
                "expected_threshold_policy_hashes",
                key,
            ),
            required_independence=_expected(
                coverage,
                "required_independence",
                key,
            ),
        )
    except UnableToGrade as exc:
        return str(exc)
    return None


def decide_release(
    coverage: object,
    results: Iterable[GraderResult],
) -> dict[str, Any]:
    """Decide only after exact result-key closure and immutable compatibility."""
    required_keys = tuple(coverage.required_result_keys)
    required = set(required_keys)
    result_list = tuple(results)
    observed_keys = [result.result_key for result in result_list]
    counts = Counter(observed_keys)
    observed = set(observed_keys)

    missing = [key for key in dict.fromkeys(required_keys) if key not in observed]
    unexpected = sorted(observed - required)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    if len(required) != len(required_keys):
        duplicates.extend(
            key for key, count in Counter(required_keys).items() if count != 1
        )
        duplicates = sorted(set(duplicates))

    incompatible = []
    for result in result_list:
        if result.result_key not in required or counts[result.result_key] != 1:
            continue
        reason = _incompatibility(coverage, result)
        if reason is not None:
            incompatible.append((result.result_key, reason))

    blocking = [
        result
        for result in result_list
        if result.result_key in required
        and result.required
        and result.verdict in BLOCKING
    ]
    response: dict[str, Any] = {
        "decision": "blocked",
        "missing": missing,
        "unexpected": unexpected,
        "duplicates": duplicates,
        "incompatible": incompatible,
        "blocking": blocking,
    }
    if missing or unexpected or duplicates or incompatible:
        return response
    if blocking:
        response["decision"] = (
            "blocked"
            if any(
                result.verdict in {"unable_to_grade", "fixture_error"}
                for result in blocking
            )
            else "fail"
        )
        return response
    response["decision"] = "pass"
    return response
