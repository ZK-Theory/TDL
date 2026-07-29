# 06h: WP6.1 Schema Identity and Artefact Command Seam Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. Write one failing
> public-seam test before each production change. Read
> `../handoffs/26-research-system-suite-red-briefing.md` (defect briefing),
> `../handoffs/28-research-system-suite-baseline-inventory.md` (measured
> baseline) and `../reviews/adversarial-rm-lane-plan-suite-review-2026-07-29.md`
> §C-1/§C-3 in full before starting. This plan exists because that review
> proved the previous approach could not be executed.

**Status:** PROPOSED — **main-path WP6.1 work, not RM lane work.** Dispatch
blocked on owner gates G-RM-8, G-RM-9, G-RM-10 (rm-00 §3) and on an independent
adversarial review of this plan.
**Created:** 2026-07-29
**Supersedes:** RM-01 Task A (the producer-emits repair), which this plan
absorbs. RM-01 retains only suite recovery.
**Goal:** Close the WP6.1 runtime/specification currency gap at its root: make
registered schema identity retrievable as exact bytes, make every command
producer emit truthful schema identity, and wire the accepted artefact command
family through command, ledger and replay so that append-only artefact records
are authoritatively producible and deterministically replayable.
**Owner authorization:** P-043 (producer emits, accepted 2026-07-28) for Tasks
1-2. Task 3 additionally requires G-RM-10.

## Why this plan exists

Handoff 26 recorded three defects. Two were fixed. The third — 86 generated
event schemas requiring `command_schema_id`, `command_schema_version` and
`command_schema_sha256` that no producer emits — was assigned to RM-01. The
2026-07-29 adversarial review proved that assignment unexecutable and, in doing
so, exposed a larger fact.

The gap is not "one missing producer field". It is that the WP6.1 **runtime**
implements a fraction of the WP6.1 **accepted surface**:

| Accepted surface | Runtime state |
|---|---|
| 86 command schemas under `.research-system/schemas/core/commands/`, all `x-lifecycle: proposed_materialized` | `CommandService._build_event` handles **6** command types and raises `unsupported command type` for the rest (`research_system/command/service.py:831-893`) |
| 86 event schemas under `.research-system/schemas/core/events/`, each requiring the `command_schema_*` triple | No producer emits any of the three fields (handoff 26 Defect 3; 156 failing cases in handoff 28) |
| `ars://core/command/RegisterArtefact`, `SetArtefactUseAuthority`, `SupersedeArtefact`, `RecordScientificReview`, `RecordStructuralValidation` | none wired |
| `ars://core/command`'s `target_stream_id` already admits `art_`; `artefact: art` registered in `.research-system/config/id-kind-registry.yaml` | no artefact stream reachable through the command path |
| P-043: the digest is of "the exact schema bytes used for that validation — never of a reserialized or reconstructed representation" | `SchemaRegistry` stores only `json.loads(...)` output; raw bytes and `source_path` are discarded at construction (`research_system/schema_registry.py:63-73`) |

Three consumers are blocked behind this one seam: the failing suite (RM-01),
any append-only artefact record (RM-03), and P-043 itself. Fixing it in one
reviewed place is cheaper and safer than three partial workarounds, and it is
the only place where editing `schema_registry.py` is in scope.

## Architecture

**The generated schemas are the accepted, stricter authority; the runtime rises
to meet them.** Nothing in this plan relaxes a schema.

Three seams, in dependency order:

1. **Schema identity.** `SchemaRegistry` gains an immutable `RegisteredSchema`
   record carrying `schema_id`, `schema_version`, `source_path`, the exact
   `raw_bytes` read from disk, and `raw_bytes_sha256` computed over those same
   bytes. `validate()` resolves through that record. The producer consumes the
   **same instance** `validate()` used — not a second lookup, not a re-read.
   This is what makes P-043's byte-exactness true rather than asserted, and it
   closes the time-of-check/time-of-use seam the review identified.

2. **Producer truthfulness.** Command submission derives the triple from the
   `RegisteredSchema` actually used to validate the command, at the single
   point every producer flows through. Never caller-supplied, never
   hard-coded, never per-event-type special-cased.

3. **Artefact command family.** `RegisterArtefact` and
   `SetArtefactUseAuthority` are wired end to end: command validation →
   `_build_event` → ledger append → pure replay reducer → projection. These
   two are chosen because they are the minimum pair that makes an artefact
   *exist* and makes its *use authority* transition — together they are the
   accepted mechanism the RM lane needs, and W2's own answer to "how does
   candidate material become admissible evidence".

