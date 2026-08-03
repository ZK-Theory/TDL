# WP6.1 Message lifecycle candidate `5c77239` independent review

Date: 2026-08-03
Task ID: `019fc3a1-33d6-78e1-991c-9c96a26c49d2`
Reviewer role: fresh independent exact-subject reviewer
Review branch: `codex/wp6-1-message-pbm01-review2-5c77239-20260803`
Verdict: `rework_required`

## Exact subject and authority

| Item | Exact identity |
|---|---|
| Candidate | `5c77239a4a30d9021605695ff3fa351c4f3e77b9` |
| Candidate subject | `[PIPELINE] P00: reject changed Message retry during index recovery` |
| Candidate parent | `29393875994a750886072825ca04be03cbe5427e` |
| Candidate tree | `5adb71549d1ce8b34ef3d1dd54ee6392727e82d7` |
| Candidate `research_system/command/service.py` blob | `5d9239e71e5847673dabf184f81b36477eed0823` |
| Parent `research_system/command/service.py` blob | `0f2def9a62a6f7de6d4d815f7ab2c193172ad70c` |
| Candidate Message test blob | `8beb5139cd1a9cbeadd666a437f5d5761b7842e5` |
| Unchanged `research_system/store/receipts.py` blob | `cae814f496f0cdb8db99abd3e850074e28df50ff` |
| Pinned design object | `0e842969c770811edf5c81dcd7e4f7a647e050ad:docs/plans/agentic-research-system/implementation/06m-wp6-lifecycle-family-pilot-design.md` |
| Pinned design blob | `80182047b5ad42ad8427db128e1b66b784c93177` |
| Implementation base | `7275184e41fbfb149d2c91462ac872012d29a961` |
| Origin | `https://github.com/stephendor/TDL.git` |

The candidate delta against its exact parent contains only:

