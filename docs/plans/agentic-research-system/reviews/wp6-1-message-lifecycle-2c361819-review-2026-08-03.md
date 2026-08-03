# WP6.1 Message lifecycle candidate `2c361819` independent review

Date: 2026-08-03
Task ID: `019fc3a1-33d6-78e1-991c-9c96a26c49d2`
Reviewer role: fresh independent exact-subject reviewer
Verdict: `accept_exact_subject`

## Exact subject and authority

| Item | Exact identity |
|---|---|
| Review worktree | `C:\Users\steph\.codex\worktrees\0bfd\TDL` |
| Review branch | `codex/wp6-1-message-pbm02-review-2c361819-20260803` |
| Origin | `https://github.com/stephendor/TDL.git` |
| Candidate | `2c3618197bcfc7a839c81c615db6d9052ef74239` |
| Candidate subject | `[PIPELINE] P00: prevent Message receipt repair before retry conflict` |
| Candidate parent | `ad42a4313ebc928c9bb21984d72ed0108427af29` |
| Candidate tree | `728ebf9cd3106fb6fd027f5c7c75eb891971bcb8` |
| Parent tree | `d9f82d3063fcbcc31f45eec7c6b2d748b2894e86` |
| Candidate `service.py` blob | `34bcac9fd7cb6ae3a06185814c666018b86e1174` |
| Parent `service.py` blob | `5d9239e71e5847673dabf184f81b36477eed0823` |
| Candidate Message test blob | `abab8c0f81803f7f03400b3b7d8872fc08824b35` |
| Parent Message test blob | `8beb5139cd1a9cbeadd666a437f5d5761b7842e5` |
| Implementation base | `7275184e41fbfb149d2c91462ac872012d29a961` |
| Design authority | `0e842969c770811edf5c81dcd7e4f7a647e050ad:docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md` |
| Design blob | `80182047b5ad42ad8427db128e1b66b784c93177` |

The design commit is not an ancestor of the candidate. It was read directly as the
exact pinned Git object above, as required by all four review records; no current-tree
path or nearby design revision was substituted.

The worktree began detached at the exact candidate. The pre-created review branch
resolved to the same commit and was unattached to every other worktree. Exactly one
`git switch codex/wp6-1-message-pbm02-review-2c361819-20260803` attached it. The
symbolic branch, candidate, parent, tree, blobs, origin, Git dir
`C:/Users/steph/TDL/.git/worktrees/TDL8`, common dir
`C:/Users/steph/TDL/.git`, ancestry, and clean initial status were then reverified.
No fallback branch, branch creation, rename, commit switch, merge, rebase,
cherry-pick, integration, or remediation occurred.

The candidate-to-parent delta contains exactly two paths:

1. `research_system/command/service.py`
2. `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

The implementation-base-to-candidate range contains exactly 12 paths: the eight
pilot implementation/test paths and four immutable prior Message review records.
This review record makes the implementation-base-to-review range exactly 13 distinct
paths, below the design ceiling of 14. The review commit itself is restricted to this
one record.

## Setup boundary

The prescribed noninteractive commands completed at the exact candidate:

```text
repowise init --index-only --yes --no-agents --no-codex --no-onboarding
exit 0; 93.4s; 2,535 files parsed; 10,376 symbols