**Deliberately out of scope:** the other 78 unwired command types. This plan
proves the pattern on two and leaves a documented path; a sweep is separate
reviewed work.

## Global constraints

- All standing constraints of `rm-00-research-methods-lane-master-plan.md` §5
  apply **except** §5.6 (assurance lanes — see below) and the RM-lane naming
  rule, which is an RM convention and not binding on main-path WP6.1 work.
- Branch `pipe/wp6-1-schema-identity-seam` from approved `main`, in a worktree
  under `.apm/worktrees/`, with `.env` copied immediately.
- **Environment.** A fresh worktree `.venv` is an empty stub and the main-repo
  interpreter lacks `jsonschema`. Provision with
  `uv sync --all-extras --no-install-package petls`, then run pytest as
  `uv run --no-sync python -m pytest -q <target> -o "addopts=" -p no:cacheprovider -p no:cov`.
  Do not pipe long background runs through `tail` — output buffers until exit.
- **Do not modify** any file under `.research-system/schemas/core/events/` or
  `.research-system/schemas/core/commands/`. The generated schemas are the
  fixed target. If a generated schema proves genuinely defective rather than
  merely strict, **stop Partial and escalate** — do not relax it.
- **Do not modify** the WP6.3 accepted-byte files
  (`.research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml`,
  `.research-system/schemas/contracts/wp6-3-tdl-private-assurance-pack.schema.json`)
  or anything under `.research-system/schemas/wp6-2-*/**`.
- No CLI surface, no provider-related code, no eval-corpus change. The P0
  invariants (37 fixtures / 14 blocked / 122 results / candidate blocked) are
  untouched; if any task moves them, stop Partial.

## File map

**Modify (Task 1):**

~~~text
research_system/schema_registry.py                      # RegisteredSchema; validate() through it
tests/research_system/unit/test_schema_registry.py
~~~

**Modify (Task 2):**

~~~text
research_system/command/service.py                      # single derivation point
research_system/store/ledger.py                         # only if envelope assembly lives here
tests/research_system/unit/test_command_service.py
~~~

**Modify (Task 3):**

~~~text
research_system/command/service.py                      # _build_event: two accepted command types
research_system/projection/replay.py                    # reducers for the two artefact events
tests/research_system/unit/test_command_service.py
tests/research_system/unit/test_replay.py
~~~

**Create (Task 3):**

~~~text
tests/research_system/integration/test_artefact_command_seam.py
~~~

The Task 2 file map is the *expected* seam (handoff 26 names
`CommandService.submit` → `ledger.append`). First action of Task 2 is to
confirm where the envelope is actually assembled. If assembly happens outside
`research_system/command/` + `research_system/store/`, report the actual seam
in the PR and stop Partial rather than widening scope silently.

`test_schema_registry.py` and `test_replay.py` are flagged by Repowise as
high-change-entropy files. Read `get_risk` before editing them.

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| H-1 | P-043 (03-decisions) | Digest is of the exact validated schema bytes, never a reserialization; independent recomputation from the schema file must reproduce it | Task 1 + Task 2 binding test |
| H-2 | Review C-1 | `validate()` and the producer must consume the *same* `RegisteredSchema` instance (no second lookup, no re-read) | Task 1 interface; Task 2 test asserts instance identity |
| H-3 | Review C-1 / handoff 26 §"existing events" | Events already durably stored lack the triple; a migrate / grandfather / no-prior-store decision is required and must be recorded | **G-RM-8** — owner decision; Task 2 blocked on it |
| H-4 | handoff 26 | 88 files repo-wide require `command_schema_sha256`; every producing path must be covered, including direct-append, T2 and internal paths | Task 2 Step 3 sweep; Task 4 matrix |
| H-5 | Review C-3 / W2 §16 | Artefact records must be authoritatively producible and deterministically replayable through accepted interfaces | Task 3 |
| H-6 | W2 §§8, 16.2 | Authority, expected-version, idempotency and state-transition validation precede any write; replay reducers are pure and versioned | Task 3; reducer purity test |
| H-7 | Review C-3 | Direct `ledger.append` must not be able to manufacture artefact events outside command authority | Task 3 negative control (direct-append bypass) |
| H-8 | Review §"Coverage and fixture gaps" 1 | TOCTOU substitution and valid-but-wrong-identity-triple fixtures | Task 1/2 negative controls |
| H-9 | Review §"Coverage and fixture gaps" 3 | Unknown-family, unknown-major, reducer-absence, genesis and incremental replay fixtures | Task 3 |
| H-10 | Vault discipline | `[PIPELINE]` entry in `04-Methods/Pipeline-Overview.md` | Close-out |
| H-11 | Observer log Obs. 136 | README status drift when acceptance records land | Close-out: README row updated in the same PR |

