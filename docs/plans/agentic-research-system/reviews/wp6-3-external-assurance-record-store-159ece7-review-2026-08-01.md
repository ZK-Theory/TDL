# WP6.3 governed external assurance record store second-remediation review

- Review date: 2026-08-01
- Review mode: two fresh independent, exact-subject, read-only attacks
- Formal reviewer task: `019fbe64-6621-7502-a135-2ac870047570`
- Independent static attacker: `/root/kan67_static_attack`
- Reviewed subject: `159ece7c13f452da9942265586bced8d298cca6f`
- Parent: `8fbede7ee82c92f0092782247aab3bdde6bbd4ea`
- Tree: `947c69da659566706b6be98cf271e3215398a6da`
- Producer remote: `origin/codex/kan67-external-assurance-record-store-r2`
- Delta: exactly 5 paths
- Verdict: `rework_required`
- Findings: 1 Critical, 3 Major, 1 Minor

## Executive disposition

The subject closes the previously reported partial command-identity and latent
grant-object expectations and adds bounded writer-lock recovery. The external
record writer's body, hash, context, relationship, self-attestation, and
in-lock authority checks also remain present.

Recovery for an interrupted command can delete a different command's already
committed grant object while preserving that different command's activation
event. One concurrent stale-lock recovery sequence can also delete a newly
acquired live lock and admit two writers. Recovery further omits the resolved
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

No schema, contract, registry, or accepted authority path changed. All 16
protected WP6.3 contract and authority-schema paths were independently compared
byte for byte with the parent and matched. Neither review made repository
changes or inferred acceptance from producer evidence.

The formal reviewer ran 91 focused tests in 314.99 seconds with coverage,
cache, and bytecode writes disabled. All passed. `git diff --check`, focused
Ruff, remote equality, exact identity, and clean-residue checks also passed.
Those results support preserved behavior but do not exercise or override the
five findings below.

## C-01 - one interrupted command can delete another committed grant object

Recovery rollback is selected by the interrupted marker's target when that
marker's `command_id` has no activation event. It does not prove that the
current object at that target still belongs to the interrupted command.

The formal public-path probe interrupted C1 before append, then accepted
distinct C2 for the same grant. Restart recovery preserved C2's committed
activation event but deleted C2's grant object while processing C1's marker.
This creates internally corrupt authority state and can make later resolution
or replay disagree with the committed ledger.

Bind pending marker ownership to the exact target generation and perform
target-level recovery isolation. Rollback must compare the current object's
canonical identity and ownership to the interrupted command before deletion.
Add the C1-interrupted, C2-committed same-target sequence and require recovery
to preserve all of C2 or fail closed without mutation.

## M-01 - stale-lock compare/unlink can delete a new live owner

`remove_stale_lock` inspects stale lock bytes and later unlinks the pathname
without an atomic compare-and-delete guard. Two recoverers can both observe
stale lock `L`; one removes it and acquires fresh `L2`; the paused recoverer
then unlinks `L2` and acquires `L3`. Both fresh owners can enter the protected
writer region.

This is reachable on Windows because the published lock has no continuously
held file handle after hard-link publication. A deterministic formal probe
allowed the second reclaimer to delete the new owner's live lock; the owner's
exit then raised `ConflictError`. The correction must use an atomic or
otherwise exclusive stale-recovery claim that cannot unlink a different owner
generation. Add a barrier interleaving control proving a fresh winner cannot
be removed and at most one writer enters.

## M-02 - recovery marker omits resolved command-schema bytes

The marker hashes the validated command envelope after caller-supplied schema
provenance has been removed. The registry resolves the schema hash from source
bytes separately. An interrupted command can therefore retry after the bytes
at the same schema ID/version change, pass marker comparison, and emit an event
with a different resolved schema hash.

The formal probe also reached this through a same-command event carrying a
different schema SHA which recovery accepted as committed. Bind and compare
the full validated envelope plus the exact resolved command-schema ID, version,
and SHA-256 used by submission. Add a negative that creates a marker under
bytes A, reloads accepted alternate bytes at the same ID/version, and requires
conflict with no mutation.

## M-03 - a partial stable marker temp permanently blocks exact retry

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
not override the five findings above.