repowise status
exit 0; 5.1s; HEAD 2c36181; 2,538 files; 12,894 symbols
```

The initializer reported that the main-checkout seed was not an ancestor and correctly
fell back to a full index. Its pre-commit repository rewrites were:

- tracked: `.claude/CLAUDE.md`, `.mcp.json`, `.repowise/mcp.json`;
- ignored: `.vscode/extensions.json`, `.vscode/mcp.json`.

The normal post-commit Repowise updater then added the tracked metadata rewrite
`.repowise-workspace.yaml` and ignored updater/index state at
`.repowise/.update.log`, `.repowise/.update.queued`,
`.repowise/centrality_cache.pkl`, `.repowise/config.yaml`,
`.repowise/duplication_cache.pkl`, `.repowise/duplication_pairs.pkl`,
`.repowise/knowledge-graph.json`, `.repowise/parse_cache.pkl`,
`.repowise/state.json`, and `.repowise/wiki.db`. All tracked setup rewrites remain
unstaged and uncommitted; all ignored setup paths remain ignored.

The bootstrap also reported registering the external Claude Desktop configuration at
`C:\Users\steph\AppData\Roaming\Claude\claude_desktop_config.json` and Claude Code
settings at `C:\Users\steph\.claude\settings.json`. Those external setup surfaces are
not review output. No setup file was restored, discarded, staged, or committed.

## Executive decision

The candidate closes PB-M-02 at the actual durable fault boundary. After fresh active
schema and lifecycle-authority resolution, it replays and validates canonical history,
compares any retained standalone original receipt with the scoped receipt, applies the
Message command-identity discriminator, and only then writes a missing original
receipt. A changed command ID therefore conflicts before repair, while an exact ID
still reconstructs only the missing standalone receipt. Existing retained-receipt,
tampered-index, and tampered-history integrity errors remain earlier than the ordinary
Message identity conflict.

The complete 13-row Message module, all required focused controls, four unchanged
non-Message retry contracts, protected objects, and independent public-API state
probes pass. No unresolved Critical or Major defect was found in the exact subject.

One requested parent-baseline prediction was disproved. The changed-ID/missing-receipt
node is semantically red on the exact parent as required. The retained-mismatching-
receipt integrity-precedence node is already green on that parent because the parent
already compares the retained receipt before running its later identity discriminator.
That node is a preservation control, not a second remediation red. This discrepancy is
reported rather than manufactured and does not identify a candidate defect.

## Source-ordering audit

The candidate ordering in `CommandService.submit` and its helpers is:

1. exact active command-schema validation and command construction
   (`research_system/command/service.py:389-437`);
2. fresh lifecycle-authority resolution, including project, subject, actor, grant,
   risk, schema identity, payload hash, target, version, canonical authority history,
   and current grant state (`service.py:448-485`, `1046-1070`, `1383-1457`);
3. exact scoped-outcome lookup by actor, grant, command type, idempotency key,
   payload, authority hash, expected version, project, and target
   (`service.py:1460-1477`; `research_system/store/receipts.py:204-287`);
4. replay and canonical event validation, including event type, original command ID,
   payload hash, stream, version, project, event schema, actor, grant, command schema,
   and lifecycle-authority history (`service.py:852-901`, `909-944`);
5. load and compare the retained original standalone receipt, raising exact
   `IntegrityError("receipt does not match scoped index")` on disagreement
   (`service.py:902-904`);
6. apply the Message identity discriminator (`service.py:905`, `1487-1500`); then
7. for an exact command ID only, write the missing original receipt
   (`service.py:906-907`).

This is the required integrity-before-identity-before-repair order. The Message-only
PB-M-01 guard remains in `_matching_committed`: it compares command ID before the
same-submission predicate and before missing-index reconstruction
(`service.py:2479-2505`). The C-01 orphan guard remains before version observation,
Message preparation, event construction, append, or receipt/index publication
(`service.py:501-505`). The distinguishing changed-ID errors remain:

- `command ID conflicts with stored receipt` when the changed ID already has a receipt;
- `command ID conflicts with committed command` when it already has a committed event;
- `idempotency key conflicts with committed command` otherwise.

The moved helper immediately returns for non-Message commands. Candidate and parent
Git blobs are identical for ReceiptStore, ledger, schema registry, replay, authority,
reducers, lifecycle bindings, test factories, and activation-marker logic. No
ReceiptStore, ledger, schema, replay, authority, reducer, factory, activation-marker,
or non-Message helper semantic was changed by this subject.

## Four-direction durable recovery matrix

Each independent probe used a separately initialized temporary control plane, the
public decorated `CommandService.submit` seam, a real activated scoped Message grant,
and a valid immutable adapter snapshot. Snapshots compared complete control and
authority file bytes; ledger events, tail, batches, and versions; standalone receipts;
scoped indexes; runtime residue; command-ID and scope maps; replay/history;
projection; and authority ledger, projection, administration context, and exact grant
identity.

| Retained durable state and retry | Exact result |
|---|---|
| Canonical event + standalone receipt; scoped index missing; identical ID | Returns the original receipt, restores exactly the missing index, emits no event, and changes no other axis. |
| Canonical event + standalone receipt; scoped index missing; changed ID | Raises exact `ConflictError("idempotency key conflicts with committed command")` before mutation; the index remains absent. |
| Canonical event + valid scoped index; standalone receipt missing; identical ID | Revalidates canonical history and current authority, returns the original receipt, and restores exactly `receipts/<original-command-id>.json`; that file is the sole file change. |
| Canonical event + valid scoped index; standalone receipt missing; changed ID | Raises exact `ConflictError("idempotency key conflicts with committed command")`; both original and changed-ID receipts remain absent and every snapshot axis is byte/semantically identical. |

Additional integrity-precedence probes passed:

- a retained standalone receipt disagreeing with the scoped receipt raises exact
  `IntegrityError("receipt does not match scoped index")` before identity conflict and
  changes nothing;
- a tampered retained scoped index with the standalone receipt absent raises exact
  `IntegrityError("scoped accepted receipt does not match canonical ledger")`, does
  not reconstruct the receipt, and changes nothing;
- tampered canonical Message history with the standalone receipt absent raises exact
  `IntegrityError("unsupported major at 2")`, does not reconstruct the receipt, and
  changes nothing; and
- an orphan standalone Message receipt with no scoped index or canonical event still
  raises `ConflictError("receipt already exists: <command_id>")` before append and
  leaves the full domain snapshot unchanged.

The independent five-scenario probe exited `0` in 6.82s. Its exact launcher used
`C:\Users\steph\TDL\.venv\Scripts\python.exe -` with the probe supplied on standard
input, `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, empty
`PYTEST_ADDOPTS`, and empty `PYTHONPATH`. All control roots were OS temporary
directories; no repository runtime path was written.

