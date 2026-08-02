# WP6.1 Message lifecycle exact-subject review — candidate `b353109`

Date: 2026-08-02  
Reviewer role: fresh independent exact-subject reviewer  
Verdict: **`rework_required`**

## Exact subject and authority

- Review worktree: `C:\Users\steph\.codex\worktrees\59b1\TDL`
- Review branch: `codex/wp6-1-message-lifecycle-review-b353109-20260802`
- Candidate: `b3531092814efbd2ff3f1fb094dd929032642d1e`
- Parent: `7275184e41fbfb149d2c91462ac872012d29a961`
- Candidate tree: `bcc703272c491aee31300690628774ebc8b74e21`
- Parent ancestry check: exit `0`
- Corrected design authority: commit `0e842969c770811edf5c81dcd7e4f7a647e050ad`, path `docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md`, blob `80182047b5ad42ad8427db128e1b66b784c93177`

The initial dispatch named `docs/plans/agentic-research-system/2026-08-02-wp6-lifecycle-family-pilot-design.md`. That path does not exist in the pinned authority commit. The dispatcher corrected this as a transcription error and confirmed the immutable `implementation/06m-...` blob above as the sole authority. This is provenance context, not an implementation finding.

The app worktree started detached. After confirming that detached `HEAD` and the named branch both resolved to the exact candidate, the reviewer made the one permitted deterministic switch to the named branch. Before the review-record write, the resolved cwd, symbolic branch, `HEAD`, branch ref, ancestry, tree, and clean status were reconfirmed. No fallback branch or commit switch was used.

The implementation diff contains exactly the eight allowed paths:

1. `research_system/authority.py`
2. `research_system/command/lifecycle.py`
3. `research_system/command/reducers.py`
4. `research_system/command/service.py`
5. `research_system/projection/replay.py`
6. `research_system/schema_registry.py`
7. `tests/research_system/factories.py`
8. `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

No implementation, test, schema, runtime-state, Jira, GitHub, PR, or external-review remediation was performed.

## Executive decision

The normal, uncorrupted first-submit path implements most of the intended Message state machine correctly: all four command/event pairs are actively bound to the protected exact schemas; the ten publication discriminants produce closed payloads; delivery, acknowledgement, and failure enforce the intended state, content, recipient, adapter, actor, and source-position joins; and the exact-schema replay route rejects the tested provenance divergences.

The candidate nevertheless cannot be accepted. Two paths permit invalid acceptance or evidence interpretation across an explicit trust boundary:

- the candidate-specific adapter retry shortcut returns an accepted receipt before project, current authority, scoped idempotency, and lifecycle-history validation; and
- recognized Message events relabelled to the generic event schema are replayed as Message state without the exact producer/schema binding.

In addition, the candidate regresses four unchanged non-Message scoped-retry contracts, exposes accepted Message content through a mutable cached-ledger alias, does not implement the design-mandated common-axis matrix for all 13 rows, and drops the configured adapter registry from one test-factory construction path.

## Severity-ranked findings

### C-01 — Critical — Accepted adapter retries bypass project, authority, scoped-index, and lifecycle-history validation

**Claim.** `CommandService.submit` invokes `_accepted_message_adapter_retry` immediately after taking an unverified ledger snapshot and before lifecycle authority resolution, scoped-receipt reconciliation, or replay (`research_system/command/service.py:449-453`). The shortcut (`service.py:1138-1161`) compares command type, stream, payload hash, idempotency key, actor, grant, schema identity, and stream version, but not the command `project_id`, recorded event type/schema/provenance, current lifecycle authority, or scoped idempotency index.

**Concrete counterexamples.** Independent temporary-control-root probes established both failures:

1. After a valid publication and delivery, resubmitting the same delivery command ID, payload, key, actor, grant, and version with a different syntactically valid `project_id` returned the original accepted receipt and left the event tail unchanged. The normal Message preparation check at `service.py:1163-1177` would reject that project binding, but the shortcut returns before reaching it.
2. After a valid publication and delivery, the temporary delivery record was changed to event schema version `2.0.0` and rehashed. Direct registry-backed replay raised `IntegrityError: unsupported major at 2`; resubmitting the identical delivery command still returned the same accepted receipt.

The same ordering can return or reconstruct an operational receipt without repairing a missing scoped index after a ledger-append/scoped-index-publication interruption.

**Impact.** This is false accepted authority/evidence for `message.deliver` and `message.delivery_failure`. It defeats the requested fail-closed project and exact-history boundary and can hide a recovery condition behind a successful receipt.

**Required disposition.** Rework the retry path so an accepted retry is returned only after the exact project, current authority contract, canonical recorded event/provenance, and scoped-idempotency state have been validated or atomically reconciled. Add decisive foreign-project, unsupported-major/forged-history, and missing-scoped-index retry tests. No remediation was made in this review.

### C-02 — Critical — Generic-schema downgrade bypasses exact Message replay provenance

**Claim.** `validate_exact_lifecycle_envelope` selects exact validation solely by `schema_id` and returns `None` for a generic ID (`research_system/command/lifecycle.py:81-95`). `_validate_recorded_event_schema` deliberately returns early for `ars://core/event` (`research_system/projection/replay.py:101-108`), and the active lifecycle-binding check also sees no exact binding. Replay then routes by the recognized Message `event_type` and reduces the record as Message state (`replay.py:455-464`, `603-608`, `646-687`).

