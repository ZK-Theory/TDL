# WP6.1 Message lifecycle exact-subject re-review — candidate `b400001`

Date: 2026-08-02
Reviewer role: fresh independent exact-subject re-reviewer
Verdict: **`rework_required`**

## Exact subject and review boundary

- Review worktree: `C:\Users\steph\.codex\worktrees\4c88\TDL`
- Review branch: `codex/wp6-1-message-lifecycle-rereview-b400001-20260802`
- Exact candidate: `b4000015c65c132da272f0ca6122060a17d8c0af`
- Candidate tree: `21c5169ff964542a86fefc3c1bd34b9362be6d5a`
- Sole parent and immutable first-review commit: `638a12b1ffb9893fac0fd2f996995c788df95693`
- Original reviewed candidate: `b3531092814efbd2ff3f1fb094dd929032642d1e`
- Implementation base: `7275184e41fbfb149d2c91462ac872012d29a961`
- Design authority: commit `0e842969c770811edf5c81dcd7e4f7a647e050ad`, path `docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md`, blob `80182047b5ad42ad8427db128e1b66b784c93177`
- First-review record: `docs/plans/agentic-research-system/reviews/wp6-1-message-lifecycle-b353109-review-2026-08-02.md`, blob `4b89a507ee6ac1699600b38458f7614b386243b6` at both `638a12b1` and the candidate

The worktree started detached. Detached `HEAD` and the named local branch both resolved to the exact candidate, so one deterministic `git switch codex/wp6-1-message-lifecycle-rereview-b400001-20260802` attached it. No fallback branch, branch creation, rename, commit switch, merge, rebase, or integration was performed.

The complete base-to-candidate diff contains exactly the immutable first-review record plus these eight implementation/test paths:

