# ARS P0 WP1 — Independent Provenance and Software Review

**Date:** 2026-07-01
**Reviewer role:** Independent provenance and software reviewer (Review Checkpoint 1 — identity and recovery freeze; Review Checkpoint 2 — schema freeze)
**Subject:** Work Package 1 (control plane and replay), branch `codex/ars-p0-foundation`
**Method:** `adversarial-design-review` applied to a committed implementation; read-only. All findings verified against the actual files, not summaries.

---

## Verdict

**`accept_with_required_changes`.**

WP1 is inside the approved P0/WP1 scope, is entirely additive, and its identity + atomic-recovery core is correct and well-tested (41/41 pass, ruff clean, `diff --check` clean, zero blast radius on existing code). No finding is blocking (no P0). The required changes are documentation/schema-text reconciliations that must land **before WP2/WP3 consume the shared models** — they are not code redesigns and do not reopen the identity/recovery freeze.

- **Identity/recovery freeze: ACCEPTED.**
- **Schema freeze: ACCEPTED WITH REQUIRED CHANGES** (P1-1, P2-1, P2-2, P2-6 below).
- **WP2/WP3 may consume these APIs: YES, conditionally** (see "Downstream consumption").

---

## Reviewed commit range and actual state

- **Expected HEAD:** `3cff54b94c42347b64b94a3ecbdff9c040c5e166` — **matches actual HEAD.**
- **Branch:** `codex/ars-p0-foundation` (confirmed).
- **Worktree:** `C:\Users\steph\TDL\.worktrees\ars-p0-foundation`.
- **Working tree:** clean at every checkpoint during the review (`git status --short` empty before and after the test run; HEAD unchanged after `uv run`). The **only** modification I made to the worktree is adding this one review deliverable under `reviews/`.
- **WP1 commit sequence (verified present, in order):**
  - `6f0a909` `[PIPELINE] P00: scaffold ARS foundation package`
  - `92e9389` `[PIPELINE] P00: add ARS core schema registry`
  - `c2baed8` `[PIPELINE] P00: add ARS external single-writer store`
  - `ce22be4` `[PIPELINE] P00: implement ARS command and receipt boundary`
  - `3cff54b` `[PIPELINE] P00: complete ARS control-plane replay slice` (HEAD)
- **Compatibility decision:** `7b48f11` `[DECISION] P00: scope Python compatibility baseline exception` (parent of `6f0a909`).
- **Footprint:** 39 files, +2268/-1; new `research_system/` package, tracked `.research-system/{config,schemas}` definitions, `tests/research_system/`, `pyproject.toml`, `.gitignore`, and one docs note.

---

## Verification commands and exact results

| Command | Result |
|---|---|
| `git rev-parse HEAD` | `3cff54b94c42347b64b94a3ecbdff9c040c5e166` (matches expected) |
| `git branch --show-current` | `codex/ars-p0-foundation` |
| `git status --short` | empty (clean, before and after run) |
| `git diff --check 7b48f11^..HEAD` | exit 0 (no whitespace/conflict-marker damage) |
| `uv run ruff check research_system tests/research_system` | `All checks passed!` (exit 0) |
| `uv run pytest <6 named files> -q --no-cov` | `41 passed in 3.43s` (exit 0), Python 3.13.5 |
| GitNexus `detect_changes(scope: compare, base_ref: main, worktree)` | 38 changed files, **0 changed symbols, 0 affected processes, risk low** — confirms additive-only, zero blast radius on `financial_tda`/`poverty_tda`/`trajectory_tda`/`shared` |
| GitNexus `impact(CommandService, upstream)` | `not found` — new package is not in the `main`-built index; new-package impact assessed directly from files (per charter) |

The pytest run collected exactly the 6 named files (41 tests). The wider repository baseline was **not** run; the Python-compat note documents 13 pre-existing `gtda`/`topologytoolkit` collection errors unrelated to ARS (see "Deferred debt").

---

## Findings

### P0 — Blocking

**None.** No finding can corrupt authority/evidence, permit invalid acceptance, leak restricted data, or make deterministic recovery impossible.

### P1 — Required before WP2/WP3 consume the APIs

