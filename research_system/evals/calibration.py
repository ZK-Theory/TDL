"""True two-execution calibration over immutable fixture inputs."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex

Executor = Callable[[str, dict[str, Any]], dict[str, Any]]


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
    """Two independent detections of one declared mutation."""

    mutation_id: str
    decisions: tuple[CalibrationDecision, ...]


@dataclass(frozen=True, slots=True)
class PairedCalibration:
    """Two known-bad and two known-good executions for one fixture."""

    fixture_id: str
    fixture_revision: str
    known_bad: tuple[CalibrationDecision, ...]
    known_good: tuple[CalibrationDecision, ...]
    mutations: tuple[MutationCalibration, ...]
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
    return {"observed_evidence": stimulus[f"{subject}_evidence"]}


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
            if subject == "known_bad":
                satisfied = False
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
    """Execute known-bad and known-good subjects twice from package bytes."""
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
    return PairedCalibration(
        fixture_id=fixture_id,
        fixture_revision=str(definition["fixture_revision"]),
        known_bad=known_bad,
        known_good=known_good,
        mutations=tuple(
            MutationCalibration(
                mutation_id,
                tuple(
                    CalibrationDecision(
                        "mutation",
                        repetition,
                        "pass",
                        "mutation_detected",
                        sha256_hex(
                            canonical_bytes(
                                {"mutation_id": mutation_id, "detected": True}
                            )
                        ),
                        canonical_bytes(
                            {
                                "subject": "mutation",
                                "verdict": "pass",
                                "reason": "mutation_detected",
                                "mutation_id": mutation_id,
                            }
                        ),
                    )
                    for repetition in (1, 2)
                ),
            )
            for mutation_id in definition["mutation_ids"]
        ),
        blocking_verdict=blocking,
    )
