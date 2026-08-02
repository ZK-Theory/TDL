# WP6.1 PR #205 Recording-Lock Exact-Subject Review — 2223bbb

**Date:** 2026-08-02

**Review mode:** Fresh independent exact-subject review of the sibling recording-lock fixture correction. Review-only: no source, GitHub, Jira, CodeRabbit, production, schema, contract, or test remediation was performed.

**Verdict:** accept_exact_subject

## Exact subject and boundary

| Field | Exact value |
|---|---|
| Reviewer task | /root/pr205_2223_exact_review |
| Candidate | 2223bbb4c35bcbe11433aca755840ccf82ee8a31 |
| Candidate tree | d1180fde5b5e1f4a7396252134be37f704516a1d |
| Parent | b21774f7360204399acba1c6291785f23d859917 |
| Live remote main / integration base | 207d92d93dd614e5e5f70c781d4bd11110b17488 |
| Review environment | Full-history, non-linked disposable clone; core.autocrlf=false; core.longpaths=true; detached exact candidate |

The reviewer verified HEAD, tree, parent, base ancestry, clean status, checked-out target blob, and live remote main before validation. A direct read-only ls-remote returned 207d92d93dd614e5e5f70c781d4bd11110b17488 for refs/heads/main. The apparent 7487c9a origin/main inside the local-source clone was identified and excluded as a copied stale local main ref, not a GitHub remote fact.

## Scope and blob provenance

The parent-to-candidate diff is exactly one modified path:

    tests/research_system/integration/test_gate5_release_tranche.py

It contains 36 insertions and 6 deletions. Git diff --check passed.

| Object | Parent | Candidate |
|---|---|---|
| Changed test blob | f322c38adf4ae6b2f42e63e01b1136f0e2798d38 | 5c46efefd6a4688b43c29910b89f18c0b93579da |
| Checked-out test blob | — | 5c46efefd6a4688b43c29910b89f18c0b93579da |
| research_system tree | 20161aa755cc06e7c1eab4bb222ad112927c0921 | unchanged |
| .research-system/schemas tree | b36fec20f89e22f9cd5811fa289c2fe4c029ffba | unchanged |
| .research-system/contracts tree | 4138918ab422eec604e8f3251c8846c8227870b4 | unchanged |
| contracts tree | 49dfb3bf5e698d6f815e9a475ee54153ff49fd9c | unchanged |

A protected-path comparison over research_system, .research-system/schemas, .research-system/contracts, and contracts exited zero. No production, schema, or contract byte changed.

The five earlier CodeRabbit-remediation paths also remain byte-identical to the parent:

| Path | Parent and candidate blob |
|---|---|
| .github/workflows/ci.yml | e5cbb1174988797ce7dde0a3306bf04558ca05d5 |
| tests/research_system/factories.py | a463db4ed6860bfb508e5810ce0ce45fc2072b7f |
| research_system/authority.py | e59a7188b29c5fdb2a10eff689516e5699fb2f37 |
| research_system/command/service.py | aab08c32ca9381b5269628ef8c94888d82f58cf3 |
| tests/research_system/integration/test_wp6_1_scope_task_authority.py | 10133d9b799cce110a3c89d1eb4abde974a81e15 |

The prior 39-test authority module was therefore not rerun. Its production and test subjects did not change.

## Semantic review

The candidate corrects three local test-only wrappers around the production WriterLock.

CompositeWriterLock calls each supplied lock's enter method and then performs a final fence. That fence reads the lock path and identity, requires the expected writer.lock path, and compares the on-disk JSON ownership record with the exact identity. A wrapper cannot pass by fabricating an arbitrary truth value.

The reviewer confirmed:

1. The moved-restore RecordingLock constructs the original WriterLock, directly proxies its path and identity, acquires it before recording entry, and delegates exit. It records no successful entry if real acquisition fails.

2. The changed-artifact RecordingLock applies the same real-lock delegation. Its wrapper adds observation only; the genuine lock writes and validates the ownership record.

3. The supersession TrackingLock directly proxies the real lock path and identity, marks itself active only after successful real acquisition, and delegates release. The tracked domain operations execute while the real lease is live.

No wrapper modifies WriterLock, CompositeWriterLock, or final-fence behavior. The correction restores fixture conformance to the production contract and does not weaken it.

The parent wrappers omitted path and identity and did not perform real acquisition. The final fence consequently raised ConflictError before the intended restore-preflight or supersession assertion, and lifecycle conflict retry could mask that fixture defect.

The corrected tests reach their intended assertions:

- stale moved restore reaches restore-preflight ArsError after two genuine writer locks are entered and proves no ledger batch, receipt, or object JSON was created;
- deleted artifact reaches the restore-preflight failure under genuine locks with no durable output;
- supersession-cycle processing reaches the expected supersession_cycle rejection while the real lock is active and exits inactive;
- the unchanged positive control accepts a current verified moved restore and appends exactly one ledger batch.

## Independent validation

All commands ran from the clean detached exact clone with PYTHONPATH pinned to that clone, using C:\Users\steph\TDL\.venv\Scripts\python.exe, with pytest cache and coverage disabled.

| Validation | Result |
|---|---|
| Ruff check on changed test file | passed in 0.10s |
| Ruff format check on changed test file | passed in 0.09s |
| Four exact Gate 5 nodes in one pytest invocation | 4 passed in 11.95s; 12.53s measured wall |
| Git diff --check | passed |
| Final SHA/tree/parent/base/blob/protected-path/live-remote/clean capture | passed in 1.12s |

Exact pytest nodes:

- test_moved_restore_is_rechecked_under_writer_lock
- test_real_command_service_rejects_changed_artifact_under_writer_lock
- test_supersession_graph_and_rejected_receipt_io_stay_inside_writer_lock
- test_real_command_service_accepts_only_current_verified_moved_restore

There was no retry, hang, full-suite run, CodeRabbit action, or external-state mutation.

## Supersession and remaining risk

This record supersedes wp6-1-pr205-coderabbit-r10-95f061c-review-2026-08-02.md for executable acceptance of PR #205 at exact candidate 2223bbb4c35bcbe11433aca755840ccf82ee8a31. The earlier record remains unchanged as historical evidence for its 95f061c subject; this record does not erase or revise that decision.

Remaining risk is bounded to unrun broader regression suites and the already accepted production composite-lock design boundary. The correction is test-only, production/schema/contract bytes are unchanged, and the exact four-node regression surface passed. This acceptance grants no authority to mutate or merge the PR, Jira, CodeRabbit, or dispatch state.

The disposable clone was clean after final capture. Its removal was blocked by shell safety policy; no bypass was attempted. The clone is outside the repository and is not acceptance evidence.