- `research_system/command/service.py`
- `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

That delta is 2 paths and 50 insertions. The cumulative implementation-base-to-candidate range contains 11 repository paths: the 8 pilot implementation/test paths and the 3 prior Message review records. Including this decision record makes the implementation-base-to-decision range 12 paths. No production, test, schema, setup, or other documentation path is part of this review commit.

## Checkout and setup boundary

The worktree began at detached `HEAD` on the exact candidate. The pre-created review branch resolved to that same commit and was unattached to any other worktree. Exactly one `git switch codex/wp6-1-message-pbm01-review2-5c77239-20260803` attached it; no branch or fallback commit was created. Before this record was written, the reverified state was:

- cwd: `C:\Users\steph\.codex\worktrees\f06c\TDL`
- branch: `codex/wp6-1-message-pbm01-review2-5c77239-20260803`
- `HEAD`: `5c77239a4a30d9021605695ff3fa351c4f3e77b9`
- Git dir: `C:/Users/steph/TDL/.git/worktrees/TDL8`
- common dir: `C:/Users/steph/TDL/.git`
- staged paths: none

The prescribed commands `repowise init --index-only --yes --no-agents --no-codex --no-onboarding` and `repowise status` completed. The initialization indexed the exact candidate and reported 2,534 files/10,371 symbols; the later status inventory reported 2,537 files/12,888 symbols. Repowise setup activity rewrote the following files, which remain deliberately unstaged and uncommitted:

- tracked: `.claude/CLAUDE.md`, `.mcp.json`, `.repowise-workspace.yaml`, `.repowise/mcp.json`
- ignored: `.vscode/extensions.json`, `.vscode/mcp.json`

The post-commit Repowise indexing hook added the `.repowise-workspace.yaml` metadata rewrite to the three tracked initialization rewrites. These setup changes were neither restored nor discarded and are separate from the sole review-record diff.

## Executive finding

### PB-M-02 - Major - changed Message retry reconstructs a missing receipt before conflict

The candidate closes PB-M-01 for the residue it tests: canonical event and standalone receipt retained, scoped idempotency index missing. It does not preserve the same no-mutation contract for the complementary durable state: canonical event and scoped index retained, standalone receipt missing.

That complementary state is reachable because `ReceiptStore.write_scoped` publishes the scoped index before it writes the standalone receipt (`research_system/store/receipts.py:358-359`). For a retry that changes only `command_id`, the authority scope still matches because command ID is excluded from the scope (`research_system/command/service.py:774-780`). The retained scoped index therefore takes this order:

1. `_load_lifecycle_authority_receipt` loads the scoped receipt and invokes `_reconcile_scoped_authority_receipt` (`service.py:1459-1483`).
2. Reconciliation verifies the canonical event and writes the missing original standalone receipt (`service.py:902-904`).
3. Only after that write does `_validate_message_scoped_retry_identity` compare command IDs and raise `ConflictError` with `idempotency key conflicts with committed command` (`service.py:1484-1500`).
4. The candidate guard in `_matching_committed` (`service.py:2501-2505`) is never reached because the retained scoped index took the earlier path.

The typed error is correct, and no new domain event or changed-command receipt is accepted. The pre-error reconstruction nevertheless changes durable authority-adjacent receipt state, violating the pilot's explicit conflict-with-no-mutation requirement. This is Major rather than Critical because ledger truth and the rejection result remain correct.

## Durable-state evidence through the public application API

The independent probe used the public decorated `CommandService.submit` seam from `control_plane(auto_authority=False)`, activated a real scoped Message grant, and normally accepted both publication and delivery before introducing the single-file fault. The two complementary missing-receipt cases used separately initialized control planes with the same starting-state construction. The probe compared ledger files, batches, tail and stream versions; standalone receipts; scoped indexes; replay/history; projection; and authority ledger/files.

| Durable direction and retry | Result |
|---|---|
| Event + receipt retained; scoped index deleted; identical retry | The candidate's existing recovery path returns the original accepted receipt and restores the exact scoped index without a new event. |
| Event + receipt retained; scoped index deleted; only `command_id` changed | The exact new candidate node raises the required typed conflict before reconstructing the index. Ledger, receipts, indexes, replay/history, projection, and authority remain unchanged. |
| Event + scoped index retained; standalone receipt deleted; identical retry | Correctly returns the original accepted receipt and restores its exact standalone receipt. Only `receipts/<original-command-id>.json` changes; all other compared axes remain identical. |
| Event + scoped index retained; standalone receipt deleted; only `command_id` changed | Raises the exact required typed conflict, but first restores `receipts/<original-command-id>.json`. Ledger, index, event, replay/history, projection, and authority remain unchanged; the receipt axis does not. This is PB-M-02. |

The existing orphan negative also remains correct: a standalone Message receipt with neither scoped index nor canonical event raises before append. Existing non-Message scoped retry behavior remains on the shared path because the new candidate guard is conditional on `_MESSAGE_COMMAND_TYPES`.

## Prior-review finding dispositions

The three existing review records were read fully and bound by exact Git object:

| Candidate and review record | Review commit | Record blob |
|---|---|---|
| `b3531092814efbd2ff3f1fb094dd929032642d1e` - `wp6-1-message-lifecycle-b353109-review-2026-08-02.md` | `638a12b1ffb9893fac0fd2f996995c788df95693` | `4b89a507ee6ac1699600b38458f7614b386243b6` |
| `b4000015c65c132da272f0ca6122060a17d8c0af` - `wp6-1-message-lifecycle-b400001-rereview-2026-08-02.md` | `9deda084366cc05f473bfe12cd4000fbf6953424` | `29763b912b391163690b8bc1f300e994fb9a6f80` |
| `62a87fd46642ac6c9c176058949bd2d43075a326` - `wp6-1-message-lifecycle-62a87fd-review-2026-08-02.md` | `29393875994a750886072825ca04be03cbe5427e` | `5a0e6e6256c38deeb338307d49e2655305fdcdf7` |

| Finding | Current disposition |
|---|---|
| C-01 orphan-receipt mutation | Closed by `62a87fd`: the orphan is rejected before Message preparation, event construction, or append. |
| C-02 authority variant/subject enforcement | Closed at the review chain's settled representative granularity; protected runtime bindings and the full module remain green. |
| M-01 lifecycle adapter source-position join | Closed; the complete Message module exercises the canonical join and retry behavior. |
| M-02 acknowledgement source-position/content join | Closed; the acknowledgement contract remains exercised in the complete module. |
| M-03 13-row pilot census/common axis | Closed at the prior review's settled granularity; the exact common-axis selection is 13 rows and all pass. |
| m-01 delivery/failure race | Closed; the complete module remains green. |
| PB-M-01 missing-index changed-command retry | Closed for the specified residue by the candidate guard and exact new regression node; parent-red proof is semantic. |
| PB-M-02 complementary missing-receipt changed-command retry | Open Major for this exact candidate. |

## Complete Message pilot census

The pinned design, catalogue, and executable `MESSAGE_ROWS` agree on exactly 13 unique rows. The collected common-axis selection contains all 13, and the complete module executes their positive, negative, replay, projection, receipt, and authority composition:

| # | Pilot row | Command -> event | Transition |
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
| 13 | `message.delivery_failure` | `RecordMessageDeliveryFailure` -> `MessageDeliveryFailed` | published -> failed |

## Independent red/green and regression evidence

All candidate Python commands used `C:\Users\steph\TDL\.venv\Scripts\python.exe` directly with `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, empty `PYTEST_ADDOPTS`/`PYTHONPATH`, `-o addopts=`, and `-p no:cacheprovider`. Coverage, cache, and automatic third-party plugins were disabled.

