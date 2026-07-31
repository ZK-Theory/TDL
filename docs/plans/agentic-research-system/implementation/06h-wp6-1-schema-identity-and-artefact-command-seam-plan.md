# 06h: WP6.1 Schema Identity and Producer-Completeness Implementation Plan

> **For the implementing Worker:** use contract-first-tdd,
> research-assurance-triage, and executing-plans-extras. This is main-path
> WP6.1 work, not an RM-lane shortcut. Read handoffs 26 and 28, P-043, and the
> 2026-07-30 G-RM-3 rereview before starting.

**Status:** REVISED 2026-07-30 (revision 3). The rereview found the
`RegisteredSchema` design feasible but only partially closed: producer and path
controls were incomplete, T2 bypassed the claimed single producer seam,
historical-event policy was only a list of names, and RM-01 could not construct
a pre/post-06h comparison after 06h had merged.
Task 0 evidence collection is blocked on a fresh G-RM-3 verdict. Task 1 is
additionally blocked on G-RM-9. Task 3 is blocked on G-RM-8, whose choice can
occur only after Task 0 supplies the branch evidence.

**Goal:** retain the exact bytes used for command validation, carry that same
validated identity into every command-originated event path including T2,
define the historical-event policy as an executable protocol, and preserve a
pinned pre-change suite/cohort record before any implementation mutation.

**Out of scope:** artefact command authority and consumer enforcement moved to
[06i](06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md). W3 context
packet lifecycle moved to
[06j](06j-w3-context-packet-lifecycle-and-resolution-plan.md). No generated
command or event schema is relaxed.

## Verified runtime seams

The plan is grounded in the exact `c99cec8` source, not an expected interface:

| Path / symbol | Observed behavior | Required change |
|---|---|---|
| `research_system/schema_registry.py::SchemaRegistry` | retains parsed JSON only | retain one immutable `RegisteredSchema` made from one byte read |
| `research_system/command/service.py::CommandService.submit` | routes T2 before generic validation; generic path appends at `service.py:312` | return/pass the exact validated record on the generic path |
| `research_system/command/t2.py::submit_t2` / `_event_envelope` | performs separate validation and appends directly at `t2.py:1153`; events omit the triple | accept the exact validated record and derive the triple in the T2 builder |
| `research_system/authority.py::initialize_control_store` | commandless bootstrap append | classify as system/bootstrap, never fabricate command provenance |
| `research_system/store/ledger.py::_append_release_from_validated_submit` | guarded continuation of a submitted command | inherits the submitting command's record |
| `research_system/evals/**` direct appends | evaluation-only synthetic events | classify as commandless fixtures; never admit them as production provenance |

The Worker must regenerate this table from the dispatch head before editing.
Any additional command-originated path joins the implementation file map.
Any genuinely commandless path gets an explicit reason and schema disposition;
it never receives a made-up command identity.

## Global constraints

- All standing constraints in RM-00 section 5 apply, except RM-only naming.
- Branch `pipe/wp6-1-schema-identity-seam` from the exact accepted pre-change
  head. Copy `.env` into the worktree and record branch, HEAD, and clean status.
- Do not modify `.research-system/schemas/core/commands/**`,
  `.research-system/schemas/core/events/**`, WP6.2 accepted schemas, or WP6.3
  accepted-byte files.
- No provider, CLI, eval-corpus, mathematical, statistical, topological, or
  representation change.
- A source-derived producer matrix and the pre-06h suite record are
  prerequisites, not post-implementation paperwork.

## File map

**Create before production edits:**

~~~text
docs/plans/agentic-research-system/implementation/06h-prechange-producer-matrix-<date>.md
docs/plans/agentic-research-system/implementation/06h-prechange-suite-baseline-<date>.md
~~~

**Modify:**

~~~text
research_system/schema_registry.py
research_system/command/service.py
research_system/command/t2.py
research_system/store/ledger.py                      # only the guarded release continuation if required
research_system/projection/replay.py                 # historical admission only for the chosen G-RM-8 branch
tests/research_system/unit/test_schema_registry.py
tests/research_system/unit/test_command_service.py
tests/research_system/unit/test_wp6_2_t2_runtime.py
tests/research_system/unit/test_replay.py             # only for the chosen historical branch
~~~

