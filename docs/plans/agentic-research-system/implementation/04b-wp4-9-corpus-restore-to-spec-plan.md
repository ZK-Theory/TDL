# ARS P0 Work Package 4.9: Corpus Restore-to-Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the fixture corpus to its accepted specification — F-036's 06b identity with three named, executed mutations (review M-1 / 04a obligation O7), and the three missing policy/variant registry files with load-bearing bindings (review M-2 / 04a obligation O8: `threshold-policies.yaml`, `p0-calibration-policy.yaml`, `p0-variant-matrix.yaml`, F-021's `mandatory_closure_sizing` variant) — closing findings M-1 and M-2 of `reviews/adversarial-wp4-full-review-2026-07-07.md` and clearing the F-036 `fixture_error` quarantine.

**Architecture:** The corpus stays materializer-generated: each change edits the shard `Case` tables in `tools/ars/materialize_*` and regenerates the affected package deterministically (byte-identical `--check` for all unchanged packages). F-036 is re-authored so its oracle is coherent with an honest derivation (the WP4.8 anti-anchoring rule stands: the executor derives from the stimulus payload only; this tranche fixes the *oracle*, then extends `execute_f036` to the restored identity in the same task so every commit is green). The three registry YAMLs become load-bearing via `research_system/evals/policies.py` checks wired into `run_p0_coverage`, and a new deterministic generator emits the variant matrix with recomputable sizing evidence.

**Tech Stack:** Python 3.13.5, PyYAML, pytest, existing `tools/ars/fixture_materializer.py` shard framework, `research_system.evals` (calibration/harness/coverage/fixture_package), `research_system.canonical.sha256_hex`.

**Owner authorization:** Direction locked by USER 2026-07-07/08 ("restore-to-spec") — recorded in PR #69's deferral note and 04a obligations O7/O8. This plan is the owner-gated corpus tranche those obligations name.

## Global Constraints

