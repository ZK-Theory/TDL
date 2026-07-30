# KAN-64 scope analysis: the runtime is red for two reasons, not one

**Created:** 2026-07-30
**For:** Stephen (owner decision on KAN-64 scope)
**Base evaluated:** `origin/main` at `9045d78`
**Status of every claim below:** reproduced on the current checkout or read from source/git, not inferred.
**Ticket:** KAN-64 — "WP6.1 runtime currency: emit `command_schema_*` on every event (producer-side)"

## Why this document exists

KAN-64's owner decision is that the runtime producer emits three fields
(`command_schema_id`, `command_schema_version`, `command_schema_sha256`) and the
generated schemas stay as they are. That decision was made from handoff 26's
Defect 3, which quoted the failure as **only** the three missing-field errors.

The live failure surface on `main` has **two independent errors**, not one. The
second — a payload-model mismatch — was not in the quoted snippet, and it means
the three-field fix cannot turn the unit/integration suites green on its own.
This changes what KAN-64 actually is, so it is worth your decision before any
code is written.

## The verified facts

**1. The date-time prerequisite is already merged.** `research_system/schema_registry.py:33-38`
on `main` returns `True` for non-strings — the exact fix handoff 26 called
Defect 2. So the real failure surface is now visible, not masked.

**2. The failures reproduce exactly.** `tests/research_system/unit/test_command_service.py`:
**10 failed, 7 passed** (~101s), matching the ticket's prediction.

**3. The live error carries two independent validation failures.** From a real run,
`test_persisted_receipt_matches_frozen_schema` and the other nine:

```
ars://core/event/TaskCreated: 'command_schema_id' is a required property;
                              'command_schema_version' is a required property;
                              'command_schema_sha256' is a required property;
payload: {'title': 'A'} is not valid under any of the given schemas
```

The first three are the ticket's target. The fourth — `payload ... is not valid`
— is separate, and it is not in handoff 26's quoted snippet.

**4. The mechanism: proposed schemas leaked into the runtime validation path.**
Commit `3ec14eb "Split WP6.1 event schemas for review"` added 86 schemas tagged
`x-lifecycle: proposed_materialized` under `.research-system/schemas/core/events/`,
each with `$id: ars://core/event/{EventType}`. Verified via git: **before that
commit no `ars://core/event/TaskCreated` `$id` existed anywhere** in
`.research-system/`.

- `bundled_schema_registry()` (`schema_registry.py:161`) loads that directory
  recursively (`root.rglob("*.schema.json")`).
- `EventLedger.append` validates each event against its per-event schema **only
  when the registry already contains it**: `if event_type == "ReleaseGateDecisionPublished"
  or self.schemas.contains(event_schema): self.schemas.validate(event_schema, ...)`
  (`ledger.py:342, 349`).
- So the split flipped `contains("ars://core/event/TaskCreated")` from False to
  True, and the runtime began enforcing **proposed** schemas against **live**
  events. Before the split the guard was inert and the suite was green.

**5. The proposed schemas demand a payload model the runtime does not build.**
The generated schemas require rich, structured payloads. The runtime `_build_event`
(`command/service.py:831-893`) passes the command payload through nearly verbatim.
Examples, read from the generated schema files:

| Event | Proposed schema requires (payload) | Runtime actually emits |
|---|---|---|
| `TaskCreated` | `{new_task_id, definition}` — `definition` is a 36-field object | the command payload verbatim (e.g. `{'title': 'A'}`) |
| `DispatchClaimed` | `dispatch_id, task_id, task_revision, lease_id, expected_dispatch_stream_version, expected_task_stream_version, expected_global_position, expected_tail_hash, declared_write_set` | `{'attempt_id': ...}` |
| `AttemptCreated` | `task_id, task_revision, attempt_ordinal, execution_epoch, new_attempt_id, dispatch_id, creation_kind` | (analogous minimal payload) |

Adding `command_schema_*` removes three of the four errors per event. The
payload-shape error remains, and it keeps the same tests red.