## Parent-baseline evidence

A history-bearing `git clone --no-hardlinks --no-checkout` was created at:

`C:\Users\steph\AppData\Local\Temp\tdl-message-pbm02-parent-red-2c361819-20260803-001`

Before checkout it was configured with `core.autocrlf=false` and
`core.longpaths=true`. It then checked out exact parent
`ad42a4313ebc928c9bb21984d72ed0108427af29`, tree
`d9f82d3063fcbcc31f45eec7c6b2d748b2894e86`, retained parent production service blob
`5d9239e71e5847673dabf184f81b36477eed0823`, and materialized only candidate Message
test blob `abab8c0f81803f7f03400b3b7d8872fc08824b35`. Status contained only the staged test
module replacement. Import-path verification resolved `research_system` from that
clone.

The exact parent command was:

```powershell
& 'C:\Users\steph\TDL\.venv\Scripts\python.exe' -m pytest -q -o addopts= -p no:cacheprovider `
  'tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_changed_command_retry_does_not_reconstruct_missing_standalone_receipt' `
  'tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_changed_command_retry_preserves_retained_receipt_integrity_precedence'
```

Result: `1 failed, 1 passed in 9.45s`; wall 9.94s; exit 1.

- The first node failed semantically at the no-reconstruction assertion because the
  original standalone receipt existed after the changed-ID conflict. This is the
  intended PB-M-02 parent red, not an import, fixture, schema, or setup failure.
- The second node passed. At the exact parent, `_reconcile_scoped_authority_receipt`
  already loads and compares a retained standalone receipt before the later call to
  `_validate_message_scoped_retry_identity`. The candidate preserves that order while
  moving identity ahead of only the `stored is None` repair. Requiring this
  preservation node to be red would require the parent to lack an integrity property
  it demonstrably already has.

One exact clone-deletion attempt was policy-denied. It was not retried, and the clone
is retained at the path above as required.

## Candidate validation evidence

All Python commands used `C:\Users\steph\TDL\.venv\Scripts\python.exe` directly with
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, empty
`PYTEST_ADDOPTS`/`PYTHONPATH`, `-o addopts=`, and `-p no:cacheprovider`. Coverage,
pytest cache, bytecode, and automatic third-party plugins were disabled. `uv` was not
used.

### Exact PB-M-02 and retained-control selection

