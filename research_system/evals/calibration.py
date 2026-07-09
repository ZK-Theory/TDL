"""Two-execution calibration of known-bad/known-good subjects over fixtures.

Every declared mutation and both control subjects are executed twice each from
per-fixture executors (``research_system.evals.executors``) driven from the
stimulus payload only; verdicts are derived by comparing observed evidence
against the committed ``expected/`` package bytes, never fabricated. See
``docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.executors import FixtureExecutor, require_executor

MutationCalibrationStatus = Literal["not_calibrated", "calibrated"]

DETERMINISTIC_REPETITIONS = 2


@dataclass(frozen=True, slots=True)
class CalibrationDecision:
    """One independently executed normalized calibration decision."""

    subject: str
    repetition: int
    verdict: str
    reason: str
    evidence_hash: str
    normalized_bytes: bytes


@dataclass(frozen=True, slots=True)
class MutationCalibration:
    """Two independent detections of one declared mutation, really executed."""

    mutation_id: str
    decisions: tuple[CalibrationDecision, ...]


@dataclass(frozen=True, slots=True)
class PairedCalibration:
    """Two known-bad and two known-good executions for one fixture.

    ``mutations`` holds a real, twice-executed detection for every id in
    ``declared_mutation_ids``; ``mutation_calibration_status`` is
    ``"calibrated"`` once every declared mutation has been executed.
    """

    fixture_id: str
    fixture_revision: str
    known_bad: tuple[CalibrationDecision, ...]
    known_good: tuple[CalibrationDecision, ...]
    mutations: tuple[MutationCalibration, ...]
    declared_mutation_ids: tuple[str, ...]
    mutation_calibration_status: MutationCalibrationStatus
    blocking_verdict: str | None


def _load(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _expected_evidence(root: Path, name: str) -> dict[str, Any]:
    return _load(root / "expected" / name)["assertions"][0]["expected_evidence"]


def _decision(
    subject: str, verdict: str, reason: str, observed: dict[str, Any],
    repetition: int,
) -> CalibrationDecision:
    evidence_hash = sha256_hex(canonical_bytes(observed))
    normalized = canonical_bytes(
        {"subject": subject, "verdict": verdict, "reason": reason,
         "evidence_hash": evidence_hash}
    )
    return CalibrationDecision(
        subject, repetition, verdict, reason, evidence_hash, normalized
    )


def _execute_twice(
    subject: str, payload: dict[str, Any], expected: dict[str, Any],
    execute: FixtureExecutor,
) -> tuple[CalibrationDecision, ...]:
    decisions = []
    for repetition in range(1, DETERMINISTIC_REPETITIONS + 1):
        observed = execute(subject, dict(payload))
        if observed == expected:
            verdict = "fail" if subject == "known_bad" else "pass"
            reason = (
                "intended_failure" if subject == "known_bad"
                else "control_satisfied"
            )
        else:
            verdict, reason = "fixture_error", "unexpected_calibration_outcome"
        decisions.append(_decision(subject, verdict, reason, observed, repetition))
    return tuple(decisions)


def _execute_mutation(
    mutation_id: str, payload: dict[str, Any],
    pre_expected: dict[str, Any], post_expected: dict[str, Any],
    execute: FixtureExecutor,
) -> MutationCalibration:
    decisions = []
    for repetition in range(1, DETERMINISTIC_REPETITIONS + 1):
        observed = execute(
            "known_bad",
            {**payload, "producer_passed": True, "mutation_id": mutation_id},
        )
        detected = observed == pre_expected and observed != post_expected
        verdict = "pass" if detected else "fixture_error"
        reason = "mutation_detected" if detected else "mutation_undetected"
        decisions.append(_decision("mutation", verdict, reason, observed, repetition))
    return MutationCalibration(mutation_id, tuple(decisions))


def calibrate_fixture(
    fixture_id: str, *, fixture_root: Path | str,
    execute: FixtureExecutor | None = None,
) -> PairedCalibration:
    """Execute known-bad, known-good, and every declared mutation twice.

    A known-bad execution that reproduces the authored pre-control evidence is
    the intended failure (``verdict="fail"``, ``reason="intended_failure"``),
    never ``fixture_error`` (review m-4).
    """
    root = Path(fixture_root) / fixture_id
    definition = _load(root / "fixture.yaml")
    payload = dict(_load(root / "input" / "stimulus.json")["payload"])
    pre_expected = _expected_evidence(root, "pre-control.json")
    post_expected = _expected_evidence(root, "post-control.json")
    executor = execute if execute is not None else require_executor(fixture_id)
    known_bad = _execute_twice("known_bad", payload, pre_expected, executor)
    known_good = _execute_twice("known_good", payload, post_expected, executor)
    mutations = tuple(
        _execute_mutation(
            mutation_id, payload, pre_expected, post_expected, executor
        )
        for mutation_id in definition["mutation_ids"]
    )
    live_classes = {
        row["grader_class"] for row in definition["required_graders"]
    }.intersection({"M", "H"})
    blocking = "unable_to_grade" if live_classes else None
    error_decisions = (
        *known_bad, *known_good,
        *(item for mutation in mutations for item in mutation.decisions),
    )
    if any(item.verdict == "fixture_error" for item in error_decisions):
        blocking = "fixture_error"
    return PairedCalibration(
        fixture_id=fixture_id,
        fixture_revision=str(definition["fixture_revision"]),
        known_bad=known_bad,
        known_good=known_good,
        mutations=mutations,
        declared_mutation_ids=tuple(definition["mutation_ids"]),
        mutation_calibration_status="calibrated",
        blocking_verdict=blocking,
    )
