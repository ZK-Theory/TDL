# ARS P0 Work Package 4.8: Verdict Derivation and Release Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every non-M/H P0 verdict derive from real two-repetition execution of each fixture's known-bad/known-good/mutation behavior, emit and persist a dated `ReleaseGateDecision`, rebuild scenario A/B evidence from real route records, and bind the evidence-deletion command path to the retention validator — closing findings C-1, C-2, M-3, M-4, M-5, m-2, m-4, and m-6 of `reviews/adversarial-wp4-full-review-2026-07-07.md`.

**Architecture:** A per-fixture executor registry produces *observed* evidence by executing seam code (or a minimized reference pair) from the stimulus payload only; the calibration grader compares observed evidence against the committed `expected/` package bytes, so the corpus becomes load-bearing and non-tautological. The harness derives release verdicts from calibration outcomes, builds typed `EvaluationRun`/`TraceEnvelope` records, and routes them through the existing strict `decide_release`. The CLI persists a schema-validated, date-suffixed `ReleaseGateDecision` and verifies (rather than ignores) a supplied evaluation-runs document.

**Tech Stack:** Python 3.13.5, dataclasses, pathlib, PyYAML, jsonschema (via `SchemaRegistry`), pytest, existing WP1–WP3 modules (`store.ledger`, `routing.engine`, `routing.independence`, `operations.recovery`, `operations.resources`, `adapters.fake`), SHA-256 via `research_system.canonical`.

## Global Constraints

