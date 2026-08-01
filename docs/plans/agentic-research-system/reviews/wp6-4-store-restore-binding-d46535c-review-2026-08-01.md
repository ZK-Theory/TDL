# WP6.4 restored-store binding r1 exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, adversarial, read-only
- Reviewed branch: `codex/review-wp64-restore-d46535c`
- Reviewed subject: `d46535c081eada7e6efa67ecfa6d48f027aeff00`
- Direct parent: `a47d8be68ca073531aef851282d4651488e82fb4`
- Tree: `306cb4d9ee9a2756f25f03a314376d23bfe04530`
- Corrective delta: 8 paths
- Verdict: `rework_required`
- Findings: 2 Critical, 3 Major, 0 Minor

## Executive disposition

The remediation proves the normal authority-v1.1 CLI restore-bind path, fresh
binding load, external-record resolver reopen, current replayed grant checks,
source-bound ordinary retry, and fresh-process replace-interruption recovery.
Those are meaningful closures. The exact subject still permits an altered
source code/schema binding to reach a durable target bind, can commit a bind
before an output-collision failure that makes retry unrecoverable, trusts
mutable retry provenance, silently reports full success without Windows
directory durability, and treats a proposed-only `VerifyRestore` command schema
as active authority.

The subject is quarantined and is not PR- or merge-authorized. KAN-57, WP6.4,
and Gate 6 remain open. The next exact subject must preserve the working
authority/recovery path while closing the source snapshot, committed-result,
retry-provenance, durability, and accepted-authority-identity seams. It must not
activate the proposed `VerifyRestore` schema or modify accepted contract/schema
bytes.

## Exact identity and validation evidence

The reviewer verified the branch, subject, parent, tree, eight-path corrective
delta, required ancestry, remote, protected paths, and clean worktree. The
subject changes no protected `.research-system/schemas`,
`.research-system/contracts`, or governing implementation-document bytes.

Validation evidence:

```text
Focused replay tests: 4 passed in 0.64s
External assurance CLI decisive tests: 1 passed each in 16.33s, 15.19s,
17.92s
Gate 5 restore/service slice: 9 passed in 103.14s
Ruff: All checks passed
git diff --check: passed
```

The public positive path successfully completed restore-bind, reopened a fresh
`ControlBinding`, and resolved a pre-existing external assurance record through
`ControlStoreAuthorityResolver`. The post-replace interruption also recovered
across a fresh process. These positives are retained requirements, not evidence
that the remaining findings are closed.

## C-01 - source authority binding is incomplete and TOCTOU-reachable

The authority path calls `verify_store_identity` without binding the expected
code roots. The copied target supplies `code_roots` and `schema_root`, but the
source authority manifest is not rechecked against that exact binding within
the final source-target lock boundary.

A direct temporary-store probe changed only the source v1.1 manifest's code and
schema roots, recomputed its self-hash, then obtained `preflight=verified`,
`finalize=True`, and a bound target. The operation can therefore resolve
authority from a source whose executable/schema binding differs from the
reviewed restore.

The correction must capture an immutable source authority/bootstrap/schema
snapshot, bind its identity and hashes to the expected target code/schema
roots, and revalidate that snapshot immediately before manifest replacement
under the same source-target lock. Any source or target mutation must leave the
target unbound.

## C-02 - config-output collision can strand a committed bind

The CLI publishes the binding configuration after manifest finalization. A
reserved-output collision with a partial configuration produced a bad-file-
descriptor failure while the target manifest was already bound. A second
attempt then rejected the partial configuration, leaving no ordinary exact
retry path. Descriptor ownership is also double-closed after the publication
helper consumes it.

The correction must transfer descriptor ownership exactly once and make the
operation's committed state explicit. Either all remaining fallible output
work is preflighted before bind, or a typed durable result must distinguish
`bound-but-config-unpublished`, retain the exact expected output digest, and
let an exact retry verify or complete that output without repeating or denying
the committed bind. Failure must never imply zero mutation after commit.

## M-01 - retry provenance is mutable and self-attested

The durable evidence compares its recorded source to a caller-supplied source,
while the CLI derives the caller source from that same mutable evidence. After
a successful bind, changing only `restore-binding-evidence.json.source_root` to
a different copied source caused the new source retry to return `accepted`.

Persist an immutable source snapshot identity and canonical digest in the
authoritative binding/receipt state. Retry must independently receive and
verify the original source identity; it must not derive both sides of the
comparison from mutable evidence. Tampered, missing, foreign, or ambiguous
evidence must fail closed after restart.

## M-02 - unsupported Windows directory durability is ignored

The directory-fsync helper reports unsupported durability, but its callers
discard that result. With every directory-fsync call forced to return `False`,
the public CLI returned success with `status="bound"`.

The implementation must propagate this result truthfully. It may either fail
closed before claiming a durable bind or return an explicit typed
pending/non-durable state whose recovery obligations are preserved across
restart. It must not report full durable success when the platform guarantee
was not obtained.

## M-03 - proposed-only VerifyRestore is treated as accepted authority

The runtime binding registry has no active `VerifyRestore` command binding;
the schema remains `proposed_materialized`. The subject bypasses that inactive
state in Python and uses the proposed schema hash as accepted authority. This
creates a runtime-authority exception without the independent review/owner
acceptance required for schema activation.

Remove the exception. The restore operation must consume an already accepted,
narrow non-dispatch authority action/scope supported by the current
ledger-backed grant model, or separately materialize and govern a non-command
internal authority identity without pretending the proposed command schema is
active. This correction is a routine least-privilege design decision under the
completion campaign; it does not authorize activating or changing the proposed
schema.

## Prior-finding disposition

- Prior C1: not closed; replayed-grant checks work, but source executable/schema
  binding remains incomplete.
- Prior C2: not closed; ordinary publication retry works, but reserved-output
  collision can strand a committed bind.
- Prior M1: not closed; ordinary different-source conflict works, but mutable
  evidence can redefine the accepted source.
- Prior M2: not closed; replace-interruption recovery works, but unsupported
  directory durability is silently promoted to success.
- Prior M3: closed; the public CLI to fresh binding to external-record resolver
  path passed with unchanged event bytes.

## Required bounded correction

The next exact subject must:

1. bind and revalidate one immutable source authority/bootstrap/schema snapshot
   under the final source-target lock;
2. make post-commit output state and descriptor ownership explicit and exactly
   retryable;
3. anchor retry to immutable authoritative source identity rather than mutable
   evidence;
4. propagate unsupported directory durability as a truthful typed outcome;
5. remove the proposed-command authority exception and use a reviewed
   least-privilege non-dispatch authority scope; and
6. preserve the already passing v1.1 authority, replay, restart, resolver,
   source-conflict, protected-byte, and denial-before-bind controls.

A fresh independent exact-subject review is required before any integration or
PR. No provider, credential, real assurance-record, acceptance-runner, or Gate
6 action belongs in this correction.
