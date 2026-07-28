# Briefing: `tests/research_system` is red on `main` — three separate defects

**Created:** 2026-07-28
**For:** the agent working the N+1 `SchemaRegistry` repair
**Tree investigated:** `449b0d002edea3013dcc32a115f1870c4a082974` (`origin/main`, PR #173 merge)
**Status of every claim below:** reproduced on an unmodified detached worktree at that commit, not inferred.

## Read this first

The `tests/research_system` unit and integration suites are **already failing on
`main`** before you change anything. If you fix the N+1 and the suite is still
red, that is not your regression. Establish this baseline before you start so
you are not chasing someone else's bug.

Baseline was confirmed by running the identical command in two worktrees — one
with unrelated changes, one detached at `449b0d00` — and diffing the output.
The progress lines were **byte-identical**.

## Environment — this matters more than usual

`uv run` fails in a fresh worktree building `petls` (CMake cannot find Boost).
Invoke the venv interpreter directly:

```bash
C:/Users/steph/TDL/.venv/Scripts/python.exe -m pytest -q tests/research_system -o "addopts=" -p no:cacheprovider -p no:cov
```

That venv is sound: pytest, jsonschema, yaml, POT, gudhi all present, and
`research_system` resolves from the worktree (cwd on `sys.path`), not the main
repo. `hypothesis`, `freezegun` and `responses` are absent but nothing imports
them.

**Timing, so silence does not look like a hang.** `pytest -q` flushes one line
per 72 tests. Tests here average ~9s, so the first progress line takes ~11
minutes. Budget: contracts 741 tests / ~11 min; the whole directory is 1515
tests and did not finish in 2 hours.

## Defect 1 — the N+1 you are already fixing

`research_system/evals/fixture_package.py:170` constructs a fresh
`SchemaRegistry(Path(schema_root))` inside `validate_fixture_package`.
`research_system/evals/coverage.py:132` calls it in a loop over the 40
`FOUNDATION_CASES`.

Measured on this tree:

- 270 `*.schema.json` files under `.research-system/schemas`
- one `SchemaRegistry()` construction = **3.15s** (`check_schema` on all 270)
- 40 rebuilds = **~126s** of pure redundant meta-schema validation

The observed cost is far worse than 126s.
`tests/research_system/unit/test_release_publication.py::test_release_event_has_a_strict_full_registered_contract`
spends **35+ minutes** inside a single `run_p0_coverage` call. Four consecutive
py-spy samples all landed inside jsonschema `ref` / `allOf` / `dynamicRef`
descent. The extra cost is the **reference-resolution cache being discarded 40
times** — each new registry starts cold, so every `$ref` and `$dynamicRef` in
the fixture documents is re-resolved from scratch on every iteration. Caching
the registry recovers that, not just the 126s.

Note there is already an `lru_cache`d `bundled_schema_registry()` at
`schema_registry.py:126` — but it is pinned to the checkout's own schema root
and takes no argument, so it cannot serve callers that pass an explicit
`schema_root`. Whatever you add should key on the root path.

## Defect 2 — the date-time fallback rejects null (in your file)

`research_system/schema_registry.py:31`:

```python
def _is_rfc3339_date_time(value: object) -> bool:
    if not isinstance(value, str) or _RFC3339_DATE_TIME.fullmatch(value) is None:
        return False
```

It returns `False` for non-strings. Per the JSON Schema spec — and per
jsonschema's own built-in `is_datetime`, which does `if not isinstance(instance,
str): return True` — `format` **must be ignored** for instance types it does not
apply to. The correct fallback returns `True` for non-strings.

This matters because schemas legitimately allow null:

```json
"occurred_at": {"type": ["string", "null"], "format": "date-time"}
```

Proof, on this tree:

```
after importing research_system.schema_registry:
  conforms(None, 'date-time') -> False     # must be True
  conforms('2026-07-28T00:00:00Z') -> True
```

**Why nobody has reported it.** Line 43 installs the fallback *only if* jsonschema
has no `date-time` checker of its own, and jsonschema registers one only when
`rfc3339-validator` is installed. That package is **absent** from this venv, so
the buggy fallback is live here and dormant on any machine that has it. Same
shape as the earlier CRLF/LF problem: a dependency-conditional gate that is green
on one machine and red on another.

**Verified fix** (two lines, confirmed to change behaviour):

```python
    if not isinstance(value, str):
        return True
    if _RFC3339_DATE_TIME.fullmatch(value) is None:
        return False