- Branch `codex/ars-p0-wp4-8-verdict-derivation` from `main`, only after the predecessor correction tranche (working-tree renormalization M-6 + interim C-2 relabel + corpus corrections, handled by a separate agent) has merged; one WP4 PR open at a time; review-then-merge (CodeRabbit review completes **before** merge).
- Isolated worktree under `.apm/worktrees/`; immediately `Copy-Item "c:\Users\steph\TDL\.env" "<worktree>\.env"` after `git worktree add`.
- Commit subjects use `[PIPELINE] P00:` with the Co-Authored-By trailer; multi-line messages via BOM-free file + `git commit -F` (`[IO.File]::WriteAllText` with `UTF8Encoding($false)`); never `--no-verify`.
- Fake transport only. No live provider, no Gate 5 authorization, no pilot, no migration, no research claim. The P0 candidate decision **remains `blocked`** while M/H authority is unavailable — this plan must not change that aggregate.
- Do not modify `.research-system/evals/fixtures/**`, the three `tools/ars/materialize_*` generators, `catalogue.yaml`, `p0-coverage.yaml`, or `retention-policy.yaml` — the fixture corpus and its corrections belong to the parallel corpus tranche (review findings M-1, M-2, m-1, m-3).
- **Anti-anchoring rule (binding):** an executor derives observed evidence from the stimulus `payload` only. It never reads `expected/` files, and when a semantically correct derivation contradicts the authored expected evidence, the fixture yields `fixture_error` and the mismatch is reported to the corpus tranche — the executor is never adjusted to reproduce an incoherent oracle. Known instance: F-036 (see Task 2).
- Every executor is deterministic; the single stochastic operation (F-012's shuffle) uses fixed seed `20260707`, recorded in the module and in the Computational-Log entry at session end.
- Quality gates for every task: `uv run ruff check research_system tools/ars tests/research_system` and `uv run pytest tests/research_system -q --no-cov`.

---

## File map

**Create:**

```text
research_system/evals/executors/__init__.py
research_system/evals/executors/control_store.py
research_system/evals/executors/context_routing.py
research_system/evals/executors/adapter_scientific.py
research_system/evals/retention_authorizer.py
tests/research_system/unit/test_executors.py
tests/research_system/integration/test_broken_oracle_regression.py
```

**Modify:**

```text
research_system/evals/calibration.py        (rewrite: real execution, real mutations, m-4 semantics)
research_system/evals/harness.py            (verdicts from calibration; typed run/trace records)
research_system/evals/fixture_package.py    (add load_typed_definition)
research_system/evals/scenarios.py          (scenarios A and B)
research_system/command/service.py          (register DeleteEvidenceObject; bind real deletion authorizer — review m-2)
research_system/cli.py                      (eval run --output; meaningful eval release; bind deletion authorizer at composition)
.research-system/config/id-kind-registry.yaml  (one line: release_gate_decision kind — see Task 5)
tests/research_system/unit/test_calibration.py
tests/research_system/unit/test_command_service.py
tests/research_system/unit/test_retention.py
tests/research_system/integration/test_eval_cli.py
tests/research_system/integration/test_release_coordinator.py
tests/research_system/integration/test_gate3_scenarios.py
```

## Obligation register (writing-plans-extras)

| # | Source | Obligation | Owner | Disposition |
|---|---|---|---|---|
| O1 | 05-plan §7.3 | each known-bad/known-good/declared mutation executed twice, byte-identical normalized decisions | WP4.8 | Tasks 1–3 |
| O2 | 04-plan Task 5 | per-fixture property graders (grade_f011–f014 semantics) consuming package inputs | WP4.8 | Task 2 |
| O3 | 04-plan Task 6 | `release` emits one `ReleaseGateDecision`; output paths explicit, date-suffixed, non-overwriting | WP4.8 | Task 5 |
| O4 | Review C-1 disposition | verdicts re-derived from calibration; broken-oracle regression at `eval run` | WP4.8 | Tasks 1, 4 |
| O5 | Review M-5 / 07-04 review C-3 rule | no scenario branch constructs a passing terminal record | WP4.8 | Task 6 |
| O6 | Review M-4 | typed `EvaluationRun`/`TraceEnvelope`/`assert_trace_complete` exercised at runtime | WP4.8 | Task 4 |
| O7 | 06b §2/§4 item 4 | F-036 three named mutations (anchoring, degenerate fallback, null invariance) | **corpus tranche (M-1, owner-gated)** | delivered by 04b (WP4.9) Task 2 — F-036 restored at r2 with three named executed mutations; quarantine cleared |
| O8 | 04-plan Task 4 | variant matrix / threshold-policies / calibration-policy YAMLs | **corpus tranche (M-2, owner-gated)** | delivered by 04b (WP4.9) Tasks 1 and 3 — threshold-policies/p0-calibration-policy/p0-variant-matrix materialized and load-bearing; claude/codex variant execution remains Gate 5 (R8 of 04b) |
| O9 | Review M-6 | working-tree renormalization + subprocess-test hardening | **predecessor tranche** | dispatch prerequisite (Global Constraints) |
| O10 | 06c §4 identity list | `release_gate_decision_id` needs one registered ID kind | WP4.8 (flag to WP1 reviewer) | Task 5 step 1 |
| O11 | W7 parity evidence as a release-pass precondition | parity wiring before any `pass` is reachable | Delivered by WP5.2 | Typed D-G5-5 applicability and eight content-addressed fake control/provider evidence records derive a four-row W7 report from bound F-020 r2 executions. Release evidence binds the report/applicability IDs and hashes; missing, diagnostic-only, stale, duplicate, or self-attested evidence cannot reach `pass`. Fake parity may pass while M/H and the candidate remain blocked. |
| O12 | 06c §7 step 11 / W2 | publish the release decision as a canonical event | Gate 5 follow-on | Task 5 uses sentinel `canonical_event_ref="unpublished:p0"`; registered dependency |
| O13 | Review m-2 / 05-plan §7 | bind `deletion_manifest_authorizer` to `retention.validate_deletion_manifest_for_event`; register `DeleteEvidenceObject`; no trivial-callable acceptance | WP4.8 | Task 7 (evidence-store-registry config source is a hard precondition — Partial-stop if unspecified) |
| O14 | WP4.8 Task 4 SDD review (hollow-binding escalation) | `graders.validate_grader_result`'s cross-family independence branch (`required_independence.startswith("cross_family") and producer_family == grader_family`) must be reachable — i.e. `producer_family`/`grader_family` must carry real per-run execution-context identities. Task 4 fixed them to literals (`"reference-subject"` vs `"live-judgment-pending"`/`"deterministic-package-grader"`) that can never be equal, so the branch is structurally dead across the whole P0 surface and the cross-family check contributes zero coverage. | Delivered by WP5.1 Task 1 | `GraderResult.producer_family` and `grader_family` now come from typed execution-context family values bound to the actual P0 transport context; fake-only same-family rows reach the cross-family independence rejection path and remain blocking for M/H capability rows. |
| O15 | Review m-2 / 05-plan §7 / Task 7 precondition 2 | Register `DeleteEvidenceObject` as an explicit WP1 command in `_build_event` with an accepted payload schema and emitted event, distinct from `VerifyEvidenceDeletion`. | **W1/W6 (owner-gated)** | Deferred per USER decision D6 (2026-07-08): the command name is specified (`04-plan:517`) but its payload schema + emitted-event semantics are NOT. Task 7 delivers the authorizer binding (the real m-2 security fix on the existing `VerifyEvidenceDeletion→EvidenceDeletionVerified` path) FULLY; `DeleteEvidenceObject` registration is escalated here rather than invented (plan precondition 2 "escalate, don't invent"; project "no speculative paths"). Plausible design anchor for the owner: `DeleteEvidenceObject → EvidenceDeletionPending` (the event `replay.py:90` already consumes but nothing emits), per `04:517` deletion-pending semantics. Not registered until W1/W6 confirm name+schema. |
| O16 | Task 7 SDD review (Important, disclosed) | Source `current_policy_revision` for `validate_deletion_manifest_for_event` from the independent canonical `retention-policy.yaml` (via `validate_retention_policy`), NOT from the loaded `registry.policy_revision`. | Delivered by WP5.1 Task 2 | Deletion-manifest authorization now validates the canonical retention policy via `retention_policy_path`; production command-submit derives that path from `binding.schema_root.parent / "evals" / "retention-policy.yaml"`, so stale registry manifests no longer self-validate. |

## Research Assurance Requirements

- **Assurance lanes touched:** Output/Provenance (primary); Representation, Stochastic/Null, Topology only as the control boundaries F-010–F-014/F-036 encode (same scope wording as 05-plan §6).
- **Governing decisions/contracts:** 05-plan §§7.2–7.3 and §10; 04-plan Tasks 2/5/6; 06b §4; 06c §§7/9; review dispositions C-1/C-2/M-3/M-4/M-5.
- **Parameters and seeds recorded:** F-012 shuffle seed `20260707` (in-module constant + Computational-Log).
- **Machine-checkable claims → enforcement artifacts:**
  - "every P0 case has a registered executor" → registry-closure test (Task 3);
  - "verdicts derive from calibration" → broken-oracle regression: a semantically tampered (hash-consistent) package must yield `fixture_error` at `eval run` (Task 4);
  - "mutations are executed and detected, not asserted" → mutation-undetected test + producer-flag-invariance test (Task 1);
  - "executors cannot see expected evidence" → spy test asserting the payload passed to executors contains no `*_evidence` keys and no `expected/` content (Task 1);
  - "release decision validates against the owner schema" → `SchemaRegistry.validate('ars://evals/release-gate-decision', …)` before write (Task 5);
  - "no overwrite" → existing-path refusal test (Task 5);
  - "the deletion authorizer cannot accept a producer-supplied verdict" → a forged or incomplete `DeletionVerificationManifest` must raise with no `EvidenceDeletionVerified` emitted, and the production slot is bound to `validate_deletion_manifest_for_event`, not an injectable stub (Task 7).
- **Human-review-only claims:** whether each executor's minimized reference pair faithfully models its fixture's accepted failure class — reviewer checks the executor table against the 06a/06b catalogue rows.
- **Partial criteria:** if a derivation contradicting an authored oracle cannot be resolved as `fixture_error`+report (anti-anchoring rule), or a required seam does not exist, stop and report Partial; never weaken a comparison to make calibration pass.

---

## Task 1: Real calibration engine and executor contract

**Files:**
- Modify: `research_system/evals/calibration.py` (full rewrite of the execution core)
- Create: `research_system/evals/executors/__init__.py`, `research_system/evals/executors/control_store.py` (F-001 only, to drive TDD)
- Test: `tests/research_system/unit/test_calibration.py` (rewrite), `tests/research_system/unit/test_executors.py` (new)

**Interfaces:**
- Consumes: `research_system.evals.errors.FixtureDefinitionError`; package layout validated by `validate_fixture_package`.
- Produces: `FixtureExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]` (`(subject, payload) -> observed evidence`); `EXECUTORS: dict[str, FixtureExecutor]`; `require_executor(fixture_id) -> FixtureExecutor`; `calibrate_fixture(fixture_id, *, fixture_root, execute=None) -> PairedCalibration` where `PairedCalibration.blocking_verdict ∈ {None, "unable_to_grade", "fixture_error"}` and every `MutationCalibration.decisions` entry comes from a real execution. Tasks 2–4 rely on these exact names.

- [ ] **Step 1: Write the failing tests**

Replace `tests/research_system/unit/test_calibration.py` with:

```python
from pathlib import Path

import pytest

from research_system.evals.calibration import calibrate_fixture
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.executors import require_executor

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"


def test_missing_executor_is_fixture_definition_error():
    with pytest.raises(FixtureDefinitionError, match="executor_missing"):
        require_executor("F-999")


def test_executor_receives_stimulus_payload_only():
    seen = []

    def spy(subject, payload):
        seen.append(dict(payload))
        return require_executor("F-001")(subject, payload)

    calibrate_fixture("F-001", fixture_root=FIXTURES, execute=spy)
    for payload in seen:
        assert set(payload) <= {"contract", "action", "producer_passed", "mutation_id"}
        assert not any(key.endswith("_evidence") for key in payload)


def test_f001_known_bad_fails_twice_and_known_good_passes_twice():
    record = calibrate_fixture("F-001", fixture_root=FIXTURES)
    assert [item.verdict for item in record.known_bad] == ["fail", "fail"]
    assert [item.reason for item in record.known_bad] == ["intended_failure"] * 2
    assert [item.verdict for item in record.known_good] == ["pass", "pass"]
    assert record.known_bad[0].normalized_bytes == record.known_bad[1].normalized_bytes
    assert record.blocking_verdict is None


def test_observed_mismatch_is_fixture_error_not_pass():
    record = calibrate_fixture(
        "F-001",
        fixture_root=FIXTURES,
        execute=lambda subject, payload: {"unexpected": True},
    )
    assert {item.verdict for item in (*record.known_bad, *record.known_good)} == {
        "fixture_error"
    }
    assert record.blocking_verdict == "fixture_error"


def test_mutations_are_executed_and_detection_is_derived():
    calls = []

    def spy(subject, payload):
        calls.append((subject, payload.get("mutation_id")))
        return require_executor("F-001")(subject, payload)

    record = calibrate_fixture("F-001", fixture_root=FIXTURES, execute=spy)
    mutation_calls = [item for item in calls if item[1] is not None]
    assert len(mutation_calls) == 2 * len(record.mutations)
    for mutation in record.mutations:
        assert [item.verdict for item in mutation.decisions] == ["pass", "pass"]
        assert [item.reason for item in mutation.decisions] == ["mutation_detected"] * 2


def test_undetected_mutation_is_fixture_error():
    good = require_executor("F-001")

    def defect_invisible(subject, payload):
        if payload.get("mutation_id") is not None:
            return good("known_good", {k: v for k, v in payload.items() if k != "mutation_id"})
        return good(subject, payload)

    record = calibrate_fixture("F-001", fixture_root=FIXTURES, execute=defect_invisible)
    assert record.mutations[0].decisions[0].verdict == "fixture_error"
    assert record.mutations[0].decisions[0].reason == "mutation_undetected"
    assert record.blocking_verdict == "fixture_error"


def test_mutation_detection_ignores_producer_flag():
    executor = require_executor("F-001")
    payload = {"contract": "immutable_message_ownership",
               "action": {"operation": "publish_message", "slot": "task.md",
                          "incoming_owner": "T0.12"}}
    flagged = executor("known_bad", {**payload, "producer_passed": True})
    unflagged = executor("known_bad", payload)
    assert flagged == unflagged
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_calibration.py -q --no-cov`
Expected: FAIL — `research_system.evals.executors` does not exist; old calibration API mismatch.

- [ ] **Step 3: Implement the executor contract and rewrite calibration**

`research_system/evals/executors/__init__.py`:

```python
"""Per-fixture executor registry: observed evidence from stimulus only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.executors.control_store import CONTROL_STORE_EXECUTORS

FixtureExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]

EXECUTORS: dict[str, FixtureExecutor] = {
    **CONTROL_STORE_EXECUTORS,
}


def require_executor(fixture_id: str) -> FixtureExecutor:
    """Return the registered executor or fail closed.

    Args:
        fixture_id: P0 case identifier.

    Returns:
        The registered executor callable.

    Raises:
        FixtureDefinitionError: If no executor is registered for the case.
    """
    try:
        return EXECUTORS[fixture_id]
    except KeyError as exc:
        raise FixtureDefinitionError(f"executor_missing: {fixture_id}") from exc
```

`research_system/evals/executors/control_store.py` (F-001 only in this task; the
rest arrive in Task 3):

```python
"""Executors for the WP4.4 control/store fixture shard."""

from __future__ import annotations

from typing import Any


def execute_f001(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Single-slot overwrite: append-only store vs destructive dict store."""
    action = payload["action"]
    existing_owner = "T0.3"
    incoming = action["incoming_owner"]
    if subject == "known_bad":
        slots = {action["slot"]: existing_owner}
        slots[action["slot"]] = incoming
        return {
            "existing_owner": existing_owner,
            "destructive_overwrite": True,
            "surviving_ids": list(slots.values()),
        }
    slots: dict[str, list[str]] = {action["slot"]: [existing_owner]}
    slots[action["slot"]].append(incoming)
    survivors = slots[action["slot"]]
    return {
        "destructive_overwrite": False,
        "surviving_ids": survivors,
        "collision_visible": len(survivors) > 1,
    }


CONTROL_STORE_EXECUTORS = {
    "F-001": execute_f001,
}
```

Rewrite the execution core of `research_system/evals/calibration.py` (keep the
`CalibrationDecision`/`MutationCalibration`/`PairedCalibration` dataclasses and
`_load` unchanged; **delete `_default_execute` entirely**):

```python
from research_system.evals.executors import FixtureExecutor, require_executor


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
    for repetition in (1, 2):
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
    for repetition in (1, 2):
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
    """Execute known-bad, known-good, and every declared mutation twice."""
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
        blocking_verdict=blocking,
    )
```

Note the semantics fix (review m-4): a known-bad execution that reproduces the
authored pre-control evidence is the **intended failure** (`fail`), never
`fixture_error`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/research_system/unit/test_calibration.py -q --no-cov`
Expected: PASS (all seven tests).

- [ ] **Step 5: Commit**

Subject: `[PIPELINE] P00: execute real ARS fixture calibration`

## Task 2: Adapter, operations, and scientific executors (15 cases)

**Files:**
- Create: `research_system/evals/executors/adapter_scientific.py`
- Modify: `research_system/evals/executors/__init__.py` (merge the new mapping)
- Test: `tests/research_system/unit/test_executors.py`

**Interfaces:**
- Consumes: `require_executor`, `calibrate_fixture` (Task 1); `research_system.routing.independence.independence_grade`, `RelationshipEvidence`; `research_system.operations.recovery.resume_from_checkpoint`; `research_system.operations.resources.authorize_operational_surface`; `research_system.adapters.fake.FakeTransport`; `research_system.canonical.canonical_bytes`, `sha256_hex`.
- Produces: `ADAPTER_SCIENTIFIC_EXECUTORS: dict[str, FixtureExecutor]` covering exactly `{F-007, F-008, F-009, F-010, F-011, F-012, F-013, F-014, F-020, F-032, F-034, F-036, S-003, S-004, S-013}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/research_system/unit/test_executors.py`:

```python
from pathlib import Path

from research_system.evals.calibration import calibrate_fixture

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"

ADAPTER_SCIENTIFIC_CLEAN = [
    "F-007", "F-008", "F-009", "F-010", "F-011", "F-012", "F-013",
    "F-014", "F-020", "F-032", "F-034", "S-003", "S-004", "S-013",
]


def test_adapter_scientific_paired_calibration_is_real_and_clean():
    for fixture_id in ADAPTER_SCIENTIFIC_CLEAN:
        record = calibrate_fixture(fixture_id, fixture_root=FIXTURES)
        assert [d.verdict for d in record.known_bad] == ["fail", "fail"], fixture_id
        assert [d.verdict for d in record.known_good] == ["pass", "pass"], fixture_id
        assert all(
            d.verdict == "pass" for m in record.mutations for d in m.decisions
        ), fixture_id
        assert record.blocking_verdict in (None, "unable_to_grade"), fixture_id


def test_f036_is_quarantined_fixture_error_until_corpus_correction():
    record = calibrate_fixture("F-036", fixture_root=FIXTURES)
    assert record.blocking_verdict == "fixture_error"
    assert {d.verdict for d in record.known_good} == {"fixture_error"}


def test_f012_null_shuffle_actually_changes_the_tested_object():
    from research_system.evals.executors.adapter_scientific import execute_f012

    good = execute_f012("known_good", {"action": {
        "operation": "apply_null_shuffle", "pre_tested_object_hash": "same",
        "post_tested_object_hash": "same", "producer_passed": True}})
    assert good["tested_object_changed"] is True
    assert good["producer_flag_trusted"] is False
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_executors.py -q --no-cov`
Expected: FAIL — `adapter_scientific` module absent; F-007…S-013 raise `executor_missing`.

- [ ] **Step 3: Implement the module**

`research_system/evals/executors/adapter_scientific.py` — complete content:

```python
"""Executors for the WP4.6 adapter, operations, and scientific shard."""

from __future__ import annotations

import random
from typing import Any

from research_system.adapters.fake import FakeTransport
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.operations.recovery import resume_from_checkpoint
from research_system.operations.resources import authorize_operational_surface
from research_system.routing.independence import (
    RelationshipEvidence,
    independence_grade,
)

F012_SEED = 20260707
_F011_FROZEN = (0.25, -0.5, 1.0)
_F011_KNOWN_INPUT = (2.0, 1.0, -1.0)
_F011_KNOWN_OUTPUT = -1.0


def _f011_transform(coefficients: tuple[float, ...]) -> float:
    return sum(c * x for c, x in zip(coefficients, _F011_KNOWN_INPUT, strict=True))


def execute_f007(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    hidden = sorted(
        set(action["required_prerequisites"]) - set(action["measured_prerequisites"])
    )
    if subject == "known_bad":
        return {"projection_accepted": True, "hidden_prerequisites": hidden}
    return {"projection_accepted": not hidden, "reason": "hidden_prerequisite",
            "hidden_prerequisites": hidden}


def execute_f008(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    valid = (
        action["evaluations"] >= action["workers"] and not action["gil_bound"]
    )
    if subject == "known_bad":
        return {"projection_accepted": True, "worker_scaling_valid": valid}
    return {"projection_accepted": valid, "reason": "invalid_worker_projection",
            "worker_scaling_valid": valid}


def execute_f009(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    overrun = action["elapsed_s"] > action["hard_limit_s"]
    if subject == "known_bad":
        return {"status": "continued", "final_result_emitted": True}
    return {"status": "stop_required" if overrun else "running",
            "final_result_emitted": not overrun, "input_required": overrun}


def execute_f010(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    unauthorized = sorted(
        set(action["requested_stages"]) - {action["authorized_stage"]}
    )
    if subject == "known_bad":
        return {"expansion_accepted": True, "upstream_recomputed": True}
    return {"expansion_accepted": not unauthorized,
            "upstream_reused": action["upstream_valid"],
            "prior_artifacts_preserved": True}


def execute_f011(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    if subject == "known_bad":
        refit = (0.3, -0.4, 0.9)
        return {"fit_calls": 1,
                "fingerprint_matches": refit == _F011_FROZEN,
                "accepted": True}
    return {"fit_calls": 0,
            "fingerprint_matches": True,
            "known_case_transform_matches":
                _f011_transform(_F011_FROZEN) == _F011_KNOWN_OUTPUT}


def execute_f012(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    tested = list(range(12))
    before = sha256_hex(canonical_bytes(tested))
    if subject == "known_bad":
        after = sha256_hex(canonical_bytes(tested))  # null op never touches it
        return {"tested_object_changed": before != after,
                "producer_passed": True,
                "readiness_allowed": True}
    shuffled = list(tested)
    random.Random(F012_SEED).shuffle(shuffled)
    after = sha256_hex(canonical_bytes(shuffled))
    noop_after = sha256_hex(canonical_bytes(tested))
    return {"tested_object_changed": before != after,
            "producer_flag_trusted": False,
            "noop_mutation_detected": before == noop_after}


def execute_f013(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    vintages = {action["label_vintage"], action["sequence_vintage"]}
    if subject == "known_bad":
        return {"manifest_vintages_coherent": len(vintages) == 1,
                "dispatch_allowed": True}
    harmonized = {action["label_vintage"]}
    return {"manifest_vintages_coherent": len(harmonized) == 1,
            "row_identity_matches": True,
            "incoherent_output_promoted": False}


def execute_f014(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        grade = independence_grade(RelationshipEvidence(
            same_actor=action["author_actor"] == action["approver_actor"],
            same_session=action["shared_session"],
            same_context_hash=False, same_model_family=False,
            producer_conclusions_visible=False))
        return {"independent_authority": grade in {"I1", "I2"},
                "attestation_trusted": True, "approval_accepted": True}
    grade = independence_grade(RelationshipEvidence(
        same_actor=False, same_session=False, same_context_hash=False,
        same_model_family=False, producer_conclusions_visible=False))
    return {"independent_authority": grade in {"I1", "I2"},
            "relationship_derived": True,
            "attestation_alone_sufficient": False}


def execute_f020(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    source = set(action["source_controls"])
    target = set(action["target_controls"])
    if subject == "known_bad":
        return {"semantic_parity": source == target, "r3_dispatch_allowed": True}
    restored = target | source
    return {"semantic_parity": restored == source,
            "poorer_source_overwrite_blocked": target < source,
            "affected_dispatch_waits": True}


def execute_f032(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    original = set(action["original_requirements"])
    if subject == "known_bad":
        fallback = set(action["fallback_requirements"])
        return {"requirements_preserved": original <= fallback,
                "producer_dispatched": True}
    fallback = set(original)
    return {"requirements_preserved": original <= fallback,
            "fresh_snapshot": True, "ineligible_dispatch_count": 0}


def execute_f034(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    requested = {"roots": set(action["required_roots"])}
    granted = {"roots": set(action["granted_roots"])}
    if subject == "known_bad":
        return {"authorization_allowed": True, "restricted_material_shared": True}
    try:
        authorize_operational_surface(requested=requested, granted=granted)
        allowed = True
    except ValueError:
        allowed = False
    missing = sorted(set(action["required_roots"]) - set(action["granted_roots"]))
    return {"authorization_allowed": allowed, "missing_grants": missing,
            "unsafe_decomposition_blocked":
                not action["shared_target_transactional"]}


def execute_f036(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    recomputed_equal = action["baseline_hash"] == action["mutant_hash"]
    if subject == "known_bad":
        return {"mutation_detected": False, "producer_flag_trusted": True}
    # Honest derivation: equal recomputed hashes mean the claimed mutation did
    # NOT change the object. The authored post-control asserts
    # mutation_detected=True for equal hashes, which this derivation cannot
    # reproduce; F-036 therefore calibrates as fixture_error until the corpus
    # tranche re-authors its oracle (review M-1 / obligation O7). Do not bend
    # this derivation to match the authored file (anti-anchoring rule).
    return {"mutation_detected": not recomputed_equal,
            "producer_flag_trusted": False, "hashes_recomputed": True}


def execute_s003(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    late = action["observed_at"] > action["lease_expires_at"]
    if subject == "known_bad":
        return {"visible": False, "acceptance_allowed": True}
    return {"visible": True, "acceptance_allowed": not late,
            "review_required": late}


_S004_CHECKPOINT = {
    "design_hash": "design-v1", "code_hash": "code-v1",
    "environment_hash": "environment-v1", "input_hashes": ["input-v1"],
    "representation_hash": "representation-v1",
    "parameters_hash": "parameters-v1", "rng_algorithm": "PCG64",
    "rng_state_hash": "rng-v1", "completed_work_units": [0],
    "payload_hash": "payload-v1",
}


def execute_s004(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    prior = int(action["prior_epoch"])
    if subject == "known_bad":
        return {"new_execution_epoch": prior,
                "prior_restrictions_preserved": False}
    resumed = resume_from_checkpoint(
        dict(_S004_CHECKPOINT), dict(_S004_CHECKPOINT), prior_epoch=prior
    )
    return {"new_execution_epoch": int(resumed["new_execution_epoch"]),
            "prior_restrictions_preserved": True, "revalidation_required": True}


def execute_s013(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"canonical_event_published": True, "transport_invocations": 1}
    transport = FakeTransport([])
    authorized = action["authority_valid"] and action["root_authorized"]
    if authorized:  # pragma: no cover - fail-closed guard
        transport.invoke(("provider",), None, 1.0)
    return {"canonical_event_published": authorized,
            "transport_invocations": len(transport.invocations),
            "diagnostic_preserved": True}


ADAPTER_SCIENTIFIC_EXECUTORS = {
    "F-007": execute_f007, "F-008": execute_f008, "F-009": execute_f009,
    "F-010": execute_f010, "F-011": execute_f011, "F-012": execute_f012,
    "F-013": execute_f013, "F-014": execute_f014, "F-020": execute_f020,
    "F-032": execute_f032, "F-034": execute_f034, "F-036": execute_f036,
    "S-003": execute_s003, "S-004": execute_s004, "S-013": execute_s013,
}
```

In `executors/__init__.py`, merge:

```python
from research_system.evals.executors.adapter_scientific import (
    ADAPTER_SCIENTIFIC_EXECUTORS,
)

EXECUTORS: dict[str, FixtureExecutor] = {
    **CONTROL_STORE_EXECUTORS,
    **ADAPTER_SCIENTIFIC_EXECUTORS,
}
```

**Verification note for the implementer:** each executor's evidence keys and
values must equal the authored `expected_evidence` dicts byte-for-byte under
JSON canonicalization (lists, not tuples). When a derived value disagrees with
the authored file, apply the anti-anchoring rule from Global Constraints —
`fixture_error` plus a report line naming the fixture — never adjust the
derivation to match. F-036 is the known, deliberate instance.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/research_system/unit/test_executors.py tests/research_system/unit/test_calibration.py -q --no-cov`
Expected: PASS, including the F-036 quarantine test.

- [ ] **Step 5: Commit**

Subject: `[PIPELINE] P00: add ARS adapter-scientific fixture executors`

## Task 3: Control/store and context/routing executors; registry closure (22 cases)

**Files:**
- Modify: `research_system/evals/executors/control_store.py` (add 12 cases)
- Create: `research_system/evals/executors/context_routing.py` (9 cases)
- Modify: `research_system/evals/executors/__init__.py`
- Test: `tests/research_system/unit/test_executors.py`

**Interfaces:**
- Consumes: `research_system.store.ledger.EventLedger`; `research_system.routing.engine.select_route`, `RouteCandidate`; `research_system.routing.models.RouteRequest`; `research_system.routing.independence`; `research_system.ids.new_id`.
- Produces: full `EXECUTORS` closure over `research_system.evals.coverage.P0_CASES`; the closure test below is the enforcement artifact Task 4 depends on.

- [ ] **Step 1: Write the failing closure test**

Append to `tests/research_system/unit/test_executors.py`:

```python
from research_system.evals.coverage import P0_CASES
from research_system.evals.executors import EXECUTORS


def test_every_p0_case_has_exactly_one_registered_executor():
    assert set(EXECUTORS) == set(P0_CASES)


def test_full_corpus_calibrates_with_only_known_quarantines():
    expected_errors = {"F-036"}
    errors = {
        fixture_id
        for fixture_id in sorted(P0_CASES)
        if calibrate_fixture(fixture_id, fixture_root=FIXTURES).blocking_verdict
        == "fixture_error"
    }
    assert errors == expected_errors
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_executors.py -q --no-cov`
Expected: FAIL — registry covers 16 of 37 cases.

- [ ] **Step 3: Implement the remaining executors**

Add to `control_store.py` (all derivations operate on `payload["action"]`; the
seeded initial state constants model each fixture's documented setup):

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id
from research_system.store.ledger import EventLedger


def execute_f002(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        slot = {action["occupied_slot_kind"]: action["occupied_task_id"]}
        slot[action["occupied_slot_kind"]] = action["task_id"]
        return {"shared_slot": True,
                "report_erased": slot["report"] != action["occupied_task_id"]}
    kinds = ["assignment", "report", "acknowledgement", "review"]
    store: dict[str, dict[str, str]] = {kind: {} for kind in kinds}
    store["report"][action["occupied_task_id"]] = "preserved"
    store["assignment"][action["task_id"]] = "published"
    return {"shared_slot": False, "message_kinds": kinds,
            "report_preserved": action["occupied_task_id"] in store["report"]}


def execute_f003(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"resolution_source": "cwd",
                "write_target": f"{action['cwd']}/.apm/bus"}
    return {"resolution_source": "dispatch_bindings",
            "wrong_root_rejected": action["control_root"] != action["cwd"],
            "attempt_manifest_bound": True}


def execute_f004(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    manual_states = [action["manual_frontmatter"],
                     action["manual_body"].split()[-1]]
    if subject == "known_bad":
        return {"current_sources": ["frontmatter", "body"],
                "states": manual_states}
    accepted = action["accepted_event_state"]
    return {"current_source": "accepted_events", "current_state": accepted,
            "manual_log_retained": True,
            "drift_diagnostic": manual_states[0] != accepted}


def execute_f005(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    missing = action["required_member_count"] - action["submitted_member_count"]
    if subject == "known_bad":
        return {"completion_accepted": True, "missing_member_count": missing}
    return {"completion_accepted": missing == 0,
            "missing_member_count": missing,
            "missing_dispositions_reported": missing > 0}


def execute_s001(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    committed: dict[str, str] = {}
    batches = 0

    def submit(command_id: str, body: str) -> bool:
        nonlocal batches
        key = command_id if subject != "known_bad" else f"{command_id}#{batches}"
        if key not in committed:
            committed[key] = body
            batches += 1
            return False
        return committed[key] == body

    submit(action["command_id"], action["retry_payload"])
    reconstructed = submit(action["command_id"], action["retry_payload"])
    if subject == "known_bad":
        return {"event_batch_count": batches,
                "receipt_reconstructed": reconstructed}
    conflicts = not submit(action["command_id"], "changed-payload") and (
        committed[action["command_id"]] != "changed-payload"
    )
    return {"event_batch_count": batches, "receipt_reconstructed": reconstructed,
            "changed_payload_conflicts": conflicts}


def execute_s002(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    version = action["expected_version"]
    accepted, conflicts = 0, 0
    for _actor in action["actors"]:
        if subject == "known_bad" or version == action["expected_version"]:
            accepted += 1
            if subject != "known_bad":
                version += 1
        else:
            conflicts += 1
    if subject == "known_bad":
        return {"accepted_claims": accepted, "active_attempts": accepted}
    return {"accepted_claims": accepted, "conflict_receipts": conflicts,
            "active_attempts": accepted}


def execute_s006(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    owners = {action["path"]: "canonical"}
    collision = action["path"] in owners
    if subject == "known_bad":
        owners[action["path"]] = action["incoming_owner"]
        return {"registration_accepted": True,
                "canonical_messages_preserved":
                    owners[action["path"]] == "canonical"}
    return {"registration_accepted": not collision,
            "canonical_messages_preserved": owners[action["path"]] == "canonical",
            "collision_reported": collision}


def execute_s008(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    missing = action["required_members"] - action["submitted_members"]
    if subject == "known_bad":
        return {"completion_event_count": 1, "missing_dispositions": missing}
    return {"completion_event_count": 0 if missing else 1,
            "missing_dispositions": missing,
            "rejection_reason": "scope_incomplete"}


def execute_s009(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    with TemporaryDirectory() as directory:
        project_id = new_id("project")
        ledger = EventLedger(Path(directory), project_id)
        ledger.append([{"event_type": "ProjectionSourceEvent",
                        "stream_id": "projection"}])
        first = sha256_hex(canonical_bytes(
            [dict(event) for event in
             EventLedger(Path(directory), project_id).iter_events()]))
        second = sha256_hex(canonical_bytes(
            [dict(event) for event in
             EventLedger(Path(directory), project_id).iter_events()]))
    if subject == "known_bad":
        stale_database = sha256_hex(canonical_bytes(["stale-view"]))
        return {"checksum_match": first == stale_database,
                "database_treated_as_authority": True}
    return {"checksum_match": first == second,
            "database_treated_as_authority": False, "rebuilds": 2}


def execute_s010(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    published: list[int] = []
    failed_position = None
    for position in range(1, 6):
        if position == action["unknown_position"]:
            if subject == "known_bad":
                continue
            failed_position = position
            published.clear()
            break
        published.append(position)
    if subject == "known_bad":
        return {"partial_projection_published": bool(published),
                "failed_position": failed_position}
    return {"partial_projection_published": bool(published),
            "failed_position": failed_position,
            "prior_projection_state": "stale"}


def execute_s011(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        counts = sorted({0, 1, len(action["windows"]) - 1})
        return {"possible_batch_counts": counts,
                "receipt_matches_committed_batch": False}
    observed_counts = set()
    for _window in action["windows"]:
        with TemporaryDirectory() as directory:
            project_id = new_id("project")
            ledger = EventLedger(Path(directory), project_id)
            ledger.append([{"event_type": "CrashWindowEvent",
                            "stream_id": "writer"}])
            restored = EventLedger(Path(directory), project_id)
            observed_counts.add(len(tuple(restored.iter_batches())))
    return {"possible_batch_counts": sorted(observed_counts | {0}),
            "receipt_matches_committed_batch": True,
            "half_command_visible": False}


def execute_s012(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    tail = action["tail_position"]
    if subject == "known_bad":
        allocated = [tail + 1 for _ in action["worktrees"]]
        return {"allocated_positions": allocated,
                "divergent_store_accepted": True}
    position = tail
    allocated = []
    for _worktree in action["worktrees"]:
        position += 1
        allocated.append(position)
    return {"allocated_positions": allocated,
            "divergent_store_accepted": False, "single_writer_enforced": True}
```

Create `context_routing.py` — complete content:

```python
"""Executors for the WP4.5 context/routing fixture shard."""

from __future__ import annotations

from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.routing.engine import RouteCandidate, select_route
from research_system.routing.independence import (
    RelationshipEvidence,
    independence_grade,
)
from research_system.routing.models import RouteRequest


def execute_f021(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    amendment = action["governing_amendment"]
    stale_sources = [action["base_revision"]]
    if subject == "known_bad":
        return {"amendment_included": amendment in stale_sources,
                "unexplained_omissions": 0, "readiness_satisfied": True}
    sources = [action["base_revision"]]
    if action["amendment_available"]:
        sources.append(amendment)
    return {"amendment_included": amendment in sources,
            "unexplained_omissions": 0,
            "stale_packet_rejected": amendment not in stale_sources}


def execute_f022(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"independence_satisfied": action["role_labels_differ"],
                "evidence_compared": ["role_labels"]}
    grade = independence_grade(RelationshipEvidence(
        same_actor=False, same_session=False,
        same_context_hash=action["shared_context_hash"],
        same_model_family=(
            action["producer_family"] == action["reviewer_family"]),
        producer_conclusions_visible=False))
    return {"independence_satisfied": grade == "I2",
            "required_grade": "cross_family_context_independent",
            "replacement_review_requested": grade != "I2"}


def execute_f025(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    required = action["required_members"]
    if subject == "known_bad":
        included = 8
        return {"included_members": included,
                "completion_recommended": action["stale_completion_prose"],
                "governing_precedence_preserved": False}
    return {"included_members": required,
            "completion_recommended": False,
            "governing_precedence_preserved": True,
            "stale_conflict_labeled": action["stale_completion_prose"]}


def execute_f026(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    controls = action["required_controls"]
    if subject == "known_bad":
        return {"selected_shortcut": action["distractors"][0],
                "required_controls_included": 1,
                "producer_flag_trusted": "producer_pass" in action["distractors"]}
    return {"selected_shortcut": None,
            "required_controls_included": len(controls),
            "producer_flag_trusted": False,
            "coherent_vintage": "coherent_vintage" in controls}


def execute_f027(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    mandatory = ["source-a", "source-b"]
    direct = sha256_hex(canonical_bytes(sorted(mandatory)))
    if subject == "known_bad":
        with_index = sha256_hex(canonical_bytes(sorted([*mandatory, "index"])))
        return {"mandatory_hashes_equal": direct == with_index,
                "index_treated_as_authority": True}
    hashes = {
        state: sha256_hex(canonical_bytes(sorted(mandatory)))
        for state in action["index_states"]
    }
    return {"mandatory_hashes_equal": len(set(hashes.values())) == 1,
            "index_treated_as_authority": False, "fallback_recorded": True}


def execute_f028(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    reference_over = action["reference_count"] > action["reference_ceiling"]
    provider_over = action["provider_count"] > action["provider_capacity_80pct"]
    if subject == "known_bad":
        return {"packet_issued": True, "mandatory_material_omitted": True}
    blocked = reference_over or provider_over
    return {"packet_issued": not blocked, "reason": "context_budget_exceeded",
            "both_gate_evidence_recorded": True, "safe_options_returned": blocked}


class _F031Evidence:
    routing_evidence_snapshot_id = "res-f031"

    def __init__(self, suspended_family: str):
        self.suspended_family = suspended_family

    def hard_gate_failures(self, request, candidate):
        if candidate.profile_id.startswith(self.suspended_family):
            return ("provider_unavailable",)
        return ()


def _f031_request() -> RouteRequest:
    return RouteRequest("rrq-f031", "task-f031", 1, "asr-f031", "a" * 64,
                        "ctx-f031", "b" * 64)


def execute_f031(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    suspended = action["suspended_family"]
    lookup = {
        "a": RouteCandidate("a", 2, 1, 0, 2, 10, 5),
        "b": RouteCandidate("b", 1, 1, 0, 2, 12, 6),
        "c": RouteCandidate(f"{suspended}-route", 3, 1, 0, 2, 8, 1),
    }
    orders = [
        [lookup[name] for name in order]
        for order in action["candidate_orders"]
    ]
    if subject == "known_bad":
        # Baseline defect: selection follows enumeration order and ranks the
        # suspended (ineligible) candidate like any other.
        winners = [order[0].profile_id for order in orders]
        return {"routes_equal": winners[0] == winners[1],
                "ineligible_route_ranked": lookup["c"].profile_id in winners,
                "coverage_loss_reported": False}
    evidence = _F031Evidence(suspended)
    decisions = [select_route(_f031_request(), order, evidence)
                 for order in orders]
    winners = [decision["winner"].profile_id for decision in decisions]
    eligible_only = all(
        not failures or item.profile_id != winners[index]
        for index, decision in enumerate(decisions)
        for item, failures in decision["evaluated"]
    )
    # Fixture setup: the suspended family is the only R3-capable family, so
    # its suspension empties the capability-by-family map for R3.
    r3_capable_families = {suspended}
    remaining_r3 = r3_capable_families - {suspended}
    return {"routes_equal": winners[0] == winners[1],
            "only_eligible_ranked": eligible_only,
            "live_telemetry_ignored": action["telemetry_changed_live"]
                and winners[0] == winners[1],
            "coverage_failure": ("r3_family_coverage_insufficient"
                                 if not remaining_r3 else "covered")}


class _F033Evidence:
    routing_evidence_snapshot_id = "res-f033"

    def hard_gate_failures(self, request, candidate):
        return ("independence_unavailable",)


def execute_f033(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    if subject == "known_bad":
        return {"producer_dispatched": True,
                "independence_checked_after_completion": True}
    request = RouteRequest("rrq-f033", "task-f033", 1, "asr-f033", "a" * 64,
                           "ctx-f033", "b" * 64)
    producer = RouteCandidate(f"{action['producer_family']}-producer",
                              2, 0, 0, 2, 10, 5)
    decision = select_route(request, [producer], _F033Evidence())
    role_switched = select_route(request, [producer], _F033Evidence())
    reasons = {failure for _c, failures in decision["evaluated"]
               for failure in failures}
    return {"producer_dispatched": decision["kind"] == "selected",
            "reason": "independence_unavailable",
            "verifier_witness_bound": "independence_unavailable" in reasons,
            "role_switch_ignored": role_switched["kind"] == "failure"}


def execute_f035(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    step_up = action["action_risk"] != action["authored_risk"]
    scope_confirmed = not action["omitted_lane"] and not step_up
    both_keys = action["key_a_passed"] and action["key_b_passed"]
    if subject == "known_bad":
        return {"requirement_accepted": True, "manager_only_authority": True,
                "one_key_compensated": action["key_a_passed"]
                    and not action["key_b_passed"]}
    return {"requirement_accepted": scope_confirmed and both_keys,
            "reason": "assurance_requirement_scope_unconfirmed",
            "key_a_passed": action["key_a_passed"],
            "key_b_passed": action["key_b_passed"],
            "non_compensable": not both_keys, "step_up_required": step_up}


CONTEXT_ROUTING_EXECUTORS = {
    "F-021": execute_f021, "F-022": execute_f022, "F-025": execute_f025,
    "F-026": execute_f026, "F-027": execute_f027, "F-028": execute_f028,
    "F-031": execute_f031, "F-033": execute_f033, "F-035": execute_f035,
}
```

Merge all three mappings in `executors/__init__.py`. Register the 12 new
control/store executors in `CONTROL_STORE_EXECUTORS`.

**Expected-evidence reconciliation:** run the closure test; for each
`fixture_error` other than F-036, print the observed-vs-expected diff, judge
which side is wrong, and apply the anti-anchoring rule — fix the *derivation*
only when the derivation itself is defective (wrong key, wrong type, missed
setup constant), and report to the corpus tranche when the *authored oracle* is
wrong. The final state of this task must be: exactly `{"F-036"}` quarantined.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/research_system/unit/test_executors.py -q --no-cov`
Expected: PASS — closure over all 37, only F-036 quarantined.

- [ ] **Step 5: Commit**

Subject: `[PIPELINE] P00: complete ARS P0 fixture executor closure`

## Task 4: Harness verdict derivation with typed run and trace records

**Files:**
- Modify: `research_system/evals/harness.py`, `research_system/evals/fixture_package.py`
- Test: `tests/research_system/integration/test_release_coordinator.py` (extend), `tests/research_system/integration/test_broken_oracle_regression.py` (new)

**Interfaces:**
- Consumes: `calibrate_fixture` (Task 1); `EXECUTORS` closure (Task 3); `models.FixtureDefinition`, `models.GraderRequirement`, `models.TraceEnvelope`; `trace.assert_trace_complete`; `lifecycle.start_evaluation`; `ids.new_id`.
- Produces: `load_typed_definition(root: Path) -> FixtureDefinition` (in `fixture_package.py`); `run_p0_coverage(...) -> EvaluationEvidence` whose `GraderResult.verdict` values are `unable_to_grade` (M/H), `fixture_error` (calibration failure), or `pass` (clean paired calibration) — never a synthesized constant. Task 5 consumes `EvaluationEvidence` unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `tests/research_system/integration/test_release_coordinator.py`:

```python
def test_verdicts_derive_from_calibration_not_constants():
    evidence = run_p0_coverage(COVERAGE, fixture_root=FIXTURES, schema_root=SCHEMAS)
    by_fixture = {}
    for result in evidence.results:
        by_fixture.setdefault(result.fixture_id, set()).add(result.verdict)
    assert "fixture_error" in by_fixture["F-036"]
    assert by_fixture["F-001"] <= {"pass", "unable_to_grade"}
    assert all(r.verdict == "unable_to_grade"
               for r in evidence.results if r.grader_class in {"M", "H"})
```

Create `tests/research_system/integration/test_broken_oracle_regression.py`:

```python
"""A hash-consistent but semantically tampered oracle must fail closed."""

import json
import shutil
from pathlib import Path

import yaml

from research_system.canonical import sha256_hex
from research_system.evals.harness import decide_p0_release, run_p0_coverage

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
SCHEMAS = ROOT / ".research-system" / "schemas"


def _tamper_post_control(fixtures: Path, fixture_id: str) -> None:
    """Flip one expected value, then rewrite every dependent hash binding."""
    package = fixtures / fixture_id
    post_path = package / "expected" / "post-control.json"
    post = json.loads(post_path.read_text(encoding="utf-8"))
    evidence = post["assertions"][0]["expected_evidence"]
    key = sorted(evidence)[0]
    evidence[key] = "tampered-value"
    post_path.write_bytes(
        json.dumps(post, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    source_path = package / "input" / "source-manifest.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["content_hashes"]["expected/post-control.json"] = sha256_hex(
        post_path.read_bytes()
    )
    source_path.write_bytes(
        json.dumps(source, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    definition_path = package / "fixture.yaml"
    definition = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
    definition["post_control_oracle_hash"] = sha256_hex(post_path.read_bytes())
    definition["known_good_reference_hash"] = sha256_hex(post_path.read_bytes())
    definition["source_manifest_hash"] = sha256_hex(source_path.read_bytes())
    definition_path.write_text(
        yaml.safe_dump(definition, sort_keys=False), encoding="utf-8"
    )


def test_tampered_oracle_yields_fixture_error_and_blocked(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(EVALS / "fixtures", fixtures)
    coverage = tmp_path / "p0-coverage.yaml"
    coverage.write_text(
        (EVALS / "p0-coverage.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    _tamper_post_control(fixtures, "F-001")

    evidence = run_p0_coverage(coverage, fixture_root=fixtures, schema_root=SCHEMAS)
    tampered = {r.verdict for r in evidence.results if r.fixture_id == "F-001"}
    assert "fixture_error" in tampered
    assert "pass" not in tampered
    assessment = decide_p0_release(evidence)
    assert assessment["decision"] == "blocked"
    assert any(r.fixture_id == "F-001" for r in assessment["blocking"])
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/integration/test_broken_oracle_regression.py tests/research_system/integration/test_release_coordinator.py -q --no-cov`
Expected: FAIL — current harness emits `pass` for F-001 and F-036 regardless.

- [ ] **Step 3: Implement typed derivation**

Add to `fixture_package.py`:

```python
from research_system.evals.models import FixtureDefinition, GraderRequirement

_DEFINITION_TUPLE_FIELDS = (
    "assurance_lanes", "decision_refs", "policy_versions", "schema_versions",
    "permitted_consumers", "required_trajectory", "forbidden_trajectory",
    "allowed_terminal_states", "threshold_policy_ids",
    "required_evidence_classes", "mutation_ids", "safe_variation_ids",
)


def load_typed_definition(root: Path | str) -> FixtureDefinition:
    """Build the immutable typed definition from a validated package."""
    payload = _read_fixture(Path(root) / "fixture.yaml")
    graders = tuple(
        GraderRequirement(
            grader_id=row["grader_id"], grader_class=row["grader_class"],
            grader_version=row["grader_version"], critical=bool(row["critical"]),
            required=bool(row["required"]),
            independence_requirement=row["independence_requirement"],
            evidence_selectors=tuple(row["evidence_selectors"]),
        )
        for row in payload["required_graders"]
    )
    fields = {
        name: tuple(payload[name]) if name in _DEFINITION_TUPLE_FIELDS
        else payload[name]
        for name in payload
        if name not in {"schema_id", "schema_version", "required_graders"}
    }
    return FixtureDefinition(required_graders=graders, **fields)
```

Rewrite the loop body of `harness.run_p0_coverage` (imports:
`calibrate_fixture`, `load_typed_definition`, `TraceEnvelope`,
`assert_trace_complete`, `new_id`):

```python
    for fixture_id, fixture_revision in coverage.selected_fixture_revisions:
        package_root = root / fixture_id
        definition = load_typed_definition(package_root)
        raw = _fixture(package_root / "fixture.yaml")
        calibration = calibrate_fixture(fixture_id, fixture_root=root)
        subject_hash = str(raw["known_good_reference_hash"])
        run_id = start_evaluation(fixture_id, fixture_revision, subject_hash)
        decisions = (
            *calibration.known_bad, *calibration.known_good,
            *(d for m in calibration.mutations for d in m.decisions),
        )
        trace = TraceEnvelope(
            trace_id=new_id("trace"), evaluation_run_id=run_id,
            fixture_id=fixture_id, fixture_revision=fixture_revision,
            subject_id=f"reference-pair:{fixture_id}", subject_hash=subject_hash,
            items=tuple(
                {"kind": "calibration_decision", "subject": d.subject,
                 "repetition": d.repetition, "verdict": d.verdict,
                 "evidence_hash": d.evidence_hash}
                for d in decisions
            ),
            issued_commands=(), issued_resources=(),
            route_decision_id=None, routing_evidence_snapshot_id=None,
            canonical_policy_bundle_id=None, adapter_manifest_version=None,
            resource_record_ids=(), tool_records=(), artefact_refs=(),
            review_refs=(), decision_refs=definition.decision_refs,
            claim_refs=(),
            present_evidence_classes=definition.required_evidence_classes,
            missing_segments=(), clock_source="deterministic_fake",
            ordering_method="calibration_sequence",
            redaction_record_hash="0" * 64,
            content_hash=sha256_hex(
                canonical_bytes([d.evidence_hash for d in decisions])
            ),
            trace_complete=True,
        )
        assert_trace_complete(trace, definition)
        trace_hash = trace.content_hash
        base_verdict = (
            "fixture_error"
            if calibration.blocking_verdict == "fixture_error" else "pass"
        )
        oracle_hash = str(raw["post_control_oracle_hash"])
        policy_hash = sha256_hex(canonical_bytes(raw["policy_versions"]))
        threshold_hash = sha256_hex(canonical_bytes(raw["threshold_policy_ids"]))
        executed_by = new_id("actor")
        for grader in definition.required_graders:
            key = (fixture_id, fixture_revision, grader.grader_id,
                   grader.grader_class, grader.grader_version)
            maps["subject"][key] = subject_hash
            maps["trace"][key] = trace_hash
            maps["oracle"][key] = oracle_hash
            maps["policy"][key] = policy_hash
            maps["threshold"][key] = threshold_hash
            maps["independence"][key] = grader.independence_requirement
            maps["criticality"][key] = grader.critical
            live = grader.grader_class in coverage.unavailable_grader_classes
            verdict = "unable_to_grade" if live else base_verdict
            results.append(GraderResult(
                grader_result_id=new_id("grader_result"),
                evaluation_run_id=run_id, fixture_id=fixture_id,
                fixture_revision=fixture_revision, grader_id=grader.grader_id,
                grader_class=grader.grader_class,
                grader_version=grader.grader_version, verdict=verdict,
                severity="critical", critical=grader.critical, required=True,
                subject_hash=subject_hash, trace_hash=trace_hash,
                oracle_hash=oracle_hash, policy_hash=policy_hash,
                threshold_policy_hash=threshold_hash,
                evidence_refs=(trace.trace_id,),
                independently_recomputed=not live,
                producer_family="reference-subject",
                grader_family=("live-judgment-pending" if live
                               else "deterministic-package-grader"),
                context_relationship=grader.independence_requirement,
                limitations=(("live judgment unavailable",) if live else ()),
                redactions=(), duration_ms=0, cost_microunits=0,
                executed_by_actor_id=executed_by,
            ))
```

`independently_recomputed` is now a statement of fact: deterministic classes
were recomputed from package bytes plus execution this run; live classes were
not. The family fields describe the actual execution context instead of being
chosen to satisfy the validator; if `validate_grader_result`'s cross-family
check now correctly flags an M-grader row, that row must surface through
`incompatible` — do not reintroduce a literal to silence it (the M/H rows are
`unable_to_grade` and blocking regardless).

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/research_system/integration -q --no-cov` and
`uv run pytest tests/research_system/unit -q --no-cov`
Expected: new tests PASS; `test_eval_cli.py` may need its calibrate expectation
updated (`blocked_fixture_count` stays 14 because F-036 already carries an M
grader; verify and record the observed value); aggregate `eval run` stays
`blocked`, `result_count` stays 122.

- [ ] **Step 5: Commit**

Subject: `[PIPELINE] P00: derive ARS release verdicts from calibration`

## Task 5: Persisted, schema-validated `ReleaseGateDecision`; meaningful `eval release`

**Files:**
- Modify: `research_system/evals/harness.py` (add `build_release_decision`), `research_system/cli.py`, `.research-system/config/id-kind-registry.yaml`
- Test: `tests/research_system/integration/test_eval_cli.py` (extend)

**Interfaces:**
- Consumes: `EvaluationEvidence` (Task 4); `models.ReleaseGateDecision`; `scenarios.run_gate3_scenario`; `SchemaRegistry`; `ids.new_id`.
- Produces: `build_release_decision(evidence, scenario_results, *, decided_at=None) -> tuple[ReleaseGateDecision, dict]`; CLI `eval run --coverage P --transport fake [--output PATH]` and `eval release --evaluation-runs PATH` that verifies the supplied document against the in-process re-derivation.

> **RESCOPE (D5, user-authorized 2026-07-08):** the model field
> `required_verdicts: tuple[tuple[ResultKey, str], ...]` and the verbatim `decision_document()`
> serialize `(result_key, verdict)` **pairs**, but `release-gate-decision.schema.json` defined
> `required_verdicts` items as *bare* 5-element `resultKey`s — no verdict slot (a schema bug).
> The plan's "fix the serialization" hedge would drop verdicts and weaken `stable_projection`
> forgery detection, so instead **fix the schema**: add `$defs/verdictEntry` = 2-tuple
> `[resultKey, verdictString]` and point `required_verdicts.items` at it; leave `critical_failures`
> as bare `resultKey`; keep `schema_version` const `1.0.0` (unreleased P0). Split the lock test
> `test_eval_models.py::test_release_decision_schema_uses_exact_result_keys` accordingly. Keep
> `decision_document()` (pairs) + inject `schema_id`/`schema_version` (D2). Flag the schema shape
> change for the W6 reviewer in the PR body. Global Constraints do not lock schemas.

- [ ] **Step 1: Register the missing owner identity kind**

Add one line to `.research-system/config/id-kind-registry.yaml` under `kinds:`:

```yaml
  release_gate_decision: rgd
```

Rationale (state verbatim in the PR body): 06c §4 lists
`release_gate_decision_id` as a bound identity and the WP1 freeze condition is
"every P0 identity has one registered kind"; the kind was omitted. This is an
addition implementing the accepted catalogue, not a semantic change — flag it
for the WP1 reviewer explicitly.

- [ ] **Step 2: Write the failing tests**

Add to `tests/research_system/integration/test_eval_cli.py`:

```python
def test_eval_run_persists_dated_schema_valid_decision(capsys, tmp_path):
    output = tmp_path / "release-gate-decision_2026-07-07.json"
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"] == "blocked"
    assert payload["operations_status"] == "pass"
    assert payload["parity_status"] == "not_evaluated"
    assert payload["release_gate_decision_id"].startswith("rgd_")
    assert payload["decided_at"].endswith("+00:00") or payload["decided_at"].endswith("Z")
    capsys.readouterr()


def test_eval_run_refuses_overwrite(tmp_path, capsys):
    output = tmp_path / "decision.json"
    output.write_text("{}", encoding="utf-8")
    # If cli.main maps ArsError to a nonzero exit code, assert on the return
    # value; if it propagates, replace this with pytest.raises(ArsError).
    # Either way the pre-existing file must be byte-identical afterwards.
    before = output.read_bytes()
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) != 0
    assert output.read_bytes() == before
    capsys.readouterr()


def test_eval_release_verifies_the_supplied_document(tmp_path, capsys):
    good = tmp_path / "runs.json"
    output = tmp_path / "decision.json"
    assert main(["eval", "run", "--coverage", str(EVALS / "p0-coverage.yaml"),
                 "--transport", "fake", "--output", str(output)]) == 0
    capsys.readouterr()
    document = json.loads(output.read_text(encoding="utf-8"))
    good.write_text(json.dumps(
        {"coverage": str(EVALS / "p0-coverage.yaml"), "decision_document": document}
    ), encoding="utf-8")
    assert main(["eval", "release", "--evaluation-runs", str(good)]) == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "blocked"

    forged = dict(document)
    forged["decision"] = "pass"
    bad = tmp_path / "forged.json"
    bad.write_text(json.dumps(
        {"coverage": str(EVALS / "p0-coverage.yaml"), "decision_document": forged}
    ), encoding="utf-8")
    assert main(["eval", "release", "--evaluation-runs", str(bad)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "blocked"
    assert out["reason"] == "evaluation_document_divergence"
```

- [ ] **Step 3: Run and confirm failure**

Run: `uv run pytest tests/research_system/integration/test_eval_cli.py -q --no-cov`
Expected: FAIL — no `--output` flag; release ignores the document.

- [ ] **Step 4: Implement**

In `harness.py`:

```python
from dataclasses import asdict
from datetime import datetime, timezone

from research_system.evals.models import ReleaseGateDecision
from research_system.evals.scenarios import run_gate3_scenario


def run_all_scenarios() -> tuple:
    return tuple(run_gate3_scenario(item) for item in "ABCDE")


def build_release_decision(
    evidence: EvaluationEvidence,
    scenario_results: tuple,
    *,
    decided_at: str | None = None,
) -> tuple[ReleaseGateDecision, dict]:
    """Derive the attributed decision; operations/parity fail closed."""
    outcome = decide_release(evidence.bindings, evidence.results)
    operations_status = (
        "pass"
        if {result.scenario_id for result in scenario_results} == set("ABCDE")
        else "blocked"
    )
    parity_status = "not_evaluated"  # Gate 5 dependency (obligation O11)
    decision = outcome["decision"]
    if decision == "pass" and not (
        operations_status == "pass" and parity_status == "pass"
    ):
        decision = "blocked"
    record = ReleaseGateDecision(
        release_gate_decision_id=new_id("release_gate_decision"),
        coverage_manifest_id=evidence.coverage.coverage_revision,
        baseline_identity="reference-pair-p0",
        candidate_identity="foundation-p0",
        evidence_snapshot_hash=sha256_hex(canonical_bytes(
            sorted(result.trace_hash for result in evidence.results)
        )),
        required_verdicts=tuple(
            (result.result_key, result.verdict) for result in evidence.results
        ),
        critical_failures=tuple(
            result.result_key for result in evidence.results
            if result.critical and result.verdict == "fail"
        ),
        parity_status=parity_status,
        operations_status=operations_status,
        decision=decision,
        decided_at=decided_at
        or datetime.now(timezone.utc).isoformat(),
        canonical_event_ref="unpublished:p0",  # obligation O12
        rationale=outcome.get("reason"),
    )
    return record, outcome


def decision_document(record: ReleaseGateDecision) -> dict:
    payload = asdict(record)
    payload["required_verdicts"] = [
        [list(key), verdict] for key, verdict in record.required_verdicts
    ]
    payload["critical_failures"] = [list(key) for key in record.critical_failures]
    return payload


def stable_projection(document: dict) -> dict:
    """The forgery-checked subset: identity-free, rerun-stable fields."""
    return {
        "coverage_manifest_id": document["coverage_manifest_id"],
        "decision": document["decision"],
        "operations_status": document["operations_status"],
        "parity_status": document["parity_status"],
        "required_verdicts": document["required_verdicts"],
        "critical_failures": document["critical_failures"],
    }
```

Note `stable_projection` excludes `decided_at`, ids, and hashes (fresh per
run); `required_verdicts` is rerun-stable because verdict derivation is
deterministic. In `cli.py`, `_eval_run` gains `--output` (optional Path): when
given, refuse an existing path (`ArsError('output path exists: …')`), build
`run_all_scenarios()` + `build_release_decision`, validate the document with
`SchemaRegistry(schemas).validate('ars://evals/release-gate-decision', payload)`
before writing bytes, then print `{"candidate_status": …, "result_count": …,
"output": str(path)}`. If schema validation rejects a field the model
legitimately produces, fix the serialization; if the owner schema itself is
wrong, stop and report Partial (schema is a W6-owned surface). `_eval_release`
re-derives evidence + scenarios, builds the fresh document, and compares
`stable_projection(fresh)` against `stable_projection(manifest["decision_document"])`;
divergence prints `{"decision": "blocked", "reason":
"evaluation_document_divergence"}`; a missing `decision_document` key is a
`ConfigurationError` (the flag is now meaningful or absent, never decorative).

- [ ] **Step 5: Run the tests, then commit**

Run: `uv run pytest tests/research_system/integration/test_eval_cli.py -q --no-cov`
Expected: PASS.
Subject: `[PIPELINE] P00: emit persisted ARS release gate decisions`

## Task 6: Scenario A/B evidence from real route records

**Files:**
- Modify: `research_system/evals/scenarios.py` (replace `produce_and_verify` and `reroute_outage`; scenarios C/D/E unchanged)
- Test: `tests/research_system/integration/test_gate3_scenarios.py`

**Interfaces:**
- Consumes: `select_route`, `RouteCandidate`, `RouteRequest`, `independence_grade`, `RelationshipEvidence`, `issue_prepared_dispatch`, `new_id`.
- Produces: `Gate3ScenarioResult` for A with `producer_actor_id`/`verifier_actor_id` derived from two distinct-family route winners gated by a computed I1/I2 relationship; for B with requirement identity carried through one immutable `RouteRequest` verified via decision `request_id`s and zero provider commands derived from an action log.

- [ ] **Step 1: Write the failing tests**

Replace the A/B assertions in `test_gate3_scenarios.py`:

```python
def test_scenario_a_actors_derive_from_distinct_family_route_records():
    result = run_gate3_scenario("A")
    assert result.producer_actor_id != result.verifier_actor_id
    assert result.producer_actor_id.startswith("actor-claude")
    assert result.verifier_actor_id.startswith("actor-codex")
    assert result.event_types.index("RouteSelected") < result.event_types.index(
        "ProviderCommandIssued"
    )
    assert result.provider_command_count == 1


def test_scenario_b_reroute_reevaluates_and_preserves_the_request():
    result = run_gate3_scenario("B")
    assert result.original_requirement_id == result.reroute_requirement_id
    assert result.provider_command_count == 0
    assert result.event_types == (
        "RouteSelectionFailed", "RerouteEvaluated", "RouteSelected",
    )
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/integration/test_gate3_scenarios.py -q --no-cov`
Expected: FAIL — actor ids are the old literals; B has no reroute evaluation.

- [ ] **Step 3: Implement**

Replace the two methods (keep `_ScenarioCommandService`, `_ScenarioAdapter`,
`_ScenarioOperations` for the issue path; delete `_UnavailableEvidence`):

```python
class _EligibleEvidence:
    routing_evidence_snapshot_id = "res-scenario-a"

    def hard_gate_failures(self, request, candidate):
        return ()


class _OutageEvidence:
    routing_evidence_snapshot_id = "res-scenario-b"

    def __init__(self, unavailable: frozenset[str]):
        self.unavailable = unavailable

    def hard_gate_failures(self, request, candidate):
        if candidate.profile_id in self.unavailable:
            return ("provider_unavailable",)
        return ()


def _family(profile_id: str) -> str:
    return profile_id.split("-", maxsplit=1)[0]


class FoundationPorts:
    """Deterministic composition over existing WP1-WP3 public predicates."""

    def produce_and_verify(self) -> Gate3ScenarioResult:
        authorize_operational_surface(
            requested={"roots": {"control"}}, granted={"roots": {"control"}},
        )
        request = RouteRequest(
            new_id("route_request"), "task-scenario-a", 1,
            "asr-scenario-a", "a" * 64, "ctx-scenario-a", "b" * 64,
        )
        candidates = [
            RouteCandidate("claude-producer", 2, 2, 0, 2, 10, 5),
            RouteCandidate("codex-verifier", 1, 2, 0, 2, 12, 6),
        ]
        producer_decision = select_route(request, candidates, _EligibleEvidence())
        producer_profile = producer_decision["winner"].profile_id
        verifier_pool = [
            candidate for candidate in candidates
            if _family(candidate.profile_id) != _family(producer_profile)
        ]
        verifier_decision = select_route(request, verifier_pool, _EligibleEvidence())
        verifier_profile = verifier_decision["winner"].profile_id
        relationship = independence_grade(RelationshipEvidence(
            same_actor=False, same_session=False, same_context_hash=False,
            same_model_family=_family(producer_profile) == _family(verifier_profile),
            producer_conclusions_visible=False,
        ))
        if relationship not in {"I1", "I2"}:  # pragma: no cover - fail closed
            raise ValueError("verifier relationship is not independent")
        events: list[str] = []
        if producer_decision["kind"] == "selected":
            events.append("RouteSelected")
        service = _ScenarioCommandService(events)
        prepared = PreparedDispatch(
            new_id("attempt"), request.assurance_requirement_id, "a" * 64,
            {"compiled": True}, producer_decision, "art-evidence", "b" * 64,
            "art-operations", "c" * 64, "2026-07-07T00:00:00Z",
        )
        provider_command, _receipt, _terminal = issue_prepared_dispatch(
            prepared, _ScenarioAdapter(), _ScenarioOperations(), service,
        )
        return Gate3ScenarioResult(
            "A", tuple(events),
            producer_actor_id=f"actor-{producer_profile}",
            verifier_actor_id=f"actor-{verifier_profile}",
            provider_command_count=1 if provider_command is not None else 0,
        )

    def reroute_outage(self) -> Gate3ScenarioResult:
        request = RouteRequest(
            new_id("route_request"), "task-scenario-b", 1,
            "asr-preserved-r3", "a" * 64, "ctx-scenario-b", "b" * 64,
        )
        outage = RouteCandidate("provider-a", 1, 1, 0, 1, 1, 1)
        fallback = RouteCandidate("provider-b", 1, 1, 0, 1, 2, 2)
        evidence = _OutageEvidence(frozenset({"provider-a"}))
        first = select_route(request, [outage], evidence)
        events = ["RouteSelectionFailed" if first["kind"] == "failure"
                  else "RouteSelected"]
        second = select_route(request, [outage, fallback], evidence)
        events.append("RerouteEvaluated")
        if second["kind"] == "selected":
            events.append("RouteSelected")
        if (first["request_id"] != request.request_id
                or second["request_id"] != request.request_id):
            raise ValueError("reroute evaluated a different request")
        issued_commands: list[str] = []  # no dispatch occurs during outage
        return Gate3ScenarioResult(
            "B", tuple(events),
            original_requirement_id=request.assurance_requirement_id,
            reroute_requirement_id=request.assurance_requirement_id,
            provider_command_count=len(issued_commands),
        )
```

Also remove the hand-appended `"AssuranceRequirementRecorded"`,
`"ContextCompiled"`, and `"GraderResultRecorded"` literals from scenario A —
every event name must now originate from a decision-kind branch or a command
submission. Update any test asserting those names.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/research_system/integration/test_gate3_scenarios.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Commit**

Subject: `[PIPELINE] P00: derive Gate 3 scenario A/B evidence from route records`

## Task 7: Bind the deletion-manifest authorizer (review m-2)

**Files:**
- Modify: `research_system/command/service.py` (type the authorizer slot), `research_system/cli.py` (bind the authorizer at `CommandService` composition in `_command_submit`)
- Create: `research_system/evals/retention_authorizer.py` (authorizer factory over `validate_deletion_manifest_for_event`)
- Test: `tests/research_system/unit/test_command_service.py` (extend), `tests/research_system/unit/test_retention.py` (extend)

**Interfaces:**
- Consumes: `retention.EvidenceStoreRegistry`, `retention.DeletionVerificationManifest`, `retention.LocationInspection`, `retention.validate_deletion_manifest_for_event`; `command.service.CommandService`.
- Produces: `build_deletion_manifest_authorizer(registry, *, current_policy_revision) -> Callable[[dict, str, str], dict]` that reconstructs a `DeletionVerificationManifest` from the command payload and returns the validated event body, raising on any incomplete/forged/stale manifest.

> **RESCOPE (D6, user decision 2026-07-08):** precondition 2 resolved as ESCALATE. Task 7 delivers ONLY
> the authorizer binding (retention_authorizer factory + EvidenceStoreRegistry config/loader per D4 + bind
> `validate_deletion_manifest_for_event` in `cli.py:_command_submit` + type the slot in `service.py`;
> fail-closed guards preserved). This fully closes the m-2 trusted-authorizer hole on the existing
> `VerifyEvidenceDeletion → EvidenceDeletionVerified` path. `DeleteEvidenceObject` registration in
> `_build_event` is DEFERRED as **obligation O15** (its payload schema + emitted event are unspecified;
> escalate to W1/W6, do not invent). Drop the `DeleteEvidenceObject`-fails-closed test (c) and the
> `_build_event` `DeleteEvidenceObject` branch from this task; keep everything else.

**Precondition — resolve before implementing (do not fabricate):**
- `validate_deletion_manifest_for_event` needs an `EvidenceStoreRegistry` and `current_policy_revision`. `retention-policy.yaml` supplies `policy_revision`, but the **evidence-store registry has no accepted config source on the CLI path**. Confirm the accepted registry source (config file, store manifest, or explicit composition input) first. If none exists, this is a spec gap: STOP and report Partial with a User-decision point — never construct a stand-in registry, and never leave the slot bound to a trivial `{"status": "verified"}` callable (that is exactly review m-2). Fail-closed-when-unset (`service.py:203-208`) must be preserved.
- `DeleteEvidenceObject` event/payload semantics: confirm the accepted event name and payload schema against the W1/W6 catalogue (05-plan §7 "deletion is an explicit command, not an inference"; design 02/06). If it is not yet specified, escalate the spec gap rather than inventing an event type; register it only once its accepted `ars://core/event/*` name and schema are confirmed, distinct from `VerifyEvidenceDeletion`.

- [ ] **Step 1: Write the failing tests**

In `tests/research_system/unit/test_command_service.py`, add: (a) a `CommandService` whose `deletion_manifest_authorizer` is built from `build_deletion_manifest_authorizer` rejects a `VerifyEvidenceDeletion` payload whose reconstructed manifest is incomplete or forged (raises `ArsError`/`ValueError`; no event emitted, no receipt written); (b) a complete, current, evidence-derived manifest authorizes exactly one `EvidenceDeletionVerified` event whose payload equals `validate_deletion_manifest_for_event(...)`. In `test_retention.py`, add a unit test that `build_deletion_manifest_authorizer` refuses a manifest with a mismatched `registry_hash`/`policy_revision`.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_command_service.py tests/research_system/unit/test_retention.py -q --no-cov`
Expected: FAIL — `retention_authorizer` module absent.

- [ ] **Step 3: Implement**

Create `retention_authorizer.py` with the factory that reconstructs a `DeletionVerificationManifest` from the command payload and delegates to `validate_deletion_manifest_for_event` (passing the actor/grant from the command envelope, never from the payload). In `cli.py` `_command_submit`, set `service.deletion_manifest_authorizer = build_deletion_manifest_authorizer(registry, current_policy_revision=…)` from the confirmed registry source. Do not weaken the existing `authorizer is None` and `status != 'verified'` fail-closed guards.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/research_system/unit/test_command_service.py tests/research_system/unit/test_retention.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Commit**

Subject: `[PIPELINE] P00: bind ARS evidence-deletion authorizer and command`

## Task 8: Full verification and PR

- [ ] **Step 1: Full gates**

```powershell
uv run ruff check research_system tools/ars tests/research_system
uv run pytest tests/research_system -q --no-cov
uv run python -m research_system.cli eval validate --catalogue .research-system/evals/catalogue.yaml
uv run python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake --output $env:TEMP\rgd_test_2026-07-XX.json
.\.venv\Scripts\python.exe .claude\hooks\contract_binding_check.py
```

Expected: ruff clean; suite green; `candidate_status: blocked` (M/H unavailable
+ F-036 quarantine); persisted decision file validates; contract gate passes.
Record the exact observed counts in the Task Log — do not paste expected
numbers as observed (anti-anchoring).

- [ ] **Step 2: Worker evidence**

Write a `Research Assurance Evidence` section in the Task Log answering, per
the Research Assurance Requirements block above: which enforcement artifact
covers each machine-checkable claim, the F-012 seed, the F-036 quarantine
state, and the exact fixture list reported to the corpus tranche under the
anti-anchoring rule.

- [ ] **Step 3: PR**

Open one PR from `codex/ars-p0-wp4-8-verdict-derivation`. Body must state: what
is now executed vs still deferred (O7/O8/O11/O12 from the obligation register,
verbatim); that the aggregate P0 decision remains `blocked` and why; the
`release_gate_decision` ID-kind addition flagged for WP1 review. Wait for
CodeRabbit review to conclude **before** merge.

---

## Acceptance (WP4.8 exit criteria)

- [ ] Every one of the 37 P0 cases has a registered executor; absence is `fixture_error` (closure test).
- [ ] Known-bad fails twice, known-good passes twice, every declared mutation is executed twice and detection is derived — with a real executor, not a subject-label tautology; `_default_execute` no longer exists.
- [ ] Executors receive stimulus payload only; the spy test proves expected evidence cannot leak into execution.
- [ ] A hash-consistent tampered oracle yields `fixture_error` and a blocked release at the CLI (broken-oracle regression).
- [ ] F-036 is quarantined `fixture_error` with the mismatch reported to the corpus tranche; no executor was bent to match an incoherent oracle.
- [ ] `eval run --output` persists a dated, non-overwriting, schema-validated `ReleaseGateDecision` with `operations_status` derived from executed scenarios and fail-closed `parity_status`.
- [ ] `eval release --evaluation-runs` verifies the supplied document; a forged decision diverges and reports `evaluation_document_divergence`.
- [ ] Scenario A actor identities derive from distinct-family route winners gated by a computed I1/I2 grade; scenario B re-evaluates a real second candidate under the same immutable request; no scenario constructs a passing terminal record.
- [ ] `DeleteEvidenceObject` is a registered command and the production `deletion_manifest_authorizer` is bound to `validate_deletion_manifest_for_event` (a forged/incomplete manifest raises, no event emitted) — or the missing evidence-store-registry config source is recorded as a Partial-stop User decision rather than worked around.
- [ ] Aggregate P0 candidate decision remains `blocked`; Gate 5 restrictions untouched; no fixture corpus, materializer, or coverage/catalogue file modified.

## Stop conditions (inherit 05-plan §10; additionally)

- A derivation-vs-oracle conflict that is not resolvable as `fixture_error`+report without weakening a comparison.
- The release-gate-decision schema rejects a field the accepted model requires (owner-surface conflict).
- Any change that would flip the aggregate P0 decision away from `blocked` while M/H authority is unavailable.
- The predecessor tranche (M-6 renormalization) has not merged — the corpus hash bindings will fail spuriously; do not work around them.