**Concrete counterexample.** A valid `MessagePublished` event was deep-copied, relabelled from `ars://core/event/MessagePublished` to `ars://core/event`, and rehashed. `replay([forged], schema_registry=runtime_registry)` accepted it and produced `status=published`. The current test at `tests/research_system/integration/test_wp6_1_message_lifecycle.py:1492-1552` changes both schema ID and event type, so it proves a missing reducer route rather than the recognized-Message downgrade.

Generic historical Task compatibility is an existing deliberate behavior, but there was no pre-activation generic Message history to preserve. Activating the new Message routes without a Message-specific cutover/provenance guard newly exposes this bypass.

**Impact.** A record that does not carry the protected Message event identity or producer binding can enter recovered Message state and projection output. This corrupts the evidence boundary the exact active bindings are meant to establish.

**Required disposition.** Add a Message activation/cutover rule that rejects recognized Message event types under the generic schema without globally breaking legitimate legacy generic histories. Add the exact recognized-type/generic-schema replay negative. No remediation was made in this review.

### M-01 — Major — The shared scoped-receipt helper regresses unchanged non-Message retry contracts

**Claim.** Candidate `service.py:1508-1515` changed `_return_scoped_receipt_or_raise` so every fresh command ID paired with an existing scoped receipt unconditionally raises an idempotency-key conflict. The parent implementation distinguished an already-used command ID from a fresh equivalent retry and otherwise returned the original scoped receipt. The helper is shared by non-Message revocation, release-publication, authority-activation, and issued-grant-revocation paths through `service.py:779-838`.

**Direct evidence.** Four exact existing nodes fail at candidate line 1515:

- `test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart`
- `test_authority_grant_source.py::test_rejected_exact_retry_is_returned_before_current_authority_recheck`
- `test_authority_grant_source.py::test_scoped_retry_rejects_reused_unrelated_command_id`
- `test_scoped_authority_grant_activation.py::test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant`

The first, second, and fourth lose the contract that a fresh command ID with the same scoped idempotency submission returns the original accepted or rejected receipt. The third requires the distinguishing `command ID` conflict for a command ID already committed elsewhere; the candidate instead reports `idempotency key conflicts with committed command`.

Both affected test files are byte-identical between parent and candidate: blobs `6915ee2897050220587dcf825aef478c54248bb8` and `d1d709ba9f82da5691484f53c78310093b520ef3`, respectively. The failures are therefore on the candidate's shared-helper change, not changed expectations.