- Branch `pipe/ars-p0-corpus-restore-to-spec` from `main` (main already contains PR #69 and PR #70); one WP4 PR open at a time; review-then-merge (CodeRabbit review completes **before** merge; merge with `gh pr merge`, never a local FF-push).
- Isolated worktree under `.apm/worktrees/`; immediately `Copy-Item "c:\Users\steph\TDL\.env" "<worktree>\.env"` after `git worktree add`.
- Commit subjects use `[PIPELINE] P00:` with the Co-Authored-By trailer; multi-line messages via BOM-free file + `git commit -F` (`[IO.File]::WriteAllText` with `UTF8Encoding($false)`); never `--no-verify`.
- **Anti-anchoring rule (binding, inherited from 04a):** executors derive observed evidence from the stimulus `payload` only and are never bent to match an incoherent oracle. This tranche re-authors the F-036 *oracle* to be derivable, then extends the executor — in that order, inside one task, with the calibration tests proving coherence.
- **The aggregate P0 candidate decision remains `blocked`** (M/H grader authority unavailable). `eval calibrate` must still report `blocked_fixture_count: 14` and `eval run` must still report `candidate_status: "blocked"` after every task. Any change to either number is a stop condition.
- Do not modify `research_system/evals/executors/` **except** `execute_f036` in `adapter_scientific.py` (Task 2). Do not modify `calibration.py` semantics (Task 1 only extracts the repetition constant), `harness.py` verdict derivation (Task 1 only inserts policy checks), `cli.py`, `scenarios.py`, `retention_authorizer.py`, or any `.research-system/schemas/**`.
- F-012's seed `20260707` is untouched. `omitted_p0` (PR #69) is untouched.
- Materializer regeneration: run every shard with `--check` after any regeneration; unchanged packages must be byte-identical. Fixture files are `eol=lf` — do not hand-edit package files; only the materializers write them.
- Quality gates for every task: `uv run ruff check research_system tools/ars tests/research_system` and `uv run pytest tests/research_system -q --no-cov` (use `uv run --no-sync` if the local venv sync is still blocked by long-running processes).

---

## File map

**Create:**

```text
.research-system/evals/threshold-policies.yaml
.research-system/evals/p0-calibration-policy.yaml
.research-system/evals/p0-variant-matrix.yaml            (generated, committed)
research_system/evals/policies.py
tools/ars/materialize_p0_variant_matrix.py
tests/research_system/unit/test_policies.py
tests/research_system/unit/test_variant_matrix.py
```

**Modify:**

```text
tools/ars/materialize_adapter_scientific_fixtures.py   (Case fields; F-036 re-authored)
tools/ars/materialize_context_routing_fixtures.py      (Case fields; F-021 sizing rows)
.research-system/evals/fixtures/F-036/**               (regenerated at r2)
.research-system/evals/fixtures/F-021/**               (regenerated at r2)
.research-system/evals/p0-coverage.yaml                (F-036: r2, F-021: r2)
research_system/evals/coverage.py                      (revision check: per-package equality, not global r1)
research_system/evals/calibration.py                   (extract DETERMINISTIC_REPETITIONS constant only)
research_system/evals/harness.py                       (insert policy bindings in run_p0_coverage)
research_system/evals/executors/adapter_scientific.py  (execute_f036 for the restored identity)
tests/research_system/unit/test_executors.py           (quarantine set -> empty)
tests/research_system/unit/test_calibration.py         (F-036 three-mutation calibration)
tests/research_system/integration/test_release_coordinator.py      (F-036 rows: unable_to_grade, not fixture_error)
tests/research_system/integration/test_adapter_scientific_fixture_corpus.py  (F-036 identity assertions)
docs/plans/agentic-research-system/implementation/04a-...plan.md   (O7/O8 dispositions -> delivered, Task 4)
```

## Obligation register (writing-plans-extras)

| # | Source | Obligation | Owner | Disposition |
|---|---|---|---|---|
| R1 | 06b §2 row F-036 | F-036 identity: lanes `topology, stochastic, representation, claim`; provenance `domain_coverage / synthetic`; three calibrated mutations (expected-value anchoring, degenerate/constant fallback, null-operation invariance); producer flags ignored | WP4.9 | Task 2 |
| R2 | 06b §4 item 4 | each mutation calibrated so the uncontrolled path plausibly passes superficial checks and the controlled path rejects it | WP4.9 | Task 2 (calibration's detection rule `observed == pre and observed != post`, executed twice per mutation) |
| R3 | 06b authority clause ("reserve the IDs without rewriting any existing fixture identity") | identity restoration is a package change → `fixture_revision` bumps to `r2`; coverage pins the new revision explicitly | WP4.9 | Task 2 (and Task 3 for F-021) |
| R4 | 04-plan Task 4 (§571) | `p0-calibration-policy.yaml` with the exact eleven-key content | WP4.9 | Task 1 — content verbatim; runtime cross-check against the engine constant |
| R5 | 04-plan Task 4 | `threshold-policies.yaml`; every fixture's `threshold_policy_ids` resolve | WP4.9 | Task 1 — closure enforced in `run_p0_coverage` |
| R6 | 04-plan Task 4 (§586) | `p0-variant-matrix.yaml` with explicit rows, never wildcards; per-shard binding tuples | WP4.9 | Task 3 — generated + committed + recomputable |
| R7 | P-028 / 04-plan §4.2, §805 | F-021 stays P1 but its `mandatory_closure_sizing` variant runs at P0; sizing matrix records reference count plus exact/evaluated provider-token evidence | WP4.9 | Task 3 — two provider-specific sizing rows (see R12), token evidence recomputed by test |
| R8 | 04-plan §586 (claude/codex adapter and rendering variants) | **executing** the fake-claude/fake-codex variant rows (variant-aware harness runs) | Delivered by WP5.2 | All 46 exact `execution_stage: gate5` rows bind selected fixture revisions and execute twice through injected fake-only paths with equal normalized-decision hashes. Their 170 six-part result keys close alongside the 132 baseline keys for exact 302-result release evidence. |
| R9 | 04-plan Task 4 (`tools/ars/materialize_p0_fixtures.py` single materializer) | single-file materializer named by the plan | accepted deviation | The three-shard structure was accepted by the 2026-07-04 review and retained; not restored. |
| R10 | 04a register O7/O8 | mark O7 and O8 delivered once this tranche merges | WP4.9 | Task 4 edits the 04a register rows |
| R11 | 05-plan / 04a Global Constraints | aggregate P0 decision stays `blocked` | WP4.9 | Global Constraint + Task 4 smoke (`blocked_fixture_count: 14`, `candidate_status: "blocked"`) |
| R12 | 04-plan Task 4 test (`fixture.variant == 'mandatory_closure_sizing'`) | a single `variant` scalar on F-021 | **USER flag in PR** | Delivered as two provider-specific binding rows (`mandatory_closure_sizing-fake-claude-count-v1`, `...-fake-codex-count-v1`) because the accepted no-wildcard rule (`fixture_package.py:231-241`) forbids one provider-spanning row. Deviation stated verbatim in the PR body for owner confirmation. |

## Research Assurance Requirements

- **Assurance lanes touched:** Output/Provenance (primary); Topology/Stochastic/Representation only as the control boundary F-036 encodes.
- **Governing decisions/contracts:** 06b §2/§4; 04-plan Task 4; 05-plan §7.3; review dispositions M-1/M-2; 04a obligations O7/O8; anti-anchoring rule (04a Global Constraints).
- **Parameters and seeds:** no new stochastic operations; F-012 seed `20260707` unchanged. Fake token-counter divisors (4 for `fake-claude-count-v1`, 3 for `fake-codex-count-v1`) are *definitions of fake provider revisions*, recorded in the generator and in the matrix rows.
- **Machine-checkable claims → enforcement artifacts:**
  - "every fixture's threshold policy resolves" → closure check in `run_p0_coverage` + `test_policies.py::test_every_p0_fixture_threshold_policy_resolves`;
  - "calibration policy matches the engine" → `require_calibration_policy` cross-check + mismatch test;
  - "F-036's three mutations are executed and detected" → `test_calibration.py::test_f036_three_named_mutations_detected` (each mutation, both repetitions, `reason="mutation_detected"`);
  - "the quarantine set is empty" → `test_executors.py` full-corpus calibration asserts **no** fixture yields `fixture_error`;
  - "the matrix is recomputable, not authored" → `--check` regeneration test + token-evidence recomputation test;
  - "no wildcard variant rows" → existing `fixture_package.py` check plus `test_variant_matrix.py` matrix-level scan;
  - "aggregate stays blocked" → Task 4 smoke assertions.
- **Human-review-only claims:** whether the re-authored F-036 scenario faithfully realizes 06b's three incident classes — reviewer checks Task 2's Case against 06b §2 row F-036 (quoted in Task 2).
- **Partial criteria:** if the restored F-036 oracle still cannot be honestly derived (calibration `fixture_error` after Task 2), stop and report Partial — never weaken the executor comparison. If any unchanged package fails `--check` byte-identity after regeneration, stop (materializer determinism broken).

---

## Task 1: Threshold and calibration policy files with runtime binding

**Files:**
- Create: `.research-system/evals/threshold-policies.yaml`, `.research-system/evals/p0-calibration-policy.yaml`, `research_system/evals/policies.py`
- Modify: `research_system/evals/calibration.py` (constant extraction), `research_system/evals/harness.py` (`run_p0_coverage` policy binding)
- Test: `tests/research_system/unit/test_policies.py` (new)

**Interfaces:**
- Consumes: `research_system.evals.errors.FixtureDefinitionError`; `research_system.errors.ConfigurationError`; `load_typed_definition` (from `fixture_package`, added in WP4.8 Task 4) whose `FixtureDefinition` carries the `threshold_policy_ids` tuple from `fixture.yaml`.
- Produces: `load_threshold_policies(path: Path | str) -> dict[str, dict]` (policy_id → row); `require_calibration_policy(path: Path | str) -> dict` (validated payload). Task 4's smoke and later tranches rely on these exact names.

- [ ] **Step 1: Write the failing tests**

Create `tests/research_system/unit/test_policies.py`:

```python
from pathlib import Path

import pytest

from research_system.errors import ConfigurationError
from research_system.evals.policies import (
    load_threshold_policies,
    require_calibration_policy,
)

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"


def test_threshold_policies_define_exact_property_v1():
    policies = load_threshold_policies(EVALS / "threshold-policies.yaml")
    row = policies["exact-property-v1"]
    assert row["comparison"] == "byte_identical_normalized_decision"
    assert set(row["grader_classes"]) == {"D", "T", "R", "O", "P"}
    assert row["model_threshold"] is None and row["human_threshold"] is None


def test_every_p0_fixture_threshold_policy_resolves():
    from research_system.evals.coverage import P0_CASES
    from research_system.evals.fixture_package import load_typed_definition

    policies = load_threshold_policies(EVALS / "threshold-policies.yaml")
    for fixture_id in sorted(P0_CASES):
        definition = load_typed_definition(EVALS / "fixtures" / fixture_id)
        missing = set(definition.threshold_policy_ids) - set(policies)
        assert not missing, f"{fixture_id} references undefined policies {missing}"


def test_calibration_policy_matches_engine():
    payload = require_calibration_policy(EVALS / "p0-calibration-policy.yaml")
    from research_system.evals.calibration import DETERMINISTIC_REPETITIONS

    assert payload["deterministic_repetitions"] == DETERMINISTIC_REPETITIONS


def test_calibration_policy_mismatch_is_configuration_error(tmp_path):
    bad = tmp_path / "p0-calibration-policy.yaml"
    bad.write_text(
        (EVALS / "p0-calibration-policy.yaml")
        .read_text(encoding="utf-8")
        .replace("deterministic_repetitions: 2", "deterministic_repetitions: 1"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError):
        require_calibration_policy(bad)


def test_empty_threshold_registry_loads_as_empty(tmp_path):
    bad = tmp_path / "threshold-policies.yaml"
    bad.write_text("schema_version: '1.0.0'\npolicies: []\n", encoding="utf-8")
    policies = load_threshold_policies(bad)
    assert policies == {}
    # The closure check itself lives in run_p0_coverage (Step 6): an empty
    # registry makes every fixture's threshold_policy_ids unresolvable there.
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_policies.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: research_system.evals.policies` (and the two YAML files absent).

- [ ] **Step 3: Create the two policy files**

`.research-system/evals/p0-calibration-policy.yaml` — **verbatim from 04-plan §571, no edits:**

```yaml
schema_version: '1.0.0'
policy_revision: p0-calibration-v1
deterministic_repetitions: 2
identical_input_requirement: byte_identical_normalized_decision
known_bad_requirement: intended_failure_in_every_repetition
known_good_requirement: intended_pass_in_every_repetition
declared_mutation_requirement: detected_in_every_repetition
stochastic_policy_missing: fixture_error
model_or_human_threshold_policy_missing: unable_to_grade
live_provider_calibration_enabled: false
```

`.research-system/evals/threshold-policies.yaml`:

```yaml
schema_version: '1.0.0'
registry_revision: p0-threshold-v1
policies:
  - threshold_policy_id: exact-property-v1
    comparison: byte_identical_normalized_decision
    grader_classes: [D, T, R, O, P]
    model_threshold: null
    human_threshold: null
    notes: >-
      Deterministic exact-match on normalized calibration decisions. M/H
      thresholds are deliberately absent in P0: a required M/H grader without
      a threshold policy yields unable_to_grade (blocking), per
      p0-calibration-policy.yaml model_or_human_threshold_policy_missing.
```

- [ ] **Step 4: Implement `research_system/evals/policies.py`**

```python
"""Load-bearing threshold and calibration policy registries (review M-2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_system.errors import ConfigurationError

_REQUIRED_CALIBRATION = {
    "schema_version": "1.0.0",
    "policy_revision": "p0-calibration-v1",
    "deterministic_repetitions": 2,
    "identical_input_requirement": "byte_identical_normalized_decision",
    "known_bad_requirement": "intended_failure_in_every_repetition",
    "known_good_requirement": "intended_pass_in_every_repetition",
    "declared_mutation_requirement": "detected_in_every_repetition",
    "stochastic_policy_missing": "fixture_error",
    "model_or_human_threshold_policy_missing": "unable_to_grade",
    "live_provider_calibration_enabled": False,
}


def _yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"cannot load policy file: {path}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError(f"policy file must be a mapping: {path}")
    return payload


def load_threshold_policies(path: Path | str) -> dict[str, dict[str, Any]]:
    """Load the threshold-policy registry keyed by threshold_policy_id.

    Args:
        path: Location of ``threshold-policies.yaml``.

    Returns:
        Mapping of policy id to its full row.

    Raises:
        ConfigurationError: If the file is malformed or ids collide.
    """
    payload = _yaml(Path(path))
    rows = payload.get("policies")
    if not isinstance(rows, list):
        raise ConfigurationError("threshold policies must be a list")
    registry: dict[str, dict[str, Any]] = {}
    for row in rows:
        policy_id = row.get("threshold_policy_id")
        if not isinstance(policy_id, str) or policy_id in registry:
            raise ConfigurationError(f"invalid or duplicate threshold policy: {policy_id!r}")
        registry[policy_id] = dict(row)
    return registry


def require_calibration_policy(path: Path | str) -> dict[str, Any]:
    """Load the calibration policy and reject any drift from the engine.

    Args:
        path: Location of ``p0-calibration-policy.yaml``.

    Returns:
        The validated policy payload.

    Raises:
        ConfigurationError: If any required key is missing or differs from the
            accepted 04-plan §571 values (fail-closed: the file cannot silently
            authorize weaker calibration than the engine performs).
    """
    payload = _yaml(Path(path))
    if payload != _REQUIRED_CALIBRATION:
        drift = {
            key: (payload.get(key), value)
            for key, value in _REQUIRED_CALIBRATION.items()
            if payload.get(key) != value
        } or {key: (payload[key], None) for key in payload.keys() - _REQUIRED_CALIBRATION.keys()}
        raise ConfigurationError(f"calibration policy drift: {drift}")
    return payload
```

- [ ] **Step 5: Extract the repetition constant in `calibration.py`**

At module level (near `FixtureExecutor`), add:

```python
DETERMINISTIC_REPETITIONS = 2
```

Replace both `for repetition in (1, 2):` loops (`_execute_twice`, `_execute_mutation`) with:

```python
    for repetition in range(1, DETERMINISTIC_REPETITIONS + 1):
```

No other calibration change.

- [ ] **Step 6: Bind both policies in `harness.run_p0_coverage`**

In `research_system/evals/harness.py`, immediately after the `coverage = load_p0_coverage(...)` call (currently ending at line 76) and the `root = Path(fixture_root)` line, insert:

```python
    threshold_policies = load_threshold_policies(root.parent / "threshold-policies.yaml")
    require_calibration_policy(root.parent / "p0-calibration-policy.yaml")
```

Inside the per-fixture loop, immediately after the typed definition for the fixture is loaded (the `load_typed_definition` call added by WP4.8 Task 4), insert:

```python
        missing_policies = set(definition.threshold_policy_ids) - set(threshold_policies)
        if missing_policies:
            raise FixtureDefinitionError(
                f"{fixture_id} references undefined threshold policies: {sorted(missing_policies)}"
            )
```

Add the import at the top: `from research_system.evals.policies import load_threshold_policies, require_calibration_policy`. (If the loop binds the definition under a different local name, adapt the variable name only — the check itself is exactly as above.)

- [ ] **Step 7: Run tests and full gates**

Run: `uv run pytest tests/research_system/unit/test_policies.py tests/research_system/unit/test_calibration.py tests/research_system/integration/test_eval_cli.py -q --no-cov`
Expected: PASS.
Run: `uv run ruff check research_system tools/ars tests/research_system` then `uv run pytest tests/research_system -q --no-cov`
Expected: clean; all tests pass (count grows by the 5 new policy tests).

- [ ] **Step 8: Commit**

Subject: `[PIPELINE] P00: bind ARS threshold and calibration policies` (BOM-free message file, `git commit -F`).

---

## Task 2: F-036 restored to its 06b identity, with an honest executor and quarantine clearance

**The governing 06b §2 row F-036 (restated for the reviewer):** priority P0; lanes `topology, stochastic, representation, claim`; provenance `domain_coverage / synthetic`. Scenario: "Three calibrated mutations are presented: an approximate sanity value is used as a target, a plausible constant/identity fallback replaces the real computation, and a null operation leaves the tested object invariant. Producer-emitted flags claim success." Post-control: "Independent graders derive or challenge the expected value, exercise the real computation and forced fallback, and recompute tested-object identity before/after the null operation. Each mutation fails its property/claim gate, producer flags are ignored." Graders D,T,R,M.

**Files:**
- Modify: `tools/ars/materialize_adapter_scientific_fixtures.py` (Case dataclass + F-036 case), `research_system/evals/executors/adapter_scientific.py` (`execute_f036`), `research_system/evals/coverage.py` (revision check), `.research-system/evals/p0-coverage.yaml` (F-036 → r2)
- Regenerate: `.research-system/evals/fixtures/F-036/**`
- Test: `tests/research_system/unit/test_calibration.py`, `tests/research_system/unit/test_executors.py`, `tests/research_system/integration/test_release_coordinator.py`, `tests/research_system/integration/test_adapter_scientific_fixture_corpus.py`

**Interfaces:**
- Consumes: calibration's mutation-detection rule (`calibration.py:122`): a mutation is detected iff the mutated known-bad execution reproduces the authored pre-control evidence and differs from post-control, in both repetitions.
- Produces: F-036 package at `fixture_revision: r2` with `mutation_ids: ["expected_value_anchoring", "degenerate_constant_fallback", "null_operation_invariance"]`; full-corpus quarantine set becomes **empty**.

- [ ] **Step 1: Write the failing calibration test**

Append to `tests/research_system/unit/test_calibration.py`:

```python
def test_f036_three_named_mutations_detected():
    record = calibrate_fixture("F-036", fixture_root=FIXTURES)
    assert record.fixture_revision == "r2"
    assert record.declared_mutation_ids == (
        "expected_value_anchoring",
        "degenerate_constant_fallback",
        "null_operation_invariance",
    )
    for mutation in record.mutations:
        assert [item.reason for item in mutation.decisions] == ["mutation_detected"] * 2
    # F-036 has a required M grader, so it stays blocked -- but honestly:
    assert record.blocking_verdict == "unable_to_grade"
```

Run: `uv run pytest tests/research_system/unit/test_calibration.py::test_f036_three_named_mutations_detected -q --no-cov`
Expected: FAIL — current package declares one generic mutation at r1 and calibrates `fixture_error`.

- [ ] **Step 2: Extend the shard `Case` dataclass**

In `tools/ars/materialize_adapter_scientific_fixtures.py`, add two defaulted fields to `Case` (after `risk_tier`):

```python
    fixture_revision: str = "r1"
    mutation_ids: tuple[str, ...] | None = None
```

In `_package`, change the `common` line (currently line 331) to:

```python
    common = {"schema_version": "1.0.0", "fixture_id": case_id, "fixture_revision": case.fixture_revision}
```

and the `mutation_ids` line (currently line 436) to:

```python
        "mutation_ids": list(case.mutation_ids) if case.mutation_ids else [f"{case.contract}-violation"],
```

- [ ] **Step 3: Re-author the F-036 case**

Replace the entire `"F-036": Case(...)` entry (lines 247–259) with:

```python
    "F-036": Case(
        "Proof-obligation anti-gaming",
        "proof_obligation_recomputation",
        "trusted_mutation_claim",
        ("topology", "stochastic", "representation", "claim"),
        {
            "operation": "grade_proof_obligation",
            "values": [2.0, 4.0, 6.0, 8.0],
            "statistic": "mean",
            "producer_reported_value": 5.2,
            "anchor_target": 5.2,
            "fallback_constant": 0.0,
            "object_hash_before_null_op": "tested-object-v1",
            "object_hash_after_null_op": "tested-object-v1",
            "producer_mutation_detected": True,
        },
        {
            "expected_value_recomputed": False,
            "anchoring_detected": False,
            "degenerate_fallback_detected": False,
            "null_invariance_detected": False,
            "producer_flag_trusted": True,
        },
        {
            "expected_value_recomputed": True,
            "anchoring_detected": True,
            "degenerate_fallback_detected": True,
            "null_invariance_detected": True,
            "producer_flag_trusted": False,
        },
        ("ExpectedValueRecomputed", "MutationRecomputed"),
        ("ProducerMutationFlagTrusted",),
        ("D", "T", "R", "M"),
        "domain_coverage",
        "synthetic",
        risk_tier="R3",
        fixture_revision="r2",
        mutation_ids=(
            "expected_value_anchoring",
            "degenerate_constant_fallback",
            "null_operation_invariance",
        ),
    ),
```

Derivability check (the reviewer verifies this arithmetic): the honest recomputed mean of `[2.0, 4.0, 6.0, 8.0]` is `5.0`; the producer-reported `5.2` equals the anchor target, so anchoring is detected (`5.2 != 5.0`); the fallback constant `0.0 != 5.0` detects the degenerate fallback; equal object hashes before/after the null operation detect null invariance. Every post-control value is derivable from the stimulus payload alone. Producer flags appear only in the payload, never in the derivation.

- [ ] **Step 4: Rewrite `execute_f036`**

Replace `execute_f036` in `research_system/evals/executors/adapter_scientific.py` (lines 180–191) with:

```python
def execute_f036(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        # Uncontrolled path: the producer flag is trusted for every presented
        # mutation -- the trusted_mutation_claim failure class itself.
        return {
            "expected_value_recomputed": False,
            "anchoring_detected": False,
            "degenerate_fallback_detected": False,
            "null_invariance_detected": False,
            "producer_flag_trusted": True,
        }
    recomputed = sum(action["values"]) / len(action["values"])
    return {
        "expected_value_recomputed": True,
        "anchoring_detected": action["producer_reported_value"] != recomputed,
        "degenerate_fallback_detected": action["fallback_constant"] != recomputed,
        "null_invariance_detected": (
            action["object_hash_before_null_op"] == action["object_hash_after_null_op"]
        ),
        "producer_flag_trusted": False,
    }
```

(The `mutation_id` injected by `_execute_mutation` rides on the known-bad path: each named mutation goes undetected by the uncontrolled path — observed equals pre-control — which is exactly calibration's detection rule. The controlled path derives all three detections from the payload arithmetic; `producer_mutation_detected` is never read.)

- [ ] **Step 5: Relax the coverage revision pin to per-package equality**

In `research_system/evals/coverage.py`, replace lines 97–98:

```python
    if set(selected.values()) != {"r1"}:
        raise FixtureDefinitionError("P0 fixture revisions must be r1")
```

with:

```python
    for fixture_id, revision in selected.items():
        definition_path = Path(fixture_root) / fixture_id / "fixture.yaml"
        declared = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
        if str(declared.get("fixture_revision")) != str(revision):
            raise FixtureDefinitionError(
                f"coverage pins {fixture_id}@{revision} but the package declares "
                f"{declared.get('fixture_revision')}"
            )
```

(Move this block after the existing `fixture_root = Path(fixture_root)` line if needed so `fixture_root` is a `Path`; `yaml` is already imported in `coverage.py` — if not, add it.) In `.research-system/evals/p0-coverage.yaml`, change `F-036: r1` to `F-036: r2` under `selected_fixture_revisions`.

- [ ] **Step 6: Regenerate the F-036 package**

```powershell
Remove-Item -Recurse -Force .research-system\evals\fixtures\F-036
uv run python tools/ars/materialize_adapter_scientific_fixtures.py --root .research-system/evals/fixtures
uv run python tools/ars/materialize_adapter_scientific_fixtures.py --root .research-system/evals/fixtures --check
uv run python tools/ars/materialize_control_store_fixtures.py --root .research-system/evals/fixtures --check
uv run python tools/ars/materialize_context_routing_fixtures.py --root .research-system/evals/fixtures --check
```

Expected: F-036 regenerated at r2; **all three `--check` runs report byte-identical** (only F-036 changed, and it matches its own regeneration).

- [ ] **Step 7: Update the tests that encoded the quarantine**

- `tests/research_system/unit/test_executors.py:109`: `expected_errors = {"F-036"}` → `expected_errors = set()` (rename the test to `test_full_corpus_calibration_has_no_fixture_errors` if its name mentions the quarantine).
- `tests/research_system/unit/test_executors.py:81` region: the F-036 calibration assertion changes from `fixture_error` to `unable_to_grade` (M grader present, mutations detected) — mirror Step 1's test.
- `tests/research_system/integration/test_release_coordinator.py:42`: replace `assert "fixture_error" in by_fixture["F-036"]` with:

```python
    assert "fixture_error" not in by_fixture["F-036"]
    assert "unable_to_grade" in by_fixture["F-036"]
```

- `tests/research_system/integration/test_adapter_scientific_fixture_corpus.py:65`: the old `CASES["F-036"].post["mutation_detected"] is True` assertion no longer type-checks; replace with the restored-identity assertions:

```python
    case = CASES["F-036"]
    assert case.lanes == ("topology", "stochastic", "representation", "claim")
    assert case.incident_basis == "domain_coverage"
    assert case.mutation_ids == (
        "expected_value_anchoring",
        "degenerate_constant_fallback",
        "null_operation_invariance",
    )
    assert case.post["anchoring_detected"] is True
```

- Sweep for stale revision pins: `grep -rn '"F-036", "r1"\|F-036.*r1' tests/research_system/` and update any hit to `r2`.

- [ ] **Step 8: Run the full gates**

Run: `uv run pytest tests/research_system -q --no-cov` and `uv run ruff check research_system tools/ars tests/research_system`
Expected: all pass. Then the invariant smoke:

```powershell
uv run python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
```

Expected JSON: `fixture_count: 37`, `blocked_fixture_count: 14`, `fixtures_with_uncalibrated_mutations: 0`, `mutation_calibration: "calibrated"`. (14 is unchanged: F-036 moves from `fixture_error` to `unable_to_grade`, still blocked by its M grader.)

- [ ] **Step 9: Commit**

Subject: `[PIPELINE] P00: restore F-036 to its 06b identity with three executed mutations`

---

## Task 3: Variant matrix, fake counting revisions, and F-021 sizing binding

**Files:**
- Create: `tools/ars/materialize_p0_variant_matrix.py`, `.research-system/evals/p0-variant-matrix.yaml` (generated), `tests/research_system/unit/test_variant_matrix.py`
- Modify: `tools/ars/materialize_context_routing_fixtures.py` (Case fields + F-021), `.research-system/evals/p0-coverage.yaml` (F-021 → r2)
- Regenerate: `.research-system/evals/fixtures/F-021/**`

**Interfaces:**
- Consumes: package bytes on disk (stimulus/pre/post JSON) — the matrix is *derived*, never hand-authored; `fixture_package.py`'s no-wildcard rule for package `variant_bindings`.
- Produces: `p0-variant-matrix.yaml` rows `{fixture_id, fixture_revision, variant_id, provider_variant, runtime_variant, os, transport, operational_profile, execution_stage}` (+ sizing fields on counting rows: `reference_count, exact_tokens, evaluated_tokens`); generator CLI with `--check`.

- [ ] **Step 1: Write the failing tests**

Create `tests/research_system/unit/test_variant_matrix.py`:

```python
import math
from pathlib import Path

import yaml

from research_system.evals.coverage import P0_CASES

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
WILDCARDS = {"*", "any", "wildcard", ""}


def _matrix():
    return yaml.safe_load((EVALS / "p0-variant-matrix.yaml").read_text(encoding="utf-8"))


def test_every_p0_case_has_exactly_one_executed_p0_row_plus_f021_sizing():
    rows = _matrix()["rows"]
    p0_rows = {}
    for row in rows:
        if row["execution_stage"] == "p0":
            p0_rows.setdefault(row["fixture_id"], []).append(row)
    assert set(p0_rows) == P0_CASES
    for fixture_id, fixture_rows in p0_rows.items():
        expected = 3 if fixture_id == "F-021" else 1
        assert len(fixture_rows) == expected, fixture_id


def test_no_wildcard_rows_and_complete_tuples():
    for row in _matrix()["rows"]:
        for field in ("variant_id", "provider_variant", "runtime_variant", "os", "transport"):
            assert str(row[field]).lower() not in WILDCARDS, row


def test_f021_sizing_rows_record_recomputable_token_evidence():
    stimulus = (EVALS / "fixtures" / "F-021" / "input" / "stimulus.json").read_bytes()
    evaluated_bytes = stimulus + b"".join(
        (EVALS / "fixtures" / "F-021" / "expected" / name).read_bytes()
        for name in ("pre-control.json", "post-control.json")
    )
    divisors = {"fake-claude-count-v1": 4, "fake-codex-count-v1": 3}
    rows = [
        row for row in _matrix()["rows"]
        if row["fixture_id"] == "F-021" and row["variant_id"].startswith("mandatory_closure_sizing")
    ]
    assert len(rows) == 2 and all(row["execution_stage"] == "p0" for row in rows)
    for row in rows:
        divisor = divisors[row["provider_variant"]]
        assert row["exact_tokens"] == math.ceil(len(stimulus) / divisor)
        assert row["evaluated_tokens"] == math.ceil(len(evaluated_bytes) / divisor)
        assert row["reference_count"] >= 1


def test_adapter_cases_register_claude_and_codex_gate5_rows():
    rows = _matrix()["rows"]
    adapter_ids = {"F-007", "F-008", "F-009", "F-010", "F-011", "F-012", "F-013",
                   "F-014", "F-020", "F-032", "F-034", "F-036", "S-003", "S-004", "S-013"}
    for fixture_id in adapter_ids:
        providers = {
            row["provider_variant"] for row in rows
            if row["fixture_id"] == fixture_id and row["execution_stage"] == "gate5"
        }
        assert providers == {"fake-claude-adapter-v1", "fake-codex-adapter-v1"}, fixture_id


def test_package_bindings_are_matrix_rows():
    import json

    matrix_ids = {
        (row["fixture_id"], row["variant_id"]) for row in _matrix()["rows"]
    }
    for fixture_id in sorted(P0_CASES):
        manifest = json.loads(
            (EVALS / "fixtures" / fixture_id / "input" / "source-manifest.json").read_text(encoding="utf-8")
        )
        for binding in manifest["variant_bindings"]:
            assert (fixture_id, binding["variant_id"]) in matrix_ids, (fixture_id, binding["variant_id"])
```

Run: `uv run pytest tests/research_system/unit/test_variant_matrix.py -q --no-cov`
Expected: FAIL — matrix file absent.

- [ ] **Step 2: Implement the generator**

Create `tools/ars/materialize_p0_variant_matrix.py`:

```python
"""Derive the explicit P0 variant matrix from the committed fixture packages.

Rows are recomputed from package bytes -- never hand-authored -- so the matrix
is load-bearing evidence (review M-2). Fake counting/adapter revisions are
*definitions*: fake-claude-count-v1 counts ceil(bytes/4), fake-codex-count-v1
counts ceil(bytes/3).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CONTROL_STORE = (
    "F-001", "F-002", "F-003", "F-004", "F-005",
    "S-001", "S-002", "S-006", "S-008", "S-009", "S-010", "S-011", "S-012",
)
CONTEXT_ROUTING = (
    "F-021", "F-022", "F-025", "F-026", "F-027", "F-028", "F-031", "F-033", "F-035",
)
ADAPTER_SCIENTIFIC = (
    "F-007", "F-008", "F-009", "F-010", "F-011", "F-012", "F-013", "F-014",
    "F-020", "F-032", "F-034", "F-036", "S-003", "S-004", "S-013",
)
OPERATIONAL_PROFILES = {
    "S-003": "long_running", "S-004": "long_running",
    "S-013": "trivial", "F-034": "trivial",
}
COUNTERS = {"fake-claude-count-v1": 4, "fake-codex-count-v1": 3}


def _revision(root: Path, fixture_id: str) -> str:
    definition = yaml.safe_load((root / fixture_id / "fixture.yaml").read_text(encoding="utf-8"))
    return str(definition["fixture_revision"])


def _executed_row(root: Path, fixture_id: str, profile: str) -> dict:
    return {
        "fixture_id": fixture_id,
        "fixture_revision": _revision(root, fixture_id),
        "variant_id": "python313-windows-in-process",
        "provider_variant": "provider-neutral",
        "runtime_variant": "python-3.13",
        "os": "windows",
        "transport": "in_process_fake",
        "operational_profile": profile,
        "execution_stage": "p0",
    }


def _gate5_adapter_rows(root: Path, fixture_id: str, profile: str) -> list[dict]:
    return [
        {
            "fixture_id": fixture_id,
            "fixture_revision": _revision(root, fixture_id),
            "variant_id": f"{provider}-windows-fake-transport",
            "provider_variant": provider,
            "runtime_variant": "python-3.13",
            "os": "windows",
            "transport": "fake",
            "operational_profile": profile,
            "execution_stage": "gate5",
        }
        for provider in ("fake-claude-adapter-v1", "fake-codex-adapter-v1")
    ]


def _sizing_rows(root: Path, fixture_id: str, stage: str) -> list[dict]:
    package = root / fixture_id
    stimulus = (package / "input" / "stimulus.json").read_bytes()
    evaluated = stimulus + b"".join(
        (package / "expected" / name).read_bytes()
        for name in ("pre-control.json", "post-control.json")
    )
    manifest = json.loads((package / "input" / "source-manifest.json").read_text(encoding="utf-8"))
    payload = json.loads(stimulus)["payload"]
    reference_count = len(manifest["authoritative_refs"]) + (
        1 if "governing_amendment" in payload.get("action", {}) else 0
    )
    return [
        {
            "fixture_id": fixture_id,
            "fixture_revision": _revision(root, fixture_id),
            "variant_id": f"mandatory_closure_sizing-{counter}",
            "provider_variant": counter,
            "runtime_variant": "python-3.13",
            "os": "windows",
            "transport": "in_process_fake",
            "operational_profile": "bounded",
            "execution_stage": stage,
            "reference_count": reference_count,
            "exact_tokens": math.ceil(len(stimulus) / divisor),
            "evaluated_tokens": math.ceil(len(evaluated) / divisor),
        }
        for counter, divisor in COUNTERS.items()
    ]


def build_matrix(root: Path) -> dict:
    rows: list[dict] = []
    for fixture_id in CONTROL_STORE:
        rows.append(_executed_row(root, fixture_id, "bounded"))
    for fixture_id in CONTEXT_ROUTING:
        rows.append(_executed_row(root, fixture_id, "bounded"))
        stage = "p0" if fixture_id == "F-021" else "gate5"
        rows.extend(_sizing_rows(root, fixture_id, stage))
    for fixture_id in ADAPTER_SCIENTIFIC:
        profile = OPERATIONAL_PROFILES.get(fixture_id, "bounded")
        rows.append(_executed_row(root, fixture_id, profile))
        rows.extend(_gate5_adapter_rows(root, fixture_id, profile))
    return {
        "schema_version": "1.0.0",
        "matrix_revision": "p0-variant-matrix-v1",
        "counting_revisions": {name: f"tokens = ceil(bytes/{d})" for name, d in COUNTERS.items()},
        "rows": rows,
    }


def main() -> None:
    """Generate or check the committed variant matrix."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=_REPO_ROOT / ".research-system" / "evals" / "fixtures")
    parser.add_argument("--output", type=Path, default=_REPO_ROOT / ".research-system" / "evals" / "p0-variant-matrix.yaml")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = yaml.safe_dump(build_matrix(args.root), sort_keys=False).encode()
    if args.check:
        if args.output.read_bytes() != rendered:
            raise SystemExit("p0-variant-matrix.yaml is not byte-identical to regeneration")
        print("p0-variant-matrix.yaml byte-identical")
        return
    args.output.write_bytes(rendered)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Add the F-021 sizing bindings to its package**

In `tools/ars/materialize_context_routing_fixtures.py`, extend that shard's `Case` dataclass with the same two defaulted fields as Task 2 Step 2 (`fixture_revision: str = "r1"`, `mutation_ids: tuple[str, ...] | None = None`) plus:

```python
    sizing_variant: bool = False
```

Wire `fixture_revision`/`mutation_ids` into that shard's `_package` exactly as in Task 2 Step 2 (the `common` dict and the `mutation_ids` line, currently line 439). Then, in `_package`, after the `variant_bindings` list is built inside `source`, append the sizing rows for sizing cases:

```python
    if case.sizing_variant:
        source["variant_bindings"] += [
            {
                "variant_id": f"mandatory_closure_sizing-{counter}",
                "provider_variant": counter,
                "runtime_variant": "python-3.13",
                "os": "windows",
                "transport": "in_process_fake",
            }
            for counter in ("fake-claude-count-v1", "fake-codex-count-v1")
        ]
```

Set on the F-021 case only: `fixture_revision="r2", sizing_variant=True` (keyword arguments appended to the existing `Case(...)` entry at line 46; its priority stays `"P1"`). Update `.research-system/evals/p0-coverage.yaml`: `F-021: r2`.

- [ ] **Step 4: Regenerate F-021 and generate the matrix**

```powershell
Remove-Item -Recurse -Force .research-system\evals\fixtures\F-021
uv run python tools/ars/materialize_context_routing_fixtures.py --root .research-system/evals/fixtures
uv run python tools/ars/materialize_context_routing_fixtures.py --root .research-system/evals/fixtures --check
uv run python tools/ars/materialize_control_store_fixtures.py --root .research-system/evals/fixtures --check
uv run python tools/ars/materialize_adapter_scientific_fixtures.py --root .research-system/evals/fixtures --check
uv run python tools/ars/materialize_p0_variant_matrix.py
uv run python tools/ars/materialize_p0_variant_matrix.py --check
```

Expected: F-021 regenerated at r2 with three `variant_bindings`; all shard `--check` runs byte-identical; matrix written then verified byte-identical. **Generate the matrix only after F-021's regeneration** — the sizing token counts are measured from the regenerated bytes.

- [ ] **Step 5: Run tests and full gates**

Run: `uv run pytest tests/research_system/unit/test_variant_matrix.py -q --no-cov`
Expected: PASS (all five tests).
Sweep for stale F-021 revision pins exactly as Task 2 Step 7 (`grep -rn '"F-021", "r1"' tests/research_system/`); F-021's calibration itself is unchanged (same stimulus/oracles — only the source manifest and revision changed, and `execute_f021` reads the payload only). Note the F-021 package hash fields (`source_manifest_hash`) change; any test asserting them regenerates its expectation from disk, never hardcodes.
Run: `uv run ruff check research_system tools/ars tests/research_system` and `uv run pytest tests/research_system -q --no-cov`
Expected: clean; all pass.

- [ ] **Step 6: Commit**

Subject: `[PIPELINE] P00: materialize ARS P0 variant matrix and F-021 sizing binding`

---

## Task 4: Full verification, obligation closure, and PR

**Files:**
- Modify: `docs/plans/agentic-research-system/implementation/04a-wp4-8-verdict-derivation-and-release-evidence-plan.md` (O7/O8 rows)

- [ ] **Step 1: Full gates and invariant smoke**

```powershell
uv run ruff check research_system tools/ars tests/research_system
uv run pytest tests/research_system -q --no-cov
uv run python -m research_system.cli eval validate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
```

Expected, exactly:
- ruff clean; all tests pass;
- `eval validate`: 37 fixtures;
- `eval calibrate`: `fixture_count: 37`, `blocked_fixture_count: 14`, `fixtures_with_uncalibrated_mutations: 0`, `mutation_calibration: "calibrated"`;
- `eval run`: `candidate_status: "blocked"`, `result_count: 122`.

Any deviation in `blocked_fixture_count` (≠14), `candidate_status` (≠blocked), or `result_count` (≠122) is a **stop condition** — report Partial, do not adjust expectations to match.

- [ ] **Step 2: Close O7/O8 in the 04a register**

In the 04a plan's obligation register, edit only the Disposition cells:
- O7 → `delivered by 04b (WP4.9) Task 2 — F-036 restored at r2 with three named executed mutations; quarantine cleared`
- O8 → `delivered by 04b (WP4.9) Tasks 1 and 3 — threshold-policies/p0-calibration-policy/p0-variant-matrix materialized and load-bearing; claude/codex variant execution remains Gate 5 (R8 of 04b)`

- [ ] **Step 3: Commit, push, PR**

Subject: `[PIPELINE] P00: close corpus obligations O7/O8 in the WP4.8 register`
PR title: `[PIPELINE] P00: ARS WP4.9 — corpus restore-to-spec (M-1, M-2)`. PR body must state, verbatim where marked:
- findings closed: M-1, M-2 (review 2026-07-07); 04a obligations O7, O8;
- the R8 deferral: *"claude/codex variant rows are registered `execution_stage: gate5`; variant-aware harness execution is a named Gate 5 dependency, not claimed here"*;
- the R12 deviation for owner confirmation: *"F-021's sizing variant is delivered as two provider-specific binding rows because the accepted no-wildcard rule forbids one provider-spanning row"*;
- revision bumps F-036→r2, F-021→r2 with the coverage-pin relaxation (per-package equality replaces the global r1 pin);
- the aggregate decision remains `blocked` (unchanged 14/122 invariants);
- the Research Assurance Evidence table (claims → enforcement artifacts, copied from this plan's Research Assurance Requirements).

Wait for CodeRabbit review to complete before merging; address findings on the branch; merge via `gh pr merge`.

- [ ] **Step 4: Vault entries (session close)**

Computational-Log (top of page, reverse-chronological): `[PIPELINE]` entry — F-036 restored to 06b identity (r2, three named mutations, quarantine cleared), policy/variant registries materialized and load-bearing, invariants unchanged (blocked 14/37, candidate blocked). No new seeds. Reference the pre-existing 2026-07-08 WP4.8 entry.

---

## Acceptance checklist

- [ ] `threshold-policies.yaml`, `p0-calibration-policy.yaml` (verbatim §571), `p0-variant-matrix.yaml` exist and are load-bearing (mismatch/omission fails `run_p0_coverage` or a binding test).
- [ ] F-036 at r2 matches 06b §2: lanes, `domain_coverage/synthetic`, three named mutations, D/T/R/M graders.
- [ ] All three F-036 mutations execute and are detected in both repetitions; producer flags never read by the derivation.
- [ ] Full-corpus quarantine set is empty (no `fixture_error` anywhere).
- [ ] F-021 stays P1, carries the sizing bindings, and the matrix records recomputable reference/token evidence for both fake counting revisions.
- [ ] No wildcard variant rows; every package binding is a matrix row.
- [ ] All shard `--check` runs and the matrix `--check` run report byte-identical.
- [ ] `blocked_fixture_count: 14`; `candidate_status: "blocked"`; `result_count: 122` — unchanged.
- [ ] 04a register rows O7/O8 marked delivered; R8/R12 stated in the PR body.
- [ ] CodeRabbit review completed before merge.

## Stop conditions (in addition to 05-plan §10)

1. The restored F-036 oracle still calibrates `fixture_error` — report Partial with the mismatch; never weaken `execute_f036`'s comparison or arithmetic.
2. Any unchanged package fails `--check` byte-identity after regeneration.
3. Any invariant drift: `blocked_fixture_count` ≠ 14, `candidate_status` ≠ `blocked`, `result_count` ≠ 122.
4. The coverage-pin relaxation (Task 2 Step 5) admits a revision mismatch instead of raising — the per-package equality check must fail closed.
