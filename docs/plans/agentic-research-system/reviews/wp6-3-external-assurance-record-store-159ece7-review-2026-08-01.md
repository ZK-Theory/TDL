# WP6.3 governed external assurance record store second-remediation review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, read-only static attack
- Reviewer: `/root/kan67_static_attack`
- Reviewed subject: `159ece7c13f452da9942265586bced8d298cca6f`
- Parent: `8fbede7ee82c92f0092782247aab3bdde6bbd4ea`
- Tree: `947c69da659566706b6be98cf271e3215398a6da`
- Producer remote: `origin/codex/kan67-external-assurance-record-store-r2`
- Delta: exactly 5 paths
- Verdict: `rework_required`
- Findings: 1 Critical, 2 Major, 1 Minor

## Executive disposition

The subject closes the previously reported partial command-identity and latent
grant-object expectations and adds bounded writer-lock recovery. The external
record writer's body, hash, context, relationship, self-attestation, and
in-lock authority checks also remain present.

One concurrent stale-lock recovery sequence can nevertheless delete a newly
acquired live lock and admit two writers. Recovery also omits the resolved
command-schema byte identity, cannot safely resume after a crash while writing
its stable temporary marker, and retains a committed marker forever on the
receipt-reconstruction return path.

The subject remains quarantined. It is not integration, PR, merge, owner,
Gate A, or Gate 6 acceptance evidence. A corrected new exact subject requires
fresh independent review.

## Exact identity and preserved boundary

The exact subject, parent, tree, producer remote, and five-path delta were
confirmed. The delta is limited to:

- `research_system/command/service.py`;
- `research_system/store/lock.py`;
- `tests/research_system/integration/test_external_assurance_record_publication.py`;
- `tests/research_system/integration/test_scoped_authority_grant_activation.py`; and
- `tests/research_system/unit/test_store.py`.

No schema, contract, registry, or accepted authority path changed. The static
review made no repository changes and did not treat producer-reported tests as
independent acceptance evidence.

## C-01 - stale-lock compare/unlink can delete a new live owner

`remove_stale_lock` inspects stale lock bytes and later unlinks the pathname
without an atomic compare-and-delete guard. Two recoverers can both observe
stale lock `L`; one removes it and acquires fresh `L2`; the paused recoverer
then unlinks `L2` and acquires `L3`. Both fresh owners can enter the protected
writer region.

This is reachable on Windows because the published lock has no continuously
held file handle after hard-link publication. The correction must use an
atomic or otherwise exclusive stale-recovery claim that cannot unlink a
different owner generation. Add a barrier interleaving control proving a fresh
winner cannot be removed and at most one writer enters.

## M-01 - recovery marker omits resolved command-schema bytes

The marker hashes the validated command envelope after caller-supplied schema
provenance has been removed. The registry resolves the schema hash from source
bytes separately. An interrupted command can therefore retry after the bytes
at the same schema ID/version change, pass marker comparison, and emit an event
with a different resolved schema hash.

Bind the exact resolved command-schema ID, version, and SHA-256 used by the
submission into the recovery identity. Add a negative that creates a marker
under bytes A, reloads accepted alternate bytes at the same ID/version, and
requires conflict with no mutation.

## M-02 - a partial stable marker temp permanently blocks exact retry

Marker creation writes a stable `command-id.json.tmp` and then replaces the
final marker. Startup scans only final `*.json` markers. A crash during the
temporary write leaves a partial temp which a later retry parses as conflict,
without a bounded quarantine, cleanup, or reconstruction route.

Use a uniquely named temporary object or a bounded, identity-safe recovery
rule for abandoned partial temps. Add a crash fixture with a truncated temp
and prove that restart reaches a safe deterministic resolution rather than a
permanent conflict.

## m-01 - committed-marker retry returns before marker cleanup

Startup verifies but retains a marker whose activation event is already
committed. Exact retry then returns through receipt/idempotency or committed
event reconstruction before the later activation cleanup branch. A crash after
append and before normal cleanup therefore leaves a permanent marker.

Add the valid marker, grant object, and committed activation event without a
receipt; restart and exact-retry; then require canonical receipt recovery and
marker removal without another activation.

## Preserved controls

Static inspection confirmed that the validated envelope now covers changed
decision, payload, actor, grant, idempotency, correlation, and causation
attempts; the prior latent-object expectation is corrected; the external
writer retains its semantic checks; scoped authority events retain the guarded
continuation; and replay still rejects unbound producers. These closures do
not override the four findings above.