```powershell
python.exe -m pytest -q -o addopts= -p no:cacheprovider `
  test_wp6_1_message_lifecycle.py::test_message_identical_retry_reconstructs_only_missing_standalone_receipt `
  test_wp6_1_message_lifecycle.py::test_message_changed_command_retry_does_not_reconstruct_missing_standalone_receipt `
  test_wp6_1_message_lifecycle.py::test_message_changed_command_retry_preserves_retained_receipt_integrity_precedence `
  test_wp6_1_message_lifecycle.py::test_message_retry_with_changed_command_id_does_not_reconstruct_missing_scoped_index `
  test_wp6_1_message_lifecycle.py::test_adapter_retry_reconciles_missing_scoped_index_without_new_message_event `
  test_wp6_1_message_lifecycle.py::test_orphan_message_receipt_is_rejected_before_append_without_mutation `
  test_wp6_1_message_lifecycle.py::test_delivery_retry_and_changed_idempotency_or_command_identity_are_atomic `
  test_wp6_1_message_lifecycle.py::test_adapter_retry_rejects_foreign_scoped_index_without_mutation `
  test_wp6_1_message_lifecycle.py::test_adapter_retry_rejects_unsupported_major_history_without_mutation
```

The command used each full repository node ID; the shortened display above shares the
same module prefix. Result: `9 passed in 8.16s`; wall 8.71s; exit 0.

### Complete Message module

```powershell
python.exe -m pytest -q -o addopts= -p no:cacheprovider tests/research_system/integration/test_wp6_1_message_lifecycle.py
```

Result: `103 passed in 41.87s`; wall 42.37s; exit 0.

### Exact 13-row collection

```powershell
python.exe -m pytest --collect-only -q -o addopts= -p no:cacheprovider tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_row_common_axis_matrix
```

Result: exactly `13 tests collected in 0.39s`; wall 0.75s; exit 0.

### Four unchanged non-Message scoped-retry controls

```powershell
python.exe -m pytest -q -o addopts= -p no:cacheprovider `
  tests/research_system/integration/test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart `
  tests/research_system/integration/test_authority_grant_source.py::test_rejected_exact_retry_is_returned_before_current_authority_recheck `
  tests/research_system/integration/test_authority_grant_source.py::test_scoped_retry_rejects_reused_unrelated_command_id `
  tests/research_system/integration/test_scoped_authority_grant_activation.py::test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant
```

Result: `4 passed in 45.34s`; wall 46.09s; exit 0.

No broader package or full repository suite was triggered. The complete 103-node
family module, exact shared callers, public fault-state probes, and unchanged shared
API/blob evidence cover the demonstrated dependency surface. No narrow failure or
shared-API change justified expansion.

## Complete 13-row census

The pinned design, accepted owner-source catalogue, and executable `MESSAGE_ROWS`
agree on exactly 13 unique rows with no missing or extra identity:

| # | Catalogue row | Command -> event | Legal transition |
|---:|---|---|---|
| 1 | `message.publish_assignment` | `PublishMessage` -> `MessagePublished` | none -> published |
| 2 | `message.publish_acknowledgement` | `PublishMessage` -> `MessagePublished` | none -> published |
| 3 | `message.publish_progress` | `PublishMessage` -> `MessagePublished` | none -> published |
| 4 | `message.publish_input_request` | `PublishMessage` -> `MessagePublished` | none -> published |
| 5 | `message.publish_escalation` | `PublishMessage` -> `MessagePublished` | none -> published |
| 6 | `message.publish_report` | `PublishMessage` -> `MessagePublished` | none -> published |
| 7 | `message.publish_review_request` | `PublishMessage` -> `MessagePublished` | none -> published |
| 8 | `message.publish_review_response` | `PublishMessage` -> `MessagePublished` | none -> published |
| 9 | `message.publish_decision_request` | `PublishMessage` -> `MessagePublished` | none -> published |
| 10 | `message.publish_handoff` | `PublishMessage` -> `MessagePublished` | none -> published |
| 11 | `message.deliver` | `RecordMessageDelivery` -> `MessageDelivered` | published -> delivered |
| 12 | `message.acknowledge` | `AcknowledgeMessage` -> `MessageAcknowledged` | delivered -> acknowledged |
| 13 | `message.delivery_failure` | `RecordMessageDeliveryFailure` -> `MessageDeliveryFailed` | published -> delivery_failed |

All four command and four event bindings remain active at version `1.0.0`. The
13-row common-axis matrix executes authority, retry command/key identity, failed
mutation, replay, projection, decisive negative, and an applicable terminal race or
explicit publication N/A for every row. The three new fault-state controls use
`RecordMessageDelivery` as the representative path through the shared Message
reconciliation helper.

## Complete prior-finding dispositions

The exact design and all four existing Message review records were read in full.
Original finding meanings, rather than later shorthand relabelling, control this table.

| Prior review record | Candidate Git blob |
|---|---|
| `wp6-1-message-lifecycle-b353109-review-2026-08-02.md` | `4b89a507ee6ac1699600b38458f7614b386243b6` |
| `wp6-1-message-lifecycle-b400001-rereview-2026-08-02.md` | `29763b912b391163690b8bc1f300e994fb9a6f80` |
| `wp6-1-message-lifecycle-62a87fd-review-2026-08-02.md` | `5a0e6e6256c38deeb338307d49e2655305fdcdf7` |
| `wp6-1-message-lifecycle-5c77239-review-2026-08-03.md` | `4c9b910cde90e732d32a01820b7d29f98bdd6cb5` |

| Finding | Original finding | Exact current disposition |
|---|---|---|
| C-01 Critical | Early accepted adapter retry bypassed project, current authority, scoped index, and canonical lifecycle history; later review also exposed orphan standalone receipt mutation. | Closed. Fresh authority/canonical reconciliation remains first, and the Message-only orphan guard rejects receipt-without-index/event before append. |
| C-02 Critical | Recognized Message events relabelled under the generic event schema bypassed exact producer/schema provenance. | Closed. The Message-specific exact-schema guard remains before projection publication; generic legacy Task controls remain compatible. |
| M-01 Major | Shared scoped-receipt changes regressed four unchanged non-Message retry contracts and distinguishing errors. | Closed. The shared behavior and all four unchanged controls pass; the moved helper is a Message no-op for non-Message commands. |
| M-02 Major | Caller-owned nested Message payloads could alias and mutate the cached accepted ledger representation. | Closed. All four Message event constructors still deep-copy payloads before the ledger boundary. |
| M-03 Major | The required executable common-axis matrix did not cover all 13 rows. | Closed at the prior settled granularity. Exactly 13 row-keyed nodes collect and the complete module passes. |
| m-01 Minor | Plain `control_plane(auto_authority=False)` dropped an explicitly supplied adapter snapshot. | Closed. The factory still forwards the immutable registry and the plain manually activated path remains covered. |
| PB-M-01 Major | With event and receipt retained but scoped index missing, a changed Message command ID received original acceptance and reconstructed the index. | Closed. `_matching_committed` checks Message command identity before same-submission reconstruction; changed-ID recovery leaves the index absent. |
| PB-M-02 Major | With event and scoped index retained but standalone receipt missing, a changed Message command ID reconstructed the receipt before conflict. | Closed at this candidate. Canonical and retained-receipt integrity checks precede Message identity, which precedes repair. |

The newest prior review's shorthand table changed the descriptions attached to several
older IDs. This review preserves the immutable original meanings above. Its row-13
transition shorthand `published -> failed` is also normalized here to the design,
catalogue, reducer, and executable identity `published -> delivery_failed`. Neither
record inconsistency changes candidate behavior.

## Static and protected identities

Exact static commands and results were:

```text
git diff --name-status ad42a4313ebc928c9bb21984d72ed0108427af29 2c3618197bcfc7a839c81c615db6d9052ef74239
exit 0; 0.033s; exactly 2 paths

git diff --name-status 7275184e41fbfb149d2c91462ac872012d29a961 2c3618197bcfc7a839c81c615db6d9052ef74239
exit 0; 0.035s; exactly 12 paths

python.exe -m ruff check --no-cache <eight pilot implementation/test paths>
All checks passed!; exit 0; 0.113s

