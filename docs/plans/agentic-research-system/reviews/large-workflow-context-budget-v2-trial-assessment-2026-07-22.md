# Large-Workflow Context-Budget V2 Trial Assessment

**Date:** 2026-07-22
**Verdict:** `approve_advisory_integration`; activated by Stephen on 2026-07-22
**Workflow system:** Standalone TDL supervision; not APM
**Evidence:**
`../handoffs/trials/gate6-wp6-2-t2-context-budget-v2-exact-state-handback.md`
**Evidence SHA-256:**
`255b187b36ca242ac19ee36aadd498ea5fae97b5b49a85fb77dac0e6ae09a239`

## Outcome

V2 did not dispatch an implementer because it found a genuine authority gap before
write scope could be frozen. That is a successful supervision outcome, not a false
stop: implementation would otherwise have invented canonical mutations or a second
writer outside accepted authority.

The method has earned advisory integration. Mandatory checker enforcement and a
`CONVENTIONS.md` lock remain deferred because no implementation/review/remediation
cycle has yet completed under the method.

## Evidence against V2 criteria

| Criterion | V2 evidence | Assessment |
|---|---|---|
| Standalone routing | No APM skill, state, Memory Bank, guide, or checker used | Pass |
| Packet reuse | V1 packet SHA-256 matched; `origin/main` unchanged | Pass |
| Delta-only intake | Zero main-delta reads and zero repeated campaign reads | Pass |
| Context budget | Stopped below 80k with zero compactions | Pass; exact telemetry unavailable |
| Skill budget | One supervisor primary skill; handoff triggered conditionally | Pass |
| Certify before regenerate | Existing WP6.1/T1a artifacts reused; zero regeneration | Pass |
| Path-scope discipline | Refused dispatch while canonical ownership was unresolved | Pass |
| Validation proportionality | Two 102-contract passes and 19 focused baseline tests | Pass for preflight |
| External-review ownership | Zero CodeRabbit actions or waits | Pass |
| One vertical deliverable | T2 only; no T3/T4/live-call expansion | Pass |
| Implement/review/remediate cycle | No implementation subject existed | Not tested |
| Assurance preservation | No dropped requirement, stale decision, or weakening | Pass |

## Independent blocker verification

The handback correctly identified a missing exact transition contract:

- P-020 already assigns all canonical mutation to the project-wide `CommandService`;
  a separate cost writer is prohibited.
- `CommandService._build_event` implements only six command types and rejects every
  other type.
- The accepted owner-source catalogue defines `RequestResourceGrant`,
  `ClaimExecutionLease`, and `ReleaseResources`, but no cost-grant issuance,
  reservation/reconciliation, provider-issue, or provider-receipt transition.
- The operations coordinator already expects command-mediated grant, issue, and receipt
  seams, so a direct implementation would bypass its declared sole-writer route.
- W2 already gives the general schema rule: compatible additions are minor versions;
  breaking required-field changes use major successors, and historical records are
  never rewritten. What remains missing is the exact T2 identity/version disposition.

The versioning question therefore does not justify mutating accepted `1.0.0` files.
T2 needs a separately reviewed WP6.2 authority addendum that materializes exact new or
successor identities without changing accepted WP6.1 bytes.

## Method disposition

On Stephen's approval, advisory integration should update only:

- global/repository large-workflow instructions;
- a new standalone supervision skill;
- `tda-task-brief-from-plan` with workflow-system and canonical-transition closure;
- `tda-handoff` with neutral standalone handback paths;
- a neutral large-workflow supervision guide.

Existing APM machinery remains untouched. The strict dispatch checker and convention
lock stay deferred until a later completed implementation/review/remediation cycle
demonstrates that the advisory contract is stable.

## Residual risk

V1 and V2 establish efficient exact-state intake, delta reuse, correct skill routing,
bounded context, and fail-closed supervision. They do not yet quantify savings for a
completed code deliverable or validate the one-cycle remediation rule. Those become
post-integration evaluation evidence, not reasons to discard the successful stop.
