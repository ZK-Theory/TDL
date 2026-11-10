---
name: writing-plans-extras
description: Complement superpowers:writing-plans when planning from accepted specifications that may contain deferred obligations, later-gate requirements, approval boundaries, or requirements outside implementation summaries. Use before task decomposition for ARS/TDL plans or any multi-document specification with forward-looking commitments.
metadata:
  version: "1.5.0"
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
6. Sweep every child/sub-plan for owner-touchpoint preconditions ("requires
   owner approval before X", "must be recorded before Y") and hoist each into
   the governing master gate checklist with its source cited. A precondition
   that remains only in child prose has no forcing function for the acceptance
   runner.
7. Run `grep -n "<package>" docs/plans/agentic-research-system/03-decisions-and-open-questions.md`
   and enter every register sentence that names the package ("Carried to
   <package>", "<package> validates …") in the obligation register, each with a
   keep or depart disposition. A forward obligation in the owner register is part
   of the next package's specification.

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

## Interface Verification (before writing tasks)

For every seam a plan names — a function, schema, runtime call, or event
family the tasks will build against — open the file and record the actual
signature/behaviour with a `path:line` citation in the plan itself, or mark
the plan `interface-unverified` and make that an explicit dispatch blocker.
A plan that writes a File Map naming a production module, or calls a seam
"expected", has recorded a doubt without paying to resolve it — the cost of
reading the file at authoring time is minutes against a Worker-session
rediscovering the same mismatch at full price, after a branch and worktree
already exist. A Stop-Partial rule present in the plan is not a substitute
for this: it only fires after dispatch, once context has already been spent.

A wiring claim ("X passes Y to Z") needs more than the signature: see "Wiring
claims" in the claims checklist below.

## Authority Boundary Check

A plan cannot mint authority by naming a gate or a dispatchable stage. Every
gate ID and dispatchable stage a plan introduces, or repurposes from an
existing one, must resolve to an accepted decision-register entry — not a
proposed-only or reviewer-only record. Extract every gate ID and
dispatchable stage from the master and child plans and fail the plan on any
that has no such resolution. A reviewer verdict (including an adversarial
review's "accept") can make a subject *eligible* for a separately recorded
owner decision; it is evidence for that decision, never a substitute for it,
and it cannot close an owner gate by itself.

## Caller-Inventory Closure

A "no other caller" or firewall claim needs a registry-aware transitive
closure, not a direct-caller grep or a module-category label ("adapter-only").
Seed the traversal from every CLI and rederivation root, follow first-party
calls through routing, coordination, executor-registry lookup, and
variant-matrix rows, and emit a literal symbol-and-fixture disposition table;
fail when a root, registry entry, wrapper, or fixture row has no recorded
disposition. For any entry classified "protected", require a runtime
negative that enters through the real root and proves capability rejection
before route/grant/lease/provider effects — a unit test at the final wrapper
alone does not establish the claim. The same closure backs a negative claim
about enforcement: see "Enforcement claims" in the claims checklist below.

## Claims About Artefacts the Plan Does Not Own

Before the plan states a claim about an artefact it does not own, do the check
and cite it. The checks live in one file shared with `adversarial-design-review`:
`../adversarial-design-review/references/claims-checklist.md`, beside this
skill's directory in whichever skills tree loaded it. Apply the **Author** line of
each entry that matches a claim in the plan: reuse, shared-store tenants (the
whole-ledger reader inventory for a new command or event family), precedents and
"handled by existing X", restated preconditions, catalogue IDs, selector
contracts, "in the shape of", verifiers, negative controls, prescribed
corrections, probes, absence, enforcement and wiring claims, rules the owner may
already have fixed, carried obligations, and shared locations. A new lesson of
this kind goes into that file, once, with both an author and a reviewer line.

## Currency Addenda

An addendum that extends an inherited status table inherits its claims of
currency. Re-derive every inherited row against current evidence, or mark each
row "not re-checked at `<commit>`". "Table X stands; these rows are added"
leaves stale classes on rows nobody re-checked.
