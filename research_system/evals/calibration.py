"""Two-execution calibration of known-bad/known-good subjects over fixtures.

Scope (interim, review C-2/m-4): this module executes the known-bad and
known-good subjects twice each and derives their verdicts. It does **not** yet
execute declared mutations — those are recorded as ``not_calibrated`` and this
module never fabricates mutation detection. Real per-fixture execution (both the
mutation path and replacement of the placeholder default executor) lands in the
WP4.8 verdict-derivation tranche; see
``docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from research_system.canonical import canonical_bytes, sha256_hex

Executor = Callable[[str, dict[str, Any]], dict[str, Any]]
MutationCalibrationStatus = Literal["not_calibrated", "calibrated"]


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
    """Two independent detections of one declared mutation.

    Typed placeholder for the WP4.8 mutation-execution rework; no instance is
    produced on the interim path, which never fabricates mutation detection.
    """

    mutation_id: str
    decisions: tuple[CalibrationDecision, ...]


@dataclass(frozen=True, slots=True)
class PairedCalibration:
    """Two known-bad and two known-good executions for one fixture.

    ``mutations`` is empty and ``mutation_calibration_status`` is
    ``"not_calibrated"`` until the WP4.8 rework executes declared mutations;
    ``declared_mutation_ids`` records what remains to be calibrated so no
    consumer reads ``blocking_verdict is None`` as "mutations were checked".
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


def _default_execute(subject: str, stimulus: dict[str, Any]) -> dict[str, Any]:
    # Placeholder executor: satisfaction tracks the subject label, so the
    # known-bad/known-good shape is exercised but not independently falsified.
    # WP4.8 replaces this with per-fixture executors driven from the stimulus
    # payload only (review C-1); do not treat its output as a grader verdict.
    return {"property_satisfied": subject == "known_good"}


def _execute_twice(
    subject: str,
    stimulus: dict[str, Any],
    execute: Executor,
) -> tuple[CalibrationDecision, ...]:
    decisions = []
    for repetition in (1, 2):
        evidence = execute(subject, stimulus)
        expected = subject == "known_good"
        if "property_satisfied" in evidence:
            satisfied = evidence["property_satisfied"] is True
        else:
            satisfied = evidence.get("observed_evidence") == stimulus.get(
                f"{subject}_evidence"
            )
        if satisfied == expected:
            verdict = "pass" if expected else "fail"
            reason = "control_satisfied" if expected else "intended_failure"
        else:
            verdict = "fixture_error"
            reason = "unexpected_calibration_outcome"
        evidence_hash = sha256_hex(canonical_bytes(evidence))
        normalized = canonical_bytes(
            {
                "subject": subject,
                "verdict": verdict,
                "reason": reason,
                "evidence_hash": evidence_hash,
            }
        )
        decisions.append(
            CalibrationDecision(
                subject,
                repetition,
                verdict,
                reason,
                evidence_hash,
                normalized,
            )
        )
    return tuple(decisions)


def calibrate_fixture(
    fixture_id: str,
    *,
    fixture_root: Path | str,
    execute: Executor = _default_execute,
) -> PairedCalibration:
    """Execute known-bad and known-good subjects twice from package bytes.

    Declared mutations are not executed here; the returned
    ``PairedCalibration`` reports them as ``not_calibrated`` (review C-2).
    """
    root = Path(fixture_root) / fixture_id
    definition = _load(root / "fixture.yaml")
    stimulus = _load(root / "input" / "stimulus.json")
    stimulus = {
        **stimulus,
        "known_bad_evidence": _load(root / "expected" / "pre-control.json")[
            "assertions"
        ][0]["expected_evidence"],
        "known_good_evidence": _load(root / "expected" / "post-control.json")[
            "assertions"
        ][0]["expected_evidence"],
    }
    live_classes = {
        row["grader_class"] for row in definition["required_graders"]
    }.intersection({"M", "H"})
    known_bad = _execute_twice("known_bad", stimulus, execute)
    known_good = _execute_twice("known_good", stimulus, execute)
    blocking = "unable_to_grade" if live_classes else None
    if any(
        item.verdict == "fixture_error" for item in (*known_bad, *known_good)
    ):
        blocking = "fixture_error"
    # Declared mutations are recorded but NOT executed on the interim path;
    # emitting detection here would fabricate the exact evidence the fixture
    # programme exists to catch (review C-2). Real mutation execution and
    # detection land in WP4.8.
    return PairedCalibration(
        fixture_id=fixture_id,
        fixture_revision=str(definition["fixture_revision"]),
        known_bad=known_bad,
        known_good=known_good,
        mutations=(),
        declared_mutation_ids=tuple(definition["mutation_ids"]),
        mutation_calibration_status="not_calibrated",
        blocking_verdict=blocking,
    )