## Research assurance requirements

- **Lanes:** Output/Provenance **and** provenance-integrity. No mathematical,
  statistical, topological or representation logic is created or altered; any
  task finding itself in such logic stops Partial. (RM-00 §5.6's blanket
  "Output/Provenance only" is replaced here because schema identity *is* the
  provenance substrate other lanes' claims rest on.)
- **Machine-checkable claims:**
  - **byte-exactness** — the emitted `command_schema_sha256` equals a digest
    the test computes independently by reading the schema file's bytes;
  - **instance identity** — the record the producer reads is the record
    `validate()` used (asserted directly, not inferred from equal values);
  - **TOCTOU resistance** — mutating the schema file on disk after registry
    construction does not change the emitted digest, and the emitted digest
    still matches the bytes actually validated against;
  - **fail-closed** — a command whose schema is unregistered fails at submit
    rather than appending an event with absent or null identity fields;
  - **no caller override** — a submitted payload supplying `command_schema_*`
    values is rejected in favour of registry-derived values;
  - **valid-but-wrong** — a syntactically valid triple naming a *different*
    registered schema is rejected, not accepted because it parses;
  - **authority** — an artefact event cannot be produced by direct
    `ledger.append` outside the command path;
  - **replay determinism** — genesis and incremental replay of a stream
    containing both artefact events reproduce identical projection state.
- **Human-review-only:** does the derivation sit at the single point every
  producer flows through, or does it patch the paths the tests happen to
  exercise? Is `RegisteredSchema` immutable in fact, or merely by convention?
- **Partial criteria:** generated-schema defect discovered; envelope seam
  outside command/store; any P0 invariant drift; retaining raw bytes proves
  memory-prohibitive at the real schema-tree size (measure before concluding);
  the artefact reducers require projection-state shape changes beyond additive.

## Task 1: Exact-byte schema identity (blocked on G-RM-9)

- [ ] **Step 1 — Failing test.** In `test_schema_registry.py`, assert that a
  registry exposes, for a known `$id`, a record whose `raw_bytes_sha256` equals
  an independently computed SHA-256 of that schema file's bytes, and whose
  `source_path` resolves to that file. Red — no such interface exists.
- [ ] **Step 2 — Run red.**

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_schema_registry.py -o "addopts=" -p no:cacheprovider -p no:cov
~~~

- [ ] **Step 3 — Implement.** Introduce a frozen `RegisteredSchema`
  (`schema_id`, `schema_version`, `source_path`, `raw_bytes`,
  `raw_bytes_sha256`, `parsed`). Read bytes once; parse from those exact bytes;
  digest those exact bytes. Store the record in `_schemas`. `validate()`
  resolves the record and validates against `record.parsed`. `contains()`
  unchanged in behaviour. Keep the existing `lru_cache` sharing semantics —
  measure the memory delta across the full schema tree and record it in the PR.
- [ ] **Step 4 — Negative controls.** (a) mutate the schema file on disk after
  construction → digest and validation behaviour unchanged (TOCTOU); (b) a
  registry built over a tree containing a byte-identical duplicate `$id` still
  raises `duplicate schema`; (c) `RegisteredSchema` mutation attempt raises.
- [ ] **Step 5 — Commit.** `[PIPELINE] P00: retain exact schema bytes and source path in the registry (P-043)`.

## Task 2: Producer emits command-schema identity (blocked on G-RM-8)

- [ ] **Pre-step — record the G-RM-8 decision** in the PR description and in
  the plan close-out: migrate existing events, grandfather them behind a
  documented predicate, or assert no prior durable store exists. If the
  decision is "migrate", the migration and its replay fixture are in scope
  here; if "grandfather", the predicate and its negative control are in scope;
  if "no prior store", the assertion needs evidence, not assumption.
- [ ] **Step 1 — Failing public-seam test.** In `test_command_service.py`,
  submit a valid command through the real `CommandService` and assert (a) the
  appended event validates against its generated schema
  (`ars://core/event/TaskCreated` at minimum), (b) `command_schema_sha256`
  matches an independently recomputed hash of the command schema file, and
  (c) the record consulted is the same instance `validate()` used. Must fail on
  `main` with the three-required-properties error quoted in handoff 26. A
  collection error is not the required red.
- [ ] **Step 2 — Run red** (worktree venv provisioned per Global constraints).
- [ ] **Step 3 — Implement minimally.** Derive the triple at submit time from
  the `RegisteredSchema` used for command validation. Sweep every
  event-producing call site (`grep -rn "ledger.append"` plus any event-factory
  helpers) and route all of them through the single derivation point. Do not
  special-case event types. Where a producer legitimately has no originating
  command (internal/system appends), do **not** fabricate command provenance —
  report the path and its correct disposition in the PR; inventing a false
  command identity is worse than the current absent one.
- [ ] **Step 4 — Negative controls.** Caller-supplied triple rejected;
  valid-but-wrong triple (naming a different registered schema) rejected;
  unregistered schema fails at submit without appending.
- [ ] **Step 5 — Green + no-regression slice.** Re-run Step 2's target plus
  `tests/research_system/unit/test_adapter_parity.py` (handoff 26 attributes
  its 16 setup errors to Defects 2→3; it should now collect and run). Record
  results either way.
- [ ] **Step 6 — Commit.** `[PIPELINE] P00: emit command-schema identity on every append path (P-043)`.

## Task 3: Wire the accepted artefact command family (blocked on G-RM-10)

- [ ] **Step 1 — Failing test.** `test_artefact_command_seam.py`: submit
  `RegisterArtefact` with a schema-valid manifest through the real
  `CommandService`; assert an `ars://core/event/ArtefactRegistered` event is
  appended, validates against its generated schema, and carries the Task 2
  identity triple. Red with `unsupported command type: RegisterArtefact`.
- [ ] **Step 2 — Implement `RegisterArtefact`.** Extend `_build_event` for the
  accepted command type. Honour W2 §8 ordering: authority, expected version,
  idempotency and state-transition validation precede the write. Write the
  artefact object through the existing `ObjectStore` seam, mirroring the
  `CreateTask` pattern. Do not invent payload fields — the accepted
  `ars://core/command/RegisterArtefact` payload schema is the contract.
- [ ] **Step 3 — Implement `SetArtefactUseAuthority`.** Same seam. Enforce the
  accepted `use_authority` enum
  (`candidate | accepted_for_scope | rejected | superseded | restricted`) as a
  *state transition*, not a field write: define and test which transitions are
  legal, and reject the rest. `subject_sha256` must match the registered
  artefact's `content_sha256` or the command is rejected — this is what makes
  the transition bind to exact bytes rather than to an identifier.
- [ ] **Step 4 — Replay reducers.** Add pure, versioned reducers for both
  events in `replay.py`. Both event `schema_id`s are already under
  `ars://core/event/`, so the existing prefix admission needs no change —
  confirm this rather than assuming it, and if the admission check needs
  widening, stop Partial and report (that would be a core-routing change).
- [ ] **Step 5 — Negative controls (all required).** (a) direct `ledger.append`
  of an artefact event outside the command path is rejected or provably cannot
  produce authoritative state; (b) unknown command type still raises;
  (c) unknown major version raises; (d) a missing reducer raises rather than
  silently no-ops; (e) genesis replay and incremental replay produce identical
  state; (f) an illegal use-authority transition is rejected; (g) a
  `subject_sha256` mismatch is rejected.
- [ ] **Step 6 — Commit.** `[PIPELINE] P00: wire the accepted artefact command family through command, ledger and replay`.

## Task 4: Producer coverage matrix

- [ ] Record, as a table in the PR description and in the close-out note, every
  event-producing path found in Task 2's sweep, with its disposition: routed
  through the derivation point, legitimately command-less (with the recorded
  decision), or out of scope with a reason. This is the artifact that makes
  H-4's "every producing path" checkable by the next reviewer rather than
  asserted by this one.
- [ ] Note explicitly which of the 78 still-unwired accepted command types
  remain, so the follow-up sweep has a starting inventory.

## Close-out

- Full targeted verification, exactly:

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_schema_registry.py tests/research_system/unit/test_command_service.py tests/research_system/unit/test_replay.py tests/research_system/integration/test_artefact_command_seam.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

  The full `tests/research_system` tree runs **once**, at the final exact head,
  as RM-01 Task B's delta run — not per task (handoff 28: ~1:13 h).
- Update the WP6.1 row in `docs/plans/agentic-research-system/README.md` in the
  same PR (H-11).
- Vault: top-of-page `[PIPELINE]` entry in `04-Methods/Pipeline-Overview.md`
  naming P-043, the registry interface, the artefact seam, and the G-RM-8
  decision as taken. No Computational-Log entry (no numerical result).
- PR description lists: the actual envelope seam found, the producer coverage
  matrix, the G-RM-8 decision and its evidence, the memory delta from retaining
  raw bytes, and the remaining unwired command types.
- **Acceptance is recorded against WP6.1, not the RM lane.**
