# WP6.1 durable authority-evidence linearization exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 0 Critical, 2 Major, 1 Minor.

This record combines two fresh, independent, read-only attacks on the same
exact corrective subject. It is not owner acceptance, PR or merge evidence,
completion of the remaining WP6.1 catalogue, or Gate 6 closure.

## Exact review identity

- Formal reviewer: `/root/pr205_toctou_exact_review`
- Independent static attacker: `/root/pr205_toctou_static_attack`
- Subject: `942c834af92b928e403459df2951999d97724f74`
- Parent: `d6a680b317fd59d57cf2837b8d050775c3183877`
- Tree: `77c045cf0aed2692be9c153067c3ecbe85ed1792`
- Producer remote: `origin/codex/wp61-durable-authority-cr-r1`
- Exact corrective delta: 5 paths
  - `research_system/command/service.py`
  - `research_system/store/lock.py`
  - `tests/research_system/factories.py`
  - `tests/research_system/integration/test_gate5_release_tranche.py`
  - `tests/research_system/integration/test_wp6_1_scope_task_authority.py`
- PR #205 remained open and unchanged at
  `bf2649c6a6fbc02bbd66e1b16403f564e1a22029` during review.

The exact subject, parent, tree, five-path delta, ancestry, producer remote,
and clean tracked review state were confirmed. The schema tree, contracts,
plans, authority implementation, runtime bindings, and six active Scope/Task
command/event bindings were unchanged.

## Executive disposition

The subject correctly linearizes the named Scope/Task lifecycle,
release-publication, and authority-administration routes across separate
domain and authority roots. Independent interleaving probes established both
winner orders, fail-closed revocation, canonical root order, bounded conflict
unwind, and no ordinary deadlock.

It is still incomplete. Two authority-governed T2 routes use a separate
authority resolver but remain outside the composite-lock boundary. In
addition, one physical root can be represented by both a normal Windows path
and its extended `\\?\` spelling; the current string-key deduplication then
tries to acquire the same physical lock twice and denies every affected
submission. Exceptional partial-acquisition cleanup can also stop after the
first release failure and leak an earlier sibling lock.

The subject remains quarantined. PR #205 must not fast-forward to this SHA.
Any corrected later SHA is a new exact subject requiring fresh independent
review and current-head external review.

## M-01 - authority-governed T2 routes remain revocation-TOCTOU capable

`IssueCostGrant` and `AuthorizeProviderIssue` resolve current revocable
authority through `t2_authority_resolver` before domain append. They are not
included in `_AUTHORITY_COORDINATED_COMMAND_TYPES`, so `_submission_lock()`
holds only the domain root. A revocation on the resolver's separate authority
store can therefore commit after the current-authority read and before the T2
append.

The next correction must expose and verify the exact resolver root identity,
hold the same canonical composite authority/domain lock from current-authority
resolution through domain append, and add deterministic revoke-wins,
domain-wins, and opposing-order/no-deadlock controls for both governed T2
routes. A resolver whose root cannot be proven must fail closed.

## M-02 - Windows extended-path aliases double-lock one physical root

`CompositeWriterLock` currently deduplicates roots using a normalized resolved
path string. On Windows, `C:\...\authority` and
`\\?\C:\...\authority` can name the same physical directory while retaining
different strings. The first acquisition creates `writer.lock`; the second
spelling encounters that same lock and raises `ConflictError` before authority
resolution or append.

The correction must group existing roots by physical file identity, choose one
caller-independent canonical path per group, and sort only distinct physical
roots. Service-level controls must cover normal, case, relative, reparse, and
extended-path spellings as well as genuinely separate roots.

## m-01 - exceptional partial-acquisition cleanup can leak a sibling lock

If acquisition of a later root fails, cleanup releases acquired locks in
reverse order. A release verification error currently interrupts that cleanup,
so an earlier acquired sibling can remain locked. Cleanup must attempt every
release while preserving and re-raising the first cleanup error after all
bounded attempts. Add a deterministic corrupted-or-replaced-metadata cleanup
control.

## Preserved closures and validation

The formal reviewer recorded the following successful exact-subject evidence
using bytecode-, cache-, and coverage-disabled focused runs:

```text
Concurrency, composite-lock, Gate-5, and admission slice: 12 passed
Append recovery, direct mutation gates, and projection slice: 7 passed
Preserved authority closures: 15 passed
Total: 34 passed
Tracked review worktree and residue checks: clean
```

Independent probes also confirmed ordinary alias deduplication for case,
relative, and reparse spellings; separate-root serialization; lock release on
projection and callback exceptions; and fail-closed malformed stale metadata.
Those green controls do not cover the three findings above.
