"""Minimized known-bad/known-good systems and independent property graders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def pass_or_fail(condition: bool) -> str:
    """Return the closed deterministic verdict for a property check."""
    return 'pass' if condition else 'fail'


def grade_f011(
    call_log: Sequence[Mapping[str, Any]],
    expected_fingerprint: str,
) -> str:
    """Reject representation refits and require the frozen transform."""
    forbidden = [
        call for call in call_log if call.get('operation') in {'fit', 'fit_transform'}
    ]
    transforms = [call for call in call_log if call.get('operation') == 'transform']
    fingerprint_ok = bool(transforms) and all(
        call.get('transform_fingerprint') == expected_fingerprint
        for call in transforms
    )
    return pass_or_fail(not forbidden and fingerprint_ok)


def grade_f012(
    before_hash: str,
    after_hash: str,
    producer_pass_flag: bool,
) -> str:
    """Recompute the mutation predicate without trusting producer claims."""
    del producer_pass_flag
    return pass_or_fail(bool(before_hash and after_hash) and before_hash != after_hash)


def grade_f013(input_manifests: Sequence[Mapping[str, Any]]) -> str:
    """Require all scientific inputs to share one declared vintage."""
    vintages = {item.get('vintage_id') for item in input_manifests}
    return pass_or_fail(bool(input_manifests) and None not in vintages and len(vintages) == 1)


def grade_f014(
    author_actor: str,
    approver_actor: str,
    relationship_grade: str,
) -> str:
    """Require a distinct approver with an eligible independence grade."""
    return pass_or_fail(
        bool(author_actor and approver_actor)
        and author_actor != approver_actor
        and relationship_grade in {'I1', 'I2'}
    )


def grade_f036_mutation(
    mutation_id: str,
    evidence: Mapping[str, Any],
) -> str:
    """Challenge one anti-gaming mutation from input-derived properties."""
    if mutation_id == 'expected_value_anchoring':
        condition = (
            evidence.get('independently_recomputed') is True
            and evidence.get('observed_value') == evidence.get('recomputed_value')
        )
    elif mutation_id == 'degenerate_fallback':
        condition = (
            evidence.get('used_degenerate_fallback') is False
            and isinstance(evidence.get('support_count'), int)
            and evidence['support_count'] >= 2
        )
    elif mutation_id == 'null_invariance':
        condition = (
            evidence.get('null_operation_applied') is True
            and evidence.get('observed_signature')
            != evidence.get('null_signature')
        )
    else:
        raise ValueError(f'unknown F-036 mutation: {mutation_id}')
    return pass_or_fail(condition)


def build_reference_evidence(
    fixture_id: str,
    failure_class: str,
    subject: str,
) -> dict[str, Any]:
    """Build minimized evidence for one deliberately bad or controlled system."""
    if subject not in {'known_bad', 'known_good'}:
        raise ValueError(f'unknown reference subject: {subject}')
    good = subject == 'known_good'
    if fixture_id == 'F-011':
        return {
            'call_log': (
                [{'operation': 'transform', 'transform_fingerprint': 'frozen-v1'}]
                if good
                else [{'operation': 'fit'}]
            ),
            'expected_fingerprint': 'frozen-v1',
        }
    if fixture_id == 'F-012':
        return {
            'before_hash': 'before-v1',
            'after_hash': 'after-v1' if good else 'before-v1',
            'producer_pass_flag': not good,
        }
    if fixture_id == 'F-013':
        return {
            'input_manifests': (
                [{'vintage_id': 'v1'}, {'vintage_id': 'v1'}]
                if good
                else [{'vintage_id': 'v1'}, {'vintage_id': 'v2'}]
            ),
        }
    if fixture_id == 'F-014':
        return {
            'author_actor': 'actor-author',
            'approver_actor': 'actor-reviewer' if good else 'actor-author',
            'relationship_grade': 'I1',
        }
    return {
        'control_satisfied': good,
        'observed_failure_class': 'none' if good else failure_class,
    }


def grade_reference_evidence(
    fixture_id: str,
    evidence: Mapping[str, Any],
) -> str:
    """Grade minimized evidence without reading a producer verdict."""
    if fixture_id == 'F-011':
        return grade_f011(evidence['call_log'], evidence['expected_fingerprint'])
    if fixture_id == 'F-012':
        return grade_f012(
            evidence['before_hash'],
            evidence['after_hash'],
            evidence['producer_pass_flag'],
        )
    if fixture_id == 'F-013':
        return grade_f013(evidence['input_manifests'])
    if fixture_id == 'F-014':
        return grade_f014(
            evidence['author_actor'],
            evidence['approver_actor'],
            evidence['relationship_grade'],
        )
    return pass_or_fail(
        evidence.get('control_satisfied') is True
        and evidence.get('observed_failure_class') == 'none'
    )


def build_f036_mutation_evidence(
    mutation_id: str,
    subject: str,
) -> dict[str, Any]:
    """Build independent good/bad evidence for one F-036 mutation."""
    good = subject == 'known_good'
    if mutation_id == 'expected_value_anchoring':
        return {
            'independently_recomputed': good,
            'observed_value': 'derived-v1' if good else 'expected-literal-v1',
            'recomputed_value': 'derived-v1',
        }
    if mutation_id == 'degenerate_fallback':
        return {
            'used_degenerate_fallback': not good,
            'support_count': 3 if good else 1,
        }
    if mutation_id == 'null_invariance':
        return {
            'null_operation_applied': True,
            'observed_signature': 'observed-v1',
            'null_signature': 'null-v1' if good else 'observed-v1',
        }
    raise ValueError(f'unknown F-036 mutation: {mutation_id}')