The prescribed selections were invoked directly as follows (the four shared node IDs are listed after the results table):

```powershell
& 'C:\Users\steph\TDL\.venv\Scripts\python.exe' -m pytest -q -o addopts= -p no:cacheprovider 'tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_retry_with_changed_command_id_does_not_reconstruct_missing_scoped_index'
& 'C:\Users\steph\TDL\.venv\Scripts\python.exe' -m pytest -q -o addopts= -p no:cacheprovider 'tests/research_system/integration/test_wp6_1_message_lifecycle.py'
& 'C:\Users\steph\TDL\.venv\Scripts\python.exe' -m pytest --collect-only -q -o addopts= -p no:cacheprovider 'tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_row_common_axis_matrix'
& 'C:\Users\steph\TDL\.venv\Scripts\python.exe' -m pytest -q -o addopts= -p no:cacheprovider `
  'tests/research_system/integration/test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart' `
  'tests/research_system/integration/test_authority_grant_source.py::test_rejected_exact_retry_is_returned_before_current_authority_recheck' `
  'tests/research_system/integration/test_authority_grant_source.py::test_scoped_retry_rejects_reused_unrelated_command_id' `
  'tests/research_system/integration/test_scoped_authority_grant_activation.py::test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant'
```

### Exact-parent red proof

A history-bearing `git clone --no-hardlinks` was configured with `core.autocrlf=false` and `core.longpaths=true`, checked out at exact parent `29393875994a750886072825ca04be03cbe5427e` / tree `7b26ca2e20e012fc8fa4761e6f39cdb55ebb2149`, and retained the parent production service blob `0f2def9a62a6f7de6d4d815f7ab2c193172ad70c`. Only the candidate Message test blob `8beb5139cd1a9cbeadd666a437f5d5761b7842e5` was materialized over that parent.

The exact new node failed for the intended application behavior:

```text
tests/research_system/integration/test_wp6_1_message_lifecycle.py::test_message_retry_with_changed_command_id_does_not_reconstruct_missing_scoped_index
Failed: DID NOT RAISE ConflictError
1 failed in 8.16s; 8.76s wall; exit 1
```

This was not a fixture, import, or schema-setup failure; import-path verification resolved production code to the clone. One deletion attempt for the explicit temporary clone was policy-denied, so it was not retried. The retained path is `C:\Users\steph\AppData\Local\Temp\tdl-message-parent-red-5c77239-20260803-001`.

### Exact-candidate commands

| Command selection | Result | Pytest / wall time |
|---|---|---|
| Exact new Message node above | 1 passed, exit 0 | 5.05s / 5.50s |
| Complete `tests/research_system/integration/test_wp6_1_message_lifecycle.py` | 100 passed, exit 0 | 34.88s / 35.40s |
| Exact common-axis node with `--collect-only -q` | exactly 13 collected, exit 0 | 0.42s / 0.87s |
| Four unchanged shared nodes listed below | 4 passed, exit 0 | 47.85s / 48.56s |

