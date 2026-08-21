# 06r — Gate 6 PR #258 Review-Convergence Plan

**Date:** 2026-08-21

**Status:** `IN_PROGRESS / schema_lineage_fix_ready_for_final_binding`

**Authority:** bounded subordinate plan to
[06q](06q-gate6-spec-real-run-integration-and-follow-up.md). This document does
not replace 06q, alter the recorded `PARK` research decision, or authorize a
merge.

**Starting subject:** PR
[#258](https://github.com/ZK-Theory/TDL/pull/258), branch
`codex/gate6-spec01-spec02-real-run`, exact head
`bb9ab7a0f679ba71d2a364410f69ec53673c2ae2`.

## 1. Purpose

PR #258 has not converged under review. Forty-nine commits, 145 changed files,
35,796 added lines, and 97 review threads have produced a repeating pattern:
individual counterexamples are repaired and tested, but the owning invariant
is not closed over the complete action or transaction family before the next
review.

The immediate objective is not to clear the latest comments one at a time. It
is to make the smallest architectural correction that gives the public SPEC
route one authoritative action-state model and the binding-advance path one
atomic transaction boundary. The current comments become required regression
examples within those two complete failure families.

Gate 6 remains `PROVEN / integration_pending`. The real-run evidence and `PARK`
disposition remain valid historical results. This plan concerns whether the
implementation candidate is safe and coherent enough to integrate.

## 2. Evidence for the diagnosis

- Review remediation after the first recorded result added 20,905 lines across
  103 files, exceeding the original 16,364-line candidate.
- Twenty-seven review threads concern `research_system/discovery/spec_flow.py`.
- Three of the four unresolved exact-head findings at plan creation concern
  SPEC action completion, retry, or evidence association.
- The latest commit changed only the SPEC candidate-scope callback in
  `spec_flow.py`; the four current defects predate that change. The review loop
  is therefore mainly delayed discovery across an oversized surface, although
  earlier remediation introduced one of the loose joins.
- The active research-observer record is
  `01M0JEKDT55EG2AAWCCJ1HEEFK`, “Specimen-by-specimen PR remediation has no
  convergence gate.”

## 3. Governing boundaries and obligation register

| Source | Obligation | Disposition here |
| --- | --- | --- |
| [06q §4](06q-gate6-spec-real-run-integration-and-follow-up.md#4-integration-job--kan-103--pr-258) | Review and remediate only current, valid findings at the exact PR head. | Preserve. The current comments are inputs to class-wide repairs, not independent scope expansions. |
| [06q stop conditions](06q-gate6-spec-real-run-integration-and-follow-up.md#stop-conditions) | No stale-subject merge, no premature `INTEGRATED`, no live-evidence amendment, and no unrelated residual jobs in PR #258. | Hard stops. |
| [06p merge admission](06p-gate6-control-model-proposal.md#m---merge-admission) | Current exact-head findings must be resolved; Stephen owns final merge authority and reviewer operation. | No merge, reviewer trigger, or inferred owner acceptance in this plan. |
| Recorded Gate 6 result | The public route and live result remain the decisive positive path. | Preserve byte/replay compatibility; do not rerun or mutate the live store during construction. |
| PR #258 current review | Three SPEC-flow findings and one binding-advance finding remain unresolved. | SPEC flow first; binding advance is the second bounded workstream. |
| Residual jobs in 06q §5 | Git locator, backup, wrapper equivalence, empirical freeze, task projection, and human result view remain follow-on work. | Explicitly out of scope for this convergence repair. |

## 4. Verified current interfaces

The plan is bound to the current code rather than an expected future shape:

- [`_COMMAND_ACTION_ROWS`](../../../../research_system/discovery/spec_flow.py#L113),
  [`_DOCUMENT_TYPES`](../../../../research_system/discovery/spec_flow.py#L139), and
  [`_SINGLE_SHOT_ACTIONS`](../../../../research_system/discovery/spec_flow.py#L167)
  formed three overlapping action registries at the starting subject.
- [`_registered_documents`](../../../../research_system/discovery/spec_flow.py#L790)
  resolves durable SPEC documents and their completion proofs.
- [`_action_identity`](../../../../research_system/discovery/spec_flow.py#L1084),
  [`_complete_action`](../../../../research_system/discovery/spec_flow.py#L1126),
  and
  [`_validate_completed_document_retry`](../../../../research_system/discovery/spec_flow.py#L1233)
  independently interpret completion and exact retries.
- [`status`](../../../../research_system/discovery/spec_flow.py#L1424) derives the
  next action from route rows, projected state, documents, and the preparation
  journal.
- [`_advance_unfenced`](../../../../research_system/discovery/spec_flow.py#L2219)
  separately derives accepted actions and `already_completed`, then dispatches
  all action families.
- The decisive public regression surface is
  [`test_discovery_spec_flow_cli.py`](../../../../tests/research_system/integration/test_discovery_spec_flow_cli.py).
- [`advance_store_binding`](../../../../research_system/store/binding_repair.py#L626)
  validates its predecessor before entering the writer lock at line 769 and
  publishes transaction effects before the final predecessor comparison.

These interfaces are verified at the starting subject. Any signature or
ownership change must update this section before a later workstream relies on
it.

## 5. SpecFlow convergence contract

One action-state evaluator must own the following invariants.

### SF-1 — Total registered action state

Every public SPEC action resolves to exactly one state from durable evidence:

- `not_started` — no preparation or completion identity exists;
- `prepared` — the exact packet is journalled for recovery but has no complete
  durable effect set;
- `completed` — the exact completion evidence exists and reconstructs the
  durable public result.

An unregistered action or contradictory evidence fails closed. Empty expected
row or document sets never imply completion.

### SF-2 — Exact completion identity

Document completion binds one complete tuple:

`(route, action, retry_id, packet_sha256, document_type, artefact_id,
content_sha256, registration_event_id, registration_event_sha256)`.

Every component is conjunctive. An action match cannot substitute for an
artefact match, and an artefact match cannot substitute for an action match.
Unrelated later registrations of the same document type are inert.

### SF-3 — Retry ordering

`advance` resolves durable state before checking live admission authority:

1. a completed exact packet returns its reconstructed durable result;
2. a completed different packet conflicts;
3. a prepared exact packet resumes its owned recovery path;
4. `not_started` work must be the next action and satisfy current authority;
   a prepared recovery that still has unpublished effects also remains subject
   to the production command service's authority checks.

Expiry of a grant after successful completion cannot invalidate an exact
read-only retry. Preparation proves packet identity and recovery ownership; it
does not extend an expired grant for effects that were never admitted.

### SF-4 — One status/admission interpretation

`status()` and `advance()` must consume the same action definitions and state
evaluator. They may format different outputs, but they cannot carry separate
completion rules, partial-action aliases, or prerequisites.

### SF-5 — Exact unrelated-evidence isolation

Unrelated route rows, foreign candidates, later same-type documents, and
completion proofs for another action must not advance, block, or corrupt the
current SPEC route.

### SF-6 — Existing durable compatibility

The live 444-event result and accepted historical compatibility paths must
replay to the same terminal status. Legacy inference remains only where the
current ledger requires it; it must feed the same action-state output rather
than remain a second admission model.

## 6. SpecFlow implementation sequence

### SF-A — Red public controls

Add and watch fail, at the public CLI or durable snapshot seam:

1. premature `review_spec_01_brief_inputs` and
   `accept_spec_01_brief_inputs` with empty effects reject without publishing
   an action identity;
2. an exact completed document retry returns the durable result after its
   original grant expires and appends nothing;
3. a later generic registration of the same SPEC document type does not poison
   status or associate with another action's completion proof.

Each is `remediation-red`. Existing route completion, changed-packet conflict,
and unrelated-row tests are `preservation-green`.

### SF-B — One internal action definition

Replace overlapping membership/alias decisions with one immutable internal
definition per public action. It may remain in `spec_flow.py` initially to
avoid adding another layer. Extract a module only if the result removes more
coordination code than it creates.

The definition owns action aliases, required durable effects, optional
document type, single-shot identity, and the completion-proof matcher. It must
not embed handler implementation or duplicate route business rules.

### SF-C — One state evaluator

Introduce one side-effect-free evaluator over the existing snapshot and exact
packet identity. Use it in document census, `status()`, retry validation, and
`advance()`.

Do not create a second persisted state machine. Events, registrations, receipts,
completion proofs, and the existing preparation journal remain the durable
facts.

### SF-D — Simplify public advancement

Make `_advance_unfenced` follow one visible order: parse packet, snapshot,
resolve action definition/state, return/conflict/resume, enforce next action,
validate the selected handler, publish, and complete. Delete the superseded
`already_completed` heuristic and action-specific completion aliases.

### SF-E — Complete family matrix

Derive the test cases from the action registry rather than a hand-written
subset. For every action class, cover applicable empty, partial, exact,
conflicting, unrelated, retry, and completion states. The positive execution
signal reports the enumerated action count; removing one registry member or
weakening an exact tuple must make a watched negative fail.

### SF-F — Compatibility and review readiness

Run the narrow public controls first, then the complete SPEC-flow integration
module because the shared action registry is cross-cutting within that module.
Run replay/live-store checks read-only. Run the broader required repository
gate only once at the frozen candidate head.

No push occurs until the local convergence review has re-read the complete
action registry, evaluator, public dispatcher, completion proof, and family
matrix together.

### 6.1 Implementation record — 2026-08-21

The local SpecFlow slice is implemented in commit
`abb435a4ec0b23f1265626ea763ed4966556d582`, based on
`bb9ab7a0f679ba71d2a364410f69ec53673c2ae2`; it has not been pushed.

Completed in this slice:

- introduced one immutable action-definition registry for required route rows,
  public aliases, document schema/type, single-shot recovery, and brief-input
  authority state across all 25 actions;
- introduced an explicit `not_started` / `prepared` / `completed` action-state
  evaluator and made `status()` and `advance()` consume it from the same
  immutable snapshot;
- indexed document completion evidence by the exact document artefact,
  content, registration event, route, action, retry, and packet tuple, so a
  later same-type registration is inert for both status and exact retry;
- reconstructed completed document and brief-input results from exact
  registrations and accepted receipts before live authority validation;
- extended the existing preparation journal to all single-shot actions, so
  completed effects without a completion identity remain `prepared` until the
  exact packet seals them;
- routed reconstructed results through the idempotent completion seam, so a
  prepared recovery appends its missing completion proof while an already
  sealed retry remains read-only; and
- corrected the approval-restart preservation test to retain the required
  `prepared` state after byte recovery until the exact packet seals completion;
  corrected two independently reproduced starting-head fixture failures
  without weakening the production Assay or external-approval replay gates;
- corrected the pre-existing assay-authority census omission by deriving
  OR-101 through OR-104 from the exact projected content and observation
  records, with a nine-phase `empty` through `accepted` control; and
- repaired seven stale module tests that reproduced unchanged at the starting
  head: the missing recorded-time fixture, exact-subject error expectation,
  projected assay census, pre-brief generic-submit negative, and three private
  helper calls/fixtures.

The consolidated remediation matrix passes all 11 public cases. The existing
seven-case preparation/restart/conflict selector passes. The three-stage
expired-grant retry, three-stage crash-before-identity, partial brief recovery,
complete SPEC-02, partial SPEC-01, and partial SPEC-02 paths pass. The final
expanded module passes all 109 tests in 5,211.12 seconds. The direct artefact
storage boundary passes; both contract-binding modes pass all 103 contracts;
Ruff, formatting, syntax compilation, and `git diff --check` pass. The local
adversarial disposition is recorded in
[the 2026-08-21 review](../reviews/adversarial-gate6-pr258-specflow-convergence-local-review-2026-08-21.md)
as `accept_with_required_changes` pending clean-head live replay.

The SpecFlow code/test workstream is locally complete. The first clean-head
live check was rejected before replay with `binding recovery Git subject
changed`: the governed live recovery binding is pinned to the preceding Git
subject. That is the separate binding-advance invariant below, not a SpecFlow
status mismatch. The rejection occurred while loading the operator and before
any replay or write.

Still open before publication:

- commit the locally validated binding-advance transaction workstream on one
  frozen candidate subject;
- advance the governed live binding to the frozen candidate subject;
- rerun read-only live general replay and public SPEC status under SF-F, with a
  complete file-byte/hash inventory before and after; and
- only if live compatibility passes, upgrade the conditional local disposition
  and push the same branch for the next owner-triggered external review cycle.

## 7. Binding-advance workstream

This begins only after SpecFlow is locally coherent.

That precondition is now met. The clean-head live rejection above is the
production trigger for this workstream: without a governed successor binding,
every new candidate head is correctly refused before the existing result can
be replayed.

The owning invariant is: acquire the writer lock before reading the authoritative
predecessor used to derive a successor; re-read and compare it under that lock;
and let a losing concurrent invocation fail before publishing a marker, object,
event, or receipt. Recovery must use the same exact operation identity.

Required controls include two contenders with the same predecessor, an exact
retry after interruption at every durable phase, and proof that the losing
contender leaves no owned residue.

### 7.1 Implementation record — 2026-08-21

The local transaction repair is implemented, reviewed, and committed as the
second local convergence commit after the SpecFlow commit; neither commit is
pushed.
`advance_store_binding` now acquires the control-store writer lock before it
selects candidate evidence or reads the authoritative recovery predecessor,
ledger, or scoped receipts. One locked helper revalidates the source-bound
manifest and owner authority, then derives and publishes exactly one successor
from that predecessor.
The public entry validates the physical runtime anchor and immutable owner
authority before it may publish the transient lock record, then repeats the
authority check inside the transaction.

A deterministic two-contender control reproduced the starting defect: the
delayed loser had selected the old predecessor before locking, then published
its own object, event, and receipt before the final recovery replacement
detected the winner. With the repaired boundary, the loser acquires the lock
after the winner, re-reads the successor, rejects the same candidate as not a
strict descendant, and leaves no marker, object, event, or receipt.

Recovery coverage now starts at marker publication and covers marker, object,
event, receipt, and recovery replacement. The original 13-case binding-advance
slice produced 12 passes and one correct redirected-file rejection whose
diagnostic label had drifted; restoring the established label made that exact
case pass. A whole-boundary reread then identified the transient lock as a
redirectable effect: physical runtime validation was added, and the redirected
runtime plus strengthened two-contender controls both pass. All 14 selected
behaviours are therefore green across the combined evidence without rerunning
the unaffected 109-case SpecFlow module.

Ruff, formatting, syntax compilation, `git diff --check`, and both contract
binding modes pass; each contract mode validates all 103 registered contracts.
The local whole-boundary review has no open code finding.

Still open for this workstream:

- obtain an authentic current owner intent and use the existing governed public
  binding-advance seam for the resulting exact candidate; and
- prove the subsequent public SPEC replay is byte-for-byte read-only and
  terminally identical to the recorded Gate 6 result.

The operational census found 24 earlier owner intent files in
`C:\Users\steph\AppData\Local\Temp\gate6-spec-live-20260815`. Every one expired
on 16 August 2026. None authorizes a new 21 August transaction, and no exact
in-progress marker exists for this candidate. The implementation therefore
rejects their reuse. A new owner-issued intent is a genuine remaining authority
input; it will not be synthesized from an old intent or treated as implied by
green local tests.

### 7.2 Reviewed route-successor correction — 2026-08-21

Stephen subsequently gave the explicit instruction to issue the current owner
intent and run the governed advance. The execution preflight then found that a
plain clean-descendant advance would still be correctly rejected: the live
binding records route-package SHA-256 `4115f135c3459465ad492295366d1877a6ccc03549c7b53b893e00655567c14f`,
whereas the reviewed candidate records
`fad7c5a9c9fd3cdec85125b20f006b7989c050d3050ec7fe7e7eb531744692d4`.
The two protected SPEC source files remain byte-identical. The route change is
the governed PARK-test and owner-decision registration added during review, not
an unexplained source mutation.

The advance seam now has a separate reviewed-route-successor variant. Its
public owner intent binds the predecessor binding hash, predecessor route hash,
successor route hash, and exact candidate commit. All four coordinates are
conjunctive; the route must actually change; both SPEC source records must
remain identical; and any mismatch rejects before publication with a complete
store-byte snapshot unchanged. The accepted successor retains those four
coordinates as transition authority, and recovery independently re-derives
their relation to the immutable predecessor object, current route, exact Git
head, and protected sources.

The flat public intent now has its own registered schema rather than claiming
the durable command-envelope identity. The legacy flat identity is accepted
only for an exact command already committed to the ledger, preserving old
idempotent retries without allowing new publication. Transition-local route
authority is removed from a later ordinary descendant successor; its immutable
predecessor object retains the historical route transition.

The watched positive, four-coordinate negative, changed-SPEC, legacy retry,
authority-tamper, and route-successor-to-ordinary-descendant controls pass. The
complete 17-case binding-advance regression passes, including five crash
phases, expiry recovery, concurrent predecessor selection, and redirection
defences. All 54 schema-registry tests pass. Ruff, formatting, syntax
compilation, and `git diff --check` pass.

The remaining operational action is now concrete: freeze this implementation
as a clean commit, materialize the newly authorized intent against that exact
commit and the current live predecessor, run the governed route-successor
advance, and then run general replay and public SPEC status with before/after
byte inventories. No push, external-review operation, or merge is authorized
by this step.

### 7.3 First live transition and replay correction — 2026-08-21

The reviewed-route implementation and this plan were frozen at local commit
`81076eb6ed1b442e7cbb61a752afdb91e5c33597`. The new canonical public intent is
`advance-binding-reviewed-route-successor-20260821-v1.json`, SHA-256
`84bbd539328a49e5ddeedcf23c7f97ab0adc90e493bf469580e7885f7b3b8abc`.
Its first invocation failed before publication because four pre-existing
owner-context schema files had CRLF worktree bytes while their exact Git blobs
used LF. The complete 1,749-file control-store inventory was unchanged. Those
four physical files were normalized to their already-committed blobs; no index,
tree, or commit content changed, and all 436 schema files then matched the exact
candidate subject.

The retry succeeded through the public `ars store advance-binding` seam:

- command payload SHA-256:
  `c9f01f547a6126d903941c1f11f349df186a0fc7a90f52c8c3d0ec2998f5790a`;
- transaction:
  `txb_01a0265b-b454-73e0-9081-fe86af2d94af`;
- live event count: 444 to 445;
- predecessor binding SHA-256:
  `05ddae128785b0890a347aca4b2e31ae4d4bee6b1c929c7378c0566a55974622`;
- successor binding SHA-256:
  `423614c3ec00815f05823f474bc5b9a0dbd299cc0853bb2f77897d8c27c32bc8`;
  and
- exact changed set: one new `StoreBindingAdvanced` event, the current binding,
  one immutable binding object, one accepted receipt, and one idempotency
  index. No recovery marker or writer lock remained.

The subsequent generic `ars replay verify` call failed read-only because its
ledger preflight admitted only an ordinary `ApprovedProjectBinding`; unlike the
Discovery operator, it did not try the explicitly selected and fully governed
`ControlBinding.load_repaired` path. All 1,753 control-store files remained
unchanged. The replay ledger now uses the same fail-closed admission order as
the operator: ordinary approved binding first, then the exact store-owned
`binding-repair-control-binding.json` only if its store-recovery foundation,
recovery object, Git subject, schema catalogue, route, sources, manifest, and
origin witness all validate. It also requires that binding to name the exact
requested control root.

The new repaired-binding replay regression and the existing CLI authority and
completed-SPEC replay tests pass. The next action is to commit this read-only
replay correction and record update, issue an ordinary clean-descendant intent
for that exact commit, advance the live binding once more without route or SPEC
change, and run full replay plus public SPEC status under complete before/after
inventories.

### 7.4 Append-only schema-lineage repair — 2026-08-21

The replay correction and record were frozen at local commit
`6acce2ba1b0912fd45b418c466cf7930cbe678ec`. Canonical ordinary intent
`advance-binding-replay-fix-20260821-v1.json`, SHA-256
`8fbd16b1aaee1ef9fccd3671eaee7bb0e9403a007de0b6a134f7590912aa8a50`,
advanced the live binding from event 445 to 446. Its transaction was
`txb_01a02668-fa30-7a1a-82a8-fa9d15ae0c7b`; binding SHA-256 moved from
`423614c3ec00815f05823f474bc5b9a0dbd299cc0853bb2f77897d8c27c32bc8`
to `572a8b66dd270619ecb993789459bf9e1775f8bcb76bede853b946085fccb7b5`.
The same exact five-path publication pattern held, route and SPEC bytes were
unchanged, transition-local route authority was not inherited, and no marker
or writer lock remained.

Full replay then failed read-only at event 149. The reviewed-route correction
had expanded the durable `AdvanceStoreBinding` command schema in place while
leaving its version at `1.0.0`. Events 149 through 441 bind the original v1.0
hash `cbbe5b6b3a9cd6d97c8c648cfe7c49e16b3b813b800e28ffa94c1d7ebe4f8157`;
the two new live events 445 and 446 bind expanded bytes under the same version,
hash `5f15223aeec3cbe0825a49b5395467a62cda255378496a04fc83941557dbc3cb`.
The registry correctly rejected that collision. All 1,757 control-store files
were unchanged by the failed replay.

The correction is append-only:

- restore the original v1.0 schema bytes and hash as the unique active
  catalogue entry for that version's history;
- add the expanded schema as proper version `1.1.0` and make v1.1 the active
  command binding for all new writes;
- retain the exact already-recorded expanded-v1.0 bytes in a content-addressed
  schema-history archive; and
- admit that archive only through a canonical exact manifest keyed by schema
  ID, version, raw-byte hash, and fixed archive path. It is never selected as
  the active or default v1.0 schema.

Unknown hashes, changed archive bytes, mismatched IDs/versions, redirected
paths, duplicate aliases, and aliases without a distinct active successor fail
closed. Registry controls prove the original v1.0 hash, the exact collision
hash, and active v1.1 hash
`6a48ef967208ccf6af8df86bcb454ddc2544f19106c6074f1c91c45d9651c967`.
New route-successor and ordinary advances emit v1.1; legacy flat public input
remains retry-only.

The next operation is to commit this lineage repair, issue one ordinary
clean-descendant intent for that exact commit, append its v1.1 binding event,
and rerun full replay and public SPEC status with unchanged-file proofs. No
historical event or object is rewritten.

## 8. Validation and exact-head review

Validation follows the changed behavior:

1. the three new remediation-red controls;
2. existing preservation controls for route completion, recovery, replay,
   changed-packet conflict, and unrelated evidence;
3. the complete SPEC-flow integration module after the registry becomes a
   shared seam;
4. formatting, Ruff, `git diff --check`, contract binding, and the direct
   artefact-storage boundary check;
5. read-only replay of the live result at the frozen local candidate;
6. one local adversarial re-read of the complete owning boundary;
7. one push and one final exact-head external review, only after the preceding
   evidence is complete.

Stephen remains the only authority to trigger or monitor CodeRabbit and to
permit merge. Resolved comments, green CI, or a mergeable state do not grant
that authority.

## 9. Stop-loss rule

After the convergence commit receives one final exact-head review:

- a new P1 in a different, demonstrably bounded family is assessed normally;
- a new P1 showing that SF-1 through SF-6 or the binding transaction invariant
  is still incomplete stops specimen remediation; and
- the current integration candidate is then retired in favour of smaller,
  coherent replacement slices unless Stephen explicitly accepts the residual
  risk.

This is the cost boundary that prevents another indefinite comment loop.

## 10. Completion rule

This plan is complete only when:

- the SpecFlow and binding-advance invariants are implemented and directly
  tested;
- the exact current live result replays unchanged;
- one frozen PR head has no unresolved material review finding;
- required CI is green at that head; and
- Stephen separately authorizes the merge.

Until then, report:

`Capability status: INCOMPLETE — PR #258 remains unintegrated.`
