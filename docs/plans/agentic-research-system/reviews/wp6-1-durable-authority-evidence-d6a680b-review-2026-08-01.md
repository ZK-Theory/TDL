# WP6.1 durable authority-evidence remediation exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `rework_required`

Findings: 0 Critical, 1 Major, 0 Minor.

This record preserves the fresh independent review of one exact corrective
subject. It is not owner acceptance, PR or merge evidence, completion of the
remaining WP6.1 catalogue, or Gate 6 closure.

## Independent review identity

- Reviewer task: `019fbe1e-0e4f-7b21-b734-6dd9b07b6190`
- Subject: `d6a680b317fd59d57cf2837b8d050775c3183877`
- Parent: `bf2649c6a6fbc02bbd66e1b16403f564e1a22029`
- Tree: `b1a69aac1d24aff5b6c0af3758d781c5a36e7101`
- Exact corrective delta: 8 paths
  - `research_system/authority.py`
  - `research_system/command/service.py`
  - `research_system/evals/executors/release_tranche.py`
  - `tests/research_system/factories.py`
  - `tests/research_system/integration/test_gate5_release_tranche.py`
  - `tests/research_system/integration/test_wp6_1_scope_task_authority.py`
  - `tests/research_system/integration/test_wp6_1_task_scope_lifecycle.py`
  - `tests/research_system/unit/test_release_publication.py`
- Exact subject identity and ancestry were confirmed.
- The tracked review worktree remained clean; review execution made no
  repository changes.

## Executive disposition

The subject closes the previously identified independent-hash, missing-binding,
revocation-identity, clock, JSONL-preservation, no-authorizer atomicity,
resolver-substitution, and exact receipt/project/replay gaps. The six active
WP6.1 lifecycle commands and runtime bindings also remain unchanged.

One authority-ordering defect remains. Domain acceptance holds the command
service's control-root lock, while current authority is read from a separate
release-tranche root. A revocation can therefore commit after the authority
projection is captured but before the domain event append, and the captured
projection is reused through acceptance. The exact subject remains
quarantined and is not PR-, merge-, or owner-acceptance-authorized.

## Closed findings and preserved controls

Fresh review confirmed that prior findings 1 and 3-9 are closed or preserved:

- authority evidence uses an independently derived hash;
- a missing authority binding fails closed;
- revocation identities are exact and resolvable;
- authority clocks are controlled consistently;
- unrelated JSONL content is preserved;
- no-authorizer rejection is atomic;
- duck or substitution resolvers are rejected;
- receipt, project, and replay identities join exactly; and
- the six active lifecycle commands and bindings are unchanged.

## Validation evidence

```text
Scope-authority integration: 18 passed
Focused authority tests: 9 passed
Missing-binding negative: 1 passed
Release-publication tests: 4 passed
git diff --check: passed
Exact identity and tracked worktree status: clean
```

The initial `uv` launcher attempt failed on a `fonttools` permission error and
is not evidence. The successful runs through the shared interpreter are the
recorded evidence. These green checks do not exercise or override the
cross-store interleaving probe below.

## M-01 - revocation can interleave after authority resolution

`CommandService` holds `self.control_root` around the acceptance sequence at
`research_system/command/service.py:557-575`. Authority state is read from a
separate root through
`research_system/evals/executors/release_tranche.py:146-176` and
`research_system/evals/executors/release_tranche.py:282-290`. The projection
captured at `research_system/command/service.py:1083-1130` is then reused
through append without a shared lock or version fence over the authority
store.

An independent probe inserted a real authority revocation after projection
capture and before the domain append. The domain command was nevertheless
accepted, producing one domain event while the authority ledger contained four
events. The accepted domain event therefore relied on authority that was no
longer current at its commit boundary.

### Minimum correction

Use one shared authority/domain lock across current-authority resolution and
domain append, or bind acceptance to a versioned authority fence that is
revalidated immediately before commit. A revocation must be unable to
interleave, or the domain command must fail closed with unchanged domain
ledger, receipt, index, snapshot, and replay state.

Add a deterministic interleaving control that pauses after authority
resolution, commits a real revocation, then resumes the domain command and
proves either serialization before revocation or fail-closed rejection after
it. Preserve the now-closed findings and the six active command/binding
boundary. A fresh independent exact-subject review is required; no PR update
or acceptance is authorized by this record.