No other production file is added silently. A newly found command producer is
added to the matrix and plan before its code is edited.

## Obligation register

| ID | Source | Obligation | Disposition |
|---|---|---|---|
| H-1 | P-043 | Digest the exact bytes validated, never a reserialization | Task 1 |
| H-2 | prior C-1 | Validator and producer use the same immutable identity record | Tasks 1-2 |
| H-3 | RR-M2 | Migrate, grandfather, and no-store must each be executable and distinguish old events from new malformed events | G-RM-8 protocol table + Task 3 |
| H-4 | RR-M1 / handoff 26 | Cover generic, T2, guarded release, and every other command-originated append | Task 0 matrix + Task 2 |
| H-5 | RR-M3 | Observe the same 156-node cohort at pinned pre- and post-06h subjects | Task 0 + RM-01 |
| H-6 | P-043 | Commandless bootstrap/eval paths carry an explicit non-command disposition | Task 0 matrix |
| H-7 | rereview fixture list | Alias, symlink, case variant, valid-wrong schema, T2 bypass, and missing mapping controls | Tasks 1-2 |
| H-8 | vault/status discipline | README and Pipeline-Overview reflect exact completion state | Close-out |

## G-RM-8: inspectable branch protocols

Stephen chooses only after the following evidence exists. The decision record
pins the selected protocol version and exact evidence identities.

| Branch | Independent evidence | Admission / transformation | Repeat and replay semantics | Stop / rollback | Distinguishing negative |
|---|---|---|---|---|---|
| **Migrate** | Read-only inventory from the bound store: store identity, ledger fingerprint, global positions, event IDs, command IDs, schema IDs/versions, and exact pre-migration batch hashes | A named migration ID maps each eligible historical command event to one canonical replacement/addendum carrying the registry-derived triple; input and output manifests are content-addressed | A second run is a no-op returning the first receipt; replay of migrated output equals the pre-migration projection for every non-provenance field and is deterministic from genesis/incremental paths | Any unmapped/ambiguous command, changed input fingerprint, duplicate target, or projection delta aborts before cutover; original store remains immutable and active until an atomic owner-approved binding switch | A newly appended event missing the triple is ineligible because eligibility is bounded by the pinned pre-migration maximum global position and inventory hash |
| **Grandfather** | Same store inventory plus a signed/attributed decision pinning `store_identity`, `ledger_fingerprint`, and `max_global_position` | Replay admits a missing triple only when all three pins match and the event position is at or below the bound maximum; no field-shape predicate alone is sufficient | Repeated replay returns the same projection and grandfather set; any store/fingerprint drift invalidates the predicate | No rewrite. Any missing/changed pin, position above the bound, or historical-set growth fails closed and requires a superseding owner decision | A new malformed event with identical shape but a greater global position must fail |
| **No prior store** | Independent filesystem/store discovery over declared roots, store registry, backup registry, and operator attestation; record commands, roots, time, and zero-store result | Fresh store only; every command-originated event requires the triple from genesis | Reinitialization is idempotent only against the same empty/new store identity; discovery is rerun before activation | Discovery of any prior store, backup, or ledger is a hard stop; choose migrate or grandfather instead | Plant a discoverable historical-store fixture outside the first searched root; the assertion must fail |

No branch may be selected from a Worker-authored summary alone.

## Research assurance requirements

- **Lanes:** Output/Provenance and provenance-integrity.
- **Machine-checkable:** exact byte hash; same object instance; TOCTOU
  resistance; alias/symlink/case normalization; command-specific schema
  binding; generic and T2 event triples; fail-closed missing mapping; chosen
  historical protocol; pre/post cohort identity.
- **Human review:** whether the producer inventory is complete and whether the
  G-RM-8 evidence is independent of the branch implementation.