**Impact.** Existing non-Message callers lose exactly-once recovery and distinguishing command-ID/key conflict semantics. This is a direct regression outside the pilot family caused by a shared seam in the allowed diff.

**Required disposition.** Restore the established shared retry semantics while keeping Message-specific conflicts at the appropriate Message boundary. All four existing nodes must pass at the reworked exact subject.

### M-02 — Major — Accepted Message content is externally aliasable in the cached ledger snapshot

**Claim.** Submit shallow-copies only the command envelope (`service.py:399`), and candidate Message event construction reuses `command.envelope["payload"]` (`service.py:2598-2609`). The existing ledger path shallow-copies the draft result, retains the nested payload object (`research_system/store/ledger.py:412`, `426-440`), and stores the event dictionaries in its cached frozen snapshot (`ledger.py:533-539`). The frozen dataclass does not make nested dictionaries immutable.

**Concrete counterexample.** After an accepted `PublishMessage`, changing `submitted_command["payload"]["body"]` changed `ledger.snapshot().events[-1]["payload"]["body"]` while a fresh durable JSONL read remained unchanged. A subsequent valid delivery failed with `IntegrityError: event hash mismatch at 1`; the durable event count remained one.

**Impact.** A caller retaining its submitted dictionary can mutate the service-local representation of an accepted immutable Message stream without an append. This creates false integrity failures and process-local divergence from durable history. The underlying shallow ledger cache predates the candidate, but the candidate introduces the Message-specific alias by passing the caller payload through unchanged.

**Required disposition.** Establish a deep immutable/copy boundary before an accepted Message payload enters the ledger draft/cache, and add a post-submit caller-mutation test. Any change to `store/ledger.py` remains subject to the design's central-owner stop condition; a Message-local copy is the bounded first option.

### M-03 — Major — The required common-axis executable matrix does not cover all 13 rows

**Claim.** The exact design requires the executable matrix to enumerate all 13 row IDs once and requires every row to pass authority, idempotency, concurrency, failed-mutation, replay, projection, and applicable decisive-negative axes (authority blob lines 918-945 and 1009-1025).

`MESSAGE_ROWS` contains the 13 IDs but drives only `test_message_rows_have_exact_runtime_schema_bindings` (`tests/research_system/integration/test_wp6_1_message_lifecycle.py:22-62`). The ten publication discriminants receive single-submit positive coverage at lines 484-508. Exact retry and changed command-ID/key behavior is exercised only for `RecordMessageDelivery` at lines 1091-1134. Authority, concurrency, replay, projection, and distinguishing negatives are likewise sampled through selected Message commands/discriminants rather than applied as the row-ID matrix required by the authority.

**Impact.** The green 77-test module does not prove the literal 13-of-13 completion rule. In particular, `PublishMessage`, `AcknowledgeMessage`, and `RecordMessageDeliveryFailure` lack equivalent exact retry/key/ID coverage, and the ten publication rows do not each traverse the common axes.

**Required disposition.** Implement a row-keyed matrix that records every exact catalogue row once and applies each common axis (with explicit applicability where a race/negative does not make semantic sense). A wildcard binding census or selected representative command is not the specified completion evidence.

### m-01 — Minor — `control_plane` silently drops the configured adapter registry when `auto_authority=False`

`tests/research_system/factories.py:491-500` passes `message_adapter_registry` to the authority service and lines 526-539 pass it to the governed replacement, but the plain domain `CommandService` constructed at lines 504-512 omits the argument. Thus `control_plane(..., auto_authority=False, message_adapter_registry=...)` silently creates a fail-closed empty adapter snapshot despite the caller's explicit configuration. This is a test-harness defect, not a production authorization bypass; default Scope/Task behavior remains unchanged.

Required disposition: pass the explicit snapshot to the plain service and add one manually activated positive adapter path with `auto_authority=False`.

## Thirteen-row semantic audit

All row identities below were checked against the frozen catalogue and implementation. “Normal path conforms” does not waive M-03: each row still lacks the authority-mandated complete executable axis record.