The four unchanged shared nodes were:

```text
tests/research_system/integration/test_authority_grant_source.py::test_revoke_is_locked_monotonic_and_exact_retry_survives_restart
tests/research_system/integration/test_authority_grant_source.py::test_rejected_exact_retry_is_returned_before_current_authority_recheck
tests/research_system/integration/test_authority_grant_source.py::test_scoped_retry_rejects_reused_unrelated_command_id
tests/research_system/integration/test_scoped_authority_grant_activation.py::test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant
```

Diff checks completed cleanly for parent-to-candidate (2 paths, 0.04s) and implementation-base-to-candidate over the 8 pilot paths (0.04s). `ruff check` passed all 8 paths in 0.10s; `ruff format --check` reported all 8 already formatted in 0.10s:

- `research_system/authority.py`
- `research_system/command/lifecycle.py`
- `research_system/command/reducers.py`
- `research_system/command/service.py`
- `research_system/projection/replay.py`
- `research_system/schema_registry.py`
- `tests/research_system/factories.py`
- `tests/research_system/integration/test_wp6_1_message_lifecycle.py`

## Protected identities

The protected candidate Git-object trees are unchanged and have the required counts:

- command schema tree `9ea0aec47e0032a2a4732f8cd230b2751bd6b7ea` - 87 files
- event schema tree `154ffc4bdde82fe903718734687e7a62797b1f69` - 86 files

All eight raw Message schema hashes were recomputed from candidate Git object bytes and match the pinned design/review values:

| Schema | SHA-256 |
|---|---|
| `PublishMessage` | `14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c` |
| `MessagePublished` | `f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f` |
| `RecordMessageDelivery` | `9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828` |
| `MessageDelivered` | `7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388` |
| `AcknowledgeMessage` | `3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d` |
| `MessageAcknowledged` | `576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be` |
| `RecordMessageDeliveryFailure` | `afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89` |
| `MessageDeliveryFailed` | `0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5` |

## Current-main composition

A read-only fetch completed in 1.31s. Pre-fetch `origin/main`, post-fetch `origin/main`, and live `git ls-remote` all resolved to `dd67dca5ff69c1aeefb903c63f3437df357280c0`; its service blob is `35f5c1b2488cc0c2d56f2fcbe7663d4f2958c407`. Candidate and current main diverge at exact merge base `7275184e41fbfb149d2c91462ac872012d29a961`. PR207 merge `9810fa98ba6f2333522b9afd659da5f335bbd79d` and its recorded follow-up head `b0d3e83c0e2e8b91ec563479dc46a22b3e1c108c` are both ancestors of current main.

A read-only `git merge-tree` composition found one service conflict hunk. Current main's KAN-67 path removes a committed activation marker when returning an existing receipt; the pilot path adds the orphan-receipt guard beside that existing-receipt return. A later integration must explicitly retain both main's committed-marker cleanup and the pilot's orphan/missing-index Message checks, then rerun main's marker tests and the complete Message module. The candidate's `_matching_committed` command-identity guard otherwise composes automatically, but the PB-M-02 repair-order defect remains. No integration, merge, or working-tree composition was performed.

## Remaining risk and boundary

- PB-M-02 is a demonstrated state mutation before the required conflict and is the blocking application defect.
- The pinned design's literal path allowlist omits the technically used `research_system/authority.py` and `research_system/command/lifecycle.py`; the prior record chain does not bind a separate owner-approved allowlist revision. This is a record/process gap, not a new candidate delta.
- The settled 13-row common-axis evidence samples some authority variants and the new recovery negative at representative command/row granularity rather than taking the full row-by-variant Cartesian product.
- Current main requires one explicit service conflict resolution before the KAN-67 marker logic and Message pilot can coexist; this review does not authorize or perform it.
- The policy-denied parent-red clone remains at the reported temporary path.

Passing schemas, the 100-node Message module, the four shared regressions, and PB-M-01's new node do not override the demonstrated complementary no-mutation failure. This review supplies neither owner acceptance nor authority to open a PR, merge, change Jira, invoke CodeRabbit, remediate production/tests, or dispatch a later lifecycle family.
