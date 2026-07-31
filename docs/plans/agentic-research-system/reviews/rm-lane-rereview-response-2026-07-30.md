# RM Lane Plan-Suite Rereview Remediation Response

**Date:** 2026-07-30
**Rereview subject:** merge commit `c99cec8051be634b00681e92022ebadc9cb66019`
**Rereview:** [adversarial-rm-lane-plan-suite-rereview-2026-07-30.md](adversarial-rm-lane-plan-suite-rereview-2026-07-30.md)
**Rereview file SHA-256:** `c73ac88f2fb34dedefbe06dae690347443ced2303d4d957b43143d376aed9e1f`
**Response scope:** plan remediation only; no runtime implementation, owner acceptance, or dispatch authority

## Disposition

The `rework_required` verdict is accepted in full. Revision 3 replaces the
overloaded 06h design with three bounded predecessors:

1. [06h](../implementation/06h-wp6-1-schema-identity-and-artefact-command-seam-plan.md)
   owns exact schema identity, the complete producer matrix, T2 binding, the
   pre-change evidence record, and the selected G-RM-8 historical protocol.
2. [06i](../implementation/06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md)
   owns catalogue-complete artefact authority, independently accepted consumer
   predicates, and fail-closed production-consumer resolution.
3. [06j](../implementation/06j-w3-context-packet-lifecycle-and-resolution-plan.md)
   owns the W3 context-packet command/event family, lifecycle writer, replay
   state, and canonical resolver.

The revised [RM-00 master](../implementation/rm-00-research-methods-lane-master-plan.md)
makes those dependencies and their owner gates explicit. G-RM-3 remains open:
this response does not make any plan dispatchable.

## Finding-by-finding response

| Finding | Accepted problem | Revision-3 disposition |
|---|---|---|
| RR-C1 | Artefact commands were not bound to catalogue authority semantics. | 06i now defines forced-candidate registration, the canonical grant/actor/scope/effectivity/version/idempotency checks, an independently accepted six-dimensional consumer predicate, the complete governing review set, Stephen's `accepted_for_scope` decision, every owner-catalogue NA/NI control, and atomic no-side-effect negatives. |
| RR-C2 | No production consumer firewall existed. | 06i defines `ArtefactUseResolver` and requires the result, review, manuscript, claim, and sensitive-sidecar seams to resolve replay state, exact content hash, accepted predicate revision, consumer, scope, and current authority. It includes direct-object, local-status, projection, substitution, supersession, and sidecar bypass controls. RM-03 and RM-04 consume these seams rather than duplicating authority. |
| RR-M1 | T2 bypassed the generic schema-identity path. | 06h Task 0 freezes a producer matrix before implementation. Task 2 explicitly covers both `CommandService.submit` and `research_system/command/t2.py`; validation requires every production append path to emit the identity triple. |
| RR-M2 | G-RM-8 branch protocols were labels rather than executable choices. | 06h gives each migrate, grandfather, and no-store branch an inventory, eligibility predicate, migration identifier, input/output, repeat/replay behavior, rollback or stop rule, and distinguishing negative. |
| RR-M3 | RM-01's baseline was entirely post-change. | 06h Task 0 records the pre-change suite result, test identities, catalogue cohort, and denominator before any implementation. RM-01 compares the same cohort and current universe after 06h. |
| RR-M4 | No accepted W3 context-packet producer, lifecycle, or resolver existed. | 06j specifies the W3-complete manifest, command/event family, permitted transitions, replay state, writer, resolver, failure states, and controls. New owner gate G-RM-12 must accept that contract before implementation. |
| RR-M5 | RM-02's append-only history was self-attested. | RM-02 now requires an independent history-bearing Git base/subject anchor supplied by the acceptance runner, validates ancestry and a pinned prior blob, forbids accepted state in the pack, and adds a coordinated asset/manifest/history rewrite negative. |
| RR-M6 | The capability boundary omitted CLI entry points and allowed broad namespaces. | RM-03 and RM-04 now enumerate the exact CLI handlers and their full transitive call graphs, require a closed capability set, forbid broad `research_system.*` allowance, and retain only the exact pre-existing Git-root discovery exception. |
| RR-m1 | RM-01 cited stale `pyproject.toml` line numbers. | RM-01 identifies the governed semantic keys and values instead of line numbers. |
| RR-m2 | RM-01 named the wrong close-out README. | RM-01 now names `docs/plans/agentic-research-system/implementation/README.md`. |
| RR-m3 | RM-00 used the obsolete `VerificationResult` term and overstated verification. | RM-00 and RM-04 use `OperatorVerificationRun` and state that the record is operator-reported evidence only; it does not certify ARS execution or acceptance. |

## Verified planning basis

The revision was written against the exact rereview subject, not against an
assumed single append seam:

- generic submission performs schema validation before its guarded append;
- T2 performs separate validation and appends through its own path;
- the existing ledger grant resolver already supplies useful current-grant,
  actor, command, scope, and effectivity checks, but it is not artefact-use
  acceptance;
- the existing control-store resolver is a content-addressed external-record
  reader, not the missing artefact consumer firewall;
- the existing context compiler and source resolver do not provide a W3 packet
  lifecycle, writer, replay authority, or accepted resolver;
- no existing production manuscript or claim consumer can serve as proof of
  artefact-use enforcement.

These facts constrain the plans' interfaces. They are not evidence that the
new contracts have been implemented.

## Gate state after remediation

| Gate | State |
|---|---|
| G-RM-3 fresh independent review of the complete revision-3 suite | **Open** |
| G-RM-8 historical-event protocol selection | **Open** |
| G-RM-9 exact schema-byte authority selection | **Open** |
| G-RM-10 artefact authority and consumer-predicate contract | **Open** |
| G-RM-12 W3 context-packet lifecycle and resolver contract | **Open** |

No implementation plan may be dispatched until its predecessor plans and owner
gates are accepted in the order stated by RM-00. A passing schema test, local
plan consistency check, or this author response cannot close G-RM-3 or any
owner gate.
