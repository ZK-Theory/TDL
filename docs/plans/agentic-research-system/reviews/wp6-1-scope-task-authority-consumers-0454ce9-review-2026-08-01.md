# WP6.1 Scope and Task authority-consumer r2 integration review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject and current-main integration,
  semantic authority, read-only
- Reviewed branch: `codex/review-wp61-r0-0454ce9`
- Reviewed subject: `0454ce9614f8ebcfe48fc68c441833738ee0b3bd`
- Parents: `ca947d95f38ce741a38b97b4c2c8d3689847afc1` and
  `6c32f17a7951ee1a01ca48b9fcaf7782125ac09e`
- Tree: `2c3f0db36b4fdb51128855e772816eba0f816b0e`
- Verdict: `rework_required`
- Findings: 0 Critical, 1 Major, 1 Minor

## Executive disposition

The r2 integration closes the original fabricated-resolver and stale-current-
authority findings. All six active Scope and Task commands now require the
exact ledger-backed resolver, resolve current authority under the writer lock
on initial submission and accepted retry, reject duck and subclass resolver
substitutions, and fail read-only after governed revocation. The current-main
merge is limited to the expected seven test lines and preserves the frozen
schema catalogue and activation set.

One durable-evidence defect remains. The lifecycle event commits the grant ID
but not its canonical hash, and replay validation silently skips the comparison
when its application projection has no grant record. Removing the sole scoped
authority-index record therefore allowed an exact restart retry to be accepted
and the index to be recreated without an authoritative evidence join. The
subject is quarantined and is not PR- or merge-authorized or evidence that
KAN-65 or WP6.1 is complete.

Because this subject already used the original producer's review-remediation
cycle, the durable-evidence correction belongs to a fresh task and exact
subject. It must preserve all closed authority controls and every accepted
schema byte.

## Exact identity and validation evidence

The reviewer confirmed the exact subject, both parents, tree, required
ancestry, nine-path delta relative to current main, clean substantive status,
and clean `git diff --check`. The merge seam adds exactly seven test lines in
`tests/research_system/integration/test_authority_grant_source.py` and has no
semantic implementation overlap.

Protected identities remained exact:

- 87 command schema files and 86 event schema files, with zero set delta from
  current main;
- all three WP6.1 contract blobs match current main;
- 28 existing runtime bindings, including the six Scope/Task commands; and
- no new schema or readiness activation.

Validation evidence:

```text
Focused WP6.1 authority/retry/replay/Gate-5/S-014/S-015 tier: 166 passed
Current semantic PR201 authority tier: 16 passed
Resolver substitution probe: duck and subclass resolvers rejected
Fresh restart/revocation probe: resolver calls 1 -> 2 -> 3; revoked retry
rejected; domain-event count remained one
Ruff on the nine expected paths: passed
git diff --check and protected-identity checks: passed
```

The complete release-publication test file timed out after 304 seconds. A
narrowed five-test tier produced four passes and the one Minor assertion
discrepancy recorded below; no full-file pass is claimed.

## M-01 - lifecycle grant evidence is not durably joined to history

The lifecycle domain event carries `authority_grant_id` but no canonical grant
hash. The replay validator attempts to compare authority evidence only when a
grant record happens to exist in the application projection; it skips that
check when the projection returns no record.

An independent disposable-store probe kept the grant active, deleted the sole
scoped authority-index record, restarted the service, and submitted the exact
committed retry. The retry returned `accepted`, appended no domain event, and
recreated the missing index. The event history exposed only the grant ID and
did not prove which canonical grant bytes authorized the original result.

The correction must bind every lifecycle result and retry to the canonical
grant evidence that is authoritative in ledger history. Replay and restart
must deterministically join the event's grant identity to the governed grant
activation/revocation history and compare the canonical hash. Missing,
ambiguous, tampered, or mismatched evidence must fail closed without recreating
authority from an unvalidated sidecar. If the complete canonical evidence is
still ledger-visible, rebuilding a disposable index from that evidence is
permitted; rebuilding it from the lifecycle event's bare ID is not.

No accepted command/event schema byte may be changed to obtain this result.

## m-01 - one publication negative has an inconsistent expected error

The narrowed release-publication regression tier rejected the operation as
required, but
`test_valid_publication_request_fails_closed_without_authorizer` expected
`release_publication_authorizer_unavailable` and observed
`release_publication_evidence_mismatch`. The operation remained fail-closed.

The fresh task should verify this test against the current exact code and fix
only the still-valid assertion or fixture ordering. It must not weaken the
publication denial or expand the WP6.1 authority subject to unrelated release
behavior.

## Required bounded correction

The fresh exact subject must:

1. join lifecycle grant IDs to canonical replay-visible governed authority
   evidence and require exact hash equality on replay/retry/restart;
2. add decisive missing, tampered, ambiguous, revoked, and index-rebuild
   controls at the real service seam;
3. preserve the exact ledger-backed resolver type, writer-lock ordering,
   fresh-resolution call, revocation, six-command lifecycle, Gate-5, and
   current-main merge controls already proved green;
4. preserve all 173 accepted WP6.1 schema bytes and the 28-binding activation
   set; and
5. verify and minimally resolve the one fail-closed publication-test
   discrepancy only if it remains reachable at the corrective subject.

A fresh independent exact-subject review is required before PR or integration.