1. `research_system/authority.py`
2. `research_system/command/lifecycle.py`
3. `research_system/command/reducers.py`
4. `research_system/command/service.py`
5. `research_system/projection/replay.py`
6. `research_system/schema_registry.py`
7. `tests/research_system/factories.py`
8. `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

No candidate code or test was remediated. No schema, catalogue, manifest, ledger, provider, KAN-67, WP6.4, W11, Jira, PR, merge, or external-review service was touched.

## Executive decision

Five first-review findings are closed at the exact candidate. The recognized-Message generic-schema downgrade now fails before projection publication while legacy generic Task replay remains compatible; shared non-Message scoped retries pass their unchanged contracts; Message payloads are deeply detached from caller-owned nested objects; the 13-row common-axis matrix is executable; and the plain control-plane factory preserves an explicitly supplied adapter snapshot.

C-01 is not closed. The candidate correctly rechecks current lifecycle authority, project, canonical history, exact provenance, and valid/foreign scoped indexes for the tested accepted-retry states. It does not classify all invalid missing-index residue before append. An independently constructed state containing an orphan accepted command receipt, no scoped index, and no canonical Message event caused submission to append `MessagePublished` and publish a scoped index before raising `ConflictError`. A command reported as conflict therefore created durable Message evidence and left contradictory receipt/index state. This is a Critical atomicity and evidence defect under the explicit C-01 no-mutation requirement.

## Mandatory first-review finding dispositions

### C-01 — not closed — Critical

What is repaired:

- Current lifecycle authority is resolved before scoped-receipt lookup at `research_system/command/service.py:448-485`.
- Indexed accepted retries replay the canonical ledger and validate the exact event type, command ID, payload hash, stream, version, project, current grant identity, actor, command schema ID/version/hash, and command payload hash at `service.py:838-938`.
- Scoped indexes bind actor, grant, command type, idempotency key, payload hash, authority hash, expected version, project, and target stream in `research_system/store/receipts.py:204-287`.
- Valid missing-index recovery reconstructs the scoped index without a second Message event; foreign indexes and unsupported-major history reject without mutation in the focused tests at `tests/research_system/integration/test_wp6_1_message_lifecycle.py:1681-1753`.

Decisive counterexample:

1. A temporary control plane was created with a valid current Message grant and adapter snapshot.
2. An accepted receipt for the exact `PublishMessage` command was written to `receipts/<command_id>.json`, while the scoped index and canonical Message event were deliberately absent.
3. The ledger and idempotency-index set were captured before calling the public `CommandService.submit` seam.
4. Submit raised `ConflictError: receipt already exists: <command_id>` only after the event count changed from `0` to `1` and the scoped-index count changed from `0` to `1`.
5. The appended event was `MessagePublished` for that command ID; the pre-existing receipt bytes remained unchanged.

The deterministic ordering is visible in source. A missing scoped index returns `None` at `service.py:1454-1471`; lifecycle commands skip ordinary stored-receipt checks at `service.py:486-492`; an empty ledger has no committed match at `service.py:493-500`; append occurs at `service.py:634-666`; and `write_scoped` publishes the new index before `write(receipt)` detects the orphan receipt at `research_system/store/receipts.py:349-359` and `:156-162`.

This state is contradictory residue, not the valid deleted-index state exercised by the green recovery test. It must reject before any ledger, receipt, index, replay, or projection mutation. Because it does not, C-01 remains material and acceptance is blocked.

### C-02 — closed

`validate_exact_lifecycle_envelope` now maps the four recognized Message event types to their exact schema IDs and rejects any mismatch at `research_system/command/lifecycle.py:62-67` and `:88-106`. Replay consumes that guard before `apply_event` at `research_system/projection/replay.py:623-714`; `rebuild_projection` publishes only after replay succeeds. The exact recognized-type/generic-schema negative preserves prior projection bytes.

The change is Message-specific. The unchanged generic Task controls `test_replay_keeps_legacy_event_without_schema_provenance_readable` and `test_future_activation_does_not_reinterpret_generic_event_history` both passed, so legitimate generic Task history remains readable.

### M-01 — closed

Shared `_return_scoped_receipt_or_raise` semantics are restored at `research_system/command/service.py:1497-1508`: the exact command ID returns the original receipt, a command ID already present in a receipt or committed event conflicts distinctly, and a fresh equivalent non-Message scoped retry returns the original receipt. Message-specific fresh-command-ID/key conflict behavior is isolated at `service.py:1482-1495`.

All four unchanged non-Message retry nodes passed. Their test files remain byte-identical to the base/candidate parent: `test_authority_grant_source.py` blob `6915ee2897050220587dcf825aef478c54248bb8`; `test_scoped_authority_grant_activation.py` blob `d1d709ba9f82da5691484f53c78310093b520ef3`.

### M-02 — closed

All four Message event constructors deep-copy the submitted payload at `research_system/command/service.py:2591-2602`, before the unchanged ledger's shallow draft/cache boundary. The focused node proves cached and durable publication payloads remain unchanged after caller mutation and a subsequent valid delivery succeeds.

An additional independent probe mutated nested `scope_refs` and `recipient_actor_ids` after accepted publication. Cached and durable payloads both remained equal to the pre-submit deep copy, and delivery was accepted. The independently canonicalized event-payload hash equalled both `MessagePublished.command_payload_hash` and replay state `content_sha256`.

### M-03 — closed for the literal common-axis requirement

The accepted catalogue contains exactly 13 unique Message rows. `MESSAGE_ROWS` enumerates the same ten publish discriminants plus delivery, acknowledgement, and delivery failure at `tests/research_system/integration/test_wp6_1_message_lifecycle.py:24-37`.

Each parametrized `test_message_row_common_axis_matrix[<exact-row-id>]` node performs, rather than merely labels:

- a currently authorized accepted submit;
- an exact retry with no mutation;
- changed command-ID/same-key and same-command-ID/changed-key conflicts;
- an unauthorized submit with no mutation;
- a row-specific valid command followed by a decisive invalid mutation;
- replay and control-plane history equality;
- projection rebuild; and
- either the delivery/failure race, acknowledgement race, or an explicit semantic N/A record for absent-stream publication rows.

The matrix body and assertions are at `test_wp6_1_message_lifecycle.py:117-204`. The 13 matrix nodes passed. The ten publish rows use explicit concurrency N/A because they have no competing terminal transition; the separately required terminal races execute for delivery, acknowledgement, and failure. Closed protected schemas and separate discriminant negatives provide the fail-closed publication evidence. This is not a label census.

### m-01 — closed

`control_plane(..., auto_authority=False, message_adapter_registry=...)` passes the explicit snapshot to the plain `CommandService` at `tests/research_system/factories.py:487-513`. The focused test at `test_wp6_1_message_lifecycle.py:1150-1187` manually activates the exact scoped Message grant and accepts publication plus adapter delivery through that plain service.

## Full frozen-pilot contract audit

### Catalogue, bindings, schemas, and payloads

- Direct parsing of `.research-system/contracts/wp6-1-owner-source-catalogue.yaml` at the candidate found exactly 13 unique `message.*` rows: ten `PublishMessage` rows plus `message.deliver`, `message.acknowledge`, and `message.delivery_failure`.
- Exactly four command types and four producer-specific event types are active at version `1.0.0` in `research_system/schema_registry.py:140-183`.
- Both protected `PublishMessage` and `MessagePublished` schemas contain exactly ten discriminator branches. Each branch is closed with `additionalProperties: false`, has a literal `message_type` constant, and declares its row-specific required facts.
- Unsupported, missing, aliased, and payload-inconsistent publish discriminants fail schema validation before domain mutation. All ten valid publish variants preserve the exact closed payload.
- Caller provenance fields are stripped before validation. Event command and schema provenance is derived from the active binding, not caller data.

### Lifecycle, content, linkage, actors, and adapters

- `reduce_message` implements only `absent -> published -> delivered -> acknowledged` or `absent -> published -> delivery_failed` at `research_system/command/reducers.py:507-581`.
- Publication binds the Message stream, sender actor, recipient set, row-specific payload, reply link, thread, typed subject, and acknowledgement correlation. Self-links and inconsistent acknowledgement correlations reject.
- Delivery binds the canonical publication payload hash, exact recipient set, adapter, and non-empty evidence. Acknowledgement separately requires current `delivered` state, a published recipient actor, the canonical publication content hash, and `source_position == MessagePublished.global_position`.
- The adapter snapshot is a frozen typed dataclass with tuple-valued capabilities/actors and a checked internal content hash at `research_system/command/service.py:226-293`. `CommandService` copies the supplied iterable to a tuple and defaults to an empty fail-closed snapshot at `service.py:330-336`.
- Missing/default, ambiguous, wrong-project, suspended/retired, premature/expired, wrong-capability, and wrong-actor adapter entries reject new adapter transitions. Exact retry returns historical acceptance without performing a second adapter action.
- The snapshot is explicitly service-local constructor authority for this bounded pilot. No adapter persistence, provider call, external action, external-party record, or W7 activation was added or claimed.

### Idempotency, concurrency, replay, projection, and no-mutation negatives

- The composite submission lock serializes Message commands with the authority store.
- Exact retries and changed key/command-ID cases are exercised for all 13 rows. The four unchanged shared retry contracts pass.
- Delivery versus failure and acknowledgement races each produce one stable winner and one unchanged loser.
- Exact Message replay checks active event/command bindings, raw schema identity, canonical payload provenance, project, actor, content/linkage, source position, stream version, transaction order, hash chain, and legal lifecycle order before state publication.
- Recognized Message events under the generic schema, unsupported major versions, wrong command provenance, actor divergence, lineage divergence, missing reducer route, and divergent terminal history fail closed.
- Rejected-path snapshots include ledger tail/batches, stream versions, accepted receipts, idempotency indexes, committed command/scope maps, replay history, and projection. The C-01 contradictory-residue counterexample is the one demonstrated exception.

### Scope

The candidate remains a single-stream Message vertical. It introduces no lifecycle DSL, generator, persistence layer, generic provider framework, second-stream append, `store/ledger.py` change, KAN-67/WP6.4/W11 behavior, external provider action, or protected schema mutation.

## Independent validation evidence

All Python and pytest commands used `C:\Users\steph\TDL\.venv\Scripts\python.exe` directly with:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTEST_ADDOPTS=''
```

