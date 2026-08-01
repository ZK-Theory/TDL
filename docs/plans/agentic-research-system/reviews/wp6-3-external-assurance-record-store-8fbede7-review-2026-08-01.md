# WP6.3 governed external assurance record store remediation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, read-only
- Review task: `019fbe13-2584-7490-ab46-5aac1730c049`
- Reviewed subject: `8fbede7ee82c92f0092782247aab3bdde6bbd4ea`
- Parent: `b7575d518a4b93e46f61a371651f220e0602048c`
- Tree: `01c6d3c7bd67f1876d660a219d103502cd6d5094`
- Delta: exactly 3 paths
- Verdict: `rework_required`
- Findings: 0 Critical, 2 Major, 1 Minor

## Executive disposition

The three-path remediation adds recovery machinery around the failed
grant-activation boundary, and its focused candidate, store, resolver, CLI,
serialization, and replay checks pass. The fresh independent probes still
reach two authority failures: the recovery marker does not bind the complete
command, payload, and prepared-envelope identity, and stale lock ownership can
become unrecoverable or be attributed to an unrelated live process. One
sibling test also retains the rejected latent-object expectation.

The subject remains quarantined. It is not integrated or accepted, is not PR-
or merge-authorized, and is not evidence that KAN-67, Gate A, or Gate 6 is
complete. A corrected new exact subject requires fresh independent review.

## Exact identity and recorded evidence

The exact subject has the required parent and tree and changes only:

- `research_system/command/service.py`;
- `research_system/store/objects.py`; and
- `tests/research_system/integration/test_external_assurance_record_publication.py`.

The previously accepted WP6.3 authority and assurance blobs are unchanged.
No accepted semantic blob is superseded by this review, and this record grants
no integration, activation, or owner-acceptance authority.

Focused evidence recorded for the exact subject:

```text
Candidate integration: 6 passed
Object-store tests: 25 passed
Resolver contract tests: 59 passed
CLI tests: 2 passed
Serialization test: 1 passed
Replay test: 1 passed
Sibling scoped-authority test selection: 1 failed, 4 passed
Broad test attempts: timed out; not evidence
```

The green focused checks do not exercise or override the independent identity
and lock-lifecycle probes below.

## M-01 - recovery marker does not bind the full retry identity

The recovery marker does not bind the complete command identity, canonical
payload identity, and prepared event-envelope identity. After an injected
pre-append failure, an independent probe retained the same `command_id`,
idempotency identity, and grant identity but changed the otherwise valid
owner-administration decision. The retry was accepted with `event_count == 3`
and revision 1 instead of being rejected as a different command meaning.

Recovery must bind and compare the complete command, payload, and prepared
envelope before any retry can reuse a marker or mutate durable state. Any
semantic difference under a reused command or idempotency identity must fail
closed. Add a decisive injected-failure test that changes a valid authority
decision while retaining the shared identifiers and proves that every store,
ledger, receipt, index, snapshot, and replay surface remains unchanged.

## M-02 - stale lock recovery can deadlock permanently

Malformed or identity-mismatched lock metadata causes recovery to return while
leaving the lock in place. The liveness check also treats a live PID as proof
of lock ownership, although PIDs can be reused or belong to an unrelated
process, and the metadata describing ownership is not published atomically.
A partial record or a live unrelated PID can therefore prevent recovery
indefinitely.

Lock creation and ownership publication must be atomic and bind a unique
process-instance identity, not PID liveness alone. Recovery must perform
bounded stale-owner revalidation and safely reclaim malformed, partial,
mismatched, or abandoned ownership without stealing a demonstrably live lock.
Add deterministic controls for partial metadata, PID reuse or mismatch, owner
death, and bounded recovery.

## m-01 - sibling test preserves the rejected latent-object contract

The sibling case in
`tests/research_system/integration/test_scoped_authority_grant_activation.py`
near line 899 still expects a latent grant object after append failure. That
expectation conflicts with the required unchanged-state failure invariant and
accounts for the focused sibling result of one failure and four passes.

Update the sibling test to require no latent object or other durable mutation
after failure, while retaining successful activation and retry coverage.

## Required bounded correction

The next exact subject must bind recovery to the full command, payload, and
event-envelope identity; replace PID-only, non-atomic lock attribution with
atomic process-instance ownership and bounded stale-owner recovery; and update
the stale sibling negative case. It must preserve all accepted blobs and prove
failure leaves every authority surface unchanged. No integration or acceptance
is authorized until a fresh independent exact-subject review succeeds.
