# WP6.1 PR #205 CodeRabbit R12 exact-subject review

**Verdict:** accept_exact_subject
**Date:** 2026-08-02
**Review mode:** Fresh independent, read-only exact-subject review
**Reviewer task:** /root/pr205_10ece4c_review
**Candidate commit:** 10ece4c72ab5dcb5b7e1369ff98a160147f757fb
**Candidate tree:** b7e88957de0100384fd03f31eb047f8e36b1f943
**Exact parent:** 650cb0d8150dbbec3b639220f7afd3bc8e763c55
**Live GitHub main:** 207d92d93dd614e5e5f70c781d4bd11110b17488

## Record relationship

This review extends and supersedes 650cb0d8150dbbec3b639220f7afd3bc8e763c55 for current executable acceptance of the late CodeRabbit nitpick correction. It does not erase or replace earlier review, remediation, or owner-decision records.

## Provenance and scope

A unique full-history, non-linked disposable clone was configured with core.autocrlf=false and core.longpaths=true before checkout, then detached at the exact candidate. Imports were pinned to and verified from that clone.

Verified:

- HEAD equals 10ece4c72ab5dcb5b7e1369ff98a160147f757fb.
- The tree equals b7e88957de0100384fd03f31eb047f8e36b1f943.
- The exact parent equals 650cb0d8150dbbec3b639220f7afd3bc8e763c55.
- The parent and live GitHub main are ancestors of the candidate.
- Read-only ls-remote returned 207d92d93dd614e5e5f70c781d4bd11110b17488 for refs/heads/main.
- The clone was clean before and after validation.
- research_system, research_system.authority, and research_system.command.service imported from the disposable clone, not another worktree.

The parent-to-candidate diff contains exactly three paths:

| Path | Parent blob | Candidate blob |
|---|---|---|
| research_system/authority.py | e59a7188b29c5fdb2a10eff689516e5699fb2f37 | 594946b40640f1c524a2a5ba58a4d3eeea3c8576 |
| research_system/command/service.py | aab08c32ca9381b5269628ef8c94888d82f58cf3 | a76e3014b0fddeb9ca70990707ef28849d98ba18 |
| tests/research_system/integration/test_wp6_1_scope_task_authority.py | 10133d9b799cce110a3c89d1eb4abde974a81e15 | e015adc4ac17fdf9f181f6ef1212defc78e1903c |

No contract or schema path differs. Git diff --check passed.

## CodeRabbit nitpick dispositions

### 1. Private helper keyword-only parameters

**Disposition: accepted.**

LedgerAuthorityGrantResolver._resolve_scoped and _resolve_command_from_projection now place the keyword-only marker immediately after self. Runtime signature inspection confirmed every non-self parameter is KEYWORD_ONLY, including projection.

All production callers use named grant, actor, command, risk, project, subject, time, and projection arguments. The sole direct test caller expands an explicitly keyed mapping and names projection. Public resolve_command, resolve_lifecycle_command, and resolve_policy_action signatures remain unchanged.

### 2. Same-replay lifecycle evidence and canonical identity

**Disposition: accepted.**

resolve_lifecycle_command takes exactly one verified authority replay, derives the administration context and bootstrap owner from it, validates the command schema identity, and passes the same replay projection through the scoped and command checks.

Current status, effectiveness, expiry, actor, actor class, subject scope, risk ceiling, active command identity, grant command membership, and owner-derived human classification remain enforced.

canonical_grant_identity is now the same frozen command_resolution object. The dataclass and lifecycle-resolver documentation explicitly state that this is same-replay bundle evidence, not an independent authority read. The integration test proves both one replay and object identity.

The service comparison remains a bundle-consistency and tamper check. A forged resolver bundle that changes only command_resolution still fails before append with the distinct bundle-resolution diagnostic and produces no domain event, receipt, or scoped index.

### 3. Missing history versus forged-hash diagnostics

**Disposition: accepted.**

_validate_lifecycle_authority_history now distinguishes:

- absent or nonmatching canonical history: lifecycle authority evidence has no canonical grant history;
- present canonical history whose hash disagrees with the resolution: lifecycle authority resolution grant hash disagrees with canonical history.

Both cases remain fail-closed. The direct test exercises both messages, while the earlier forged-bundle service test preserves decisive no-append evidence.

The renamed test and updated documentation no longer claim source independence. The remaining opaque fixture title containing Independent hash is data, not an assertion or authority-source claim.

## Independent validation

All commands ran from the exact disposable clone with PYTHONPATH pinned to it, bytecode writes disabled, pytest cache disabled, and coverage options disabled.

| Validation | Result |
|---|---|
| Ruff check on all three changed paths | passed in 0.091s |
| Ruff format check on all three changed paths | passed in 0.103s |
| Git diff --check from exact parent | passed in 0.042s |
| Runtime keyword-only signature proof | passed in 0.228s |
| Full scope-task authority integration file | 39 passed in 14.66s; 15.069s wall |
| Two exact shared policy-action nodes | 2 passed in 18.25s; 18.964s wall |

The policy nodes were:

- test_owner_decision_activates_resolves_retries_and_revokes_scoped_grant;
- test_policy_resolution_uses_one_projection_snapshot_and_checks_owner_first.

## Remaining risk

This is exact-subject executable acceptance only. It is not merge, dispatch, schema/contract activation, or owner-acceptance authority.

The disposable clone remained clean, but its single policy-checked cleanup command was rejected before execution. No bypass or retry was attempted; no source-repository state was changed.
