# WP6 direct-provider-routing blast-radius review

**Date:** 2026-07-26  
**Subject:** active WP6 requirements for ARS-controlled Claude/Codex invocation  
**Verdict:** `rework_required`  
**Trigger:** owner clarification that Claude and Codex are subscription/OAuth
applications used in operator-initiated sessions, not APIs or CLIs for ARS to
invoke  
**Proposed correction:** P-042 and
`implementation/06g-wp6-owner-operated-session-amendment.md`

## Executive finding

The active WP6 plan encoded a materially different operating model from the
owner's intended workflow. Its T3/T4 transports, T1b live calibration, provider
profiles, and cost-grant/receipt chain would make ARS responsible for model
invocation. That responsibility is neither wanted nor appropriate for the
owner's subscription/OAuth setup.

The blast radius is high in planning and dependency governance but low in
runtime code. The current adapter path defaults to disabled and rejects a real
transport even when its live flag is set. The minimal correction is therefore
to supersede the live-provider programme's active authority, preserve its
historical artifacts, and redirect Gate 6 to an operator-mediated handoff.

## Findings

### F-1 - Critical - Active plan contradicts owner authority

P-033 requires live Claude/Codex transports before research dispatch, and P-035
places T3/T4 and T1b on the mandatory WP6.2 sequence. If executed, ARS would
launch or directly control provider work despite the owner's explicit statement
that it must not do so.

**Disposition:** supersede P-033 and the active P-035 sequence through P-042.

### F-2 - Major - Authentication and accounting model does not fit subscription use

The T2/T3/T4 design assumes machine-resolved secrets, provider commands,
receipts, reservations, and cost reconciliation. OAuth credentials for the
owner's subscription applications must remain outside ARS, and subscription
sessions do not provide the intended per-call cost-grant boundary.

**Disposition:** retain accepted T2 bytes as historical evidence, but mark their
provider-call application not applicable to first-release operator sessions.

### F-3 - Major - Unwanted provider work blocks unrelated Gate 6 value

Gate A A3/A6 and D-G6-2/D-G6-3 make adapters, live parity, evaluated profiles,
and live calibration prerequisites for WP6.4 and Gate 6. This blocks the
assurance pack and operator workflow on capabilities the owner does not want.

**Disposition:** retire those live limbs from the first-release gate and use the
revised WP6.1 + WP6.3 -> WP6.4 dependency path.

### F-4 - Minor - Runtime scaffolding is dormant, not an immediate execution risk

`research_system/adapters/claude.py:8` and
`research_system/adapters/codex.py:8` construct provider CLI commands, but
`research_system/adapters/provider.py:48` defaults live provider operation to
disabled. Lines 64-65 reject live operations while disabled, and lines 187-191
reject non-fake live transport capability. Existing relevant tests use
`FakeTransport`.

**Disposition:** make no runtime-code change in this amendment. Preserve the
fail-closed behavior and deterministic tests.

## Blast-radius matrix

| Surface | Impact | Required action |
|---|---:|---|
| Decision register | High | Add P-042; preserve prior decisions as historical provenance. |
| WP6 master and WP6.2 approved snapshots | High semantic impact | Do not rewrite; apply the dated 06g amendment. |
| Gate A / D-G6-2 / D-G6-3 | High | Retire only their live-provider limbs for first release. |
| WP6 dependency graph | High | Remove WP6.2 live activation from the WP6.3/WP6.4 critical path. |
| WP6.2 T1a-T8 dispatch sequence | High | Defer; cancel T3/T4 dispatches before implementation. |
| Design and implementation indexes | Medium | Label direct-provider materials historical/deferred under P-042. |
| Jira KAN-55/KAN-62/KAN-63 | Medium | Record supersession; cancel T3/T4; remove obsolete block after amendment acceptance. |
| Jira KAN-56 | Medium | Make WP6.3 the next active preparation item after acceptance. |
| Adapter runtime | Low | No code change; live execution remains disabled. |
| Schemas/contracts/tests | Low | Preserve unchanged as historical and deterministic evidence. |
| W4/W5 assurance | Medium | Retain roles, risk, and independence; move provider/session selection to the operator. |
| W7/W8 | Medium | Retain generic policy/resource concepts; remove direct-provider execution and subscription metering from first-release gates. |

## Keep, amend, defer

**Keep**

- durable task state, exact artifacts, provenance, acceptance authority, and
  independent review;
- role and assurance requirements;
- deterministic fake adapters and fail-closed runtime policy;
- immutable accepted plan/contract/review artifacts.

**Amend**

- model routing becomes a recorded operator decision;
- provider-family diversity, where required, is evidence about separately
  initiated sessions rather than an automated dispatch capability;
- WP6.4 validates the brief-out/evidence-back workflow.

**Defer**

- direct provider invocation;
- credential resolution;
- live semantic-parity activation;
- evaluated provider eligibility profiles;
- provider-native receipts and per-call subscription cost accounting.

## Residual risks

1. Existing historical documents still contain mandatory live-provider language.
   Indexes and P-042 must make the supersession visible so a future worker does
   not dispatch from an obsolete snapshot alone.
2. Operator-mediated sessions need a concise handoff/return contract in WP6.4;
   this amendment defines the boundary but does not implement it.
3. Independence evidence must remain explicit. Manual session initiation does
   not by itself prove a fresh context or independent review.
4. Jira dependency links can continue to imply the obsolete sequence until
   they are corrected and read back after the amendment is accepted.

## Review boundary

This review supports a planning correction only. It does not accept runtime
implementation, provider calls, credentials, Gate 6, a pilot, or research
claims.