```

With this applied, `test_command_service.py` goes from **16 failed** to
**7 passed / 10 failed** — real progress, but not sufficient, because of
Defect 3. The fix was verified and then reverted; it is not committed anywhere.

**Take this one.** It is in `schema_registry.py`, the file you are already
editing. Two agents touching it separately will conflict.

## Defect 3 — 86 generated event schemas require fields the runtime never emits

This is the larger one and it is **not** yours to fix. It is recorded here so
you do not mistake it for fallout from your change.

After Defect 2 is fixed, the remaining failures surface as:

```
ars://core/event/TaskCreated: 'command_schema_id' is a required property;
                              'command_schema_version' is a required property;
                              'command_schema_sha256' is a required property
```

Facts established:

- `.research-system/schemas/core/events/` holds **86 generated event schemas**;
  **88 files repo-wide** require `command_schema_sha256`.
- `.research-system/schemas/core/events/task_created.schema.json` carries
  `$id: ars://core/event/TaskCreated` and lists all three `command_schema_*`
  fields as `required`.
- **No production code emits them.** `grep -rn "command_schema_id" --include=*.py
  research_system` returns nothing. The only Python referencing these fields is
  the WP6.1 materialization test and oracle machinery under
  `tests/research_system/contracts/`.
- Provenance: `3ec14eb [PIPELINE] P00: Split WP6.1 event schemas for review`.

So WP6.1 schema materialization landed a stricter event-schema family ahead of
the runtime that has to satisfy it. `CommandService.submit` →
`ledger.append` → `SchemaRegistry.validate` fails against the generated schema.

The contracts suite is green (741 passed) because it validates the
materialization itself, not the runtime append path — which is exactly why this
went unnoticed.

**This is a WP6.1 currency gap.** The WP6.3 handoff packets already flag that
KAN-54's `Done` covers the D-G6-3 precheck only, not broader runtime completion.
This is that gap, now concrete and reproducible.

### Resolved 2026-07-28 — producer emits

**Owner decision: the producer emits the fields. The generated schemas are
correct and stay as they are.**

The runtime event producer must populate `command_schema_id`,
`command_schema_version` and `command_schema_sha256` on every emitted event, from
the identity of the command schema that validated the originating command. The
path is `CommandService.submit` → `ledger.append` → `SchemaRegistry.validate`.

This is the right direction on the merits, not just the one that makes the suite
green. The requirement encodes real provenance: every persisted event becomes
self-describing about the command contract it was produced under, which is what
makes replay and audit verifiable rather than assumed. Relaxing the 86 schemas
would discard that provenance permanently and silently — precisely the class of
loss this programme's content-addressing work exists to prevent.

**Open sub-questions for whoever takes this**, to be answered rather than
assumed:

- **Back-compatibility.** Events already persisted lack these fields. Decide
  whether existing streams are migrated, grandfathered by a schema version
  boundary, or whether no durable store predates the change. Do not assume the
  last without checking.
- **Source of the sha256.** Whether it hashes the command schema's raw bytes or
  its canonical form, and whether it resolves through the existing registry or a
  pinned manifest. It must match whatever the WP6.1 materialization oracle
  already assumes, since the generated schemas came from there.
- **Fixture and test-helper updates.** Every helper constructing an event
  envelope needs the new fields, including `execute_s009` in
  `research_system/evals/executors/control_store.py`.

Note this is strictly downstream of **Defect 2** — until the date-time fallback
is fixed, the `occurred_at` error masks these errors and you will not see the
real failure surface.

## Failure inventory

Positions map to collection order, `--ignore=tests/research_system/unit/test_release_publication.py`.

| Tests | Module | Symptom |
|---|---|---|
| 1–16 (all) | `test_adapter_parity.py` | ERROR in setup — Defect 2, then Defect 3 |
| 59–74 (all) | `test_command_service.py` | FAILED — Defect 2, then Defect 3 |
| beyond 74 | not yet enumerated | the full run has never completed |

The inventory past test 74 is **unknown**. Nobody has seen this suite finish.
Establishing the complete list is worth doing once your fix makes a full run
affordable — that is arguably the biggest single benefit of the N+1 repair.

## Do not touch

`.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml` and
`.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`
are owner-accepted at exact bytes at `449b0d00`. Editing either breaks that
acceptance and forces a fresh independent review.
