# WP6.1 Scope and Task authority-consumer exact-subject review

- Review date: 2026-08-01
- Review mode: fresh independent, exact-subject, semantic authority, read-only
- Reviewed branch: `codex/wp61-scope-task-authority-consumers-r1`
- Reviewed subject: `b07e6814ddfa010e844430452e07ab6d32fdfa73`
- Direct parent: `570468d5747043fc0f5268ff7ac961e305ebc80b`
- Tree: `880ec2b3f2e48dfee32bf1276dac225172fab4de`
- Verdict: `rework_required`
- Findings: 0 Critical, 2 Major, 0 Minor

## Executive disposition

The subject binds the six already active Scope and Task commands, preserves
writer-lock ordering, rejects authority denial before domain mutation, builds
the intended schema triples, and covers basic replay. Those mechanics do not
close the authority contract because the production-facing lifecycle helper
can accept fabricated duck-typed authority and accepted retries need not rerun
current-authority resolution.

The candidate remains quarantined. It is not accepted, merge-authorized, or
evidence that KAN-65 or WP6.1 is complete.

## M-01 — fabricated lifecycle authority remains admissible

`CommandService` accepts an untyped resolver surface and invokes a duck-typed
`resolve_command`. The subject adds `_FixtureLifecycleAuthorityResolver` under
the production package's Gate-5 evaluation helper. That resolver invents an
administration context and active grant result, ignores the exact command,
risk, and evaluation time, and can produce accepted Scope or Task lifecycle
results without a real ledger-backed grant.

Routing through `CommandService` does not cure this defect. The canonical
authority boundary must require the ledger-backed resolver and the helper must
create real governed grant evidence or remain unable to produce an accepted
lifecycle result.

## M-02 — accepted retry omits fresh current-authority resolution

A committed retry loads a lifecycle authority sidecar and calls only
`scoped_grant_identity`. That surface verifies immutable grant identity but
does not re-evaluate effective, expiry, or revocation state; those checks occur
in `resolve_command`. The event retains only `authority_grant_id`, while replay
does not retain or validate the full resolution evidence.

An independent direct probe accepted the first submission, then changed the
resolver to deny fresh resolution. The retry still returned `accepted` and
the resolver call count remained one. An expired or newly revoked grant can
therefore return a prior accepted receipt after restart without a fresh
authorization decision.

## Validation evidence

The reviewer verified the exact subject, parent, tree, branch/remote equality,
eight-path delta, clean `git diff --check`, and absence of new schema,
readiness, or provider activation. Targeted validation passed:

- 6 WP6.1 Scope/Task authority integration tests;
- 91 command-service, replay, and Gate-5 tranche tests; and
- 66 authority-source tests in 9 minutes 46 seconds.

Total: 163 passed.

## Required rework and boundary

The next subject must remove fabricated authority from the production-facing
helper, require canonical ledger-backed command resolution, re-evaluate
current authority on accepted retries, and preserve replay-visible durable
resolution evidence. It must receive a fresh independent exact-subject review
after PR #201's final integration seam is stable.

Jira KAN-65 comment `10362` records the same disposition. This record grants no
authority, activates no schema, and does not authorize a provider, pilot,
research execution, or merge.