**6. Why the gates never caught this.** The commit-time contract gate and the
741-test contracts suite both validate the **materialization** of these schemas
(that the generator produces them correctly), never the runtime **append** path
that has to satisfy them. Handoff 26 names this blind spot; it is also why a
"for review" split could silently change runtime behaviour.

## The fork

The same evidence supports two coherent readings, and they differ by roughly an
order of magnitude in scope.

### Reading A — the runtime grows into the proposed schemas (the ticket)

The proposed schemas are the target; the runtime must conform. Emitting
`command_schema_*` is step one. Step two — **not in the ticket** — is building
the full proposed payload model for every core event type: rich `definition`
objects, `declared_write_set`, `expected_tail_hash`, `creation_kind`, and so on,
across ~86 event types, plus the command payloads that feed them and every
fixture. Until that migration lands, the unit/integration suites stay red.

- **Faithful to** the owner decision as stated ("schemas stay as they are").
- **Cost:** large. A runtime event-model migration, not a three-field change.
- **Greens the suite:** no, not until the payload migration is also done.
- **KAN-64 under this reading:** deliver the three fields + binding test +
  back-compat answer, then **document the payload mismatch as a separate defect**
  and leave those tests red-but-attributed — which KAN-64's own acceptance
  permits ("green **or** every remaining failure attributed to a different
  documented defect"). The payload defect is currently undocumented; this reading
  makes documenting it part of the deliverable.

### Reading B — the "for review" schemas should not gate live events yet

The regression is that proposed schemas entered the runtime registry. A schema
split "for review" is, by its own label, not yet the active contract. Give the
runtime registry (or the ledger's `contains()` gate) a lifecycle boundary that
excludes `x-lifecycle: proposed_materialized` schemas, ship a negative control,
and the runtime stops enforcing proposals against live events.

- **Cost:** small and targeted.
- **Greens the suite:** the failures caused by *this* enforcement, yes — but see
  the honesty note below.
- **Provenance is not lost:** `command_schema_*` can still be added as the good
  invariant it is (Reading A's step one), independently of whether the full
  proposed schemas gate the runtime.
- **Diverges from** the owner's stated direction, which leaned toward A.

**Honesty note on "greens the suite."** Nobody has seen `tests/research_system`
finish (handoff 26: 1515 tests, did not complete in 2 hours; Defect 1 is an
unfixed N+1 in `fixture_package.py`). Reading B clears the schema-enforcement
failures in `test_command_service.py` / `test_adapter_parity.py`; it does **not**
prove the whole directory is green. I have not run the full suite and will not
claim it passes.

## The one point both readings share

`command_schema_*` provenance is worth having regardless of the fork. The owner's
rationale holds: every persisted event becomes self-describing about the command
contract it was produced under, which makes replay and audit verifiable rather
than assumed. Reading A requires it; Reading B is compatible with it. So the
provenance work is not wasted under either choice — only the payload question
differs.

## What the owner's "never relax a generated schema" did and did not settle

The locked rule — "never relax a generated schema to make a suite green when the
requirement encodes provenance" — was reasoned entirely about `command_schema_*`
provenance. Whether it extends to the **payload model** (i.e. whether the runtime
must adopt the full proposed payloads, or whether those payloads are a proposal
still under review) is a separate question the rule does not answer, and it is
the crux of the A/B fork.

## What I recommend you decide

1. **A or B** — does the runtime grow into the proposed schemas (A), or do the
   for-review schemas stop gating live events until scheduled (B)?
2. Either way, I proceed to add `command_schema_*` provenance (from the
   `ars://core/command` identity the command was actually validated against),
   with a binding test that re-derives the identity from the registry rather than
   asserting a literal, and a written back-compat answer.
3. If A: I also document the payload-model mismatch as a distinct defect so the
   remaining red is attributed, per KAN-64's acceptance.

I have not written any code or changed any schema. This document is uncommitted.

## Sensitive information

No credentials, tokens, provider session data, or private research data are
included.
