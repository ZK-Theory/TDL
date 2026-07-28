# Research context: docs/plans/agentic-research-system/handoffs/26-research-system-suite-red-briefing.md
# Purpose: Bound the redundant work in the fixture-validation path, so an N+1
# regression fails a test instead of surfacing as an apparent hang (obs 133).

from __future__ import annotations

from pathlib import Path

import pytest

from research_system import schema_registry as schema_registry_module
from research_system.evals.coverage import FOUNDATION_CASES, load_p0_coverage
from research_system.schema_registry import SchemaRegistry

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
FIXTURES = EVALS / "fixtures"
SCHEMAS = ROOT / ".research-system" / "schemas"
COVERAGE = EVALS / "p0-coverage.yaml"

# One construction per distinct schema root. Deliberately not "<= 40": the point
# is that the count must not scale with the number of fixtures at all.
MAX_REGISTRY_CONSTRUCTIONS = 1


@pytest.fixture
def construction_count(monkeypatch):
    """Count real ``SchemaRegistry`` constructions, cache misses included.

    The registry cache is process-global, so a prior test can leave it warm and
    make this budget look satisfied when nothing was measured. Clearing it first
    makes the count reflect this call alone.
    """
    schema_registry_module._registry_for_resolved_root.cache_clear()

    calls = {"n": 0}
    original = SchemaRegistry.__init__

    def counting_init(self, root):
        calls["n"] += 1
        original(self, root)

    monkeypatch.setattr(SchemaRegistry, "__init__", counting_init)
    return calls


def test_coverage_load_does_not_rebuild_the_registry_per_fixture(construction_count):
    """A registry rebuild per fixture is the N+1 that made this suite unrunnable.

    Constructing a registry meta-validates all 270 schema files (~3.4s) and
    discards the ``referencing`` resolver cache, so every ``$ref`` and
    ``$dynamicRef`` in the fixture documents is re-resolved from scratch. Done
    once per fixture across the foundation set, that turned a single test into
    a 35-minute call that looked like a hang.

    This asserts the shape of the work rather than its duration: wall-clock
    budgets are flaky on a shared machine, while a construction count is
    deterministic, fast, and names the defect exactly.
    """
    load_p0_coverage(COVERAGE, fixture_root=FIXTURES, schema_root=SCHEMAS)

    assert construction_count["n"] <= MAX_REGISTRY_CONSTRUCTIONS, (
        f"{construction_count['n']} SchemaRegistry constructions for "
        f"{len(FOUNDATION_CASES)} fixtures; expected at most "
        f"{MAX_REGISTRY_CONSTRUCTIONS}. A per-fixture rebuild has returned."
    )


def test_the_budget_would_notice_a_per_fixture_rebuild():
    """Negative control: prove the budget is not vacuously satisfiable.

    If the counted quantity could never exceed the threshold -- because the
    fixture set is empty, or because the count is measured somewhere the work
    does not happen -- the test above would pass while enforcing nothing.
    """
    assert (
        len(FOUNDATION_CASES) > MAX_REGISTRY_CONSTRUCTIONS
    ), "the foundation set must be larger than the budget, or a per-fixture rebuild could not push the count over it"