`uv` was not used. Pytest commands additionally used `-o "addopts=" -p no:cacheprovider`.

### Complete Message module

```text
python.exe -m pytest -q -o "addopts=" -p no:cacheprovider tests/research_system/integration/test_wp6_1_message_lifecycle.py
98 passed in 54.22s
```

### Mandatory shared retry nodes

```text
python.exe -m pytest -q -o "addopts=" -p no:cacheprovider tests/research_system/integration/test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart tests/research_system/integration/test_authority_grant_source.py::test_rejected_exact_retry_is_returned_before_current_authority_recheck tests/research_system/integration/test_authority_grant_source.py::test_scoped_retry_rejects_reused_unrelated_command_id tests/research_system/integration/test_scoped_authority_grant_activation.py::test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant

4 passed in 103.90s
```

### Focused six-disposition and contract nodes

```text
python.exe -m pytest -q -o "addopts=" -p no:cacheprovider tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_row_common_axis_matrix tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_adapter_retry_rechecks_project_and_current_authority_before_returning_receipt tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_adapter_retry_rejects_unsupported_major_history_without_mutation tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_adapter_retry_reconciles_missing_scoped_index_without_new_message_event tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_adapter_retry_rejects_foreign_scoped_index_without_mutation tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_recognized_message_event_under_generic_schema_fails_before_projection_publication tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_published_message_payload_is_detached_from_caller_and_remains_deliverable tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_plain_control_plane_uses_explicit_adapter_snapshot_with_manually_activated_authority tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_schema_bindings_preserve_all_eight_protected_raw_hashes tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_delivery_acknowledgement_and_failure_follow_only_the_frozen_paths tests/research_system/unit/test_replay.py::test_replay_keeps_legacy_event_without_schema_provenance_readable tests/research_system/unit/test_replay.py::test_future_activation_does_not_reinterpret_generic_event_history

25 passed in 41.19s
```