python.exe -m ruff format --check --no-cache <eight pilot implementation/test paths>
8 files already formatted; exit 0; 0.096s
```

The eight paths were `research_system/authority.py`,
`research_system/command/lifecycle.py`, `research_system/command/reducers.py`,
`research_system/command/service.py`, `research_system/projection/replay.py`,
`research_system/schema_registry.py`, `tests/research_system/factories.py`, and
`tests/research_system/integration/test_wp6_1_message_lifecycle.py`.

Base, parent, candidate, and live main all resolve the protected trees identically:

| Protected registry | Exact tree | Files |
|---|---|---:|
| Command schemas | `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` | 87 |
| Event schemas | `154ffc4bdde82fe903718734687e7a62797b1f69` | 86 |

SHA-256 over exact raw candidate Git-object bytes produced:

| Schema | Bytes | Raw SHA-256 |
|---|---:|---|
| `PublishMessage` | 91,363 | `14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c` |
| `MessagePublished` | 91,354 | `f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f` |
| `RecordMessageDelivery` | 7,566 | `9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828` |
| `MessageDelivered` | 10,483 | `7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388` |
| `AcknowledgeMessage` | 7,280 | `3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d` |
| `MessageAcknowledged` | 10,221 | `576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be` |
| `RecordMessageDeliveryFailure` | 7,303 | `afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89` |
| `MessageDeliveryFailed` | 10,212 | `0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5` |

The raw-object hash pass exited `0` in 0.705s. No accepted schema, catalogue,
manifest, strict-contract, owner-decision, or raw-byte object changed. The protected
13-row census is unchanged.

## Current-main composition

The exact read-only refresh was:

```text
git fetch --no-tags origin main
exit 0; 1.429s
```

Pre-fetch `origin/main`, post-fetch `origin/main`, and live `git ls-remote` all resolve
to `dd67dca5ff69c1aeefb903c63f3437df357280c0`, tree
`50628117946f3dd4c5fda2ca9d9d100447142515`, service blob
`35f5c1b2488cc0c2d56f2fcbe7663d4f2958c407`. Candidate and current main diverge at
exact merge base `7275184e41fbfb149d2c91462ac872012d29a961`. The PR #207 merge
`9810fa98ba6f2333522b9afd659da5f335bbd79d`, its follow-up head
`b0d3e83c0e2e8b91ec563479dc46a22b3e1c108c`, and KAN-67 repair
`f7cbc84874c50d727e8947b0b98255e0dc610dc1` are all ancestors of live main.

WP6.4 candidate `3d5a1a7bdf6af80f47e6be3aa68c4d32708fd1ab` is an ancestor of neither
the reviewed candidate nor live main and remains excluded.

The nonintegrating command

```text
git merge-tree 7275184e41fbfb149d2c91462ac872012d29a961 2c3618197bcfc7a839c81c615db6d9052ef74239 dd67dca5ff69c1aeefb903c63f3437df357280c0
```

exited `0` in 0.076s. Four paths changed on both sides: `authority.py`,
`command/service.py`, `projection/replay.py`, and `schema_registry.py`. Exactly one
text conflict hunk occurs in `service.py`. A later explicitly authorized integration
must preserve this semantic order:

1. main's activation-marker status validation before committed matching;
2. on a committed match, materialize or return the receipt, remove the committed
   activation marker, and return;
3. immediately afterward, the pilot's Message orphan-receipt guard;
4. main's `_reconcile_scoped_activation_receipt` before common
   `_reconcile_scoped_authority_receipt`;
5. PB-M-01 command identity before same-submission and missing-index reconstruction;
6. PB-M-02 retained-receipt integrity before identity before missing-receipt repair.

An ours/theirs resolution would lose either KAN-67 cleanup or the Message guard. The
other three shared files auto-merge textually but still require semantic regression at
an eventual integration head. No integration tree was checked out, written, staged,
or committed.

## Remaining risk and boundary

- The parent-baseline instruction incorrectly predicted a red result for the retained-
  receipt integrity-preservation node. Direct parent execution and source ordering
  prove it was already green. This is an evidence-contract discrepancy, not an exact-
  subject behavior defect.
- The three new recovery tests use `RecordMessageDelivery` as the representative
  shared-helper route rather than a 13-row-by-recovery-state Cartesian product. The
  normal common-axis matrix still exercises all 13 rows; this is the prior settled
  representative granularity.
- The cumulative pilot range includes `research_system/authority.py` and
  `research_system/command/lifecycle.py`, which are absent from the pinned design's
  literal initial path allowlist. That pre-existing provenance/process discrepancy is
  documented in the prior review chain and is not a candidate delta.
- Current main requires the explicit one-hunk semantic composition above. This review
  does not authorize that integration or infer it from an automatic merge.
- The policy-denied parent clone remains at its reported OS temporary path.
- Repowise setup residue remains deliberately dirty and outside the review commit.
- No package or repository-wide suite was run because no narrow failure or shared-API
  change triggered the broader tier.

This decision is bound only to the exact candidate and its protected identities. It
does not constitute owner acceptance, merge or PR authority, Jira completion,
CodeRabbit invocation, KAN-67 integration, WP6.4 work, W11 work, external action, or
permission to dispatch a later lifecycle family.
