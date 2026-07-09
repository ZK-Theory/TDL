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

# Catalogue members deferred out of P0 with an explicit rationale (05-plan
# §4.4). Kept exhaustive so every non-selected, non-Gate-5 catalogue case has a
# recorded omission reason (acceptance item 1).
P0_DEFERRED = frozenset(
    {
        "F-006", "F-015", "F-016", "F-017", "F-018", "F-019",
        "F-023", "F-024", "F-029", "F-030", "F-037", "F-038",
        "S-005", "S-007",
    }
)

# Gate 5 capability cases, deferred with capability restrictions (05-plan §4.4).
GATE5_DEFERRED = frozenset({"S-014", "S-015", "S-016"})


@dataclass(frozen=True, slots=True)
class DeferredCapability:
    """One capability that remains disabled until Gate 5."""

    fixture_id: str
    capability: str
    reason: str
    status: str
    required_before: str


@dataclass(frozen=True, slots=True)
class DeferredCatalogueCase:
    """One catalogue case deferred out of P0 with a recorded rationale."""

    fixture_id: str
    reason: str
    plan_ref: str


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
    omitted_p0: tuple[DeferredCatalogueCase, ...]
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
    if payload.get("transport") != "fake":
        raise FixtureDefinitionError("P0 requires deterministic fake transport")

    keys: list[ResultKey] = []
    fixture_root = Path(fixture_root)
    for fixture_id, revision in selected.items():
        definition_path = fixture_root / fixture_id / "fixture.yaml"
        declared = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
        if str(declared.get("fixture_revision")) != str(revision):
            raise FixtureDefinitionError(
                f"coverage pins {fixture_id}@{revision} but the package declares "
                f"{declared.get('fixture_revision')}"
            )
    # Enforce the exhaustive-catalogue claim: every staged fixture directory on
    # disk must be accounted for by an active, deferred, or Gate 5 catalogue set.
    catalogue = P0_CASES | P0_DEFERRED | GATE5_DEFERRED
    staged = {
        path.name
        for path in fixture_root.iterdir()
        if path.is_dir() and (path / "fixture.yaml").is_file()
    }
    orphans = sorted(staged - catalogue)
    if orphans:
        raise FixtureDefinitionError(
            f"fixture directories absent from the catalogue: {orphans}"
        )
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

    omitted_rows = payload.get("omitted_gate5")
    coverage_revision = payload.get("coverage_revision")
    if not isinstance(omitted_rows, list) or not isinstance(coverage_revision, str):
        raise FixtureDefinitionError(
            "coverage_revision and omitted_gate5 must be well-formed"
        )
    try:
        omitted = tuple(DeferredCapability(**row) for row in omitted_rows)
    except (TypeError, KeyError) as exc:
        raise FixtureDefinitionError("invalid omitted_gate5 row") from exc
    if {item.fixture_id for item in omitted} != set(GATE5_DEFERRED):
        raise FixtureDefinitionError("exact Gate 5 deferrals required")
    if any(
        item.status != "capability_disabled" or item.required_before != "gate5"
        for item in omitted
    ):
        raise FixtureDefinitionError("Gate 5 capabilities must remain disabled")

    deferred_rows = payload.get("omitted_p0")
    if not isinstance(deferred_rows, list):
        raise FixtureDefinitionError("omitted_p0 must be a list")
    try:
        deferred = tuple(DeferredCatalogueCase(**row) for row in deferred_rows)
    except (TypeError, KeyError) as exc:
        raise FixtureDefinitionError("invalid omitted_p0 row") from exc
    if {item.fixture_id for item in deferred} != set(P0_DEFERRED):
        raise FixtureDefinitionError(
            "omitted_p0 must explain every deferred catalogue case exactly"
        )
    if any(not item.reason or not item.plan_ref for item in deferred):
        raise FixtureDefinitionError("omitted_p0 rows require reason and plan_ref")
    if payload.get("gate5_authorized") is not False:
        raise FixtureDefinitionError("Gate 5 must remain unauthorized")
    if tuple(payload.get("scenarios", ())) != ("A", "B", "C", "D", "E"):
        raise FixtureDefinitionError("exact scenarios A-E required")
    return P0Coverage(
        coverage_revision=coverage_revision,
        transport="fake",
        selected_fixture_revisions=tuple(sorted(selected.items())),
        required_result_keys=tuple(keys),
        accepted_grader_classes=("D", "O", "P", "R", "T"),
        unavailable_grader_classes=("H", "M"),
        omitted_gate5=tuple(sorted(omitted, key=lambda item: item.fixture_id)),
        omitted_p0=tuple(sorted(deferred, key=lambda item: item.fixture_id)),
        scenarios=("A", "B", "C", "D", "E"),
        gate5_authorized=False,
    )