**P1-1 — `CommandService.submit()` performs only a subset of W2 §8.2 and is not an authorization boundary, but the WP1 plan states it "performs W2 section 8.2 checks in order."**
- **Evidence:** `research_system/command/service.py:32-66`. The implemented order is: envelope schema (§8.2 step 1, `service.py:33`), chain integrity via `replay` (`service.py:35,43`), idempotency from committed events (step 6, `service.py:36,44,68-88`), expected stream version (step 5, `service.py:47-56`), transition preconditions via reducers (step 7, `projection/replay.py:56-92`), and batch integrity (step 9, `store/ledger.py:38-100`). **Absent:** referenced-object existence/hash (step 2), canonical owner/compat mode (step 3), **actor + authority-grant evaluation (step 4)**, and assurance/review/human gates (step 8). Plan claim: `implementation/01-control-plane-and-replay-plan.md:595`.
- **Failure scenario:** any schema-valid command carrying a well-formed `authority_grant_id` is accepted without checking the grant exists, is unexpired/unrevoked, covers the actor, or permits `command_type`; likewise `ClaimDispatch` on a never-issued dispatch is accepted (`service.py:125-127`, no DispatchIssued precondition). A WP2/WP3 author reading the WP1 child plan could assume `submit()` already gates authority and omit it.
- **Impact:** operations/validity — mislabels an authorization control on a control-plane foundation. The deferral itself is legitimate (the master plan's forward-obligation matrix assigns W4/W5 authority to WP2, `05-...-plan.md:190-198`); only the WP1 child-plan prose overstates coverage.
- **Minimum correction (documentation, not code):** correct `01-control-plane-and-replay-plan.md:595` to state the implemented subset and cross-reference that §8.2 steps 2/3/4/8 are WP2/WP3 obligations; add a one-line docstring on `CommandService.submit` that it is **not** an authorization gate. No code change required for P0.
- **Affected work packages:** WP2 (authority/independence), WP3 (adapters/operations).

### P2 — Minor / hardening (address opportunistically; P2-1/P2-2/P2-6 recommended at schema freeze)

**P2-1 — `canonical_bytes` is not RFC 8785, which W2 §7.1/§9.2 mandate.**
- **Evidence:** `research_system/canonical.py:8-11` uses `json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False)`. W2 §7.1 and §9.2 specify "RFC 8785 canonical JSON" for `content_hash`/`event_hash`.
- **Failure scenario:** identical for P0 (all IDs/keys ASCII, payloads string/int → deterministic, and write and verify use the same function, so the hash chain and idempotency index are internally sound). Diverges from RFC 8785 for float payloads (RFC 8785 mandates ECMAScript number formatting) and non-BMP Unicode keys (RFC 8785 sorts by UTF-16 code units; Python sorts by code point).
- **Impact:** validity of any future cross-implementation verification (e.g. S-013/S-014 backup-restore, currently deferred) and of any non-ASCII/float payload. The WP1 plan pre-specified this exact function (`01-...-plan.md:153-157`), so it is plan-consistent; W2 §7.1 was simply never amended.
- **Minimum correction:** either amend W2 §7.1/§9.2 to record the P0 canonicalization (json.dumps-sorted, ASCII/int domain) with a Gate-5 obligation to adopt true JCS before external-store interchange, or replace `canonical_bytes` with a JCS implementation. Record the decision.

**P2-2 — `task.schema.json` is unenforced and its `status` enum diverges from frozen W2 §11.1 and from the reducer.**
- **Evidence:** `.research-system/schemas/core/task.schema.json:11` enum = `proposed/ready/active/blocked/partial/completed/cancelled/superseded`. W2 §11.1 canonical Task statuses are `draft/readiness_pending/ready/in_progress/review_pending/blocked/input_required/paused/accepted/rejected/partial/cancelled/superseded`. The reducer emits `draft`/`readiness_pending` (`command/reducers.py:20-25`). Grep confirms `ars://core/task` and `ars://core/authority-grant` are **never referenced** in `research_system/` — both schemas are registered by the loader but validate nothing; the stored "task" object is the raw command payload (`command/service.py:117-121` → `store/objects.py:12-45`), which does not conform to `task.schema.json`.
- **Failure scenario:** a WP2 consumer that validates task-definition objects against the frozen `ars://core/task` inherits a status vocabulary that neither W2 nor the reducer uses.
- **Impact:** schema/consumer drift at the freeze boundary.
- **Minimum correction:** align `task.schema.json:11` with W2 §11.1 (or explicitly scope it as a placeholder), and record that object-level schema enforcement (task/authority-grant) is deferred to the package that first persists those records.

**P2-3 — Idempotency uses `authority_grant_id` where W2 §13.1 names `authority_scope`; receipts are keyed solely by `command_id`.**
- **Evidence:** tuple built at `command/service.py:71-77` = `(actor_id, authority_grant_id, command_type, idempotency_key)`; W2 §13.1 = `(actor_id, authority_scope, command_type, idempotency_key)`. Receipts persisted at `store/receipts.py:54` under `receipts/{command_id}.json`.
- **Failure scenario:** using `authority_grant_id` is safe (stricter than scope; a retry that changed only the grant would fail the stream-version guard, not silently double-commit). Separately, because there is no global `command_id`-uniqueness enforcement, a caller that reused one `command_id` across two different actors/streams would commit the event batch and then fail at `receipts.write` (`store/receipts.py:59`, different bytes → `ConflictError`), leaving a committed event without its own receipt; a later retry would reconstruct/serve a cross-actor receipt (`service.py:90-102`). Not reachable with UUIDv7 IDs under the stated caller contract (retries reuse `command_id`; distinct commands get distinct IDs).
- **Impact:** latent robustness only.
- **Minimum correction:** either key receipts on the idempotency tuple or assert `command_id` global uniqueness at append so misuse fails **before** the batch commits; note the `authority_grant_id`↔`authority_scope` substitution as the intended P0 reading of W2 §13.1.

**P2-4 — CLI worktree enumeration degrades to a single-root disjointness check on `git` failure.**
- **Evidence:** `research_system/cli.py:26-44`. If `git worktree list --porcelain` returns non-zero, only the single provided root is registered (`cli.py:36-38`), so `require_external_control_root` cannot reject a control root nested in an unenumerated sibling worktree.
- **Failure scenario:** git transiently unavailable **and** the operator points `--control-root` inside an unregistered worktree.
- **Impact:** low-probability weakening of the externality guarantee.
- **Minimum correction:** treat a non-zero `git worktree list` as fail-closed (raise) rather than degrade, or require the caller to pass the full root set explicitly.

**P2-5 (informational) — non-protected caller fields can override ledger-set values via the `**candidate` spread.**
- **Evidence:** `store/ledger.py:63-77`. `_PROTECTED_FIELDS` (`ledger.py:14-26`) guards positions/hashes/transaction fields, but `recorded_at` (`ledger.py:73`) and other caller keys are spread after and would override. The `CommandService` is the sole caller and sets these itself (`service.py:130-145`), so this is not reachable in P0.
- **Minimum correction:** add `recorded_at` (and `event_type`/`stream_id`/`payload` are already popped) to the protected set for defence in depth.

**P2-6 — `execution_lease` prefix `els` in the frozen ID registry appears to diverge from W2 §6.1 (`lse`).**
- **Evidence:** `.research-system/config/id-kind-registry.yaml:20` `execution_lease: els`; W2 §6.1 lists `lse | lease`. The plan states prefixes are field-scoped from the W8 owner catalogue (`01-...-plan.md:115`), which I could not inspect (W8 not in the governing-doc set for this review).
- **Impact:** the registry is a **WP1-frozen** artifact consumed by WP3; a wrong lease prefix would surface only there.
- **Minimum correction:** confirm `els` against the accepted W8 catalogue before WP3 consumes the registry; if W8 uses `lse`, correct the registry now.

---

## Attacks performed (and why each failed to break the design)

| Attack | Outcome |
|---|---|
| **Concurrency / double writer** | `WriterLock` (`store/lock.py:17-26`) uses `O_CREAT\|O_EXCL`; the second concurrent writer gets `ConflictError`. Idempotency + expected-version are re-checked **inside** the lock (`service.py:43-56`, double-checked locking). No double-commit reachable. Loser fails closed (raw `ConflictError`, acceptable for P0). |
| **Crash ordering / atomicity** | Six fault-injection tests (`test_control_plane_fixtures.py:90-196`) inject after object write, after batch temp fsync, after event rename, before ledger-tail refresh, after receipt temp fsync, and after receipt rename. Every case recovers to **exactly one** batch and a **byte-identical** receipt reconstructed from committed events (`_assert_recovered`, lines 31-58). Commit point = `os.replace` (`ledger.py:124-125`). Orphan objects/temp files are inert (replay reads only `events/`). |
| **Corrupt / malformed history** | `replay` (`projection/replay.py:108-165`) fails closed on bad major, non-`ars://core/event/` schema_id, position gap/overlap, previous-hash break, event-hash mismatch, project-identity mismatch, per-stream version gap, and incomplete transaction. `test_broken_canonical_tail_blocks_later_command` (`fixtures:198-214`) proves a tampered committed tail blocks the next command with no new batch. |
| **Identity substitution** | `load_store_manifest`/`verify_store_identity` (`store/identity.py:58-97`) verify manifest hash (tamper-evident), control-root binding, project ID, 64-hex store identity, and code-root binding; `test_s012` covers identity mismatch, code-root mismatch, and worktree-local store rejection. |
| **Path escape** | `require_external_control_root` (`store/layout.py:17-33`) resolves parent strict + final non-strict and rejects equal/ancestor/descendant overlap; the CLI enumerates **all** worktrees + main root (`cli.py:26-44`). Reparse-parent and ancestor/descendant escapes are tested (`test_store.py:19-46`, `test_replay.py:102-121`). |
| **Idempotency-key reuse** | Tuple from committed events, not receipt lookup (`service.py:68-88`). Same tuple+payload → original receipt; same key/diff payload or diff command_id → `ConflictError`; same key across command types → independent (`test_command_service.py:20-45`). |
| **Partial transactions** | Transaction index/count tracked across the batch and at EOF (`replay.py:148-164`); incomplete transaction → `IntegrityError`. Batches are single JSONL files published by one atomic rename. |
| **Stale versions** | `expected_stream_version` re-checked against the replayed tail inside the lock (`service.py:47-56`); mismatch → conflict receipt, no event. `test_competing_claims` exercises it. |
| **Receipt / schema drift** | Command validated against `ars://core/command` (enforced, `service.py:33`); event conforms to `ars://core/event` and is test-asserted (`test_replay.py:44-48`); receipt conforms to `ars://core/receipt`, test-asserted (`test_command_service.py:111-120`, `fixtures:45-58`). Object non-conformance recorded as P2-2. |
| **Projection overwrite** | `_projection_rebuild` (`cli.py:90-105`) rejects output equal to/under the control root and any path outside a code-root `.research-system/projections/`; rebuild is full-replay + atomic temp/rename; `test_s006_...` proves rejection of `task.md` and `control_root/events/...`. `test_s009` proves determinism + disposability (canonical events unchanged). |
| **Scope-completion bypass** | `_validate_scope_completion` (`replay.py:26-53`) requires an exact `scope_definition_ref` revision and a disposition for **every** required member, naming missing/extra/invalid ones; `test_s008` asserts `missing dispositions: T2.2` and reducer purity. (Enforced at replay; no command-side `CompleteScope` exists in WP1 — see residual risks.) |
| **Live-state / migration probe** | `diff --stat` + grep confirm the change set touches only `research_system/`, tracked `.research-system/{config,schemas}`, `tests/`, `pyproject.toml`, `.gitignore`, and one docs note. No live control root, evidence root, migration, provider integration, `.apm/`, vault, or research artifact is created or mutated. Tests use `tmp_path` control roots exclusively; the only repo read is of **tracked schema definitions** (`.research-system/schemas`), which is intended. |

---

## WP1 acceptance-checklist disposition (`01-control-plane-and-replay-plan.md:688-698`)

| Item | Disposition |
|---|---|
| S-001/S-002/S-006/S-008/S-009/S-010/S-011/S-012 represented by named tests | **PASS** — all present and named (`test_s001_...`, `test_competing_claims`, `test_s006_...`, `test_s008_...`, `test_s009_...`, `test_s010_...`, six `test_s011_...`, `test_s012_...`). |
| F-001–F-005 known-bad/controlled paths gradeable without active APM state | **PASS with caveat** — F-001/F-002 (`test_s001_s002_f001_f002`, `test_distinct_task_and_artefact_objects_cannot_overwrite`), F-003 (explicit-root CLI + config binding), F-005 (`test_s008`). F-004's *drift-diagnostic* aspect is represented only by disposable rebuild-from-events; no explicit `ProjectionDriftDetected` event in WP1 (deferred). |
| Atomic recovery yields zero or one committed batch | **PASS** — six crash-window tests. |
| Crash after event rename before receipt reconstructs original receipt from event-derived evidence | **PASS** — `test_s011_crash_after_event_rename_reconstructs_receipt`, byte-identical, no second batch. |
| Unknown schemas, broken hashes, stale versions, second writers fail closed | **PASS**. |
| Deleting projections changes no canonical state | **PASS** — `test_s009`. |
| Control root explicit and external in every CLI/test path | **PASS** — argparse-required paths, no cwd inference; `foundation.yaml` `control_root: null, control_root_required: true`. |
| Independent reviewer accepts staged diff before WP2/WP3 consume APIs | **This review** — `accept_with_required_changes`. |

---

## Explicit freeze decisions

- **Identity and recovery freeze (Checkpoint 1): ACCEPTED.** Owner-registered UUIDv7 IDs with field-scoped validation and no arbitrary-prefix constructor (`ids.py:37-97`), root separation across all registered worktrees and resolved reparse parents (`store/layout.py`, `cli.py:26-44`), fail-closed store identity (`store/identity.py`), committed-command reconstruction that is byte-identical and adds no second batch (`service.py:90-102`, `fixtures:31-58`), and zero-or-one committed batch across every tested crash window are all correct. No P1/P2 finding touches identity or recovery correctness.
- **Schema freeze (Checkpoint 2): ACCEPTED WITH REQUIRED CHANGES.** Runtime command/event/receipt representations agree with the frozen schemas (enforced or test-asserted). Land P1-1 (authority-deferral disclosure), P2-1 (canonical-JSON standard reconciliation), P2-2 (task-schema status vocabulary + object-enforcement deferral note), and P2-6 (lease prefix vs W8) **before** WP2/WP3 consume the shared models. These are prose/schema-text fixes.

## Downstream consumption — may WP2/WP3 consume these APIs?

**Yes, conditionally.** The command/event/receipt/replay/store/ID APIs are stable and correct for consumption, provided consumers observe:
1. `CommandService.submit()` validates **schema + expected-version + idempotency + transition + batch-integrity only**. It is **not** an authorization boundary — WP2 must add W4/W5 actor/authority-grant and assurance evaluation (§8.2 steps 2/3/4/8); do not assume WP1 gates authority (P1-1).
2. Do not rely on `ars://core/task` / `ars://core/authority-grant` object validation being performed by WP1 — it is not (P2-2).
3. If any consumer introduces float or non-ASCII canonical payloads, or cross-store interchange, resolve the canonical-JSON standard first (P2-1).
4. Confirm the frozen `id-kind-registry.yaml` lease prefix against the W8 catalogue before WP3 emits lease IDs (P2-6).

---

## Residual risks and deferred debt

- **Stale writer lock after a true hard crash.** The lock intentionally never auto-breaks (`store/lock.py`; plan Task 3). The crash-window tests simulate crashes as Python exceptions that unwind the `with WriterLock` block and release the lock, so they do not exercise a hard crash (kill/power loss) that would strand `runtime/writer.lock`. **Committed-command receipt reconstruction is unaffected** (it runs before lock acquisition, `service.py:35-38`), but any **new** command after a hard-crash-while-locked is blocked until an operator removes the lock. This is the specified fail-closed behavior, not a defect — flagged as an operational residual.
- **Fixture-catalogue verification limit.** The W6 fixture catalogue (06a/06b) was outside this review's governing-doc set. S-006 and the exact F-001–F-005 semantics are bound to named tests that exercise plausible controls, but each test was not cross-checked against the authoritative fixture definition. Recommend the fixture-activation checkpoint (master plan checkpoint 5) close that binding.
- **Command-side `CompleteScope` is absent in WP1.** Scope-completion is enforced only at replay (`replay.py:26-53`); the service can emit only `TaskCreated`/`DispatchClaimed`, so no WP1 command can produce a `ScopeCompleted` event. Enforcement via the reducer/replay is correct and tested; the command path is legitimately deferred.
- **Deferred Python-compatibility debt.** Repository-wide collection still has 13 pre-existing `gtda`/`topologytoolkit` import errors on the 3.13.5 pin, confined to existing financial/shared modules and unrelated to ARS (`python-compatibility-baseline-2026-07-01.md`). The exception **conceals no ARS-required dependency**: ARS imports only stdlib + `jsonschema` (already pinned) + `PyYAML` (already a repo dependency); the 6 named ARS test files run clean. The note correctly forbids waiving any future ARS import failure under it.

---

## Provenance statement

The worktree was clean at every checkpoint and HEAD equalled the expected `3cff54b` throughout. `uv run` created only an uncommitted local environment; no tracked file changed. The single modification I introduced is this review file. No live control/evidence root, migration, provider integration, `.apm/`, vault, or research state was created or altered during the review.
