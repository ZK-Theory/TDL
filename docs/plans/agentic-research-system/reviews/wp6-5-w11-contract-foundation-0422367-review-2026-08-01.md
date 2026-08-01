# WP6.5 W11 contract-foundation exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, contract and authority, read-only
- Reviewed branch: `codex/kan58-w11-contract-foundation`
- Reviewed subject: `04223674acdb82ee00d1410e960414d624c326b1`
- Direct parent: `c84eb2aaf0890d36d3735d08a14169f4c50935cd`
- Tree: `edd1254a8925bfead0ccbe25a74df21cecc75b4b`
- Subject scope: 64 added paths, no modifications or deletions
- Verdict: `rework_required`
- Findings: 0 Critical, 4 Major, 2 Minor

## Executive disposition

The subject is correctly bounded to an inert W11 contract foundation and its
accepted W11 source identity is exact. The schema family loads and its local
references resolve, but independent negative probes found four material
contract weakenings and an ineffective committed-subject inertness control.

The subject remains quarantined. It is not accepted, merge-authorized, runtime
activated, or evidence that KAN-58 or D-G6-4 limb 2 is complete.

## Exact identity and validation evidence

The reviewer verified the 64-path additive delta, clean `git diff --check`, and
the accepted W11 authority at:

- commit `892d1d1650cdcf71d2a886318e174a18e11d5de0`;
- blob `f90729d0c42a0de98d064fac0824d1969c871c82`;
- raw SHA-256 `65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70`;
- 185,214 LF-only bytes.

Direct validation established 62 valid Draft 2020-12 schemas, 62 unique schema
IDs, 623 resolved local references, and a schema-valid bootstrap YAML. The
focused contract suite passed all 10 tests from the normal worktree and from an
unrelated working directory.

## M-01 - owner-row identity excludes accepted rows and admits foreign rows

The catalogue owner-row pattern accepts `OR-000` and `OR-100`, while rejecting
valid `OR-040` and `OR-041`. It must encode exactly `OR-001` through `OR-041`
and `OR-101` through `OR-140`, with decisive lower, upper, gap, and foreign-row
controls.

## M-02 - revision lineage and source-reference discriminants are weakened

The content schemas type `supersedes_revision` without enforcing revision 1 as
`null` and every later revision as the exact predecessor. Their source
references also permit record identities to use an external locator and
external identities to use record ID/revision fields. Direct invalid mutations
validated. The correction must provide deterministic exact-predecessor
semantic validation and ref-kind-specific identities across the content
family, with reachable negative tests.

## M-03 - Assay axis values and accepted domains are not typed

The scorecard axis `value` accepts arbitrary JSON, while the rubric permits no
declared value type or usable domain. Null, object, array, absent-domain, and
wrong-domain examples therefore pass or a valid numeric bounds object fails.
The correction must bind each axis kind to an explicit closed value domain and
test valid Boolean, integer, and registered-measure cases plus their decisive
mutations.

## M-04 - the inertness test does not inspect the committed subject

The current control checks only staged and unstaged worktree differences. A
clean commit containing runtime Python changes would pass. It must be replaced
by an immutable exact-subject or range control, or moved to an independently
recorded exact-subject gate that cannot self-certify committed runtime changes
and will not fail merely because unrelated future `main` commits exist.

## Minor findings

W11 requires UTC RFC 3339 timestamps, but `format: date-time` alone admits a
non-UTC offset such as `+01:00`. The representative tests also do not exercise
the owner-row, revision, reference, axis, or UTC contracts above.

## Required rework and authority boundary

The bounded remediation branch is
`codex/kan58-w11-contract-foundation-r1`, starting at the rejected subject.
After the findings are corrected and directly validated, the new exact subject
requires a fresh independent review.

Jira KAN-58 comment `10371` records the same disposition. This review grants no
runtime binding, catalogue or acceptance instance, OR-140 execution, migration,
transition, cutover, provider action, owner acceptance, or merge authority.
