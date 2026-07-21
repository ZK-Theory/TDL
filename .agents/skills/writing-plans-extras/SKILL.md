---
name: writing-plans-extras
description: Complement superpowers:writing-plans when planning from accepted specifications that may contain deferred obligations, later-gate requirements, approval boundaries, or requirements outside implementation summaries. Use before task decomposition for ARS/TDL plans or any multi-document specification with forward-looking commitments.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - manager
    - implementer
  runtime: agnostic
---

# Writing Plans Extras

Use alongside superpowers:writing-plans. This extension prevents accepted but non-local obligations from disappearing during work-package decomposition.

## Forward-Obligation Scan

Before defining tasks:

1. Inventory every governing specification, amendment, decision record, and acceptance note.
2. Search the full sources, not only summaries, for forward-looking language such as:
   - the plan must, next gate, before implementation, before release
   - deferred to, follow-up, requires separate approval
   - retention, deletion verification, migration, handoff, owner decision
3. Record each hit in an obligation register with:
   - source path and section;
   - exact obligation and owner;
   - triggering gate or deadline;
   - disposition: work package, test, review authority, explicit deferral, or out of scope.
4. Trace every obligation to a numbered plan task or a named, justified deferral. Never silently drop a hit because it sits outside the primary interface section.
5. Surface contradictions, missing owners, and unresolved approval gates before presenting the plan as executable.

## Plan Integration

Keep the obligation register in the master plan or its governing checklist. Task-level plans may reference it, but the master plan remains responsible for complete closure. Preserve owner-review and implementation-approval gates literally.

## Pre-Delivery Check

- Re-run the forward-language scan against every governing source.
- Confirm every hit has a source-backed disposition and every deferral has an owner and next gate.
- Confirm no plan task crosses an approval boundary merely because the underlying specification was accepted.
## Authority and lifecycle bindings

- For parity or policy plans, give every required semantic field a typed accepted source. Adjacent metadata and self-attested manifests are not substitutes; missing authority requires an owner-gated decision and fail-closed Partial.
- Bind evidence IDs and hashes to the execution that produced them, with negatives for plain or self-attested manifests.
- Scope re-baselines by lifecycle and evidence epoch. Never let a later baseline silently redefine the identity of evidence accepted under an earlier gate.