| Exact catalogue row | Command/event and legal transition | Review disposition |
|---|---|---|
| `message.publish_assignment` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed assignment payload and normal transition conform; common axes incomplete. |
| `message.publish_acknowledgement` | `PublishMessage` / `MessagePublished`; `none -> published` | Correlation must equal opaque external/legacy `reply_to_message_id`; self-link rejects; normal path conforms; common axes incomplete. |
| `message.publish_progress` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed progress payload and normal transition conform; common axes incomplete. |
| `message.publish_input_request` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed input-request payload and normal transition conform; common axes incomplete. |
| `message.publish_escalation` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed escalation payload and normal transition conform; common axes incomplete. |
| `message.publish_report` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed report payload and normal transition conform; common axes incomplete. |
| `message.publish_review_request` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed review-request payload and normal transition conform; common axes incomplete. |
| `message.publish_review_response` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed review-response payload and normal transition conform; common axes incomplete. |
| `message.publish_decision_request` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed decision-request payload and normal transition conform; common axes incomplete. |
| `message.publish_handoff` | `PublishMessage` / `MessagePublished`; `none -> published` | Closed handoff payload and normal transition conform; common axes incomplete. |
| `message.deliver` | `RecordMessageDelivery` / `MessageDelivered`; `published -> delivered` | Content, recipients, evidence, and adapter join conform on the normal path; C-01 invalidates retry acceptance; common axes incomplete. |
| `message.acknowledge` | `AcknowledgeMessage` / `MessageAcknowledged`; `delivered -> acknowledged` | Delivered state is checked separately; actor must be a published recipient; content/recipients bind; `source_position` is the exact `MessagePublished.global_position`; common axes incomplete. |
| `message.delivery_failure` | `RecordMessageDeliveryFailure` / `MessageDeliveryFailed`; `published -> delivery_failed` | Adapter capability/evidence and terminal divergence conform on the normal path; C-01 invalidates retry acceptance; common axes incomplete. |

The reducer rejects publication on an existing stream, delivery before publication or after a terminal state, acknowledgement before delivery or after terminal divergence, and failure before publication or after delivery/acknowledgement/failure. The focused module's legal/illegal transition and race tests passed, including one-winner delivery/failure and acknowledgement races. The distinguishing negative-state implementation is sound on the normal exact-history path; M-03 is the missing per-row proof, and C-01/C-02 are bypass paths around that normal validation.

## Authority, content, linkage, idempotency, and replay conclusions

### Normal authority path

- `MessageAdapterRegistration` is a typed frozen dataclass. Its canonical content binds the configured adapter ID, project, registry revision, status, effective interval, command capabilities, and allowed actors; the constructor validates its supplied content hash.
- `CommandService` constructor-injects a tuple snapshot and defaults to an empty fail-closed registry. Missing, ambiguous, retired/suspended, premature/expired, wrong-project, wrong-capability, and wrong-actor records reject.
- Lifecycle resolution binds the exact project, Message subject, command schema identity/version/hash, actor, risk, stream/version, and command payload hash to canonical authority evidence. Sender and acknowledger identities are joined to the resolved actor/recipient rules.
- This is deliberately a service-local owner-governed pilot snapshot, not real W7 adapter or general agent/service activation. Non-owner general actor reachability remains a later integration concern, not a defect against this bounded pilot.
- C-01 overrides these conclusions for the early accepted adapter-retry path.

### Content and linkage

- Online publication sets `content_sha256` to SHA-256 of canonical bytes of `MessagePublished.payload`. That payload is the exact command payload, so it agrees with `command_payload_hash`; delivery and acknowledgement validate the same hash.
- Acknowledgement separately requires `delivered` state and then requires `source_position` to equal the original `MessagePublished.global_position`.
- `reply_to_message_id` is preserved as opaque external/legacy lineage and is not required to resolve locally. A self-link rejects. For the acknowledgement publication discriminant, `correlation_message_id == reply_to_message_id` is required. Normal retry/replay preserves and validates these fields.
- M-02 violates the immutable service-local content representation after an otherwise accepted publication.

