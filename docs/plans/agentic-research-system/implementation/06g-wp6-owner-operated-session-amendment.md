# WP6 owner-operated external-session amendment

**Date:** 2026-07-26  
**Status:** `owner_direction_accepted_review_pending`  
**Authority:** P-042; Stephen's explicit 2026-07-26 correction of the intended
Claude/Codex operating model  
**Amends:** the active execution authority of
`06-wp6-gate6-readiness-and-integration-plan.md` and
`06b-wp6-2-live-capability-plan.md`  
**Preservation rule:** those approved snapshots and their contracts remain
unchanged as historical evidence

## 1. Owner correction

Stephen uses Claude and Codex through subscription products authenticated by
their own OAuth flows. ARS is not intended to invoke either provider, route
requests directly to either model, or manage their authentication.

For the first ARS release:

- Stephen or another authorized operator starts each Claude or Codex session in
  the provider's normal application;
- OAuth tokens and session credentials remain outside ARS and must not be read,
  stored, resolved, copied, refreshed, logged, or passed by ARS;
- ARS must not spawn `claude`, `codex exec`, another provider process, or a
  direct provider API call;
- the operator selects the external application/session and supplies it with
  the ARS brief;
- ARS records the task role, assurance requirement, exact Git subject,
  artifacts, review identity, decisions, and evidence returned from that
  operator-initiated session;
- independent review is established through a separately initiated review task
  or fresh context with exact-subject evidence, not automated provider routing;
- subscription usage is not represented as a per-call provider cost grant or
  provider receipt.

The external session is therefore a user-operated work context, not an
ARS-controlled transport.

## 2. Superseded active requirements

| Prior authority | Active disposition under P-042 |
|---|---|
| P-033 full live capability before research dispatch | Superseded. Direct Claude/Codex transports, live semantic parity, live-grader activation, and evaluated provider profiles are not first-release prerequisites. |
| P-035 T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8 sequence | Superseded for active execution. T3/T4 provider issue and T1b live calibration are removed from the Gate 6 critical path. |
| P-029/P-030 automated provider eligibility and routing | Amended for first release. Risk and assurance still govern role assignment and review, but the operator chooses the external session; ARS does not choose or invoke a provider. |
| WP6.2 live adapter/parity/profile work | Deferred optional architecture, not Gate A or Gate 6 work. |
| D-G6-2 live threshold acceptance | Retired from the active first-release gate. |
| D-G6-3 WP6.2 live descriptor/evidence limb | Retired from the active first-release gate. |
| 251 frozen plus 51 live results and the 54-obligation P1 closure | Historical proposed live-activation evidence only; not an active release criterion. |
| Provider call reservation, metering, and reconciliation | Not applicable to user-operated subscription sessions. Existing accepted T2 artifacts remain historical exact-byte evidence. |

This amendment does not claim that human-operated evidence satisfies the old
T1b-M or T1b-H requirements. It removes that live-provider activation programme
from the first-release scope.

## 3. Revised WP6 dependency path

The active Gate 6 dependency path is:

```text
WP6.1 runtime task lifecycle --------\
                                      -> WP6.4 project binding and preflight -> Gate 6
WP6.3 TDA/panel assurance pack ------/

WP6.5 W11 specification lane remains independent.
WP6.6 dossier admission and WP6.7 legacy consolidation retain their existing gates.
```

WP6.4 must test an operator-mediated handoff and return path:

1. ARS produces a bounded brief and exact subject identity.
2. An authorized operator starts the external model session.
3. The session produces repository artifacts or a review record.
4. ARS records the resulting Git/Jira/task evidence and checks the required
   independence and acceptance authorities.

No step grants ARS provider invocation or credential access.

## 4. Gate and work-package dispositions

| Item | Disposition |
|---|---|
| Gate A A3 (live adapters) | Retired as a first-release blocker. The current fail-closed runtime is acceptable. |
| Gate A A6 (evaluated model profiles) | Retired as a first-release blocker. Operator selection does not create automated eligibility evidence. |
| WP6.2 T3 Claude transport | Cancel as superseded before implementation. |
| WP6.2 T4 Codex transport | Cancel as superseded before implementation. |
| WP6.2 T1a/T1b/T5-T8 live activation | Defer outside the first release; it must not block WP6.3 or WP6.4. |
| WP6.3 | Becomes the next active Gate 6 preparation package after this amendment is accepted. |
| WP6.4 | Must bind the owner-operated session workflow and verify exact-subject evidence without provider automation. |

## 5. Artifact and code preservation

The following are retained unchanged:

- the approved WP6 master and WP6.2 plan snapshots;
- the T2 authority/cost contracts and exact-byte acceptance records;
- the T3/T4 live-issue catalogue, schema, tests, fixtures, and proposed addendum;
- the 51-row replacement map and 54-obligation activation contract;
- existing provider adapter scaffolding and deterministic fake tests.

The runtime must keep live provider operation disabled. No removal or refactor is
required by this planning amendment because current provider execution is
already fail-closed. Any future proposal to reactivate direct provider control
requires a new owner decision, threat/credential review, and independently
reviewed implementation plan.

## 6. First-release evidence contract

For an operator-initiated model task, ARS evidence must identify:

- the task and requested role;
- the assurance/review requirement;
- the authorized operator identity;
- a stable handoff/session identifier shared by the brief and returned evidence;
- the exact repository subject (commit/tree/path identities as applicable);
- the operator-selected session family when relevant to an accepted
  independence rule;
- the resulting artifacts, test evidence, and review verdict;
- the reviewer identity and an explicit provenance link to the separate review
  task or fresh context used for any independent review;
- the accepting authority and any unresolved findings.

Provider-native invocation receipts, OAuth or credential material, token
metering, and per-call cost reconciliation are neither required nor permitted.

## 7. Hard stops

This amendment authorizes planning and dependency correction only. It does not
authorize:

- provider invocation, credential access, or subscription automation;
- runtime implementation or removal of historical contracts;
- Gate 6 acceptance, pilot initialization, eligibility transition, result, or
  claim;
- treating an author self-review as independent verification;
- merging this amendment without a fresh review of its consistency with the
  active WP6 indexes and Jira dependency state.
