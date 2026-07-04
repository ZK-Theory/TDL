"""Immutable-binding checks shared by deterministic and judgment graders."""

from research_system.evals.errors import UnableToGrade
from research_system.evals.models import GraderResult


def validate_grader_result(
    result: GraderResult,
    *,
    expected_subject_hash: str,
    expected_trace_hash: str,
    expected_oracle_hash: str,
    expected_policy_hash: str,
    expected_threshold_policy_hash: str,
    required_independence: str,
) -> None:
    """Fail closed when a grader is stale, unbound, or not independent."""
    if not result.required:
        raise UnableToGrade('required grader result is not marked required')
    hash_bindings = {
        'subject': (result.subject_hash, expected_subject_hash),
        'trace': (result.trace_hash, expected_trace_hash),
        'oracle': (result.oracle_hash, expected_oracle_hash),
        'policy': (result.policy_hash, expected_policy_hash),
    }
    mismatches = [
        label
        for label, (observed, expected) in hash_bindings.items()
        if not observed or observed != expected
    ]
    if mismatches:
        raise UnableToGrade('incompatible hashes: ' + ','.join(mismatches))
    if (
        not result.threshold_policy_hash
        or result.threshold_policy_hash != expected_threshold_policy_hash
    ):
        raise UnableToGrade('missing or stale threshold policy')
    if result.context_relationship != required_independence:
        raise UnableToGrade('required independence relationship unavailable')
    if (
        required_independence == 'deterministic_independent'
        and not result.independently_recomputed
    ):
        raise UnableToGrade('independent recomputation unavailable')
    if (
        required_independence.startswith('cross_family')
        and result.producer_family == result.grader_family
    ):
        raise UnableToGrade('cross-family independence unavailable')
