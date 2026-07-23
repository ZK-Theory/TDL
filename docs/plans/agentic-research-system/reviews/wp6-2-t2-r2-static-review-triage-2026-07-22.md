# WP6.2 T2 R2 Static Review Triage

**Date:** 2026-07-22
**Status:** manager triage; no candidate acceptance or remediation authority
**Workflow:** standalone
**Research priority:** mathematical, statistical, result, provenance, and reproducibility assurance first

## Exact reviewed record

| Item | Identity |
|---|---|
| Candidate | `36b51b0571bc312043e5325ac22aee5d323e70b2` |
| Candidate tree | `be7cd32faeb9aa44c9351e3101f05c0a6ae391a6` |
| Corrected R2 report commit | `a10de8df9e0be8b381e6257aa761d8d8cea2506b` |
| Corrected R2 report blob | `f93c030d59b7df74e08d4a960f28045a6c9fbec2` |
| Corrected R2 report raw SHA-256 | `c2bb533d05d40f6720709406d98f096b288894c0eb0e044b44edcd3fc376cf8b` |
| Verdict | `rework_required`: 4 Critical, 4 Major, 0 Minor |

The first report commit bound the wrong file named `06b`. The reviewer corrected the
authority to `implementation/06b-wp6-2-live-capability-plan.md`, blob
`4b8bc7e12df98d5760b0aede7bb7d37dfc8d49b9`, raw SHA-256
`365e90089307958b7c833c635e74e3c63e65aa72e3c03945ea8f304431edfe38`, read its 542
lines, and re-evaluated the affected findings. The verdict and counts remained
unchanged. No candidate path was modified.

## Validation boundary

The static reviewer verified the exact candidate, 27-path set, 26 manifest leaves,
protected predecessor identities, LF bytes, and authority objects. The existing focused
T2 suite passed 165 tests and the validate-only contract gate passed 102 contracts.

At Stephen's direction the reprovisioned review did not run reviewer-authored security
payloads, fuzzing, mutation probes, scanners, external services, or the redundant full
665-test framework. Those omissions are explicit limitations, not candidate findings.
The report correction did not rerun tests and skipped the test-running commit hook to
preserve that restriction; it changed only the report.

## Finding triage

| Finding | Manager disposition | Research-system relevance | Proposed P-039 treatment |
|---|---|---|---|
| C1 Receipt 2.0 ordered proof | Retain, blocking | Canonical evidence and deterministic replay | Remediate exactly |
| C2 event-derived idempotency tuple | Retain, blocking | Prevents duplicated work, evidence, cost, and results after rebuild | Remediate exactly |
| C3 eight-seam pre-issue evidence | Split | Minimal credential non-persistence is necessary; scanner/manifest runtime evidence is premature | Keep opaque reference and non-persistence; defer eight-seam runtime proof to T3/T4 |
| C4 exact authority subjects | Retain, blocking | Binds work to the intended Task, Dispatch, Attempt, grant, and evidence | Remediate exactly |
| M1 composed cost/evidence gate | Retain, bounded | Operational enabling control with small closure cost | Compose existing validators; add no new accounting system |
| M2 complete W7 successors | Split/defer | Exact provider provenance matters; exhaustive runtime field assurance is T3/T4 work | Keep the T2 authority/cost subset; defer full W7 qualification |
| M3 receipt stream UUIDv7 | Retain, bounded | Deterministic identity and audit lookup | Apply existing canonical-ID rule |
| I1 independent oracle/baseline | Retain, blocking | Prevents producer self-certification and makes immutable evidence auditable | Add independent exact sets and live recomputation |

Even if C3's overextended security surface and M2's runtime-only field assurance are
removed from T2, the candidate remains `rework_required` because C1, C2, C4, and I1 are
independent authority, replay, provenance, and audit defects.

## Research-first interpretation

The narrow credential property protects research operations: raw provider credentials
must not be persisted in canonical research records. It does not justify a parallel
security-assurance programme before an adapter or resolver exists. The eight-seam
manifest and provider-specific canary evidence can only become meaningful against the
real T3/T4 transport, logging, and persistence paths.

Likewise, W7's complete provider surface is a runtime-adapter qualification obligation.
T2 needs only enough exact command/receipt evidence to preserve authority, idempotency,
cost reconciliation, provenance, and later audit. Treating every W7 child field as a T2
semantic gate moves T3/T4 implementation assurance into a contract-only package.

## Next gate

The large-workflow procedure permits only one ordinary author-review-remediation cycle.
R2 therefore cannot be sent directly into another author cycle. Stephen must first
accept an exact second-cycle authority ruling. The proposed P-039 ruling narrows the
orthogonal scope, defines the retained finding set, sets an effort budget, and permits
one final contract-only remediation followed by fresh static R3.

