"""Exact P0 fixture closure and Gate 5 capability restrictions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.fixture_package import validate_fixture_package
from research_system.evals.models import ResultKey

P0_CASES = frozenset(
    {
        "F-001", "F-002", "F-003", "F-004", "F-005",
        "F-007", "F-008", "F-009", "F-010", "F-011", "F-012", "F-013",
        "F-014", "F-020", "F-021", "F-022", "F-025", "F-026", "F-027",
        "F-028", "F-031", "F-032", "F-033", "F-034", "F-035", "F-036",
        "S-001", "S-002", "S-003", "S-004", "S-006", "S-008", "S-009",
        "S-010", "S-011", "S-012", "S-013",
    }
)


@dataclass(frozen=True, slots=True)
class DeferredCapability:
    """One capability that remains disabled until Gate 5."""

    fixture_id: str
    capability: str
    reason: str
    status: str
    required_before: str


@dataclass(frozen=True, slots=True)
class P0Coverage:
    """Validated exact fixture, grader, scenario, and deferral closure."""

    coverage_revision: str
    transport: str
    selected_fixture_revisions: tuple[tuple[str, str], ...]
    required_result_keys: tuple[ResultKey, ...]
    accepted_grader_classes: tuple[str, ...]
    unavailable_grader_classes: tuple[str, ...]
    omitted_gate5: tuple[DeferredCapability, ...]
    scenarios: tuple[str, ...]
    gate5_authorized: bool


def _yaml(path: Path) -> dict:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FixtureDefinitionError(f"invalid coverage YAML: {path}") from exc
    if not isinstance(value, dict):
        raise FixtureDefinitionError("coverage must be an object")
    return value


def load_p0_coverage(
    path: Path | str,
    *,
    fixture_root: Path | str,
    schema_root: Path | str,
) -> P0Coverage:
    """Load the exact P0 closure and validate every selected package."""
    payload = _yaml(Path(path))
    selected = payload.get("selected_fixture_revisions")
    if not isinstance(selected, dict) or set(selected) != P0_CASES:
        raise FixtureDefinitionError("coverage must select exact P0_CASES")
    if set(selected.values()) != {"r1"}:
        raise FixtureDefinitionError("P0 fixture revisions must be r1")
    if payload.get("transport") != "fake":
        raise FixtureDefinitionError("P0 requires deterministic fake transport")

    keys: list[ResultKey] = []
    fixture_root = Path(fixture_root)
    for fixture_id in sorted(P0_CASES):
        validated = validate_fixture_package(
            fixture_root / fixture_id,
            schema_root=schema_root,
        )
        definition = _yaml(fixture_root / fixture_id / "fixture.yaml")
        if validated.fixture_revision != selected[fixture_id]:
            raise FixtureDefinitionError(f"coverage revision mismatch: {fixture_id}")
        keys.extend(
            (
                fixture_id,
                validated.fixture_revision,
                grader["grader_id"],
                grader["grader_class"],
                grader["grader_version"],
            )
            for grader in definition["required_graders"]
        )
    if len(keys) != len(set(keys)):
        raise FixtureDefinitionError("duplicate required result key")

    omitted = tuple(DeferredCapability(**row) for row in payload["omitted_gate5"])
    if {item.fixture_id for item in omitted} != {"S-014", "S-015", "S-016"}:
        raise FixtureDefinitionError("exact Gate 5 deferrals required")
    if any(
        item.status != "capability_disabled" or item.required_before != "gate5"
        for item in omitted
    ):
        raise FixtureDefinitionError("Gate 5 capabilities must remain disabled")
    if payload.get("gate5_authorized") is not False:
        raise FixtureDefinitionError("Gate 5 must remain unauthorized")
    if tuple(payload.get("scenarios", ())) != ("A", "B", "C", "D", "E"):
        raise FixtureDefinitionError("exact scenarios A-E required")
    return P0Coverage(
        coverage_revision=str(payload["coverage_revision"]),
        transport="fake",
        selected_fixture_revisions=tuple(sorted(selected.items())),
        required_result_keys=tuple(keys),
        accepted_grader_classes=("D", "O", "P", "R", "T"),
        unavailable_grader_classes=("H", "M"),
        omitted_gate5=tuple(sorted(omitted, key=lambda item: item.fixture_id)),
        scenarios=("A", "B", "C", "D", "E"),
        gate5_authorized=False,
    )