### Independent decisive probes

```text
orphan accepted receipt + absent scoped index + absent canonical event
  -> ConflictError after MessagePublished append
  -> event count 0 -> 1
  -> scoped-index count 0 -> 1
  -> pre-existing receipt bytes unchanged

nested caller payload mutation after accepted MessagePublished
  -> cached payload unchanged
  -> durable payload unchanged
  -> independently canonicalized payload hash == command_payload_hash == replay content_sha256
  -> subsequent delivery accepted
```

Both probes used disposable OS temporary control roots and did not touch repository runtime state.

### Static and diff hygiene

```text
python.exe -m ruff check research_system/authority.py research_system/command/lifecycle.py research_system/command/reducers.py research_system/command/service.py research_system/projection/replay.py research_system/schema_registry.py tests/research_system/factories.py tests/research_system/integration/test_wp6_1_message_lifecycle.py
All checks passed!

python.exe -m ruff format --check research_system/authority.py research_system/command/lifecycle.py research_system/command/reducers.py research_system/command/service.py research_system/projection/replay.py research_system/schema_registry.py tests/research_system/factories.py tests/research_system/integration/test_wp6_1_message_lifecycle.py
8 files already formatted

git diff --check 638a12b1ffb9893fac0fd2f996995c788df95693 b4000015c65c132da272f0ca6122060a17d8c0af
exit 0

git diff --check 7275184e41fbfb149d2c91462ac872012d29a961 b4000015c65c132da272f0ca6122060a17d8c0af -- research_system/authority.py research_system/command/lifecycle.py research_system/command/reducers.py research_system/command/service.py research_system/projection/replay.py research_system/schema_registry.py tests/research_system/factories.py tests/research_system/integration/test_wp6_1_message_lifecycle.py
exit 0
```

The complete base-to-candidate `git diff --check` reports only the immutable first-review record's intentional Markdown hard breaks at lines 3 and 4. No candidate code/test whitespace error is present.

No package or full repository suite was run. The full 98-node Message module, exact shared retry nodes, focused semantic controls, and decisive C-01 failure define the demonstrated dependency surface; the Critical no-mutation failure made broader validation unnecessary.

## Protected identities

The protected schema registries are unchanged at the exact candidate:

| Registry | Tree | Entries |
|---|---|---:|
| Commands | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | 87 |
| Events | `154ffc4bdde82fe903718734687e7a62797b1f69` | 86 |

Independent SHA-256 over raw bytes read from the candidate Git object produced:

| Active identity (`1.0.0`) | Bytes | Raw SHA-256 |
|---|---:|---|
| `PublishMessage` | 91,363 | `14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c` |
| `MessagePublished` | 91,354 | `f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f` |
| `RecordMessageDelivery` | 7,566 | `9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828` |
| `MessageDelivered` | 10,483 | `7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388` |
| `AcknowledgeMessage` | 7,280 | `3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d` |
| `MessageAcknowledged` | 10,221 | `576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be` |
| `RecordMessageDeliveryFailure` | 7,303 | `afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89` |
| `MessageDeliveryFailed` | 10,212 | `0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5` |

## Remaining integration risk

A live fetch during this review resolved `origin/main` to `dd67dca5ff69c1aeefb903c63f3437df357280c0`. Both the earlier supplied main `9810fa98ba6f2333522b9afd659da5f335bbd79d` and accepted PR #207 head `b0d3e83c` are ancestors. The paths between `9810fa98` and `dd67dca5` are only:

- `.claude/CLAUDE.md`
- `.repowise-workspace.yaml`
- `docs/plans/agentic-research-system/README.md`

The frozen candidate was not rebased, merged, cherry-picked, or otherwise reconciled with current main. PR #207/KAN-67 and current-main reconciliation remain a separate later integration gate. This exact-subject decision neither penalizes the candidate for main drift nor authorizes integration, merge, owner acceptance, Jira changes, or later-family dispatch.

## Decision audit

- Exact candidate acceptance: blocked by the surviving Critical C-01 atomic no-mutation defect.
- C-02, M-01, M-02, M-03, and m-01: closed at this exact subject as described above.
- Protected schemas and materialized sets: keep unchanged; all exact identities match.
- Message pilot architecture: bounded single-stream/service-local design remains otherwise supported by the reviewed evidence.
- Integration and owner action: deferred to a later reworked exact subject and separate current-main gate.
