# WP6.4 restored-store binding exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, authority and recovery, read-only
- Reviewed branch: `codex/wp64-store-restore-binding-r1`
- Reviewed subject: `a47d8be68ca073531aef851282d4651488e82fb4`
- Direct parent: `8169bd87a51a4bee0650d538b83ef7968369976b`
- Tree: `74d27a9c7c3ff6b69e1295457542543ff063e9ac`
- Subject scope: 7 changed paths
- Verdict: `rework_required`
- Findings: 2 Critical, 3 Major, 0 Minor

## Executive disposition

The subject implements a useful restored-store binding primitive and preserves
its stated seven-path boundary, but it does not yet prove the current scoped
KAN-66 authority grant, and the CLI can durably mutate the manifest before a
later fallible step fails. Those are acceptance and recovery blockers. The
subject remains quarantined and is not merge-authorized or evidence that
KAN-57, KAN-67, WP6.4, or Gate 6 is complete.

This is the producer's first independent review cycle. The same producer may
perform one bounded remediation against these exact findings, followed by a
fresh independent exact-subject review.

## Exact identity and validation evidence

The reviewer verified the seven-path delta, clean `git diff --check`, and no
provider, schema, or assurance-record contract changes. The focused changed-
behavior suite passed 22 tests, but the direct semantic probes below reached
invalid states that the suite did not cover.

## C-01 - current scoped restore authority is not enforced

The positive path accepts a legacy manifest v1.0 store without the current
bootstrap nonce and canonical schema-root identity. It constructs a ledger
resolver but uses only its replay callback, and an empty administration history
returns without resolving the exact current, scoped, non-revoked restore
grant. Caller-consistent receipt and registry inputs can therefore pass without
establishing KAN-66 authority.

The corrected path must use an authority v1.1 bootstrap store and resolve the
exact restore grant under the writer lock before publishing a binding.

## C-02 - late CLI failure can commit a rebind and make retry impossible

The CLI finalizes the manifest before resolving and validating the schema root,
reserving or publishing the configuration output, and loading the emitted
`ControlBinding`. A later failure therefore returns an error after the store is
already bound; normal retry is then rejected as `store_not_moved`.

A temporary-directory probe reproduced both facts: the manifest was bound
after the reported failure, and the retry became diagnostic-only. All fallible
preflight work must occur before the single durable publication boundary, or a
committed-result protocol must make the outcome and retry exact.

## M-01 - a conflicting source retry is silently accepted

Once the target root is bound, the public primitive returns idempotent success
before comparing the supplied source. Because the original source root is not
retained durably, a retry naming a different source is accepted. A direct probe
confirmed this. The binding identity must retain enough source provenance to
distinguish an exact retry from a conflict.

## M-02 - Windows directory durability is overstated

The implementation fsyncs the temporary file and performs a same-directory
replace, but treats Windows directory-open or fsync failures as success. It can
therefore report a stronger directory-durability guarantee than it proves, and
there is no post-replace interruption test. The corrected contract and tests
must make the Windows durability/recovery semantics accurate and observable;
they must not silently claim a directory fsync that was not performed.

## M-03 - no authorized end-to-end reopen through the CLI exists

The current integration evidence either calls the primitive directly on a
legacy store or stops after `ControlBinding.load`. It does not demonstrate an
authority v1.1 store moving through the public CLI, emitting a fresh binding,
and reopening a pre-existing external assurance record with
`ControlStoreAuthorityResolver.resolve`.

## Required bounded correction

The remediation must establish a current scoped non-revoked grant under the
writer lock; preflight every fallible CLI operation before publication; reject
post-bind conflicting-source retries; state and test truthful Windows recovery
semantics; and add one public CLI-to-binding-to-resolver integration path over
an existing external assurance record. Provider invocation, credential access,
new assurance schemas, and unrelated runtime work remain out of scope.