### Exactly-once and rejected mutation

- Message commands use the composite submission lock. The normal candidate tests establish one stable winner and unchanged loser state for the tested acknowledgement and delivery/failure races.
- Every non-accepted Message receipt returns without domain receipt/idempotency persistence (`service.py:950-953`), and the rejection snapshots include ledger tail, stream versions, accepted receipts, idempotency indexes, command indexes, projection, and replay state.
- C-01 bypasses retry reconciliation; M-01 is a direct non-Message exactly-once regression; M-03 leaves most row-specific retry/conflict axes unproven.

### Replay and projection

- With exact Message schema IDs, replay validates source command identity/hash/version, content, source position, reply/correlation linkage, sender/acknowledger actor binding, lifecycle order, and terminal divergence. Unsupported major versions fail before projection publication in the tested normal route.
- C-02 bypasses all exact Message binding validation through the generic schema ID. C-01 returns accepted before the same replay validation can run.

## Protected schema and runtime-binding evidence

The protected materialized registries are byte/set-identical between parent and candidate:

| Registry | Parent tree | Candidate tree | Entries |
|---|---|---|---:|
| Commands | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | 87 |
| Events | `154ffc4bdde82fe903718734687e7a62797b1f69` | `154ffc4bdde82fe903718734687e7a62797b1f69` | 86 |

Direct SHA-256 over raw bytes read from the candidate Git object produced:

| Active identity (`1.0.0`) | Bytes | SHA-256 |
|---|---:|---|
| `PublishMessage` | 91,363 | `14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c` |
| `MessagePublished` | 91,354 | `f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f` |
| `RecordMessageDelivery` | 7,566 | `9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828` |
| `MessageDelivered` | 10,483 | `7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388` |
| `AcknowledgeMessage` | 7,280 | `3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d` |
| `MessageAcknowledged` | 10,221 | `576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be` |
| `RecordMessageDeliveryFailure` | 7,303 | `afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89` |
| `MessageDeliveryFailed` | 10,212 | `0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5` |

Runtime inspection and the 13-row binding test confirm four command and four producer-specific event bindings, exact version `1.0.0`, and `SchemaRegistry.resolve_identity(...).raw_bytes`/SHA agreement. Unsupported command binding/version mismatches are rejected before the submission lock or publication. No protected schema byte or materialized registry-set mutation occurred.

## Independent validation evidence

All Python/pytest commands used `C:\Users\steph\TDL\.venv\Scripts\python.exe` directly with `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTEST_ADDOPTS=''`, `-o addopts=''`, and `-p no:cacheprovider`. `uv` was not used.

### Message module

```text
python.exe -m pytest -q -o addopts='' -p no:cacheprovider tests/research_system/integration/test_wp6_1_message_lifecycle.py
77 passed in 37.26s
```

### Exact command-service, replay, and schema-registry nodes

```text
tests/research_system/unit/test_command_service.py::test_create_task_vertical_uses_exact_activated_schema_identity
tests/research_system/unit/test_command_service.py::test_create_task_rejects_unbound_schema_version_without_writes
tests/research_system/unit/test_command_service.py::test_identical_retry_returns_original_receipt_and_one_batch
tests/research_system/unit/test_command_service.py::test_same_idempotency_key_with_changed_payload_conflicts
tests/research_system/unit/test_command_service.py::test_reused_command_id_conflicts_before_second_batch
tests/research_system/unit/test_command_service.py::test_committed_batch_reconstructs_missing_receipt_on_retry
tests/research_system/unit/test_replay.py::test_s010_unknown_major_fails_before_projection_publication
tests/research_system/unit/test_replay.py::test_replay_rejects_wrong_recorded_command_schema_hash
tests/research_system/unit/test_replay.py::test_replay_rejects_wrong_recorded_command_schema_version
tests/research_system/unit/test_replay.py::test_replay_rejects_absent_command_provenance_after_default_cutover
tests/research_system/unit/test_replay.py::test_replay_validates_recorded_specific_event_with_inert_registry
tests/research_system/unit/test_schema_registry.py::test_validation_rejects_wrong_recorded_source_hash
tests/research_system/unit/test_schema_registry.py::test_materialized_schema_is_inert_until_exact_binding_is_active
tests/research_system/unit/test_schema_registry.py::test_runtime_bindings_activate_first_scope_task_slice_and_t2_verticals
tests/research_system/unit/test_schema_registry.py::test_t2_event_versions_coexist_and_v1_1_identity_binds_exact_raw_bytes

15 passed in 50.22s
```

