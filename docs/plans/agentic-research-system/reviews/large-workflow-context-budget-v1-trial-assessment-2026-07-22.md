# Large-Workflow Context-Budget V1 Trial Assessment

**Date:** 2026-07-22
**Verdict:** `revise_and_retrial`
**Workflow system:** Standalone TDL supervision; not APM
**Evidence:**
`../handoffs/trials/gate6-wp6-2-context-budget-v1-exact-state-handback.md`
**Evidence SHA-256:**
`209f1cd1f83fd2051d9da1738c4cea58b9262ccd6e5a79a7926dddf85b2e1e4f`

## Outcome

V1 successfully tested certification/intake and the rotation boundary. It did not test
delivery supervision. The task reached its first automatic compaction after exact-state
reconstruction and stopped as instructed before a T2 branch, worktree, implementer, or
reviewer existed. Permanent integration is therefore premature.

Stephen also corrected a design error: WP6 is independent of APM. Loading
`apm-2-initiate-manager` imported an unrelated lifecycle merely because the generic
coordinator role was called a Manager. V2 must reject that coupling explicitly.

## Evidence against the trial criteria

| Criterion | V1 evidence | Assessment |
|---|---|---|
| Fresh coordination context | Fresh task; no WP6.1 conversation inherited | Pass |
| Rotation | Stopped at first compaction, approximately the 80k envelope | Pass, exact token telemetry unavailable |
| Fresh delegation | Two read-only explorers used `fork_turns: none` | Pass for exploration; implementation/review untested |
| Skill budget | Two declared primary skills, but one was an inapplicable APM skill | Fail; routing identity was missing |
| Certify before regenerate | WP6.1 and T1a identities certified; no regeneration | Pass |
| Current-state correction | Replaced stale open-stack and T1a-pending snapshots with exact current evidence | Pass |
| External review ownership | No CodeRabbit trigger, poll, wait, schedule, or automation | Pass |
| One vertical deliverable | T2 selected but not dispatched | Not tested |
| Validation ladder | No new candidate existed; zero focused/package/full runs | Not tested |
| Author-review-remediation cycle | Zero implementers and reviewers | Not tested |
| Assurance preservation | No dropped requirement, false stop, or weakened gate reported | Pass for intake |
| Efficiency measurement | Approximate context only; no exact tokens or completed-deliverable comparison | Insufficient |

## What V1 established

The broad intake work need not be repeated. The packet proves, at its snapshot:

- the complete WP6.1 stack is integrated on `origin/main` at
  `efcecd8669fb225061c6eaf300e31bc07d352f6e`;
- accepted WP6.1 command, event, core, and Stage-2 identities remain exact;
- WP6.2 T1a has distinct independent review, owner acceptance, and merge provenance;
- the next eligible vertical deliverable is WP6.2 T2 only;
- T3/T4, live calls, T1b, T5-T8, eligibility, research execution, and claims remain
  excluded.

V2 should verify the packet hash, fetch current `origin/main`, inspect only the remote
delta since the packet, and reopen broader certification only if that delta touches a
bound authority or T2 prerequisite.

## Method revisions required before V2

1. Add `workflow_system: standalone` to every packet and dispatch envelope.
2. Prohibit numbered APM skills, `.apm` state, APM Memory Bank, APM guides, and APM
   checkers in standalone tasks.
3. Split broad certification/intake from delivery supervision. A delivery supervisor
   consumes the exact-state packet rather than replaying the full campaign history.
4. Use `tda-task-brief-from-plan` as the supervisor's only primary skill. Invoke
   `tda-handoff` conditionally at rotation with an explicit neutral repository path;
   do not use its `.apm/memory` default.
5. Route T2 implementation separately with at most two primary skills:
   `schema-contract-design` and `contract-first-tdd`. The security guardrail is
   conditional on the credential/cost boundary and must not become a third primary.
6. Keep the 80k/first-compaction boundary for V2. The problem in V1 was repeated
   intake scope, not evidence that the boundary itself was too low.

## V2 success condition

V2 must supervise one bounded T2 implementation through focused and candidate-head
validation plus one fresh independent review and at most one remediation cycle, or
stop at a genuine technical or owner gate. It must retain exact context/fork/skill/read/
validation/cycle measurements and preserve every T2 hard exclusion.

## Integration decision

Do not yet integrate the general method into repo skills or gates. If V2 succeeds,
return its handback for an `approve_advisory_integration` or further revision decision.
Advisory integration would target standalone AGENTS guidance, a standalone supervision
skill, `tda-task-brief-from-plan`, `tda-handoff`, and a neutral guide. Existing APM
machinery remains unchanged. A mandatory checker and `CONVENTIONS.md` lock still require
a second successful large-workflow use after advisory integration.
