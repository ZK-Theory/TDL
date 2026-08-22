# 06r — Gate 6 PR #258 Review Convergence (retired historical evidence)

**Date:** 2026-08-22
**Status:** `RETIRED / SUPERSEDED FOR ACTIVE EXECUTION`
**Authority:** historical diagnostic record only. The sole active recovery and
closure authority is [06q](06q-gate6-spec-real-run-integration-and-follow-up.md).
This document authorizes no remediation, review trigger, merge, provider use,
live-store write, or owner decision.

## 1. Why this record is retained

PR #258 was closed unmerged at
`94f8bc1fc92bdc5259acab02e73a3958202ab2e`. Its branch remains historical
evidence. The candidate reached 145 changed files, 35,796 additions, and 114
review threads, with seven unresolved P1 families. Those facts explain why
specimen-by-specimen remediation was retired; they do not make the old branch
the current implementation or closure candidate.

The historical positive result remains valid: the real SPEC route produced a
durable result with 126 configurations and 42 deterministic reruns, ending at
`PROVEN/spec_02_owner_decided` and ledger tail `444 ResourcesReleased`. The
result is `PARK`, not empirical adoption or a scientific claim.

## 2. Diagnostic failure families

The seven unresolved PR #258 P1 families are retained exactly as historical
diagnostic evidence:

1. legacy corrections not bound to their causal prefix;
2. binding advance unanchored to `WriterLock`;
3. brief-input actions completing without sealed identity;
4. public commands bypassing the repaired-binding loader;
5. owner context including unsealed SPEC-02 approvals;
6. registered-content recovery enumerating an unanchored directory; and
7. grants outliving the actor session.

Separately, the historical SF1-SF6 action-model controls are:

1. total action state;
2. the exact completion tuple;
3. retry ordering and authority expiry;
4. one status/admission interpretation;
5. isolation of unrelated evidence; and
6. historical compatibility.

These lists must not be collapsed: the P1 families are the exact unresolved
review defects, while SF1-SF6 are the broader action-model controls that the
replacement plan must make observable.

The old convergence proposal correctly identified the need for one action
registry, one pure evaluator, and one atomic binding transaction. Its
individual review findings, matrices, and local test claims remain useful
diagnostic evidence, but they are not current acceptance evidence for the
replacement implementation.

## 3. Supersession rule

06q replaces the old integration-pending route with a controlled recovery and
closure plan. Its six sequential PRs re-express the same failure families at
the current public seams, retain verified result wording, and set the review
stop-loss boundary. No work should continue by appending another specimen to
this retired plan. Any future finding must be classified against the owning
06q invariant and current exact head.

## 4. Historical review boundary

The old candidate was not merged, and no historical review conclusion can be
carried to a later head. A fresh exact-subject review is required after the
replacement slices and fresh real run. Stephen remains the only person who
triggers CodeRabbit, authorizes merge, or decides Gate 6 closure.

For current status, architecture, acceptance, and closure evidence, read
[06q](06q-gate6-spec-real-run-integration-and-follow-up.md) and the
[real-run result handoff](../handoffs/01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-result.md).