- **Partial:** generated schema defect; unbounded producer path; inability to
  identify the pre-change cohort; historical inventory ambiguity; any P0
  invariant movement.

## Task 0: freeze producer and pre-change evidence

1. Record cwd, branch, exact pre-06h HEAD, merge-base, and clean status.
2. Generate the producer matrix by searching actual append and event-builder
   call sites. Classify generic submit, T2, guarded release, authority bootstrap,
   eval fixtures, and every additional hit.
3. Reverify the handoff-28 public-signature prerequisite and record its current
   defining commit.
4. At this exact pre-change head, collect the full `tests/research_system` node
   list with bytecode/cache/coverage writes disabled. Persist the exact node
   IDs, count, command, interpreter, commit, and clean-status check.
5. Persist the handoff-28 156-node Defect-3 cohort verbatim and resolve every
   node at the pre-change head. Record additions, removals, and renames rather
   than replacing the cohort.
6. Commit only the two evidence records:
   `[PIPELINE] P00: freeze pre-06h producer and suite evidence (P-043)`.

Task 1 cannot start until independent review confirms that these records were
collected before production mutation.

## Task 1: exact-byte schema identity (G-RM-9)

1. Add a failing public test for frozen `RegisteredSchema(schema_id,
   schema_version, source_path, raw_bytes, raw_bytes_sha256, parsed)`.
2. Read each schema once as bytes; parse and hash those bytes; store the record.
   `validate()` validates `record.parsed` and returns that same record.
3. Normalize the registered source identity once and reject a second path
   (relative alias, symlink, Windows case variant) that resolves to a different
   file or attempts to shadow an existing ID.
4. Prove file mutation after registry construction does not change validation
   or the returned digest; prove record mutation and duplicate IDs fail.
5. Measure and record full-tree memory cost.

## Task 2: complete command-producer binding

1. Add one shared `validate_command(envelope) -> RegisteredSchema` contract,
   but do not claim one control-flow point. Generic submit and T2 are two real
   producer paths that must both consume it.
2. Generic submit uses the active command-specific binding and passes the exact
   returned record into event construction and the guarded release continuation.
3. `submit_t2` performs its accepted T2 checks, obtains the exact registered T2
   command schema used, and passes that record into `_event_envelope`; every T2
   event derives the triple there before append.
4. A missing mapping, wrong registered schema, caller-supplied triple, or
   command/event builder that lacks a validated record fails before append.
5. Commandless paths remain as recorded in Task 0 and receive no fabricated
   triple. Their event schemas and admission are tested separately.
6. Re-run the producer search and fail if any command-originated path is absent
   from the matrix.

## Task 3: implement the selected historical protocol

Implement only the G-RM-8 branch Stephen selected from the completed protocol
table. Add one positive, one new-malformed-event bypass negative, repeat-run,
genesis replay, incremental replay, and rollback/stop test. The decision record,
inventory, migration/predicate identity, and evidence hashes are required test
inputs; no ambient current-directory or field-shape inference is accepted.

## Task 4: post-change targeted proof

Run:

~~~powershell
uv run --no-sync python -m pytest -q tests/research_system/unit/test_schema_registry.py tests/research_system/unit/test_command_service.py tests/research_system/unit/test_wp6_2_t2_runtime.py tests/research_system/unit/test_replay.py -o "addopts=" -p no:cacheprovider -p no:cov
uv run --no-sync ruff check research_system
~~~

The full `tests/research_system` run belongs to RM-01 after this exact head is
merged. Do not collect a substitute "pre" baseline here after mutation.

## Close-out

- Update the 06h/WP6.1 row in `implementation/README.md`.
- PR description includes both Task 0 records, the final producer matrix, the
  G-RM-8 decision/evidence, exact targeted results, memory delta, and remaining
  commandless paths.
- Vault `[PIPELINE]` entry names P-043, the exact pre/post subjects, and the
  selected historical protocol.
- Independent exact-subject review precedes Stephen's acceptance. Passing tests
  do not close G-RM-9 or establish plan acceptance.