### Shared-helper regression nodes

First exact pair:

```text
tests/research_system/integration/test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart
tests/research_system/integration/test_scoped_authority_grant_activation.py::test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant

2 failed at research_system/command/service.py:1515
```

Dependency-triggered exact expansion:

```text
tests/research_system/integration/test_authority_grant_source.py::test_rejected_exact_retry_is_returned_before_current_authority_recheck
tests/research_system/integration/test_authority_grant_source.py::test_scoped_retry_rejects_reused_unrelated_command_id

2 failed in 53.40s at research_system/command/service.py:1515
```

The failures are the named candidate regression and conflict-distinction evidence; no package or full suite was justified after this decisive shared-helper result.

### Adversarial temporary-control-root probes

```text
foreign-project exact adapter retry -> same accepted receipt; event tail unchanged
direct replay after delivery schema_version=2.0.0 -> IntegrityError: unsupported major at 2
same delivery retry after that unsupported-major record -> accepted; same receipt=True
recognized MessagePublished relabelled to ars://core/event -> replay status=published
post-submit caller payload mutation -> cached snapshot changed; durable reread unchanged
subsequent valid delivery in that process -> IntegrityError: event hash mismatch at 1; durable event count=1
```

The probes wrote only disposable OS temporary control roots and did not touch repository `.research-system` runtime state.

### Formatting and diff integrity

```text
python.exe -m ruff check <all eight changed Python paths>
All checks passed!

python.exe -m ruff format --check <all eight changed Python paths>
8 files already formatted

git diff --check 7275184e41fbfb149d2c91462ac872012d29a961 b3531092814efbd2ff3f1fb094dd929032642d1e
exit 0

git diff --name-only 7275184e41fbfb149d2c91462ac872012d29a961 b3531092814efbd2ff3f1fb094dd929032642d1e
exactly the eight allowlisted paths; no extras
```

No pytest cache, coverage addopts, bytecode, setup-only Repowise/Claude rewrite, or external review service was created or used. Status was clean immediately before this review-record write.

## Decision audit and remaining integration risk

- **Exact candidate acceptance:** reject; `rework_required` because C-01 and C-02 permit invalid accepted/evidence states and M-01 is a demonstrated shared regression.
- **Protected schemas:** keep unchanged; all protected trees and eight raw hashes match.
- **Message pilot architecture:** keep the bounded service-local typed snapshot and existing single-stream design, but close the retry, exact-provenance, and immutability boundaries before re-review.
- **W7 activation:** defer; this candidate is not and does not authorize real W7 adapter/actor activation.
- **Owner/merge decision:** defer to a later exact reworked candidate and separate owner decision; this review does not authorize merge or dispatch.
- **PR #207 integration condition:** PR #207 was not inspected, merged, cherry-picked, or reviewed. Before any later merge, an integration candidate must reconcile the live main/PR #207 `service.py` seam if it overlaps this Message work. This is a remaining integration condition only, not a finding on this exact subject.

## Final verdict

**`rework_required`**

The exact candidate is not acceptable until the two Critical boundaries and three Major findings are closed and independently re-reviewed at a new exact subject. The protected schema evidence and normal-path passing tests remain useful positive evidence, but they do not override the demonstrated invalid retry/replay acceptance or the shared non-Message regressions.
